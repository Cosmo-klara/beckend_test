import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

MAX_LEN_MAJOR_NAME = 224  # 专业名称上限长度

def ensure_packages(packages: List[str]):
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

ensure_packages(["pandas", "PyMySQL"])

import pandas as pd
import pymysql

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASSWORD", "cosmo")
DB_NAME = os.environ.get("DB_NAME", "manager")

BASE_DIR = Path(__file__).resolve().parent
COLLEGE_CSV = BASE_DIR / "data" / "院校数据" / "全国大学数据_合并.csv"
OUTPUT_DIR = BASE_DIR / "output"

COLLEGE_REQUIRED = ["全国统一招生代码", "大学", "985", "211", "双一流", "省份", "城市"]
ADMISSION_REQUIRED = [
    "年份", "学校", "_985", "_211", "双一流", "科类", "批次",
    "专业", "最低分", "最低分排名", "全国统一招生代码", "招生类型", "生源地"
]

def sanitize_text(value, max_len: Optional[int] = None) -> Optional[str]:
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s == "":
        return None
    # 折叠多余空白与全角括号
    s = " ".join(s.split())
    s = s.translate(str.maketrans({"（": "(", "）": ")", "　": " "}))
    if max_len is not None and len(s) > max_len:
        return s[:max_len]
    return s

def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "gbk"]
    last_err = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"读取失败：{path}\n{last_err}")

def clean_code(value) -> Optional[int]:
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return int(float(s))  # 处理 10001.0 / 科学计数法
    except Exception:
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else None

def to_int_safe(value, default=None) -> Optional[int]:
    if pd.isna(value):
        return default
    s = str(value).strip()
    if s == "":
        return default
    try:
        return int(round(float(s)))
    except Exception:
        return default

# 文本处理函数区域
def smart_shorten_major_name(value, max_len: int = MAX_LEN_MAJOR_NAME) -> Optional[str]:
    """
    通用规则：
    - 字符串不超长：原样返回；
    - 超长：优先按最后一个“、”截断；
    - 若截断后存在未闭合“（”，补齐并加“等）”；
    - 若没有“、”：直接硬截断，并尽量配平括号。
    """
    s = sanitize_text(value, None)
    if s is None:
        return None
    if len(s) <= max_len:
        return s

    truncated = s[:max_len]
    # 优先在最后一个“、”处截断
    cut_pos = truncated.rfind("、")
    if cut_pos != -1:
        base = truncated[:cut_pos].rstrip("、，,；; ")
        candidate = base
        # 截断后若存在未闭合的“（”，用“等）”补齐
        if candidate.count("（") > candidate.count("）"):
            candidate += "等）"
            # 再次确保不超长
            if len(candidate) > max_len:
                candidate = candidate[:max_len]
            # 最后配平一次
            if candidate.count("（") > candidate.count("）"):
                candidate += "）"
        return candidate

    # 没有“、”时，直接硬截断
    candidate = truncated.rstrip()
    # 配平括号
    if candidate.count("（") > candidate.count("）"):
        candidate += "）"
        if len(candidate) > max_len:
            candidate = candidate[:max_len]
    return candidate


def import_college_info(conn) -> Tuple[int, set]:
    df = read_csv_with_fallback(COLLEGE_CSV)
    df.columns = [str(c).strip() for c in df.columns]
    miss = [c for c in COLLEGE_REQUIRED if c not in df.columns]
    if miss:
        raise ValueError(f"院校CSV缺列：{miss}")

    df = df[COLLEGE_REQUIRED].copy()
    df["全国统一招生代码"] = df["全国统一招生代码"].map(clean_code)

    # 清洗与类型转换
    df["985"] = pd.to_numeric(df["985"], errors="coerce").fillna(0).astype(int)
    df["211"] = pd.to_numeric(df["211"], errors="coerce").fillna(0).astype(int)
    df["双一流"] = pd.to_numeric(df["双一流"], errors="coerce").fillna(0).astype(int)
    df["省份"] = df["省份"].astype(str).str.strip()
    df["城市"] = df["城市"].astype(str).str.strip()

    # 丢弃无有效编码的行
    df = df.dropna(subset=["全国统一招生代码"]).copy()

    sql = """
    INSERT INTO college_info
        (COLLEGE_CODE, COLLEGE_NAME, IS_985, IS_211, IS_DFC, PROVINCE, CITY_NAME, BASE_INTRO)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        COLLEGE_NAME=VALUES(COLLEGE_NAME),
        IS_985=VALUES(IS_985),
        IS_211=VALUES(IS_211),
        IS_DFC=VALUES(IS_DFC),
        PROVINCE=VALUES(PROVINCE),
        CITY_NAME=VALUES(CITY_NAME)
    """
    rows = []
    for _, r in df.iterrows():
        code = int(r["全国统一招生代码"])
        name = str(r["大学"]).strip()
        is_985 = int(r["985"])
        is_211 = int(r["211"])
        is_dfc = int(r["双一流"])
        province = str(r["省份"]).strip()
        city = str(r["城市"]).strip()
        rows.append((code, name, is_985, is_211, is_dfc, province, city, None))

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    print(f"[college_info] 导入/更新 {len(rows)} 行")
    valid_codes = set(df["全国统一招生代码"].astype(int).tolist())
    return len(rows), valid_codes

def import_admission_scores(conn, valid_codes: Optional[set] = None):
    # 遍历 data 下除“院校数据”外的子目录，导入所有 *.csv
    total = 0
    for child in OUTPUT_DIR.iterdir():
        if not child.is_dir():
            continue
        for csv in child.glob("*.csv"):
            try:
                df = read_csv_with_fallback(csv)
                df.columns = [str(c).strip() for c in df.columns]
                miss = [c for c in ADMISSION_REQUIRED if c not in df.columns]
                if miss:
                    print(f"[跳过] {csv.name} 缺列：{miss}")
                    continue

                df = df[ADMISSION_REQUIRED].copy()
                # 清洗&映射
                df["全国统一招生代码"] = df["全国统一招生代码"].map(clean_code)
                df = df.dropna(subset=["全国统一招生代码"]).copy()
                df["全国统一招生代码"] = df["全国统一招生代码"].astype(int)

                if valid_codes is not None:
                    df = df[df["全国统一招生代码"].isin(valid_codes)].copy()
                    if df.empty:
                        print(f"[{csv.name}] 无匹配院校编码，跳过")
                        continue

                df["ADMISSION_YEAR"] = df["年份"].apply(lambda v: to_int_safe(v))
                df["MIN_SCORE"] = df["最低分"].apply(lambda v: to_int_safe(v))
                df["MIN_RANK"] = df["最低分排名"].apply(lambda v: to_int_safe(v))
                df["TYPE"] = df["科类"].astype(str).str.strip()
                df["MAJOR_NAME"] = df["专业"].astype(str).str.strip()

                original_major = df["专业"].apply(lambda v: sanitize_text(v, None))
                # 超长统一截断：优先“、”，否则直接截断；必要时补“等）”
                df["MAJOR_NAME"] = original_major.apply(lambda v: smart_shorten_major_name(v, MAX_LEN_MAJOR_NAME)).fillna("未知")

                orig_len = original_major.fillna("").astype(str).str.len()
                final_len = df["MAJOR_NAME"].fillna("").astype(str).str.len()
                replaced = int((orig_len > final_len).sum())
                if replaced > 0:
                    print(f"[{csv.name}] 专业名称超长截断处理 {replaced} 条")

                df["PROVINCE"] = df["生源地"].astype(str).str.strip()  # 作为录取省份



                df = df.dropna(subset=["ADMISSION_YEAR", "MIN_SCORE"]).copy()

                # 基于关键维度去重，避免重复导入
                dedup_cols = ["全国统一招生代码", "PROVINCE", "ADMISSION_YEAR", "MAJOR_NAME", "MIN_SCORE", "MIN_RANK"]
                before = len(df)
                df = df.drop_duplicates(subset=dedup_cols).copy()
                dup_removed = before - len(df)

                sql = """
                INSERT INTO college_admission_score
                    (COLLEGE_CODE, TYPE, MAJOR_NAME, PROVINCE, ADMISSION_YEAR, MIN_SCORE, MIN_RANK)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
                """
                rows = []
                for _, r in df.iterrows():
                    rows.append((
                        int(r["全国统一招生代码"]),
                        r["TYPE"],
                        r["MAJOR_NAME"],
                        r["PROVINCE"],
                        int(r["ADMISSION_YEAR"]),
                        int(r["MIN_SCORE"]),
                        int(r["MIN_RANK"]),
                    ))

                with conn.cursor() as cur:
                    cur.executemany(sql, rows)
                conn.commit()
                total += len(rows)

                print(f"[{csv.name}] 导入 {len(rows)} 行（去重移除 {dup_removed} 行）")
            except Exception as e:
                print(f"[错误] 处理 {csv} 失败：{e}")

    print(f"[college_admission_score] 总导入 {total} 行")

def main():
    print(f"连接数据库 {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME} ...")
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        charset="utf8mb4", autocommit=False
    )
    try:
        import_admission_scores(conn, None)
        print("全部导入完成（仅导入历年录取分数线）")
    finally:
        conn.close()

if __name__ == "__main__":
    main()


