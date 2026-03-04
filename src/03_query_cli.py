import argparse
import sqlite3
import pandas as pd

DB_PATH = "db/mlb_history.sqlite3"

def union_all_view(conn, like_pattern, view_name):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (like_pattern,))
    tables = [r[0] for r in cur.fetchall()]
    if not tables:
        raise SystemExit(f"No tables matched pattern '{like_pattern}'.")

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--league", choices=["AL", "NL"])
    ap.add_argument("--stat", type=str, default="Home Runs")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    try:
        union_all_view(conn, "raw_table_0_%", "v_hit")
        union_all_view(conn, "raw_table_1_%", "v_mid")
        union_all_view(conn, "raw_table_2_%", "v_last")

        sql = """
        SELECT year, league, stat, name, team, value FROM v_mid
        UNION ALL
        SELECT year, league, stat, name, team, value FROM v_last
        """
        all_pitch = pd.read_sql_query(sql, conn)
        all_pitch = all_pitch[all_pitch["stat"].str.lower() != "statistic"]
        all_pitch = all_pitch[all_pitch["stat"].notna()]
        all_pitch = all_pitch[all_pitch["stat"].astype(str).str.len() > 0]

        conn.execute("DROP TABLE IF EXISTS tmp_pitch")
        all_pitch.to_sql("tmp_pitch", conn, if_exists="replace", index=False)

        filters = []
        params = []

        if args.year:
            filters.append("a.year = ?")
            params.append(str(args.year))
        if args.league:
            filters.append("a.league = ?")
            params.append(args.league)

        filters.append("lower(a.stat) = lower(?)")
        params.append(args.stat)

        where = "WHERE " + " AND ".join(filters)

        query = f"""
        SELECT
          a.year, a.league,
          a.stat AS hitting_stat,
          a.name AS hitting_leader,
          a.team AS hitting_team,
          a.value AS hitting_value,
          p.name AS era_leader,
          p.team AS era_team,
          p.value AS era_value
        FROM v_hit a
        LEFT JOIN tmp_pitch p
          ON p.year = a.year
         AND p.league = a.league
         AND lower(p.stat) = 'era'
        {where}
        ORDER BY CAST(a.year AS INT) DESC
        LIMIT ?
        """

        df = pd.read_sql_query(query, conn, params=params + [args.limit])
        df = df[df["hitting_stat"].str.lower() != "statistic"]

        print(df.to_string(index=False))

    finally:
        conn.close()

if __name__ == "__main__":
    main()