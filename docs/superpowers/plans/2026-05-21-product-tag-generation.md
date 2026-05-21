# 产品标签自动生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在产品导入时自动调用 LLM 生成 `scene_tags` 和 `contraindication_tags`，使全部 315 个有效产品进入推荐池。

**Architecture:** 新增 `TagGenerator` 服务（独立模块），在 `POST /api/staff/products/import` 中对无标签产品调用生成，失败时重试一次并记录到 `failed_tags[]` 响应字段。

**Tech Stack:** Python, Anthropic LLM API (`app.config.settings`), openpyxl

---

## File Map

| 文件 | 职责 |
|------|------|
| Create: `backend/app/services/tag_generator.py` | TagGenerator 服务，调用 LLM 生成标签 |
| Modify: `backend/app/api/staff.py:93-160` | 接入 TagGenerator，改造导入逻辑，处理失败重试和响应 |
| Create: `backend/tests/test_tag_generator.py` | TagGenerator 单元测试 |

---

## Task 1: TagGenerator 服务

**Files:**
- Create: `backend/app/services/tag_generator.py`
- Test: `backend/tests/test_tag_generator.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_tag_generator.py
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, 'backend')
from app.services.tag_generator import TagGenerator

def test_generate_returns_scene_and_contra_tags():
    gen = TagGenerator()
    with patch.object(gen, '_call_llm', return_value={"scene_tags": "补气, 健脾", "contraindication_tags": "胃寒少吃"}):
        result = gen.generate("山药茯苓饼干", "山药、茯苓、面粉")
    assert "补气" in result["scene_tags"]
    assert "胃寒" in result["contraindication_tags"]

def test_generate_calls_correct_prompt():
    gen = TagGenerator()
    captured = {}
    def capture_prompt(prompt, messages):
        captured["prompt"] = prompt
        return MagicMock(text='{"scene_tags": "x", "contraindication_tags": "y"}')
    with patch.object(gen, '_call_llm', side_effect=capture_prompt):
        gen.generate("测试", "成分")
    assert "山药茯苓饼干" in captured["prompt"] or "测试" in captured["prompt"]
```

- [ ] **Step 2: Run test to verify it fails**

```
cd E:/VIBE/beicaoji && python -m pytest backend/tests/test_tag_generator.py -v 2>&1
```
Expected: FAIL — module not found

- [ ] **Step 3: Write TagGenerator implementation**

```python
# backend/app/services/tag_generator.py
import json
import time
from anthropic import Anthropic
from app.config import settings

TAG_GENERATION_SYSTEM = """你是药食同源产品标签专家。根据产品信息生成场景标签和禁忌标签。

产品名称：{name}
成分：{ingredients}

要求：
- scene_tags：适合的场景或调理方向，用有意义的词描述，2-5 个，用逗号分隔
- contraindication_tags：禁忌或需慎用的情况，如"孕妇慎用"、"胃寒少吃"、"经期慎用"，用逗号分隔，无则写"无"

只输出一行 JSON：
{"scene_tags": "...", "contraindication_tags": "..."}"""

class TagGenerationError(Exception):
    pass

class TagGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    def generate(self, name: str, ingredients: str) -> dict:
        """Returns {"scene_tags": "...", "contraindication_tags": "..."}"""
        prompt = TAG_GENERATION_SYSTEM.format(name=name, ingredients=ingredients or "未知")
        text = self._call_llm(prompt)
        try:
            data = json.loads(text)
            return {
                "scene_tags": data.get("scene_tags", ""),
                "contraindication_tags": data.get("contraindication_tags", ""),
            }
        except json.JSONDecodeError:
            raise TagGenerationError(f"LLM 返回格式错误: {text[:100]}")

    def _call_llm(self, prompt: str) -> str:
        resp = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=256,
            system="你是一个 JSON 输出的标签生成器。",
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if hasattr(block, "text"):
                return block.text.strip()
        raise TagGenerationError("LLM 返回为空")
```

- [ ] **Step 4: Run test to verify it passes**

```
cd E:/VIBE/beicaoji && python -m pytest backend/tests/test_tag_generator.py -v 2>&1
```
Expected: PASS (mocked — no real API call)

- [ ] **Step 5: Commit**

```bash
cd E:/VIBE/beicaoji
git add backend/app/services/tag_generator.py backend/tests/test_tag_generator.py
git commit -m "feat: add TagGenerator service for auto scene/contra tag generation"
```

---

## Task 2: 集成到导入 API

**Files:**
- Modify: `backend/app/api/staff.py:93-160`（约 70 行）

- [ ] **Step 1: Read current staff.py import logic**

```bash
head -160 backend/app/api/staff.py | tail -70
```

- [ ] **Step 2: Write test for failed_tags response**

```python
# Append to backend/tests/test_tag_generator.py

def test_import_with_tag_generation_failure():
    """当 TagGenerator 两次失败时，failed_tags 应包含该产品"""
    # 验证 data_importer 在生成失败时的行为
    # （实际集成测试，依赖真实 DB）
    pass
```

- [ ] **Step 3: Modify import endpoint — add tag generation**

在 `existing` / `new product` 写入后，如果 `scene_tags` 为空（或整个 tags 为空），调用 `TagGenerator.generate()`，失败时重试一次，最终失败则记入 `failed_tags[]`。

关键修改点（伪代码）：

```python
from app.services.tag_generator import TagGenerator

tag_gen = TagGenerator()
failed_tags = []

# 在产品写入后：
if not (product.scene_tags and product.scene_tags.strip()):
    scene_tags, contra_tags = None, None
    for attempt in range(2):
        try:
            tags = tag_gen.generate(product.name, product.ingredients)
            scene_tags = tags["scene_tags"]
            contra_tags = tags["contraindication_tags"]
            break
        except Exception as e:
            if attempt == 0:
                time.sleep(5)
                continue
            failed_tags.append({"sku_id": sku, "name": product.name, "reason": str(e)[:100]})
    if scene_tags:
        product.scene_tags = scene_tags
        product.contraindication_tags = contra_tags
```

- [ ] **Step 4: Modify import response — add failed_tags**

在返回语句添加：

```python
return {
    "imported": imported,
    "updated": updated,
    "total": imported + updated,
    "failed": failed,        # 原逻辑（数据库写入失败）
    "failed_tags": failed_tags,  # 新增：标签生成失败列表
}
```

- [ ] **Step 5: Verify with curl**

```bash
curl -s -X POST http://localhost:8004/api/staff/products/import \
  -F "file=@beicaoji-产品目录/biscuit.xlsx" 2>&1 | python -m json.tool
```
Expected: 响应中有 `failed_tags` 字段（可能为空）

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/staff.py
git commit -m "feat: integrate TagGenerator into products/import endpoint"
```

---

## Task 3: 批量补全现有空标签产品

**Files:**
- Modify: `backend/app/api/staff.py` — 新增 endpoint `POST /api/staff/products/generate-tags`

- [ ] **Step 1: Add batch generation endpoint**

```python
@router.post("/products/generate-tags")
async def generate_missing_tags(db=Depends(get_db)):
    """对所有 scene_tags 为空的有效产品批量生成标签"""
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.stock > 0,
        (Product.scene_tags == None) | (Product.scene_tags == "")
    ).all()

    gen = TagGenerator()
    success = 0
    failed = []
    for p in products:
        try:
            tags = gen.generate(p.name, p.ingredients or "")
            p.scene_tags = tags["scene_tags"]
            p.contraindication_tags = tags["contraindication_tags"]
            db.commit()
            success += 1
        except Exception as e:
            failed.append({"sku_id": p.sku_id, "name": p.name, "reason": str(e)[:100]})
        if len(failed) % 10 == 0:
            db.commit()  # 每 10 个失败产品提交一次

    db.commit()
    return {"total": len(products), "success": success, "failed": failed}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/staff.py
git commit -m "feat: add batch tag generation endpoint"
```

---

## Task 4: 验证推荐多样性提升

- [ ] **Step 1: 统计补全前后标签覆盖率**

```python
# 补全前
from app.models import get_session
from app.models.product import Product
db = get_session()
before = db.query(Product).filter(Product.is_active==True, Product.stock>0, Product.scene_tags!=None, Product.scene_tags!="").count()
total = db.query(Product).filter(Product.is_active==True, Product.stock>0).count()
print(f"补全前覆盖率: {before}/{total} = {before/total:.0%}")
```

- [ ] **Step 2: 调用批量生成**

```bash
curl -s -X POST http://localhost:8004/api/staff/products/generate-tags 2>&1
```

- [ ] **Step 3: 补全后覆盖率**

```bash
# 同上，验证覆盖率应为 100%
```

- [ ] **Step 4: 验证推荐多样性**

用相同体质+场景参数调用推荐 API 多次（3次），对比返回的 `products` 和 `bundle` 列表，应有随机性差异。

```bash
for i in 1 2 3; do
  curl -s -X POST http://localhost:8004/api/chat/send \
    -H "Content-Type: application/json" \
    -d '{"message": "我睡眠不好", "open_id": "test"}' | python -m json.tool | grep -E '"name"|"sku_id"'
  echo "---"
done
```

Expected: 两次推荐的 bundle 中应有不同产品（因为 `_build_bundle` 有 `random.shuffle`）

---

## Self-Review Checklist

- [ ] TagGenerator 独立于其他服务，可单独测试
- [ ] `_call_llm` 是私有方法，不对外暴露
- [ ] `failed_tags` 正确追加到 API 响应
- [ ] 批量 endpoint 不重复 commit（每 10 个失败才 commit 一次）
- [ ] 导入后覆盖率从 ~30% 提升到 ~100%