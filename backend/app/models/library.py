import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class LibraryCategory(BaseModel, SoftDeleteMixin):
    """
    Book classification category (e.g. Science, Literature, Engineering).
    """
    __tablename__ = "library_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    books: Mapped[List["LibraryBook"]] = relationship("LibraryBook", back_populates="category")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_library_categories_tenant_code"),
        Index("ix_library_categories_tenant_code", "tenant_id", "code"),
    )


class LibraryBook(BaseModel, SoftDeleteMixin):
    """
    Catalog master entity representing a distinct book title, author, edition, and metadata.
    """
    __tablename__ = "library_books"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    isbn: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    edition: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    available_copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    shelf_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    category: Mapped["LibraryCategory"] = relationship("LibraryCategory", back_populates="books")
    copies: Mapped[List["LibraryBookCopy"]] = relationship(
        "LibraryBookCopy", back_populates="book", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_library_books_tenant_title", "tenant_id", "title"),
        Index("ix_library_books_tenant_author", "tenant_id", "author"),
        Index("ix_library_books_tenant_isbn", "tenant_id", "isbn"),
    )


class LibraryBookCopy(BaseModel, SoftDeleteMixin):
    """
    Physical individual copy of a book with its own unique barcode / accession number.
    """
    __tablename__ = "library_book_copies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    accession_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="AVAILABLE", nullable=False, index=True
    )  # AVAILABLE, ISSUED, LOST, DAMAGED, RESERVED
    condition_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    book: Mapped["LibraryBook"] = relationship("LibraryBook", back_populates="copies")
    borrow_records: Mapped[List["LibraryBorrowRecord"]] = relationship(
        "LibraryBorrowRecord", back_populates="copy"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "accession_number", name="uq_library_copies_tenant_acc"),
        Index("ix_library_copies_tenant_book", "tenant_id", "book_id"),
        Index("ix_library_copies_tenant_status", "tenant_id", "status"),
    )


class LibraryBorrowRecord(BaseModel, SoftDeleteMixin):
    """
    Circulation tracking: issuing, due dates, returns, and late fine calculation.
    """
    __tablename__ = "library_borrow_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    copy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_book_copies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("library_books.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    borrower_type: Mapped[str] = mapped_column(
        String(20), default="STUDENT", nullable=False
    )  # STUDENT, TEACHER, STAFF
    borrower_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="ISSUED", nullable=False, index=True
    )  # ISSUED, RETURNED, OVERDUE, LOST
    fine_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    fine_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    issued_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    received_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    copy: Mapped["LibraryBookCopy"] = relationship("LibraryBookCopy", back_populates="borrow_records")
    book: Mapped["LibraryBook"] = relationship("LibraryBook")
    borrower_user: Mapped["User"] = relationship("User", foreign_keys=[borrower_user_id])
    student: Mapped[Optional["StudentProfile"]] = relationship("StudentProfile")

    __table_args__ = (
        Index("ix_library_borrows_tenant_user", "tenant_id", "borrower_user_id"),
        Index("ix_library_borrows_tenant_status", "tenant_id", "status"),
        Index("ix_library_borrows_tenant_student", "tenant_id", "student_id"),
    )
