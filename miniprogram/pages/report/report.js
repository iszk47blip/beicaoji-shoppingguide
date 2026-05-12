Page({
  data: { report: {} },

  onBuyOffline() {
    wx.showModal({
      title: '到店购买',
      content: '请向店员出示此推荐页面，店员会帮你完成购买。',
      showCancel: false,
    });
  }
});
