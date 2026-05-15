const api = require('../../utils/api');
const cart = require('../../utils/stores/cart');
const orderStore = require('../../utils/stores/order');

Page({
  data: {
    messages: [],
    quickReplies: [],
    inputText: '',
    loading: false,
    sessionId: '',
    scrollTop: 0,
    cartCount: 0,
    cartTotal: 0,
    cartItems: [],
    cartPanelShow: false,
    orderShow: false,
    orderNo: '',
    orderTime: '',
    hasOrders: false
  },

  onLoad() {
    this._cartSub = (state) => {
      this.setData({
        cartCount: state.count, cartTotal: state.total, cartItems: state.items
      });
    };
    cart.subscribe(this._cartSub);
    this._initChat();
  },

  onUnload() {
    cart.unsubscribe(this._cartSub);
  },

  _initChat() {
    const sid = api.generateSessionId();
    this.setData({ sessionId: sid, loading: true });
    api.sendMessage('', sid).then(res => {
      this.setData({ loading: false });
      this._handleResponse(res);
    }).catch(err => {
      console.error('Init failed:', err);
      this.setData({ loading: false });
      this.addMessage('text', 'bot', '你好！我是焙草集的健康顾问，有什么可以帮你的？');
    });
  },

  addMessage(type, role, content) {
    const msg = { type, role, content };
    const messages = [...this.data.messages, msg];
    this.setData({ messages }, () => {
      setTimeout(() => this.setData({ scrollTop: 999999 }), 100);
    });
  },

  addRecommendation(rec, content) {
    const msg = { type: 'recommendation', role: 'bot', content, constitution: rec.constitution, bundle: rec.bundle };
    const messages = [...this.data.messages, msg];
    this.setData({ messages }, () => {
      setTimeout(() => this.setData({ scrollTop: 999999 }), 100);
    });
  },

  addCatalog(catalog, content) {
    const msg = { type: 'catalog', role: 'bot', content: content || '', categories: catalog };
    const messages = [...this.data.messages, msg];
    this.setData({ messages }, () => {
      setTimeout(() => this.setData({ scrollTop: 999999 }), 100);
    });
  },

  _handleResponse(res) {
    if (res.recommendation) {
      this.addRecommendation(res.recommendation, res.message);
    } else if (res.catalog) {
      this.addCatalog(res.catalog, res.message);
    } else if (res.message) {
      this.addMessage('text', 'bot', res.message);
    }
    if (res.quick_replies) {
      this.setData({ quickReplies: res.quick_replies });
    }
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  onQuickReply(e) {
    const text = e.currentTarget.dataset.text;
    this.addMessage('text', 'user', text);
    this.setData({ quickReplies: [], loading: true });
    this._send(text);
  },

  onSend() {
    const text = this.data.inputText.trim();
    if (!text) return;
    this.addMessage('text', 'user', text);
    this.setData({ inputText: '', quickReplies: [], loading: true });
    this._send(text);
  },

  _send(message) {
    api.sendMessage(message, this.data.sessionId).then(res => {
      this.setData({ loading: false });
      this._handleResponse(res);
    }).catch(err => {
      this.setData({ loading: false });
      console.error('Send failed:', err);
      this.addMessage('text', 'system', '网络连接失败，请确认后端已启动。');
    });
  },

  // --- Cart events from product-card ---

  onProductQuantityChange(e) {
    const { product, skuId, quantity, quickBuy } = e.detail;
    if (cart.getQuantity(skuId) === 0) {
      cart.add(product);
    } else {
      cart.setQuantity(skuId, quantity);
    }
    if (quickBuy) {
      this.setData({ cartPanelShow: true });
    }
  },

  // --- Cart bar ---

  onCartBarTap() {
    this.setData({ cartPanelShow: true });
  },

  // --- Cart panel ---

  onCartPanelClose() {
    this.setData({ cartPanelShow: false });
  },

  onCartQtyChange(e) {
    const { skuId, quantity } = e.detail;
    cart.setQuantity(skuId, quantity);
  },

  onCartRemove(e) {
    cart.remove(e.detail.skuId);
  },

  onCartClear() {
    cart.clear();
    this.setData({ cartPanelShow: false });
    this.showToast('购物车已清空');
  },

  onCartCopy() {
    const items = cart.getItems();
    let text = '我的选购清单：\n';
    items.forEach(i => {
      text += `${i.name} x${i.quantity} ¥${(i.price * i.quantity).toFixed(1)}\n`;
    });
    text += `\n合计：¥${cart.total().toFixed(1)}`;
    wx.setClipboardData({ data: text, success: () => this.showToast('已复制选购清单') });
  },

  onCartCheckout() {
    this.setData({ cartPanelShow: false });
    const now = new Date();
    const orderNo = 'BCJ' + Date.now().toString(36).toUpperCase();
    const timeStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')} ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    this.setData({ orderShow: true, orderNo, orderTime: timeStr });
  },

  onOrderClose() {
    this.setData({ orderShow: false });
  },

  onOrderConfirm(e) {
    const items = cart.getItems();
    orderStore.add({
      orderNo: e.detail.orderNo || this.data.orderNo,
      time: this.data.orderTime,
      items: items.map(i => ({ sku_id: i.sku_id, name: i.name, price: i.price, quantity: i.quantity })),
      total: cart.total(),
      count: cart.count()
    });
    cart.clear();
    this.setData({ orderShow: false, hasOrders: true });
    this.addMessage('text', 'system', `下单成功！订单号：${this.data.orderNo}\n到店出示订单号取货。`);
    this.showToast('下单成功');
  },

  onShowOrders() {
    wx.navigateTo({ url: '/pages/orders/orders' });
  },

  onViewReport() {
    wx.navigateTo({
      url: '/pages/report/report',
      success: page => {
        page.setData({ sessionId: this.data.sessionId });
      }
    });
  },

  showToast(msg) {
    wx.showToast({ title: msg, icon: 'none', duration: 2000 });
  }
});
