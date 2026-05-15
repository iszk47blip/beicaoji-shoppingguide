let _items = [];
let _listeners = [];

function notify() {
  const state = { items: [..._items], count: count(), total: total() };
  _listeners.forEach(fn => fn(state));
}

function add(product) {
  const item = _items.find(i => i.sku_id === product.sku_id);
  if (item) {
    if (item.quantity < 99) item.quantity++;
  } else {
    _items.push({
      sku_id: product.sku_id,
      name: product.name,
      category: product.category || '',
      ingredients: product.ingredients || '',
      price: product.price || 0,
      quantity: 1
    });
  }
  notify();
}

function remove(skuId) {
  _items = _items.filter(i => i.sku_id !== skuId);
  notify();
}

function setQuantity(skuId, qty) {
  if (qty < 1) {
    remove(skuId);
    return;
  }
  if (qty > 99) qty = 99;
  const item = _items.find(i => i.sku_id === skuId);
  if (item) {
    item.quantity = qty;
  }
  notify();
}

function getQuantity(skuId) {
  const item = _items.find(i => i.sku_id === skuId);
  return item ? item.quantity : 0;
}

function count() {
  return _items.reduce((s, i) => s + i.quantity, 0);
}

function total() {
  return _items.reduce((s, i) => s + (i.price || 0) * i.quantity, 0);
}

function getItems() {
  return [..._items];
}

function clear() {
  _items = [];
  notify();
}

function subscribe(fn) {
  _listeners.push(fn);
}

function unsubscribe(fn) {
  _listeners = _listeners.filter(f => f !== fn);
}

module.exports = { add, remove, setQuantity, getQuantity, count, total, getItems, clear, subscribe, unsubscribe };
