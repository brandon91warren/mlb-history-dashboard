import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

DB_PATH = "db/mlb_history.sqlite3"

def union_all_view_raw(conn, like_pattern, view_name):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (like_pattern,))
    tables = [r[0] for r in cur.fetchall()]

    if not tables:
        cur.execute(f"DROP VIEW IF EXISTS {view_name}")
        cur.execute(
            f"CREATE TEMP VIEW {view_name} AS "
            "SELECT NULL AS year, NULL AS league, NULL AS stat, NULL AS name, NULL AS team, NULL AS value, NULL AS extra WHERE 0;"
        )
        conn.commit()
        return

    parts = []
    for t in tables:
        pieces = t.split("_")
        year = pieces[3]
        league = pieces[4].upper()
        parts.append(
            f"""
            SELECT
              '{year}' AS year,
              '{league}' AS league,
              "0" AS stat,
              "1" AS name,
              "2" AS team,
              "3" AS value,
              "4" AS extra
            FROM {t}
            """
        )

    cur.execute(f"DROP VIEW IF EXISTS {view_name}")
    cur.execute(f"CREATE TEMP VIEW {view_name} AS " + " UNION ALL ".join(parts))
    conn.commit()

def clean_leader_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in ["stat", "name", "team", "value"]:
        out[c] = out[c].astype(str).str.strip()

    out = out[out["stat"].str.lower() != "statistic"]
    out = out[~out["stat"].str.contains(r"\bhistory\b|\byear-by-year\b|\bteam standings\b|\bworld series\b|\ball-star\b", case=False, regex=True)]
    out["value_num"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["value_num"])
    out["year"] = out["year"].astype(int)
    return out

@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        union_all_view_raw(conn, "raw_table_0_%", "v_hit_raw")
        union_all_view_raw(conn, "raw_table_1_%", "v_mid_raw")
        union_all_view_raw(conn, "raw_table_2_%", "v_last_raw")

        hit_raw = pd.read_sql_query("SELECT * FROM v_hit_raw", conn)
        mid_raw = pd.read_sql_query("SELECT * FROM v_mid_raw", conn)
        last_raw = pd.read_sql_query("SELECT * FROM v_last_raw", conn)

        hit = clean_leader_frame(hit_raw)
        pitch = clean_leader_frame(pd.concat([mid_raw, last_raw], ignore_index=True))

        return hit, pitch
    finally:
        conn.close()

def main():
    st.set_page_config(page_title="MLB History Dashboard", layout="wide")
    st.title("MLB History Dashboard")

    hit, pitch = load_data()

    years = sorted(hit["year"].unique().tolist())
    leagues = sorted(hit["league"].unique().tolist())

    c1, c2 = st.columns(2)
    with c1:
        year = st.selectbox("Year", years, index=len(years) - 1 if years else 0)
    with c2:
        league = st.selectbox("League", leagues, index=0)

    hit_yl = hit[(hit["year"] == year) & (hit["league"] == league)]
    pitch_yl = pitch[(pitch["year"] == year) & (pitch["league"] == league)]

    hit_stats = sorted(hit_yl["stat"].unique().tolist())
    pitch_stats = sorted(pitch_yl["stat"].unique().tolist())

    c3, c4 = st.columns(2)
    with c3:
        hit_stat = st.selectbox("Hitting Stat", hit_stats, index=0 if hit_stats else 0)
    with c4:
        pitch_stat = st.selectbox("Pitching Stat", pitch_stats, index=0 if pitch_stats else 0)

    st.subheader("Hitting Leaders")
    hit_plot = hit_yl[hit_yl["stat"].str.lower() == str(hit_stat).lower()].copy()
    hit_plot = hit_plot.sort_values("value_num", ascending=False).head(15)
    fig1 = px.bar(hit_plot, x="name", y="value_num", hover_data=["team", "value"], title=f"{year} {league} — {hit_stat} (Top 15)")
    fig1.update_layout(xaxis_title="Player", yaxis_title="Value")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Pitching Leaders")
    pitch_plot = pitch_yl[pitch_yl["stat"].str.lower() == str(pitch_stat).lower()].copy()
    ascending = str(pitch_stat).strip().lower() in {"era", "whip"}
    pitch_plot = pitch_plot.sort_values("value_num", ascending=ascending).head(15)
    fig2 = px.bar(pitch_plot, x="name", y="value_num", hover_data=["team", "value"], title=f"{year} {league} — {pitch_stat} (Top 15)")
    fig2.update_layout(xaxis_title="Player", yaxis_title="Value")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Joined Insight: Selected Hitting Stat + ERA Leader")
    era = pitch_yl[pitch_yl["stat"].str.lower() == "era"].copy()
    era = era.sort_values("value_num", ascending=True).head(1)

    best_hit = hit_plot.head(1)[["year", "league", "stat", "name", "team", "value"]].copy()
    best_hit.columns = ["year", "league", "hitting_stat", "hitting_leader", "hitting_team", "hitting_value"]

    if not era.empty:
        best_era = era[["name", "team", "value"]].copy()
        best_era.columns = ["era_leader", "era_team", "era_value"]
        joined = pd.concat([best_hit.reset_index(drop=True), best_era.reset_index(drop=True)], axis=1)
    else:
        best_hit["era_leader"] = None
        best_hit["era_team"] = None
        best_hit["era_value"] = None
        joined = best_hit

    st.dataframe(joined, use_container_width=True)

if __name__ == "__main__":
    main()