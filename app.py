# -*- coding: utf-8 -*-
"""
美国锂离子电池（HS 850760）进口监测平台
中国份额与竞争力动态监测 · 基于 USA Trade Online（美国普查局）月度贸易数据，HS 六位编码 850760
运行：streamlit run app.py
"""
import json
import os
import sys

# 保证无论从哪个目录启动（如 Streamlit Cloud 的仓库根目录），都能找到本目录下的 src 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import census_api as CA
from src import hts10 as H
from src import state_map as SM
from src import insights as INS

pd.options.plotting.backend = "plotly"

# ================================================================ 页面配置
st.set_page_config(
    page_title="美国锂电池进口贸易监测平台",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================================================================ 样式
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
    html, body, [class*="css"], .stMarkdown, .stMetric { font-family: 'Noto Sans SC', sans-serif; }
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px; }
    /* 顶部标题条（白色卡片 + Li 徽标 + 底部深绿饰条） */
    .hero { border-radius: 14px; padding: 20px 26px 18px; background: #FFFFFF;
            border: 1px solid #E8E6E0; box-shadow: 0 1px 3px rgba(0,0,0,.04);
            display: flex; align-items: center; justify-content: space-between; gap: 18px; }
    .hero-left { display: flex; align-items: center; min-width: 0; }
    .hero-badge { width: 52px; height: 52px; border-radius: 12px; background: #12355B; color: #ffffff;
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 21px; margin-right: 18px; flex: 0 0 auto; }
    .hero-text { min-width: 0; }
    .hero h1 { color: #12355B; font-size: 26px; font-weight: 800; margin: 0; letter-spacing: .5px; }
    .hero-meta { color: #6B6B66; font-size: 14px; margin: 10px 0 0; }
    .hero p  { color: #6B6B66; font-size: 13.5px; margin: 6px 0 0; }
    .hero-right { flex: 0 0 auto; }  /* hero 容器 align-items:center，按钮在整个标题栏垂直居中 */
    .hero-btn { background: #12355B !important; color: #ffffff !important; font-size: 15px; font-weight: 700;
            padding: 11px 28px; border-radius: 9px; text-decoration: none !important; white-space: nowrap;
            box-shadow: 0 1px 3px rgba(0,0,0,.12); display: inline-block; }
    .hero-btn:hover, .hero-btn:visited, .hero-btn:active { background: #0E2A47 !important; color: #ffffff !important; text-decoration: none !important; }
    .hero-bar { height: 4px; background: #14532D; border-radius: 0 0 2px 2px; margin-top: 2px; }
    /* 生成报告按钮：深蓝主色 */
    div[data-testid="stButton"] button[kind="primary"] {
        background: #12355B; border: none; font-weight: 700; }
    div[data-testid="stButton"] button[kind="primary"]:hover { background: #0E2A47; }
    /* KPI 卡片（自绘，保证数值完整显示、永不出现省略号） */
    .kpi-row { display: flex; flex-wrap: wrap; gap: 12px; margin: 2px 0 4px; }
    .kpi { flex: 1 1 180px; min-width: 172px; background: #ffffff; border: 1px solid #E8E6E0;
           border-radius: 12px; padding: 16px 18px 12px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
    .kpi-label { color: #6B6B68; font-size: 13px; margin-bottom: 6px; white-space: normal; word-break: break-word; }
    .kpi-value { color: #1A1A1A; font-weight: 700; font-size: clamp(1.1rem, 1.75vw, 1.55rem);
                 line-height: 1.3; white-space: normal; overflow-wrap: anywhere; word-break: break-word; }
    .kpi-delta { font-size: 12.5px; margin-top: 6px; white-space: normal; overflow-wrap: anywhere; }
    .kpi-delta .pd-neg { color: #C0392B; font-weight: 600; }
    .kpi-delta .pd-pos { color: #1E8449; font-weight: 600; }
    .kpi-delta .pd-flat { color: #6B6B68; }
    /* 旧版 st.metric 样式（其他页备用） */
    div[data-testid="stMetric"] { background: #ffffff; border: 1px solid #E8E6E0;
        border-radius: 12px; padding: 16px 18px 12px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
    div[data-testid="stMetric"] label { color: #6B6B68 !important; font-size: 13px !important; }
    div[data-testid="stMetric"] div { color: #1A1A1A !important; font-weight: 700 !important; }
    /* 区块标题 */
    .sec-title { font-size: 17px; font-weight: 700; color: #12355B; margin: 6px 0 2px;
                 border-left: 4px solid #2E86AB; padding-left: 10px; }
    .sec-sub { font-size: 12.5px; color: #8A8A86; margin-bottom: 4px; }
    /* tab 样式 */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #E8E6E0; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; padding: 8px 18px; font-size: 14.5px; }
    .stTabs [aria-selected="true"] { background: #EAF2F8; color: #12355B !important; font-weight: 700; }
    /* 侧边栏 */
    section[data-testid="stSidebar"] { background: #F7F6F3; }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.6rem; }
    /* 州与口岸页：来源地选择器高亮横条 */
    .pick-banner { background: #FFF7E6; border: 1.5px solid #E8A23D; border-left: 6px solid #E67E22;
        border-radius: 10px; padding: 10px 14px 8px; margin-bottom: 0; }
    .pick-banner .pb-title { font-size: 16px; font-weight: 700; color: #7A4A00; }
    .pick-banner .pb-sub { font-size: 12.5px; color: #9A7B3F; margin-top: 2px; }
    section[data-testid="stMain"] div[data-testid="stSelectbox"] > div,
    div[data-testid="block-container"] div[data-testid="stSelectbox"] > div {
        border: 1.8px solid #E67E22 !important; border-radius: 9px !important;
        background: #FFFBF2 !important; }
    div[data-testid="block-container"] div[data-testid="stSelectbox"] label { font-weight: 700; color: #7A4A00 !important; }
    hr { margin: 8px 0; }
    /* AI 解读 / 生成报告 按钮 */
    div[data-testid="stButton"] button[kind="secondary"] {
        background: #fff; color: #12355B; border: 1.5px solid #C9D4E0;
        font-weight: 600; border-radius: 8px; }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        border-color: #2E86AB; color: #2E86AB; }
    div[data-testid="stButton"] button[kind="primary"] {
        background: #0E8074; border-color: #0E8074; color: #fff;
        font-weight: 600; border-radius: 8px; }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #0B6B60; border-color: #0B6B60; }
</style>""", unsafe_allow_html=True)

# ================================================================ 数据加载
state_df = D.load_state()
port_df = D.load_port()

mat = D.monthly_by_country(state_df)          # 月度 × 国家 金额
tot, share = D.with_shares(mat)               # 总额 & 份额
_cm_raw = D.monthly_by_continent(state_df)    # 月度 × 大洲 金额（原产地代码首位归类）
cont_mat = _cm_raw.reindex(columns=[c for c in D.CONTINENT_ORDER if c in _cm_raw.columns])
_, cont_share = D.with_shares(cont_mat)       # 月度 × 大洲 份额
conc = D.concentration(share, 5)              # CR5 / HHI / 熵
conc10 = D.concentration(share, 10)


MONTHS = list(mat.index)
T = mat.index.to_timestamp()
POLICY_TS = D.POLICY_DATE.to_timestamp().to_pydatetime()  # 原生 datetime，避免 pandas 3.x 时间戳加法限制
LAST_M = MONTHS[-1]
PREV_M = MONTHS[-2]


def ts(idx):
    """PeriodIndex / Period Series / Period 列表 → Datetime，供 plotly 使用"""
    if isinstance(idx, pd.Series):
        return idx.dt.to_timestamp()
    if isinstance(idx, pd.PeriodIndex):
        return idx.to_timestamp()
    if isinstance(idx, (list, tuple)) and idx and isinstance(idx[0], pd.Period):
        return pd.PeriodIndex(idx).to_timestamp()
    return idx


# ================================================================ 侧边栏
with st.sidebar:
    st.markdown("### ⚙️ 全局筛选")

    m0, m1 = st.select_slider(
        "数据周期", options=MONTHS,
        value=(MONTHS[max(0, len(MONTHS) - 36)], LAST_M),
        format_func=lambda m: str(m),
    )
    sel_range = [m for m in MONTHS if m0 <= m <= m1]
    sel_ts = [m.to_timestamp() for m in sel_range]

    mode = st.radio("统计口径", ["当月值", "年初至今累计", "12个月滚动累计"], horizontal=True,
                    help="当月值：保留全部波动细节；年初至今累计：每年 1 月至所选末端月的累计（同比与去年同期同段比较）；"
                         "12个月滚动累计：任意月份向前 12 个月合计，用于观察平滑趋势")

    topn = st.slider("重点来源地数量（Top N）", 4, 12, 8)

    st.markdown("---")
    st.markdown("### 🔄 数据自动更新")

    _key = CA.get_api_key()
    _key_input = st.text_input(
        "Census API Key（可选，免费申请）", value=_key, type="password",
        help="在 api.census.gov/data/key_signup.html 免费申请；不填则仅使用本地缓存/Excel 数据")
    if _key_input.strip() and _key_input.strip() != _key:
        CA.save_api_key(_key_input)
        st.toast("API Key 已保存")

    _cache_last = CA.cache_last_month()
    if st.button("🔄 检查并更新数据", type="primary",
                 help="从 US Census API 增量拉取最新月份（州与口岸两个端点）"):
        _progress = st.empty()
        _bar = st.progress(0, text="正在连接 Census API…")

        def _cb(i, n, ym):
            _bar.progress((i) / max(n, 1), text=f"拉取 {ym}（第 {i+1}/{n} 个月）")

        _res = CA.update_cache(progress_cb=_cb)
        _bar.empty()
        if _res["ok"] and _res["fetched"]:
            st.success(f"更新完成：新增 {_res['fetched'][0]} ~ {_res['fetched'][-1]} 共 {len(_res['fetched'])} 个月")
            D.st_cache_data_clear()
            st.rerun()
        elif _res["ok"]:
            st.info(_res["reason"])
        else:
            st.error(_res["reason"])
            st.caption("提示：请确认本环境能访问 api.census.gov，并已填入有效的 API Key。离线时平台继续使用本地缓存数据。")

    if _cache_last:
        st.caption(f"本地数据已更新至：**{_cache_last}**")

    with st.expander("高级：全量重建数据缓存"):
        st.caption("当官方修订历史数据、或本地缓存出现异常时使用。将从 API 重新下载 2012-01 起全部月份（约 4-6 分钟）。")
        if st.button("🧹 全量重建（重新下载全部月份）"):
            _bar2 = st.progress(0, text="全量重建中…")

            def _cb2(i, n, ym):
                _bar2.progress(i / max(n, 1), text=f"拉取 {ym}（第 {i+1}/{n} 个月）")

            _res2 = CA.update_cache(progress_cb=_cb2, force_from=CA.START_MONTH)
            _bar2.empty()
            if _res2["ok"] and _res2["fetched"]:
                st.success(f"重建完成：{_res2['fetched'][0]} ~ {_res2['fetched'][-1]} 共 {len(_res2['fetched'])} 个月")
                D.st_cache_data_clear()
                st.rerun()
            elif _res2["ok"]:
                st.info(_res2["reason"])
            else:
                st.error(_res2["reason"])


# ================================================================ 报告独立页面（点击「生成报告」后整页展示）
try:  # 页首「生成报告」为链接按钮（?view=report），刷新/直达也能进入报告页
    if st.query_params.get("view") == "report":
        st.session_state["_report_view"] = True
except Exception:
    pass
if st.session_state.get("_report_view"):
    _rep_md = INS.report_md(mat, mode, m0, m1, state_df, port_df)
    _rc1, _rc2, _rc3 = st.columns([7.0, 1.5, 1.7])
    with _rc1:
        st.markdown(f"""
        <div class="hero" style="margin-bottom:0">
          <div class="hero-left">
            <div class="hero-text">
              <h1>📄 美国锂离子电池进口监测报告</h1>
              <p>HS 850760 &nbsp;|&nbsp; 数据窗口 {m0} – {m1} &nbsp;|&nbsp; 口径：{mode} &nbsp;|&nbsp;
                 数据源：USA Trade Online（美国普查局）</p>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    with _rc2:
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        if st.button("← 返回看板", use_container_width=True):
            st.session_state["_report_view"] = False
            try:
                st.query_params.pop("view")
            except Exception:
                pass
            st.rerun()
    with _rc3:
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        st.download_button("⬇️ 下载报告（.md）", data=_rep_md,
                           file_name=f"美国锂电进口监测报告_{m1}_{mode}.md",
                           mime="text/markdown", type="primary", use_container_width=True)
    st.markdown(_rep_md.split("\n", 1)[1])
    st.caption("报告数字与平台各页一致（份额按对应口径金额重算）；州与口岸部分为当月口径、按所选窗口汇总。"
               "内容由平台根据载入数据自动生成，不含前瞻性预测。")
    st.stop()

# ================================================================ 页首
_qp = dict(st.query_params) if hasattr(st, "query_params") else {}
_q_keep = "&".join(f"{k}={v}" for k, v in _qp.items() if k != "view")
_rep_href = "?" + (_q_keep + "&" if _q_keep else "") + "view=report"
st.markdown(f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-badge">Li</div>
    <div class="hero-text">
      <h1>美国锂电池进口贸易监测平台</h1>
      <p class="hero-meta">HS 8507.60 &nbsp;·&nbsp; 原产国口径 &nbsp;·&nbsp; 月度更新至 {mat.index[-1]} &nbsp;·&nbsp; 数据来源：USA Trade Online</p>
    </div>
  </div>
  <div class="hero-right">
    <a class="hero-btn" href="{_rep_href}" title="按当前筛选生成完整监测报告（独立页面展示，可下载）">生成报告</a>
  </div>
</div>
<div class="hero-bar"></div>""", unsafe_allow_html=True)

# ================================================================ 自动数据更新
@st.cache_data(ttl=21600, show_spinner=False)  # 探测结果缓存 6 小时
def _probe_latest_api(_key_sig: str):
    try:
        r = CA.probe_latest_month(CA.get_api_key())
        return str(r) if r else None
    except Exception:  # noqa: BLE001 - 离线时静默跳过
        return None


_latest_api = _probe_latest_api(CA.get_api_key() or "no-key")
_cache_last0 = CA.cache_last_month()
if _latest_api and (_cache_last0 is None or pd.Period(_latest_api, freq="M") > _cache_last0):
    with st.spinner(f"检测到 Census API 已发布 {_latest_api} 数据，正在自动增量更新…"):
        _auto = CA.update_cache()
    if _auto["ok"] and _auto["fetched"]:
        st.toast(f"数据已自动更新至 {_latest_api}", icon="✅")
        D.st_cache_data_clear()
        st.rerun()


def agg_series(s: pd.Series) -> pd.Series:
    """按口径聚合：当月 / 年初至今累计（每年 1 月起累加）/ 12个月滚动"""
    if mode == "当月值":
        return s
    if mode == "年初至今累计":
        return s.groupby(s.index.year).cumsum()
    return s.rolling(12).sum()


def agg_mat(m: pd.DataFrame) -> pd.DataFrame:
    if mode == "当月值":
        return m
    if mode == "年初至今累计":
        return m.groupby(m.index.year).cumsum()
    return m.rolling(12).sum()


def share_series(c: str) -> pd.Series:
    """指定来源地的份额序列，自动跟随口径。
    累计/滚动口径下必须用累计金额重算份额（份额是相对量，不能对月度份额直接滚动求和）"""
    if mode == "当月值":
        return share[c]
    r = agg_mat(mat)
    return r[c] / r.sum(axis=1) * 100


def amounts_at(ref: pd.Period, lag_years: int = 0) -> pd.Series:
    """按当前口径返回「各来源地金额」截面；lag_years=1 取去年同期（同段累计口径一致）"""
    ref = ref - lag_years * 12
    if mode == "当月值":
        return mat.loc[ref]
    if mode == "年初至今累计":
        start = pd.Period(f"{ref.year}-01", freq="M")
        return mat.loc[(mat.index >= start) & (mat.index <= ref)].sum()
    return mat.loc[(mat.index >= ref - 11) & (mat.index <= ref)].sum()


def sel_mask(idx):
    return [m0 <= m <= m1 for m in idx]


# ================================================================ 绘图工具
BLUE = "#2E86AB"
NAVY = "#12355B"

# 大洲固定配色（亚洲置红，突出中国所在大洲）
CONT_COLORS = {"亚洲": "#D64541", "欧洲": "#2E6DA4", "北美洲": "#7F8C8D",
               "南美洲": "#E67E22", "大洋洲": "#16A085", "非洲": "#B7950B",
               "其他": "#B4B2A9"}


def style_fig(fig, height=380, legend_h=True, margin=None):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=42 if legend_h else 18, b=10) if margin is None else margin,
        font=dict(family="Noto Sans SC, sans-serif", size=12.5, color="#3A3A38"),
        plot_bgcolor="white", paper_bgcolor="white",
        hovermode="x unified" if legend_h else "closest",
        legend=dict(orientation="h", y=1.08, x=0, title="") if legend_h else {},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F0EEE9", gridwidth=1, linecolor="#D8D6D0", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#F0EEE9", gridwidth=1, linecolor="#D8D6D0", zeroline=False, tickformat=",.0f")
    return fig


def vline_policy(fig, label="2024-09 301关税调整"):
    """手动绘制政策虚线（shape + annotation），避开 plotly add_vline 内部的日期算术兼容性问题"""
    fig.add_shape(type="line", xref="x", yref="paper",
                  x0=POLICY_TS, x1=POLICY_TS, y0=0, y1=1,
                  line=dict(width=1.4, dash="dash", color="#D64541"))
    if not label:
        return
    fig.add_annotation(xref="x", yref="paper", x=POLICY_TS, y=1.0, yanchor="top",
                       text=label, showarrow=False,
                       font=dict(size=11, color="#12355B"),
                       bgcolor="rgba(255,255,255,0.85)", bordercolor="#D8D6D0", borderwidth=1,
                       borderpad=2, align="left", xshift=4)


def sec(title, sub=""):
    st.markdown(f'<p class="sec-title">{title}</p>'
                + (f'<p class="sec-sub">{sub}</p>' if sub else ""), unsafe_allow_html=True)


def top_countries_in_range(n=None, exclude=None):
    n = n or topn
    totals = mat.loc[sel_range].sum().sort_values(ascending=False)
    if exclude:
        totals = totals.drop([c for c in exclude if c in totals.index])
    return list(totals.head(n).index)


# ================================================================ 10 位 HTS 品类视图
CAT_COLORS = {"车用动力电池": "#2E86AB", "其他锂电": "#E8A33D",
              "储能电池系统": "#D64541", "其他锂电（旧口径）": "#E8A33D"}


def _policy_hts10(w: int):
    """政策冲击页 · 10 位 HTS 品类视图（车用动力电池 / 其他锂电 / 储能电池系统）"""
    if not H.available():
        st.info("10 位 HTS 品类数据文件（data/raw/hts10/ 下两个 Excel）未随部署上传，该视图暂不可用；其余分析不受影响。")
        return
    d = H.data()
    m = H.mat_cat(d).reindex(columns=["车用动力电池", "其他锂电"]).fillna(0)
    s = H.share_of_total(m)
    mc = H.mat_cat(d, col="cat").reindex(
        columns=["车用动力电池", "其他锂电（旧口径）", "储能电池系统", "其他锂电"]).fillna(0)

    P = D.POLICY_DATE
    pre = [p for p in (P - i for i in range(1, w + 1)) if p in m.index]
    post = [p for p in (P + i for i in range(w)) if p in m.index]
    if len(pre) < 3 or len(post) < 3:
        st.warning("当前数据范围不足以覆盖该事件窗口，请更换窗口。")
        return

    a_pre, a_post = m.loc[pre].mean(), m.loc[post].mean()
    s_pre, s_post = s.loc[pre].mean(), s.loc[post].mean()
    cn = d[d["country"] == "中国"]
    cn_sh = {}
    for cat in ["车用动力电池", "其他锂电"]:
        v = cn[cn["cat_cont"] == cat].groupby("month")["value"].sum().reindex(m.index).fillna(0)
        cn_sh[cat] = (v / m[cat].replace(0, np.nan) * 100)

    new_start = pd.Period("2026-02", freq="M")
    stm = mc["储能电池系统"][mc.index >= new_start]
    oth90 = mc["其他锂电"][mc.index >= new_start]
    tot_new = mc[mc.index >= new_start].sum(axis=1)

    def _kpi(label, val, sub, tone="flat"):
        color = {"up": "#C0392B", "down": "#1E8449", "flat": "#6B6B68"}[tone]
        return (f'<div class="kpi"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{val}</div>'
                f'<div class="kpi-delta"><span style="color:{color}">{sub}</span></div></div>')

    def _chg(a, b):
        return (b / a - 1) * 100 if a else np.nan

    st.markdown('<div class="kpi-row">' + "".join([
        _kpi("车用动力电池（8507600010）· 政策后月均",
             f"{a_post['车用动力电池']/1e8:,.2f} 亿美元",
             f"政策前 {a_pre['车用动力电池']/1e8:,.2f} 亿美元（{_chg(a_pre['车用动力电池'], a_post['车用动力电池']):+.1f}%）"
             f"· 占锂电 {s_post['车用动力电池']:.1f}%",
             "up" if a_post["车用动力电池"] > a_pre["车用动力电池"] else "down"),
        _kpi("其他锂电（8507600020 → 0030+0090）· 政策后月均",
             f"{a_post['其他锂电']/1e8:,.2f} 亿美元",
             f"政策前 {a_pre['其他锂电']/1e8:,.2f} 亿美元（{_chg(a_pre['其他锂电'], a_post['其他锂电']):+.1f}%）"
             f"· 占锂电 {s_post['其他锂电']:.1f}%",
             "up" if a_post["其他锂电"] > a_pre["其他锂电"] else "down"),
        _kpi("储能电池系统（8507600030）· 2026-02 起月均",
             f"{stm.mean()/1e8:,.2f} 亿美元",
             f"占锂电 {stm.sum()/tot_new.sum()*100:.1f}%（新设税号，仅 {len(stm)} 个月样本）", "flat"),
        _kpi("其他锂电（8507600090）· 2026-02 起月均",
             f"{oth90.mean()/1e8:,.2f} 亿美元",
             f"占锂电 {oth90.sum()/tot_new.sum()*100:.1f}%（消费电子、电动工具等残余类）", "flat"),
    ]) + "</div>", unsafe_allow_html=True)

    # ---------------- 结构演变
    sec("品类结构：车用动力电池与其他锂电的份额演变",
        f"100% 堆叠面积（%）；HTS 10 位自 {m.index[0]} 起统计，红色虚线为 2024-09 301 关税时点")
    fig = go.Figure()
    for cat in ["其他锂电", "车用动力电池"]:
        fig.add_scatter(x=ts(s.index), y=s[cat], name=cat, mode="lines", stackgroup="one",
                        line=dict(width=0.8, color=CAT_COLORS[cat]),
                        customdata=m[cat] / 1e8,
                        hovertemplate="%{fullData.name}：%{y:.1f}%（%{customdata:.2f} 亿美元）<extra></extra>")
    vline_policy(fig)
    fig = style_fig(fig, 360)
    fig.update_yaxes(title="占锂电总进口份额（%）", range=[0, 100], ticksuffix="%")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"注：10 位数据自 {m.index[0]} 起至 {m.index[-1]}（比 6 位平台多一个月，因 Census 10 位口径发布略早）；"
               "2026-02 起「其他锂电」为 8507600030（储能电池系统）与 8507600090（其他）的合计，"
               "与拆分前的 8507600020 保持连续可比；两类合计与原 6 位总额逐月一致。")

    # ---------------- 分品类：金额 + 中国份额
    c1, c2 = st.columns(2)
    for col, cat in zip([c1, c2], ["车用动力电池", "其他锂电"]):
        with col:
            sec(f"{cat}：进口额与中国份额",
                "柱=月度进口额（亿美元，左轴）；线=中国在该品类的份额（%，右轴）")
            fig = go.Figure()
            fig.add_bar(x=ts(m.index), y=m[cat] / 1e8, name="进口额",
                        marker_color=CAT_COLORS[cat], opacity=0.9,
                        hovertemplate="%{y:.2f} 亿美元<extra></extra>")
            fig.add_scatter(x=ts(cn_sh[cat].index), y=cn_sh[cat], name="中国份额", yaxis="y2",
                            line=dict(color="#12355B", width=1.9),
                            hovertemplate="中国份额 %{y:.1f}%<extra></extra>")
            fig.add_shape(type="line", xref="x", yref="paper", x0=POLICY_TS, x1=POLICY_TS,
                          y0=0, y1=1, line=dict(width=1.2, dash="dash", color="#D64541"))
            fig = style_fig(fig, 340)
            fig.update_yaxes(title="进口额（亿美元）")
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                          range=[0, 100], ticksuffix="%", title="中国份额（%）",
                                          tickfont=dict(size=11)))
            st.plotly_chart(fig, width="stretch")
    st.caption(f"注：政策时点 2024-09-27，仅对车用动力电池（8507600010）即时生效；"
               f"中国在车用电池的份额由 2024 年 {cn_sh['车用动力电池'][cn_sh['车用动力电池'].index.year == 2024].mean():.1f}% "
               f"降至 2026 年 {cn_sh['车用动力电池'][cn_sh['车用动力电池'].index.year == 2026].mean():.1f}%；"
               f"其他锂电的 301 关税自 2026-01 起执行，2026 年中国份额为 "
               f"{cn_sh['其他锂电'][cn_sh['其他锂电'].index.year == 2026].mean():.1f}%。")

    # ---------------- 政策前后对比
    c1, c2 = st.columns([1.1, 1])
    with c1:
        sec(f"政策前后：品类月均进口额（±{w} 个月）", "单位：亿美元/月；百分比为政策后相对政策前的变化")
        fig = go.Figure()
        fig.add_bar(x=["车用动力电池", "其他锂电"],
                    y=[a_pre["车用动力电池"] / 1e8, a_pre["其他锂电"] / 1e8],
                    name=f"政策前（{pre[0]}–{pre[-1]}）", marker_color="#9DC3D8",
                    text=[f"{a_pre['车用动力电池']/1e8:.2f}", f"{a_pre['其他锂电']/1e8:.2f}"],
                    textposition="outside")
        fig.add_bar(x=["车用动力电池", "其他锂电"],
                    y=[a_post["车用动力电池"] / 1e8, a_post["其他锂电"] / 1e8],
                    name=f"政策后（{post[0]}–{post[-1]}）", marker_color="#D64541",
                    text=[f"{a_post['车用动力电池']/1e8:.2f}（{_chg(a_pre['车用动力电池'], a_post['车用动力电池']):+.1f}%）",
                          f"{a_post['其他锂电']/1e8:.2f}（{_chg(a_pre['其他锂电'], a_post['其他锂电']):+.1f}%）"],
                    textposition="outside")
        fig = style_fig(fig, 380)
        fig.update_yaxes(title="月均进口额（亿美元）")
        fig.update_layout(barmode="group")
        st.plotly_chart(fig, width="stretch")
    with c2:
        sec("品类结构：政策前后对比", "各自归一化为 100%")
        fig = go.Figure()
        for i, (lab, ss) in enumerate([("政策前", s_pre), ("政策后", s_post)]):
            for cat in ["其他锂电", "车用动力电池"]:
                fig.add_bar(y=[lab], x=[ss[cat]], orientation="h", name=cat,
                            marker_color=CAT_COLORS[cat], showlegend=(i == 0),
                            text=[f"{ss[cat]:.1f}%"], textposition="inside",
                            hovertemplate=f"{cat} %{{x:.1f}}%<extra></extra>")
        fig = style_fig(fig, 300, legend_h=True)
        fig.update_layout(barmode="stack")
        fig.update_xaxes(title="占锂电总进口份额（%）", range=[0, 100], ticksuffix="%")
        fig.update_yaxes(title="")
        st.plotly_chart(fig, width="stretch")

    # ---------------- 2026-02 拆分
    sec("2026-02 起：其他锂电拆分为储能电池系统与其他",
        f"月度进口额（亿美元），共 {len(stm)} 个月；8507600020 自 2026-02 停止使用")
    fig = go.Figure()
    for cat in ["车用动力电池", "储能电池系统", "其他锂电"]:
        fig.add_bar(x=ts(stm.index), y=mc[cat][mc.index >= new_start] / 1e8, name=cat,
                    marker_color=CAT_COLORS[cat],
                    hovertemplate="%{y:.2f} 亿美元<extra></extra>")
    fig = style_fig(fig, 360)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="进口额（亿美元）")
    st.plotly_chart(fig, width="stretch")
    st.caption("注：8507600030 为「完整封装于壳体内的储能电池系统」（HTS 统计注释 2：具备充放电功能、含电池管理与配套部件、"
               "容量 ≥1 千瓦时、整体封装）；8507600090 为其余锂离子电池（消费电子、电动工具等）。"
               "该拆分使储能电池首次可被单独追踪，恰逢非动力锂电 301 关税 2026-01 起执行，可用于观察关税对储能的传导。")

    # ---------------- 明细表
    sec("品类明细：政策前后对比", f"政策前 {w} 个月 vs 政策后 {w} 个月")
    rows = []
    for cat in ["车用动力电池", "其他锂电"]:
        _c = cn_sh[cat]
        rows.append({
            "品类": cat,
            "政策前月均(亿美元)": a_pre[cat] / 1e8,
            "政策后月均(亿美元)": a_post[cat] / 1e8,
            "月均额变化(%)": _chg(a_pre[cat], a_post[cat]),
            "政策前结构份额(%)": s_pre[cat],
            "政策后结构份额(%)": s_post[cat],
            "政策前中国份额(%)": _c.loc[pre].mean(),
            "政策后中国份额(%)": _c.loc[post].mean(),
        })
    for cat, code in [("储能电池系统", "8507600030"), ("其他锂电", "8507600090")]:
        _v = mc[cat][mc.index >= new_start]
        _v_cn = cn[cn["hts10"] == code].groupby("month")["value"].sum().reindex(_v.index).fillna(0)
        rows.append({
            "品类": f"{cat}（{code}，2026-02 起）",
            "政策前月均(亿美元)": np.nan, "政策后月均(亿美元)": _v.mean() / 1e8,
            "月均额变化(%)": np.nan, "政策前结构份额(%)": np.nan,
            "政策后结构份额(%)": _v.sum() / tot_new.sum() * 100,
            "政策前中国份额(%)": np.nan, "政策后中国份额(%)": (_v_cn.sum() / _v.sum() * 100) if _v.sum() else np.nan,
        })
    tbl = pd.DataFrame(rows)
    for c in ["政策前月均(亿美元)", "政策后月均(亿美元)"]:
        tbl[c] = tbl[c].map(lambda x: "—" if pd.isna(x) else f"{x:,.2f}")
    for c in ["月均额变化(%)"]:
        tbl[c] = tbl[c].map(lambda x: "—" if pd.isna(x) else f"{x:+.1f}")
    for c in ["政策前结构份额(%)", "政策后结构份额(%)", "政策前中国份额(%)", "政策后中国份额(%)"]:
        tbl[c] = tbl[c].map(lambda x: "—" if pd.isna(x) else f"{x:.1f}")
    st.dataframe(tbl, width="stretch", hide_index=True)
    st.caption("注：「结构份额」= 该品类占锂电总进口的比例；「中国份额」= 中国在该品类进口中的占比，两者含义不同。"
               "储能与其他两类仅 2026-02 起可分离，故政策前后对比留空；其月均与份额为 2026-02 至最新月的均值。")


# ================================================================ 各页底部 AI 解读
def ai_block(pages, **kw):
    """在页面底部渲染该页专属的 AI 解读（结论均来自当前筛选下的实时计算）；
    pages 可为单个页面名，也可为列表（合并页签时按顺序合并各节）"""
    if isinstance(pages, str):
        pages = [pages]
    _secs = []
    for _p in pages:
        _secs += INS.ai_reading(_p, mat, mode, m0, m1, state_df, port_df, **kw)
    if not _secs:
        return
    st.markdown("---")
    st.markdown('<p class="sec-title">🤖 AI 解读</p>'
                '<p class="sec-sub">本页结论由当前筛选自动计算，每条均附具体数值与对比窗口</p>',
                unsafe_allow_html=True)
    for _i, _sec in enumerate(_secs):
        with st.expander(_sec["title"], expanded=(_i == 0)):
            st.markdown(_sec["body"])
    st.caption("解读随「数据周期 / 统计口径」自动更新；基于官方贸易统计，不含对未来走势的预测。")


# ================================================================ TAB 结构
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📈 总览仪表盘", "🌍 来源地结构与集中度", "📊 中国看板",
     "⚡ 政策冲击分析", "🗺️ 州与口岸分布", "📖 数据说明"])

# ==================================================================
# TAB 1 总览仪表盘
# ==================================================================
with tab1:
    tot_sel = agg_series(tot)
    yoy_tot = D.yoy(tot)
    # KPI 参考月 = 所选区间末端月，随侧边栏「数据周期」联动
    ref_m = m1

    def _delta_html(text, kind):
        if not text:
            return ""
        return f'<div class="kpi-delta"><span class="pd-{kind}">{text}</span></div>'

    # ---- 按口径取「截面金额」：当月 / 年初至今累计 / 12个月滚动 ----
    _amt = amounts_at(ref_m)
    _amt_ly = amounts_at(ref_m, lag_years=1) if (ref_m - 12) in mat.index else None
    _total = float(_amt.sum())
    _total_ly = float(_amt_ly.sum()) if _amt_ly is not None else np.nan
    _yoy_val = (_total / _total_ly - 1) * 100 if (_total_ly and pd.notna(_total_ly)) else np.nan
    _cn = float(_amt.get("中国", 0))
    _cn_ly = float(_amt_ly.get("中国", 0)) if _amt_ly is not None else np.nan
    _cn_sh = _cn / _total * 100 if _total else np.nan
    _cn_sh_ly = (_cn_ly / _total_ly * 100) if (_amt_ly is not None and _total_ly) else np.nan
    _p = _amt / _total if _total else _amt
    _cr5 = float(_p.nlargest(5).sum() * 100)
    _hhi = float((_p ** 2).sum())
    _cr5_ly = float((_amt_ly / _amt_ly.sum()).nlargest(5).sum() * 100) if _amt_ly is not None else np.nan

    if mode == "当月值":
        _lab_v = f"{ref_m} 当月进口额"
        _lab_s = f"{ref_m} 中国份额"
        _lab_prev = "较去年同期"
        _cmp_cr5 = f"去年同期 {_cr5_ly:.1f}%" if pd.notna(_cr5_ly) else None
    elif mode == "年初至今累计":
        _lab_v = f"{ref_m.year} 年 1–{ref_m.month} 月累计进口额"
        _lab_s = f"累计中国份额（1–{ref_m.month} 月）"
        _lab_prev = "较去年同期同段"
        _cmp_cr5 = f"去年同期 {_cr5_ly:.1f}%" if pd.notna(_cr5_ly) else None
    else:
        _lab_v = f"截至 {ref_m} 的 12 个月累计进口额"
        _lab_s = "12 个月滚动中国份额"
        _lab_prev = "较上一个 12 个月"
        _cmp_cr5 = f"去年同期 {_cr5_ly:.1f}%" if pd.notna(_cr5_ly) else None

    _d1 = f"{_yoy_val:+.1f}% 同比" if pd.notna(_yoy_val) else None
    _d_s = f"{(_cn_sh - _cn_sh_ly):+.1f} pp {_lab_prev}" if pd.notna(_cn_sh_ly) else None
    _sel_total = float(tot.loc[sel_range].sum())
    _v5 = f"{_sel_total/1e8:,.1f} 亿美元"
    kpi_html = f"""
<div class="kpi-row">
  <div class="kpi"><div class="kpi-label">{_lab_v}</div>
    <div class="kpi-value">{_total/1e8:,.2f} 亿美元</div>{_delta_html(_d1, "neg" if (_d1 and not _d1.startswith("+")) else "pos")}</div>
  <div class="kpi"><div class="kpi-label">{_lab_s}</div>
    <div class="kpi-value">{_cn_sh:.1f}%</div>{_delta_html(_d_s, "flat")}</div>
  <div class="kpi"><div class="kpi-label">CR5 集中度</div>
    <div class="kpi-value">{_cr5:.1f}%</div>{_delta_html(_cmp_cr5, "flat")}</div>
  <div class="kpi"><div class="kpi-label">HHI 指数</div>
    <div class="kpi-value">{_hhi:.3f}</div>{_delta_html("0-1，越高越集中", "flat")}</div>
  <div class="kpi"><div class="kpi-label">所选区间累计（{m0}–{m1}）</div>
    <div class="kpi-value">{_v5}</div>{_delta_html(f"{len(sel_range)} 个月合计", "flat")}</div>
</div>"""
    st.markdown(kpi_html, unsafe_allow_html=True)

    sec("美国锂离子电池进口总额走势",
        f"柱状为当月进口额（左轴），折线为{'年初至今累计' if mode=='年初至今累计' else '12 个月滚动累计'}"
        f"（右轴），红色虚线为 2024 年 301 关税调整")

    fig = go.Figure()
    fig.add_bar(x=T, y=tot / 1e8, name="当月进口额（亿美元）",
                marker_color="#9DC3D8", hovertemplate="%{x|%Y-%m}<br>%{y:,.2f} 亿美元<extra></extra>")
    _line_name = "年初至今累计（亿美元）" if mode == "年初至今累计" else "12个月滚动累计（十亿美元）"
    _line_y = tot_sel / (1e8 if mode == "年初至今累计" else 1e9)
    fig.add_scatter(x=T, y=_line_y, name=_line_name,
                    line=dict(color=NAVY, width=2.4),
                    hovertemplate="%{x|%Y-%m}<br>%{y:,.2f}<extra></extra>")
    vline_policy(fig)
    fig = style_fig(fig, 400)
    fig.update_layout(yaxis=dict(title="当月（亿美元）"),
                      yaxis2=dict(title=("累计（亿美元）" if mode == "年初至今累计" else "滚动累计（十亿美元）"),
                                  overlaying="y", side="right", showgrid=False))
    fig.update_traces(yaxis="y", selector=dict(type="bar"))
    fig.update_traces(yaxis="y2", selector=dict(type="scatter"))
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns([3, 2])
    with c1:
        sec("进口额同比增速", "同比消除季节性；红=增长，绿=下降")
        fig = go.Figure()
        colors = ["#D64541" if v >= 0 else "#27AE60" for v in yoy_tot.fillna(0)]
        fig.add_bar(x=T, y=yoy_tot, marker_color=colors, name="同比增速")
        fig.add_hline(y=0, line_width=1, line_color="#B4B2A9")
        fig = style_fig(fig, 320)
        fig.update_yaxes(title="同比（%）", tickformat=",d")
        st.plotly_chart(fig, width="stretch")
        st.caption("注：本图为**当月值**同比（消除季节性的标准做法），不随统计口径切换；"
                   "累计口径的同比请看上方 KPI 卡。")
    with c2:
        sec("月度进口额分布特征", f"{MONTHS[0].year}-{LAST_M.year} 年各日历月份进口额箱线图")
        seas = pd.DataFrame({"month_cal": [m.month for m in MONTHS], "v": (tot / 1e8).values})
        fig = px.box(seas, x="month_cal", y="v", color_discrete_sequence=[BLUE])
        fig = style_fig(fig, 320)
        fig.update_xaxes(title="月份", tickvals=list(range(1, 13)))
        fig.update_yaxes(title="当月进口额（亿美元）")
        st.plotly_chart(fig, width="stretch")

    ai_block("overview")

# ==================================================================
# TAB 2 来源地结构
# ==================================================================
with tab2:
    # ---------------- 分组方式（两种视图共用下方的侧边栏日期筛选）
    _grp_opt = ["按细分来源地", "按大洲"]
    if hasattr(st, "segmented_control"):
        _grp = st.segmented_control(
            "来源地分组方式", _grp_opt, default=_grp_opt[0], key="_src_group",
            help="按大洲：以 Census 原产地代码首位归类（1/2 开头=北美洲、3=南美洲、4=欧洲、"
                 "5=亚洲、6=大洋洲、7=非洲），先把同一大洲的原产地金额加总，再计算份额")
    else:
        _grp = st.radio("来源地分组方式", _grp_opt, horizontal=True, key="_src_group")
    by_cont = (_grp or _grp_opt[0]) == "按大洲"
    gmat = cont_mat if by_cont else mat
    gshare = cont_share if by_cont else share
    gp = CONT_COLORS if by_cont else D.COUNTRY_COLORS
    unit = "大洲" if by_cont else "来源地"
    if by_cont:
        groups = [c for c in cont_mat.columns]
        _note = ("各大洲金额先加总、再重算份额；归类依据为原产地代码首位，"
                 "与侧边栏数据周期（" + f"{m0}–{m1}" + "）联动")
    else:
        groups = top_countries_in_range()
        _note = f"展示 Top {topn} 来源地及其余地区合计份额"

    sec(f"{unit}份额演变（堆叠面积）",
        f"{_note}；口径：{'12个月滚动' if mode=='12个月滚动累计' else ('年初至今累计' if mode=='年初至今累计' else '当月')}")
    mat_sel = agg_mat(gmat)
    stack = mat_sel[groups].copy()
    if not by_cont:      # 大洲视图本身就是全口径加总，无需「其他」兜底
        stack["其他"] = mat_sel[[c for c in mat_sel.columns if c not in groups]].sum(axis=1)
    share_stack = stack.div(stack.sum(axis=1), axis=0) * 100

    fig = go.Figure()
    for c in list(stack.columns):
        fig.add_scatter(x=ts(stack.index), y=share_stack[c], name=c, stackgroup="s",
                        line=dict(width=0.6, color=gp.get(c, "#B4B2A9")),
                        fillcolor=gp.get(c, "#B4B2A9"),
                        hovertemplate="%{x|%Y-%m} " + c + " 份额 %{y:.1f}%<extra></extra>")
    vline_policy(fig)
    fig = style_fig(fig, 440)
    fig.update_yaxes(title="份额（%）", range=[0, 100], tickformat=",d")
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns([2, 3])
    with c1:
        sec("所选周期平均份额排名", f"{m0} ~ {m1} 平均月度份额（{unit}）")
        avg_share = gshare.loc[sel_range].mean().sort_values(ascending=False).head(10)
        fig = go.Figure()
        fig.add_bar(x=avg_share.values[::-1], y=list(avg_share.index)[::-1], orientation="h",
                    marker_color=[gp.get(c, "#B4B2A9") for c in avg_share.index][::-1],
                    text=[f"{v:.1f}%" for v in avg_share.values[::-1]], textposition="outside",
                    hovertemplate="%{y} 平均份额 %{x:.1f}%<extra></extra>")
        fig = style_fig(fig, 400, legend_h=False)
        fig.update_xaxes(title="平均份额（%）", range=[0, avg_share.max() * 1.2], tickformat=",d")
        fig.update_yaxes(tickfont=dict(size=12.5))
        st.plotly_chart(fig, width="stretch")
    with c2:
        sec(f"主要{unit}排名变化",
            "每个月份按份额排名，连线展示排名的时间演变（越小越靠前）")
        bump_countries = groups[:8] if by_cont else top_countries_in_range(8)
        ranks = gshare[bump_countries].loc[sel_range].rank(axis=1, ascending=False)
        fig = go.Figure()
        for c in bump_countries:
            is_cn = (c == "中国" or c == "亚洲")
            fig.add_scatter(x=ts(ranks.index), y=ranks[c], name=c, mode="lines+markers",
                            line=dict(color=gp.get(c, "#B4B2A9"), width=3 if is_cn else 2.2),
                            marker=dict(size=7 if is_cn else 6), cliponaxis=False,
                            hovertemplate="%{x|%Y-%m} " + c + " 排名第 %{y:.0f}<extra></extra>")
        fig = style_fig(fig, 400)
        # 显式范围 + 上下留白，防止第 1 名的线被绘图区顶边裁剪
        fig.update_yaxes(title="份额排名", range=[len(bump_countries) + 0.6, 0.4],
                         tickvals=list(range(1, len(bump_countries) + 1)), tickformat=",d")
        st.plotly_chart(fig, width="stretch")

    if not by_cont:
        sec("东亚三大供给国对比（中日韩）",
            "份额此消彼长：中国 vs 韩国、日本")
        fig = go.Figure()
        for c in ["中国", "韩国", "日本"]:
            if c in share.columns:
                fig.add_scatter(x=T, y=share_series(c),
                                name=c, line=dict(color=D.COUNTRY_COLORS[c], width=2.2))
        vline_policy(fig)
        fig = style_fig(fig, 380)
        fig.update_yaxes(title="份额（%）", tickformat=",d")
        st.plotly_chart(fig, width="stretch")
    else:
        sec("各大洲月度进口额",
            "同一大洲的原产地金额加总后的绝对规模（亿美元），堆叠展示总量与结构；"
            "份额看上方堆叠面积图，此处看盘子大小")
        fig = go.Figure()
        for c in groups[::-1]:
            fig.add_bar(x=T, y=agg_series(gmat[c]) / 1e8, name=c,
                        marker_color=gp.get(c, "#B4B2A9"),
                        hovertemplate="%{x|%Y-%m} " + c + " %{y:,.1f} 亿美元<extra></extra>")
        vline_policy(fig)
        fig = style_fig(fig, 380)
        fig.update_layout(barmode="stack")
        fig.update_yaxes(title="进口额（亿美元）", tickformat=",d")
        st.plotly_chart(fig, width="stretch")

    # ================================================================
    # 集中度与多元化（原独立页签，合并至此）
    # ================================================================
    st.markdown("---")
    sec("市场集中度：CR5 与 CR10",
        "CR5=前五大来源地份额合计；CR10=前十大来源地份额合计，CR10−CR5 的差距越大，说明第 6~10 名来源地的重要性越高")
    fig = go.Figure()
    fig.add_scatter(x=T, y=conc["CR5"], name="CR5（%）", line=dict(color=BLUE, width=2.2))
    fig.add_scatter(x=T, y=conc10["CR10"], name="CR10（%）", line=dict(color="#7FB3D5", width=1.8, dash="dot"))
    vline_policy(fig)
    fig = style_fig(fig, 360)
    fig.update_yaxes(title="集中度（%）", tickformat=",d")
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        sec("HHI 指数", "0-1，越高越集中")
        fig = go.Figure()
        fig.add_scatter(x=T, y=conc["HHI"], name="HHI", line=dict(color=NAVY, width=2.2), fill="tozeroy", fillcolor="rgba(18,53,91,.08)")
        vline_policy(fig)
        fig = style_fig(fig, 330, legend_h=False)
        fig.update_yaxes(tickformat=".3f")
        st.plotly_chart(fig, width="stretch")
    with c2:
        sec("多元化指数（1 − HHI）与熵指数", "越高越多元；美国进口来源趋于集中还是分散，一图可见")
        fig = go.Figure()
        fig.add_scatter(x=T, y=1 - conc["HHI"], name="1 − HHI", line=dict(color="#27AE60", width=2.2))
        fig.add_scatter(x=T, y=conc["熵指数"] / np.log(mat.shape[1]), name="归一化熵指数", line=dict(color="#E67E22", width=1.8, dash="dot"))
        vline_policy(fig)
        fig = style_fig(fig, 330)
        fig.update_yaxes(tickformat=".2f")
        st.plotly_chart(fig, width="stretch")

    sec("主要来源地份额明细表", "近 12 个月均值 vs 此前 12 个月均值，观察份额消长")
    if len(sel_range) >= 24:
        now12, prev12 = sel_range[-12:], sel_range[-24:-12]
        tbl = pd.DataFrame({
            "地区": share.columns,
            "此前12个月份额(%)": share.loc[prev12].mean().values,
            "近12个月份额(%)": share.loc[now12].mean().values,
        })
        tbl["变化(pp)"] = tbl["近12个月份额(%)"] - tbl["此前12个月份额(%)"]
        tbl["份额排名"] = tbl["近12个月份额(%)"].rank(ascending=False, method="min").astype(int)
        tbl = tbl.sort_values("份额排名").head(12)
        tbl["此前12个月份额(%)"] = tbl["此前12个月份额(%)"].map("{:.2f}".format)
        tbl["近12个月份额(%)"] = tbl["近12个月份额(%)"].map("{:.2f}".format)
        tbl["变化(pp)"] = tbl["变化(pp)"].map("{:+.2f}".format)
        tbl = tbl[["份额排名", "地区", "此前12个月份额(%)", "近12个月份额(%)", "变化(pp)"]]
        st.dataframe(tbl, width="stretch", hide_index=True, height=430)
    else:
        st.info("所选周期不足 24 个月，请拉长时间范围。")

    ai_block(["structure", "concentration"], continent=by_cont)

# ==================================================================
# TAB 3 中国竞争力
# ==================================================================
with tab3:
    china_v = mat["中国"]
    china_share_s = share["中国"]

    # 与总览一致：按口径取截面（当月 / 年初至今累计 / 12个月滚动）
    _cn_amt = amounts_at(ref_m)
    _cn_amt_ly = amounts_at(ref_m, lag_years=1) if (ref_m - 12) in mat.index else None
    _cn_v = float(_cn_amt.get("中国", 0))
    _cn_v_ly = float(_cn_amt_ly.get("中国", 0)) if _cn_amt_ly is not None else np.nan
    _c_yoy = (_cn_v / _cn_v_ly - 1) * 100 if (_cn_v_ly and pd.notna(_cn_v_ly)) else np.nan
    _cn_sh_now = _cn_v / float(_cn_amt.sum()) * 100 if _cn_amt.sum() else np.nan
    _cn_sh_ly = (_cn_v_ly / float(_cn_amt_ly.sum()) * 100) if (_cn_amt_ly is not None and _cn_amt_ly.sum()) else np.nan
    _d1 = f"同比 {_c_yoy:+.1f}%" if pd.notna(_c_yoy) else None
    _d1_kind = "neg" if (pd.notna(_c_yoy) and _c_yoy < 0) else "pos"
    if mode == "当月值":
        _lab_cv, _lab_cs, _lab_cmp = f"{ref_m} 自华进口额", f"{ref_m} 中国份额", "较去年同期"
    elif mode == "年初至今累计":
        _lab_cv = f"{ref_m.year} 年 1–{ref_m.month} 月自华累计进口额"
        _lab_cs = f"累计中国份额（1–{ref_m.month} 月）"
        _lab_cmp = "较去年同期同段"
    else:
        _lab_cv, _lab_cs, _lab_cmp = "截至该月的12个月自华累计", "12 个月滚动中国份额", "较上一个 12 个月"
    _d2 = (f"{(_cn_sh_now - _cn_sh_ly):+.1f} pp {_lab_cmp}" if pd.notna(_cn_sh_ly)
           else (f"近12个月均值 {china_share_s.loc[sel_range[-12:]].mean():.1f}%" if len(sel_range) >= 12 else None))
    # 峰值在所选区间内计算，随「数据周期」联动
    _share_sel = china_share_s.loc[sel_range]
    _peak_v = _share_sel.max()
    _peak_m = _share_sel.idxmax()
    _kpi3 = f"""
<div class="kpi-row">
  <div class="kpi"><div class="kpi-label">{_lab_cv}</div>
    <div class="kpi-value">{_cn_v/1e8:,.2f} 亿美元</div>{_delta_html(_d1, _d1_kind)}</div>
  <div class="kpi"><div class="kpi-label">{_lab_cs}</div>
    <div class="kpi-value">{_cn_sh_now:.1f}%</div>{_delta_html(_d2, "flat")}</div>
  <div class="kpi"><div class="kpi-label">份额峰值（所选区间）</div>
    <div class="kpi-value">{_peak_v:.1f}%</div>{_delta_html(f"出现在 {_peak_m}", "flat")}</div>
</div>"""
    st.markdown(_kpi3, unsafe_allow_html=True)

    sec("自华进口额与份额双轴走势",
        f"柱=自华进口额（亿美元，{'12个月滚动累计' if mode != '当月值' else '当月值'}），"
        f"线=份额（%，{'滚动份额由滚动金额重算' if mode != '当月值' else '当月'}，右轴）；随侧边栏「统计口径」联动")
    fig = go.Figure()
    fig.add_bar(x=T, y=agg_series(china_v) / 1e8, name="自华进口额（亿美元）", marker_color="#D64541",
                opacity=0.85, hovertemplate="%{x|%Y-%m}<br>%{y:,.2f} 亿美元<extra></extra>")
    fig.add_scatter(x=T, y=share_series("中国"), name="中国份额（%）", yaxis="y2",
                    line=dict(color=NAVY, width=2.2), hovertemplate="%{x|%Y-%m} 份额 %{y:.1f}%<extra></extra>")
    vline_policy(fig)
    fig = style_fig(fig, 380)
    fig.update_layout(yaxis=dict(title="进口额（亿美元）"),
                      yaxis2=dict(title="份额（%）", overlaying="y", side="right", showgrid=False, tickformat=",d"))
    st.plotly_chart(fig, width="stretch")

    sec("中国份额变动与其他来源地份额变化",
        "对比所选周期首末各12个月。份额具有相对性：金额不变也可能因其他来源地下降而份额上升，"
        "故并列展示「份额变化（pp）」与「进口额变化（%）」以便相互印证；红=上升、绿=下降")
    if len(sel_range) >= 24:
        head12 = sel_range[:12]
        tail12 = sel_range[-12:]
        ds = (share.loc[tail12].mean() - share.loc[head12].mean()).sort_values()
        ds_show = ds[ds.abs() > 0.05]
        _hv = mat.loc[head12].mean().reindex(ds_show.index)
        _tv = mat.loc[tail12].mean().reindex(ds_show.index)
        _BASE_MIN = 1e6  # 首期12个月月均进口额下限（美元），低于此基数不计算百分比
        dv_raw = (_tv / _hv.replace(0, np.nan) - 1) * 100
        dv_x, dv_txt, _muted = [], [], []
        for _v, _h in zip(dv_raw.values, _hv.values):
            _base_small = (not pd.isna(_h)) and _h < _BASE_MIN
            if pd.isna(_v):
                dv_x.append(0.0); dv_txt.append("新增"); _muted.append(True)
            elif _base_small:
                dv_x.append(0.0); dv_txt.append("基数过小"); _muted.append(True)
            else:
                dv_x.append(float(_v)); dv_txt.append(f"{_v:+.1f}%"); _muted.append(False)
        _cd = list(zip(ds_show.values, dv_txt))
        _h = max(340, 28 * len(ds_show))
        _colors = ["#27AE60" if v < 0 else "#D64541" for v in ds_show.values]
        dv_colors = ["rgba(0,0,0,0)" if m else c for m, c in zip(_muted, _colors)]
        cL, cR = st.columns(2)
        with cL:
            st.markdown('<p style="font-weight:700;color:#3A3A38;margin:0 0 4px 2px;">份额变化（百分点）</p>',
                        unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_bar(x=ds_show.values, y=list(ds_show.index), orientation="h",
                        marker_color=_colors, customdata=_cd,
                        text=[f"{v:+.1f}" for v in ds_show.values], textposition="outside",
                        hovertemplate="%{y}：份额 %{customdata[0]:+.1f} pp · 进口额 %{customdata[1]}<extra></extra>")
            fig = style_fig(fig, _h, legend_h=False)
            fig.update_xaxes(title="份额变化（pp）", tickformat="+,d")
            st.plotly_chart(fig, width="stretch")
        with cR:
            st.markdown('<p style="font-weight:700;color:#3A3A38;margin:0 0 4px 2px;">进口额变化（%）</p>',
                        unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_bar(x=dv_x, y=list(ds_show.index), orientation="h",
                        marker_color=dv_colors, customdata=_cd,
                        text=dv_txt, textposition="outside",
                        hovertemplate="%{y}：份额 %{customdata[0]:+.1f} pp · 进口额 %{customdata[1]}<extra></extra>")
            fig = style_fig(fig, _h, legend_h=False)
            fig.update_xaxes(title="进口额变化（%）", tickformat="+,d")
            st.plotly_chart(fig, width="stretch")
        st.caption("注：① 仅展示份额变化绝对值 > 0.05 pp 的来源地；② 「新增」表示首期 12 个月无进口记录；"
                   "③ 「基数过小」表示首期月均进口额低于 100 万美元，百分比变化失真（小基数效应），故不绘制条形。"
                   "两图按份额变化同序排列，便于对照。")
    else:
        st.info("所选周期不足 24 个月，无法计算首末对比，请拉长时间范围。")

    ai_block("china")

# ==================================================================
# TAB 4 政策冲击分析
# ==================================================================
with tab4:

    _gran = st.radio(
        "HTS 编码粒度",
        ["6 位合计（850760）", "10 位细分（车用动力电池 / 其他锂电 / 储能电池系统）"],
        horizontal=True,
        help="6 位：以 850760 全口径看总量与来源地份额；10 位：区分车用动力电池（8507600010）与其他锂电，数据自 2015-07 起，2026-02 起其他锂电进一步拆分为储能电池系统（8507600030）与其他（8507600090）",
    )
    w = st.radio("事件窗口（政策前后各 N 个月）", [6, 12, 18, 24], horizontal=True, index=1)
    if _gran.startswith("6"):
        sec("政策冲击：2024 年 9 月 301 关税调整",
            "美国贸易代表署（USTR）四年复审，对华锂电分品类上调 301 关税。车用动力电池（HTS 8507.60.0010）由 7.5% 升至 25%，2024-09-27 生效；其余锂电（HTS 8507.60.0020）2026 年 1 月起执行。")


        ev = D.event_study(mat, share, window=w)
        ev_top = ev.head(8)

        # 动态主角名单：中国（基准）+ 份额升幅前 4 + 降幅前 4，与下方份额变化图同口径
        _ds_all = ev.set_index("来源地")["份额变化(pp)"].sort_values()
        _ds_ex = _ds_all.drop(index=["中国"], errors="ignore")
        _gainers = list(_ds_ex.tail(4).index)[::-1]      # 升幅最大者在前
        _losers = list(_ds_ex.head(4).index)             # 降幅最大者在前
        focus = ["中国"] + [c for c in _gainers if c in share.columns] \
                + [c for c in _losers if c in share.columns and c not in _gainers]

        c1, c2 = st.columns(2)
        with c1:
            sec(f"政策前 vs 政策后：月均进口额（±{w} 个月）",
                "单位：百万美元；入选标准：按政策后月均进口额取前 8 的来源地（体量视角）")
            fig = go.Figure()
            fig.add_bar(x=ev_top["来源地"], y=ev_top["政策前月均(百万美元)"], name=f"政策前({D.POLICY_DATE-w}~) ",
                        marker_color="#9DC3D8")
            fig.add_bar(x=ev_top["来源地"], y=ev_top["政策后月均(百万美元)"], name=f"政策后(~{D.POLICY_DATE+w})",
                        marker_color="#D64541")
            fig = style_fig(fig, 380)
            fig.update_yaxes(title="月均进口额（百万美元）", tickformat=",d")
            st.plotly_chart(fig, width="stretch")
            st.caption("注：本图回答“谁的绝对金额最大”，故按政策后月均进口额排序；"
                       "增幅大但体量小的来源地（如波兰、泰国）不会进入本图，请看右侧份额变化图与明细表。")
        with c2:
            sec(f"政策前后份额变化（±{w} 个月，pp）",
                "红=份额上升，绿=份额下降；各取变化最大的 8 个来源地，核心问题：中国丢掉的份额被谁承接")
            d = ev.set_index("来源地")["份额变化(pp)"].sort_values()
            d_show = pd.concat([d.head(8), d.tail(8)]).sort_values()
            fig = go.Figure()
            fig.add_bar(x=d_show.values, y=list(d_show.index), orientation="h",
                        marker_color=["#27AE60" if v < 0 else "#D64541" for v in d_show.values],
                        text=[f"{v:+.2f}" for v in d_show.values], textposition="outside",
                        hovertemplate="%{y} %{x:+.2f} pp<extra></extra>")
            fig = style_fig(fig, max(380, 26 * len(d_show)), legend_h=False)
            fig.update_xaxes(title="份额变化（百分点）", tickformat="+,d")
            st.plotly_chart(fig, width="stretch")
            st.caption("注：按份额变化幅度双向截取——降幅最大 8 个 + 升幅最大 8 个，共 16 个来源地；"
                       "份额为相对指标，某个来源地金额不变也可能因中国下降而份额上升。")

        sec("政策时点前后：重点地区月度份额走势",
            f"虚线为 2024-09 政策生效时点；入选标准：中国 + 份额升幅前 4 + 降幅前 4（与上方份额变化图同口径）")
        fig = go.Figure()
        pol_range = [D.POLICY_DATE - i for i in range(w, 0, -1)] + [D.POLICY_DATE + i for i in range(w)]
        pol_range = [p for p in pol_range if p in share.index]
        for c in focus:
            if c in share.columns:
                fig.add_scatter(x=ts(pol_range), y=share.loc[pol_range, c], name=c,
                                line=dict(color=D.COUNTRY_COLORS.get(c, "#B4B2A9"),
                                          width=2.4 if c == "中国" else 1.6))
        vline_policy(fig)
        fig = style_fig(fig, 400)
        fig.update_yaxes(title="当月份额（%）", tickformat=",d")
        st.plotly_chart(fig, width="stretch")
        _focus_txt = "、".join(
            f"{c}（{_ds_all.get(c, float('nan')):+.2f}pp）" for c in focus)
        st.caption(f"注：本期入选地区为 {_focus_txt}，名额随事件窗口（±{w} 个月）自动重算，"
                   f"换窗口名单会变，引用时请注明窗口。中国线加粗作基准；"
                   f"政策时点为 2024-09-27（图中按月份标注于 2024-09）。")

        sec("事件研究明细表", f"政策前 {w} 个月 vs 政策后 {w} 个月，按政策后月均进口额排序（前 12）")
        show = ev.head(12).copy()
        for col in ["政策前月均(百万美元)", "政策后月均(百万美元)"]:
            show[col] = show[col].map("{:,.1f}".format)
        for col in ["政策前份额(%)", "政策后份额(%)"]:
            show[col] = show[col].map("{:.2f}".format)
        show["月均额变化(%)"] = show["月均额变化(%)"].map("{:+.1f}".format)
        show["份额变化(pp)"] = show["份额变化(pp)"].map("{:+.2f}".format)
        st.dataframe(show, width="stretch", hide_index=True, height=430)
        st.caption("注：本表按政策后月均进口额降序取前 12，用于核对金额与份额两个维度；"
                   "份额升幅最大但与体量无关的来源地请以右侧份额变化图为准。")

    else:
        _policy_hts10(w)

    ai_block("policy", policy_win=w)

# ==================================================================
# TAB 5 州与口岸分布
# ==================================================================
with tab5:
    st.markdown("""
<div class="pick-banner">
  <div class="pb-title">🎯 第一步：请先在下方选择来源地</div>
  <div class="pb-sub">此选择决定下方地图、口岸排名与州趋势展示哪个来源地的数据；默认「全部来源地合计」</div>
</div>""", unsafe_allow_html=True)
    geo_country = st.selectbox("⬇️ 选择来源地（点击展开）",
                               ["全部来源地合计"] + top_countries_in_range(12))
    if geo_country == "全部来源地合计":
        gdf = state_df[state_df["month"].isin(sel_range)]
        gport = port_df[port_df["month"].isin(sel_range)]
        tag = "全部来源地"
    else:
        gdf = state_df[(state_df["country"] == geo_country) & (state_df["month"].isin(sel_range))]
        gport = port_df[(port_df["country"] == geo_country) & (port_df["month"].isin(sel_range))]
        tag = geo_country

    sec(f"{tag}·目的地州分布地图（{m0}~{m1}）",
        "进入本页后自动从 2017 年起逐年播放，终点为侧边栏所选末端月，播完停在终点画面；"
        "颜色越深 = 该州占全美进口份额越高（年度份额之间可直接比较），悬停可看金额")
    _EXCL = ["XX", "PR", "VI"]
    _codes = sorted(state_df.loc[~state_df["state_code"].isin(_EXCL), "state_code"].unique())
    _names = (state_df.drop_duplicates("state_code")
              .set_index("state_code")["state_name"].to_dict())
    _src = state_df if geo_country == "全部来源地合计" else state_df[state_df["country"] == geo_country]

    def _share_frame(sub, label, sublabel):
        agg = (sub.loc[~sub["state_code"].isin(_EXCL)]
               .groupby("state_code")["value"].sum().reindex(_codes).fillna(0.0))
        tot = float(agg.sum()) or 1.0
        sh = agg / tot * 100
        return {"codes": _codes, "label": label, "sub": sublabel,
                "z": [round(float(v), 2) for v in sh.values],
                "cd": [[_names.get(c, c), f"{a / 1e8:,.2f}", f"{s:.1f}"]
                       for c, a, s in zip(_codes, agg.values, sh.values)]}

    # 帧 1..n：2017 起每个完整日历年；末帧：侧边栏所选区间（默认到最新月份）
    _frames = []
    for _y in range(2017, m1.year):
        _seg = _src[(_src["month"] >= pd.Period(f"{_y}-01", freq="M")) &
                    (_src["month"] <= pd.Period(f"{_y}-12", freq="M"))]
        if len(_seg):
            _frames.append(_share_frame(_seg, f"{_y} 年", "全年份额"))
    _frames.append(_share_frame(gdf, f"{m1}", f"所选区间 {m0} – {m1} 的累计份额"))

    _geo_seen = st.session_state.get("_map_geo_seen")
    _play = _geo_seen != geo_country            # 首次进入 / 更换来源地才播放；改日期直接定格
    if _play:
        st.session_state["_map_geo_seen"] = geo_country
    SM.show_iframe_html(SM.state_share_map(_frames, play=_play, height=486), 486)

    stt = gdf.groupby(["state_code", "state_name"])["value"].sum().reset_index()
    stt["pct"] = stt["value"] / stt["value"].sum() * 100
    _excl_pct = stt.loc[stt["state_code"].isin(_EXCL), "pct"].sum()
    _last_share = pd.Series(_frames[-1]["z"], index=_codes).sort_values(ascending=False)
    st.caption(
        f"注：末帧为所选区间（{m0}–{m1}）累计份额，其中 "
        + "、".join(f"{_names.get(c, c)} {v:.1f}%" for c, v in _last_share.head(3).items())
        + f" 居前；色标上限按全部帧的最高份额（{max(max(f['z']) for f in _frames):.1f}%）统一，"
        "因此不同年份的颜色深浅可直接比较。"
        + (f" 海外领地及未识别州合计占 {_excl_pct:.1f}%，未在地图中显示。" if _excl_pct > 0.05 else "")
    )

    sec(f"{tag}·入境口岸 Top 12（{m0}~{m1}）", "按卸货口岸汇总")
    pt = gport.groupby("port_name")["value"].sum().sort_values(ascending=False).head(12)
    fig = go.Figure()
    fig.add_bar(x=pt.values / 1e8, y=list(pt.index)[::-1], orientation="h",
                marker_color=BLUE, text=[f"{v/1e8:,.1f}" for v in pt.values[::-1]],
                textposition="outside",
                hovertemplate="%{y} 进口额 %{x:,.1f} 亿美元<extra></extra>")
    fig = style_fig(fig, 400, legend_h=False)
    fig.update_xaxes(title="进口额（亿美元）", tickformat=",d")
    st.plotly_chart(fig, width="stretch")

    sec(f"{tag}·主要入境口岸份额结构演变",
        "按所选区间合计取 Top 6 口岸，展示各口岸当月份额（%）；份额口径不受总量膨胀影响，可跨年份直接比较")
    top6p = gport.groupby("port_name")["value"].sum().nlargest(6).index.tolist()
    pv = (gport[gport["port_name"].isin(top6p)]
          .groupby(["month", "port_name"])["value"].sum().unstack(fill_value=0)
          .reindex(columns=top6p, fill_value=0))
    # 份额分母取当月全部口岸合计（含未进 Top6 的口岸），保证份额可比
    pv = pv.sort_index()
    pv_share = pv.div(gport.groupby("month")["value"].sum().reindex(pv.index), axis=0) * 100
    pv_share = pv_share.fillna(0)
    fig = go.Figure()
    _pal = [BLUE, "#E67E22", "#27AE60", "#D64541", "#8E7CC3", "#C9A227"]
    for i, p in enumerate(top6p):
        fig.add_scatter(x=ts(pv_share.index), y=pv_share[p], name=p, mode="lines",
                        stackgroup="one", line=dict(width=0.6, color=_pal[i % len(_pal)]),
                        fillcolor=_pal[i % len(_pal)],
                        hovertemplate="%{x|%Y-%m} " + p + " 份额 %{y:.1f}%<extra></extra>")
    # 其余口岸合计（灰色带），保证堆叠到 100%，避免早期年份出现"半空"读图歧义
    _n_other = gport["port_name"].nunique() - len(top6p)
    fig.add_scatter(x=ts(pv_share.index), y=100 - pv_share.sum(axis=1), name="其余口岸合计", mode="lines",
                    stackgroup="one", line=dict(width=0.6, color="#D6D4CC"), fillcolor="#D6D4CC",
                    hovertemplate="%{x|%Y-%m} 其余 " + str(_n_other) + " 个口岸合计 %{y:.1f}%<extra></extra>")
    vline_policy(fig)
    fig = style_fig(fig, 380)
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title="当月份额（%）", range=[0, 100], ticksuffix="%")
    fig.update_xaxes(title="")
    st.plotly_chart(fig, width="stretch")
    _sum6 = pv_share.sum(axis=1)
    st.caption(f"注：纵轴为各口岸占当月全部入境口岸进口额的比重，6 个口岸合计 {_sum6.min():.0f}%–{_sum6.max():.0f}%，"
               f"灰色带为其余 {_n_other} 个口岸合计份额。Top 6 按所选区间（{m0}–{m1}）合计金额排序，"
               f"换区间会重新排序；早期年份口岸分散、灰色带较宽，说明当时尚无主导口岸。")

    ai_block("states")

# ==================================================================
# TAB 6 数据说明
# ==================================================================
with tab6:
    sec("数据来源与口径", None if True else "")
    st.markdown("""
| 项目 | 说明 |
|---|---|
| 产品范围 | HS **850760** 锂离子蓄电池。自 HS 2012 版修订（2012 年）起设为独立六位子目，口径连续可比；本平台覆盖 **2012-01 至今**的全区间月度数据 |
| 数据来源 | **USA Trade Online**（美国普查局官方数据库），按 HS 六位编码 850760 检索，口径为一般进口海关价值；平台自动更新通过 Census 国际贸易 API（`imports/statehs`、`imports/porths`，与 USA Trade Online 同源）实现 |
| 品类细分（10 位） | **HTS 10 位**自 2015-07 起统计：8507600010 车用动力电池；8507600020 其他锂电（至 2026-01）。2026-02 起其他锂电拆分为 **8507600030 储能电池系统**（统计注释 2：≥1 千瓦时、含电池管理与配套部件、整体封装）与 **8507600090 其他**（消费电子、电动工具等）。10 位数据取自 Census API 同一端点，两类合计与 6 位总额逐月一致；无 10 位细分的月份（2012-01 至 2015-06）仅在 6 位视图展示 |
| 数据更新 | **自动增量更新**：打开平台时探测 API 最新月份，发现新数据自动拉取；也可在侧边栏手动点击「检查并更新数据」 |
| 本地缓存 | API 数据写入 Parquet 缓存（增量式，支持官方数据修订重拉）；缓存缺失时自动回退到 `data/raw/` 的 Excel |
| 原产地口径 | **原产地**（Country of Origin，Census 官方字段），非起运国 |
| 大洲归类 | 「按大洲」视图依据 **Census 原产地代码首位**归类：1/2 开头 = 北美洲（含中美洲与加勒比）、3 = 南美洲、4 = 欧洲（俄罗斯、土耳其按 Census 分区计入）、5 = 亚洲（含中国台湾/香港/澳门）、6 = 大洋洲、7 = 非洲；先把同一大洲的原产地金额加总，再重算份额。代码来自官方导出（State/Port 明细的「国家代码」列与 API 的 CTY_CODE），不依赖国家名称 |
| 时间范围 | 2012-01 起（月度，共 176 个月），随 API 发布自动延伸 |
| 州与口岸 | 州 = 申报目的地州（STATE 缩写自动映射全名）；口岸 = 卸货口岸，不必然等于报关口岸 |
| 交叉验证 | 建议与 UN COMTRADE（CIF 口径）对照，注意两者系统性计价差异 |
""", unsafe_allow_html=True)

    _ci = D.cache_info()
    st.caption(
        f"**数据版本自检**：当前载入 {MONTHS[0]} – {LAST_M}（{len(MONTHS)} 个月）"
        f" · 数据文件 `{_ci['source']}`"
        f" · 缓存构建于 {_ci['built_at'] or '—'}。"
        " 若此处显示的起始年份与数据文件不符，说明平台仍在读取旧缓存，请在侧边栏点击「检查并更新数据」，"
        "或在 Streamlit Cloud 的 Manage app → Reboot app 重启应用。"
    )

    sec("指标定义")
    st.markdown("""
| 指标 | 定义 |
|---|---|
| 份额 s(j,t) | 第 j 国当月进口额 ÷ 当月进口总额 × 100% |
| 同比增速 | (X_t − X_{t−12}) / X_{t−12} × 100% |
| CR5 / CR10 | 前 5 / 前 10 大来源地份额之和 |
| HHI | Σ s²（份额以小数计），取值 0-1，越高越集中 |
| 熵指数 | −Σ s·ln(s)，并按 ln(N) 归一化便于跨期比较 |
| 多元化指数 | 1 − HHI |
| 事件窗口 | 以 2024-09（301 关税调整生效）为时点，前后各 N 个月对比 |
""", unsafe_allow_html=True)

    sec("使用提示")
    st.markdown("""
- 侧边栏可切换 **当月值 / 12 个月滚动累计** 口径与时间范围；滚动口径适合看趋势，当月口径适合看拐点与政策冲击。
- 政策冲击为描述性前后对比（事件研究图表），未控制同期宏观因素（如美国本土产能爬坡、需求周期），因果推断需谨慎。
""", unsafe_allow_html=True)

    st.markdown("---")
    st.caption("平台用于研究监测，数据以 USA Trade Online / 美国普查局官方发布为准 · 生成时间：2026-10")
