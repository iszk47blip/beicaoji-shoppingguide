# QA 测试用例 — 焙草集 AI 销售助手

**日期:** 2026-05-23
**URL:** http://localhost:8002
**框架:** FastAPI + Vanilla JS SPA
**现状:** 后端 28 个 API 端点，221 件商品已导入，数据库新建但无对话/订单数据

---

## 测试环境

| 项目 | 值 |
|------|-----|
| 服务器 | http://localhost:8002 |
| 数据库 | SQLite - `E:\VIBE\beicaoji\beicaoji.db` |
| LLM | MiniMax M2.7（需有效 API key） |
| 后台 | http://localhost:8002/staff-admin |
| API 文档 | http://localhost:8002/docs |

---

## 已知问题（测试前必读）

1. **LLM API key 过期/无效** → chat API 全部 500。需在 `backend/.env` 配置有效的 `llm_api_key`
2. **商品名乱码** → 有赞导出的 Excel 编码有问题，部分商品名/分类名不可读
3. **所有数据表为空**（除 products）→ 需先生成 mock 数据或跑真实对话

---

## Phase 1: 准备测试数据

### 1.1 生成 Mock 数据
```bash
cd E:/VIBE/beicaoji
python -m app.mock_data --days 30 --seed 42
```
验证：
- `GET /api/staff/customers` → 应有 ~100 条顾客
- `GET /api/staff/orders?page=1` → 应有 ~90 条订单
- `GET /api/staff/conversations?page=1` → 应有 ~210 条对话

### 1.2 配置主推产品
```bash
curl -X PUT http://localhost:8002/api/staff/hot-products \
  -H "Content-Type: application/json" \
  -d '{"products":[{"sku_id":"B001","sort_order":1},{"sku_id":"T001","sort_order":2}]}'
```
验证：`GET /api/staff/hot-products` → 返回 2 个主推产品

### 1.3 配置体质套餐
```bash
curl -X PUT http://localhost:8002/api/staff/constitution-bundles/气虚质 \
  -H "Content-Type: application/json" \
  -d '{"products":[{"sku_id":"B001","sort_order":1},{"sku_id":"T001","sort_order":2}]}'
```
验证：`GET /api/staff/constitution-bundles` → 气虚质 有 2 个产品

---

## Phase 2: API 端点测试

### 2.1 商品管理

| # | 用例 | 方法 | 路径 | 预期 |
|---|------|------|------|------|
| 1 | 商品列表 | GET | `/api/staff/products?page=1&page_size=20` | 200, total>0 |
| 2 | 商品搜索 | GET | `/api/staff/products?q=茶` | 200, 返回含"茶"的商品 |
| 3 | 分类筛选 | GET | `/api/staff/products?category=tea` | 200, 只返回茶类 |
| 4 | 零库存筛选 | GET | `/api/staff/products?stock_zero=true` | 200, stock=0 的商品 |
| 5 | 按 SKU 查询 | GET | `/api/staff/products/by-skus?skus=B001,T001` | 200, 返回指定 SKU 的商品 |
| 6 | 更新商品 | PATCH | `/api/staff/products/B001` body: `{"price":99}` | 200, price 更新为 99 |
| 7 | 更新不存在的商品 | PATCH | `/api/staff/products/NOEXIST` | 404 |
| 8 | 分类列表 | GET | `/api/staff/categories` | 200, 返回分类+计数 |
| 9 | 批量库存（相对） | PATCH | `/api/staff/products/batch-stock-relative` body: `[{"sku_id":"B001","delta":5}]` | 200, stock += 5 |
| 10 | 批量库存（绝对） | PATCH | `/api/staff/products/batch-stock-relative` body: `[{"sku_id":"B001","stock":10}]` | 200, stock = 10 |
| 11 | Excel 导入预览 | POST | `/api/staff/products/preview` (multipart file) | 200, 返回 mapping+samples+warnings |
| 12 | Excel 导入 | POST | `/api/staff/products/import` (multipart file) | 200, 返回 imported/updated 计数 |

### 2.2 对话 API（需有效 LLM key）

| # | 用例 | 方法 | 路径 | Body | 预期 |
|---|------|------|------|------|------|
| 13 | 首次对话 | POST | `/api/chat/send` | `{"session_id":"t1","message":"你好"}` | 200, stage=greeting/screening, 有 message |
| 14 | 带渠道的对话 | POST | `/api/chat/send` | `{"session_id":"t2","message":"帮我看看体质","channel":"wechat-dongmen"}` | 200, 对话记录 channel="wechat-dongmen" |
| 15 | 多轮对话 | POST | `/api/chat/send` | `{"session_id":"t1","message":"都没有"}` (在第13步之后) | 200, stage 推进 |
| 16 | 空消息（初始化） | POST | `/api/chat/send` | `{"session_id":"t3","message":""}` | 200, 返回欢迎消息 |
| 17 | 重置会话 | POST | `/api/chat/reset` | `{"session_id":"t1"}` | 200, `{"status":"ok"}` |

### 2.3 对话管理

| # | 用例 | 方法 | 路径 | 预期 |
|---|------|------|------|------|
| 18 | 对话列表 | GET | `/api/staff/conversations?page=1&page_size=20` | 200, 应显示上面创建的对话 |
| 19 | 对话详情（messages_history） | GET | `/api/staff/conversations?page=1&page_size=20` | 返回的每项应有 messages_history 数组 |
| 20 | 渠道筛选 | GET | `/api/staff/conversations?channel=wechat-dongmen` | 200, 只返回该渠道的对话 |
| 21 | 标记筛选 | GET | `/api/staff/conversations?flagged_only=true` | 200, 只返回已标记的对话 |
| 22 | 标记对话 | PATCH | `/api/staff/conversations/{id}/flag` | 200, is_flagged 切换 |
| 23 | 添加备注 | PATCH | `/api/staff/conversations/{id}/notes` body: `{"staff_notes":"测试备注","staff_tags":"问题,待跟进"}` | 200, 返回更新后的值 |
| 24 | 渠道统计 | GET | `/api/staff/channels` | 200, 返回各渠道对话计数 |

### 2.4 LLM 审核

| # | 用例 | 方法 | 路径 | 预期 |
|---|------|------|------|------|
| 25 | 运行审核 | POST | `/api/staff/reviews/run?days=1` | 200, 返回 reviewed/problems_found/suggestions |
| 26 | 审核列表 | GET | `/api/staff/reviews?page=1` | 200, 返回审核记录含 quality_score |

### 2.5 报表

| # | 用例 | 方法 | 路径 | 预期 |
|---|------|------|------|------|
| 27 | 概览 | GET | `/api/staff/reports/overview?start=2026-05-01&end=2026-05-23` | 200, 返回 revenue/orders/avg/conversion |
| 28 | 收入趋势 | GET | `/api/staff/reports/revenue-trend?start=2026-05-01&end=2026-05-23&granularity=day` | 200, 返回每日收入数组 |
| 29 | 商品排行 | GET | `/api/staff/reports/product-ranking?start=2026-05-01&end=2026-05-23&limit=10` | 200, 返回 TOP10 |
| 30 | 转化漏斗 | GET | `/api/staff/reports/conversion-funnel?start=2026-05-01&end=2026-05-23` | 200, 返回各阶段数据 |
| 31 | 分类占比 | GET | `/api/staff/reports/category-distribution?start=2026-05-01&end=2026-05-23` | 200, 返回各分类营收占比 |
| 32 | 体质分布 | GET | `/api/staff/reports/constitution-distribution?start=2026-05-01&end=2026-05-23` | 200, 返回各体质人数 |

### 2.6 顾客 & 订单

| # | 用例 | 方法 | 路径 | 预期 |
|---|------|------|------|------|
| 33 | 顾客列表 | GET | `/api/staff/customers?page=1&page_size=20` | 200 |
| 34 | 顾客详情 | GET | `/api/staff/customers/{id}` | 200, 含对话列表 |
| 35 | 创建订单 | POST | `/api/staff/orders` body: `{"order_no":"TEST001","total_amount":99}` | 200 |
| 36 | 重复订单号 | POST | `/api/staff/orders` body: `{"order_no":"TEST001",...}` | 409 |
| 37 | 订单列表 | GET | `/api/staff/orders?page=1&page_size=20` | 200 |
| 38 | 订单状态筛选 | GET | `/api/staff/orders?status=paid` | 200, 只返回 paid |
| 39 | 订单详情 | GET | `/api/staff/orders/{id}` | 200 |
| 40 | 更新订单状态 | PATCH | `/api/staff/orders/{id}/status?status=paid` | 200 |
| 41 | 无效状态 | PATCH | `/api/staff/orders/{id}/status?status=invalid` | 400 |

---

## Phase 3: 前端 UI 测试

### 3.1 商品管理页

| # | 操作 | 预期 |
|---|------|------|
| 42 | 打开 http://localhost:8002/staff-admin | 默认显示商品管理页 |
| 43 | 点击分类 pill | 筛选对应分类商品 |
| 44 | 搜索框输入"茶" | 返回含"茶"的商品 |
| 45 | 勾选"无库存" | 只显示 stock=0 的商品 |
| 46 | 点击某个商品行 | 选中高亮 |
| 47 | 点击"批量修改库存" | 弹出 modal |
| 48 | 修改库存并保存 | stock 更新，表格刷新 |
| 49 | 点击右上角上传按钮 | 弹出文件选择 |
| 50 | 选择 Excel 文件 | 显示预览（mapping + samples + warnings）|

### 3.2 订单管理页

| # | 操作 | 预期 |
|---|------|------|
| 51 | 点击左侧"订单"导航 | 切换到订单列表 |
| 52 | 点击订单行 | 展开订单详情 |

### 3.3 主推管理页

| # | 操作 | 预期 |
|---|------|------|
| 53 | 点击左侧"主推"导航 | 显示当前主推产品列表 |
| 54 | 搜索商品并添加到主推 | 列表更新 |
| 55 | 拖拽排序 | 顺序更新 |
| 56 | 保存 | PUT 生效 |

### 3.4 体质套餐页

| # | 操作 | 预期 |
|---|------|------|
| 57 | 点击左侧"体质套餐"导航 | 显示体质 tab 切换 |
| 58 | 切换到不同体质 | 显示对应套餐产品 |
| 59 | 添加/移除产品 | 套餐更新 |
| 60 | 保存 | PUT 生效 |

### 3.5 对话审核页（新增功能）

| # | 操作 | 预期 |
|---|------|------|
| 61 | 点击左侧"对话"导航 | 切换到对话审核页 |
| 62 | 列表显示对话记录 | 表格显示 ID/时间/渠道/阶段/预览/标记 |
| 63 | 点击"已标记"筛选 | 只显示 is_flagged=true 的对话 |
| 64 | 点击"详情" | 弹出 modal 显示完整对话历史 |
| 65 | 在 modal 中输入备注和标签 | 输入框可编辑 |
| 66 | 点击"保存" | 备注保存成功，toast 提示 |
| 67 | 点击"标记"按钮 | 对话标记状态切换 |
| 68 | 点击"运行审核" | 触发 LLM 审核，返回结果 |
| 69 | 翻页 | 分页正常工作 |

### 3.6 报表页

| # | 操作 | 预期 |
|---|------|------|
| 70 | 点击左侧"报表"导航 | 显示 KPI 卡片 + 图表 |
| 71 | 切换时间范围（7天/30天/90天）| 数据更新 |
| 72 | 6 个图表全部渲染 | 无空白/报错 |
| 73 | 调整窗口大小 | 图表自适应 resize |

---

## Phase 4: 边界情况

| # | 用例 | 预期 |
|---|------|------|
| 74 | 空数据库时打开后台 | 显示空状态提示，不报错 |
| 75 | 对话列表为空 | 显示"暂无对话记录" |
| 76 | API 返回 500 | 页面显示错误提示，不崩溃 |
| 77 | 并发对话（同一 session_id 快速连续请求）| 不丢失数据，不覆盖 |
| 78 | 超长消息（>1000 字符） | 正确截断存储 |
| 79 | 特殊字符消息 | 正确存储，XSS 防护 |

---

## 测试执行记录模板

| # | 状态 | 备注 |
|---|------|------|
| 1 | ⬜ | |
| 2 | ⬜ | |
| ... | | |

状态标记：✅ PASS / ❌ FAIL / ⚠️ WARNING / ⬜ NOT TESTED / 🔲 BLOCKED

---

## 已知 Bug（来自代码审查）

1. **chat.py:295** — `scene_input` 字段赋值使用了 `scene_raw`，但 Conversation 模型字段名是 `scene_input`，不影响功能但命名不一致
2. **staff.py:408** — channels API 的 `order_count` 硬编码为 0，缺少 order-to-conversation 关联
3. **staff-admin.html** — 对话列表 API 被调用了两次（`openConvDetail` 里重复 fetch），应重构为直接传入数据
