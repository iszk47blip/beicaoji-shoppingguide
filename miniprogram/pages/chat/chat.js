const api = require('../../utils/api');

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false
  },

  onLoad() {
    this.addMessage('bot', '你好！我是焙草集的健康顾问 🌿\n\n我可以帮你了解自己的身体状态，推荐适合你的药食同源调理产品。\n准备好了就告诉我～');
  },

  addMessage(role, content) {
    this.data.messages.push({ role, content });
    this.setData({ messages: this.data.messages });
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  async onSend() {
    const text = this.data.inputText.trim();
    if (!text) return;

    this.addMessage('user', text);
    this.setData({ inputText: '', loading: true });

    try {
      const res = await api.sendMessage(text);
      this.setData({ loading: false });
      this.addMessage('bot', res.message);

      if (res.recommendation) {
        wx.navigateTo({
          url: '/pages/report/report',
          success: page => page.setData({ report: res.recommendation })
        });
      }
    } catch (err) {
      this.setData({ loading: false });
      this.addMessage('bot', '抱歉出了点问题，请稍后再试。');
    }
  }
});
