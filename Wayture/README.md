# Wayture 游览导览

一个基于 Vue 3 和 Vite 的游览导览演示项目，包含：

- 首页探索入口
- 微软 OpenID 登录（MSAL）
- 地图/列表景点展示
- 游览列表管理与攻略生成
- 游览详情页同步高亮地图
- 明信片生成与对话式编辑

## 运行方式

1. 安装依赖

```bash
npm install
```

2. 启动开发服务

```bash
npm run dev
```

3. 访问

打开浏览器并访问 `http://localhost:4173`

## 注意

请在 `src/composables/useAuth.ts` 中替换 `YOUR_MICROSOFT_APP_CLIENT_ID` 为你的 Azure AD 应用 Client ID。

如果需要定制 `authority`、`scopes` 或 `redirectUri`，也可以在该文件中修改。