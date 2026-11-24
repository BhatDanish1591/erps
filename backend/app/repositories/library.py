import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import StudentProfile, TeacherProfile
from app.models.library import (
    LibraryBook,
    LibraryBookCopy,
    LibraryBorrowRecord,
    LibraryCategory,
)
from app.models.user import User


class LibraryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Categories ─────────────────────────────────────────────────────────────
    async def get_category_by_id(
        self, tenant_id: uuid.UUID, category_id: uuid.UUID
    ) -> Optional[LibraryCategory]:
        stmt = select(LibraryCategory).where(
            LibraryCategory.tenant_id == tenant_id,
            LibraryCategory.id == category_id,
            LibraryCategory.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_categories(self, tenant_id: uuid.UUID) -> List[LibraryCategory]:
        stmt = (
            select(LibraryCategory)
            .where(
                LibraryCategory.tenant_id == tenant_id,
                LibraryCategory.is_deleted == False,
            )
            .order_by(LibraryCategory.name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_category(
        self, tenant_id: uuid.UUID, name: str, code: str, description: Optional[str] = None
    ) -> LibraryCategory:
        cat = LibraryCategory(
            tenant_id=tenant_id, name=name, code=code.upper(), description=description
        )
        self.session.add(cat)
        await self.session.flush()
        return cat

    # ── Books Catalog ──────────────────────────────────────────────────────────
    async def get_book_by_id(
        self, tenant_id: uuid.UUID, book_id: uuid.UUID
    ) -> Optional[LibraryBook]:
        stmt = (
            select(LibraryBook)
            .where(
                LibraryBook.tenant_id == tenant_id,
                LibraryBook.id == book_id,
                LibraryBook.is_deleted == False,
            )
            .options(selectinload(LibraryBook.category), selectinload(LibraryBook.copies))
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_books(
        self,
        tenant_id: uuid.UUID,
        category_id: Optional[uuid.UUID] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
    ) -> List[LibraryBook]:
        stmt = (
            select(LibraryBook)
            .where(
                LibraryBook.tenant_id == tenant_id,
                LibraryBook.is_deleted == False,
            )
            .options(selectinload(LibraryBook.category))
        )
        if category_id:
            stmt = stmt.where(LibraryBook.category_id == category_id)
        if search_query:
            q = f"%{search_query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(LibraryBook.title).like(q),
                    func.lower(LibraryBook.author).like(q),
                    func.lower(LibraryBook.isbn).like(q),
                )
            )
        stmt = stmt.order_by(LibraryBook.title.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_book(
        self,
        tenant_id: uuid.UUID,
        category_id: uuid.UUID,
        title: str,
        author: str,
        isbn: Optional[str] = None,
        publisher: Optional[str] = None,
        edition: Optional[str] = None,
        publication_year: Optional[int] = None,
        total_copies: int = 1,
        shelf_location: Optional[str] = None,
        description: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        accession_numbers: Optional[List[str]] = None,
    ) -> LibraryBook:
        book = LibraryBook(
            tenant_id=tenant_id,
            category_id=category_id,
            title=title,
            author=author,
            isbn=isbn,
            publisher=publisher,
            edition=edition,
            publication_year=publication_year,
            total_copies=total_copies,
            available_copies=total_copies,
            shelf_location=shelf_location,
            description=description,
            cover_image_url=cover_image_url,
        )
        self.session.add(book)
        await self.session.flush()

        # Create physical copies
        acc_list = accession_numbers or [f"ACC-{book.id.hex[:6].upper()}-{i+1}" for i in range(total_copies)]
        for acc in acc_list:
            copy = LibraryBookCopy(
                tenant_id=tenant_id,
                book_id=book.id,
                accession_number=acc,
                status="AVAILABLE",
            )
            self.session.add(copy)
        await self.session.flush()
        return book

    # ── Copies & Circulation ───────────────────────────────────────────────────
    async def get_copy_by_id(
        self, tenant_id: uuid.UUID, copy_id: uuid.UUID
    ) -> Optional[LibraryBookCopy]:
        stmt = (
            select(LibraryBookCopy)
            .where(
                LibraryBookCopy.tenant_id == tenant_id,
                LibraryBookCopy.id == copy_id,
                LibraryBookCopy.is_deleted == False,
            )
            .options(selectinload(LibraryBookCopy.book))
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_book_copies(
        self, tenant_id: uuid.UUID, book_id: uuid.UUID
    ) -> List[LibraryBookCopy]:
        stmt = (
            select(LibraryBookCopy)
            .where(
                LibraryBookCopy.tenant_id == tenant_id,
                LibraryBookCopy.book_id == book_id,
                LibraryBookCopy.is_deleted == False,
            )
            .order_by(LibraryBookCopy.accession_number)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def issue_book_copy(
        self,
        tenant_id: uuid.UUID,
        copy_id: uuid.UUID,
        borrower_user_id: uuid.UUID,
        borrower_type: str = "STUDENT",
        student_id: Optional[uuid.UUID] = None,
        teacher_id: Optional[uuid.UUID] = None,
        due_days: int = 14,
        issued_by_user_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> LibraryBorrowRecord:
        copy = await self.get_copy_by_id(tenant_id, copy_id)
        if not copy or copy.status != "AVAILABLE":
            raise ValueError(f"Book copy is not available for issue (current status: {copy.status if copy else 'Not found'})")

        today = date.today()
        due_date = today + timedelta(days=due_days)

        borrow = LibraryBorrowRecord(
            tenant_id=tenant_id,
            copy_id=copy.id,
            book_id=copy.book_id,
            borrower_type=borrower_type,
            borrower_user_id=borrower_user_id,
            student_id=student_id,
            teacher_id=teacher_id,
            issue_date=today,
            due_date=due_date,
            status="ISSUED",
            issued_by_user_id=issued_by_user_id,
            notes=notes,
        )
        copy.status = "ISSUED"

        # Decrement available copies on the book
        book = await self.session.get(LibraryBook, copy.book_id)
        if book and book.available_copies > 0:
            book.available_copies -= 1

        self.session.add(borrow)
        await self.session.flush()
        return borrow

    async def return_book_copy(
        self,
        tenant_id: uuid.UUID,
        copy_id: uuid.UUID,
        fine_amount: Decimal = Decimal("0.00"),
        fine_paid: bool = False,
        condition_notes: Optional[str] = None,
        received_by_user_id: Optional[uuid.UUID] = None,
    ) -> LibraryBorrowRecord:
        # Find active borrow record
        stmt = (
            select(LibraryBorrowRecord)
            .where(
                LibraryBorrowRecord.tenant_id == tenant_id,
                LibraryBorrowRecord.copy_id == copy_id,
                LibraryBorrowRecord.status.in_(["ISSUED", "OVERDUE"]),
            )
            .order_by(LibraryBorrowRecord.issue_date.desc())
        )
        borrow = (await self.session.execute(stmt)).scalars().first()
        if not borrow:
            raise ValueError("No active borrow record found for this copy")

        copy = await self.session.get(LibraryBookCopy, copy_id)
        if copy:
            copy.status = "AVAILABLE"
            if condition_notes:
                copy.condition_notes = condition_notes

        book = await self.session.get(LibraryBook, borrow.book_id)
        if book:
            book.available_copies += 1

        borrow.return_date = date.today()
        borrow.status = "RETURNED"
        borrow.fine_amount = fine_amount
        borrow.fine_paid = fine_paid
        borrow.received_by_user_id = received_by_user_id

        await self.session.flush()
        return borrow

    async def get_borrow_record_by_id(
        self, tenant_id: uuid.UUID, record_id: uuid.UUID
    ) -> Optional[LibraryBorrowRecord]:
        stmt = (
            select(LibraryBorrowRecord)
            .where(
                LibraryBorrowRecord.tenant_id == tenant_id,
                LibraryBorrowRecord.id == record_id,
            )
            .options(
                selectinload(LibraryBorrowRecord.book),
                selectinload(LibraryBorrowRecord.copy),
                selectinload(LibraryBorrowRecord.borrower_user),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_borrow_records(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[LibraryBorrowRecord]:
        stmt = (
            select(LibraryBorrowRecord)
            .where(LibraryBorrowRecord.tenant_id == tenant_id)
            .options(
                selectinload(LibraryBorrowRecord.book),
                selectinload(LibraryBorrowRecord.copy),
                selectinload(LibraryBorrowRecord.borrower_user),
            )
        )
        if user_id:
            stmt = stmt.where(LibraryBorrowRecord.borrower_user_id == user_id)
        if student_id:
            stmt = stmt.where(LibraryBorrowRecord.student_id == student_id)
        if status:
            stmt = stmt.where(LibraryBorrowRecord.status == status)
        stmt = stmt.order_by(LibraryBorrowRecord.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_library_report(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        total_books_stmt = select(func.count(LibraryBook.id)).where(
            LibraryBook.tenant_id == tenant_id, LibraryBook.is_deleted == False
        )
        total_copies_stmt = select(func.count(LibraryBookCopy.id)).where(
            LibraryBookCopy.tenant_id == tenant_id, LibraryBookCopy.is_deleted == False
        )
        avail_copies_stmt = select(func.count(LibraryBookCopy.id)).where(
            LibraryBookCopy.tenant_id == tenant_id,
            LibraryBookCopy.status == "AVAILABLE",
            LibraryBookCopy.is_deleted == False,
        )
        issued_copies_stmt = select(func.count(LibraryBookCopy.id)).where(
            LibraryBookCopy.tenant_id == tenant_id,
            LibraryBookCopy.status == "ISSUED",
            LibraryBookCopy.is_deleted == False,
        )
        overdue_stmt = select(func.count(LibraryBorrowRecord.id)).where(
            LibraryBorrowRecord.tenant_id == tenant_id,
            LibraryBorrowRecord.status == "ISSUED",
            LibraryBorrowRecord.due_date < date.today(),
        )

        total_fines_stmt = select(func.coalesce(func.sum(LibraryBorrowRecord.fine_amount), Decimal("0.00"))).where(
            LibraryBorrowRecord.tenant_id == tenant_id,
            LibraryBorrowRecord.fine_paid == True,
        )
        pending_fines_stmt = select(func.coalesce(func.sum(LibraryBorrowRecord.fine_amount), Decimal("0.00"))).where(
            LibraryBorrowRecord.tenant_id == tenant_id,
            LibraryBorrowRecord.fine_paid == False,
            LibraryBorrowRecord.fine_amount > Decimal("0.00"),
        )

        return {
            "total_books": (await self.session.execute(total_books_stmt)).scalar() or 0,
            "total_copies": (await self.session.execute(total_copies_stmt)).scalar() or 0,
            "available_copies": (await self.session.execute(avail_copies_stmt)).scalar() or 0,
            "issued_copies": (await self.session.execute(issued_copies_stmt)).scalar() or 0,
            "overdue_copies": (await self.session.execute(overdue_stmt)).scalar() or 0,
            "total_fines_collected": (await self.session.execute(total_fines_stmt)).scalar() or Decimal("0.00"),
            "pending_fines": (await self.session.execute(pending_fines_stmt)).scalar() or Decimal("0.00"),
        }
