# Air Quality (NBRO Sri Lanka)

Fetches live air quality station data from the NBRO endpoint and stores a
normalized JSON snapshot in the repository. A GitHub Action runs on a schedule
to keep the data updated.

## Data source

- Endpoint: https://aq.nbro.gov.lk/invoker.php

## Output

- File: `air_quality/data/latest.json`
- Format: JSON with an array of stations plus metadata
- Extra fields added by the fetcher:
  - `timestamp_iso_utc`
  - `sl_aqi_label`
  - `sl_aqi_est`
  - `sl_aqi_range`
  - `pm25_band_range`

## Local setup

Requirements:
- Python 3.11+ recommended

Install dependencies:
```bash
python -m pip install -r requirements.txt
```

Run the fetcher:
```bash
python scripts/fetch_nbro_aq.py
```

## GitHub Actions

The scheduled workflow is in `/.github/workflows/fetch_nbro_aq.yml` and runs
every 10 minutes by default. It:
- installs Python and dependencies
- runs the fetcher
- commits `air_quality/data/latest.json` if it changed

To change the schedule, edit the `cron` expression in the workflow.

## Project layout

- `scripts/fetch_nbro_aq.py`: fetches and enriches station data
- `air_quality/data/latest.json`: latest snapshot (generated)
- `requirements.txt`: Python dependencies

## Notes

- The fetcher sorts stations by name and device ID to reduce noisy commits.
