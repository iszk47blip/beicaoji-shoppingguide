const STORAGE_KEY = 'orders';

function getAll() {
  try {
    return wx.getStorageSync(STORAGE_KEY) || [];
  } catch (e) {
    return [];
  }
}

function add(order) {
  const orders = getAll();
  orders.unshift(order);
  wx.setStorageSync(STORAGE_KEY, orders);
}

module.exports = { getAll, add };
