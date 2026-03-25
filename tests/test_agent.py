from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_app.config import get_settings, resolve_model_config
from agent_app.core.agent import Agent
from agent_app.llm.mock import MockLLM
from agent_app.main import build_skill_registry, build_tool_registry
from agent_app.memory.session_store import JsonSessionStore
from agent_app.skills.loader import load_skill_from_markdown
from agent_app.skills.registry import SkillRegistry
from agent_app.tools.calculator import CalculatorTool
from agent_app.tools.document_readers import ReadPdfTool, ReadWordTool, ReadXlsxTool
from agent_app.tools.filesystem import (
    MoveFileTool,
    ReadFileTool,
    RemoveFileTool,
    RenameFileTool,
    WriteFileTool,
)
from agent_app.tools.registry import ToolRegistry
from agent_app.tools.time_tool import TimeNowTool


class AgentFlowTestCase(unittest.TestCase):
    def test_agent_uses_calculator_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ToolRegistry()
            registry.register(TimeNowTool())
            registry.register(CalculatorTool())

            agent = Agent(
                llm=MockLLM(),
                tool_registry=registry,
                session_store=JsonSessionStore(Path(tmpdir)),
            )

            reply = agent.run("2 * (3 + 4)", session_id="calc")

        self.assertIn("14", reply)

    def test_agent_reports_loaded_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ToolRegistry()
            registry.register(TimeNowTool())
            skill_dir = Path(tmpdir) / "skills"
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skill_dir / "inspector.md"
            skill_path.write_text(
                (
                    "---\n"
                    "name: inspector\n"
                    "description: Inspect local content.\n"
                    "tools: read_file\n"
                    "---\n"
                    "Look at local files before answering.\n"
                ),
                encoding="utf-8",
            )

            agent = Agent(
                llm=MockLLM(),
                tool_registry=registry,
                session_store=JsonSessionStore(Path(tmpdir)),
                skill_registry=SkillRegistry.from_directory(skill_dir),
            )

            reply = agent.run(
                "当前有哪些技能",
                session_id="skills",
                skill_names=["inspector"],
            )

        self.assertIn("inspector", reply)


class FileToolTestCase(unittest.TestCase):
    def test_file_tools_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            writer = WriteFileTool(workspace)
            reader = ReadFileTool(workspace)
            renamer = RenameFileTool(workspace)
            mover = MoveFileTool(workspace)
            remover = RemoveFileTool(workspace)

            write_result = writer.run(
                json.dumps({"path": "notes/todo.txt", "content": "hello agent"})
            )
            self.assertIn("写入文件", write_result.content)

            read_result = reader.run(json.dumps({"path": "notes/todo.txt"}))
            self.assertEqual("hello agent", read_result.content)

            rename_result = renamer.run(
                json.dumps({"path": "notes/todo.txt", "new_name": "done.txt"})
            )
            self.assertIn("重命名文件", rename_result.content)

            move_result = mover.run(
                json.dumps(
                    {
                        "source": "notes/done.txt",
                        "destination": "archive/done.txt",
                    }
                )
            )
            self.assertIn("移动文件", move_result.content)

            remove_result = remover.run(json.dumps({"path": "archive/done.txt"}))
            self.assertIn("删除文件", remove_result.content)
            self.assertFalse((workspace / "archive" / "done.txt").exists())

    def test_file_tools_reject_paths_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = ReadFileTool(Path(tmpdir))
            result = reader.run(json.dumps({"path": "../outside.txt"}))
            self.assertIn("工作目录内", result.content)


class DocumentReaderToolTestCase(unittest.TestCase):
    def test_read_pdf_tool_extracts_text(self) -> None:
        from reportlab.pdfgen import canvas

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            pdf_path = workspace / "docs" / "sample.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            pdf = canvas.Canvas(str(pdf_path))
            pdf.drawString(72, 720, "Hello PDF")
            pdf.drawString(72, 700, "Second line")
            pdf.save()

            reader = ReadPdfTool(workspace)
            result = reader.run(json.dumps({"path": "docs/sample.pdf"}))

        self.assertIn("Hello PDF", result.content)
        self.assertIn("Second line", result.content)

    def test_read_xlsx_tool_extracts_cells(self) -> None:
        from openpyxl import Workbook

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            xlsx_path = workspace / "data" / "sample.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Summary"
            sheet.append(["name", "score"])
            sheet.append(["alice", 95])
            workbook.save(xlsx_path)
            workbook.close()

            reader = ReadXlsxTool(workspace)
            result = reader.run(json.dumps({"path": "data/sample.xlsx"}))

        self.assertIn("[Sheet Summary]", result.content)
        self.assertIn("alice\t95", result.content)

    def test_read_word_tool_extracts_paragraphs_and_tables(self) -> None:
        from docx import Document

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            docx_path = workspace / "docs" / "sample.docx"
            docx_path.parent.mkdir(parents=True, exist_ok=True)

            document = Document()
            document.add_paragraph("Hello Word")
            table = document.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "name"
            table.cell(0, 1).text = "role"
            table.cell(1, 0).text = "alice"
            table.cell(1, 1).text = "agent"
            document.save(docx_path)

            reader = ReadWordTool(workspace)
            result = reader.run(json.dumps({"path": "docs/sample.docx"}))

        self.assertIn("Hello Word", result.content)
        self.assertIn("alice\tagent", result.content)


class SkillTestCase(unittest.TestCase):
    def test_load_skill_from_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "reader.md"
            skill_path.write_text(
                (
                    "---\n"
                    "name: reader\n"
                    "description: Read local documents.\n"
                    "tools: read_file, read_pdf\n"
                    "---\n"
                    "Use file tools before answering.\n"
                ),
                encoding="utf-8",
            )

            skill = load_skill_from_markdown(skill_path)

        self.assertEqual("reader", skill.name)
        self.assertEqual(("read_file", "read_pdf"), skill.allowed_tools)
        self.assertIn("Use file tools", skill.prompt)

    def test_build_skill_registry_from_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skills"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "writer.md").write_text(
                (
                    "---\n"
                    "name: writer\n"
                    "description: Write files safely.\n"
                    "---\n"
                    "Prefer write_file for edits.\n"
                ),
                encoding="utf-8",
            )
            settings = get_settings(model_provider="mock")
            settings.skills_dir = skill_dir

            registry = build_skill_registry(settings)

        self.assertEqual(["writer"], [skill.name for skill in registry.list_skills()])


class ModelConfigTestCase(unittest.TestCase):
    def test_openai_preset(self) -> None:
        config = resolve_model_config(provider="openai", api_key_override="test-openai")
        self.assertEqual("openai", config.provider)
        self.assertEqual("gpt-4.1-mini", config.model_name)
        self.assertEqual("https://api.openai.com/v1", config.base_url)
        config.validate()

    def test_gemini_preset(self) -> None:
        config = resolve_model_config(provider="gemini", api_key_override="test-gemini")
        self.assertEqual("gemini", config.provider)
        self.assertEqual("gemini-2.5-flash", config.model_name)
        self.assertEqual(
            "https://generativelanguage.googleapis.com/v1beta/openai/",
            config.base_url,
        )
        config.validate()

    def test_glm_alias_and_preset(self) -> None:
        config = resolve_model_config(provider="glm-4.7", api_key_override="test-glm")
        self.assertEqual("glm", config.provider)
        self.assertEqual("glm-4.7", config.model_name)
        self.assertEqual("https://api.z.ai/api/paas/v4/", config.base_url)
        config.validate()

    def test_settings_builds_registry_with_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = get_settings(model_provider="mock")
            settings.workspace_root = Path(tmpdir)
            registry = build_tool_registry(settings)
            tool_names = {spec.name for spec in registry.specs()}

        self.assertTrue(
            {
                "read_file",
                "write_file",
                "rename_file",
                "move_file",
                "rm_file",
                "read_pdf",
                "read_xlsx",
                "read_word",
            }.issubset(tool_names)
        )


if __name__ == "__main__":
    unittest.main()
