"""One-off: verify Cognee memory is isolated per tenant.

Adds a distinctive listing for two tenants, then recalls each and asserts neither tenant's
recall surfaces the other's listing. Requires the local stack (Neo4j + pgvector) + OpenAI.

    uv run python scripts/verify_tenant_isolation.py
"""

import asyncio
import uuid

from dotenv import load_dotenv

load_dotenv(override=False)

from src.memory.store import get_memory_store  # noqa: E402

TAG = uuid.uuid4().hex[:6]
A = f"org_alpha_{TAG}"
B = f"org_beta_{TAG}"
A_STREET = f"Zephyrwood Crescent {TAG}"
B_STREET = f"Quibblestone Lane {TAG}"


async def main() -> None:
    store = get_memory_store()

    await store.add_listings(
        A,
        {"name": "Alpha Realty"},
        [
            {
                "code": f"A-{TAG}",
                "address": A_STREET,
                "beds": 3,
                "price": 450000,
                "area": "Sarnia",
                "description": "3 bed bungalow",
            }
        ],
    )
    await store.add_listings(
        B,
        {"name": "Beta Realty"},
        [
            {
                "code": f"B-{TAG}",
                "address": B_STREET,
                "beds": 3,
                "price": 460000,
                "area": "Sarnia",
                "description": "3 bed bungalow",
            }
        ],
    )

    crit = {"area": "Sarnia", "minBeds": 3}
    a_text = " ".join(str(r) for r in await store.recall(A, crit, top_k=5))
    b_text = " ".join(str(r) for r in await store.recall(B, crit, top_k=5))

    print("\n--- tenant A recall ---\n", a_text[:600])
    print("\n--- tenant B recall ---\n", b_text[:600])

    # The recall is an LLM answer, so match on the distinctive street word and agent name
    # rather than the exact address string (the model reformats the random tag).
    a_ok = (
        "Zephyrwood" in a_text
        and "Alpha Realty" in a_text
        and "Quibblestone" not in a_text
        and "Beta Realty" not in a_text
    )
    b_ok = (
        "Quibblestone" in b_text
        and "Beta Realty" in b_text
        and "Zephyrwood" not in b_text
        and "Alpha Realty" not in b_text
    )

    print("\n=== RESULT ===")
    print(f"A sees own, not B's : {a_ok}")
    print(f"B sees own, not A's : {b_ok}")
    print("ISOLATION:", "PASS" if (a_ok and b_ok) else "FAIL")


if __name__ == "__main__":
    asyncio.run(main())
