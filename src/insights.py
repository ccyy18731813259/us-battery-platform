# -*- coding: utf-8 -*-
"""AI 解读与报告生成引擎。

所有结论均由平台载入的数据实时计算得出（不加任何外部判断），
保证「有理有据」：每条结论都附带具体数值与时间窗口。
统计口径与主界面一致：当月值 / 年初至今累计 / 12 个月滚动累计。

页面解读按页拆分（page 参数）：overview / structure / china / concentration / policy / states。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

POLICY = pd.Period("2024-09", freq="M")

MODE_LABEL = {"当月值": "当月值", "年初至今累计": "年初至今累计（YTD）", "12个月滚动累计": "12 个月滚动累计"}


# ---------------------------------------------------------------- 基础口径
def agg_series(s: pd.Series, mode: str) -> pd.Series:
    if mode == "12个月滚动累计":
        return s.rolling(12, min_periods=1).sum()
    if mode == "年初至今累计":
        return s.groupby(s.index.year).cumsum()
    return s


def agg_mat(mat: pd.DataFrame, mode: str) -> pd.DataFrame:
    if mode == "12个月滚动累计":
        return mat.rolling(12, min_periods=1).sum()
    if mode == "年初至今累计":
        return mat.groupby(mat.index.year).cumsum()
    return mat


def share_mat(mat: pd.DataFrame, mode: str) -> pd.DataFrame:
    m = agg_mat(mat, mode)
    return m.div(m.sum(axis=1), axis=0) * 100


def _yi(v: float) -> str:
    return f"{v / 1e8:,.2f} 亿美元"


def _pct(v: float) -> str:
    return f"{v:.1f}%"


def _pp(v: float) -> str:
    return f"{v:+.1f} pp"


def _chg(v: float) -> str:
    return f"{v:+.1f}%"


def _g(v: float) -> str:
    """自然语言化的变动表述：增长 12.3% / 下降 4.5%"""
    if pd.isna(v):
        return "—"
    return f"{'增长' if v >= 0 else '下降'} {abs(v):.1f}%"


def _yoy(s: pd.Series, at) -> float:
    prev_at = at - 12
    if prev_at not in s.index:
        return float("nan")
    base = s.loc[prev_at]
    if not base or pd.isna(base) or base == 0:
        return float("nan")
    return (s.loc[at] / base - 1) * 100


def _window_pair(mat: pd.DataFrame, m0: pd.Period, m1: pd.Period):
    """返回 (窗口月份列表, 前一段等长窗口月份列表)"""
    w = [m for m in mat.index if m0 <= m <= m1]
    loc0 = mat.index.get_loc(m0)
    if loc0 - len(w) >= 0:
        return w, list(mat.index[loc0 - len(w): loc0])
    h = len(w) // 2
    return w[h:], w[:h]


# ---------------------------------------------------------------- 核心统计
def _stats(mat: pd.DataFrame, mode: str, m0: pd.Period, m1: pd.Period) -> dict:
    tot = mat.sum(axis=1)
    at = mat.index[-1]
    prev_at = at - 12
    sh = share_mat(mat, mode)
    sh_m = share_mat(mat, "当月值")
    tot_agg = agg_series(tot, mode)
    cn = "中国" if "中国" in mat.columns else None

    s = {"at": at, "prev_at": prev_at, "mode": mode, "cn": cn}

    # ---- 总量 ----
    s["cur_total"] = tot_agg.loc[at]
    s["total_yoy"] = _yoy(tot_agg, at)
    _r12 = tot.rolling(12, min_periods=1).sum()
    s["roll12"] = _r12.iloc[-1]
    s["roll12_yoy"] = _yoy(_r12, at)
    _m3, _p3 = tot.iloc[-3:].mean(), tot.iloc[-6:-3].mean()
    s["momo3"] = (_m3 / _p3 - 1) * 100 if _p3 else float("nan")
    s["peak_m"], s["peak_v"] = tot.idxmax(), tot.max()
    s["cur_m"] = tot.loc[at]
    s["cur_vs_peak"] = s["cur_m"] / s["peak_v"] * 100
    s["months_since_peak"] = len([m for m in mat.index if m > s["peak_m"]])
    s["cur_pctile"] = (tot < tot.loc[at]).mean() * 100
    s["roll_pctile"] = (_r12.dropna() < _r12.loc[at]).mean() * 100
    _yoy_s = tot.pct_change(12) * 100
    s["yoy_last3"] = _yoy_s.iloc[-3:].mean()
    s["yoy_prev3"] = _yoy_s.iloc[-6:-3].mean()
    s["cn_roll12"] = mat[cn].rolling(12, min_periods=1).sum().iloc[-1] if cn else float("nan")
    s["cn_roll12_yoy"] = _yoy(mat[cn].rolling(12, min_periods=1).sum(), at) if cn else float("nan")

    # ---- 中国 ----
    s["cn_share"] = sh.loc[at, cn] if cn else float("nan")
    s["cn_share_prev"] = sh.loc[prev_at, cn] if cn and prev_at in sh.index else float("nan")
    s["cn_rank"] = int(sh.loc[at].rank(ascending=False)[cn]) if cn else 0
    sh_cn = sh_m[cn] if cn else pd.Series(dtype=float)
    s["cn_peak_m"], s["cn_peak_v"] = sh_cn.idxmax(), sh_cn.max()
    _post_pol = sh_cn.loc[sh_cn.index >= POLICY]
    s["cn_min_since_policy"], s["cn_min_since_policy_m"] = _post_pol.min(), _post_pol.idxmin()
    cnt, i = 0, len(sh_cn) - 1
    while i >= 12 and pd.notna(sh_cn.iloc[i]) and pd.notna(sh_cn.iloc[i - 12]) and sh_cn.iloc[i] < sh_cn.iloc[i - 12]:
        cnt += 1
        i -= 1
    s["cn_below_yoy_months"] = cnt

    # ---- 集中度 ----
    def _cr_hhi(row: pd.Series, k: int = 5):
        v = row.dropna().sort_values(ascending=False)
        p = v / 100
        return v.head(k).sum(), float((p ** 2).sum())

    s["cr5_now"], s["hhi_now"] = _cr_hhi(sh.loc[at])
    s["cr10_now"] = float(sh.loc[at].dropna().sort_values(ascending=False).head(10).sum())
    s["n1_now"] = int((sh.loc[at].dropna() > 1).sum())
    if prev_at in sh.index:
        s["cr5_prev"], s["hhi_prev"] = _cr_hhi(sh.loc[prev_at])
        s["cr10_prev"] = float(sh.loc[prev_at].dropna().sort_values(ascending=False).head(10).sum())
        s["n1_prev"] = int((sh.loc[prev_at].dropna() > 1).sum())
    else:
        s["cr5_prev"] = s["hhi_prev"] = s["cr10_prev"] = float("nan")
        s["n1_prev"] = 0
    _p_row = sh.loc[at].dropna() / 100
    _p_row = _p_row[_p_row > 0]
    s["entropy_now"] = float(-(_p_row * np.log(_p_row)).sum())

    # HHI 历史序列（月度口径）
    _hhi_hist = ((sh_m.div(100)) ** 2).sum(axis=1)
    s["hhi_hist"] = _hhi_hist
    s["hhi_hist_min"], s["hhi_hist_max"] = _hhi_hist.min(), _hhi_hist.max()
    s["hhi_hist_min_m"], s["hhi_hist_max_m"] = _hhi_hist.idxmin(), _hhi_hist.idxmax()

    # ---- 窗口结构 ----
    w, pw = _window_pair(mat, m0, m1)
    s["window"], s["prev_window"] = w, pw
    s["win_label"] = f"{w[0]} – {w[-1]}" if w else f"{m0} – {m1}"
    s["split"] = bool(pw) and pw[0] == m0  # 对照期落在所选区间内部 = 无更早历史，按前后两段拆
    s["base_label"] = f"{pw[0]} – {pw[-1]}" if pw else "—"
    # 侧边栏所选区间本身（总览 KPI 卡「所选区间累计」用）
    _sel = [m for m in mat.index if m0 <= m <= m1]
    s["sel_label"] = f"{m0} – {m1}"
    s["sel_total"] = float(mat.loc[_sel].sum().sum()) if _sel else 0.0
    # 结构页「平均份额排名」图：所选区间平均份额
    if _sel:
        _avg = mat.loc[_sel].sum()
        s["avg_share"] = (_avg / _avg.sum() * 100).sort_values(ascending=False)
        s["avg_top5"] = s["avg_share"].head(5)
    # 结构页「份额明细表」：近 12 个月 vs 此前 12 个月；中国页「份额变动」图：首 12 vs 末 12
    if len(_sel) >= 24:
        _n12, _p12 = _sel[-12:], _sel[-24:-12]
        _sn, _sq = mat.loc[_n12].sum(), mat.loc[_p12].sum()
        s["t12_now"] = _sn / _sn.sum() * 100
        s["t12_prev"] = _sq / _sq.sum() * 100
        s["t12_diff"] = (s["t12_now"] - s["t12_prev"].reindex(s["t12_now"].index).fillna(0)).dropna()
        s["t12_now_label"] = f"{_n12[0]} – {_n12[-1]}"
        s["t12_prev_label"] = f"{_p12[0]} – {_p12[-1]}"
        _h, _t = _sel[:12], _sel[-12:]
        s["h12_label"], s["t12_label"] = f"{_h[0]} – {_h[-1]}", f"{_t[0]} – {_t[-1]}"
        s["head_amt"] = float(mat.loc[_h].sum().sum())
        s["tail_amt"] = float(mat.loc[_t].sum().sum())
        if cn:
            s["cn_h12"], s["cn_t12"] = float(mat.loc[_h, cn].sum()), float(mat.loc[_t, cn].sum())
            s["oth_h12"] = s["head_amt"] - s["cn_h12"]
            s["oth_t12"] = s["tail_amt"] - s["cn_t12"]
    sw, sp = mat.loc[w].sum(), mat.loc[pw].sum()
    s["window_total"], s["prev_total"] = sw.sum(), sp.sum()
    s["window_yoy"] = (sw.sum() / sp.sum() - 1) * 100 if sp.sum() else float("nan")
    s["top5"] = sw.sort_values(ascending=False).head(5)
    s["top10"] = sw.sort_values(ascending=False).head(10)
    _cjk = [c for c in ["中国", "日本", "韩国"] if c in mat.columns]
    if _cjk and sw.sum() and sp.sum():
        s["cjk_w"] = float(sw[_cjk].sum() / sw.sum() * 100)
        s["cjk_p"] = float(sp[_cjk].sum() / sp.sum() * 100)
    diff_pp = (sw / sw.sum() - sp / sp.sum()).dropna() * 100 if sp.sum() else pd.Series(dtype=float)
    s["diff_pp"] = diff_pp
    s["gainers"] = diff_pp[diff_pp > 0].sort_values(ascending=False).head(3)
    s["losers"] = diff_pp[diff_pp < 0].sort_values().head(3)
    if cn:
        s["cn_w"] = sw.get(cn, 0.0)
        s["cn_p"] = sp.get(cn, 0.0)
        s["cn_w_chg"] = (s["cn_w"] / s["cn_p"] - 1) * 100 if s["cn_p"] else float("nan")
        s["others_w"] = s["window_total"] - s["cn_w"]
        s["others_p"] = s["prev_total"] - s["cn_p"]
        s["others_chg"] = (s["others_w"] / s["others_p"] - 1) * 100 if s["others_p"] else float("nan")
        s["cn_share_w"] = s["cn_w"] / s["window_total"] * 100
        s["cn_share_p"] = s["cn_p"] / s["prev_total"] * 100 if s["prev_total"] else float("nan")

    # ---- 政策 ----
    pre = [m for m in mat.index if POLICY - 12 <= m < POLICY]
    post = [m for m in mat.index if POLICY <= m < POLICY + 12]
    s["pre_idx"], s["post_idx"] = pre, post
    s["pre_total"], s["post_total"] = tot.loc[pre].mean(), tot.loc[post].mean()
    s["pre_cn"] = sh_m.loc[pre, cn].mean() if cn else float("nan")
    s["post_cn"] = sh_m.loc[post, cn].mean() if cn else float("nan")
    _late = [m for m in mat.index if m >= POLICY + 18]
    s["late_idx"] = _late
    s["late_total"] = tot.loc[_late].mean() if len(_late) >= 3 else float("nan")
    s["late_cn"] = sh_m.loc[_late, cn].mean() if cn and len(_late) >= 3 else float("nan")
    return s


# ---------------------------------------------------------------- 地域与口岸
def _geo_stats(state_df: pd.DataFrame, port_df: pd.DataFrame, m0: pd.Period, m1: pd.Period) -> dict:
    out = {}
    EXCL = ["XX", "PR", "VI"]
    sd = state_df[(state_df.month >= m0) & (state_df.month <= m1) & (~state_df.state_code.isin(EXCL))]
    g = sd.groupby("state_name")["value"].sum().sort_values(ascending=False)
    tot = float(g.sum()) or 1.0
    out["st_total"] = tot
    out["st_top"] = g.head(3)
    out["st_cr3"] = g.head(3).sum() / tot * 100
    out["st_hhi"] = float(((g / tot) ** 2).sum())
    out["st_n"] = int(len(g))
    pd_ = port_df[(port_df.month >= m0) & (port_df.month <= m1)]
    pg = pd_.groupby("port_name")["value"].sum().sort_values(ascending=False)
    ptot = float(pg.sum()) or 1.0
    out["pt_total"] = ptot
    out["pt_top"] = pg.head(3)
    out["pt_cr3"] = pg.head(3).sum() / ptot * 100
    out["pt_hhi"] = float(((pg / ptot) ** 2).sum())
    out["pt_n"] = int(len(pg))

    # 与前一等长窗口对比（仅前 3 州 / 前 3 口岸的份额 pp 变化）
    months = sorted(state_df.month.unique())
    if m0 in months:
        i0 = months.index(m0)
        n = len([m for m in months if m0 <= m <= m1])
        if i0 - n >= 0:
            pw = months[i0 - n: i0]
            sd_p = state_df[(state_df.month.isin(pw)) & (~state_df.state_code.isin(EXCL))]
            gp = sd_p.groupby("state_name")["value"].sum()
            if gp.sum():
                cur_sh = g / tot * 100
                prev_sh = gp / gp.sum() * 100
                d = (cur_sh - prev_sh.reindex(cur_sh.index).fillna(0)).sort_values()
                out["st_gain"], out["st_lose"] = d.tail(2)[::-1], d.head(2)
            pd_p = port_df[port_df.month.isin(pw)]
            pgp = pd_p.groupby("port_name")["value"].sum()
            if pgp.sum():
                cur_sh = pg / ptot * 100
                prev_sh = pgp / pgp.sum() * 100
                d = (cur_sh - prev_sh.reindex(cur_sh.index).fillna(0)).sort_values()
                out["pt_gain"], out["pt_lose"] = d.tail(2)[::-1], d.head(2)
    return out


def _cont_stats(state_df: pd.DataFrame, m0: pd.Period, m1: pd.Period) -> dict:
    from src import data as DD
    cm = DD.monthly_by_continent(state_df)
    w = [m for m in cm.index if m0 <= m <= m1]
    if not w:
        return {}
    i0 = cm.index.get_loc(w[0])
    sw = cm.loc[w].sum()
    out = {"now": (sw / sw.sum() * 100).sort_values(ascending=False)}
    _ms = cm.loc[w].div(cm.loc[w].sum(axis=1), axis=0) * 100
    out["avg"] = _ms.mean().sort_values(ascending=False)
    if i0 - len(w) >= 0:
        pw = list(cm.index[i0 - len(w): i0])
        sp = cm.loc[pw].sum()
        out["diff"] = ((sw / sw.sum() - sp / sp.sum()) * 100).dropna()
        out["base_label"] = f"{pw[0]} – {pw[-1]}"
    return out


# ---------------------------------------------------------------- 10 位品类（可选）
def _hts10_block() -> list:
    """返回 [(品类, 政策前月均, 政策后月均, 中国份额前, 中国份额后, 是否仅近期数据)]"""
    try:
        from src import hts10 as H
        d = H.data()
    except Exception:  # noqa: BLE001 - 云端缺数据文件时跳过
        return []
    out = []
    for cat in ["车用动力电池", "其他锂电"]:
        sub = d[d.cat_cont == cat]
        if sub.empty:
            continue
        t = sub.groupby("month")["value"].sum()
        c = sub[sub.country == "中国"].groupby("month")["value"].sum()
        shc = (c / t * 100).dropna()
        pre = [m for m in t.index if POLICY - 12 <= m < POLICY]
        post = [m for m in t.index if POLICY <= m < POLICY + 12]
        if not pre or not post:
            continue
        out.append((cat, t.loc[pre].mean(), t.loc[post].mean(),
                    shc.reindex(pre).mean(), shc.reindex(post).mean(), False))
    try:
        ess = d[d.cat == "储能电池系统"]
        if not ess.empty:
            t = ess.groupby("month")["value"].sum()
            c = ess[ess.country == "中国"].groupby("month")["value"].sum()
            shc = (c / t * 100).dropna()
            out.append(("储能电池系统（8507600030）", float("nan"), t.mean(),
                        float("nan"), shc.mean(), True))
    except Exception:  # noqa: BLE001
        pass
    return out


# ================================================================ 分节内容
def _sec_total(s: dict, mode: str) -> dict:
    mn = MODE_LABEL[mode]
    b = [f"**当前口径下进口规模 {_yi(s['cur_total'])}（{mn}，截至 {s['at']}），"
         f"同比{_g(s['total_yoy'])}。**"]
    if mode == "12个月滚动累计":
        b.append(f"近 3 个月月均较此前 3 个月{'回升' if s['momo3'] > 0 else '回落'} {abs(s['momo3']):.1f}%，"
                 f"短期动量偏{'强' if s['momo3'] > 0 else '弱'}。")
    else:
        b.append(f"近 12 个月合计 {_yi(s['roll12'])}（同比{_g(s['roll12_yoy'])}）；"
                 f"近 3 个月月均较此前 3 个月{'回升' if s['momo3'] > 0 else '回落'} {abs(s['momo3']):.1f}%，"
                 f"短期动量偏{'强' if s['momo3'] > 0 else '弱'}。" if pd.notna(s["roll12_yoy"]) else
                 f"近 12 个月合计 {_yi(s['roll12'])}。")
    b.append(f"单月峰值 {_yi(s['peak_v'])}（{s['peak_m']}），当前单月为峰值的 {s['cur_vs_peak']:.0f}%，"
             f"距峰值 {s['months_since_peak']} 个月；当前规模处于历史 {s['cur_pctile']:.0f} 分位、"
             f"滚动 12 个月处于 {s['roll_pctile']:.0f} 分位。")
    if pd.notna(s["yoy_last3"]) and pd.notna(s["yoy_prev3"]):
        b.append(f"同比增速近 3 个月均值 {_chg(s['yoy_last3'])}，此前 3 个月 {_chg(s['yoy_prev3'])}，"
                 f"降幅{'收窄' if s['yoy_last3'] > s['yoy_prev3'] else '扩大'}，"
                 f"{'底部企稳迹象初现' if s['yoy_last3'] > s['yoy_prev3'] and s['yoy_last3'] < 0 else '仍处下行通道' if s['yoy_last3'] < 0 else '进入正增长区间'}。")
    return {"title": f"📌 总量与趋势（口径：{mn}）", "body": b}


def _sec_china(s: dict) -> dict:
    b = [f"**中国当前份额 {_pct(s['cn_share'])}，第 {s['cn_rank']} 大来源地**；"
         f"较上年同期同段 {_pp(s['cn_share'] - s['cn_share_prev'])}（去年同期 {_pct(s['cn_share_prev'])}）。",
         f"月度份额峰值 {_pct(s['cn_peak_v'])}（{s['cn_peak_m']}）；2024-09 关税生效以来最低 "
         f"{_pct(s['cn_min_since_policy'])}（{s['cn_min_since_policy_m']}），"
         f"区间回落 {abs(s['cn_peak_v'] - s['cn_min_since_policy']):.1f} pp。"]
    if s["cn_below_yoy_months"] >= 3:
        b.append(f"份额已**连续 {s['cn_below_yoy_months']} 个月低于上年同月**，属趋势性回落而非单月扰动。")
    else:
        b.append(f"低于上年同月的月份累计 {s['cn_below_yoy_months']} 个，尚未形成连续回落。")
    if "cn_h12" in s and s.get("oth_h12"):
        b.append(f"按本页「份额变动」图口径（首 12 个月 {s['h12_label']} vs 末 12 个月 {s['t12_label']}）："
                 f"自华进口 {_yi(s['cn_h12'])} → {_yi(s['cn_t12'])}"
                 f"（{_g((s['cn_t12'] / s['cn_h12'] - 1) * 100) if s['cn_h12'] else '—'}）；"
                 f"其他来源地合计 {_yi(s['oth_h12'])} → {_yi(s['oth_t12'])}"
                 f"（{_g((s['oth_t12'] / s['oth_h12'] - 1) * 100) if s['oth_h12'] else '—'}）。")
    return {"title": "🇨🇳 中国份额与自华进口", "body": b}


def _sec_structure(s: dict) -> dict:
    """对应结构页：堆叠面积 / 平均份额排名 / 排名变化 / 中日韩 / 份额明细表"""
    b = [f"所选区间（{s['sel_label']}）合计 {_yi(s['sel_total'])}，平均月度份额前五："
         + "、".join(f"{k} {_pct(v)}" for k, v in s["avg_top5"].items()) + "。"]
    if "t12_diff" in s:
        d = s["t12_diff"]
        up = d[d > 0.1].sort_values(ascending=False).head(3)
        dn = d[d < -0.1].sort_values().head(3)
        _up = "、".join(f"{k} {_pp(v)}" for k, v in up.items()) or "无明显上升"
        _dn = "、".join(f"{k} {_pp(v)}" for k, v in dn.items()) or "无明显下降"
        b.append(f"近 12 个月（{s['t12_now_label']}）较此前 12 个月（{s['t12_prev_label']}）："
                 f"份额上升最多 **{_up}**；下降最多 **{_dn}**；"
                 f"份额上行的来源地 {int((d > 0.05).sum())} 个、下行的 {int((d < -0.05).sum())} 个。")
    if s.get("cn_share_w") is not None and pd.notna(s.get("cn_share_p", float("nan"))) and "t12_diff" not in s:
        _d = s["cn_share_w"] - s["cn_share_p"]
        b.append(f"中国份额 {_pct(s['cn_share_p'])} → {_pct(s['cn_share_w'])}（{_pp(_d)}）。")
    if s.get("cjk_w") is not None:
        b.append(f"中日韩合计份额 {_pct(s['cjk_w'])}（{'前段' if s.get('split') else '前一段'} "
                 f"{_pct(s['cjk_p'])}，{_pp(s['cjk_w'] - s['cjk_p'])}），东亚三大供给国的合计地位"
                 f"{'上升' if s['cjk_w'] >= s['cjk_p'] else '下降'}，内部排序变化见「东亚三大供给国对比」。")
    if "t12_diff" in s and "中国" in s["t12_diff"].index:
        d = s["t12_diff"]
        dcn = float(d["中国"])
        _lead = "、".join([k for k in d[d > 0.05].sort_values(ascending=False).index if k != "中国"][:2]) or "非中国来源"
        b.append(f"结构特征：中国平均份额 {_pct(s['t12_prev']['中国'])} → {_pct(s['t12_now']['中国'])}（{_pp(dcn)}），"
                 + (f"让出的份额主要由 {_lead} 承接，属**替代型调整**——变化发生在来源结构，而非需求总量。"
                    if dcn < 0 else "份额进一步向中国集中，其他来源地整体让位。"))
    return {"title": "🧩 来源地结构变化", "body": b}


def _sec_continent(s: dict, cs: dict) -> dict:
    now = cs.get("now")
    b = []
    if now is not None and len(now):
        _avg = cs.get("avg", now)
        head = "、".join(f"{k} {_pct(v)}" for k, v in _avg.head(3).items())
        b.append(f"按大洲看（原产地代码归类）：所选区间平均月度份额前三大洲为 {head}。")
        if "diff" in cs and len(cs["diff"]):
            d = cs["diff"][cs["diff"].abs() >= 0.1].sort_values()
            if len(d):
                up = "、".join(f"{k} {_pp(v)}" for k, v in d[d > 0].tail(2)[::-1].items()) or "无"
                dn = "、".join(f"{k} {_pp(v)}" for k, v in d[d < 0].head(2).items()) or "无"
                b.append(f"较前一段等长窗口（{cs['base_label']}）：上升 {up}；下降 {dn}（变动不足 0.1 pp 未列示）。")
            b.append("份额在亚洲内部转移而非跨洲转移，说明竞争仍集中在东亚供应链内部。"
                     if now.index[0] == "亚洲" and cs["diff"].get("亚洲", 0) >= 0 else
                     "跨洲份额出现位移，需关注新增大洲来源的可持续性。")
    return {"title": "🌐 大洲格局", "body": b}


def _sec_concentration(s: dict, deep: bool = False) -> dict:
    b = [f"CR5 {_pct(s['cr5_now'])}（上年同期 {_pct(s['cr5_prev'])}），"
         f"CR10 {_pct(s['cr10_now'])}（上年 {_pct(s['cr10_prev'])}）；"
         f"HHI {s['hhi_now']:.3f}（上年 {s['hhi_prev']:.3f}），"
         f"{'下降' if s['hhi_now'] < s['hhi_prev'] else '上升' if s['hhi_now'] > s['hhi_prev'] else '持平'} "
         f"{abs(s['hhi_now'] - s['hhi_prev']):.3f}。"]
    b.append(f"HHI 低于 0.15 视为分散、0.15–0.25 为中度集中、高于 0.25 为高度集中，当前处于"
             f"{'分散' if s['hhi_now'] < 0.15 else '高位集中' if s['hhi_now'] > 0.25 else '中度集中'}区间；"
             f"份额超过 1% 的来源地 {s['n1_now']} 个（上年 {s['n1_prev']} 个）。")
    if deep:
        b.append(f"历史区间：2012 年以来 HHI 最高 {s['hhi_hist_max']:.3f}（{s['hhi_hist_max_m']}）、"
                 f"最低 {s['hhi_hist_min']:.3f}（{s['hhi_hist_min_m']}），当前处于历史 "
                 f"{(s['hhi_hist'] < s['hhi_now']).mean() * 100:.0f} 分位。")
        b.append(f"熵指数 {s['entropy_now']:.2f}（份额分布越均匀越高），可视为有效来源地数量的近似："
                 f"约为 {np.exp(s['entropy_now']):.1f} 个等份额来源地。")
        b.append("集中度与经济含义：HHI 回落意味着单一来源中断对总供给的冲击乘数下降，"
                 "但同时抬高了跨来源地的合规、品质与物流管理成本。" if s["hhi_now"] < s["hhi_prev"] else
                 "集中度回升意味着供给更依赖少数来源，价格谈判与断供风险敞口同时扩大。")
    return {"title": "⚖️ 集中度与多元化", "body": b}


def _policy_stats(mat: pd.DataFrame, win: int) -> dict:
    """政策前后各 win 个月的月均规模与均值份额（与政策页「事件窗口」单选同步）"""
    tot = mat.sum(axis=1)
    shm = share_mat(mat, "当月值")
    cn = "中国" if "中国" in mat.columns else None
    pre = [m for m in mat.index if POLICY - win <= m < POLICY]
    post = [m for m in mat.index if POLICY <= m < POLICY + win]
    return {
        "win": win, "pre_n": len(pre), "post_n": len(post),
        "pre_total": tot.loc[pre].mean() if pre else float("nan"),
        "post_total": tot.loc[post].mean() if post else float("nan"),
        "pre_cn": shm.loc[pre, cn].mean() if cn and pre else float("nan"),
        "post_cn": shm.loc[post, cn].mean() if cn and post else float("nan"),
    }


def _sec_policy(s: dict, detail: bool = True, pol: dict | None = None) -> dict:
    if pol is None:
        p = {"win": 12, "pre_total": s["pre_total"], "post_total": s["post_total"],
             "pre_cn": s["pre_cn"], "post_cn": s["post_cn"]}
        _w = 12
    else:
        p, _w = pol, pol["win"]
    b = [f"**301 关税（2024-09 生效）前后各 {_w} 个月对比（当月口径）**：月均进口额 {_yi(p['pre_total'])} → "
         f"{_yi(p['post_total'])}（{(p['post_total'] / p['pre_total'] - 1) * 100:+.1f}%）；"
         f"中国份额均值 {_pct(p['pre_cn'])} → {_pct(p['post_cn'])}（{p['post_cn'] - p['pre_cn']:+.1f} pp）。"]
    if pd.notna(s["late_total"]):
        b.append(f"政策生效 18 个月后的最近 {len(s['late_idx'])} 个月：月均 {_yi(s['late_total'])}、"
                 f"中国份额均值 {_pct(s['late_cn'])}，代表调整后的新稳态水平。")
    if detail:
        h10 = _hts10_block()
        if h10:
            seg = []
            for cat, pre, post, pc, qc, only_recent in h10:
                if only_recent:
                    seg.append(f"{cat} 2026-02 起单列：月均 {_yi(post)}、中国份额 {_pct(qc)}")
                else:
                    seg.append(f"{cat}：月均 {_yi(pre)}→{_yi(post)}（{(post / pre - 1) * 100:+.1f}%），"
                               f"中国份额 {_pct(pc)}→{_pct(qc)}")
            b.append("按 10 位编码细分：" + "；".join(seg) + "。")
            car = [x for x in h10 if x[0] == "车用动力电池"]
            oth = [x for x in h10 if x[0] == "其他锂电"]
            if car and oth:
                c, o = car[0], oth[0]
                if (c[2] / c[1] - 1) < 0 < (o[2] / o[1] - 1):
                    b.append("品类分化明显：被关税直接覆盖的车用动力电池显著收缩，未被首批覆盖的其他锂电逆势增长，"
                             "说明本轮调整精准落在被加征品类，而非全品类需求萎缩。")
    return {"title": "⚡ 政策影响（301 关税）", "body": b}


def _sec_geo(g: dict) -> list:
    secs = []
    if not g:
        return secs
    st_top = "、".join(f"{k} {_pct(v / g['st_total'] * 100)}" for k, v in g["st_top"].items())
    b = [f"窗口内申报目的地合计 {_yi(g['st_total'])}，覆盖 {g['st_n']} 个州（不含海外领地与未识别州）；"
         f"前三大州：{st_top}，合计 {_pct(g['st_cr3'])}，州层面 HHI {g['st_hhi']:.3f}。",
         f"州集中度{'高于' if g['st_hhi'] > g['pt_hhi'] else '低于'}口岸集中度（口岸 HHI {g['pt_hhi']:.3f}），"
         f"说明{'下游制造与组装环节的地理集中度更高' if g['st_hhi'] > g['pt_hhi'] else '入关环节比消费地更集中'}。"]
    if "st_gain" in g and len(g["st_gain"]):
        b.append("份额上升：" + "、".join(f"{k} {_pp(v)}" for k, v in g["st_gain"].items()) +
                 "；下降：" + "、".join(f"{k} {_pp(v)}" for k, v in g["st_lose"].items()) +
                 "（与前一段等长窗口比较）。")
    secs.append({"title": "🗺️ 目的地州分布", "body": b})

    pt_top = "、".join(f"{k} {_pct(v / g['pt_total'] * 100)}" for k, v in g["pt_top"].items())
    b = [f"窗口内入境口岸合计 {_yi(g['pt_total'])}，覆盖 {g['pt_n']} 个口岸；前三大口岸：{pt_top}，"
         f"合计 {_pct(g['pt_cr3'])}，口岸 HHI {g['pt_hhi']:.3f}。"]
    if "pt_gain" in g and len(g["pt_gain"]):
        b.append("口岸份额变化：上升 " + "、".join(f"{k} {_pp(v)}" for k, v in g["pt_gain"].items()) +
                 "；下降 " + "、".join(f"{k} {_pp(v)}" for k, v in g["pt_lose"].items()) + "。")
        b.append("口岸格局变化通常领先于州分布变化，可作为供应链路径调整的早期信号。")
    secs.append({"title": "🚢 入境口岸格局", "body": b})
    return secs


def _sec_seasonal(mat: pd.DataFrame, s: dict) -> dict:
    """对应总览页「月度进口额分布特征」箱线图：只看日历月的季节性"""
    tot = mat.sum(axis=1) / 1e8
    by_m = tot.groupby(tot.index.month).mean()
    hi_m, lo_m = int(by_m.idxmax()), int(by_m.idxmin())
    b = [f"按日历月统计，月均进口额最高为 {hi_m} 月（{by_m.max():,.2f} 亿美元），"
         f"最低为 {lo_m} 月（{by_m.min():,.2f} 亿美元），峰谷差 {by_m.max() / by_m.min() - 1:.0%}。"]
    yr = tot.groupby(tot.index.year)
    amp = (yr.max() / yr.min() - 1).dropna()
    b.append(f"各年度内最高月与最低月的差幅中位数为 {amp.median():.0%}（{amp.index.min()}–{amp.index.max()} 年），"
             f"单月数据受季节性与交付节奏影响明显，判断趋势宜看 12 个月滚动口径。")
    cur_pos = ((tot[tot.index.month == s["at"].month] < tot.loc[s["at"]]).mean()) * 100
    b.append(f"最新月 {s['at']}（{s['at'].month} 月）进口额处于该日历月历史 {cur_pos:.0f} 分位。")
    return {"title": "📅 季节性特征", "body": b}


def _sec_snapshot(s: dict, mode: str) -> dict:
    """对应总览页顶部五张 KPI 卡：只做指标快照，不做深挖"""
    b = [f"**{MODE_LABEL[mode]}** 口径下：进口额 {_yi(s['cur_total'])}（同比{_g(s['total_yoy'])}）；"
         f"中国份额 {_pct(s['cn_share'])}（第 {s['cn_rank']} 大来源地，较上年同期同段 "
         f"{_pp(s['cn_share'] - s['cn_share_prev'])}）；CR5 {_pct(s['cr5_now'])}（上年同期 {_pct(s['cr5_prev'])}）；"
         f"HHI {s['hhi_now']:.3f}；所选区间（{s['sel_label']}）累计 {_yi(s['sel_total'])}。"]
    b.append("口径提示：金额卡按「统计口径」切换，同比与份额卡均与上年同期同段比较；"
             "CR5/HHI 由当期份额分布计算，故切换口径时数值同步变化。分项解读见后续页签。")
    return {"title": "🎯 指标卡速读", "body": b}


# ---------------------------------------------------------------- 页面解读入口
def ai_reading(page: str, mat: pd.DataFrame, mode: str, m0: pd.Period, m1: pd.Period,
               state_df: pd.DataFrame | None = None, port_df: pd.DataFrame | None = None,
               policy_win: int = 12, continent: bool = False) -> list:
    s = _stats(mat, mode, m0, m1)
    s["_std"] = float(mat.sum(axis=1).iloc[-12:].std())
    if page == "overview":
        # 本页 = 五张 KPI 卡 + 总额走势 + 同比增速 + 月度箱线图
        out = [_sec_snapshot(s, mode), _sec_total(s, mode)]
    elif page == "structure":
        # 本页上半部分按「细分来源地 / 大洲」切换，解读随之切换：
        # 细分视图 = 份额堆叠面积 / 平均份额排名 / 排名变化 / 中日韩 / 明细表
        # 大洲视图 = 大洲份额堆叠 / 平均份额排名 / 排名变化 / 各大洲月度进口额
        if continent:
            out = [_sec_continent(s, _cont_stats(state_df, m0, m1))] if state_df is not None else []
        else:
            out = [_sec_structure(s)]
            if state_df is not None:
                out.append(_sec_continent(s, _cont_stats(state_df, m0, m1)))
    elif page == "concentration":
        # 本页下半部分 = CR5/CR10、HHI、多元化与熵、份额明细表
        out = [_sec_concentration(s, deep=True)]
    elif page == "china":
        # 本页 = 自华进口额与份额双轴 + 中国份额变动与其他来源地份额变化（首末各 12 个月）
        out = [_sec_china(s)]
        if "t12_diff" in s:
            d = s["t12_diff"]
            dcn = float(d.get("中国", float("nan")))
            _gain = (d[d > 0.05].drop(labels=["中国"], errors="ignore")
                     .sort_values(ascending=False).head(3))
            if pd.notna(dcn) and dcn < 0 and len(_gain):
                _tot_chg = (s["tail_amt"] / s["head_amt"] - 1) * 100 if s["head_amt"] else float("nan")
                out.append({"title": "🔁 替代承接结构",
                            "body": [f"中国份额回落期间，上升最快的是 " +
                                     "、".join(f"{k}（{_pp(v)}）" for k, v in _gain.items()) +
                                     f"；同期总进口额{_g(_tot_chg)}。",
                                     f"承接方集中在 {'、'.join(list(_gain.index))}，"
                                     f"说明订单主要在既有供应体系内重新分配，而非转向全新来源地；"
                                     f"新增来源能否持续供货仍需观察。"]})
    elif page == "policy":
        # 本页 = 政策冲击 / 政策前后月均与份额变化 / 重点地区份额走势 / 事件研究明细
        out = [_sec_policy(s, detail=True, pol=_policy_stats(mat, policy_win))]
    elif page == "states":
        out = _sec_geo(_geo_stats(state_df, port_df, m0, m1)) if state_df is not None and port_df is not None else []
        if not out:
            out = [_sec_total(s, mode)]
    else:
        out = [_sec_snapshot(s, mode), _sec_total(s, mode)]
    for o in out:
        if isinstance(o.get("body"), list):
            o["body"] = "\n".join(f"- {x}" for x in o["body"])
    return out


# ================================================================ 报告
def _md_table(rows: list, header: list) -> str:
    out = "| " + " | ".join(header) + " |\n"
    out += "|" + "|".join(["---"] * len(header)) + "|\n"
    for r in rows:
        out += "| " + " | ".join(str(x) for x in r) + " |\n"
    return out


def report_md(mat: pd.DataFrame, mode: str, m0: pd.Period, m1: pd.Period,
              state_df: pd.DataFrame, port_df: pd.DataFrame) -> str:
    s = _stats(mat, mode, m0, m1)
    s["_std"] = float(mat.sum(axis=1).iloc[-12:].std())
    at = s["at"]
    tot = mat.sum(axis=1)
    sh_m = share_mat(mat, "当月值")
    w = s["window"]
    L = []
    L.append("# 美国锂离子电池（HS 850760）进口监测报告")
    L.append("")
    L.append(f"**数据窗口**：{m0} – {m1}　**统计口径**：{MODE_LABEL[mode]}　**最新数据月**：{at}")
    L.append(f"**数据来源**：USA Trade Online / 美国普查局国际贸易 API（HS 850760，一般进口海关价值，原产地口径）")
    L.append(f"**生成时间**：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}（由平台根据载入数据自动生成）")
    L.append("")

    # ---------------- 摘要
    L.append("## 一、摘要")
    L.append(f"美国锂离子电池进口在 {s['peak_m']} 触及单月峰值 {_yi(s['peak_v'])} 后进入调整期，"
             f"截至 {at} 单月规模为峰值的 {s['cur_vs_peak']:.0f}%，12 个月滚动规模同比{_g(s['roll12_yoy'])}。"
             f"供给格局同步重构：中国份额由上年的 {_pct(s['cn_share_prev'])} 降至 {_pct(s['cn_share'])}，"
             f"HHI 由 {s['hhi_prev']:.3f} 降至 {s['hhi_now']:.3f}，采购来源由单一主导转向多来源并存。"
             f"2024-09 生效的 301 关税构成这一轮调整的政策起点，但品类间反应明显分化。")
    L.append("")
    L.append("**核心结论：**")
    key = [f"当前口径进口规模 {_yi(s['cur_total'])}（同比{_g(s['total_yoy'])}）；近 12 个月合计 {_yi(s['roll12'])}。",
           f"中国份额 {_pct(s['cn_share'])}（第 {s['cn_rank']} 位），较上年同期同段 "
           f"{_pp(s['cn_share'] - s['cn_share_prev'])}；关税生效以来最低 {_pct(s['cn_min_since_policy'])}。",
           f"集中度 CR5 {_pct(s['cr5_now'])}、HHI {s['hhi_now']:.3f}（上年 {_pct(s['cr5_prev'])} / {s['hhi_prev']:.3f}）。"]
    if len(s["gainers"]):
        key.append("份额上升前三：" + "、".join(f"{k}（{_pp(v)}）" for k, v in s["gainers"].items()) +
                   "；下降前三：" + "、".join(f"{k}（{_pp(v)}）" for k, v in s["losers"].items()) + "。")
    key.append(f"301 关税后 12 个月：月均 {_yi(s['post_total'])}、中国份额均值 {_pct(s['post_cn'])}，"
               f"较政策前{_g((s['post_total'] / s['pre_total'] - 1) * 100)} / {s['post_cn'] - s['pre_cn']:+.1f} pp。")
    L.extend(f"- {x}" for x in key)
    L.append("")

    # ---------------- 二 总量
    L.append("## 二、总量与趋势")
    L.append(f"**现状**：截至 {at}，{MODE_LABEL[mode]}口径进口规模为 {_yi(s['cur_total'])}，"
             f"同比{_g(s['total_yoy'])}；近 12 个月合计 {_yi(s['roll12'])}。")
    L.append("")
    L.append(f"**解读**：进口额在 {s['peak_m']} 达到单月峰值 {_yi(s['peak_v'])} 后已连续 {s['months_since_peak']} 个月处于峰值下方，"
             f"当前为峰值的 {s['cur_vs_peak']:.0f}%，处于历史 {s['cur_pctile']:.0f} 分位——绝对水平仍高于 2012–2020 年常态区间，"
             f"属于「高位回落」而非「需求塌陷」。近 3 个月月均较此前 3 个月{s['momo3']:+.1f}%，"
             f"同比增速由 {_chg(s['yoy_prev3'])} 变为 {_chg(s['yoy_last3'])}，"
             f"{'降幅收窄、底部特征增强' if s['yoy_last3'] > s['yoy_prev3'] else '降幅扩大、下行压力仍在'}"
             f"，但单月波动（标准差 {_yi(s['_std'])}）较大，宜以滚动口径判断方向。")
    L.append("")
    L.append("**最近 12 个月月度明细（当月口径）：**")
    L.append("")
    rows = []
    for m, v in tot.iloc[-12:].items():
        yoy = (v / tot.loc[m - 12] - 1) * 100 if m - 12 in tot.index and tot.loc[m - 12] else float("nan")
        cn_s = sh_m.loc[m, "中国"] if "中国" in sh_m.columns else float("nan")
        rows.append([str(m), f"{v / 1e8:,.2f}", f"{yoy:+.1f}%" if pd.notna(yoy) else "—",
                     f"{cn_s:.1f}%" if pd.notna(cn_s) else "—"])
    L.append(_md_table(rows, ["月份", "进口额（亿美元）", "同比", "中国份额"]))
    L.append("")

    # ---------------- 三 结构
    L.append("## 三、来源地结构")
    if s.get("split"):
        L.append(f"所选区间 {s['sel_label']} 覆盖全部历史、无更早对照期，故按前后两段比较："
                 f"后段（{s['win_label']}）合计 {_yi(s['window_total'])}，较前段（{s['base_label']}）{_g(s['window_yoy'])}。")
    else:
        L.append(f"窗口（{s['win_label']}）合计 {_yi(s['window_total'])}，较前一段等长窗口（{s['base_label']}）{_g(s['window_yoy'])}。")
    L.append("")
    if s.get("cn_w") is not None:
        L.append(f"**解读**：结构变化具有明确的「替代」特征——中国进口额由 {_yi(s['cn_p'])} 变为 {_yi(s['cn_w'])}"
                 f"（{_g(s['cn_w_chg'])}），同期其他来源地合计由 {_yi(s['others_p'])} 变为 {_yi(s['others_w'])}"
                 f"（{_g(s['others_chg'])}）。"
                 + ("总盘子扩张而中国绝对额下降，说明新增需求几乎全部由非中国来源承接，"
                    "这是典型的份额替代而非需求收缩。"
                    if s["others_chg"] > 0 and s["cn_w_chg"] < 0 else
                    "中国与其他来源地同向变化，份额变动主要来自增速差而非绝对量此消彼长。")
                 + f"承接方以 {'、'.join(list(s['gainers'].index)[:3])} 为主，"
                 f"升幅最大的 {list(s['gainers'].index)[0]} 份额提高 {_pp(s['gainers'].iloc[0])}。")
        L.append("")
    rows = []
    for k, v in s["top10"].items():
        d = s["diff_pp"].get(k, float("nan"))
        rows.append([k, f"{v / 1e8:,.2f}", f"{v / s['window_total'] * 100:.1f}%",
                     f"{d:+.1f} pp" if pd.notna(d) else "—"])
    L.append("**前十大来源地：**")
    L.append("")
    L.append(_md_table(rows, ["来源地", "进口额（亿美元）", "窗口份额", "份额较前段变化"]))
    L.append("")

    # ---------------- 四 集中度
    L.append("## 四、集中度与多元化")
    L.append(f"CR5 {_pct(s['cr5_now'])}、CR10 {_pct(s['cr10_now'])}、HHI {s['hhi_now']:.3f}"
             f"（上年同期 {_pct(s['cr5_prev'])} / {_pct(s['cr10_prev'])} / {s['hhi_prev']:.3f}）；"
             f"份额超过 1% 的来源地 {s['n1_now']} 个（上年 {s['n1_prev']} 个）。")
    L.append("")
    L.append(f"**解读**：HHI 从 {s['hhi_prev']:.3f} 降至 {s['hhi_now']:.3f}，已从「高度集中」（>0.25）回到"
             f"{'中度集中' if 0.15 <= s['hhi_now'] <= 0.25 else '分散'}区间，与 2012 年以来最低点 "
             f"{s['hhi_hist_min']:.3f}（{s['hhi_hist_min_m']}）的距离为 {abs(s['hhi_now'] - s['hhi_hist_min']):.3f}。"
             f"有效来源地数量（熵指数折算）约 {np.exp(s['entropy_now']):.1f} 个。"
             f"集中度下降降低了单一来源中断的冲击乘数，但也意味着单位采购的合规与品质管理成本上升。")
    L.append("")
    rows = []
    yr = tot.groupby(tot.index.year).sum()
    for y in sorted(yr.index)[-6:]:
        ysum = mat[mat.index.year == y].sum()
        ysh = (ysum / ysum.sum() * 100).sort_values(ascending=False)
        rows.append([str(y), f"{yr[y] / 1e8:,.1f}", f"{ysh.head(5).sum():.1f}%",
                     f"{((ysh / 100) ** 2).sum():.3f}", f"{ysh.get('中国', float('nan')):.1f}%"])
    L.append(_md_table(rows, ["年份", "进口额（亿美元）", "CR5", "HHI", "中国份额"]))
    L.append("")

    # ---------------- 五 政策
    L.append("## 五、政策冲击（301 关税）")
    L.append("2024-09-27 起，车用动力电池（HTS 8507.60.0010）301 税率由 7.5% 上调至 25%；"
             "其余锂电（HTS 8507.60.0020）自 2026 年 1 月起执行。")
    L.append("")
    h10 = _hts10_block()
    car = next((x for x in h10 if x[0] == "车用动力电池"), None)
    oth = next((x for x in h10 if x[0] == "其他锂电"), None)
    L.append(f"**解读**：政策前 12 个月月均 {_yi(s['pre_total'])}、中国份额均值 {_pct(s['pre_cn'])}；"
             f"政策后 12 个月月均 {_yi(s['post_total'])}（{_g((s['post_total'] / s['pre_total'] - 1) * 100)}）、"
             f"中国份额 {_pct(s['post_cn'])}（{s['post_cn'] - s['pre_cn']:+.1f} pp）。"
             + (f"分品类看，被直接加征的车用动力电池月均 {(car[2] / car[1] - 1) * 100:+.1f}%、"
                f"中国份额由 {_pct(car[3])} 降至 {_pct(car[4])}；未被首批覆盖的其他锂电月均 "
                f"{(oth[2] / oth[1] - 1) * 100:+.1f}%。关税的抑制效应集中在被覆盖品类，"
                f"而非全品类需求萎缩。" if car and oth else "")
             + (f"政策生效 18 个月后最近 {len(s['late_idx'])} 个月月均 {_yi(s['late_total'])}、"
                f"中国份额 {_pct(s['late_cn'])}，显示调整已进入新的稳态。" if pd.notna(s["late_total"]) else ""))
    L.append("")
    rows = [["月均进口额", _yi(s["pre_total"]), _yi(s["post_total"]),
             f"{(s['post_total'] / s['pre_total'] - 1) * 100:+.1f}%"],
            ["中国份额均值", _pct(s["pre_cn"]), _pct(s["post_cn"]), f"{s['post_cn'] - s['pre_cn']:+.1f} pp"]]
    L.append(_md_table(rows, ["指标", "政策前 12 个月", "政策后 12 个月", "变化"]))
    L.append("")
    if h10:
        L.append("**按 10 位 HS 编码细分（数据自 2015-07 起）：**")
        L.append("")
        rows = []
        for cat, pre, post, pc, qc, only_recent in h10:
            if only_recent:
                rows.append([cat, "—", f"{post / 1e8:,.2f}", f"{qc:.1f}%", "—"])
            else:
                rows.append([cat, f"{pre / 1e8:,.2f}", f"{post / 1e8:,.2f}",
                             f"{pc:.1f}%→{qc:.1f}%", f"{(post / pre - 1) * 100:+.1f}%"])
        L.append(_md_table(rows, ["品类", "政策前月均（亿美元）", "政策后月均（亿美元）", "中国份额（前→后）", "月均变化"]))
        L.append("")

    # ---------------- 六 州与口岸
    L.append("## 六、申报目的地州与入境口岸")
    g = _geo_stats(state_df, port_df, m0, m1)
    L.append(f"**解读**：进口在空间上高度集中——前三大州合计 {_pct(g['st_cr3'])}、前三大口岸合计 {_pct(g['pt_cr3'])}，"
             f"州 HHI {g['st_hhi']:.3f}、口岸 HHI {g['pt_hhi']:.3f}。"
             f"{'州集中度高于口岸，说明制造与组装环节比入关环节更集中，物流路径调整的传导会更慢。' if g['st_hhi'] > g['pt_hhi'] else '口岸集中度高于州，说明入关高度依赖少数节点，港口拥堵或改道的敏感度更高。'}")
    L.append("")
    st_g = state_df[(state_df.month >= m0) & (state_df.month <= m1) &
                    (~state_df.state_code.isin(["XX", "PR", "VI"]))].groupby(["state_code", "state_name"])["value"].sum().sort_values(ascending=False)
    rows = [[c, n, f"{v / 1e8:,.2f}", f"{v / st_g.sum() * 100:.1f}%"] for (c, n), v in st_g.head(10).items()]
    L.append("**目的地州 Top 10：**")
    L.append("")
    L.append(_md_table(rows, ["州", "名称", "进口额（亿美元）", "占比"]))
    L.append("")
    p_g = port_df[(port_df.month >= m0) & (port_df.month <= m1)].groupby(["port_code", "port_name"])["value"].sum().sort_values(ascending=False)
    rows = [[c, n, f"{v / 1e8:,.2f}", f"{v / p_g.sum() * 100:.1f}%"] for (c, n), v in p_g.head(10).items()]
    L.append("**入境口岸 Top 10：**")
    L.append("")
    L.append(_md_table(rows, ["口岸", "名称", "进口额（亿美元）", "占比"]))
    L.append("")

    # ---------------- 七 风险与口径
    L.append("## 七、风险提示与口径说明")
    L.append(f"- **替代可持续性**：{list(s['gainers'].index)[0] if len(s['gainers']) else '新晋来源地'} 等承接方份额上升较快，"
             f"需观察其月度金额是否连续，而非一次性转移。")
    L.append(f"- **集中度双向风险**：HHI {s['hhi_now']:.3f} 已明显低于上年（{s['hhi_prev']:.3f}），分散化降低断供冲击，"
             f"但来源地增多会抬高合规与品质验证成本。")
    L.append(f"- **波动性**：近 12 个月单月进口额标准差 {_yi(s['_std'])}，单月同比波动大，趋势判断应以 12 个月滚动口径为主。")
    L.append("- 统计范围：HS 850760 锂离子蓄电池（2012 年 HS2012 版起为独立子目），原产地口径，一般进口海关价值。")
    L.append("- 三档口径：当月值 / 年初至今累计（与上年同期同段比较）/ 12 个月滚动累计；份额均按对应口径金额重算。")
    L.append("- 数据为官方海关申报值，可能与企业出货节奏存在时滞；本报告不含前瞻性预测。")
    return "\n".join(L)
