---
name: test-order-flow
description: 端到端测试焙草集 H5 聊天下单流程
---

# Test Order Flow

测试 H5 聊天下单的完整流程，验证两个 bug 修复是否生效。

## 测试目标

1. **Bug 1 修复验证**：快捷回复按钮点击后，`conversation_snapshot` 包含用户消息
2. **Bug 2 修复验证**：新订单 `created_at` 为北京时间（不是 UTC+0 差8小时）

## 手动测试步骤

### Step 1: 启动本地服务器（如未运行）

```bash
cd E:/VIBE/beicaoji/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### Step 2: 打开 H5 页面

浏览器打开 `http://localhost:8002/test-chat.html`

### Step 3: 走完体质识别流程

1. 输入任意身体症状（如"累"、"上火"、"睡不好"）
2. 回答体质问题
3. 收到推荐后点击**快捷回复按钮**（不是手动输入）
4. 进入结算页提交订单

### Step 4: 验证 conversation_snapshot

打开浏览器 DevTools → Network，找到 `POST /api/chat/orders` 请求，查看 `conversation_snapshot` 数组：
- 必须包含 `{"role":"user", "content": "xxx", ...}` 条目
- 如果是空数组或只有 assistant 条目，说明 Bug 1 未修复

### Step 5: 验证 created_at 时区

```bash
# 直连服务器数据库
ssh user@server "sqlite3 /www/beicaoji/beicaoji.db 'SELECT order_no, created_at FROM orders ORDER BY rowid DESC LIMIT 3;'"

# 期望：created_at 显示 15:44 这样的北京时间
# 如果显示 07:44 说明仍是 UTC 时间（Brug 2 未修复）
```

## 自动验证脚本

```python
# 验证 created_at 时区（服务器上执行）
import sqlite3, datetime
conn = sqlite3.connect('/www/beicaoji/beicaoji.db')
cur = conn.cursor()
cur.execute("SELECT order_no, created_at FROM orders ORDER BY rowid DESC LIMIT 3")
for row in cur.fetchall():
    print(row)
    # 期望：2026-06-02 15:44:xx 这样的北京时间
conn.close()
```

## 通过标准

- [ ] `conversation_snapshot` 包含用户消息（快捷回复触发）
- [ ] 新订单 `created_at` 与当前北京时间误差在1分钟内
- [ ] 订单状态为 `pending`
- [ ] `recommendation_snapshot` 非空
