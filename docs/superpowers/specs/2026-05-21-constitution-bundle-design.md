# 体质套餐管理与智能推荐设计

## Overview

两个关联需求：
1. **体质固定套餐后台管理** — 店员可在后台为每种体质配置固定产品套餐
2. **智能推荐流程** — LLM 基于顾客对话上下文补充推荐，与固定套餐去重后展示

## 背景

现有问题：
- 顾客问"你都有什么产品"时，展示按体质分类的套餐（气虚质/阳虚质/阴虚质/湿热质）→ 不符合顾客心理预期，他想要的是"有什么好产品"而不是"我是什么体质"
- 体质辨识后的产品推荐只有固定套餐，缺少根据顾客实际情况的个性化补充

## 设计决策

### 决策 1：「你都有什么产品」展示什么
- 展示**店家主推产品**（hot products），不展示体质分类
- 由后台运营人员维护一个"主推列表"（固定 3~6 款）
- 销售顾问角色直接推荐，带动转化率

### 决策 2：体质套餐数据结构
- 每种体质（气虚质/阳虚质/阴虚质/湿热质）对应一个套餐
- 套餐内容：商品 SKU 列表 + 描述语
- 数据存在数据库，店员可在 staff-admin 后台修改
- 固定套餐作为主推款，LLM 补充推荐在此基础上"锦上添花"

### 决策 3：LLM 补充推荐逻辑
- 基于**对话全程上下文**（体质描述 + 口味偏好）推理推荐
- 去重：与固定套餐中已有的 SKU 过滤后展示
- 数量：由 LLM 自己判断（信任 LLM 的判断），建议上限 3~4 款以免推荐列表过长

## 数据模型

### 方案 A（推荐）：新增 `constitution_bundle` 表
```sql
CREATE TABLE constitution_bundle (
    id INTEGER PRIMARY KEY,
    constitution_type VARCHAR(20) NOT NULL,  -- 气虚质/阳虚质/阴虚质/湿热质
    sku_id VARCHAR(20) NOT NULL,
    sort_order INTEGER DEFAULT 0,
    description VARCHAR(200),  -- 可选：这款产品的推荐语
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(constitution_type, sku_id)
);

CREATE TABLE hot_product (
    id INTEGER PRIMARY KEY,
    sku_id VARCHAR(20) NOT NULL UNIQUE,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

优势：清晰、便于店员管理、与商品解耦

### 方案 B：扩展 Product 模型
在 Product 模型加 `constitution_bundle` JSON 字段。

劣势：修改商品时容易误伤套餐内容、数据不独立

## API 设计

### 体质套餐管理
- `GET /api/staff/constitution-bundles` — 获取所有体质套餐
- `PUT /api/staff/constitution-bundles/:type` — 整体替换某体质套餐（传入 sku_id 列表 + 描述语）
- `PATCH /api/staff/constitution-bundles/:type/products` — 单个添加/删除套餐内商品

### 主推产品管理
- `GET /api/staff/hot-products` — 获取主推列表
- `PUT /api/staff/hot-products` — 整体替换主推列表
- `PATCH /api/staff/hot-products/reorder` — 调整顺序

### 推荐流程（chat.py 修改）
```
用户问"你都有什么产品"
  → 返回 hot_products 列表（主推款）

体质辨识完成，进入 RECOMMEND
  1. 查询固定套餐（constitution_bundle 表）
  2. LLM 基于对话上下文 + 固定套餐内容 → 生成补充推荐（去重后）
  3. 合并展示：固定套餐产品 + LLM 推荐产品
```

## 推荐展示字段
```json
{
  "fixed_bundle": [
    {"name": "...", "sku_id": "...", "category": "...", "price": ..., "ingredients": "...", "reason": "固定套餐说明"}
  ],
  "llm_recommendations": [
    {"name": "...", "sku_id": "...", "category": "...", "price": ..., "ingredients": "...", "reason": "LLM个性化推荐原因"}
  ],
  "total_count": N
}
```

## Staff Admin 后台页面

在现有 staff-admin.html 增加两个 Tab：
- **主推管理** — 表格展示主推产品，支持增删、拖拽排序
- **体质套餐** — 四个体质 tab（气虚质/阳虚质/阴虚质/湿热质），每个 tab 下展示关联产品，支持增删

## 暂不实现（后续）
- LLM 推荐理由的个性化文案生成（直接用固定文案）
- 口味偏好提取（依赖对话流中收集）
- 主推产品的浏览量/销量排序