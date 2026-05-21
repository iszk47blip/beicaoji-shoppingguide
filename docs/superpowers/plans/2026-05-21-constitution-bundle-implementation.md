# 体质套餐管理与智能推荐实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增体质固定套餐后台管理 + 主推产品管理 + LLM 智能补充推荐

**Architecture:**
- 新建 `constitution_bundle` 和 `hot_product` 两张表，存储体质套餐商品和店家主推产品
- Staff API 新增 CRUD 端点管理套餐内容
- 推荐流程改为：固定套餐 + LLM 基于对话上下文补充（去重后展示）
- Staff-admin.html 新增两个 Tab：主推管理、体质套餐

**Tech Stack:** FastAPI, SQLAlchemy, Pure HTML/JS staff-admin

---

## Part 1: 数据库模型

### Task 1: 新建 ConstitutionBundle 模型

**Files:**
- Create: `backend/app/models/constitution_bundle.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_constitution_bundle.py`

- [ ] **Step 1: 创建测试文件**

```python
# backend/tests/test_constitution_bundle.py
from app.models.constitution_bundle import ConstitutionBundle, HotProduct

def test_constitution_bundle_crud(test_db):
    from app.models.constitution_bundle import ConstitutionBundle
    # 写入
    item = ConstitutionBundle(constitution_type="气虚质", sku_id="S001", sort_order=0)
    test_db.add(item)
    test_db.commit()
    # 读取
    result = test_db.query(ConstitutionBundle).filter_by(constitution_type="气虚质").all()
    assert len(result) == 1
    assert result[0].sku_id == "S001"

def test_hot_product_crud(test_db):
    from app.models.constitution_bundle import HotProduct
    item = HotProduct(sku_id="S001", sort_order=0)
    test_db.add(item)
    test_db.commit()
    result = test_db.query(HotProduct).all()
    assert len(result) == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest backend/tests/test_constitution_bundle.py -v`
Expected: FAIL — model not defined

- [ ] **Step 3: 写入模型**

```python
# backend/app/models/constitution_bundle.py
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from app.models import Base

class ConstitutionBundle(Base):
    __tablename__ = "constitution_bundle"
    __table_args__ = (UniqueConstraint("constitution_type", "sku_id"),)

    id = Column(Integer, primary_key=True)
    constitution_type = Column(String(20), nullable=False, index=True)
    sku_id = Column(String(20), nullable=False, index=True)
    sort_order = Column(Integer, default=0)
    description = Column(String(200))
    created_at = Column(DateTime, default=__import__("datetime").datetime.utcnow)


class HotProduct(Base):
    __tablename__ = "hot_product"

    id = Column(Integer, primary_key=True)
    sku_id = Column(String(20), nullable=False, unique=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=__import__("datetime").datetime.utcnow)
```

- [ ] **Step 4: 修改 models/__init__.py 导出**

```python
from app.models.constitution_bundle import ConstitutionBundle, HotProduct
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest backend/tests/test_constitution_bundle.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/constitution_bundle.py backend/app/models/__init__.py backend/tests/test_constitution_bundle.py
git commit -m "feat: add ConstitutionBundle and HotProduct models"
```

---

## Part 2: Staff API 端点

### Task 2: 体质套餐 API

**Files:**
- Modify: `backend/app/api/staff.py`
- Test: `backend/tests/test_constitution_bundle.py`

- [ ] **Step 1: 写测试**

```python
def test_get_constitution_bundles(test_db_with_bundle):
    from app.models.constitution_bundle import ConstitutionBundle
    # fixtures: 已在 test_db_with_bundle 里写入气虚质套餐数据
    from app.api.staff import router as staff_router
    # 用 TestClient 测试 /api/staff/constitution-bundles
    # (实际用 app 作为 fixture)
```

- [ ] **Step 2: 添加端点到 staff.py**

在 `staff.py` 末尾添加：

```python
@router.get("/constitution-bundles")
def get_constitution_bundles(db=Depends(get_db)):
    bundles = db.query(ConstitutionBundle).order_by(ConstitutionBundle.sort_order).all()
    # 按体质类型分组
    grouped = {}
    for b in bundles:
        grouped.setdefault(b.constitution_type, []).append({
            "sku_id": b.sku_id,
            "sort_order": b.sort_order,
            "description": b.description,
            "name": db.query(Product).filter_by(sku_id=b.sku_id).first().name if db.query(Product).filter_by(sku_id=b.sku_id).first() else b.sku_id
        })
    return grouped


@router.put("/constitution-bundles/{ctype}")
def put_constitution_bundle(ctype: str, data: dict, db=Depends(get_db)):
    # data: {"products": [{"sku_id":"...","sort_order":0,"description":"..."}], "description": "..."}
    # 删除旧的，批量插入新的
    db.query(ConstitutionBundle).filter(ConstitutionBundle.constitution_type == ctype).delete()
    for i, p in enumerate(data.get("products", [])):
        item = ConstitutionBundle(
            constitution_type=ctype,
            sku_id=p["sku_id"],
            sort_order=p.get("sort_order", i),
            description=p.get("description", "")
        )
        db.add(item)
    db.commit()
    return {"status": "ok", "count": len(data.get("products", []))}


@router.get("/hot-products")
def get_hot_products(db=Depends(get_db)):
    items = db.query(HotProduct).order_by(HotProduct.sort_order).all()
    return [{"sku_id": h.sku_id, "sort_order": h.sort_order,
             "name": db.query(Product).filter_by(sku_id=h.sku_id).first().name if db.query(Product).filter_by(sku_id=h.sku_id).first() else h.sku_id}
            for h in items]


@router.put("/hot-products")
def put_hot_products(data: dict, db=Depends(get_db)):
    # data: {"products": [{"sku_id":"...","sort_order":0}]}
    db.query(HotProduct).delete()
    for i, p in enumerate(data.get("products", [])):
        item = HotProduct(sku_id=p["sku_id"], sort_order=p.get("sort_order", i))
        db.add(item)
    db.commit()
    return {"status": "ok", "count": len(data.get("products", []))}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/staff.py
git commit -m "feat(staff-api): add constitution-bundles and hot-products CRUD endpoints"
```

---

## Part 3: 推荐流程修改

### Task 3: 修改 RecommendEngine — 添加 LLM 补充逻辑

**Files:**
- Modify: `backend/app/services/recommend_engine.py`
- Test: `backend/tests/test_constitution_bundle.py`

- [ ] **Step 1: 写测试**

```python
def test_llm_supplement_recommendations(test_db_with_bundle):
    from app.services.recommend_engine import RecommendEngine
    from app.services.product_service import ProductService
    svc = ProductService(test_db_with_bundle)
    engine = RecommendEngine(svc)
    # 已有固定套餐数据
    result = engine.recommend('{"qi_deficiency":"是"}', "最近睡不好")
    assert "fixed_bundle" in result
    assert "llm_recommendations" in result
    # 去重验证：fixed 和 llm 的 sku_id 不重复
    fixed_skus = {p["sku_id"] for p in result.get("fixed_bundle", [])}
    llm_skus = {p["sku_id"] for p in result.get("llm_recommendations", [])}
    assert len(fixed_skus & llm_skus) == 0
```

- [ ] **Step 2: 修改 RecommendEngine.recommend()**

在 `recommend()` 方法中添加 `fixed_bundle` 字段，从数据库读取固定套餐。

新增 `_llm_supplement()` 方法：传入固定套餐 SKU 列表 + 对话上下文 → 返回 LLM 推荐列表（去重后）。

修改 `_build_bundle()` 的返回值结构：

```python
def recommend(self, constitution_raw: str, scene_input: str) -> dict:
    # ... 现有逻辑 ...
    # 1. 读取固定套餐
    fixed_items = self._get_fixed_bundle(constitution_type)
    # 2. LLM 补充
    llm_items = self._llm_supplement(fixed_skus, constitution_raw, scene_input)
    # 3. 去重合并
    return {
        "constitution": constitution,
        "scene_tags": scene_tags,
        "fixed_bundle": [_to_dict(p) for p in fixed_items],
        "llm_recommendations": [_to_dict(p) for p in llm_items],
        "no_match": len(fixed_items + llm_items) == 0,
    }
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/recommend_engine.py
git commit -m "feat: add fixed_bundle + llm_supplement to recommend engine"
```

---

### Task 4: 修改 chat.py — 更新推荐展示结构

**Files:**
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: 更新 `_describe_recommendation`**

修改 `_describe_recommendation()` 函数，分别描述 `fixed_bundle` 和 `llm_recommendations` 两部分。

```python
def _describe_recommendation(engine, state, rec):
    fixed = rec.get("fixed_bundle", [])
    llm_recs = rec.get("llm_recommendations", [])
    # 构建分段描述文本...
```

- [ ] **Step 2: 修改返回结构**

在 `/api/chat/send` 的返回中，把 `recommendation` 字段的 `bundle` 替换为展示用字段（前端需要 `fixed_bundle` 和 `llm_recommendations` 分开）。

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat(chat): update recommendation structure with fixed_bundle and llm_recommendations"
```

---

### Task 5: 修改「你都有什么产品」流程

**Files:**
- Modify: `backend/app/api/chat.py`, `backend/app/services/dialogue_engine.py`

- [ ] **Step 1: 修改 intent=show_catalog 处理**

将 `show_catalog` intent 的响应从体质分类套餐改为 hot_products 列表。

```python
elif intent == "show_catalog":
    product_svc = ProductService(db)
    hot_items = product_svc.get_hot_products()  # 新增方法
    catalog = {"hot_products": hot_items, ...}
```

- [ ] **Step 2: 在 ProductService 添加 get_hot_products()**

```python
def get_hot_products(self):
    from app.models.constitution_bundle import HotProduct
    items = self.session.query(HotProduct).order_by(HotProduct.sort_order).all()
    return [self.get_by_sku(h.sku_id) for h in items if self.get_by_sku(h.sku_id)]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/chat.py backend/app/services/product_service.py
git commit -m "feat: show hot_products instead of constitution catalog on show_catalog intent"
```

---

## Part 4: Staff Admin UI

### Task 6: Staff Admin 新增 Tab

**Files:**
- Modify: `backend/app/staff-admin.html`

- [ ] **Step 1: 添加 Tab 导航**

在 staff-admin.html 现有 Tab 栏后面新增：
```html
<div class="tab-btn" data-tab="hot-products">主推管理</div>
<div class="tab-btn" data-tab="bundle-manage">体质套餐</div>
```

- [ ] **Step 2: 主推管理 Tab 内容**

表格展示 hot_products，支持添加商品（下拉选 SKU）、删除、拖拽排序。保存调用 `PUT /api/staff/hot-products`。

- [ ] **Step 3: 体质套餐 Tab 内容**

四个 sub-tab（气虚质/阳虚质/阴虚质/湿热质），每个展示该体质套餐商品列表，支持添加/删除。保存调用 `PUT /api/staff/constitution-bundles/:type`。

- [ ] **Step 4: 测试手动**

在浏览器打开 `/staff-admin`，测试主推管理和体质套餐的增删改。

- [ ] **Step 5: Commit**

```bash
git add backend/app/staff-admin.html
git commit -m "feat(staff-admin): add hot-products and constitution bundle management tabs"
```

---

## 依赖顺序

```
Task 1 (模型) → Task 2 (API) → Task 3 (RecommendEngine) → Task 4 (chat.py) → Task 5 (show_catalog) → Task 6 (Staff Admin UI)
```

Part 1 和 Part 2 可并行开发（模型和 API 无依赖）。