const api = require('../../utils/api');
const cart = require('../../utils/stores/cart');

Page({
  data: {
    report: null,
    loading: true,
    cartCount: 0,
    cartTotal: 0
  },

  onLoad(options) {
    this._cartSub = (state) => {
      const count = state.count;
      const total = state.total;
      this.setData({ cartCount: count, cartTotal: total });
      if (this.data.report && this.data.report.bundle) {
        const bundle = this.data.report.bundle.map(p => ({
          ...p, quantity: cart.getQuantity(p.sku_id)
        }));
        this.setData({ 'report.bundle': bundle });
      }
    };
    cart.subscribe(this._cartSub);

    if (options.sessionId) {
      this._loadReport(options.sessionId);
    } else {
      const sid = api.generateSessionId();
      this._loadReport(sid);
    }
  },

  onUnload() {
    cart.unsubscribe(this._cartSub);
  },

  _loadReport(sid) {
    wx.request({
      url: api.BASE + '/report/' + sid + '/data',
      success: (res) => {
        if (res.data && res.data.recommendation) {
          const rec = res.data.recommendation;
          const bundle = (rec.bundle || []).map(p => ({
            ...p, quantity: cart.getQuantity(p.sku_id)
          }));
          this.setData({
            report: { ...rec, bundle },
            loading: false
          });
        } else {
          this.setData({ loading: false });
        }
      },
      fail: () => {
        this.setData({ loading: false });
      }
    });
  },

  onProductQuantityChange(e) {
    const { product, skuId, quantity } = e.detail;
    if (cart.getQuantity(skuId) === 0) {
      cart.add(product);
    } else {
      cart.setQuantity(skuId, quantity);
    }
  },

  onCartBarTap() {
    wx.navigateBack();
  },

  onBuyOffline() {
    wx.showModal({
      title: '到店购买',
      content: '请向店员出示此推荐页面，店员会帮你完成购买。',
      showCancel: false
    });
  },

  onBackToChat() {
    wx.navigateBack();
  }
});
