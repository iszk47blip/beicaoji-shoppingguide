# 小程序测试指南

## 运行测试

```bash
cd miniprogram

# 安装依赖
npm install

# 单元测试
npm test

# 监听模式
npm run test:watch

# E2E 测试（需先配置开发者工具端口）
npm run test:e2e
```

## 单元测试

基于 Jest + jest-environment-jsdom，测试小程序前端纯逻辑。

**覆盖范围：**
- `utils/stores/cart.js` — 购物车状态管理（12 个测试）
- `utils/api.js` — API 请求封装（8 个测试）

**Mock 策略：** 所有微信 API（`wx.request`、`wx.getStorageSync` 等）已在 `tests/setup.js` 中 mock，测试不依赖真机。

**添加新测试：** 在 `tests/unit/` 下创建 `*.test.js` 文件。

## E2E 测试

基于 `miniprogram-automator`，控制微信开发者工具模拟器进行端到端测试。

### 前置配置

1. 打开微信开发者工具
2. 点击「工具 → 自动化测试 → 开启自动化测试端口」（默认端口 9420）
3. 确保后端已启动：`cd backend && python -m uvicorn app.main:app --reload`

### 运行 E2E

```bash
npm run test:e2e
```

当前覆盖场景：
- 页面加载验证
- 导航栏标题正确
- 发送消息流程
- 购物车开关

## 构建和上传

```bash
npm run build    # 构建
npm run upload  # 上传
```

## CI 集成

E2E 测试需要在 GitHub Actions 或其他 CI 中运行，需要：
1. 启动微信开发者工具并开启自动化端口
2. 运行 `npm run test:e2e`