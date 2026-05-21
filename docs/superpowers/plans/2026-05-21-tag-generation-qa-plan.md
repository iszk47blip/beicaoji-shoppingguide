# RecommendEngine QA Test Plan

**Date:** 2026-05-21
**Feature:** TagGenerator fix + batch generation (100% coverage achieved)
**Backend:** http://localhost:8000

## Prior Learnings
- Previous context: only ~54/317 products were ever recommended; 219 had empty `scene_tags`/`contraindication_tags`
- Root cause: `TagGenerator._call_llm` failed to handle `ThinkingBlock` from MiniMax-M2.7 model
- Fix: Added `thinking={"type": "disabled"}` + regex JSON extraction from `TextBlock`
- Batch completed: 59/59 products tagged, final coverage 252/252 (100%)

---

## Test Plan

### 1. API Health Check
**Test:** `GET /api/staff/products`
- Verify total products = 317 (all products) or 252 (active+stock)
- Verify `scene_tags` and `contraindication_tags` fields present in response

### 2. Tag Coverage Verification
**Test:** `GET /api/staff/products?stock_zero=true`
- Count products where `scene_tags` is null or empty
- Expected: 0 products with empty tags (100% coverage)

### 3. Recommend Engine Diversity (Critical Test)
**Test:** `POST /api/chat/send` with various symptoms
- Input A: `"我最近总是睡不好，容易醒"` → verify recommendations span multiple categories
- Input B: `"总是觉得累，不想说话"` → verify recommendations span multiple categories
- Input C: `"最近消化不好，胀气"` → verify recommendations span multiple categories
- **Expected:** Recommendations should NOT be dominated by a single category (e.g., biscuits/tea)
- **Baseline:** Previously only biscuits (饼干) and tea (茶) appeared due to empty tags

### 4. Tag Generation Integration
**Test:** `POST /api/staff/products/generate-tags`
- Send request to regenerate tags
- Verify response shows `success` count and `failed` count
- Verify tags are populated after call

### 5. Import with Auto-Tagging
**Test:** Upload a small test Excel with one product
- Verify tags are auto-generated on import
- Verify `failed_tags` is tracked correctly

### 6. Regression: Existing Recommendation Tests
**Test:** `pytest backend/tests/test_recommend_engine.py`
- Verify `test_recommend_bundle_cross_category` still passes
- Verify no new console errors in staff-admin page

---

## Success Criteria
- [ ] All 6 tests pass
- [ ] Recommendation diversity confirmed (≥3 categories per query)
- [ ] Zero products with empty `scene_tags` in active+stock set
- [ ] `test_recommend_engine.py` passes with no modifications needed