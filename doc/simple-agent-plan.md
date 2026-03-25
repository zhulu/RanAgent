# 简易 Python Agent 框架规划与当前实现

## 目标

这套框架的目标是提供一个可控、可扩展、便于继续手改的单 Agent 基础工程。设计原则如下：

- 先做单 Agent，不急着上多 Agent
- 先跑通工具调用、技能加载、会话状态和模型配置
- 保持 LLM、工具、技能、存储之间解耦
- 默认支持本地无密钥调试，避免一开始就被外部模型服务阻塞

## 当前总体架构

当前主链路：

`CLI -> Agent Loop -> Skill Context -> LLM Backend -> Tool Registry -> Session Store`

这条链路的运行过程是：

1. CLI 接收用户输入和运行参数
2. Agent 读取会话历史
3. 按需加载 skill，并把 skill 内容注入为系统上下文
4. LLM 决策是直接回复还是调用工具
5. 如果调用工具，执行后把结果写回消息历史
6. 生成最终回复并持久化本轮会话

## 目录设计

```text
agent_app/
  main.py
  config.py

  core/
    agent.py
    messages.py
    state.py

  llm/
    base.py
    factory.py
    mock.py
    openai_compatible.py

  tools/
    base.py
    registry.py
    calculator.py
    time_tool.py
    filesystem.py
    document_readers.py

  skills/
    base.py
    loader.py
    registry.py

  memory/
    session_store.py

  observability/
    logger.py

skills/
  file_analyst.md

tests/
```

## 模块职责

- `agent_app/main.py`
  负责 CLI 参数解析、构建模型、工具注册表、技能注册表和 Agent 实例。
- `agent_app/config.py`
  负责统一管理环境变量、provider 预设和模型配置解析。
- `agent_app/core/agent.py`
  负责主循环，连接会话、技能上下文、LLM 决策和工具执行。
- `agent_app/llm/`
  负责模型适配，当前有本地 `MockLLM` 和 `OpenAICompatibleLLM`。
- `agent_app/tools/`
  负责文件、文档和基础工具能力。
- `agent_app/skills/`
  负责解析 markdown skill 文件，并在运行时将其转成系统消息。
- `agent_app/memory/session_store.py`
  负责本地 JSON 会话持久化。

## 已实现功能

### Agent 主循环

- 接收用户输入
- 读取会话历史
- 注入选中的 skill
- 调用 LLM 决策
- 执行工具
- 保存回复和工具结果

### 模型配置

支持以下 provider：

- `mock`
- `openai`
- `gemini`
- `glm` / `glm-4.7`

当前做法是统一映射为配置对象，再由工厂构建具体 LLM 后端。

### 文件工具

当前已有：

- `read_file`
- `write_file`
- `rename_file`
- `move_file`
- `rm_file`

这些工具只允许操作工作目录内的文件，避免越界访问。

### 文档工具

当前已有：

- `read_pdf`
- `read_xlsx`
- `read_word`

说明：

- `read_pdf` 用于提取 PDF 文本
- `read_xlsx` 用于读取 Excel sheet 内容
- `read_word` 当前仅支持 `.docx`

### 技能系统

当前 skill 采用 markdown 文件定义，支持解析：

- `name`
- `description`
- `tools`
- 正文 prompt

skill 会在运行时被注入成系统上下文，用于给模型补稳定任务说明和能力边界。

### 会话存储

- 当前使用本地 JSON 文件存储会话历史
- 支持按 `session_id` 分会话持久化

## 当前示例技能

当前仓库已提供：

- `skills/file_analyst.md`

用途：

- 告诉 agent 在处理本地文件问题时优先调用文档和文件读取工具

## 当前验证结果

目前已经验证通过的内容：

- 文件工具读写、重命名、移动、删除
- PDF 内容提取
- XLSX 内容提取
- DOCX 内容提取
- 模型配置解析
- 技能加载和技能注入
- Agent 主流程基础行为

## 下一步建议

这套架构现在已经适合作为继续扩展的底座。下一步最合理的几个方向是：

1. 增加 `list_dir`、`search_in_files`、`stat_file`
2. 让 `skill.allowed_tools` 真正参与工具调用约束
3. 接 FastAPI，把 CLI 变成服务
4. 引入 SQLite 级别的长期记忆或简单 RAG
