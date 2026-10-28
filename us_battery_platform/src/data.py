# -*- coding: utf-8 -*-
"""
美国锂离子电池（HS 850760）进口监测平台 —— 数据层
数据来源：US Census Bureau API（imports/state-hs、imports/port-hs）
口径：一般进口海关价值（美元），原产国口径，月度
"""
import hashlib
import os

import numpy as np
import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "data", "raw", "850760_美国进口数据_2017-2026.xlsx")
CACHE_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------- 国家名称映射
COUNTRY_CN = {
    "CHINA": "中国", "TAIWAN": "中国台湾", "HONG KONG": "中国香港", "MACAU": "中国澳门",
    "KOREA, SOUTH": "韩国", "JAPAN": "日本", "GERMANY": "德国", "CANADA": "加拿大",
    "MEXICO": "墨西哥", "MALAYSIA": "马来西亚", "VIETNAM": "越南", "POLAND": "波兰",
    "UNITED KINGDOM": "英国", "ITALY": "意大利", "THAILAND": "泰国", "INDIA": "印度",
    "FRANCE": "法国", "SWITZERLAND": "瑞士", "SINGAPORE": "新加坡", "NETHERLANDS": "荷兰",
    "BELGIUM": "比利时", "AUSTRIA": "奥地利", "SPAIN": "西班牙", "HUNGARY": "匈牙利",
    "CZECH REPUBLIC": "捷克", "SWEDEN": "瑞典", "INDONESIA": "印度尼西亚",
    "PHILIPPINES": "菲律宾", "TURKEY": "土耳其", "BRAZIL": "巴西", "ISRAEL": "以色列",
    "MOROCCO": "摩洛哥", "AUSTRALIA": "澳大利亚", "RUSSIA": "俄罗斯", "DENMARK": "丹麦",
    "NORWAY": "挪威", "FINLAND": "芬兰", "IRELAND": "爱尔兰", "PORTUGAL": "葡萄牙",
    "GREECE": "希腊", "ROMANIA": "罗马尼亚", "SLOVAKIA": "斯洛伐克", "SLOVENIA": "斯洛文尼亚",
    "CROATIA": "克罗地亚", "BULGARIA": "保加利亚", "SERBIA": "塞尔维亚", "UKRAINE": "乌克兰",
    "BELARUS": "白俄罗斯", "LITHUANIA": "立陶宛", "LATVIA": "拉脱维亚", "ESTONIA": "爱沙尼亚",
    "ICELAND": "冰岛", "LUXEMBOURG": "卢森堡", "MALTA": "马耳他", "CYPRUS": "塞浦路斯",
    "ARGENTINA": "阿根廷", "CHILE": "智利", "COLOMBIA": "哥伦比亚", "PERU": "秘鲁",
    "ECUADOR": "厄瓜多尔", "URUGUAY": "乌拉圭", "PARAGUAY": "巴拉圭", "BOLIVIA": "玻利维亚",
    "VENEZUELA": "委内瑞拉", "COSTA RICA": "哥斯达黎加", "PANAMA": "巴拿马",
    "GUATEMALA": "危地马拉", "HONDURAS": "洪都拉斯", "NICARAGUA": "尼加拉瓜",
    "EL SALVADOR": "萨尔瓦多", "DOMINICAN REPUBLIC": "多米尼加", "JAMAICA": "牙买加",
    "BAHAMAS": "巴哈马", "BARBADOS": "巴巴多斯", "BERMUDA": "百慕大",
    "TRINIDAD AND TOBAGO": "特立尼达和多巴哥", "CAYMAN ISLANDS": "开曼群岛",
    "BRITISH VIRGIN ISLANDS": "英属维尔京群岛", "TURKS AND CAICOS ISLANDS": "特克斯和凯科斯群岛",
    "CURACAO": "库拉索", "ST PIERRE AND MIQUELON": "圣皮埃尔和密克隆", "MONTSERRAT": "蒙特塞拉特",
    "SOUTH AFRICA": "南非", "EGYPT": "埃及", "NIGER": "尼日尔", "NIGERIA": "尼日利亚",
    "KENYA": "肯尼亚", "TANZANIA": "坦桑尼亚", "ETHIOPIA": "埃塞俄比亚", "GHANA": "加纳",
    "CAMEROON": "喀麦隆", "CHAD": "乍得", "MALI": "马里", "GUINEA": "几内亚",
    "SIERRA LEONE": "塞拉利昂", "MOZAMBIQUE": "莫桑比克", "ZAMBIA": "赞比亚",
    "GABON": "加蓬", "SEYCHELLES": "塞舌尔", "MAYOTTE": "马约特", "GUADELOUPE": "瓜德罗普",
    "BANGLADESH": "孟加拉国", "PAKISTAN": "巴基斯坦", "SRI LANKA": "斯里兰卡",
    "NEPAL": "尼泊尔", "BURMA": "缅甸", "CAMBODIA": "柬埔寨", "LAOS": "老挝",
    "MONGOLIA": "蒙古", "KOREA, NORTH": "朝鲜", "NEW ZEALAND": "新西兰",
    "FIJI": "斐济", "PAPUA NEW GUINEA": "巴布亚新几内亚", "TONGA": "汤加", "TUVALU": "图瓦卢",
    "SAUDI ARABIA": "沙特阿拉伯", "UNITED ARAB EMIRATES": "阿联酋", "QATAR": "卡塔尔",
    "KUWAIT": "科威特", "OMAN": "阿曼", "BAHRAIN": "巴林", "JORDAN": "约旦",
    "LEBANON": "黎巴嫩", "IRAQ": "伊拉克", "IRAN": "伊朗", "GEORGIA": "格鲁吉亚",
    "ARMENIA": "亚美尼亚", "AZERBAIJAN": "阿塞拜疆", "KAZAKHSTAN": "哈萨克斯坦",
    "UZBEKISTAN": "乌兹别克斯坦", "AFGHANISTAN": "阿富汗", "ALGERIA": "阿尔及利亚",
    "TUNISIA": "突尼斯", "LIBYA": "利比亚", "LIECHTENSTEIN": "列支敦士登", "MONACO": "摩纳哥",
    "SAN MARINO": "圣马力诺", "ANDORRA": "安道尔", "NORTH MACEDONIA": "北马其顿",
    "ALBANIA": "阿尔巴尼亚", "BOSNIA AND HERZEGOVINA": "波黑", "MOLDOVA": "摩尔多瓦",
}

# 重点观测来源国
KEY_COUNTRIES = ["中国", "韩国", "日本", "中国台湾", "越南", "马来西亚", "墨西哥", "德国", "加拿大", "波兰"]

# 固定配色（重点国家）
COUNTRY_COLORS = {
    "中国": "#D64541", "韩国": "#2E6DA4", "日本": "#E67E22", "中国台湾": "#7D3C98",
    "越南": "#16A085", "马来西亚": "#27AE60", "墨西哥": "#7F8C8D", "德国": "#B7950B",
    "加拿大": "#5D6D7E", "波兰": "#A04000", "泰国": "#48C9B0", "印度": "#9B59B6",
    "英国": "#34495E", "意大利": "#C0392B", "印度尼西亚": "#1ABC9C", "菲律宾": "#F1C40F",
    "其他": "#B4B2A9",
}

POLICY_DATE = pd.Period("2024-09", freq="M")  # 2024 年 301 关税调整生效


def _cn(name: str) -> str:
    return COUNTRY_CN.get(str(name).strip().upper(), str(name).strip())


# ---------------------------------------------------------------- 原始数据读取
def _read_sheet(sheet: str, code_col: str, name_col: str, code_en: str, name_en: str) -> pd.DataFrame:
    """读取单个 sheet 并做基础清洗，返回长表。code_col/name_col 为地理维度的中文列名"""
    df = pd.read_excel(RAW_FILE, sheet_name=sheet, header=5)
    df = df.rename(columns={
        "国家名称（原产国）": "country_raw", "月份": "month",
        code_col: code_en, name_col: name_en,
        "进口金额（美元）": "value", "海运毛重（千克）": "w_sea", "空运毛重（千克）": "w_air",
        "HS编码": "hs",
    })
    keep = ["country_raw", "month", "value", "w_sea", "w_air", code_en, name_en]
    df = df[[c for c in keep if c in df.columns]].copy()
    df["country"] = df["country_raw"].map(_cn)
    df["month"] = pd.PeriodIndex(pd.to_datetime(df["month"], format="%Y-%m"), freq="M")
    for c in ["value", "w_sea", "w_air"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["w_total"] = df["w_sea"] + df["w_air"]
    return df


def _file_hash() -> str:
    """原始文件内容哈希，用于缓存失效判断"""
    h = hashlib.md5()
    with open(RAW_FILE, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@st.cache_data(show_spinner="正在加载 USITC/Census 数据…")
def _load_sheet(_hash: str, sheet: str, code_col: str, name_col: str, code_en: str, name_en: str) -> pd.DataFrame:
    return _read_sheet(sheet, code_col, name_col, code_en, name_en)


_SHEET_CONF = {
    "load_state": ("State_目的地州", "美国州代码", "美国州名称", "state_code", "state_name"),
    "load_port": ("Port_入境口岸", "口岸代码", "卸货口岸名称", "port_code", "port_name"),
}

# ---------------------------------------------------------------- 数据源路由
# 优先级：API 更新产生的 Parquet 缓存 > 用户导入的 Excel
_PARQUET = {
    "state": os.path.join(CACHE_DIR, "state.parquet"),
    "port": os.path.join(CACHE_DIR, "port.parquet"),
}


@st.cache_data(show_spinner=False)
def _load_parquet(_sig: tuple, kind: str) -> pd.DataFrame:
    df = pd.read_parquet(_PARQUET[kind])
    df["month"] = pd.PeriodIndex(df["month"], freq="M")
    return df


def _parquet_sig(kind: str):
    p = _PARQUET[kind]
    if os.path.exists(p):
        st_ = os.stat(p)
        return (st_.st_mtime, st_.st_size)
    return (0, 0)


def st_cache_data_clear():
    """数据更新后清除全部缓存，强制重新加载"""
    st.cache_data.clear()


def load_state() -> pd.DataFrame:
    sig = _parquet_sig("state")
    if sig != (0, 0):
        return _load_parquet(sig, "state")
    return _load_sheet(_file_hash(), *_SHEET_CONF["load_state"])


def load_port() -> pd.DataFrame:
    sig = _parquet_sig("port")
    if sig != (0, 0):
        return _load_parquet(sig, "port")
    return _load_sheet(_file_hash(), *_SHEET_CONF["load_port"])


# ---------------------------------------------------------------- 指标计算
def monthly_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """月度 × 国家 进口额矩阵（州/口岸汇总 = 美国全国口径）"""
    m = df.groupby(["month", "country"], as_index=False)["value"].sum()
    return m.pivot(index="month", columns="country", values="value").fillna(0)


def monthly_weights(df: pd.DataFrame) -> pd.DataFrame:
    """月度 × 国家 毛重矩阵"""
    m = df.groupby(["month", "country"], as_index=False)["w_total"].sum()
    return m.pivot(index="month", columns="country", values="w_total").fillna(0)


def with_shares(mat: pd.DataFrame) -> pd.DataFrame:
    """在月度×国家矩阵上追加各国家份额列（%），返回 (value_mat, share_mat)"""
    tot = mat.sum(axis=1)
    share = mat.div(tot.replace(0, np.nan), axis=0) * 100
    return tot, share


def concentration(share: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """CR_n、HHI、熵指数（份额单位：%）"""
    s = (share / 100).copy()
    cr = share.apply(lambda r: r.nlargest(top_n).sum(), axis=1)
    hhi = (s ** 2).sum(axis=1)
    ent = -(s * np.log(s.replace(0, np.nan))).sum(axis=1)
    return pd.DataFrame({"CR%d" % top_n: cr, "HHI": hhi, "熵指数": ent})


def yoy(series: pd.Series) -> pd.Series:
    """同比增速（%），月度数据滞后 12 期"""
    return series.pct_change(12) * 100


def rolling12(series: pd.Series) -> pd.Series:
    return series.rolling(12).sum()


def unit_price(value_mat: pd.DataFrame, weight_mat: pd.DataFrame) -> pd.DataFrame:
    """单价代理指标：美元/千克（基于海运+空运毛重，仅对有重量的月份计算）"""
    w = weight_mat.replace(0, np.nan)
    return (value_mat / w).where(w.notna() & (value_mat > 0))


def event_study(mat: pd.DataFrame, share: pd.DataFrame, window: int = 12,
                policy: pd.Period = POLICY_DATE):
    """政策前后各 window 个月的均值对比，返回 DataFrame：国家 | 政策前月均额 | 政策后月均额 | 份额变化pp"""
    pre_idx = [policy - i for i in range(1, window + 1)]
    post_idx = [policy + i for i in range(window)]
    pre_idx = [p for p in pre_idx if p in mat.index]
    post_idx = [p for p in post_idx if p in mat.index]

    pre_v = mat.loc[pre_idx].mean()
    post_v = mat.loc[post_idx].mean()
    pre_s = share.loc[pre_idx].mean()
    post_s = share.loc[post_idx].mean()

    out = pd.DataFrame({
        "国家": mat.columns,
        "政策前月均(百万美元)": pre_v.values / 1e6,
        "政策后月均(百万美元)": post_v.values / 1e6,
        "政策前份额(%)": pre_s.values,
        "政策后份额(%)": post_s.values,
    })
    out["月均额变化(%)"] = np.where(out["政策前月均(百万美元)"] > 0,
                                (out["政策后月均(百万美元)"] / out["政策前月均(百万美元)"] - 1) * 100, np.nan)
    out["份额变化(pp)"] = out["政策后份额(%)"] - out["政策前份额(%)"]
    return out.sort_values("政策后月均(百万美元)", ascending=False).reset_index(drop=True)


def fmt_usd(v: float) -> str:
    """美元金额格式化：亿/千万"""
    if v >= 1e8:
        return f"{v/1e8:.2f} 亿美元"
    if v >= 1e4:
        return f"{v/1e4:.1f} 万美元"
    return f"{v:,.0f} 美元"
