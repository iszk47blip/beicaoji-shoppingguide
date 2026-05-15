const cart = require('../../utils/stores/cart');

Component({
  properties: {
    product: { type: Object, value: {} }
  },

  data: {
    emoji: '',
    _qty: 0
  },

  lifetimes: {
    attached() {
      const sku = this.properties.product.sku_id;
      this.setData({ _qty: cart.getQuantity(sku) });
      this._cartSub = (state) => {
        const qty = (state.items.find(i => i.sku_id === sku) || {}).quantity || 0;
        if (qty !== this.data._qty) {
          this.setData({ _qty: qty });
        }
      };
      cart.subscribe(this._cartSub);
    },
    detached() {
      if (this._cartSub) cart.unsubscribe(this._cartSub);
    }
  },

  observers: {
    'product.category': function(cat) {
      const map = { biscuit: '🍪', bread: '🍞', tea: '🍵', toy: '🎐' };
      this.setData({ emoji: map[cat] || '🌿' });
    },
    'product.sku_id': function(sku) {
      if (this._cartSub) cart.unsubscribe(this._cartSub);
      this.setData({ _qty: cart.getQuantity(sku) });
      const self = this;
      this._cartSub = (state) => {
        const qty = (state.items.find(i => i.sku_id === sku) || {}).quantity || 0;
        if (qty !== self.data._qty) {
          self.setData({ _qty: qty });
        }
      };
      cart.subscribe(this._cartSub);
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
    }
  }
});
