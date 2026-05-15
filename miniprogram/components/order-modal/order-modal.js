Component({
  properties: {
    show: { type: Boolean, value: false },
    items: { type: Array, value: [] },
    total: { type: Number, value: 0 },
    count: { type: Number, value: 0 },
    orderNo: { type: String, value: '' },
    orderTime: { type: String, value: '' }
  },

  methods: {
    onClose() {
      this.triggerEvent('close');
    },

    onConfirm() {
      this.triggerEvent('confirm', { orderNo: this.properties.orderNo });
    }
  }
});
