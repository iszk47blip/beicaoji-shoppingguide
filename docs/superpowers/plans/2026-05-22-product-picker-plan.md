# 商品选择器 Slide-over 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `staff-admin.html` 中实现一个 Slide-over 选择器面板，支持多选+搜索+分类筛选，共用于主推产品和体质套餐两个场景

**Architecture:**
- 单一 `<div id="productPicker">` Slide-over 面板，通过 JS 闭包管理状态
- 调用时传入 `alreadySelectedSkuIds[]`（已选 sku 列表）+ `onAdd(items[])` 回调
- 面板内实时搜索 `/api/staff/products?q=xxx&category=yyy`，分页加载
- 已选商品显示已勾选状态，Checkbox 禁用（保留在列表里便于确认）

**Tech Stack:** Vanilla JS + CSS, existing API, no new dependencies

---

## 文件结构

- **Modify:** `backend/app/staff-admin.html` — 新增 Slide-over 面板 HTML/CSS/JS
- **Modify:** `backend/app/api/staff.py` — `hot-products` 和 `bundle` 的 add/remove API 无需改动（已有）

---

## Task 1: Slide-over 面板 HTML + CSS

**Files:**
- Modify: `backend/app/staff-admin.html` — 在 `</body>` 前添加面板 HTML，在 `<style>` 中添加面板 CSS

- [ ] **Step 1: 添加面板 HTML**

在 `staff-admin.html` 末尾 `</body>` 前添加：

```html
<!-- Product Picker Slide-over -->
<div id="productPicker" class="picker-overlay" onclick="closePickerOnOverlay(event)">
  <div class="picker-panel">
    <div class="picker-header">
      <span class="picker-title">选择商品</span>
      <button class="btn btn-ghost btn-icon picker-close" onclick="closeProductPicker()">✕</button>
    </div>
    <div class="picker-toolbar">
      <input type="text" id="pickerSearch" class="picker-search" placeholder="搜索商品名称/条码..." oninput="onPickerSearchInput()">
      <div id="pickerCategoryPills" class="picker-pills"></div>
    </div>
    <div id="pickerResults" class="picker-results">
      <div class="picker-loading">加载中…</div>
    </div>
    <div class="picker-footer">
      <span id="pickerSelectedCount">已选 0 件</span>
      <button class="btn btn-primary" id="pickerConfirmBtn" onclick="confirmPickerSelection()" disabled>确认添加 →</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: 添加面板 CSS**

在 `staff-admin.html` 末尾的 `<style>` 块之前添加：

```css
/* Product Picker Slide-over */
.picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 1000;
  display: none;
  align-items: flex-end;
  justify-content: flex-end;
}
.picker-overlay.show {
  display: flex;
}
.picker-panel {
  width: 480px;
  max-width: 100vw;
  height: 100vh;
  background: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0,0,0,0.12);
  animation: slideIn 0.2s ease-out;
}
@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}
.picker-title { font-size: 16px; font-weight: 600; color: #333; }
.picker-close { font-size: 18px; color: #888; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 4px; }
.picker-close:hover { background: #f5f5f5; }
.picker-toolbar {
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.picker-search {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}
.picker-pills {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.picker-pills::-webkit-scrollbar { height: 0; }
.ppicker-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
  background: #f0f0f0;
  color: #666;
}
.ppicker-pill.active { background: #2d7d46; color: #fff; }
.picker-results {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.picker-loading {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 14px;
}
.picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.picker-item:hover { background: #f8f8f8; }
.picker-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.picker-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.picker-item.disabled input { cursor: not-allowed; }
.picker-item-info { flex: 1; min-width: 0; }
.picker-item-name {
  font-size: 14px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.picker-item-meta {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.picker-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-top: 1px solid #eee;
  background: #fafafa;
}
#pickerSelectedCount { font-size: 13px; color: #666; }
```

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/staff-admin.html
git commit -m "feat(staff-admin): add product picker slide-over HTML/CSS"
```

---

## Task 2: 面板 JS 逻辑

**Files:**
- Modify: `backend/app/staff-admin.html` — 在 `<script>` 末尾添加面板 JS

- [ ] **Step 1: 添加 picker 状态管理变量**

在 `staff-admin.html` 的 `<script>` 顶部（API const 下方）添加：

```javascript
// Product Picker state
let _pickerCallback = null;          // function(items: [{sku_id, name, category, price}])
let _pickerSelected = [];             // [{sku_id, name, category, price}]
let _pickerAllProducts = [];         // current page loaded
let _pickerSearch = "";
let _pickerCategory = "";
let _pickerDebounceTimer = null;
let _pickerPage = 1;
let _pickerHasMore = true;
let _pickerLoading = false;
```

- [ ] **Step 2: 添加 picker 核心函数**

在 `<script>` 末尾添加：

```javascript
// ── Product Picker ──────────────────────────────────────────

async function openProductPicker(callback, alreadySelectedSkuIds) {
  _pickerCallback = callback;
  _pickerSelected = (alreadySelectedSkuIds || []).map(sku => ({ sku_id: sku }));
  document.getElementById('pickerSearch').value = '';
  document.getElementById('pickerResults').innerHTML = '<div class="picker-loading">加载中…</div>';
  document.getElementById('pickerSelectedCount').textContent = '已选 0 件';
  document.getElementById('pickerConfirmBtn').disabled = true;
  document.getElementById('pickerCategoryPills').innerHTML = '';
  _pickerSearch = '';
  _pickerCategory = '';
  _pickerPage = 1;
  _pickerHasMore = true;
  // Load categories for pills
  loadPickerCategories();
  // Load first page
  await loadPickerProducts(true);
  document.getElementById('productPicker').classList.add('show');
}

function closeProductPicker() {
  document.getElementById('productPicker').classList.remove('show');
  _pickerCallback = null;
  _pickerSelected = [];
}

function closePickerOnOverlay(e) {
  if (e.target.id === 'productPicker') closeProductPicker();
}

async function loadPickerCategories() {
  const data = await api('/categories');
  const pills = document.getElementById('pickerCategoryPills');
  pills.innerHTML = '<span class="ppicker-pill active" onclick="setPickerCategory(\'\')">全部</span>';
  (data.categories || []).forEach(cat => {
    pills.innerHTML += `<span class="ppicker-pill" onclick="setPickerCategory(\'${cat}\')">${cat}</span>`;
  });
}

function setPickerCategory(cat) {
  _pickerCategory = cat;
  _pickerPage = 1;
  _pickerHasMore = true;
  document.querySelectorAll('.ppicker-pill').forEach(el => {
    el.classList.toggle('active', el.textContent === (cat || '全部'));
  });
  loadPickerProducts(true);
}

function onPickerSearchInput() {
  clearTimeout(_pickerDebounceTimer);
  _pickerDebounceTimer = setTimeout(() => {
    _pickerSearch = document.getElementById('pickerSearch').value.trim();
    _pickerPage = 1;
    _pickerHasMore = true;
    loadPickerProducts(true);
  }, 300);
}

async function loadPickerProducts(reset) {
  if (_pickerLoading) return;
  if (!reset && !_pickerHasMore) return;
  if (reset) {
    _pickerAllProducts = [];
    _pickerPage = 1;
  }
  _pickerLoading = true;
  const params = new URLSearchParams({ page: _pickerPage, page_size: 50 });
  if (_pickerSearch) params.set('q', _pickerSearch);
  if (_pickerCategory) params.set('category', _pickerCategory);
  const data = await api('/products?' + params.toString());
  const products = data.products || [];
  if (reset) {
    _pickerAllProducts = products;
    document.getElementById('pickerResults').innerHTML = '';
  } else {
    _pickerAllProducts.push(...products);
  }
  _pickerHasMore = products.length === 50;
  _pickerPage++;
  _pickerLoading = false;
  renderPickerItems();
  // Setup infinite scroll
  setupPickerScroll();
}

function renderPickerItems() {
  const container = document.getElementById('pickerResults');
  const selectedSkus = new Set(_pickerSelected.map(i => i.sku_id));
  container.innerHTML = _pickerAllProducts.map(p => {
    const isSelected = selectedSkus.has(p.sku_id);
    const isDisabled = isSelected;
    return `<div class="picker-item${isDisabled ? ' disabled' : ''}" data-sku="${p.sku_id}" onclick="togglePickerItem('${p.sku_id}')">
      <input type="checkbox"${isSelected ? ' checked' : ''}${isDisabled ? ' disabled' : ''} onclick="event.stopPropagation();togglePickerItem('${p.sku_id}')">
      <div class="picker-item-info">
        <div class="picker-item-name">${p.name || p.sku_id}</div>
        <div class="picker-item-meta">${p.category || ''} ${p.price ? '· ¥' + p.price : ''} ${p.stock !== undefined ? '· 库存' + p.stock : ''}</div>
      </div>
    </div>`;
  }).join('');
  if (!_pickerAllProducts.length) {
    container.innerHTML = '<div class="picker-loading">未找到商品</div>';
  }
}

function togglePickerItem(sku) {
  const product = _pickerAllProducts.find(p => p.sku_id === sku);
  if (!product) return;
  const idx = _pickerSelected.findIndex(i => i.sku_id === sku);
  if (idx >= 0) {
    _pickerSelected.splice(idx, 1);
  } else {
    _pickerSelected.push({ sku_id: product.sku_id, name: product.name, category: product.category, price: product.price });
  }
  updatePickerUI();
}

function updatePickerUI() {
  const count = _pickerSelected.length;
  document.getElementById('pickerSelectedCount').textContent = `已选 ${count} 件`;
  document.getElementById('pickerConfirmBtn').disabled = count === 0;
  // Update checkbox states without full re-render
  _pickerSelected.forEach(item => {
    const row = document.querySelector(`.picker-item[data-sku="${item.sku_id}"]`);
    if (row) {
      row.querySelector('input').checked = true;
      row.classList.add('disabled');
      row.querySelector('input').disabled = true;
    }
  });
}

function setupPickerScroll() {
  const el = document.getElementById('pickerResults');
  if (el.dataset.bound) return;
  el.dataset.bound = '1';
  el.addEventListener('scroll', () => {
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 100) {
      if (!_pickerLoading && _pickerHasMore) loadPickerProducts(false);
    }
  });
}

function confirmPickerSelection() {
  if (!_pickerCallback || !_pickerSelected.length) return;
  const items = _pickerSelected.map(i => ({ ...i }));
  closeProductPicker();
  _pickerCallback(items);
}
```

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/staff-admin.html
git commit -m "feat(staff-admin): add product picker slide-over JS logic"
```

---

## Task 3: 主推产品 Tab 接入选择器

**Files:**
- Modify: `backend/app/staff-admin.html` — 修改 `#hotProductsView` 工具栏，替换"添加"按钮

- [ ] **Step 1: 修改主推产品工具栏**

Read: `backend/app/staff-admin.html` around line 680-695

找到：
```html
<select id="addHotProductSelect" style="flex:1;padding:6px 10px...">
```
替换为：
```html
<button class="btn btn-secondary" onclick="openHotProductPicker()">+ 添加商品</button>
```

找到 `addHotProduct()` 函数（大约 line 1429），改为：

```javascript
function openHotProductPicker() {
  const alreadySkus = window._hotProducts ? window._hotProducts.map(p => p.sku_id) : [];
  openProductPicker(async function(items) {
    for (const item of items) {
      await addHotProductItem(item);
    }
    loadHotProducts();
  }, alreadySkus);
}

async function addHotProductItem(item) {
  await fetch(API + '/hot-products', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ products: [...(window._hotProducts || []), { sku_id: item.sku_id, sort_order: (window._hotProducts || []).length }].map(p => ({ sku_id: p.sku_id, sort_order: p.sort_order || 0 })) })
  });
}
```

找到 `loadHotProducts()`，在数据加载后将结果存入 `window._hotProducts`：

```javascript
function loadHotProducts() {
  fetch(API + '/hot-products').then(r => r.json()).then(data => {
    window._hotProducts = data;
    renderHotProducts(data);
  });
}
```

- [ ] **Step 2: 测试**

访问 `http://127.0.0.1:8004/staff-admin`，切换到主推产品 Tab，点击"+ 添加商品"，验证 Slide-over 面板正常弹出、搜索/分类/多选/确认流程。

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/staff-admin.html
git commit -m "feat(staff-admin): wire hot products picker to slide-over panel"
```

---

## Task 4: 体质套餐 Tab 接入选择器

**Files:**
- Modify: `backend/app/staff-admin.html` — 修改体质套餐工具栏

- [ ] **Step 1: 修改体质套餐添加按钮**

Read: `backend/app/staff-admin.html` around line 1485-1490

找到 `addBundleSelect-${type}` 下拉框和按钮，替换为：

```html
<button class="btn btn-secondary" onclick="openBundlePicker('${type}')">+ 添加商品</button>
```

找到 `addBundleItem(type)` 函数，替换为：

```javascript
function openBundlePicker(type) {
  const existing = window._bundles && window._bundles[type] ? window._bundles[type] : [];
  const alreadySkus = existing.map(p => p.sku_id);
  openProductPicker(async function(items) {
    for (const item of items) {
      await addBundleItemToType(type, item);
    }
    loadBundles();
  }, alreadySkus);
}

async function addBundleItemToType(type, item) {
  // Append to existing bundle items for this type
  const current = window._bundles && window._bundles[type] ? [...window._bundles[type]] : [];
  current.push({ sku_id: item.sku_id, sort_order: current.length });
  await fetch(API + '/constitution-bundles/' + type, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: current.map(p => ({ sku_id: p.sku_id, sort_order: p.sort_order || 0 })) })
  });
}
```

- [ ] **Step 2: 测试**

切换到体质套餐 Tab，点击某一类型的"+ 添加商品"，验证面板正常弹出。

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/staff-admin.html
git commit -m "feat(staff-admin): wire constitution bundle picker to slide-over panel"
```

---

## Task 5: 清理旧的下拉框代码

**Files:**
- Modify: `backend/app/staff-admin.html` — 移除旧的下拉框 DOM 和 JS

- [ ] **Step 1: 移除旧下拉框 DOM**

搜索 `addHotProductSelect` 和 `addBundleSelect`，删除对应的 `<select>` 元素。

- [ ] **Step 2: 移除旧的 loadAddHotProductSelect / loadBundleSelect 函数**

删除 `loadAddHotProductSelect()` 和相关的 `addHotProduct()` 中直接操作 select 的逻辑。

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/staff-admin.html
git commit -m "refactor(staff-admin): remove legacy select-based product pickers"
```

---

## 自检清单

1. **Spec 覆盖：**
   - [x] Slide-over 面板 HTML/CSS → Task 1
   - [x] 多选+搜索+分类筛选 JS 逻辑 → Task 2
   - [x] 已选商品显示已勾选+禁用 → Task 2 (togglePickerItem + updatePickerUI)
   - [x] 主推产品接入 → Task 3
   - [x] 体质套餐接入 → Task 4
   - [x] 旧下拉框清理 → Task 5

2. **Placeholder scan:** 无 TBD/TODO

3. **API 兼容性:** 直接复用现有 `/api/staff/products`（已有 q + category 参数）和 `/api/staff/hot-products` + `/api/staff/constitution-bundles/{type}`（已有 PUT 端点）

4. **性能:** 分页 50 条/页，滚动到底部自动加载下一页，无全量加载

---

## 执行方式

**1. Subagent-Driven (推荐)** — 每 task 派发独立 subagent，task 间 review，快速迭代

**2. Inline Execution** — 当前 session 内顺序执行，有 checkpoint

选择哪种？
