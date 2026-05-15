Component({
  properties: {
    skuId: { type: String, value: '' },
    quantity: { type: Number, value: 0 },
    min: { type: Number, value: 0 },
    max: { type: Number, value: 99 }
  },

  methods: {
    onMinus() {
      if (this.properties.quantity <= this.properties.min) return;
      const newQty = this.properties.quantity - 1;
      this.triggerEvent('change', { skuId: this.properties.skuId, quantity: newQty, delta: -1 });
    },
    onPlus() {
      if (this.properties.quantity >= this.properties.max) return;
      const newQty = this.properties.quantity + 1;
      this.triggerEvent('change', { skuId: this.properties.skuId, quantity: newQty, delta: 1 });
    }
  }
});
