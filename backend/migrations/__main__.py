"""Run migrations standalone: python -m migrations"""

import asyncio

from backend.database import async_engine
from backend.migrations import MigrationRunner


async def main() -> None:
    runner = MigrationRunner(async_engine)
    applied = await runner.run_pending()
    if applied:
        print(f"Migrations applied: {applied}")  # noqa: T201
    else:
        print("No pending migrations")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
