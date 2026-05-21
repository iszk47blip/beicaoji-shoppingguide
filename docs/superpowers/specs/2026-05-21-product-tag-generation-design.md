# 产品标签自动生成设计

## Status
- Date: 2026-05-21
- Branch: master
- Author: 焙草集 AI 销售助手团队

## 背景问题

317 个有效产品中，219 个（69%）的 `scene_tags` 和 `contraindication_tags` 为空。推荐系统依赖 `scene_tags` 过滤，导致每次推荐都局限在少数有标签的产品（饼干+茶，约 54 个）。用户反馈推荐结果单一，总是被推荐相同产品。

## 目标

在产品导入时自动生成 `scene_tags` 和 `contraindication_tags`，使全部 317 个产品进入推荐池，提升推荐多样性。

## 决策

| 项目 | 决策 |
|------|------|
| 触发方式 | 导入时自动生成（不手动触发） |
| 生成字段 | `scene_tags`（自由文本），`contraindication_tags`（自由文本） |
| 标签格式 | 自由文本，由 LLM 根据产品名称和成分自行判断 |
| 失败策略 | API 失败 → 等 5 秒重试一次 → 还失败 → 记录失败产品，导入成功，产品带空标签，响应附带失败列表供运营处理 |

## 架构设计

### 新增服务：TagGenerator

```
backend/app/services/tag_generator.py
```

职责：
1. 给定产品名称 + 成分 → 调用 LLM 生成 `scene_tags` 和 `contraindication_tags`
2. 对输入文本做自由文本标签生成，不使用固定枚举

Prompt 设计（SYSTEM）：
```
你是药食同源产品标签专家。根据产品信息生成场景标签和禁忌标签。

产品名称：{name}
成分：{ingredients}

要求：
- scene_tags：适合的场景或调理方向，用有意义的词描述，2-5 个，用逗号分隔
- contraindication_tags：禁忌或需慎用的情况，如"孕妇慎用"、"胃寒少吃"、"经期慎用"，用逗号分隔，无则写"无"

只输出一行 JSON：
{"scene_tags": "...", "contraindication_tags": "..."}
```

### 修改：data_importer.py

新增 `_generate_tags(product)` 方法：
- 调用 TagGenerator 生成标签
- 失败时重试一次（等待 5 秒）
- 还失败则记录到 failed列表

导入流程变化：
```
Excel 读取 → 数据验证 → 逐条导入 DB
                         ↓
              对于每条新记录（有 sku_id 且 tags 为空）：
                   ├→ TagGenerator.generate() → 写入 scene_tags + contraindication_tags
                   ├→ 失败一次 → 等待 5 秒 → 重试
                   └→ 还失败 → 记入 failed[]，产品正常导入成功，标签留空
                         ↓
              导入结果返回 {imported, updated, total, failed: [{sku_id, name, reason}]}
```

### TagGenerator 接口

```python
class TagGenerator:
    def generate(self, name: str, ingredients: str) -> dict:
        """Returns {"scene_tags": "...", "contraindication_tags": "..."}"""
        # 调用 LLM，解析 JSON 结果
        # 失败时抛出异常（让调用方处理重试）
```

### API 响应变化

`POST /api/staff/products/import` 响应新增 `failed_tags` 字段：

```json
{
  "imported": 10,
  "updated": 3,
  "total": 13,
  "failed": [],                          // 导入过程中数据库写入失败（保留原逻辑）
  "failed_tags": [                       // 新增：标签生成失败列表（供运营后续处理）
    {"sku_id": "A001", "name": "xxx产品", "reason": "LLM API 超时"}
  ]
}
```

## 数据流

```
Excel 文件
    ↓
data_importer.do_import()
    ↓
遍历每行 product
    ├→ validate_row()        → 数据校验
    ├→ upsert_product()      → 写入/更新 product 记录
    └→ _generate_tags()      → 如果 scene_tags 为空，触发标签生成
                                  ├→ TagGenerator.generate(name, ingredients)
                                  │     └→ LLM API 调用
                                  ├→ 失败 → sleep(5) → 重试
                                  └→ 还失败 → 记入 failed_tags[]，产品入库，标签为空
    ↓
返回 ImportResult(imported, updated, total, failed, failed_tags)
```

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| LLM API 超时/网络错误 | 等待 5 秒重试一次，仍失败记入 failed_tags |
| LLM 返回格式错误（JSON 解析失败） | 等 5 秒重试，仍失败记入 failed_tags |
| 产品本身数据缺失（无 name） | 跳过标签生成，导入时直接记录 failed |

## 待运营处理的工作流

`failed_tags` 不为空时，运营后台显示提醒：
- 提示有 N 个产品标签生成失败
- 运营可在产品列表中手动补充标签
- 或后续手动触发批量补全工具

## 验证方式

1. 导入前记录各品类有标签产品数量
2. 导入后对比：应覆盖全部 315 个 active 产品
3. 抽检：检查生成标签是否符合产品成分逻辑（如"山药"产品应匹配"补气"相关标签）
4. 推荐测试：用相同体质+场景组合，多次推荐，检查结果是否比原来更多样

## 实施顺序

1. 新建 `tag_generator.py`
2. 修改 `data_importer.py`，接入 TagGenerator
3. 修改 `POST /api/staff/products/import` 响应，添加 `failed_tags` 字段
4. 现有 219 个空标签产品：可通过重新导入同一 Excel 触发批量补全（需要先在 importer 里支持"跳过已有标签产品"逻辑）
5. 验证 + 推荐效果测试