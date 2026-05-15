Component({
  properties: {
    show: { type: Boolean, value: false },
    items: { type: Array, value: [] },
    total: { type: Number, value: 0 },
    count: { type: Number, value: 0 },
    orderNo: { type: String, value: '' },
    orderTime: { type: String, value: '' }
  },

  observers: {
    'items': function(items) {
      const formatted = (items || []).map(i => ({
        ...i,
        _subtotal: ((i.price || 0) * (i.quantity || 0)).toFixed(1)
      }));
      this.setData({ _items: formatted });
    },
    'total': function(total) {
      this.setData({ _total: (total || 0).toFixed(1) });
    }
  },

  methods: {
    noop() {},

    onClose() {
      this.triggerEvent('close');
    },

    onConfirm() {
      this.triggerEvent('confirm', { orderNo: this.properties.orderNo });
    }
  }
});
