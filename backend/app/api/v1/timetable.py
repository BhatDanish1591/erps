from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, require_any_role
from app.schemas.timetable import (
    ConflictCheckResponse,
    SubstituteAssignmentCreate,
    SubstituteAssignmentResponse,
    TimetableEntryCreate,
    TimetableEntryResponse,
    TimetableEntryUpdate,
    TimetableHolidayCreate,
    TimetableHolidayResponse,
    TimetablePeriodCreate,
    TimetablePeriodResponse,
    TimetableScheduleCreate,
    TimetableScheduleResponse,
    TimetableScheduleUpdate,
    TimetableSettingCreate,
    TimetableSettingResponse,
    WeeklyTimetableResponse,
)
from app.services.timetable_service import TimetableService

router = APIRouter(prefix="/timetable", tags=["Timetable Management"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Timetable Settings & Periods
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/settings", response_model=Dict[str, Any])
async def get_timetable_settings(
    academic_session_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    settings = await service.get_settings(tenant_id, academic_session_id)
    return {"success": True, "data": settings.model_dump()}


@router.put("/settings", response_model=Dict[str, Any])
async def update_timetable_settings(
    data: TimetableSettingCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    updated = await service.update_settings(tenant_id, data.academic_session_id, data.model_dump(exclude_unset=True))
    return {"success": True, "data": updated.model_dump()}


@router.get("/periods", response_model=Dict[str, Any])
async def list_periods(
    academic_session_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    periods = await service.list_periods(tenant_id, academic_session_id)
    return {"success": True, "data": [p.model_dump() for p in periods]}


@router.post("/periods", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_period(
    data: TimetablePeriodCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    period = await service.create_period(tenant_id, data.model_dump())
    return {"success": True, "data": period.model_dump()}


@router.delete("/periods/{period_id}", response_model=Dict[str, Any])
async def delete_period(
    period_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    success = await service.delete_period(tenant_id, period_id)
    return {"success": success, "message": "Period deleted successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Institutional Holiday Calendar
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/holidays", response_model=Dict[str, Any])
async def list_holidays(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    holidays = await service.list_holidays(tenant_id, academic_session_id, from_date, to_date)
    return {"success": True, "data": [h.model_dump() for h in holidays]}


@router.post("/holidays", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_holiday(
    data: TimetableHolidayCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    holiday = await service.create_holiday(tenant_id, data.model_dump())
    return {"success": True, "data": holiday.model_dump()}


@router.delete("/holidays/{holiday_id}", response_model=Dict[str, Any])
async def delete_holiday(
    holiday_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    success = await service.delete_holiday(tenant_id, holiday_id)
    return {"success": success, "message": "Holiday deleted successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Timetable Schedules
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/schedules", response_model=Dict[str, Any])
async def list_schedules(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    schedules = await service.list_schedules(tenant_id, academic_session_id, status_filter)
    return {"success": True, "data": [s.model_dump() for s in schedules]}


@router.post("/schedules", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: TimetableScheduleCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    schedule = await service.create_schedule(tenant_id, data.model_dump())
    return {"success": True, "data": schedule.model_dump()}


@router.get("/schedules/{schedule_id}", response_model=Dict[str, Any])
async def get_schedule_details(
    schedule_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    schedule = await service.get_schedule(tenant_id, schedule_id)
    return {"success": True, "data": schedule.model_dump()}


@router.put("/schedules/{schedule_id}", response_model=Dict[str, Any])
async def update_schedule(
    schedule_id: uuid.UUID,
    data: TimetableScheduleUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    updated = await service.update_schedule(tenant_id, schedule_id, data.model_dump(exclude_unset=True))
    return {"success": True, "data": updated.model_dump()}


@router.post("/schedules/{schedule_id}/publish", response_model=Dict[str, Any])
async def publish_schedule(
    schedule_id: uuid.UUID,
    force: bool = Query(False, description="Override non-blocking conflict warnings"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    published = await service.publish_schedule(tenant_id, schedule_id, current_user.id, force=force)
    return {"success": True, "data": published.model_dump()}


@router.get("/schedules/{schedule_id}/conflicts", response_model=Dict[str, Any])
async def audit_schedule_conflicts(
    schedule_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    report = await service.check_schedule_conflicts(tenant_id, schedule_id)
    return {"success": True, "data": report.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Timetable Entries & Quick Conflict Check
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/entries", response_model=Dict[str, Any])
async def list_entries(
    schedule_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    teacher_id: Optional[uuid.UUID] = Query(None),
    room_number: Optional[str] = Query(None),
    day_of_week: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    entries = await service.list_entries(
        tenant_id=tenant_id,
        schedule_id=schedule_id,
        class_id=class_id,
        section_id=section_id,
        teacher_id=teacher_id,
        room_number=room_number,
        day_of_week=day_of_week,
    )
    return {"success": True, "data": [e.model_dump() for e in entries]}


@router.post("/entries", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: TimetableEntryCreate,
    ignore_conflicts: bool = Query(False),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    entry = await service.create_entry(tenant_id, data.model_dump(), ignore_conflicts=ignore_conflicts)
    return {"success": True, "data": entry.model_dump()}


@router.put("/entries/{entry_id}", response_model=Dict[str, Any])
async def update_entry(
    entry_id: uuid.UUID,
    data: TimetableEntryUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    updated = await service.update_entry(tenant_id, entry_id, data.model_dump(exclude_unset=True))
    return {"success": True, "data": updated.model_dump()}


@router.delete("/entries/{entry_id}", response_model=Dict[str, Any])
async def delete_entry(
    entry_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    success = await service.delete_entry(tenant_id, entry_id)
    return {"success": success, "message": "Timetable entry deleted successfully."}


@router.get("/check-conflicts", response_model=Dict[str, Any])
async def check_conflicts_query(
    day_of_week: str = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
    teacher_id: Optional[uuid.UUID] = Query(None),
    room_number: Optional[str] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    semester: Optional[int] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    schedule_id: Optional[uuid.UUID] = Query(None),
    exclude_entry_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    conflicts = await service.detect_conflicts(
        tenant_id=tenant_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        teacher_id=teacher_id,
        room_number=room_number,
        class_id=class_id,
        section_id=section_id,
        course_id=course_id,
        semester=semester,
        batch_id=batch_id,
        schedule_id=schedule_id,
        exclude_entry_id=exclude_entry_id,
    )
    return {
        "success": True,
        "data": {
            "has_conflicts": len(conflicts) > 0,
            "total_conflicts": len(conflicts),
            "conflicts": [c.model_dump() for c in conflicts],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Calendar Views: Matrix, Class, Teacher & My Timetable
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/weekly-matrix", response_model=Dict[str, Any])
async def get_weekly_matrix(
    schedule_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    teacher_id: Optional[uuid.UUID] = Query(None),
    room_number: Optional[str] = Query(None),
    target_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    view = await service.get_weekly_view(
        tenant_id=tenant_id,
        schedule_id=schedule_id,
        class_id=class_id,
        section_id=section_id,
        teacher_id=teacher_id,
        room_number=room_number,
        target_date=target_date,
    )
    return {"success": True, "data": view.model_dump()}


@router.get("/class/{class_id}", response_model=Dict[str, Any])
async def get_class_timetable(
    class_id: uuid.UUID,
    section_id: Optional[uuid.UUID] = Query(None),
    schedule_id: Optional[uuid.UUID] = Query(None),
    target_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    view = await service.get_weekly_view(
        tenant_id=tenant_id,
        class_id=class_id,
        section_id=section_id,
        schedule_id=schedule_id,
        target_date=target_date,
    )
    return {"success": True, "data": view.model_dump()}


@router.get("/teacher/{teacher_id}", response_model=Dict[str, Any])
async def get_teacher_timetable(
    teacher_id: uuid.UUID,
    schedule_id: Optional[uuid.UUID] = Query(None),
    target_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    view = await service.get_weekly_view(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        schedule_id=schedule_id,
        target_date=target_date,
    )
    return {"success": True, "data": view.model_dump()}


@router.get("/my-timetable", response_model=Dict[str, Any])
async def get_my_timetable(
    target_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    current_user: User = Depends(require_any_role(["STUDENT", "PARENT", "TEACHER", "INSTITUTION_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get authorized personal timetable.
    Teachers view their assigned schedule + active substitutions.
    Students/Parents view their enrolled class & section schedule.
    """
    service = TimetableService(session)
    user_role = claims.get("role", "STUDENT")
    view = await service.get_my_timetable(
        tenant_id=tenant_id,
        user=current_user,
        user_role=user_role,
        target_date=target_date,
    )
    return {"success": True, "data": view.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Substitute Teacher Assignment
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/substitutes", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def assign_substitute_teacher(
    data: SubstituteAssignmentCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Assign a substitute teacher for a specific date, enforcing overlap conflict checks.
    """
    service = TimetableService(session)
    sub = await service.assign_substitute(
        tenant_id=tenant_id,
        timetable_entry_id=data.timetable_entry_id,
        assignment_date=data.assignment_date,
        substitute_teacher_id=data.substitute_teacher_id,
        assigned_by=current_user.id,
        reason=data.reason,
    )
    return {"success": True, "data": sub.model_dump()}


@router.get("/substitutes", response_model=Dict[str, Any])
async def list_substitutes(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    teacher_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TimetableService(session)
    subs = await service.list_substitutes(tenant_id, from_date, to_date, teacher_id)
    return {"success": True, "data": [s.model_dump() for s in subs]}
