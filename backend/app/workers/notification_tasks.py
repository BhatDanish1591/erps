import asyncio
import logging
import uuid
from app.core.database import get_db_context
from app.services.notification_service import NotificationService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="notifications.process_outbox_item", bind=True, max_retries=3)
def process_outbox_item_task(self, outbox_id_str: str):
    """
    Celery worker task to process an individual outbox item asynchronously.
    """
    async def _run():
        async with get_db_context(system=True) as session:
            service = NotificationService(session)
            return await service.process_outbox_item(uuid.UUID(outbox_id_str))

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(_run())
        return {"success": success, "outbox_id": outbox_id_str}
    except Exception as exc:
        logger.error(f"Error in process_outbox_item_task: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="notifications.process_pending_outbox_batch")
def process_pending_outbox_batch_task(limit: int = 50):
    """
    Periodic beat task to process any pending or retrying outbox items.
    """
    async def _run():
        async with get_db_context(system=True) as session:
            service = NotificationService(session)
            return await service.process_pending_outbox_batch(limit=limit)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    count = loop.run_until_complete(_run())
    return {"processed_count": count}
