# 焙草集 AI 销售助手

药食同源门店 AI 推荐系统，微信小程序 + FastAPI 后端。

## 项目结构

```
beicaoji/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── models/      # Product, Customer, Conversation
│   │   ├── services/    # dialogue_engine, recommend_engine, constitution_analyzer
│   │   └── api/         # /api/chat/send
│   └── tests/
├── docs/                # 设计文档和实施计划
└── beicaoji-产品目录/    # Excel 商品数据
```

## 技术栈

- Python 3.11+, FastAPI, SQLAlchemy, Redis
- 微信小程序原生框架
- 有赞承载订单/支付（后续接入）

## 开发原则（来自 Karpathy 指南）

### 1. 编码前思考

**不要假设。不要隐藏困惑。呈现权衡。**

- 明确说明假设 — 不确定就询问而不是猜测
- 困惑时停下来 — 指出不清楚的地方并要求澄清

### 2. 简洁优先

**用最少的代码解决问题。不要过度推测。**

- 不添加要求之外的功能
- 不为不可能发生的场景做错误处理
- 100行能搞定的事，不要写成1000行

### 3. 精准修改

**只碰必须碰的。只清理自己造成的混乱。**

- 每一行修改都直接追溯到用户请求
- 不"改进"相邻无关的代码

### 4. 目标驱动执行

**定义成功标准。循环验证直到达成。**

- 多步骤任务先说明计划，再执行
- 通过测试验证，不是"让它工作"

### 已知坑

- `process_user_message` 必须覆盖所有 stage，遇到未知 stage 会静默 fallback 到默认回复
- 阶段推进后立即 commit 到 git，multi-process reload 会读取旧 bytecode
