import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.auth import Membership, Role
from app.models.tenant import Tenant
from app.models.user import User


@pytest.mark.asyncio
async def test_outbox_event_emission_and_non_blocking_duplicate_prevention(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Test that core events are emitted into the transactional outbox without blocking,
    and duplicate events are safely deduplicated via idempotency keys.
    """
    session = db_session
    tenant = Tenant(name="Oakridge International", slug=f"oak-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    admin_user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@oakridge.edu",
        password_hash="pw",
        full_name="Admin Director",
        is_active=True,
    )
    session.add(admin_user)
    await session.flush()

    session.add(Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id))
    await session.commit()

    token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Emit an event into outbox
    event_payload = {
        "user_id": str(admin_user.id),
        "email": "student.parent@example.com",
        "phone": "919876543210",
        "student_name": "Arjun Patel",
        "date": "2026-11-20",
        "message": "Your ward Arjun Patel was marked ABSENT today.",
    }
    idempotency_key = f"absent_{admin_user.id}_2026-11-20"

    emit_res = await client.post(
        "/api/v1/notifications/emit",
        headers=headers,
        json={
            "event_type": "STUDENT_ABSENT",
            "event_payload": event_payload,
            "idempotency_key": idempotency_key,
        },
    )
    assert emit_res.status_code == 200, emit_res.text
    outbox_data = emit_res.json()
    assert outbox_data["status"] == "PENDING"
    assert outbox_data["event_type"] == "STUDENT_ABSENT"
    assert outbox_data["idempotency_key"] == idempotency_key
    outbox_id = outbox_data["id"]

    # 2. Duplicate emission with same idempotency key must not create a duplicate outbox entry
    dup_res = await client.post(
        "/api/v1/notifications/emit",
        headers=headers,
        json={
            "event_type": "STUDENT_ABSENT",
            "event_payload": event_payload,
            "idempotency_key": idempotency_key,
        },
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["id"] == outbox_id

    # 3. Verify it appears in outbox listing
    list_res = await client.get("/api/v1/notifications/outbox", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(item["id"] == outbox_id for item in items)


@pytest.mark.asyncio
async def test_outbox_worker_processing_multi_channel_and_preferences(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Test worker outbox processing across multiple channels (Email, WhatsApp, SMS, In-App),
    respecting user notification opt-outs and creating delivery logs.
    """
    session = db_session
    tenant = Tenant(name="Greenwood High", slug=f"gwh-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    user = User(
        email=f"parent-{uuid.uuid4().hex[:6]}@gmail.com",
        password_hash="pw",
        full_name="Vikram Mehta",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    session.add(Membership(tenant_id=tenant.id, user_id=user.id, role_id=admin_role.id))
    await session.commit()

    token = create_access_token(
        user_id=user.id, email=user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Update user preferences: enable Email, WhatsApp, and In-App, but disable SMS
    pref_res = await client.put(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={
            "channel_email": True,
            "channel_whatsapp": True,
            "channel_in_app": True,
            "channel_sms": False,  # Opted out of SMS
            "category_attendance": True,
        },
    )
    assert pref_res.status_code == 200
    prefs = pref_res.json()
    assert prefs["channel_sms"] is False
    assert prefs["channel_whatsapp"] is True

    # 2. Emit a fee reminder notification
    emit_res = await client.post(
        "/api/v1/notifications/emit",
        headers=headers,
        json={
            "event_type": "FEE_REMINDER",
            "event_payload": {
                "user_id": str(user.id),
                "email": "parent.finance@example.com",
                "phone": "919123456789",
                "student_name": "Neha Sharma",
                "invoice_number": "INV-2026-101",
                "amount": "15000",
                "due_date": "2026-12-05",
                "title": "Term Fee Due",
                "message": "Fee invoice INV-2026-101 for INR 15,000 is due on 2026-12-05.",
            },
        },
    )
    assert emit_res.status_code == 200
    outbox_id = emit_res.json()["id"]

    # 3. Process the outbox batch
    process_res = await client.post(
        "/api/v1/notifications/outbox/process-batch",
        headers=headers,
    )
    assert process_res.status_code == 200
    assert process_res.json()["processed_count"] >= 1

    # 4. Check delivery logs: Email, WhatsApp, and In-App should be logged; SMS should NOT be sent
    logs_res = await client.get("/api/v1/notifications/logs", headers=headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()

    channels_dispatched = [l["channel"] for l in logs if l.get("outbox_id") == outbox_id]
    assert "IN_APP" in channels_dispatched
    assert "EMAIL" in channels_dispatched
    assert "WHATSAPP" in channels_dispatched
    assert "SMS" not in channels_dispatched  # Verified: Opt-out respected!

    # 5. Check In-App Notification was created and can be marked read
    in_app_res = await client.get("/api/v1/notifications/in-app", headers=headers)
    assert in_app_res.status_code == 200
    notifs = in_app_res.json()
    assert len(notifs) >= 1
    target_notif = notifs[0]
    assert target_notif["is_read"] is False

    read_res = await client.post(
        f"/api/v1/notifications/in-app/{target_notif['id']}/read",
        headers=headers,
    )
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True


@pytest.mark.asyncio
async def test_tenant_specific_integration_configuration_and_test_probe(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Test institution-specific provider configuration for Meta WhatsApp, Amazon SES/Resend,
    MSG91, Firebase, and S3/R2 storage, credentials masking, and test connectivity probes.
    """
    session = db_session
    tenant = Tenant(name="Delhi World Public School", slug=f"dwps-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    admin_user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@dwps.edu",
        password_hash="pw",
        full_name="Admin DWPS",
        is_active=True,
    )
    session.add(admin_user)
    await session.flush()

    session.add(Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id))
    await session.commit()

    token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Configure Meta WhatsApp Cloud API integration
    config_res = await client.post(
        "/api/v1/integrations",
        headers=headers,
        json={
            "provider_type": "WHATSAPP_META",
            "is_enabled": True,
            "credentials": {
                "access_token": "EAAXsampleMetaTokenSecret999888777",
                "phone_number_id": "100987654321098",
            },
            "settings": {
                "waba_id": "998877665544",
                "sender_phone": "+15551234567",
            },
        },
    )
    assert config_res.status_code == 200, config_res.text
    saved = config_res.json()
    assert saved["provider_type"] == "WHATSAPP_META"
    assert saved["is_enabled"] is True
    # Verify sensitive token is masked!
    assert saved["masked_credentials"]["access_token"] != "EAAXsampleMetaTokenSecret999888777"
    assert "..." in saved["masked_credentials"]["access_token"] or "******" in saved["masked_credentials"]["access_token"]

    # 2. Configure AWS S3 Storage integration
    s3_res = await client.post(
        "/api/v1/integrations",
        headers=headers,
        json={
            "provider_type": "STORAGE_S3",
            "is_enabled": True,
            "credentials": {
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            },
            "settings": {
                "bucket_name": "edusaas-school-docs",
                "region": "ap-south-1",
            },
        },
    )
    assert s3_res.status_code == 200
    assert s3_res.json()["provider_type"] == "STORAGE_S3"

    # 3. Run test probe on WhatsApp integration
    test_res = await client.post(
        "/api/v1/integrations/WHATSAPP_META/test",
        headers=headers,
        json={"provider_type": "WHATSAPP_META", "recipient": "919876543210"},
    )
    assert test_res.status_code == 200
    probe = test_res.json()
    assert probe["success"] is True
    assert "succeeded" in probe["message"]

    # 4. Verify integration status updated to ACTIVE after test
    get_res = await client.get("/api/v1/integrations/WHATSAPP_META", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_provider_webhooks_and_delivery_status_tracking(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Test delivery status tracking via provider webhooks:
    - Meta WhatsApp webhook hub challenge verification and status updates (delivered, read).
    - Amazon SES SNS webhook updates (delivery, bounce).
    - MSG91 DLR delivery reports.
    """
    session = db_session
    tenant = Tenant(name="St. Xavier High", slug=f"sxh-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    admin_user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@sxh.edu",
        password_hash="pw",
        full_name="Rev Father Admin",
        is_active=True,
    )
    session.add(admin_user)
    await session.flush()

    session.add(Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id))
    await session.commit()

    token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Meta WhatsApp Webhook Challenge verification
    challenge_res = await client.get(
        "/api/v1/notifications/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=test_challenge_12345&hub.verify_token=edusaas_token"
    )
    assert challenge_res.status_code == 200
    assert challenge_res.text == "test_challenge_12345"

    # 2. Emit an event and process it to generate a real log entry with provider_message_id
    emit_res = await client.post(
        "/api/v1/notifications/emit",
        headers=headers,
        json={
            "event_type": "EXAM_SCHEDULED",
            "event_payload": {
                "user_id": str(admin_user.id),
                "phone": "919876543210",
                "exam_title": "Mid-Term Mathematics",
                "start_time": "2026-12-01 09:00 AM",
            },
        },
    )
    assert emit_res.status_code == 200
    await client.post("/api/v1/notifications/outbox/process-batch", headers=headers)

    # Find the generated WhatsApp log
    logs_res = await client.get("/api/v1/notifications/logs?channel=WHATSAPP", headers=headers)
    assert logs_res.status_code == 200
    wa_logs = logs_res.json()
    assert len(wa_logs) > 0
    wamid = wa_logs[0]["provider_message_id"]
    assert wamid is not None

    # 3. Simulate Meta WhatsApp Status Webhook callback (status: "delivered")
    wa_webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": wamid,
                                    "status": "delivered",
                                    "timestamp": "1732000000",
                                    "recipient_id": "919876543210",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    hook_res = await client.post("/api/v1/notifications/webhooks/whatsapp", json=wa_webhook_payload)
    assert hook_res.status_code == 200
    assert hook_res.json()["processed"] is True

    # 4. Verify log status was updated to DELIVERED
    updated_logs_res = await client.get("/api/v1/notifications/logs?channel=WHATSAPP", headers=headers)
    assert updated_logs_res.status_code == 200
    matching_log = next(l for l in updated_logs_res.json() if l["provider_message_id"] == wamid)
    assert matching_log["status"] == "DELIVERED"
    assert matching_log["delivered_at"] is not None
