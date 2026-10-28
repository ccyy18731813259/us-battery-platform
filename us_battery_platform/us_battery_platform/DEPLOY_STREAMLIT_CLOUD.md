# Streamlit Community Cloud 部署指南

将本平台部署到 Streamlit 官方免费云（`https://你的应用名.streamlit.app`）。

## 前置准备

1. 注册 GitHub 账号（github.com）
2. 注册 Streamlit Community Cloud（share.streamlit.io，直接用 GitHub 账号登录）

## 步骤

### 1. 创建 GitHub 仓库并上传代码

在 GitHub 上新建仓库（如 `us-battery-import-platform`），然后本地执行：

```bash
cd us_battery_platform
git init
git add .
git commit -m "美国锂电池进口监测平台"
git branch -M main
git remote add origin https://github.com/你的用户名/us-battery-import-platform.git
git push -u origin main
```

> 仓库可以是 Private 的（部署时授权 Streamlit 访问即可）。
> `.gitignore` 已排除 API Key 和本地缓存，不会泄露。

### 2. 在 Streamlit Cloud 上部署

1. 打开 share.streamlit.io → 用 GitHub 登录
2. 右上角 **Create app** → **Deploy a public app from GitHub**
3. 选择仓库 → 分支 `main` → **Main file path** 填 `app.py`
4. （可选）App URL 自定义子域名，如 `us-lithium-battery`
5. 点 **Deploy**，等待 3-5 分钟自动安装依赖并启动

### 3. 配置 API Key（自动更新用）

1. 部署完成后 → 应用右下角 **Manage app** → **Settings** → **Secrets**
2. 填入：

```toml
CENSUS_API_KEY = "你的key"
```

3. 保存后应用自动重启。代码通过环境变量读取该 Key，无需改任何代码。

## 注意事项

- **免费实例限制**：约 1GB 内存、7 天无访问会休眠（再次访问冷启动 1-2 分钟）、文件系统重启后重置
- 缓存重置没关系：平台会自动从 Excel 重新播种，再增量拉取 API 新月份
- 数据文件（4.4MB Excel）在仓库内，部署即带全量历史数据
- 想保持常驻不休眠，可升级 Cloud（按月付费）或改用云服务器自部署

## 与 WorkBuddy 发布的对比

| | WorkBuddy 发布 | Streamlit Cloud |
|---|---|---|
| 链接 | workbuddy.host 域名 | 你自己的 .streamlit.app 域名 |
| 休眠 | 不休眠 | 7 天无访问休眠 |
| 更新方式 | 对话中让我重新发布 | git push 自动重新部署 |
| 费用 | 免费 | 免费（有限制） |

---

## 本项目的准备状态（已为你完成）

- ✅ 已初始化 Git 仓库并完成首个提交（`git log` 可见）
- ✅ `.gitignore` 已排除 API Key（`data/processed/census_key.txt`）与本地缓存
- ✅ `requirements.txt` 已锁定版本（pandas<3，避免线上兼容问题）
- ✅ 数据文件已入库（4.4MB Excel），部署即带全量历史数据

### 你只需要做（3 步）

```bash
# 1. GitHub 上新建仓库（不要勾选初始化 README），然后在本地执行：
cd "D:/workbuddy产出/2026-10-24-20-29-18/us_battery_platform"
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

2. 打开 https://share.streamlit.io → GitHub 登录 → **Create app** → 选仓库 → Main file 填 `app.py` → Deploy

3. 部署完成后：**Manage app → Settings → Secrets** 粘贴：

```toml
CENSUS_API_KEY = "c805235c8b9c9762e72afffbfb16eececef3da7b"
```

保存后自动重启，自动更新即生效。
