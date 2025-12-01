import os
import sys
import pandas as pd

# 以当前脚本所在目录为基准的相对路径
SCRIPT_DIR = os.path.dirname(__file__)
BASE_PATH = os.path.join(SCRIPT_DIR, "全国大学数据_筛选.csv")
CODES_PATH = os.path.join(SCRIPT_DIR, "本科院校.csv")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "全国大学数据_合并.csv")

BASE_REQUIRED_COLS = ["省份", "大学", "本或专科", "985", "211", "双一流", "城市"]
CODES_REQUIRED_COLS = ["学校", "全国统一招生代码"]
FINAL_COLUMNS = ["全国统一招生代码", "大学", "985", "211", "双一流", "省份", "城市"]

def read_csv_with_fallback(path):
    encodings = ["utf-8-sig", "utf-8", "gbk"]
    last_err = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_err = e
    print(f"读取失败：{path}\n{last_err}")
    sys.exit(1)

def normalize_name(value):
    if pd.isna(value):
        return ""
    v = str(value).strip()
    trans = str.maketrans({"（": "(", "）": ")", "　": " "})
    v = v.translate(trans)
    v = " ".join(v.split())  # 折叠多余空白
    return v

def clean_code(value):
    if pd.isna(value):
        return None
    v = str(value).strip()
    if v == "":
        return None
    try:
        # 统一为整数：处理类似 10001.0、1.000e4 等格式
        return str(int(float(v)))
    except Exception:
        # 回退：提取纯数字
        digits = "".join(ch for ch in v if ch.isdigit())
        return digits if digits else None

def main():
    # 读取底稿与代码表
    base = read_csv_with_fallback(BASE_PATH)
    codes = read_csv_with_fallback(CODES_PATH)

    # 校验列
    miss_base = [c for c in BASE_REQUIRED_COLS if c not in base.columns]
    if miss_base:
        print(f"底稿缺少必要列：{miss_base}")
        sys.exit(1)
    miss_codes = [c for c in CODES_REQUIRED_COLS if c not in codes.columns]
    if miss_codes:
        print(f"代码表缺少必要列：{miss_codes}")
        sys.exit(1)

    # 轻量规范化名称，用作连接键
    base["__join_key"] = base["大学"].apply(normalize_name)
    codes["__join_key"] = codes["学校"].apply(normalize_name)

    # 代码表按 join_key 去重（保留首个）
    codes_unique = codes.drop_duplicates(subset=["__join_key"]).copy()
    # 清洗招生代码为整数的字符串；不可用则置为 None
    codes_unique["全国统一招生代码"] = codes_unique["全国统一招生代码"].map(clean_code)

    # 左连接
    merged = pd.merge(
        base,
        codes_unique[["__join_key", "全国统一招生代码"]],
        on="__join_key",
        how="left",
        validate="many_to_one"  # 保证底稿：多，对代码表：一
    )

    # 类型标准化
    for col in ["985", "211", "双一流"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int)
    # 删除无招生代码的行，并确保为字符串
    merged = merged[merged["全国统一招生代码"].notna()]
    merged["全国统一招生代码"] = merged["全国统一招生代码"].astype(str)
    # 清理列与重排
    if "本或专科" in merged.columns:
        merged = merged.drop(columns=["本或专科"])
    merged = merged[FINAL_COLUMNS]

    # 输出
    out_dir = os.path.dirname(OUTPUT_PATH)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    merged.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    # 简报
    total = len(merged)
    print(f"合并完成：{OUTPUT_PATH}")
    print(f"总行数：{total}")

if __name__ == "__main__":
    main()