from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import (
    get_active_tenant_id,
    get_current_user,
    get_current_user_claims,
    require_any_role,
)
from app.schemas.advanced_modules import (
    BookIssueRequest,
    BookReturnRequest,
    LibraryBookCopyResponse,
    LibraryBookCreate,
    LibraryBookResponse,
    LibraryBorrowRecordResponse,
    LibraryCategoryCreate,
    LibraryCategoryResponse,
    LibraryReportResponse,
)
from app.services.entitlement_service import require_feature
from app.services.library_service import LibraryService

router = APIRouter(
    prefix="/library",
    tags=["Library Management"],
    dependencies=[Depends(require_feature("LIBRARY_MANAGEMENT"))],
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Categories
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[LibraryCategoryResponse])
async def list_categories(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    return await service.list_categories(tenant_id)


@router.post(
    "/categories",
    response_model=LibraryCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: LibraryCategoryCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    return await service.create_category(tenant_id, payload)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Books & Inventory
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/books", response_model=List[LibraryBookResponse])
async def list_books(
    category_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    books = await service.list_books(
        tenant_id=tenant_id,
        category_id=category_id,
        search_query=search,
        limit=limit,
    )
    result = []
    for b in books:
        res = LibraryBookResponse.model_validate(b)
        if "category" in b.__dict__ and b.category:
            res.category_name = b.category.name
        result.append(res)
    return result


@router.post(
    "/books",
    response_model=LibraryBookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_book(
    payload: LibraryBookCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    book = await service.create_book(tenant_id, payload)
    res = LibraryBookResponse.model_validate(book)
    if "category" in book.__dict__ and book.category:
        res.category_name = book.category.name
    return res


@router.get("/books/{book_id}", response_model=LibraryBookResponse)
async def get_book(
    book_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    book = await service.get_book(tenant_id, book_id)
    res = LibraryBookResponse.model_validate(book)
    if "category" in book.__dict__ and book.category:
        res.category_name = book.category.name
    return res


@router.get("/books/{book_id}/copies", response_model=List[LibraryBookCopyResponse])
async def list_book_copies(
    book_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    return await service.list_book_copies(tenant_id, book_id)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Book Issue & Return
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/issue",
    response_model=LibraryBorrowRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_book(
    payload: BookIssueRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    record = await service.issue_book(
        tenant_id=tenant_id,
        data=payload,
        issued_by_user_id=current_user.id,
    )
    res = LibraryBorrowRecordResponse.model_validate(record)
    if "book" in record.__dict__ and record.book:
        res.book_title = record.book.title
    if "copy" in record.__dict__ and record.copy:
        res.accession_number = record.copy.accession_number
    if "borrower_user" in record.__dict__ and record.borrower_user:
        res.borrower_name = record.borrower_user.full_name
    return res


@router.post("/return", response_model=LibraryBorrowRecordResponse)
async def return_book(
    payload: BookReturnRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    record = await service.return_book(
        tenant_id=tenant_id,
        data=payload,
        received_by_user_id=current_user.id,
    )
    res = LibraryBorrowRecordResponse.model_validate(record)
    if "book" in record.__dict__ and record.book:
        res.book_title = record.book.title
    if "copy" in record.__dict__ and record.copy:
        res.accession_number = record.copy.accession_number
    if "borrower_user" in record.__dict__ and record.borrower_user:
        res.borrower_name = record.borrower_user.full_name
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 4. Borrow History & Tracking
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/borrows", response_model=List[LibraryBorrowRecordResponse])
async def list_borrow_history(
    user_id: Optional[uuid.UUID] = Query(None),
    student_id: Optional[uuid.UUID] = Query(None),
    borrow_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)

    # Restrict students to their own records
    target_user_id = user_id
    if claims.get("role") == "STUDENT":
        target_user_id = current_user.id

    records = await service.list_borrow_history(
        tenant_id=tenant_id,
        user_id=target_user_id,
        student_id=student_id,
        status=borrow_status,
        limit=limit,
    )
    result = []
    for r in records:
        res = LibraryBorrowRecordResponse.model_validate(r)
        if "book" in r.__dict__ and r.book:
            res.book_title = r.book.title
        if "copy" in r.__dict__ and r.copy:
            res.accession_number = r.copy.accession_number
        if "borrower_user" in r.__dict__ and r.borrower_user:
            res.borrower_name = r.borrower_user.full_name
        result.append(res)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 5. Reports
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/reports/summary", response_model=LibraryReportResponse)
async def get_library_reports(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = LibraryService(session)
    report_data = await service.get_library_reports(tenant_id)
    return LibraryReportResponse(**report_data)
