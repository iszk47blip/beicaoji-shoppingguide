const api = require('../../utils/api');
const cart = require('../../utils/stores/cart');
const orderStore = require('../../utils/stores/order');

Page({
  data: {
    messages: [],
    quickReplies: [],
    inputText: '',
    loading: false,
    loadingHint: '',
    sessionId: '',
    scrollAnchor: 'a0',
    cartCount: 0,
    cartTotal: 0,
    cartItems: [],
    cartPanelShow: false,
    orderShow: false,
    orderNo: '',
    orderTime: '',
    hasOrders: false,
    voiceState: 'idle',       // idle | recording | recognizing | error
    voiceHint: '',
    voiceBtnText: ''
  },

  _initVoice() {
    this._recorder = wx.createRecordManager();
    this._recorder.onStart(() => {
      this._recordStartY = 0;
      this.setData({
        voiceState: 'recording',
        voiceHint: '正在聆听...',
        voiceBtnText: '60'
      });
      this._startCountdown(60);
    });
    this._recorder.onStop((res) => {
      if (this._canceled) {
        this._canceled = false;
        this.setData({ voiceState: 'idle', voiceHint: '', voiceBtnText: '' });
        return;
      }
      const duration = res.duration || 0;
      if (duration < 1000) {
        this.setData({ voiceState: 'error', voiceHint: '识别失败，请重试' });
        this._resetVoiceState(2000);
        return;
      }
      this._handleVoiceResult(res);
    });
    this._recorder.onError((err) => {
      this.setData({ voiceState: 'error', voiceHint: '识别失败，请重试' });
      this._resetVoiceState(2000);
    });
  },

  _startCountdown(seconds) {
    let left = seconds;
    this._countdownTimer = setInterval(() => {
      left--;
      if (left <= 0) {
        clearInterval(this._countdownTimer);
        this._countdownTimer = null;
        this.setData({ voiceBtnText: '0' });
        this._recorder.stop();
      } else {
        this.setData({ voiceBtnText: String(left) });
      }
    }, 1000);
  },

  _resetVoiceState(delay) {
    setTimeout(() => {
      this.setData({ voiceState: 'idle', voiceHint: '', voiceBtnText: '' });
    }, delay || 0);
  },

  _handleVoiceResult(res) {
    this.setData({ voiceState: 'recognizing', voiceHint: '识别中...', voiceBtnText: '' });
    const text = (res.text || '').trim();
    if (!text) {
      this.setData({ voiceState: 'error', voiceHint: '识别失败，请重试' });
      this._resetVoiceState(2000);
      return;
    }
    this.setData({ voiceState: 'idle', voiceHint: '', voiceBtnText: '' });
    this.addMessage('text', 'user', text);
    this.setData({ inputText: '', quickReplies: [], loading: true, loadingHint: '小焙正在思考...' });
    this._scrollToBottom();
    this._send(text);
  },

  onVoiceTap() {
    // idle 时点按同按住的开始效果一样
  },

  onVoiceTouchStart(e) {
    if (this.data.voiceState !== 'idle') return;
    this._canceled = false;
    this._recordStartY = e.touches[0].clientY;
    this._recorder.start({ duration: 60000, format: 'mp3' });
  },

  onVoiceTouchMove(e) {
    if (this.data.voiceState !== 'recording') return;
    const deltaY = this._recordStartY - e.touches[0].clientY;
    if (deltaY > 80 && !this._canceled) {
      this._canceled = true;
      this.setData({ voiceHint: '松开取消' });
    } else if (deltaY <= 40 && this._canceled) {
      this._canceled = false;
      this.setData({ voiceHint: '正在聆听...' });
    }
  },

  onVoiceTouchEnd(e) {
    if (this.data.voiceState !== 'recording') return;
    if (this._countdownTimer) {
      clearInterval(this._countdownTimer);
      this._countdownTimer = null;
    }
    this._recorder.stop();
  },

  onLoad() {
    this._initVoice();
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
    if (this._countdownTimer) clearInterval(this._countdownTimer);
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
    const anchor = 'a' + Date.now();
    this.setData({ messages, scrollAnchor: anchor });
  },

  addRecommendation(rec, content) {
    const msg = { type: 'recommendation', role: 'bot', content, constitution: rec.constitution, bundle: rec.bundle };
    const messages = [...this.data.messages, msg];
    const anchor = 'a' + Date.now();
    this.setData({ messages, scrollAnchor: anchor });
  },

  addCatalog(catalog, content) {
    const msg = { type: 'catalog', role: 'bot', content: content || '', categories: catalog };
    const messages = [...this.data.messages, msg];
    const anchor = 'a' + Date.now();
    this.setData({ messages, scrollAnchor: anchor });
  },

  _scrollToBottom() {
    wx.nextTick(() => {
      wx.createSelectorQuery().select('.message-list').boundingClientRect((rect) => {
        if (rect) {
          wx.pageScrollTo({ scrollTop: rect.top + rect.height + 9999, duration: 300 });
        }
      }).exec();
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
    this._scrollToBottom();
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  onQuickReply(e) {
    const text = e.currentTarget.dataset.text;
    this.addMessage('text', 'user', text);
    this.setData({ quickReplies: [], loading: true, loadingHint: '小焙正在思考...' });
    this._scrollToBottom();
    this._send(text);
  },

  onSend() {
    const text = this.data.inputText.trim();
    if (!text) return;
    this.addMessage('text', 'user', text);
    this.setData({ inputText: '', quickReplies: [], loading: true, loadingHint: '小焙正在思考...' });
    this._scrollToBottom();
    this._send(text);
  },

  _send(message) {
    api.sendMessage(message, this.data.sessionId).then(res => {
      this.setData({ loading: false, loadingHint: '' });
      this._handleResponse(res);
    }).catch(err => {
      this.setData({ loading: false, loadingHint: '' });
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