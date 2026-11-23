# -*- coding: utf-8 -*-
"""
美国锂离子电池 10 位 HTS 品类数据层

编码沿革：
  8507600010  车用动力电池（EV 动力电池，2015-07 起统计）
  8507600020  其他锂离子电池（2015-07 ~ 2026-01）
  8507600030  储能电池系统（BESS，2026-02 起；统计注释 2：≥1 kWh、含 BMS、整体封装）
  8507600090  其他锂离子电池（2026-02 起，0030 之外的残余类：消费电子、电动工具等）

数据来源：US Census API（HTS 10 位），原产国 × 海关区 × 月份；
本模块只保留「真实原产国 + 全国关区合计」口径，与平台 6 位总额逐月一致（已验证）。
"""
import os

import pandas as pd
import streamlit as st

from .data import COUNTRY_CN

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTS10_DIR = os.path.join(BASE_DIR, "data", "raw", "hts10")
FILE_EV = os.path.join(HTS10_DIR, "8507600010_美国月度进口数据.xlsx")
FILE_OTHER = os.path.join(HTS10_DIR, "其他锂离子电池_2013至今_月度进口数据.xlsx")

START_MONTH = pd.Period("2015-07", freq="M")

# 品类编码 → 展示名
CAT = {
    "8507600010": "车用动力电池",
    "8507600020": "其他锂电（旧口径）",
    "8507600030": "储能电池系统",
    "8507600090": "其他锂电",
}
CAT_CODE = {v: k for k, v in CAT.items()}

# 连续口径：0020 在 2026-02 起由 0030 + 0090 承接
CONT_CAT = {"8507600010": "车用动力电池", "8507600020": "其他锂电",
            "8507600030": "其他锂电", "8507600090": "其他锂电"}
CONT_ORDER = ["车用动力电池", "其他锂电"]
CAT_ORDER = ["车用动力电池", "其他锂电（旧口径）", "储能电池系统", "其他锂电"]

COLORS = {"车用动力电池": "#2E86AB", "其他锂电": "#E8A33D",
          "其他锂电（旧口径）": "#E8A33D", "储能电池系统": "#D64541", "其他锂电 ": "#8E7CC3"}


def _read(path: str, sheet: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)
    df = df.rename(columns={"一般进口金额（美元）": "value", "月份": "month",
                            "HTS编码": "hts10", "原产国代码": "ccode", "原产国名称": "country_raw"})
    df["ccode"] = df["ccode"].astype(str).str.strip()
    df["hts10"] = df["hts10"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["region"] = df["海关区代码"].astype(str).str.strip()
    cid = pd.to_numeric(df["ccode"], errors="coerce")
    # 只保留真实原产国（4 位数字代码 ≥ 1000）与全国关区合计行，避免聚合组与关区重复计入
    df = df[(cid >= 1000) & (df["region"] == "-")].copy()
    df["month"] = pd.PeriodIndex(pd.to_datetime(df["month"].astype(str), format="%Y-%m"), freq="M")
    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0.0)
    df["country"] = df["country_raw"].astype(str).str.strip().map(lambda x: COUNTRY_CN.get(x, x.title()))
    return df[["month", "country", "hts10", "value"]]


@st.cache_data(show_spinner="正在加载 10 位 HTS 品类数据…")
def load_hts10(_sig: tuple) -> pd.DataFrame:
    ev = _read(FILE_EV, "API明细")
    ev["hts10"] = "8507600010"
    other = _read(FILE_OTHER, "API原始明细")
    df = pd.concat([ev, other], ignore_index=True)
    df = df[df["value"] > 0]
    df["cat"] = df["hts10"].map(CAT)
    df["cat_cont"] = df["hts10"].map(CONT_CAT)
    return df.reset_index(drop=True)


def _sig() -> tuple:
    out = []
    for p in (FILE_EV, FILE_OTHER):
        s = os.stat(p)
        out += [round(s.st_mtime, 0), s.st_size]
    return tuple(out)


def available() -> bool:
    """两个 10 位品类 Excel 是否齐全（云端漏传时界面降级为提示，不报错）"""
    return os.path.exists(FILE_EV) and os.path.exists(FILE_OTHER)


def data() -> pd.DataFrame | None:
    if not available():
        return None
    return load_hts10(_sig())


# ---------------------------------------------------------------- 透视
def mat_cat(df: pd.DataFrame, col: str = "cat_cont") -> pd.DataFrame:
    """月份 × 品类金额矩阵（美元）"""
    m = df.groupby(["month", col], as_index=False)["value"].sum()
    return m.pivot(index="month", columns=col, values="value").fillna(0).sort_index()


def mat_country_cat(df: pd.DataFrame, col: str = "cat_cont") -> pd.DataFrame:
    """来源地 × 品类 总额（美元），用于政策前后对比"""
    return df.groupby(["country", col], as_index=False)["value"].sum().pivot(
        index="country", columns=col, values="value").fillna(0)


def share_of_total(m: pd.DataFrame) -> pd.DataFrame:
    return m.div(m.sum(axis=1), axis=0) * 100
