from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

DATASET_ID = "OpenDataMoroccanLaw/morocco-cassation-court-decisions"


def summarize_dataset(size_payload: dict[str, Any], stats_payload: dict[str, Any]) -> dict[str, Any]:
    dataset_size = size_payload["size"]["dataset"]
    columns = {
        item["column_name"]: item["column_statistics"]
        for item in stats_payload["statistics"]
    }
    return {
        "dataset": DATASET_ID,
        "rows": dataset_size["num_rows"],
        "parquet_bytes": dataset_size["num_bytes_parquet_files"],
        "columns": len(stats_payload["statistics"]),
        "date_min": columns["date"]["min"],
        "date_max": columns["date"]["max"],
        "chambers": columns["chamber"]["frequencies"],
        "missing_bench": columns["bench"]["nan_count"],
        "missing_decision_number": columns["decision_number"]["nan_count"],
        "missing_docket_number": columns["docket_number"]["nan_count"],
        "missing_date": columns["date"]["nan_count"],
        "text_length_min": columns["text"]["min"],
        "text_length_max": columns["text"]["max"],
    }


def fetch_dataset_audit(session: requests.Session | None = None) -> dict[str, Any]:
    client = session or requests.Session()
    encoded = quote(DATASET_ID, safe="")
    size_response = client.get(
        f"https://datasets-server.huggingface.co/size?dataset={encoded}", timeout=(10, 45)
    )
    size_response.raise_for_status()
    stats_response = client.get(
        "https://datasets-server.huggingface.co/statistics"
        f"?dataset={encoded}&config=default&split=train",
        timeout=(10, 45),
    )
    stats_response.raise_for_status()
    return summarize_dataset(size_response.json(), stats_response.json())
