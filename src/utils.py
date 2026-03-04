import os
import re
import pandas as pd

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def to_int(series):
    return pd.to_numeric(series.astype(str).str.replace(",", "").str.strip(), errors="coerce").astype("Int64")

def to_float(series):
    return pd.to_numeric(series.astype(str).str.replace(",", "").str.strip(), errors="coerce")

def normalize_team(team):
    if team is None:
        return ""
    return re.sub(r"\s+", " ", str(team)).strip()

def clean_standings(df):
    out = df.copy()
    out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
    if "team" in out.columns:
        out["team"] = out["team"].map(normalize_team)
    for col in ["w","l","t"]:
        if col in out.columns:
            out[col] = to_int(out[col])
    if "wp" in out.columns:
        out["wp"] = to_float(out["wp"])
    if "gb" in out.columns:
        out["gb"] = out["gb"].astype(str).str.replace("-", "0", regex=False)
        out["gb"] = to_float(out["gb"])
    return out

def clean_leaders(df):
    out = df.copy()
    out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
    if "#" in out.columns:
        out = out.rename(columns={"#":"value"})
    if "team" in out.columns:
        out["team"] = out["team"].map(normalize_team)
    if "value" in out.columns:
        out["value_num"] = to_float(out["value"])
    return out

def safe_filename(s):
    return re.sub(r"[^a-zA-Z0-9_\-]+","_",s).strip("_")