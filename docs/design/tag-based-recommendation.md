# 标签驱动的智能推荐系统

Date: 2026-05-23
Status: 设计中

## 核心逻辑

```
顾客对话 → 体质锁定 + 困扰提取
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
固定套餐(全部)      AI语义理解困扰
体质专属必推        ↓
                 标签匹配(2-3件)
                 scene_tags搜索
                     ↓
    ┌─────────┴─────────┐
    ↓                   ↓
  合并推荐(4-6件) ← 禁忌过滤
                     ↓
              优先输出：套餐在前，标签匹配在后
```

## 三步推荐流程

### Step 1: 固定套餐（已有，不需要改）

从 `constitution_bundles` 表读取该体质的固定套餐，后台配了几件就推几件。

### Step 2: 双层标签匹配（新增）

**为什么需要两层？** 标签可能是口语（"睡眠不好"），AI 可能输出术语（"失眠"），单层匹配会漏。

```
顾客说"睡眠不好"
  ↓
第一层（直接匹配）：用"睡眠"原词搜 scene_tags → 命中"睡眠不好""改善睡眠"
第二层（AI 语义）：LLM 理解 → "失眠,安神,盗汗,阴虚火旺" → 补充搜索
  ↓
合并去重，直接匹配的排前面
```

#### 第一层：直接关键词匹配（无 LLM）

```python
def _direct_match(scene_input, exclude_skus, limit=4):
    """直接用顾客原话中的词匹配 scene_tags"""
    # 从顾客原话提取有意义的词（去掉停用词）
    words = extract_keywords(scene_input)  # "睡眠不好" → ["睡眠", "不好"]
    for product in all_products:
        score = sum(1 for w in words if w in product.scene_tags)
        if score > 0 and product.sku_id not in exclude_skus:
            yield (score, product)
```

#### 第二层：AI 语义理解后匹配（1 次 LLM）

**LLM prompt**：
```
顾客困扰：睡眠不好，半夜总是醒，醒了就睡不着

请将顾客的困扰映射为 3-5 个调理方向/症状关键词。注意：
- 同时输出口语和术语，比如「睡眠不好」和「失眠」都要有
- 用逗号分隔，只输出关键词

示例输出：睡眠不好,失眠,安神,助眠,盗汗,阴虚火旺
```

```python
def _ai_match(scene_input, exclude_skus, limit=3):
    """LLM 语义理解后匹配"""
    keywords = llm_extract_keywords(scene_input)
    for product in all_products:
        score = sum(1 for kw in keywords if kw in product.scene_tags)
        if score > 0 and product.sku_id not in exclude_skus:
            yield (score, product)
```

#### 合并

```python
def match_by_tags(scene_input, exclude_skus, total=6):
    direct = list(_direct_match(scene_input, exclude_skus))
    ai = list(_ai_match(scene_input, exclude_skus + [p.sku_id for _,p in direct]))
    
    # 直接匹配排前面，AI 匹配排后面
    return [p for _,p in sorted(direct, key=lambda x: -x[0])][:3] + \
           [p for _,p in sorted(ai, key=lambda x: -x[0])][:3]
```

### Step 3: 禁忌过滤（新增）

根据筛查结果排除：
- `screening_result == "blocked"` → 不推荐任何产品
- 筛查出"备孕/怀孕/哺乳" → 排除 `contraindication_tags` 含"孕妇/备孕/哺乳"的产品
- 筛查出"处方药" → 排除含"药物相互作用"的产品

## 推荐结果结构

```json
{
  "constitution": {"constitution_type": "阴虚质"},
  "fixed_bundle": [
    {"name": "百合山药吐司", "role": "core", "reason": "阴虚质核心推荐"},
    {"name": "石斛麦冬茶", "role": "core", "reason": "阴虚质核心推荐"}
  ],
  "tag_matched": [
    {"name": "酸枣仁安神饼干", "role": "match", "reason": "匹配「失眠」「安神」"},
    {"name": "桑葚枸杞茶", "role": "match", "reason": "匹配「盗汗」「滋阴」"}
  ],
  "excluded": []  // 被禁忌过滤掉的产品
}
```

## 改动清单

| 文件 | 改动 | 行数 |
|------|------|------|
| `recommend_engine.py` | 新增 `_ai_extract_keywords()` LLM调用 | ~30行 |
| `recommend_engine.py` | 新增 `_match_by_tags()` 标签匹配 | ~25行 |
| `recommend_engine.py` | 新增 `_filter_by_contraindication()` 禁忌过滤 | ~20行 |
| `recommend_engine.py` | 修改 `recommend()` 整合三步流程 | ~15行 |
| `chat.py` | 传递 `screening_result` 给推荐引擎 | ~5行 |

总改动约 100 行，集中在 `recommend_engine.py`。

## 前端展示

推荐卡片按角色分组：
```
【专属推荐】← 固定套餐
  百合山药吐司 - 阴虚质核心推荐
  石斛麦冬茶 - 阴虚质核心推荐

【根据你的困扰「睡眠不好」特别推荐】← 标签匹配
  酸枣仁安神饼干 - 安神助眠
  桑葚枸杞茶 - 滋阴润燥
```
