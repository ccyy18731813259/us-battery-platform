# 美国锂离子电池进口监测平台

HS **850760**（锂离子蓄电池）美国进口动态监测平台，重点追踪**中国份额与竞争力变迁**。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动平台
streamlit run app.py
```

浏览器访问 http://localhost:8501

## 数据

- 数据源（双通道，自动切换）：
  1. **US Census API 自动更新**（推荐）：平台启动时自动探测最新月份并增量拉取；需在侧边栏填入免费 API Key（[申请地址](https://api.census.gov/data/key_signup.html)），写入 `data/processed/census_key.txt` 或环境变量 `CENSUS_API_KEY`
  2. **Excel 导出回退**：`data/raw/850760_美国进口数据_2017-2026.xlsx`（API 不可达时自动使用）
- API 数据落盘为 Parquet 缓存（`data/processed/state.parquet`、`port.parquet`），按月增量、支持官方修订重拉；侧边栏提供「全量重建」
- 包含两个数据维度：
  - `State_目的地州`：国家 × 月份 × 美州 × 进口额/重量
  - `Port_入境口岸`：国家 × 月份 × 口岸 × 进口额/重量

## 平台结构（7 个页面）

| 页面 | 内容 |
|---|---|
| 📈 总览仪表盘 | 进口总额走势（当月+12个月滚动）、同比增速、季节性箱线图、KPI |
| 🌍 来源地结构 | 份额堆叠面积、Top N 排名、Bump Chart 排名演变、中日韩台对比 |
| 🇨🇳 中国竞争力 | 自华进口额与份额双轴、国别单价对比（量价分离）、份额流向矩阵 |
| 🎯 集中度与多元化 | CR5/CR10、HHI、1−HHI、归一化熵指数、份额明细表 |
| ⚡ 政策冲击分析 | 2024-09 301关税事件研究：±N 个月前后对比、份额变化、明细表 |
| 🗺️ 州与口岸分布 | 目的地州 treemap、入境口岸 Top12、年度州趋势、运输方式结构 |
| 📖 数据说明 | 口径、指标定义、解读提示 |

## 指标体系

- **总量**：进口额、同比增速（滞后12期消除季节性）、12个月滚动累计
- **结构**：来源国份额、CR5/CR10、HHI、熵指数、多元化指数（1−HHI）
- **竞争力**：单价代理 = 金额 ÷ 海运+空运毛重（美元/千克，6个月平滑）
- **政策**：2024-09-30 301 关税调整为事件时点，可调事件窗口（±6/12/18/24 个月）

## 技术栈

Python · Streamlit · Plotly · pandas · numpy

## 目录

```
us_battery_platform/
├── app.py                  # 主应用（Streamlit）
├── run.py                  # 部署启动器（读取 PORT 环境变量）
├── src/
│   ├── data.py             # 数据加载（Parquet 优先 → Excel 回退）、指标计算
│   └── census_api.py       # Census API 自动更新（增量拉取、修订重拉、Key 管理）
├── data/raw/               # 原始 Excel 数据
├── data/processed/         # API 缓存（parquet）+ 元信息 + API Key
├── .streamlit/config.toml  # 主题配置
└── requirements.txt
```
