#!/usr/bin/env python3
"""
Seed the database with mock data from mock_data/stores.json.
Calls the /stores/import API endpoint on a running backend.
Usage: python seed.py [--base-url http://localhost:8000]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_stores(mock_data_dir: Path) -> list[dict]:
    stores_file = mock_data_dir / "stores.json"
    if not stores_file.exists():
        print(f"ERROR: {stores_file} not found", file=sys.stderr)
        sys.exit(1)

    with open(stores_file, encoding="utf-8") as f:
        raw = json.load(f)

    # Normalize to StoreImportItem schema
    items = []
    for s in raw:
        items.append(
            {
                "store_id": s["store_id"],
                "name": s["name"],
                "city": s["city"],
                "category": s["category"],
                "rating": s["rating"],
                "monthly_orders": s["monthly_orders"],
                "gmv_last_7d": s["gmv_last_7d"],
                "review_count": s["review_count"],
                "review_reply_rate": s["review_reply_rate"],
                "ros_health": s["ros_health"],
                "competitor_avg_discount": s["competitor_avg_discount"],
                "issues": s.get("issues", []),
            }
        )
    return items


def seed(base_url: str, mock_data_dir: Path) -> None:
    stores = load_stores(mock_data_dir)
    url = f"{base_url}/stores/import"

    payload = json.dumps({"stores": stores}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(
            f"ERROR: Cannot connect to backend at {base_url}. "
            "Is the server running? (make backend-dev) Error: " + str(e.reason)
        )
        sys.exit(1)

    count = len(data) if isinstance(data, list) else 1
    print(f"Seeded {count} store(s) from mock_data/stores.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database with mock store data")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--mock-data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "mock_data",
        help="Path to mock_data directory",
    )
    args = parser.parse_args()

    seed(args.base_url, args.mock_data_dir)


if __name__ == "__main__":
    main()
