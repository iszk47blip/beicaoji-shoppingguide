Component({
  properties: {
    show: { type: Boolean, value: false },
    items: { type: Array, value: [] },
    total: { type: Number, value: 0 }
  },

  methods: {
    noop() {},

    onClose() {
      this.triggerEvent('close');
    },

    onOverlayTap() {
      this.triggerEvent('close');
    },

    onStepperChange(e) {
      this.triggerEvent('qtychange', e.detail);
    },

    onRemove(e) {
      const skuId = e.currentTarget.dataset.skuId;
      this.triggerEvent('remove', { skuId });
    },

    onClear() {
      this.triggerEvent('clear');
    },

    onCopy() {
      this.triggerEvent('copy');
    },

    onCheckout() {
      this.triggerEvent('checkout');
    }
  }
});
