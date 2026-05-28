# P1 & P2 详细设计

Date: 2026-05-23

---

## P1：对话两阶段快速定位

### 现状

对话流程中，体质判断走的是固定 5 字段逐一询问：

```
问寒热 → 问上火 → 问气虚 → 问湿热 → 问出汗
```

问题：
1. 只覆盖 5 种体质信号，10 种体质无法区分
2. 每个问题与顾客的回答无关，像做问卷
3. 10 种体质全问完需要 5+ 轮，顾客没耐心
4. 不会根据已有信息缩小范围

### 目标

**最多 3 个问题锁定体质（含开放描述），覆盖全部 10 种体质。**

### 方案：信号提取 + 候选集缩小

#### 阶段一：开放描述（1 轮）

顾客自由描述身体感受 → LLM 提取信号 → 映射到候选体质。

```
顾客: "最近总觉得累，消化不好，肚子胀"
        ↓ LLM 信号提取
{ qi_deficiency: 0.8, dampness: 0.7, digestion: "腹胀" }
        ↓ 信号映射
候选: [气虚质(80%), 痰湿质(70%), 平和质(20%)]
```

**关键改动**：不再让 LLM 映射到固定字段选项，而是输出信号向量（0-1 概率），代码层映射到体质。

#### 阶段二：鉴别追问（1-2 轮）

在 2-3 个候选体质之间做最小化鉴别。

```
候选: [气虚质, 痰湿质]
鉴别问题: "你平时是怕冷多一点，还是觉得身体沉、肚子胀更多一点？"
         ↑ 气虚→怕冷           ↑ 痰湿→体沉腹胀

顾客答"身体沉" → 痰湿质概率升至 90% → 锁定
```

如果候选概率接近（如 45% vs 40%），再问一轮；否则直接取最高。

#### 终止条件

- 某个体质概率 ≥ 80% → 直接锁定
- 已问 3 轮（含开放描述）→ 取最高概率
- 顾客说"都还好/不知道" → 归为平和质

### 实现改动

**`dialogue_engine.py` 新增方法：**

```python
def _extract_constitution_signals(self, user_input: str) -> dict:
    """从自由描述提取 10 体质信号向量，返回 {体质类型: 概率}"""
    # LLM prompt: 输出 JSON {"气虚质": 0.8, "痰湿质": 0.6, ...}
    # 只输出概率 > 0.3 的体质

def _narrow_candidates(self, signals: dict) -> list:
    """信号映射为候选体质列表，按概率降序"""
    # 取 top 3，概率归一化

def _ask_differential_question(self, candidates: list, ctx: str) -> str:
    """根据 2-3 个候选体质生成鉴别问题"""
    # LLM prompt: "顾客可能偏 A 质或 B 质，请想一个自然的问题来区分"
    # 问题必须让顾客容易回答（二选一），不能是中医术语

def _lock_constitution(self, candidates: list, user_input: str) -> dict:
    """根据鉴别回答更新候选概率，锁定最终体质"""
    # LLM 判断回答更支持哪个候选
```

**`_handle_constitution` 流程改为：**

```
if 首次进入:
    return 开放描述("最近身体感觉怎么样？")
elif 开放描述已回复:
    signals = _extract_signals(user_input)
    if max(signals) >= 0.8:  # 高置信度直接锁定
        return _confirm_and_proceed(signals)
    else:
        candidates = _narrow_candidates(signals)
        return _ask_differential_question(candidates)
elif 鉴别已回答:
    locked = _lock_constitution(candidates, user_input)
    return _confirm_and_proceed(locked)
```

### 新增文件

不需要新增文件，改动集中在 `dialogue_engine.py`，约 150-200 行。

### 风险

| 风险 | 缓解 |
|------|------|
| LLM 信号提取不准 | 信号只做初筛，鉴别追问做二次确认 |
| 鉴别问题太专业 | prompt 要求用日常语言，不出现中医术语 |
| 体质标签错误 | 后台允许店员手动修正（后续 P3） |

---

## P2：套餐角色标记 + 推荐引擎联动

### 现状

套餐就是一个产品列表，没有结构。推荐引擎 `recommend_engine.py` 不读套餐，自己算。

### 目标

1. 套餐产品有角色（核心/搭配/锦上添花）
2. 推荐引擎读取套餐池，结合顾客困扰做二次筛选
3. AI 推荐文案体现角色差异

### 方案

#### 套餐角色定义

| 角色 | sort_order | 含义 | 对话中怎么用 |
|------|-----------|------|-------------|
| 核心 | 1-2 | 直接针对该体质的产品 | AI 重点介绍："特别适合你的有这两款..." |
| 搭配 | 3-5 | 关联或互补产品 | AI 顺带推荐："另外搭配这个效果更好..." |
| 锦上添花 | 6-7 | 应季/香囊/礼盒 | AI 附加："还有一个很适合送人/自用..." |

#### 推荐引擎改造

**`recommend_engine.py` 当前逻辑：**
- 根据 constitution_raw + scene_raw 独立匹配产品
- 不读套餐池
- 输出不分角色

**改为：**

```python
def recommend(self, constitution_type: str, scene: str, bundle_pool: dict) -> dict:
    """
    constitution_type: 已锁定的体质类型（如 "痰湿质"）
    scene: 顾客困扰（如 "消化不好，肚子胀"）
    bundle_pool: 该体质的套餐池 {core: [...], side: [...], delight: [...]}
    """
    # 1. 核心产品直接取套餐池（保证一致性）
    core = bundle_pool.get('core', [])[:2]

    # 2. 搭配产品根据 scene 在套餐池内筛选
    side = self._filter_by_scene(bundle_pool.get('side', []), scene)[:2]

    # 3. 锦上添花取套餐池第一件
    delight = bundle_pool.get('delight', [])[:1]

    return {
        'constitution_type': constitution_type,
        'core_bundle': core,
        'side_bundle': side,
        'delight': delight,
        'explanation': self._generate_explanation(constitution_type, core, scene)
    }
```

#### 后端 API 改动

套餐 GET 接口返回增加 role 字段：

```json
{
  "气虚质": [
    {"sku_id": "...", "sort_order": 1, "role": "core", "name": "..."},
    {"sku_id": "...", "sort_order": 3, "role": "side", "name": "..."}
  ]
}
```

`staff.py` 的 `get_constitution_bundles` 加 3 行：根据 sort_order 自动标注 role。

#### 对话中体现角色

AI 推荐文案改为三段式：

```
小张你好～你是偏痰湿体质，消化不好、肚子胀都和它有关。

【核心推荐】
薏仁茯苓吐司 — 薏仁+茯苓化痰祛湿，每天早上来两片
鸡内金山楂饼干 — 山楂消食，鸡内金助消化

【搭配建议】
陈皮木樨茶 — 搭配着喝，陈皮理气祛湿效果更好

【锦上添花】
安神浮梦香囊 — 放枕边帮你安稳入睡
```

### 改动范围

| 文件 | 改动 | 行数 |
|------|------|------|
| `recommend_engine.py` | 读套餐池 + 按角色筛选 + 三段式文案 | ~60 行 |
| `dialogue_engine.py` | P1 的 constitution 结果传给推荐引擎 | ~20 行 |
| `chat.py` | 推荐时查询套餐池传给引擎 | ~15 行 |
| `staff.py` | 套餐 GET 接口加 role 字段 | ~5 行 |
| `staff-admin.html` | 套餐编辑器显示角色标签 | ~30 行 |

---

## 实施顺序

```
P1 first（对话体验 → 体质锁定准确）
  ↓
P2 second（套餐角色 → 推荐质量提升）
  ↓
P3 later（店员修正体质 + 套餐效果数据追踪）
```

P1 是基础——只有快速准确地锁定体质，后续的套餐推荐才有意义。P2 在 P1 之上让推荐更结构化、更可运营。
