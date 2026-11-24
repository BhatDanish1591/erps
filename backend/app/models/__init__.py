from __future__ import annotations

from app.models.base import Base, BaseModel, SoftDeleteMixin, TenantBaseModel, TenantMixin, TimestampMixin
from app.models.enums import (
    BillingCycle,
    DiscountType,
    InstitutionType,
    InvoiceStatus,
    LoginStatus,
    MembershipStatus,
    PaymentStatus,
    RoleScope,
    SessionStatus,
    SubscriptionStatus,
    TenantStatus,
)
from app.models.tenant import Tenant, TenantDomain, TenantSetting
from app.models.user import LoginHistory, RefreshToken, User
from app.models.auth import Membership, Permission, Role, RolePermission
from app.models.invitation import Invitation
from app.models.academic import (
    AcademicDegree,
    AcademicFaculty,
    AcademicHierarchy,
    AcademicSession,
    AcademicSubjectMapping,
    CollegeBatch,
    CollegeEnrollmentDetail,
    CollegeSemester,
    Course,
    Department,
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentDocument,
    StudentEnrollmentHistory,
    StudentParent,
    StudentProfile,
    StudentPromotion,
    Subject,
    TeacherAssignment,
    TeacherAttendance,
    TeacherDocument,
    TeacherLeave,
    TeacherProfile,
    TeacherSubjectMapping,
    TimetableEntry,
)
from app.models.subscription import (
    Coupon,
    PlanFeature,
    Subscription,
    SubscriptionInvoice,
    SubscriptionPayment,
    SubscriptionPlan,
    WebhookEvent,
)
from app.models.audit import AuditLog
from app.models.super_admin import (
    GlobalAnnouncement,
    PlatformIntegration,
    PlatformSetting,
    SupportTicket,
    SupportTicketReply,
)
from app.models.attendance import (
    AttendanceCorrectionLog,
    AttendanceDeviceLog,
    StudentAttendanceEntry,
    StudentAttendanceSession,
)
from app.models.examination import (
    ExamAuditLog,
    Examination,
    ExaminationQuestion,
    QuestionBank,
    StudentExamAnswer,
    StudentExamAttempt,
)
from app.models.result import (
    GradingScale,
    ReEvaluationRequest,
    ReportCardTemplate,
    ResultRevisionHistory,
    StudentSubjectResult,
    StudentTermResult,
)
from app.models.lms import (
    Assignment,
    AssignmentSubmission,
    StudyMaterial,
    StudyMaterialVersion,
)
from app.models.timetable import (
    SubstituteTeacherAssignment,
    TimetableHoliday,
    TimetablePeriod,
    TimetableSchedule,
    TimetableSetting,
)
from app.models.fee import (
    FeeCategory,
    FeeDiscountScholarship,
    FeeInvoice,
    FeePayment,
    FeePaymentWebhookEvent,
    FeeStructure,
    FeeStructureComponent,
    FeeStructureInstallment,
    StudentFeeAllocation,
)
from app.models.parent import ParentTeacherMessage, StudentLinkVerificationCode
from app.models.notification import (
    NotificationLog,
    NotificationOutbox,
    NotificationTemplate,
    TenantIntegration,
    UserNotification,
    UserNotificationPreference,
)
from app.models.library import (
    LibraryBook,
    LibraryBookCopy,
    LibraryBorrowRecord,
    LibraryCategory,
)
from app.models.transport import (
    StudentTransportAllocation,
    TransportDriver,
    TransportGpsLog,
    TransportMaintenanceLog,
    TransportRoute,
    TransportStop,
    TransportVehicle,
)
from app.models.hostel import (
    HostelAttendance,
    HostelBuilding,
    HostelMaintenanceRequest,
    HostelRoom,
    HostelRoomAllocation,
    HostelVisitor,
)
from app.models.report import ScheduledReport

__all__ = [
    # Base
    "Base",
    "BaseModel",
    "TenantBaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "TenantMixin",
    # Enums
    "InstitutionType",
    "TenantStatus",
    "RoleScope",
    "MembershipStatus",
    "SessionStatus",
    "BillingCycle",
    "SubscriptionStatus",
    "InvoiceStatus",
    "PaymentStatus",
    "LoginStatus",
    # Tenant
    "Tenant",
    "TenantDomain",
    "TenantSetting",
    # User
    "User",
    "RefreshToken",
    "LoginHistory",
    # Auth & RBAC
    "Permission",
    "Role",
    "RolePermission",
    "Membership",
    # Academic & Hierarchy
    "AcademicSession",
    "AcademicFaculty",
    "AcademicDegree",
    "SchoolClass",
    "Section",
    "Department",
    "Course",
    "CollegeSemester",
    "CollegeBatch",
    "Subject",
    "AcademicSubjectMapping",
    "TeacherSubjectMapping",
    "StudentProfile",
    "StudentAcademicEnrollment",
    "SchoolEnrollmentDetail",
    "CollegeEnrollmentDetail",
    "StudentPromotion",
    "AcademicHierarchy",
    "StudentDocument",
    "StudentEnrollmentHistory",
    "StudentParent",
    "TeacherProfile",
    "TeacherAssignment",
    "TimetableEntry",
    "TeacherAttendance",
    "TeacherLeave",
    "TeacherDocument",
    "Invitation",
    # Subscription & Billing
    "BillingCycle",
    "DiscountType",
    "SubscriptionStatus",
    "InvoiceStatus",
    "PaymentStatus",
    "SubscriptionPlan",
    "PlanFeature",
    "Coupon",
    "Subscription",
    "SubscriptionInvoice",
    "SubscriptionPayment",
    "WebhookEvent",
    # Audit
    "AuditLog",
    # Super Admin
    "GlobalAnnouncement",
    "SupportTicket",
    "SupportTicketReply",
    "PlatformSetting",
    "PlatformIntegration",
    # Attendance
    "StudentAttendanceSession",
    "StudentAttendanceEntry",
    "AttendanceCorrectionLog",
    "AttendanceDeviceLog",
    # Examination
    "QuestionBank",
    "Examination",
    "ExaminationQuestion",
    "StudentExamAttempt",
    "StudentExamAnswer",
    "ExamAuditLog",
    # Results & Report Cards
    "GradingScale",
    "StudentSubjectResult",
    "StudentTermResult",
    "ResultRevisionHistory",
    "ReEvaluationRequest",
    "ReportCardTemplate",
    # LMS & Study Material
    "StudyMaterial",
    "StudyMaterialVersion",
    "Assignment",
    "AssignmentSubmission",
    # Timetable
    "TimetableSetting",
    "TimetablePeriod",
    "TimetableHoliday",
    "TimetableSchedule",
    "SubstituteTeacherAssignment",
    # Fees & Finance
    "FeeCategory",
    "FeeStructure",
    "FeeStructureComponent",
    "FeeStructureInstallment",
    "FeeDiscountScholarship",
    "StudentFeeAllocation",
    "FeeInvoice",
    "FeePayment",
    "FeePaymentWebhookEvent",
    # Parent & Guardian Portal
    "StudentLinkVerificationCode",
    "ParentTeacherMessage",
    # Notification & Integration System
    "TenantIntegration",
    "NotificationTemplate",
    "UserNotificationPreference",
    "NotificationOutbox",
    "NotificationLog",
    "UserNotification",
    # Library Management
    "LibraryCategory",
    "LibraryBook",
    "LibraryBookCopy",
    "LibraryBorrowRecord",
    # Transport Management
    "TransportVehicle",
    "TransportDriver",
    "TransportRoute",
    "TransportStop",
    "StudentTransportAllocation",
    "TransportMaintenanceLog",
    "TransportGpsLog",
    # Hostel Management
    "HostelBuilding",
    "HostelRoom",
    "HostelRoomAllocation",
    "HostelAttendance",
    "HostelVisitor",
    "HostelMaintenanceRequest",
    # Analytics & Reporting
    "ScheduledReport",
]
