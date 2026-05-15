const cart = require('../../utils/stores/cart');

Component({
  properties: {
    product: { type: Object, value: {}, observer: '_onProductChange' }
  },

  data: {
    emoji: '',
    _qty: 0,
    _sku: ''
  },

  lifetimes: {
    detached() {
      if (this._cartSub) cart.unsubscribe(this._cartSub);
    }
  },

  methods: {
    _onProductChange(p) {
      if (!p || !p.sku_id) return;
      const sku = p.sku_id;
      if (this._sku === sku) return;
      this._sku = sku;

      if (this._cartSub) cart.unsubscribe(this._cartSub);

      const emojiMap = { biscuit: '🍪', bread: '🍞', tea: '🍵', toy: '🎐' };
      this.setData({ emoji: emojiMap[p.category] || '🌿', _qty: cart.getQuantity(sku) });

      this._cartSub = (state) => {
        const item = state.items.find(i => i.sku_id === sku);
        const qty = item ? item.quantity : 0;
        if (qty !== this.data._qty) {
          this.setData({ _qty: qty });
        }
      };
      cart.subscribe(this._cartSub);
    },

    onStepperChange(e) {
      const prod = this.properties.product;
      this.triggerEvent('quantitychange', {
        product: prod,
        skuId: prod.sku_id,
        delta: e.detail.delta,
        quantity: e.detail.quantity
      });
    }
  }
});
