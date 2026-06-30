"""Seed a few Sarnia fixtures into Cognee so the demo data is reproducible.

Run it against the backend's environment (the stack must be up and OPENAI_API_KEY set):

  docker compose up -d db neo4j
  cd backend && uv run python ../scripts/demo_seed.py

Prints what was seeded.
"""

import asyncio
import os
import sys

# Make the backend package importable regardless of the current directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def main() -> None:
    from src.memory.store import get_memory_store

    store = get_memory_store()
    realtor = {"name": "Riley", "email": "riley@example.com"}
    listings = [
        {
            "code": "S1",
            "address": "123 Maple Street, Sarnia",
            "price": 450000,
            "beds": 3,
            "baths": 2,
            "sqft": 1500,
            "description": "Charming 3 bed bungalow near the park",
            "area": "Sarnia",
        },
        {
            "code": "S2",
            "address": "88 Lakeshore Road, Sarnia",
            "price": 625000,
            "beds": 4,
            "baths": 3,
            "sqft": 2400,
            "description": "Waterfront family home with a large yard",
            "area": "Sarnia",
        },
        {
            "code": "S3",
            "address": "12 Front Street, Sarnia",
            "price": 320000,
            "beds": 2,
            "baths": 1,
            "sqft": 1050,
            "description": "Updated downtown condo, walk to everything",
            "area": "Sarnia",
        },
    ]
    await store.add_listings(realtor, listings)
    await store.upsert_buyer(
        {
            "phone": "+1-519-555-0100",
            "name": "Dana",
            "criteria": {"area": "Sarnia", "minBeds": 3, "maxPrice": 500000},
        }
    )
    print(
        f"Seeded {len(listings)} Sarnia listings and 1 buyer "
        f"for realtor {realtor['name']}."
    )


if __name__ == "__main__":
    asyncio.run(main())
