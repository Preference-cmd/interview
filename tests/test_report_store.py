import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models import Report


def _make_session():
    sess = MagicMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    return sess


@pytest.mark.asyncio
class TestCreateReport:
    async def test_creates_report_with_all_fields(self):
        from backend.stores.report import ReportStore

        sess = _make_session()
        store = ReportStore(sess)

        await store.create_report(
            store_id=1,
            report_type="weekly",
            content_md="# Weekly Report\n...",
            content_json={"metrics": {"gmv": 5000}},
        )

        sess.add.assert_called_once()
        sess.flush.assert_called_once()
        added = sess.add.call_args[0][0]
        assert isinstance(added, Report)
        assert added.store_id == 1
        assert added.report_type == "weekly"
        assert added.content_md == "# Weekly Report\n..."
        assert added.content_json == {"metrics": {"gmv": 5000}}

    async def test_defaults_content_json_to_empty_dict(self):
        from backend.stores.report import ReportStore

        sess = _make_session()
        store = ReportStore(sess)

        await store.create_report(
            store_id=2,
            report_type="daily",
            content_md="# Daily",
            content_json=None,
        )

        added = sess.add.call_args[0][0]
        assert added.content_json == {}
