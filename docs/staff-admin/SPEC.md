# Staff Admin - 库存管理后台

## Overview

简单 HTML 单页应用，给店员维护商品基础信息和库存。

## Tech

纯 HTML + Vanilla JS，无框架。直接调用 staff API。

## E2E Flow

1. 店员打开 `/staff-admin`
2. 左侧按分类列出商品列表，支持搜索商品名称、条码、成分
3. 点击商品编辑库存数字，回车或失焦自动保存
4. 支持多选批量修改库存（设为固定值或增减相对值）
5. 导入有赞 Excel 商品清单（自动去重）

## Routes

- `GET /staff-admin` → 渲染后台页面 (`backend/app/staff-admin.html`)
- `GET /api/staff/products` → 列表（支持分类筛选、stock_zero 筛选、搜索）
- `GET /api/staff/categories` → 分类列表
- `PATCH /api/staff/products/batch-stock-relative` → 批量更新库存（绝对值或相对值）
- `POST /api/staff/products/import` → 导入有赞 Excel，全量更新
- `GET /api/staff/products/selected?ids=id1,id2` → 查询选中商品用于确认

## 权限

无认证，局域网内使用。后续可加简单 PIN 保护。

## 已实现功能

- KPI 栏：全部 / 有库存 / 低库存 / 零库存 四个计数
- 分类标签栏：动态显示所有分类及商品数量
- 商品表格：名称、条码、分类、价格、成分、库存（可编辑）
- 搜索：按名称、条码、成分关键词搜索（实时 debounce）
- 库存编辑：失焦或回车触发 `/batch-stock-relative` 保存
- 批量操作：选择多个商品 → 批量设为固定值 或 批量增减
- 导入：拖拽或点击上传有赞 Excel，显示新增/更新/失败数量

## API Response Shape

### `GET /api/staff/products`
```json
{"total": 252, "products": [{"id":1,"sku_id":"...","name":"...","category":"...","price":0,"stock":9999,"is_active":true,"ingredients":null}]}
```

### `POST /api/staff/products/import`
```json
{"imported": 5, "updated": 10, "total": 15, "failed_tags": []}
```

### `PATCH /api/staff/products/batch-stock-relative`
```json
{"updated": 3, "items": [{"sku_id": "...", "stock": 10}]}
```