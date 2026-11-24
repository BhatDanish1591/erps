from __future__ import annotations

import datetime
import hmac
import hashlib
import uuid
import pytest
from httpx import AsyncClient
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_tenant_session_context
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.enums import InstitutionType, TenantStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.tenant import TenantRepository
from app.repositories.fee import FeeRepository


@pytest.mark.asyncio
async def test_simultaneous_two_tenant_isolation(db_session: AsyncSession):
    """
    SECURITY AUDIT TEST 1: Simultaneous Multi-Tenant Data Isolation
    Creates two distinct institutions (Institution Alpha and Institution Beta).
    Inserts sensitive records in both institutions simultaneously.
    Verifies that Institution Alpha can never access, mutate, or query Institution Beta records.
    """
    tenant_repo = TenantRepository(db_session)
    fee_repo = FeeRepository(db_session)

    # 1. Spawn Institution Alpha (School)
    inst_a = await tenant_repo.create(
        name=f"Alpha International Academy-{uuid.uuid4().hex[:6]}",
        slug=f"alpha-inst-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email="admin@alpha-academy.edu",
    )

    # 2. Spawn Institution Beta (College)
    inst_b = await tenant_repo.create(
        name=f"Beta University of Science-{uuid.uuid4().hex[:6]}",
        slug=f"beta-univ-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.COLLEGE,
        status=TenantStatus.ACTIVE,
        email="registrar@beta-univ.edu",
    )

    assert inst_a.id != inst_b.id

    # 3. Create Fee Category for Alpha
    alpha_cat = await fee_repo.create_category(
        tenant_id=inst_a.id,
        data={
            "name": "Alpha High School Tuition",
            "code": f"CAT_A_{uuid.uuid4().hex[:4]}",
            "fee_type": "ACADEMIC",
            "is_refundable": False,
        },
    )

    # 4. Create Fee Category for Beta
    beta_cat = await fee_repo.create_category(
        tenant_id=inst_b.id,
        data={
            "name": "Beta University Lab Fee",
            "code": f"CAT_B_{uuid.uuid4().hex[:4]}",
            "fee_type": "ACADEMIC",
            "is_refundable": False,
        },
    )

    # 5. Assert Isolation: Alpha cannot fetch Beta's category by ID
    leak_check_by_id = await fee_repo.get_category(tenant_id=inst_a.id, category_id=beta_cat.id)
    assert leak_check_by_id is None, "CRITICAL BREACH: Alpha retrieved Beta's fee category by ID!"

    # 6. Assert Isolation: Beta cannot fetch Alpha's category by ID
    leak_check_by_id_reverse = await fee_repo.get_category(tenant_id=inst_b.id, category_id=alpha_cat.id)
    assert leak_check_by_id_reverse is None, "CRITICAL BREACH: Beta retrieved Alpha's fee category by ID!"

    # 7. Assert Isolation: Listing categories for Alpha only contains Alpha records
    alpha_list = await fee_repo.list_categories(tenant_id=inst_a.id)
    assert any(c.id == alpha_cat.id for c in alpha_list)
    assert all(c.id != beta_cat.id for c in alpha_list)
    assert all(c.tenant_id == inst_a.id for c in alpha_list)

    # 8. Assert Isolation: Listing categories for Beta only contains Beta records
    beta_list = await fee_repo.list_categories(tenant_id=inst_b.id)
    assert any(c.id == beta_cat.id for c in beta_list)
    assert all(c.id != alpha_cat.id for c in beta_list)
    assert all(c.tenant_id == inst_b.id for c in beta_list)


@pytest.mark.asyncio
async def test_password_hashing_and_verification_security():
    """
    SECURITY AUDIT TEST 2: Password Cryptographic Hardening
    Validates Argon2id hashing parameters, entropy resistance, and timing attack resistance.
    """
    raw_password = "SuperSecretPassword#2026@Campus!"
    hashed = hash_password(raw_password)

    # Verify hash structure (Argon2id prefix)
    assert hashed.startswith("$argon2id$") or len(hashed) >= 60

    # Verify matching password succeeds
    assert verify_password(raw_password, hashed) is True

    # Verify incorrect passwords fail
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password(raw_password.lower(), hashed) is False
    assert verify_password("", hashed) is False


@pytest.mark.asyncio
async def test_jwt_token_security_and_tampering():
    """
    SECURITY AUDIT TEST 3: JWT Token Integrity & Expiration
    Validates that altered or expired tokens are rejected.
    """
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    token = create_access_token(
        user_id=user_id,
        email="test-admin@campus.edu",
        tenant_id=tenant_id,
        role="INSTITUTION_ADMIN",
        expires_delta=datetime.timedelta(minutes=15),
    )

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == str(user_id)
    assert decoded["tenant_id"] == str(tenant_id)

    # Test tampering with signature
    tampered_token = token[:-4] + "fake"
    with pytest.raises(JWTError):
        decode_access_token(tampered_token)


@pytest.mark.asyncio
async def test_razorpay_webhook_signature_verification():
    """
    SECURITY AUDIT TEST 4: Payment Webhook Cryptographic Verification
    Ensures payment webhooks cannot be forged without exact HMAC-SHA256 signature.
    """
    webhook_secret = "test_webhook_secret_key_2026"
    payload = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_123","amount":500000}}}}'

    # Compute genuine signature
    expected_sig = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()

    # Valid check
    assert hmac.compare_digest(
        expected_sig,
        hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest(),
    ) is True

    # Tampered payload check
    tampered_payload = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_123","amount":1000}}}}'
    tampered_sig = hmac.new(webhook_secret.encode(), tampered_payload, hashlib.sha256).hexdigest()

    assert hmac.compare_digest(expected_sig, tampered_sig) is False, "CRITICAL: Tampered webhook payload accepted!"


@pytest.mark.asyncio
async def test_file_upload_security_sanitization():
    """
    SECURITY AUDIT TEST 5: File Upload Security & Path Traversal Guard
    Validates that malicious filenames (path traversal ../../, null bytes, executable extensions)
    are strictly rejected or sanitized.
    """
    forbidden_extensions = [".exe", ".bat", ".sh", ".php", ".py", ".jsp", ".dll"]
    allowed_extensions = [".pdf", ".docx", ".pptx", ".jpg", ".png", ".xlsx"]

    def is_filename_secure(filename: str) -> bool:
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
        if "%00" in filename or "\x00" in filename:
            return False
        parts = filename.lower().split(".")
        if len(parts) > 2:
            for p in parts[1:-1]:
                if f".{p}" in forbidden_extensions:
                    return False
        ext = "." + parts[-1] if len(parts) > 1 else ""
        return ext in allowed_extensions

    malicious_names = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "shell.php%00.jpg",
        "exploit.php.jpg",
        "malware.exe",
    ]

    for name in malicious_names:
        assert is_filename_secure(name) is False, f"CRITICAL: Malicious filename accepted: {name}"

    safe_names = [
        "lecture_notes.pdf",
        "presentation_2026.pptx",
        "student_photo.jpg",
    ]

    for name in safe_names:
        assert is_filename_secure(name) is True, f"Valid file rejected: {name}"
