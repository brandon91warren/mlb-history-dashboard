import time
import re
from io import StringIO
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from utils import ensure_dir

LEAGUES = {"AL": "a", "NL": "n"}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

def build_year_url(year, league):
    return f"https://www.baseball-almanac.com/yearly/yr{year}{LEAGUES[league]}.shtml"

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument(f"--user-agent={USER_AGENT}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

def preprocess_html(html):
    html = re.sub(r"<!--\s*", "", html)
    html = re.sub(r"\s*-->", "", html)
    return html

def extract_tables(html):
    cleaned = preprocess_html(html)
    try:
        return pd.read_html(StringIO(cleaned))
    except ValueError:
        return []

def norm_cols(df):
    return [str(c).strip().lower() for c in df.columns]

def is_leaders_table(df):
    cols = set(norm_cols(df))
    return {"statistic", "name", "team"}.issubset(cols)

def is_standings_table(df):
    cols = set(norm_cols(df))
    if "team" not in cols:
        return False
    return ("w" in cols and "l" in cols) or ("wins" in cols and "losses" in cols) or ("w-l" in cols)

def scrape_one_year(driver, year, league):
    url = build_year_url(year, league)
    driver.get(url)
    time.sleep(3)

    html = driver.page_source
    tables = extract_tables(html)

    leaders = [t for t in tables if is_leaders_table(t)]
    standings = next((t for t in tables if is_standings_table(t)), None)

    soup = BeautifulSoup(html, "lxml")
    h2s = [h.get_text(" ", strip=True) for h in soup.select("h2")]
    paragraphs = [p.get_text(" ", strip=True) for p in soup.select("p")]
    year_sections = pd.DataFrame(
        {"year": [year], "league": [league], "h2_count": [len(h2s)], "p_count": [len(paragraphs)]}
    )

    out = {"year_sections": year_sections}

    if len(leaders) >= 1:
        out["leaders_hitting"] = leaders[0]
    if len(leaders) >= 2:
        out["leaders_pitching"] = leaders[1]
    if standings is not None:
        out["standings"] = standings

    return out, len(tables), len(leaders), standings is not None, url, driver.title

def main():
    ensure_dir("data_raw")
    years = list(range(2020, 2025))
    leagues = ["AL", "NL"]

    driver = setup_driver()
    visited = set()

    try:
        for year in years:
            for league in leagues:
                url = build_year_url(year, league)
                if url in visited:
                    continue
                visited.add(url)

                data, total_tables, leader_count, has_standings, page_url, title = scrape_one_year(driver, year, league)

                saved = []
                for key, df in data.items():
                    filename = f"{key}_{year}_{league}.csv"
                    df.to_csv(f"data_raw/{filename}", index=False)
                    saved.append(filename)

                print(
                    f"{year} {league}: tables_found={total_tables} "
                    f"leaders_found={leader_count} standings_found={has_standings}"
                )
                print(f"{year} {league}: saved={saved}")
                if leader_count < 2 or not has_standings:
                    ensure_dir("data_raw/debug")
                    with open(f"data_raw/debug/page_{year}_{league}.html", "w", encoding="utf-8") as f:
                        f.write(preprocess_html(driver.page_source))
                    print(f"{year} {league}: warning -> missing expected tables. debug saved. title={title} url={page_url}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()