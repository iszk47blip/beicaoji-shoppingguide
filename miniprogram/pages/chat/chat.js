const api = require('../../utils/api');

Page({
  data: {
    messages: [],
    quickReplies: [],
    inputText: '',
    loading: false,
    sessionId: ''
  },

  onLoad() {
    this._initChat();
  },

  _initChat() {
    const sid = api.generateSessionId();
    this.setData({ sessionId: sid, loading: true });
    api.sendMessage('', sid).then(res => {
      this.setData({ loading: false });
      if (res.message) {
        this.addMessage('text', 'bot', res.message);
      }
      if (res.quick_replies) {
        this.setData({ quickReplies: res.quick_replies });
      }
      if (res.recommendation) {
        this.addRecommendation(res.recommendation, res.message);
      }
      if (res.catalog) {
        this.addCatalog(res.catalog);
      }
    }).catch(() => {
      this.setData({ loading: false });
      this.addMessage('text', 'bot', '你好！我是焙草集的健康顾问，有什么可以帮你的？');
    });
  },

  addMessage(type, role, content) {
    const msg = { type, role, content };
    this.data.messages.push(msg);
    this.setData({ messages: this.data.messages });
  },

  addRecommendation(rec, content) {
    const msg = { type: 'recommendation', role: 'bot', content, constitution: rec.constitution, bundle: rec.bundle };
    this.data.messages.push(msg);
    this.setData({ messages: this.data.messages });
  },

  addCatalog(catalog) {
    const msg = { type: 'catalog', role: 'bot', categories: catalog };
    this.data.messages.push(msg);
    this.setData({ messages: this.data.messages });
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
      if (res.message) {
        this.addMessage('text', 'bot', res.message);
      }
      if (res.recommendation) {
        this.addRecommendation(res.recommendation, res.message);
      }
      if (res.catalog) {
        this.addCatalog(res.catalog);
      }
      if (res.quick_replies) {
        this.setData({ quickReplies: res.quick_replies });
      }
    }).catch(() => {
      this.setData({ loading: false });
      this.addMessage('text', 'system', '抱歉出了点问题，请稍后再试。');
    });
  }
});
