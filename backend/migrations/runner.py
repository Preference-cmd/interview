from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class MigrationRunner:
    """
    Lightweight SQL migration runner.
    Reads SQL files from migrations/sql/, applies pending ones,
    and records them in the schema_migrations table.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def run_pending(self) -> list[str]:
        """Run all pending migrations. Returns list of newly applied versions."""
        applied = await self._get_applied_all()
        newly_applied: list[str] = []

        migrations_dir = Path(__file__).parent / "sql"
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            version = _extract_version(sql_file.name)
            if version not in applied:
                async with self._session_factory() as conn:
                    await self._apply(conn, sql_file, version)
                    newly_applied.append(version)
        return newly_applied

    @property
    def _session_factory(self) -> async_sessionmaker:
        return async_sessionmaker(self.engine, expire_on_commit=False)

    async def _get_applied_all(self) -> set[str]:
        async with self._session_factory() as conn:
            return await self._get_applied(conn)

    async def _get_applied(self, conn: AsyncSession) -> set[str]:
        try:
            result = await conn.execute(text("SELECT version FROM schema_migrations"))
            rows = result.fetchall()
            return {row[0] for row in rows}
        except Exception:
            # Table doesn't exist yet — no migrations applied
            return set()

    async def _apply(self, conn: AsyncSession, sql_file: Path, version: str) -> None:
        sql_content = sql_file.read_text()
        for statement in sql_content.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))
        await conn.execute(
            text("INSERT OR IGNORE INTO schema_migrations (version) VALUES (:version)"),
            {"version": version},
        )
        await conn.commit()


def _extract_version(filename: str) -> str:
    """Extract version from '0001_initial_schema.sql' -> '0001_initial_schema'."""
    return filename.replace(".sql", "")
