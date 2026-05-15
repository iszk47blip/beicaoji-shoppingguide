const BASE = 'http://localhost:8004/api';

function generateSessionId() {
  let sid = wx.getStorageSync('session_id');
  if (!sid) {
    sid = 'wx_' + Date.now() + '_' + Math.random().toString(36).slice(2);
    wx.setStorageSync('session_id', sid);
  }
  return sid;
}

function sendMessage(message = '', sessionId) {
  const sid = sessionId || generateSessionId();
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE + '/chat/send',
      method: 'POST',
      timeout: 60000,
      data: { session_id: sid, message },
      success: res => resolve(res.data),
      fail: reject
    });
  });
}

function resetSession() {
  wx.removeStorageSync('session_id');
}

module.exports = { sendMessage, resetSession, generateSessionId, BASE };
