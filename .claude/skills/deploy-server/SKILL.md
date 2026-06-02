---
name: deploy-server
description: 上传修改到焙草集服务器并重启 uvicorn
disable-model-invocation: true
---

# Deploy Server

将本地修改同步到服务器并重启 uvicorn。

## 前置条件

- 本地修改已 commit
- 服务器 SSH 访问可用
- 知道服务器 PID（或用 `ps aux | grep uvicorn` 查找）

## 部署步骤

### 1. 上传文件

```bash
# 上传 chat.py
scp E:/VIBE/beicaoji/backend/app/api/chat.py user@server:/www/beicaoji/backend/app/api/chat.py

# 上传 test-chat.html
scp E:/VIBE/beicaoji/test-chat.html user@server:/www/beicaoji/test-chat.html
```

### 2. 重启 uvicorn（必须用 kill -9）

```bash
ssh user@server
ps aux | grep uvicorn | grep -v grep
kill -9 <pid>          # 必须 -9，普通 kill 杀不掉
nohup uvicorn app.main:app --host 0.0.0.0 --port 8002 &
```

### 3. 验证

```bash
# 检查服务健康
curl http://127.0.0.1:8002/api/chat/health

# 检查新订单 created_at 时区（创建一笔测试订单后）
curl -s http://127.0.0.1:8002/api/chat/orders | python -c "
import sys, json
orders = json.load(sys.stdin)
for o in orders[-3:]:
    print(o['order_no'], o['created_at'], o.get('conversation_snapshot', '')[:80])
"
```

## 常见问题

- **kill 不掉？** 用 `kill -9 <pid>` 而不是 `kill <pid>`
- **端口被占用？** `lsof -i :8002` 或 `netstat -ano | findstr 8002`
- **上传后没生效？** 多进程 reload 有缓存，必须 `kill -9` 强制重启
