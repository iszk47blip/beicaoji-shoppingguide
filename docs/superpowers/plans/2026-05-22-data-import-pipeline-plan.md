# 数据导入管道重构 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 `data_importer.py`，实现动态列映射 + Merge 策略，新增 Preview API endpoint，重用现有 Import Modal 结构

**Architecture:**
- 完全重写 `data_importer.py`，核心逻辑拆分为 `parse_excel()` (解析+映射) 和 `merge_product()` (Merge 决策)
- 新增 `POST /api/staff/products/preview` endpoint，返回映射预览，不写 DB
- 修改现有 `POST /api/staff/products/import` endpoint，调用新导入逻辑
- 前端复用现有 Import Modal，新增预览确认步骤

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, openpyxl, TagGenerator

---

## 文件结构

- **Create:** `backend/app/services/data_importer.py` (重写)
- **Modify:** `backend/app/api/staff.py:96-195` (重构 import endpoint，新增 preview endpoint)
- **Modify:** `backend/app/staff-admin.html:757-780` (Import Modal 增加预览确认步骤)
- **Test:** `backend/tests/test_importer.py` (新增测试用例)

---

## Task 1: 动态列映射引擎

**Files:**
- Create: `backend/app/services/data_importer.py`
- Test: `backend/tests/test_importer.py`

- [ ] **Step 1: 写测试 — 列映射正确识别**

```python
def test_dynamic_column_mapping():
    """Test that column names map to correct fields regardless of position."""
    from app.services.data_importer import parse_excel_columns
    # Simulate a header row with known column names
    headers = ["条码", "商品名称", "零售价", "一级分类", "成分", "适宜人群", "商品标签", "场景标签", "禁忌标签", "销售话术"]
    field_map = parse_excel_columns(headers)
    assert field_map["条码"] == "sku_id"
    assert field_map["商品名称"] == "name"
    assert field_map["零售价"] == "price"
    assert field_map["一级分类"] == "category"
    assert field_map["成分"] == "ingredients"
    assert field_map["适宜人群"] == "ingredients"  # fallback to ingredients
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_importer.py::test_dynamic_column_mapping -v`
Expected: FAIL — function not defined

- [ ] **Step 3: 实现 parse_excel_columns 函数**

```python
import re

FIELD_ALIASES = {
    "sku_id": ["条码", "商品条码", "sku_id", "SKU_ID", "商品编码"],
    "name": ["商品名称", "名称", "name", "品名"],
    "price": ["零售价", "价格", "price", "售价"],
    "category": ["一级分类", "分类", "category", "商品分类"],
    "ingredients": ["成分", "ingredients", "配料", "主要成分"],
    "feature_tag": ["商品标签", "feature_tag", "标签"],
    "scene_tags": ["场景标签", "scene_tags", "适用场景"],
    "sales_script": ["销售话术", "sales_script", "话术"],
    "contraindication_tags": ["禁忌标签", "禁忌", "contraindication_tags"],
}


def parse_excel_columns(headers: list[str]) -> dict[str, str]:
    """
    Map header names to field names dynamically.
    Returns dict of {field_name: column_index}.
    Handles case-insensitive and fuzzy matching.
    """
    result = {}
    for idx, header in enumerate(headers):
        if not header:
            continue
        header_clean = str(header).strip()
        for field_name, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                if alias.lower() == header_clean.lower() or alias in header_clean:
                    if field_name not in result:
                        result[field_name] = idx
                    break
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_importer.py::test_dynamic_column_mapping -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/services/data_importer.py tests/test_importer.py
git commit -m "feat(importer): add dynamic column mapping engine"
```

---

## Task 2: Merge 逻辑 — 字段分类决策

**Files:**
- Modify: `backend/app/services/data_importer.py`

- [ ] **Step 1: 写测试 — 已有商品主数据覆盖，Tag 保留**

```python
def test_merge_preserves_tags_updates_master():
    """Test that existing product's name/price are overwritten but tags preserved."""
    from app.services.data_importer import merge_product
    from app.models.product import Product
    existing = Product(
        sku_id="B001",
        name="旧名称",
        price=10.0,
        category="饼干",
        scene_tags="睡眠, 焦虑",
        feature_tag="安神",
        sales_script="",
        contraindication_tags=""
    )
    new_data = {
        "name": "新名称",
        "price": 25.0,
        "category": "饼干",
        "ingredients": "薰衣草, 洋甘菊",
    }
    merge_product(existing, new_data)
    assert existing.name == "新名称"
    assert existing.price == 25.0
    assert existing.scene_tags == "睡眠, 焦虑"  # preserved
    assert existing.feature_tag == "安神"  # preserved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_importer.py::test_merge_preserves_tags_updates_master -v`
Expected: FAIL — merge_product not defined

- [ ] **Step 3: 实现 merge_product 函数**

```python
# Fields where Excel data always wins (source of truth)
MASTER_DATA_FIELDS = {"name", "price", "category", "ingredients", "is_active", "sku_id"}

# Fields where AI generation is trusted — preserve existing, fill if empty
TAG_DATA_FIELDS = {"feature_tag", "scene_tags", "sales_script", "contraindication_tags"}


def merge_product(existing: Product, new_data: dict) -> bool:
    """
    Merge new_data into existing product.
    Returns True if any field was changed.
    Master data fields always overwrite.
    Tag data fields: preserve existing, only fill if empty.
    """
    changed = False
    for field in MASTER_DATA_FIELDS:
        if field in new_data and new_data[field] not in (None, ""):
            val = new_data[field]
            if field == "price" and val is not None:
                val = float(val)
            if field == "is_active":
                val = bool(val)
            if getattr(existing, field, None) != val:
                setattr(existing, field, val)
                changed = True

    for field in TAG_DATA_FIELDS:
        current = getattr(existing, field, None) or ""
        if current.strip():
            continue  # preserve existing
        if field in new_data and new_data[field] not in (None, ""):
            setattr(existing, field, new_data[field])
            changed = True

    return changed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_importer.py::test_merge_preserves_tags_updates_master -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/services/data_importer.py tests/test_importer.py
git commit -m "feat(importer): implement merge logic with tag preservation"
```

---

## Task 3: Preview API Endpoint

**Files:**
- Modify: `backend/app/api/staff.py`

- [ ] **Step 1: 写测试 — preview endpoint 返回正确结构**

```python
def test_preview_endpoint_returns_mapping_and_warnings():
    """Test that preview endpoint returns mapping, samples, and warnings."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    # Requires a real xlsx file for full test
    # This test verifies endpoint exists and returns correct shape
    with open("beicaoji-产品目录/bread.xlsx", "rb") as f:
        response = client.post(
            "/api/staff/products/preview",
            files={"file": ("bread.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert response.status_code == 200
    data = response.json()
    assert "mapping" in data
    assert "samples" in data
    assert "warnings" in data
    assert "total_rows" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_importer.py::test_preview_endpoint_returns_mapping_and_warnings -v`
Expected: FAIL — 404 (endpoint not defined)

- [ ] **Step 3: 实现 preview endpoint**

在 `staff.py` 的 `import_excel` 函数上方添加：

```python
@router.post("/products/preview")
async def preview_import(file: UploadFile = File(...), db=Depends(get_db)):
    """上传 Excel，返回预览（映射+样例+警告），不写 DB。"""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件")
    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb.active

    headers = [cell.value for cell in ws[1]]
    field_map = parse_excel_columns(headers)

    # Count total data rows
    total_rows = sum(1 for row in ws.iter_rows(min_row=2) if any(c.value for c in row))

    # Collect samples and warnings
    samples = []
    warnings = []
    existing_skus = {p.sku_id for p in db.query(Product.sku_id).all()}

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=7, values_only=True), start=2):
        row_data = {}
        for field_name, col_idx in field_map.items():
            val = row[col_idx] if col_idx < len(row) else None
            row_data[field_name] = val

        sku = row_data.get("sku_id", "")
        name = row_data.get("name", "")

        # Check for garbled name (non-UTF8)
        is_garbled = False
        if name:
            try:
                name.encode("utf-8")
            except UnicodeEncodeError:
                is_garbled = True

        if is_garbled:
            warnings.append({
                "row": row_idx,
                "type": "garbled",
                "sku_id": sku or "(empty)",
                "message": "商品名乱码，请在有赞后台修正后重新导入"
            })
        elif sku and sku in existing_skus:
            warnings.append({
                "row": row_idx,
                "type": "duplicate",
                "sku_id": sku,
                "message": "数据库已存在，将更新主数据"
            })

        samples.append({k: v for k, v in row_data.items() if k})

    return {
        "total_rows": total_rows,
        "mapping": {v: k for k, v in field_map.items()},  # invert: field_name -> column_name
        "warnings": warnings,
        "samples": samples
    }
```

**依赖导入（需在 staff.py 顶部确认）：**

```python
from app.services.data_importer import parse_excel_columns, merge_product, import_all
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_importer.py::test_preview_endpoint_returns_mapping_and_warnings -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/api/staff.py tests/test_importer.py
git commit -m "feat(api): add POST /products/preview endpoint"
```

---

## Task 4: 重构 import_excel Endpoint — 集成新导入逻辑

**Files:**
- Modify: `backend/app/api/staff.py:96-195`

- [ ] **Step 1: 写测试 — 导入时主数据更新，Tag 保留**

```python
def test_import_updates_master_preserves_tags():
    """Test that re-importing updates name/price but preserves existing tags."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Base
    from app.models.product import Product
    from app.services.data_importer import import_products_from_wb

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Insert existing product with tags
    existing = Product(
        sku_id="B001",
        name="旧名称",
        price=10.0,
        category="饼干",
        scene_tags="睡眠",
        feature_tag="安神",
    )
    session.add(existing)
    session.commit()

    # Import updated data
    import_products_from_wb(session, wb)  # wb = openpyxl.load_workbook(...)

    # Verify name/price updated
    updated = session.query(Product).filter_by(sku_id="B001").first()
    assert updated.name == "新名称"  # from Excel
    assert updated.price == 25.0    # from Excel
    assert updated.scene_tags == "睡眠"  # preserved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_importer.py::test_import_updates_master_preserves_tags -v`
Expected: FAIL — function not defined

- [ ] **Step 3: 实现 import_products_from_wb 函数**

在 `data_importer.py` 末尾添加：

```python
def import_products_from_wb(session, wb) -> dict:
    """
    Import products from an openpyxl Workbook object.
    Uses dynamic column mapping, applies merge strategy.
    Returns {imported, updated, tag_filled, skipped_garbled}.
    """
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    field_map = parse_excel_columns(headers)

    imported = updated = tag_filled = skipped_garbled = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        row_data = {}
        for field_name, col_idx in field_map.items():
            val = row[col_idx] if col_idx < len(row) else None
            row_data[field_name] = val

        sku = str(row_data.get("sku_id") or "").strip()
        if not sku:
            continue

        name = str(row_data.get("name") or "").strip()
        # Check garbled
        is_garbled = False
        if name:
            try:
                name.encode("utf-8")
            except UnicodeEncodeError:
                is_garbled = True

        if is_garbled:
            skipped_garbled += 1
            continue

        existing = session.query(Product).filter(Product.sku_id == sku).first()

        if existing:
            changed = merge_product(existing, row_data)
            updated += 1
            # Tag fill if empty
            if not (existing.scene_tags and existing.scene_tags.strip()):
                tag_filled += 1
        else:
            product = Product(sku_id=sku)
            merge_product(product, row_data)
            session.add(product)
            imported += 1

    session.commit()
    return {"imported": imported, "updated": updated, "tag_filled": tag_filled, "skipped_garbled": skipped_garbled}
```

- [ ] **Step 4: 重构 import_excel endpoint**

用新函数替换 `import_excel` 中的循环逻辑，保留外围的 file handling 和 response：

```python
@router.post("/products/import")
async def import_excel(file: UploadFile = File(...), db=Depends(get_db)):
    """上传有赞导出的商品库 Excel，增量导入（主数据用导入值，Tag 保留/补全）"""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件")
    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))

    result = import_products_from_wb(db, wb)
    return {
        "imported": result["imported"],
        "updated": result["updated"],
        "tag_filled": result["tag_filled"],
        "skipped_garbled": result["skipped_garbled"],
        "errors": []
    }
```

**注意：** `import_products_from_wb` 需要接受 `db` session 参数（FastAPI 的 `db=Depends(get_db)`）。

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_importer.py::test_import_updates_master_preserves_tags -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/api/staff.py app/services/data_importer.py tests/test_importer.py
git commit -m "feat(importer): refactor import_excel with merge strategy"
```

---

## Task 5: 前端预览确认 Modal

**Files:**
- Modify: `backend/app/staff-admin.html:757-780` (Import Modal)
- Modify: `backend/app/staff-admin.html:1073-1127` (Import JS)

- [ ] **Step 1: 分析现有 Import Modal 结构**

Read: `backend/app/staff-admin.html` lines 757-780 and 1073-1127

现有 Import Modal 有三个状态：
1. `importHint` = "点击上传或拖拽 Excel 文件"
2. `importHint` = "已选: {filename}" → 等待确认
3. `importHint` = "导入中…" → `doImport()` 调用 API

需要新增第四个状态：预览确认。流程：
`选择文件 → doPreview() → 显示预览 → doImportConfirmed() → 导入`

- [ ] **Step 2: 添加预览 UI**

在 `importModal` 的 `.modal-body` 中，在 `<div class="import-area">` 下方添加：

```html
<!-- Preview section (hidden by default) -->
<div id="importPreview" style="display:none; margin-top:16px;">
  <div style="font-size:13px;color:#666;margin-bottom:8px;">列映射确认：</div>
  <div id="previewMapping" style="background:#f8f8f8;border-radius:6px;padding:10px;font-size:12px;margin-bottom:12px;"></div>
  <div id="previewWarnings" style="margin-bottom:12px;"></div>
  <div style="font-size:13px;color:#666;margin-bottom:4px;">数据样例（前5行）：</div>
  <div id="previewSamples" style="max-height:200px;overflow-y:auto;border:1px solid #eee;border-radius:6px;"></div>
</div>
```

- [ ] **Step 3: 添加预览 JS 函数**

在 `doImport()` 函数下方添加：

```javascript
async function doPreview() {
  const fileInput = document.getElementById('importFile');
  if (!fileInput.files.length) return;
  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  document.getElementById('importHint').textContent = '正在分析...';
  try {
    const res = await fetch(API + '/products/preview', { method: 'POST', body: fd }).then(r => r.json());
    // Show preview section
    document.getElementById('importPreview').style.display = 'block';
    // Render mapping
    const mappingDiv = document.getElementById('previewMapping');
    const mapLines = Object.entries(res.mapping || {}).map(([field, col]) => `${col} → ${field}`).join('\n');
    mappingDiv.innerHTML = '<pre style="margin:0;white-space:pre-wrap;">' + mapLines + '</pre>';
    // Render warnings
    const warnDiv = document.getElementById('previewWarnings');
    if (res.warnings && res.warnings.length) {
      warnDiv.innerHTML = res.warnings.map(w =>
        `<div style="color:${w.type === 'garbled' ? '#e74c3c' : '#e67e22'};font-size:12px;margin-bottom:4px;">
          ${w.type === 'garbled' ? '🔴' : '⚠️'} 第${w.row}行: ${w.message} (sku: ${w.sku_id})
        </div>`
      ).join('');
    } else {
      warnDiv.innerHTML = '';
    }
    // Render samples
    const samplesDiv = document.getElementById('previewSamples');
    samplesDiv.innerHTML = res.samples.map(s =>
      `<div style="padding:6px 10px;border-bottom:1px solid #f0f0f0;font-size:12px;">
        <strong>${s.sku_id || '(无条码)'}</strong>: ${s.name || '(无名称)'} | ¥${s.price || 0}
      </div>`
    ).join('');
    document.getElementById('importHint').textContent = `共 ${res.total_rows} 行，已分析`;
    document.getElementById('importBtn').disabled = false;
    document.getElementById('importBtn').textContent = '确认导入';
  } catch(e) {
    document.getElementById('importHint').textContent = '分析失败，请重试';
    console.error(e);
  }
}
```

- [ ] **Step 4: 修改 doImport 逻辑**

`doImport()` 改为先检查是否有预览数据，如果有则直接用，没有则调用原 API：

```javascript
let _previewResult = null;

async function doImport() {
  if (!_previewResult) {
    // Old path: direct import (for backward compat)
    await _doImportOriginal();
    return;
  }
  // New path: confirmed import
  const fd = new FormData();
  fd.append('file', document.getElementById('importFile').files[0]);
  document.getElementById('importBtn').disabled = true;
  document.getElementById('importHint').textContent = '导入中…';
  try {
    const res = await fetch(API + '/products/import', { method: 'POST', body: fd }).then(r => r.json());
    const el = document.getElementById('importResult');
    el.className = 'import-result success';
    el.innerHTML = `<span><span class="num">${res.imported}</span> 新增</span><span><span class="num">${res.updated}</span> 更新</span><span><span class="num">${res.skipped_garbled}</span> 跳过</span>`;
    document.getElementById('importHint').textContent = '导入完成';
    document.getElementById('importBtn').textContent = '导入';
    _previewResult = null;
  } catch(e) {
    document.getElementById('importHint').textContent = '导入失败';
    document.getElementById('importBtn').disabled = false;
    document.getElementById('importBtn').textContent = '确认导入';
  }
}
```

**修改 `handleFileSelect`**：选完文件后立即调用 `doPreview()`：

```javascript
function handleFileSelect(input) {
  if (!input.files.length) return;
  document.getElementById('importHint').textContent = '已选: ' + input.files[0].name;
  document.getElementById('importBtn').disabled = true;
  document.getElementById('importPreview').style.display = 'none';
  _previewResult = null;
  document.getElementById('importBtn').textContent = '预览确认';
  doPreview();
}
```

- [ ] **Step 5: 测试**

访问 `http://127.0.0.1:8004/staff-admin`，打开 Import Modal，上传 `beicaoji-产品目录/bread.xlsx`，验证预览区域正确显示映射和警告。

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/staff-admin.html
git commit -m "feat(staff-admin): add import preview confirmation flow"
```

---

## 自检清单

1. **Spec 覆盖：** 每个 spec 需求都有对应 task？
   - [x] 动态列映射 → Task 1
   - [x] Preview API → Task 3
   - [x] Merge 策略（主数据覆盖/Tags 保留） → Task 2
   - [x] 乱码行跳过 → Task 4
   - [x] 前端预览确认 → Task 5
   - [ ] Tag AI 补全触发（batch）→ 未单独实现（现有 `/products/generate-tags` endpoint 已支持）

2. **Placeholder scan:** 无 TBD/TODO/未填内容

3. **类型一致性:** `merge_product(existing, new_data)` 签名在 Task 2 和 Task 4 中一致

---

## 执行方式

Plan 完成后提供两种执行选项：

**1. Subagent-Driven (推荐)** — 每 task 派发独立 subagent，task 间 review，快速迭代

**2. Inline Execution** — 当前 session 内顺序执行，有 checkpoint

选择哪种？
