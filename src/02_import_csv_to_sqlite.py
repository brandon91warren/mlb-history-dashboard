import glob
import os
import sqlite3
import pandas as pd
from utils import ensure_dir, safe_filename

DB_PATH = "db/mlb_history.sqlite3"

def infer_table_name(csv_path):
    base = os.path.basename(csv_path).replace(".csv", "")
    return safe_filename(base).lower()

def main():
    ensure_dir("db")

    csv_files = glob.glob("data_raw/**/*.csv", recursive=True)

    conn = sqlite3.connect(DB_PATH)

    try:
        for csv_path in csv_files:
            table = infer_table_name(csv_path)

            df = pd.read_csv(csv_path)

            df.to_sql(table, conn, if_exists="replace", index=False)

            print(f"Imported {csv_path} -> {table}")

        conn.commit()

    finally:
        conn.close()

if __name__ == "__main__":
    main()