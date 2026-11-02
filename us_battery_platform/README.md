# 美国锂离子电池进口监测平台

HS **850760**（锂离子蓄电池）美国进口动态监测平台，重点追踪**中国份额与来源地结构变迁**。

- 数据范围：**2012-01 – 2026-08**，共 176 个月，123 个原产地
- 数据来源：USA Trade Online（美国普查局），HS 六位编码 850760；锂离子蓄电池自 2012 年（HS2012 版）起为独立子目
- 金额口径：一般进口海关价值（美元），原产国口径；州 = 申报目的地州，口岸 = 卸货口岸

## 快速开始

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器访问 http://localhost:8501

## 数据

**双通道，自动切换：**

1. **Census API 自动更新**（推荐）：平台启动时探测最新月份并增量拉取，与 USA Trade Online 同源
   - 端点：`imports/statehs`、`imports/porths`，谓词 `I_COMMODITY=850760`、`SUMMARY_LVL=DET`
   - API Key 免费申请：https://api.census.gov/data/key_signup.html
   - 配置方式（优先级从高到低）：环境变量 `CENSUS_API_KEY` / Streamlit secrets / 侧边栏输入（写入 `data/processed/census_key.txt`）/ 本地 key 文件
2. **Excel 回退**：`data/raw/850760_美国进口数据_2012-2026.xlsx`（API 不可达时自动使用）

**缓存机制：** API 增量结果落盘为 `data/processed/state.parquet`、`port.parquet`，并记录 `api_meta.json`。有 Parquet 时优先读取，否则从 Excel 重建；侧边栏提供「全量重建」。

**两个维度：**

- `State_目的地州`：原产地 × 月份 × 州 × 进口额
- `Port_入境口岸`：原产地 × 月份 × 口岸 × 进口额

## 统计口径

侧边栏「统计口径」三档，全部 KPI、图表、份额随之联动：

| 口径 | 含义 | 份额计算 |
|---|---|---|
| 当月值 | 所选月份当月进口额 | 当月各来源地金额 ÷ 当月总额 |
| 年初至今累计 | 每年 1 月至所选末端月的累计，同比对比「去年同期同段」 | 区间累计金额重新计算 |
| 12 个月滚动累计 | 任意月份向前 12 个月合计 | 滚动金额重新计算 |

## 平台结构（7 个页面）

| 页面 | 内容 |
|---|---|
| 📈 总览仪表盘 | KPI（进口额、中国份额、CR5、同比等，随口径联动）、进口额走势、同比增速、月度进口额分布箱线图 |
| 🌍 来源地结构 | 份额堆叠面积、所选周期平均份额排名、主要来源地排名变化（Bump Chart）、东亚三大供给地对比 |
| 📊 中国看板 | 自华进口额与份额双轴走势、中国份额变动与其他来源地份额变化（双向柱）、份额流向 |
| 🎯 集中度与多元化 | CR5/CR10、HHI、多元化指数（1−HHI）与熵指数、主要来源地份额明细表 |
| ⚡ 政策冲击分析 | 2024-09 301 关税事件研究：政策前后月均额、份额变化（中国 + 升幅前 4 + 降幅前 4）、明细表 |
| 🗺️ 州与口岸分布 | 申报目的地州分布地图、入境口岸 Top 12、主要入境口岸份额结构演变 |
| 📖 数据说明 | 数据来源与口径、指标定义、使用提示 |

## 指标体系

- **总量**：进口额、同比增速（滞后 12 期以消除季节性）、累计进口额
- **结构**：来源地份额、CR5 / CR10、HHI（0–1）、熵指数（归一化 0–1）、多元化指数（1 − HHI）
- **政策**：2024-09-27 生效的 301 关税调整（车用动力电池 HTS 8507.60.0010，7.5% → 25%）作为事件时点，窗口可选 ±6/12/18/24 个月

## 部署

**本地：** `streamlit run app.py`

**Streamlit Community Cloud：**

1. 仓库推送到 GitHub，Main file path 填 `app.py`
2. 可选：在 App settings → Secrets 增加

```toml
CENSUS_API_KEY = "你的密钥"
```

3. Cloud 环境每次重启 `data/processed/` 若不存在会自动从 Excel 重建缓存；若仓库内已含 parquet 则直接读取

> `run.py` 仅用于 WorkBuddy 一键发布（读取 `PORT` 环境变量），Streamlit Cloud 不需要。

## 技术栈

Python · Streamlit · Plotly · pandas · numpy · openpyxl · pyarrow

## 目录

```
us_battery_platform/
├── app.py                  # 主应用（7 个页面）
├── run.py                  # 部署启动器（读取 PORT 环境变量）
├── src/
│   ├── data.py             # 数据加载（Parquet 优先 → Excel 重建）、指标计算
│   └── census_api.py       # Census API 自动更新（增量拉取、修订重拉、Key 管理）
├── data/raw/               # 原始 Excel 数据（2012-2026）
├── data/processed/         # 缓存（parquet）+ 元信息 + 本地 API Key（不入库）
├── .streamlit/config.toml  # 主题配置
└── requirements.txt
```
