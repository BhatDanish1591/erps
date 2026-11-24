from __future__ import annotations

import contextvars
import uuid
from typing import Optional

# Global contextvar tracking the tenant id for the active execution context / request
_current_tenant_id: contextvars.ContextVar[Optional[uuid.UUID]] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


def get_current_tenant_id() -> Optional[uuid.UUID]:
    """Retrieve the current active tenant UUID from context, or None if unassigned."""
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: Optional[uuid.UUID]) -> contextvars.Token:
    """Set the current tenant UUID in context, returning a token to reset if needed."""
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token: contextvars.Token) -> None:
    """Reset the tenant context back to its previous state."""
    _current_tenant_id.reset(token)
