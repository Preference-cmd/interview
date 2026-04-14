from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Report


class ReportStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_report(
        self,
        store_id: int,
        report_type: str,
        content_md: str | None,
        content_json: dict | None,
    ) -> Report:
        """Create and persist a report record."""
        report = Report(
            store_id=store_id,
            report_type=report_type,
            content_md=content_md,
            content_json=content_json or {},
        )
        self._session.add(report)
        await self._session.flush()
        return report
