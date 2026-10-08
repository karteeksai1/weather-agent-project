import sqlite3
from datetime import date, timedelta
import httpx

DB = "weather.db"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
CITIES = [
    ("Hyderabad", "IN", 17.385, 78.4867),
    ("Bengaluru", "IN", 12.9716, 77.5946),
    ("Mumbai", "IN", 19.076, 72.8777),
    ("London", "GB", 51.5072, -0.1276),
    ("Tokyo", "JP", 35.6762, 139.6503),
    ("New York", "US", 40.7128, -74.006),
]
DAYS = 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    UNIQUE(name, country)
);
CREATE TABLE IF NOT EXISTS daily_weather (
    city_id INTEGER NOT NULL REFERENCES cities(id),
    day TEXT NOT NULL,
    temp_max REAL,
    temp_min REAL,
    precipitation_mm REAL,
    PRIMARY KEY (city_id, day)
);
"""


def fetch_daily(lat, lon, start, end):
    r = httpx.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["daily"]


def main():
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    end = date.today() - timedelta(days=6)
    start = end - timedelta(days=DAYS)

    for name, country, lat, lon in CITIES:
        conn.execute(
            "INSERT OR IGNORE INTO cities (name, country, latitude, longitude) VALUES (?, ?, ?, ?)",
            (name, country, lat, lon),
        )
        city_id = conn.execute(
            "SELECT id FROM cities WHERE name = ? AND country = ?", (name, country)
        ).fetchone()[0]

        daily = fetch_daily(lat, lon, start, end)
        rows = zip(
            daily["time"],
            daily["temperature_2m_max"],
            daily["temperature_2m_min"],
            daily["precipitation_sum"],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO daily_weather VALUES (?, ?, ?, ?, ?)",
            [(city_id, d, mx, mn, p) for d, mx, mn, p in rows],
        )
        print(f"Loaded {len(daily['time'])} days for {name}")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()