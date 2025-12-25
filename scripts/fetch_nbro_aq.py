#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

ENDPOINT = "https://aq.nbro.gov.lk/invoker.php"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_FILE = os.path.join(REPO_ROOT, "air_quality", "data", "latest.json")


# SL AQI bands as shown on NBRO AQ site (PM2.5 µg/m3 to AQI bands)
# Good: 0–25 => 0–50
# Moderate: 25.1–50 => 51–100
# Unhealthy for sensitive group: 50.1–75 => 101–150
# Unhealthy: 75.1–150 => 151–200
# Very Unhealthy: 150.1–250 => 201–300
# Hazardous: >250.1 => 301–500
# Source: aq.nbro.gov.lk page table
BREAKPOINTS = [
    # (pm25_low, pm25_high, aqi_low, aqi_high, label)
    (0.0, 25.0, 0, 50, "Good"),
    (25.1, 50.0, 51, 100, "Moderate"),
    (50.1, 75.0, 101, 150, "Unhealthy for Sensitive Groups"),
    (75.1, 150.0, 151, 200, "Unhealthy"),
    (150.1, 250.0, 201, 300, "Very Unhealthy"),
    (250.1, float("inf"), 301, 500, "Hazardous"),
]


def iso_from_ms(ts_ms: Optional[float]) -> Optional[str]:
    if ts_ms is None:
        return None
    try:
        dt = datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def classify_pm25(pm25: Optional[float]) -> Dict[str, Any]:
    if pm25 is None:
        return {"sl_aqi_label": "Unknown", "sl_aqi_est": None}

    pm = float(pm25)

    for pm_lo, pm_hi, aqi_lo, aqi_hi, label in BREAKPOINTS:
        if pm_lo <= pm <= pm_hi:
            # Linear interpolation to estimate AQI within the band
            if pm_hi == pm_lo:
                est = aqi_hi
            else:
                est = aqi_lo + (pm - pm_lo) * (aqi_hi - aqi_lo) / (pm_hi - pm_lo)
            return {
                "sl_aqi_label": label,
                "sl_aqi_est": int(round(est)),
                "sl_aqi_range": [aqi_lo, aqi_hi],
                "pm25_range": [pm_lo, pm_hi if pm_hi != float("inf") else None],
            }

    return {"sl_aqi_label": "Unknown", "sl_aqi_est": None}


def main() -> None:
    r = requests.get(
        ENDPOINT,
        headers={"User-Agent": "air_quality_bot/1.0 (+https://github.com/enigmazero-net/air_quality)"},
        timeout=30,
    )
    r.raise_for_status()

    data: List[Dict[str, Any]] = r.json()

    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    enriched: List[Dict[str, Any]] = []
    for item in data:
        pm25 = item.get("pm25", None)
        info = classify_pm25(pm25)

        enriched_item = dict(item)
        enriched_item["timestamp_iso_utc"] = iso_from_ms(item.get("timestamp"))
        enriched_item["sl_aqi_label"] = info.get("sl_aqi_label")
        enriched_item["sl_aqi_est"] = info.get("sl_aqi_est")
        enriched_item["sl_aqi_range"] = info.get("sl_aqi_range")
        enriched_item["pm25_band_range"] = info.get("pm25_range")
        enriched.append(enriched_item)

    # Stable ordering to reduce noisy commits
    enriched.sort(key=lambda x: (str(x.get("name", "")), str(x.get("meta_device_id", ""))))

    output = {
        "source": ENDPOINT,
        "fetched_at_utc": fetched_at,
        "count": len(enriched),
        "stations": enriched,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {OUT_FILE} ({len(enriched)} stations) at {fetched_at}")


if __name__ == "__main__":
    main()
