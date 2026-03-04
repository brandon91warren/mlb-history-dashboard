# MLB History Dashboard

This project scrapes historical Major League Baseball data from Baseball Almanac, stores the data in a SQLite database, and presents insights using an interactive Streamlit dashboard.

## Features

- Web scraping using Selenium
- Data cleaning and transformation using Pandas
- SQLite database storage
- Command line querying
- Interactive Streamlit dashboard with filters and visualizations

## Project Structure

src/
- 01_scrape_mlb_history.py — Scrapes MLB historical data
- 02_import_csv_to_sqlite.py — Imports CSV data into SQLite
- 03_query_cli.py — Command line query tool
- 04_dashboard_streamlit.py — Interactive dashboard

data_raw/
- Raw scraped data

db/
- SQLite database

## Setup Instructions

Create a virtual environment:

```
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```
pip install -r requirements.txt
```

Run the scraper:

```
python src/01_scrape_mlb_history.py
```

Import the data:

```
python src/02_import_csv_to_sqlite.py
```

Query the database:

```
python src/03_query_cli.py --year 2020 --league AL --stat "Home Runs"
```

Run the dashboard:

```
streamlit run src/04_dashboard_streamlit.py
```

## Dashboard Screenshot

![Dashboard](screenshot.png)

## Insights

- Users can explore MLB hitting and pitching leaders by year and league.
- The dashboard dynamically updates charts based on selected statistics.
- A joined insight shows the hitting leader and ERA leader for a selected year and league.
