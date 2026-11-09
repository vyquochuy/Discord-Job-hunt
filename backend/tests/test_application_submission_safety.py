import inspect
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.resume import ApplicationChannelEnum, ApplicationStatusEnum
from app.schemas.resume import ApplicationSubmitRequest
from app.services.tailoring.application_service import application_service


def test_submission_defaults_to_simulation():
    assert ApplicationSubmitRequest().simulate_only is True
    assert inspect.signature(application_service.submit_application).parameters['simulate_only'].default is True


@pytest.mark.asyncio
@pytest.mark.parametrize('channel', list(ApplicationChannelEnum))
async def test_actual_submission_rejected_without_writing(channel):
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await application_service.submit_application(session, uuid.uuid4(), channel=channel, simulate_only=False)
    assert exc.value.status_code == 501
    assert 'transport' in exc.value.detail.lower()
    session.add.assert_not_called()
    session.execute.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_manual_external_sent_tracking_remains_available(monkeypatch):
    record = SimpleNamespace(status=ApplicationStatusEnum.READY, sent_at=None)
    monkeypatch.setattr(type(application_service), 'get_application_by_id', AsyncMock(return_value=record))
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    updated = await application_service.update_application_status(session, uuid.uuid4(), ApplicationStatusEnum.SENT)
    assert updated.status == ApplicationStatusEnum.SENT
    assert updated.sent_at is not None
    session.commit.assert_awaited_once()
