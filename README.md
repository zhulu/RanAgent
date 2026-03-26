# Minimal Python Agent Skeleton

一个方便继续手改的单 Agent 骨架，默认支持本地离线调试，并内置文件工具、文档读取工具、技能系统、FastAPI 服务层和 SQLite 长期记忆。

## 当前架构

主链路如下：

`CLI / FastAPI -> Agent Loop -> Skill Context -> LLM Backend -> Tool Registry -> Session Store + SQLite Memory`

主要模块：

- `agent_app/main.py`
  CLI 入口和组件装配。
- `agent_app/api/server.py`
  FastAPI 服务入口。
- `agent_app/core/`
  Agent 主循环、消息结构、会话状态、上下文裁剪。
- `agent_app/llm/`
  LLM 抽象、Mock 实现、OpenAI-compatible 实现。
- `agent_app/tools/`
  文件工具、目录检索工具、文档读取工具，且每个工具都带结构化输入说明。
- `agent_app/skills/`
  markdown skill 解析、注册和运行时注入。
- `agent_app/memory/`
  JSON 会话存储和 SQLite 长期记忆。

## 当前能力

- 单 Agent 主循环
- 多模型配置
  支持 `mock`、`openai`、`gemini`、`glm` / `glm-4.7`
- 文件工具
  `read_file`、`write_file`、`rename_file`、`move_file`、`rm_file`
- 工作区检索工具
  `list_dir`、`search_in_files`、`stat_file`
- 文档工具
  `read_pdf`、`read_xlsx`、`read_word`
- 工具元数据
  暴露 `input_schema` 和 `example_input`，便于模型正确构造参数
- 技能系统
  从 `skills/*.md` 加载 skill，并让 `allowed_tools` 真正约束可调用工具
- 记忆系统
  短期会话历史保存在 JSON 中，长期记忆保存在 SQLite 中，并在运行时做简单检索注入
- 上下文保护
  过长工具结果会自动截断，避免拖垮上下文窗口
- FastAPI 服务
  提供 `/health`、`/config`、`/tools`、`/skills`、`/sessions`、`/memories/search`、`/chat`

## 本次新增

- 工具结构化元数据
  每个工具现在都提供 `input_schema` 和 `example_input`
- 会话管理
  支持列出 session、读取 session、删除 session
- 记忆管理
  支持按关键词搜索长期记忆，并清理指定 session 的 SQLite 记忆
- 上下文保护
  过长工具输出会自动裁剪，避免直接撑爆上下文窗口
- 服务配置查看
  新增 `/config`，可查看当前服务装配后的关键运行配置

## 快速开始

```bash
python -m agent_app.main "现在几点"
python -m agent_app.main "2 * (3 + 4)"
python -m agent_app.main --list-skills
python -m agent_app.main --skills file_analyst "当前有哪些技能"
```

查看模型配置：

```bash
python -m agent_app.main --show-model-config --provider openai --api-key test-key
```

启动服务：

```bash
uvicorn agent_app.api.server:app --reload
```

## 常用接口

- `GET /health`
- `GET /config`
- `GET /tools`
- `GET /skills`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `GET /memories/search?q=...`
- `DELETE /memories/session/{session_id}`
- `POST /chat`

## 环境变量

```bash
set AGENT_MODEL_PROVIDER=openai
set OPENAI_API_KEY=your_key
set AGENT_MEMORY_DB_PATH=.agent_state/memory/memory.db
set AGENT_MAX_TOOL_RESULT_CHARS=4000
set AGENT_MAX_MEMORY_CONTEXT_HITS=3
```

## Skill 示例

```md
---
name: file_analyst
description: Help the agent inspect workspace files and summarize local content.
tools: list_dir, stat_file, search_in_files, read_file, read_pdf, read_xlsx, read_word
---
Use directory and document-reading tools before answering questions about local files.
```
