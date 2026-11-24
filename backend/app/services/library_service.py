import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.library import (
    LibraryBook,
    LibraryBookCopy,
    LibraryBorrowRecord,
    LibraryCategory,
)
from app.repositories.library import LibraryRepository
from app.schemas.advanced_modules import (
    BookIssueRequest,
    BookReturnRequest,
    LibraryBookCreate,
    LibraryCategoryCreate,
)


class LibraryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LibraryRepository(session)

    async def create_category(
        self, tenant_id: uuid.UUID, data: LibraryCategoryCreate
    ) -> LibraryCategory:
        cat = await self.repo.create_category(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            description=data.description,
        )
        await self.session.commit()
        return cat

    async def list_categories(self, tenant_id: uuid.UUID) -> List[LibraryCategory]:
        return await self.repo.list_categories(tenant_id)

    async def create_book(
        self, tenant_id: uuid.UUID, data: LibraryBookCreate
    ) -> LibraryBook:
        category = await self.repo.get_category_by_id(tenant_id, data.category_id)
        if not category:
            raise NotFoundException(message=f"Category {data.category_id} not found")

        book = await self.repo.create_book(
            tenant_id=tenant_id,
            category_id=data.category_id,
            title=data.title,
            author=data.author,
            isbn=data.isbn,
            publisher=data.publisher,
            edition=data.edition,
            publication_year=data.publication_year,
            total_copies=data.total_copies,
            shelf_location=data.shelf_location,
            description=data.description,
            cover_image_url=data.cover_image_url,
            accession_numbers=data.accession_numbers,
        )
        await self.session.commit()
        return await self.repo.get_book_by_id(tenant_id, book.id)

    async def list_books(
        self,
        tenant_id: uuid.UUID,
        category_id: Optional[uuid.UUID] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
    ) -> List[LibraryBook]:
        return await self.repo.list_books(
            tenant_id=tenant_id,
            category_id=category_id,
            search_query=search_query,
            limit=limit,
        )

    async def get_book(
        self, tenant_id: uuid.UUID, book_id: uuid.UUID
    ) -> LibraryBook:
        book = await self.repo.get_book_by_id(tenant_id, book_id)
        if not book:
            raise NotFoundException(message=f"Book {book_id} not found")
        return book

    async def list_book_copies(
        self, tenant_id: uuid.UUID, book_id: uuid.UUID
    ) -> List[LibraryBookCopy]:
        return await self.repo.list_book_copies(tenant_id, book_id)

    async def issue_book(
        self,
        tenant_id: uuid.UUID,
        data: BookIssueRequest,
        issued_by_user_id: Optional[uuid.UUID] = None,
    ) -> LibraryBorrowRecord:
        try:
            record = await self.repo.issue_book_copy(
                tenant_id=tenant_id,
                copy_id=data.copy_id,
                borrower_user_id=data.borrower_user_id,
                borrower_type=data.borrower_type,
                student_id=data.student_id,
                teacher_id=data.teacher_id,
                due_days=data.due_days,
                issued_by_user_id=issued_by_user_id,
                notes=data.notes,
            )
            await self.session.commit()
            return await self.repo.get_borrow_record_by_id(tenant_id, record.id)
        except ValueError as ex:
            raise ValidationException(message=str(ex))

    async def return_book(
        self,
        tenant_id: uuid.UUID,
        data: BookReturnRequest,
        received_by_user_id: Optional[uuid.UUID] = None,
    ) -> LibraryBorrowRecord:
        try:
            record = await self.repo.return_book_copy(
                tenant_id=tenant_id,
                copy_id=data.copy_id,
                fine_amount=data.fine_amount,
                fine_paid=data.fine_paid,
                condition_notes=data.condition_notes,
                received_by_user_id=received_by_user_id,
            )
            await self.session.commit()
            return await self.repo.get_borrow_record_by_id(tenant_id, record.id)
        except ValueError as ex:
            raise ValidationException(message=str(ex))

    async def list_borrow_history(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[LibraryBorrowRecord]:
        return await self.repo.list_borrow_records(
            tenant_id=tenant_id,
            user_id=user_id,
            student_id=student_id,
            status=status,
            limit=limit,
        )

    async def get_library_reports(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        return await self.repo.get_library_report(tenant_id)
