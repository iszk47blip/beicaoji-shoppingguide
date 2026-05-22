# 数据导入管道重构 — 设计文档

**日期**: 2026-05-22
**状态**: 已批准，待实现

---

## 背景

Staff 从有赞后台下载商品 Excel，通过后台界面上传导入。当前 pipeline 存在两个问题：

1. **列映射硬编码** — `data_importer.py` 用固定 position 映射，有赞 Excel 列顺序变化时静默损坏数据
2. **重复导入策略缺失** — 再次导入时覆盖 AI 生成的标签，或不更新已变动的价格/名称

---

## 导入流程

```
Staff 下载 Youzan Excel
        ↓
  后台上传（/api/staff/products/import）
        ↓
  动态列映射引擎
  （读表头 → 字段名匹配）
        ↓
  预览确认页面
  （映射 + 样例 + 警告）
        ↓
  Staff 确认
        ↓
  Merge 写入
  (主数据用导入值 / Tag 保留或 AI 补全)
```

---

## 字段分类 & Merge 规则

| 字段 | 来源 | Merge 规则 |
|------|------|-----------|
| `sku_id` | Excel | 唯一标识，以导入为准 |
| `name` | Excel | 以导入为准 |
| `price` | Excel | 以导入为准 |
| `category` | Excel | 以导入为准 |
| `ingredients` | Excel | 以导入为准 |
| `is_active` | Excel | 以导入为准 |
| `feature_tag` | AI 推理 | 已有则保留；空则触发 AI 补全 |
| `scene_tags` | AI 推理 | 已有则保留；空则触发 AI 补全 |
| `sales_script` | AI 推理 | 已有则保留；空则触发 AI 补全 |
| `contraindication_tags` | AI 推理 | 已有则保留；空则触发 AI 补全 |

**为什么这样分**：结构化主数据（name/price/ingredients）来源稳定、以导入为准；标签类字段（scene_tags/sales_script）是 AI 推理生成，属于推断数据，已有则保留是防止静默覆盖人工校正结果。

---

## 列映射引擎

### 映射规则（部分）

```python
FIELD_MAP = {
    "条码": "sku_id",
    "商品名称": "name",
    "价格": "price",
    "商品分类": "category",
    "成分": "ingredients",
    "适宜人群": "ingredients",   # 特殊：Youzan 格式下可能映射到 ingredients
    "商品标签": "feature_tag",
    "场景标签": "scene_tags",
    "销售话术": "sales_script",
    "禁忌标签": "contraindication_tags",
}
```

映射时大小写不敏感，模糊匹配（如包含"标签"字段优先匹配 `feature_tag`）。

### 未识别列处理

Excel 中存在系统不认识的新列时：
- **预览页面显示警告**：发现未知列 `XXX`
- **不影响导入**：跳过未知列，不写入数据库

---

## 预览确认页面

上传后展示：

1. **表头映射表** — 每行：`Excel 列名 → 系统字段`，可直接看到映射结果
2. **前 5 行样例** — 每行展示原始值，乱码时显示 `sku_id + [乱码]`
3. **警告信息**：
   - 🔴 乱码行（UTF-8 解码失败）：标红，显示 `sku_id + "商品名乱码"`
   - ⚠️ 重复 sku_id（数据库已存在）：显示"将更新"状态
   - 🟡 缺主数据行（name 或 price 为空）

### 乱码处理流程

1. 导入时尝试 UTF-8 解码
2. 解码失败 → 标记为乱码行
3. 预览页面：**不显示损坏内容，直接显示 `sku_id + [商品名乱码]`**
4. Staff 在 Youzan 修改商品名后重新下载导入

---

## API 设计

### `POST /api/staff/products/preview`

上传 Excel，返回预览信息（不写入数据库）。

**Request**: `multipart/form-data`, `file: Excel`

**Response**:
```json
{
  "total_rows": 120,
  "mapping": {"条码": "sku_id", "商品名称": "name", ...},
  "warnings": [
    {"row": 5, "type": "garbled", "sku_id": "B011", "message": "商品名乱码"},
    {"row": 10, "type": "duplicate", "sku_id": "T001", "message": "数据库已存在，将更新"}
  ],
  "samples": [
    {"sku_id": "B001", "name": "真实姓名", "price": 29.0, ...},
    ...
  ]
}
```

### `POST /api/staff/products/import`

确认后正式导入。

**Request**: `multipart/form-data`, `file: Excel`

**Response**:
```json
{
  "imported": 5,
  "updated": 10,
  "skipped_garbled": 2,
  "tag_filled": 3,
  "errors": []
}
```

---

## 涉及文件

- `backend/app/api/staff.py` — 新增 `POST /products/preview` + 修改 `POST /products/import`
- `backend/app/services/data_importer.py` — 完全重写，动态映射 + Merge 逻辑
- `backend/app/staff-admin.html` — 新增上传 + 预览 Modal（复用现有 Import Modal 结构）

---

## Tag AI 补全触发条件

当 `feature_tag` / `scene_tags` / `sales_script` / `contraindication_tags` 在数据库中为空时，导入后触发 `TagGenerator` 补全。批量补全而非逐条调用，减少 API 开销。
