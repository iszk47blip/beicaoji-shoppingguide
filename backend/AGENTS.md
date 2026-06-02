# 焙草集 AI 销售助手（后端）

药食同源门店 AI 推荐系统，微信小程序 + FastAPI 后端。

## 项目结构

```
backend/
├── app/
│   ├── api/           # /api/chat/send, /api/chat/orders
│   ├── models/        # Product, Customer, Conversation, Order
│   ├── services/      # dialogue_engine, recommend_engine, constitution_analyzer
│   └── main.py        # FastAPI app entry
└── tests/
```

## 技术栈

- Python 3.11+, FastAPI, SQLAlchemy, SQLite
- H5 移动端（test-chat.html）
- 有赞承载订单/支付（后续接入）

## 开发原则

### 1. 编码前思考
- 不确定就问，不要假设
- 困惑时停下来要求澄清

### 2. 简洁优先
- 用最少的代码解决问题
- 100行能搞定的事不要写成1000行

### 3. 精准修改
- 每行修改直接追溯到用户请求
- 不"改进"相邻无关的代码

### 4. 目标驱动
- 定义成功标准再执行
- 通过测试验证，不是"让它工作"

## 已知坑

- `process_user_message` 必须覆盖所有 stage，遇到未知 stage 会静默 fallback
- 阶段推进后立即 commit 到 git，multi-process reload 会读取旧 bytecode

## MCP

- `context7` — FastAPI/SQLAlchemy 文档查询（已配置）
