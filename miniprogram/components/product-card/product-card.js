Component({
  properties: {
    product: { type: Object, value: {} },
    quantity: { type: Number, value: 0 }
  },

  data: {
    emoji: ''
  },

  observers: {
    'product.category': function(cat) {
      const map = { biscuit: '🍪', bread: '🍞', tea: '🍵', toy: '🎐' };
      this.setData({ emoji: map[cat] || '🌿' });
    }
  },

  methods: {
    onStepperChange(e) {
      this.triggerEvent('quantitychange', {
        product: this.properties.product,
        skuId: e.detail.skuId || this.properties.product.sku_id,
        delta: e.detail.delta,
        quantity: e.detail.quantity
      });
    },

    onQuickBuy() {
      this.triggerEvent('quantitychange', {
        product: this.properties.product,
        skuId: this.properties.product.sku_id,
        delta: 1,
        quantity: 1,
        quickBuy: true
      });
    }
  }
});
