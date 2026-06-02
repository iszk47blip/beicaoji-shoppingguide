# 焙草集 AI 销售助手（后端）

## 快速导航

- **API 路由**: `app/api/chat.py` — `/api/chat/send`, `/api/chat/orders`
- **核心服务**: `app/services/dialogue_engine.py`, `app/services/recommend_engine.py`
- **测试**: `tests/test_constitution_bundle.py`
- **数据库**: `beicaoji.db` (SQLite)

## 已知坑

- `process_user_message` 必须覆盖所有 stage，遇到未知 stage 会静默 fallback 到默认回复
- 阶段推进后立即 commit 到 git，multi-process reload 会读取旧 bytecode

## 快捷 skill

- `/deploy-server` — 上传修改到服务器并重启 uvicorn
- `/test-order-flow` — H5 聊天下单流程测试
