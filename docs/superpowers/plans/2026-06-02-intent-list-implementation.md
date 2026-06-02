# 意向清单功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把"假支付"改成"保存意向清单"，顾客点一下直接存订单到数据库，状态=pending，提示到店再支付。同时修复订单详情页三个 snapshot 字段为空的问题。

**Architecture:** 前端 test-chat.html 改 checkout 流程（改文案 + 改确认框）；后端 chat.py 的 /orders 接口接收前端传来的 snapshot 数据（不依赖 _session_store），解决多进程/重启后内存丢失的问题。

**Tech Stack:** FastAPI, HTML/JS (test-chat.html), SQLAlchemy

---

## 文件改动概览

| 文件 | 改动 |
|------|------|
| `test-chat.html`（仓库根目录） | 改按钮文案、去支付文字、确认框提示语、成功提示；新增 conversationHistory/constitutionType/constitutionRaw/recommendation 全局变量 |
| `backend/app/api/chat.py` | OrderRequest 新增 4 个可选字段（snapshot 数据），create_order 优先用请求体数据 |

---

## Task 1: 改购物车面板按钮文案

**Files:**
- Modify: `backend/test-chat.html:683`

- [ ] **Step 1: 找到按钮文案位置**

行 683: `<button class="btn-checkout" onclick="checkout()" id="btn-checkout-text">去结算</button>`

- [ ] **Step 2: 改按钮文案**

把 `去结算` 改成 `保存意向清单`

- [ ] **Step 3: 改 updateCartBar 中动态更新按钮的逻辑**

行 1133-1136:
```javascript
  var checkoutBtn = document.getElementById('btn-checkout-text');
  if (checkoutBtn) {
    checkoutBtn.textContent = count > 0 ? '去结算 ¥' + total.toFixed(2).replace(/\.?0+$/, '') : '去结算';
```

改成:
```javascript
  var checkoutBtn = document.getElementById('btn-checkout-text');
  if (checkoutBtn) {
    checkoutBtn.textContent = count > 0 ? '保存意向清单 ¥' + total.toFixed(2).replace(/\.?0+$/, '') : '保存意向清单';
```

---

## Task 2: 改订单确认框中的提示语

**Files:**
- Modify: `backend/test-chat.html:1318-1337`

- [ ] **Step 1: 找到订单确认框的 HTML 生成位置**

`checkout()` 函数（行 1300-1341）生成订单确认框。

- [ ] **Step 2: 改提示语段落**

行 1329-1332 当前是:
```javascript
'<div class="order-section" style="font-size:13px;color:#999">' +
'<p>📍 取货方式：到店自取</p>' +
'<p>🏪 门店地址：焙草集门店</p>' +
'<p style="margin-top:4px;font-size:11px;color:#bbb">此为模拟订单，实际支付将对接有赞</p>' +
'</div>' +
```

改成:
```javascript
'<div class="order-section" style="font-size:13px;color:#999">' +
'<p>📍 取货方式：到店自取</p>' +
'<p>🏪 门店地址：焙草集门店</p>' +
'<p style="margin-top:6px;color:#5B8C5A;font-weight:500">✓ 已选好商品，无需立即支付</p>' +
'<p style="margin-top:4px;font-size:12px;color:#999">到店后报订单号取货，商品准备好后支付即可</p>' +
'</div>' +
```

- [ ] **Step 3: 改按钮文案**

行 1334-1336 当前是:
```javascript
'<button class="btn-order-close" onclick="closeOrder()">继续选购</button>' +
'<button class="btn-order-confirm" onclick="confirmOrder(\'' + orderNo + '\')">确认下单</button>' +
```

改成:
```javascript
'<button class="btn-order-close" onclick="closeOrder()">继续选购</button>' +
'<button class="btn-order-confirm" onclick="confirmOrder(\'' + orderNo + '\')">确认保存</button>' +
```

---

## Task 3: 改下单成功后的聊天区提示

**Files:**
- Modify: `backend/test-chat.html:1369-1378`

- [ ] **Step 1: 找到 confirmOrder 成功后的提示位置**

`confirmOrder` 函数中，行 1369-1378 生成聊天区成功消息。

- [ ] **Step 2: 改成功提示**

当前是:
```javascript
  const div = document.createElement('div');
  div.className = 'msg system';
  div.innerHTML = '✅ 下单成功！<br>订单号: ' + escapeHtml(orderNo) + '<br><span style="font-size:11px;color:#999">请到店出示订单号取货</span>';
  chat.appendChild(div);
```

改成:
```javascript
  const div = document.createElement('div');
  div.className = 'msg system';
  div.innerHTML = '✅ 清单已保存！<br>订单号: ' + escapeHtml(orderNo) + '<br><span style="font-size:12px;color:#5B8C5A">到店后出示此订单号，店员会为您准备商品<br>本次无需支付，商品准备好后到店支付即可</span>';
  chat.appendChild(div);
```

- [ ] **Step 3: 改 Toast 提示**

行 1377 当前是:
```javascript
  showToast('下单成功 ✓');
```

改成:
```javascript
  showToast('清单已保存 ✓');
```

---

## Task 4: 验证并测试

**Files:**
- Test: `http://localhost:8000/`

- [ ] **Step 1: 启动服务器（如果未运行）**

```bash
cd E:/VIBE/beicaoji/backend/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 2: 打开浏览器测试**

访问 `http://localhost:8000/`，测试流程：
1. 和 AI 对话选购商品，添加到购物车
2. 点击购物车栏，打开购物车面板
3. 验证按钮文案是"保存意向清单"
4. 点击"保存意向清单"，看确认框提示语是否正确
5. 点击"确认保存"，看成功提示是否正确
6. 去 orders.html 看订单是否以 pending 状态存入

- [ ] **Step 3: 提交代码**

```bash
git add backend/test-chat.html
git commit -m "feat: convert fake payment to intent list — save order directly without payment"
```
