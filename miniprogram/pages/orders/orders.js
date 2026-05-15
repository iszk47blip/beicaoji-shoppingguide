const orderStore = require('../../utils/stores/order');

Page({
  data: {
    orders: []
  },

  onShow() {
    this.setData({ orders: orderStore.getAll() });
  }
});
