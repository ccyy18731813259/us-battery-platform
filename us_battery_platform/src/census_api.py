# -*- coding: utf-8 -*-
"""
美国 Census Bureau 国际贸易 API 自动更新模块
端点：imports/state-hs、imports/porths（HS 850760，月度，原产国口径）
策略：本地 Parquet 缓存（data/processed/）→ 增量拉取缺失月份 → 失败时回退 Excel
API Key 免费申请：https://api.census.gov/data/key_signup.html
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import pandas as pd

from .data import BASE_DIR, CACHE_DIR, _cn

API_BASE = "https://api.census.gov/data/timeseries/intltrade/imports"
COMMODITY = "850760"

ENDPOINTS = {
    "state": {
        "path": "statehs",
        "get": ["CTY_CODE", "CTY_NAME", "YEAR", "MONTH", "STATE",
                "I_COMMODITY", "GEN_VAL_MO", "VES_WGT_MO", "AIR_WGT_MO"],
        "geo_cols": {"code": "STATE", "name": None},
    },
    "port": {
        "path": "porths",
        "get": ["CTY_CODE", "CTY_NAME", "YEAR", "MONTH", "PORT", "PORT_NAME",
                "I_COMMODITY", "GEN_VAL_MO", "VES_WGT_MO", "AIR_WGT_MO"],
        "geo_cols": {"code": "PORT", "name": "PORT_NAME"},
    },
}

STATE_NAMES = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DC": "District of Columbia", "DE": "Delaware", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine",
    "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri", "MS": "Mississippi",
    "MT": "Montana", "NC": "North Carolina", "ND": "North Dakota",
    "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NV": "Nevada", "NY": "New York", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "PR": "Puerto Rico", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VA": "Virginia", "VI": "U.S. Virgin Islands", "VT": "Vermont",
    "WA": "Washington", "WI": "Wisconsin", "WV": "West Virginia",
    "WY": "Wyoming", "XX": "Unidentified",
}

PARQUET_FILES = {"state": os.path.join(CACHE_DIR, "state.parquet"),
                 "port": os.path.join(CACHE_DIR, "port.parquet")}
META_FILE = os.path.join(CACHE_DIR, "api_meta.json")
KEY_FILE = os.path.join(CACHE_DIR, "census_key.txt")

START_MONTH = pd.Period("2017-01", freq="M")


class CensusAPIError(Exception):
    pass


# ---------------------------------------------------------------- API Key
def get_api_key() -> str:
    """key 来源优先级：环境变量 > 本地 key 文件"""
    if os.environ.get("CENSUS_API_KEY"):
        return os.environ["CENSUS_API_KEY"].strip()
    if os.path.exists(KEY_FILE):
        try:
            return open(KEY_FILE, encoding="utf-8").read().strip()
        except OSError:
            return ""
    return ""


def save_api_key(key: str):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key.strip())


# ---------------------------------------------------------------- 底层请求
def _http_get_json(url: str, timeout: int = 25) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BatteryImportMonitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except OSError:
            pass
        raise CensusAPIError(f"HTTP {e.code}: {body or e.reason}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise CensusAPIError(f"网络连接失败：{e}") from e


def fetch_month(kind: str, ym: pd.Period, key: str = "") -> pd.DataFrame:
    """拉取某个月、单一端点的明细数据，返回标准化长表（列结构与 Excel 路径一致）

    注意：API 会在明细行之外返回两类汇总行（国别合计 geo="-"，全部国家合计 CTY_NAME="TOTAL FOR ALL COUNTRIES"），
    若不过滤会导致重复计算；此处统一剔除，仅保留 国家 × 州/口岸 明细。
    """
    conf = ENDPOINTS[kind]
    geo_code_col = conf["geo_cols"]["code"]
    params = {
        "get": ",".join(conf["get"]),
        "COMM_LVL": "HS6",
        "I_COMMODITY": COMMODITY,   # 谓词名必须是变量名 I_COMMODITY（COMMODITY 会报 unknown predicate）
        "SUMMARY_LVL": "DET",       # 只要明细行，排除 EU/APEC 等国家分组汇总
        "time": str(ym),
    }
    if key:
        params["key"] = key
    url = f"{API_BASE}/{conf['path']}?" + urllib.parse.urlencode(params)
    raw = _http_get_json(url)
    if not raw or len(raw) < 2:
        # 空月：返回与标准结构一致的空表，避免污染下游缓存列
        base_cols = ["country_raw", "country", "month", "value", "w_sea", "w_air"]
        geo = ["state_code", "state_name"] if kind == "state" else ["port_code", "port_name"]
        empty = pd.DataFrame(columns=base_cols + geo + ["w_total"])
        return empty.astype({"value": "float64", "w_sea": "float64", "w_air": "float64", "w_total": "float64"})

    header = []
    seen = {}
    for c in raw[0]:
        seen[c] = seen.get(c, 0) + 1
        header.append(c if seen[c] == 1 else f"{c}_{seen[c]}")  # API 会重复返回 I_COMMODITY 等列
    df = pd.DataFrame(raw[1:], columns=header)

    # 剔除汇总行：全部国家合计 + 国别合计（geo 为 "-"）
    df = df[~df["CTY_NAME"].astype(str).str.upper().str.startswith("TOTAL FOR ALL")]
    df = df[df.get("CTY_CODE", "").astype(str).str.strip() != "-"]
    df = df[df[geo_code_col].astype(str).str.strip() != "-"]

    out = pd.DataFrame()
    out["country_raw"] = df["CTY_NAME"].str.strip()
    out["country"] = out["country_raw"].map(_cn)
    out["month"] = str(ym)
    out["value"] = pd.to_numeric(df.get("GEN_VAL_MO", 0), errors="coerce").fillna(0)
    out["w_sea"] = pd.to_numeric(df.get("VES_WGT_MO", 0), errors="coerce").fillna(0)
    out["w_air"] = pd.to_numeric(df.get("AIR_WGT_MO", 0), errors="coerce").fillna(0)
    if kind == "state":
        code = df["STATE"].astype(str).str.strip()
        out["state_code"] = code
        out["state_name"] = code.map(STATE_NAMES).fillna(code)
    else:
        out["port_code"] = df["PORT"].astype(str).str.strip()
        out["port_name"] = df["PORT_NAME"].astype(str).str.strip()
    out["w_total"] = out["w_sea"] + out["w_air"]
    # 剔除全零行，与历史 Excel 导出口径保持一致
    out = out[~((out["value"] == 0) & (out["w_total"] == 0))]
    return out.reset_index(drop=True)


def probe_latest_month(key: str = "", max_try: int = 5) -> pd.Period | None:
    """探测 API 上已发布的最新月份：从上上月开始向前最多试 max_try 个月"""
    cand = pd.Period(datetime.now().strftime("%Y-%m"), freq="M") - 1
    for _ in range(max_try):
        try:
            df = fetch_month("state", cand, key)
            if len(df):
                return cand
        except CensusAPIError:
            return None  # 网络不通/无 key，直接放弃本次探测
        cand -= 1
    return None


# ---------------------------------------------------------------- 本地缓存
def _read_meta() -> dict:
    if os.path.exists(META_FILE):
        try:
            return json.load(open(META_FILE, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _write_meta(meta: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(meta, open(META_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _replace_month(kind: str, new_df: pd.DataFrame, ym: pd.Period):
    """parquet 缓存中替换某个月的全部行（支持数据修订重拉）"""
    path = PARQUET_FILES[kind]
    if os.path.exists(path) and len(new_df) == 0:
        old = pd.read_parquet(path)
        old = old[old["month"] != str(ym)]
        old.to_parquet(path, index=False)
        return
    if not os.path.exists(path):
        new_df.to_parquet(path, index=False)
        return
    old = pd.read_parquet(path)
    old = old[old["month"] != str(ym)]
    pd.concat([old, new_df], ignore_index=True).to_parquet(path, index=False)


def seed_cache_from_excel(kind: str, df: pd.DataFrame):
    """把 Excel 数据落成 parquet 种子缓存（仅当 parquet 不存在时），并初始化元信息"""
    path = PARQUET_FILES[kind]
    if os.path.exists(path):
        return
    seed = df.copy()
    seed["month"] = seed["month"].astype(str)
    os.makedirs(CACHE_DIR, exist_ok=True)
    seed.to_parquet(path, index=False)
    meta = _read_meta()
    if not meta.get("last_month"):
        meta["last_month"] = str(seed["month"].max())
        meta["seeded_from"] = "excel"
        meta["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _write_meta(meta)


def cache_last_month() -> pd.Period | None:
    """当前缓存覆盖到的最新月份"""
    meta = _read_meta()
    if meta.get("last_month"):
        return pd.Period(meta["last_month"], freq="M")
    return None


def update_cache(progress_cb=None, force_from: pd.Period | None = None) -> dict:
    """增量拉取缺失月份，写入 parquet 缓存。返回执行摘要。遇错即停以保证月份连续。"""
    # 确保缓存存在：无 parquet 时用 Excel 播种（避免全量重拉 116 个月）
    if not (os.path.exists(PARQUET_FILES["state"]) and os.path.exists(PARQUET_FILES["port"])):
        try:
            from . import data as _data
            seed_cache_from_excel("state", _data.load_state())
            seed_cache_from_excel("port", _data.load_port())
        except Exception as e:  # noqa: BLE001 - 播种失败不阻断 API 更新
            seed_err = str(e)
        else:
            seed_err = ""
    else:
        seed_err = ""

    key = get_api_key()
    latest = probe_latest_month(key)
    if latest is None:
        return {"ok": False, "reason": "无法连接 Census API（本机网络不通，或尚未配置 API Key）",
                "fetched": [], "latest": None}

    _last = cache_last_month()
    start = force_from or (_last + 1 if _last is not None else None)
    if start is None:
        existing = None
        for kind in ("state", "port"):
            p = PARQUET_FILES[kind]
            if os.path.exists(p):
                mx = pd.read_parquet(p, columns=["month"])["month"].max()
                existing = max(existing or "", mx)
        start = pd.Period(existing, freq="M") + 1 if existing else START_MONTH

    if start > latest:
        return {"ok": True, "reason": "缓存已是最新（API 当前提供至 %s）" % latest,
                "fetched": [], "latest": latest}

    months = []
    cur = start
    while cur <= latest:
        months.append(cur)
        cur += 1

    fetched = []
    error = None
    for i, ym in enumerate(months):
        if progress_cb:
            progress_cb(i, len(months), ym)
        for kind in ("state", "port"):
            try:
                df = fetch_month(kind, ym, key)
                _replace_month(kind, df, ym)
            except CensusAPIError as e:
                error = f"{ym} {kind}: {e}"
                break
        if error:
            break
        fetched.append(str(ym))

    if fetched:
        meta = _read_meta()
        meta["last_month"] = str(pd.Period(fetched[-1], freq="M"))
        meta["latest_on_api"] = str(latest)
        meta["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _write_meta(meta)

    return {"ok": error is None, "fetched": fetched, "latest": latest,
            "errors": [error] if error else ([] if not seed_err else [seed_err]),
            "reason": error or ("更新完成，新增 %d 个月" % len(fetched) if fetched else "缓存已是最新")}
