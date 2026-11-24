from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProviderDispatchResult:
    success: bool
    status: str  # DISPATCHED, DELIVERED, FAILED
    provider: str
    provider_message_id: Optional[str] = None
    error_details: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseChannelAdapter(ABC):
    """
    Abstract base class for all external provider notification channel adapters.
    Never returns fake success. Accurately reports provider responses, errors, and IDs.
    """

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        content: str,
        template_meta: Optional[Dict[str, Any]] = None,
        tenant_config: Optional[Dict[str, Any]] = None,
    ) -> ProviderDispatchResult:
        pass
