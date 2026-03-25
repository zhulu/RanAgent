# Minimal Python Agent Skeleton

一个方便继续手改的单 Agent 骨架，默认支持本地离线调试，并内置文件工具、文档读取工具和轻量技能系统。

## 当前架构

主链路如下：

`CLI -> Agent Loop -> Skill Context -> LLM Backend -> Tool Registry -> Session Store`

目录职责：

- `agent_app/main.py`
  CLI 入口、参数解析、组件装配。
- `agent_app/config.py`
  运行配置与模型 provider 预设。
- `agent_app/core/`
  Agent 主循环、消息结构、会话状态。
- `agent_app/llm/`
  LLM 抽象、Mock 实现、OpenAI-compatible 实现。
- `agent_app/tools/`
  通用工具抽象、文件工具、文档读取工具。
- `agent_app/skills/`
  技能文件解析、技能注册、运行时注入。
- `agent_app/memory/`
  会话历史持久化。

## 当前能力

- 单 Agent 主循环
  支持用户输入、工具调用、工具结果回注和最终回复生成。
- 多模型配置
  支持 `mock`、`openai`、`gemini`、`glm` / `glm-4.7`。
- 文件工具
  `read_file`、`write_file`、`rename_file`、`move_file`、`rm_file`。
- 文档工具
  `read_pdf`、`read_xlsx`、`read_word`。
  其中 `read_word` 当前支持 `.docx`，不支持旧版 `.doc`。
- 技能系统
  支持从 `skills/*.md` 加载 skill，解析 front matter 和正文，并在运行时注入系统上下文。
- 会话存储
  当前使用本地 JSON 持久化会话历史。
- CLI 能力
  支持直接运行对话、查看模型配置、列出技能、按名称加载技能。

## 快速开始

```bash
python -m agent_app.main "现在几点"
python -m agent_app.main "2 * (3 + 4)"
python -m agent_app.main --list-skills
python -m agent_app.main --skills file_analyst "当前有哪些技能"
```

查看模型配置解析结果：

```bash
python -m agent_app.main --show-model-config --provider openai --api-key test-key
python -m agent_app.main --show-model-config --provider gemini --api-key test-key
python -m agent_app.main --show-model-config --provider glm-4.7 --api-key test-key
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 环境变量

```bash
set AGENT_MODEL_PROVIDER=openai
set OPENAI_API_KEY=your_key

set AGENT_MODEL_PROVIDER=gemini
set GEMINI_API_KEY=your_key

set AGENT_MODEL_PROVIDER=glm
set GLM_API_KEY=your_key
```

## Skill 格式

技能文件默认放在 `skills/` 目录，格式示例：

```md
---
name: file_analyst
description: Help the agent inspect workspace documents.
tools: read_file, read_pdf, read_xlsx, read_word
---
Use document-reading tools before answering questions about local files.
```

## 当前验证状态

已覆盖：

- 文件工具读写、重命名、移动、删除
- PDF、XLSX、DOCX 内容提取
- 模型配置解析
- 技能加载、技能注入
- Agent 主流程基础行为
