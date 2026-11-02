# -*- coding: utf-8 -*-
"""
美国锂离子电池（HS 850760）进口监测平台
中国份额与竞争力动态监测 · 基于 USA Trade Online（美国普查局）月度贸易数据，HS 六位编码 850760
运行：streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import census_api as CA

pd.options.plotting.backend = "plotly"

# ================================================================ 页面配置
st.set_page_config(
    page_title="美国锂电池进口监测平台",
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
    /* 顶部标题条 */
    .hero { border-radius: 14px; padding: 22px 28px; margin-bottom: 18px;
            background: linear-gradient(120deg, #12355B 0%, #1D5A8A 60%, #2E86AB 100%); }
    .hero h1 { color: #ffffff; font-size: 26px; font-weight: 700; margin: 0; letter-spacing: 1px; }
    .hero p  { color: rgba(255,255,255,.82); font-size: 13.5px; margin: 6px 0 0; }
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
    .sidebar-note { font-size: 12px; color: #8A8A86; line-height: 1.7; }
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
</style>""", unsafe_allow_html=True)

# ================================================================ 数据加载
state_df = D.load_state()
port_df = D.load_port()

mat = D.monthly_by_country(state_df)          # 月度 × 国家 金额
tot, share = D.with_shares(mat)               # 总额 & 份额
conc = D.concentration(share, 5)              # CR5 / HHI / 熵
conc10 = D.concentration(share, 10)

st.markdown(f"""
<div class="hero">
  <h1>🔋 美国锂离子电池进口监测平台</h1>
  <p>HS 850760 · 锂离子蓄电池 &nbsp;|&nbsp; 原产国口径 · 一般进口海关价值 &nbsp;|&nbsp;
     数据源：USA Trade Online（美国普查局）HS 850760 · 月度更新至 {mat.index[-1]} &nbsp;|&nbsp; 重点监测：中国份额与竞争力变迁</p>
</div>""", unsafe_allow_html=True)

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

    st.markdown("---")
    st.markdown(
        '<p class="sidebar-note">'
        '<b>数据口径</b><br>'
        '· 金额：一般进口海关价值（美元），接近 FOB 价<br>'
        '· 原产地：Country of Origin，非起运国<br>'
        '· 州 = 申报目的地州；口岸 = 卸货口岸<br><br>'
        f'<b>数据范围</b>：{MONTHS[0]} ~ {LAST_M}，{len(mat.columns)} 个原产国</p>',
        unsafe_allow_html=True)


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
    fig.add_annotation(xref="x", yref="paper", x=POLICY_TS, y=1.0, yanchor="top",
                       text=label, showarrow=False,
                       font=dict(size=11, color="#D64541"),
                       align="left", xshift=4)


def sec(title, sub=""):
    st.markdown(f'<p class="sec-title">{title}</p>'
                + (f'<p class="sec-sub">{sub}</p>' if sub else ""), unsafe_allow_html=True)


def top_countries_in_range(n=None, exclude=None):
    n = n or topn
    totals = mat.loc[sel_range].sum().sort_values(ascending=False)
    if exclude:
        totals = totals.drop([c for c in exclude if c in totals.index])
    return list(totals.head(n).index)


# ================================================================ TAB 结构
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["📈 总览仪表盘", "🌍 来源地结构", "📊 中国看板", "🎯 集中度与多元化",
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

# ==================================================================
# TAB 2 来源地结构
# ==================================================================
with tab2:
    sec("来源地份额演变（堆叠面积）",
        f"展示 Top {topn} 来源地及其余地区合计份额；口径：{'12个月滚动' if mode=='12个月滚动累计' else '当月'}")
    top_cs = top_countries_in_range()
    mat_sel = agg_mat(mat)
    stack = mat_sel[top_cs].copy()
    others = mat_sel[[c for c in mat_sel.columns if c not in top_cs]].sum(axis=1)
    stack["其他"] = others
    share_stack = stack.div(stack.sum(axis=1), axis=0) * 100

    fig = go.Figure()
    for c in list(stack.columns):
        fig.add_scatter(x=ts(stack.index), y=share_stack[c], name=c, stackgroup="s",
                        line=dict(width=0.6, color=D.COUNTRY_COLORS.get(c, "#B4B2A9")),
                        fillcolor=D.COUNTRY_COLORS.get(c, "#B4B2A9"),
                        hovertemplate="%{x|%Y-%m} " + c + " 份额 %{y:.1f}%<extra></extra>")
    vline_policy(fig)
    fig = style_fig(fig, 440)
    fig.update_yaxes(title="份额（%）", range=[0, 100], tickformat=",d")
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns([2, 3])
    with c1:
        sec(f"所选周期平均份额排名", f"{m0} ~ {m1} 平均月度份额")
        avg_share = share.loc[sel_range].mean().sort_values(ascending=False).head(10)
        fig = go.Figure()
        fig.add_bar(x=avg_share.values[::-1], y=list(avg_share.index)[::-1], orientation="h",
                    marker_color=[D.COUNTRY_COLORS.get(c, "#B4B2A9") for c in avg_share.index][::-1],
                    text=[f"{v:.1f}%" for v in avg_share.values[::-1]], textposition="outside",
                    hovertemplate="%{y} 平均份额 %{x:.1f}%<extra></extra>")
        fig = style_fig(fig, 400, legend_h=False)
        fig.update_xaxes(title="平均份额（%）", range=[0, avg_share.max() * 1.2], tickformat=",d")
        fig.update_yaxes(tickfont=dict(size=12.5))
        st.plotly_chart(fig, width="stretch")
    with c2:
        sec("主要来源地排名变化",
            "每个月份按份额排名，连线展示排名的时间演变（越小越靠前）")
        bump_countries = top_countries_in_range(8)
        ranks = share[bump_countries].loc[sel_range].rank(axis=1, ascending=False)
        fig = go.Figure()
        for c in bump_countries:
            is_cn = (c == "中国")
            fig.add_scatter(x=ts(ranks.index), y=ranks[c], name=c, mode="lines+markers",
                            line=dict(color=D.COUNTRY_COLORS.get(c, "#B4B2A9"), width=3 if is_cn else 2.2),
                            marker=dict(size=7 if is_cn else 6), cliponaxis=False,
                            hovertemplate="%{x|%Y-%m} " + c + " 排名第 %{y:.0f}<extra></extra>")
        fig = style_fig(fig, 400)
        # 显式范围 + 上下留白，防止第 1 名的线被绘图区顶边裁剪
        fig.update_yaxes(title="份额排名", range=[len(bump_countries) + 0.6, 0.4],
                         tickvals=list(range(1, len(bump_countries) + 1)), tickformat=",d")
        st.plotly_chart(fig, width="stretch")

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

# ==================================================================
# TAB 4 集中度与多元化
# ==================================================================
with tab4:
    sec("市场集中度：CR5 与 CR10", "CR5=前五大来源地份额合计；CR10=前十大来源地份额合计，CR10−CR5 的差距越大，说明第 6~10 名来源地的重要性越高")
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

# ==================================================================
# TAB 5 政策冲击分析
# ==================================================================
with tab5:
    sec("政策冲击：2024 年 9 月 301 关税调整",
        "美国贸易代表署（USTR）四年复审，对华锂电分品类上调 301 关税。车用动力电池（HTS 8507.60.0010）由 7.5% 升至 25%，2024-09-27 生效；其余锂电（HTS 8507.60.0020）2026 年 1 月起执行。")

    w = st.radio("事件窗口（政策前后各 N 个月）", [6, 12, 18, 24], horizontal=True, index=1)

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

# ==================================================================
# TAB 6 州与口岸分布
# ==================================================================
with tab6:
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
        "颜色越深 = 进口额越高，展示美国锂电池的申报目的地州分布；波多黎各等海外领地与未识别州（XX）不在图中")
    stt = gdf.groupby(["state_code", "state_name"])["value"].sum().reset_index()
    stt["value_yi"] = stt["value"] / 1e8
    stt["pct"] = stt["value"] / stt["value"].sum() * 100
    map_df = stt[~stt["state_code"].isin(["XX", "PR", "VI"])]
    _excl_pct = stt.loc[stt["state_code"].isin(["XX", "PR", "VI"]), "pct"].sum()
    if _excl_pct > 0.05:
        st.caption(f"注：海外领地及未识别州合计占 {_excl_pct:.1f}%，未在地图中显示。")
    fig = px.choropleth(map_df, locations="state_code", locationmode="USA-states",
                        color="value", color_continuous_scale="Blues",
                        scope="usa", custom_data=["state_name", "value", "pct"])
    # 与参考图一致：灰色州界线清晰可见
    fig.update_traces(marker_line_color="#8A8A86", marker_line_width=0.7,
                      hovertemplate="<b>%{customdata[0]}</b><br>进口额：%{customdata[1]:,.0f} 美元<br>占比：%{customdata[2]:.1f}%<extra></extra>")
    _vmax = max(map_df["value"].max(), 1)
    _tickvals = list(np.linspace(0, _vmax, 5))
    _ticktext = [f"{v/1e8:,.0f}亿" for v in _tickvals]
    fig.update_layout(height=480, margin=dict(l=10, r=10, t=10, b=10),
                      font=dict(family="Noto Sans SC, sans-serif", size=12.5, color="#3A3A38"),
                      paper_bgcolor="white",
                      geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="#FFFFFF", showlakes=True,
                               showsubunits=True, subunitcolor="#8A8A86", subunitwidth=0.5,
                               showcoastlines=False, showland=False),
                      coloraxis_colorbar=dict(title="进口金额（美元）", thickness=14,
                                              len=0.85, tickvals=_tickvals, ticktext=_ticktext))
    st.plotly_chart(fig, width="stretch")

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

# ==================================================================
# TAB 7 数据说明
# ==================================================================
with tab7:
    sec("数据来源与口径", None if True else "")
    st.markdown("""
| 项目 | 说明 |
|---|---|
| 产品范围 | HS **850760** 锂离子蓄电池。自 HS 2012 版修订（2012 年）起设为独立六位子目，口径连续可比；本平台覆盖 **2012-01 至今**的全区间月度数据 |
| 数据来源 | **USA Trade Online**（美国普查局官方数据库），按 HS 六位编码 850760 检索，口径为一般进口海关价值；平台自动更新通过 Census 国际贸易 API（`imports/statehs`、`imports/porths`，与 USA Trade Online 同源）实现 |
| 数据更新 | **自动增量更新**：打开平台时探测 API 最新月份，发现新数据自动拉取；也可在侧边栏手动点击「检查并更新数据」 |
| API Key | 在 api.census.gov/data/key_signup.html 免费申请，填入侧边栏后保存在服务端本地（不随页面暴露） |
| 本地缓存 | API 数据写入 Parquet 缓存（增量式，支持官方数据修订重拉）；缓存缺失时自动回退到 `data/raw/` 的 Excel |
| 金额口径 | 一般进口海关价值（Customs Value），接近 FOB 价，不含国际运费、保险费与美国进口关税 |
| 原产地口径 | **原产地**（Country of Origin，Census 官方字段），非起运国 |
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
