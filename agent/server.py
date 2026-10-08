import sqlite3
from contextlib import closing
from datetime import date, timedelta
import httpx
from mcp.server.fastmcp import FastMCP

DB = "weather.db"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

mcp = FastMCP("weather-data", host="127.0.0.1", port=8000)


def query(sql, params=()):
    with closing(sqlite3.connect(DB)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, params)]


def _city(name):
    rows = query("SELECT * FROM cities WHERE LOWER(name) = LOWER(?)", (name,))
    if not rows:
        raise ValueError(f"Unknown city '{name}'. Call list_cities to see available cities.")
    return rows[0]


def _clamp_days(days):
    return max(1, min(int(days), 60))


@mcp.tool()
def list_cities() -> list[dict]:
    """List every city available in the local weather database."""
    return query("SELECT name, country, latitude, longitude FROM cities ORDER BY name")


@mcp.tool()
def get_city_history(city: str, days: int = 14) -> list[dict]:
    """Return day-by-day max/min temperature and precipitation for a city over the last N days (1-60)."""
    row = _city(city)
    days = _clamp_days(days)
    start = (date.today() - timedelta(days=days + 6)).isoformat()
    return query(
        """SELECT day, temp_max, temp_min, precipitation_mm
           FROM daily_weather
           WHERE city_id = ? AND day >= ?
           ORDER BY day DESC""",
        (row["id"], start),
    )


@mcp.tool()
def get_city_summary(city: str, days: int = 30) -> dict:
    """Summarize a city's weather over the last N days (1-60): average highs/lows, total rainfall, and rainy-day count."""
    row = _city(city)
    days = _clamp_days(days)
    start = (date.today() - timedelta(days=days + 6)).isoformat()
    stats = query(
        """SELECT COUNT(*) AS days_counted,
                  ROUND(AVG(temp_max), 1) AS avg_high_c,
                  ROUND(AVG(temp_min), 1) AS avg_low_c,
                  ROUND(SUM(precipitation_mm), 1) AS total_rain_mm,
                  SUM(CASE WHEN precipitation_mm > 1 THEN 1 ELSE 0 END) AS rainy_days
           FROM daily_weather
           WHERE city_id = ? AND day >= ?""",
        (row["id"], start),
    )[0]
    return {"city": row["name"], "country": row["country"], "window_days": days, **stats}


@mcp.tool()
def get_live_weather(city: str) -> dict:
    """Fetch the current live weather for a city from the Open-Meteo API."""
    row = _city(city)
    r = httpx.get(
        FORECAST_URL,
        params={
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "timezone": "auto",
        },
        timeout=15,
    )
    r.raise_for_status()
    current = r.json()["current"]
    return {"city": row["name"], "time": current["time"], "temperature_c": current["temperature_2m"],
            "humidity_pct": current["relative_humidity_2m"], "wind_kmh": current["wind_speed_10m"],
            "precipitation_mm": current["precipitation"]}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")