# 简易 Python Agent 架构与当前实现

## 当前主链路

`CLI / FastAPI -> Agent Loop -> Skill Context -> LLM Backend -> Tool Registry -> Session Store + SQLite Memory`

## 已实现能力

- 单 Agent 主循环
- Mock 与 OpenAI-compatible 模型适配
- 文件工具：`read_file`、`write_file`、`rename_file`、`move_file`、`rm_file`
- 工作区工具：`list_dir`、`search_in_files`、`stat_file`
- 文档工具：`read_pdf`、`read_xlsx`、`read_word`
- 工具结构化元数据：`input_schema`、`example_input`
- 技能加载、front matter 解析、`allowed_tools` 约束
- JSON 会话存储
- SQLite 长期记忆和简单检索注入
- 过长工具结果裁剪
- FastAPI 服务层

## 本次新增功能

- 工具结构化元数据
  所有工具补充了 `input_schema` 和 `example_input`
- Session 管理
  支持列出 session、读取 session、删除 session
- Memory 管理
  支持搜索长期记忆，以及按 session 清理 SQLite 记忆
- 上下文保护
  过长工具结果会自动截断后再注入上下文
- 运行配置查看
  FastAPI 新增 `/config` 用于查看当前关键配置

## 服务接口

- `GET /health`
- `GET /config`
- `GET /tools`
- `GET /skills`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `GET /memories/search`
- `DELETE /memories/session/{session_id}`
- `POST /chat`

## 下一步方向

1. 给 `allowed_tools` 再加更细的参数级约束
2. 把 SQLite 记忆升级为 embedding 检索
3. 增加 `list_dir` 的分页与排序
4. 给服务层补 streaming 输出
