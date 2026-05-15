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
      this.setData({ cartCount: state.count, cartTotal: state.total });
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
        const data = res.data;
        const report = data && data.report ? data.report : data;
        if (report && report.constitution_type) {
          this.setData({ report, loading: false });
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
