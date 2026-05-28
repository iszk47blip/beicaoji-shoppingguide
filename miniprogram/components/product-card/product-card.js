const cart = require('../../utils/stores/cart');

Component({
  properties: {
    product: { type: Object, value: {}, observer: '_onProductChange' }
  },

  data: {
    emoji: '',
    catCls: 'bg-biscuit',
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

      const catMap = {
        '面包类': { emoji: '🍞', cls: 'bread' },
        '茶饮类': { emoji: '🍵', cls: 'tea' },
        '零食类': { emoji: '🥨', cls: 'snack' },
        '香囊类': { emoji: '🎐', cls: 'sachet' },
        '文玩类': { emoji: '🎋', cls: 'play' },
        '耗材类': { emoji: '📦', cls: 'supply' },
        '面团类': { emoji: '🥖', cls: 'dough' },
        '礼盒套餐': { emoji: '🎁', cls: 'gift' },
        '现场冲泡茶饮': { emoji: '🫖', cls: 'brew' },
        biscuit: { emoji: '🍪', cls: 'biscuit' },
        bread: { emoji: '🍞', cls: 'bread' },
        tea: { emoji: '🍵', cls: 'tea' },
        toy: { emoji: '🎐', cls: 'toy' },
      };
      const cfg = catMap[p.category] || { emoji: '🌿', cls: 'biscuit' };
      this.setData({ emoji: cfg.emoji, catCls: 'bg-' + cfg.cls, _qty: cart.getQuantity(sku) });

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
