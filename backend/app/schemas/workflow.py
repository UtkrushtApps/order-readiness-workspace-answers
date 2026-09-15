from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(StrEnum):
    new = "new"
    paid = "paid"
    processing = "processing"
    shipped = "shipped"
    cancelled = "cancelled"
    refunded = "refunded"


class FulfillmentState(StrEnum):
    unassigned = "unassigned"
    ready = "ready"
    blocked = "blocked"
    packed = "packed"
    shipped = "shipped"
    cancelled = "cancelled"


class PaymentState(StrEnum):
    unpaid = "unpaid"
    attempted = "attempted"
    paid = "paid"
    partially_refunded = "partially_refunded"
    refunded = "refunded"


class WorkflowFilters(BaseModel):
    status: OrderStatus | None = None
    readiness: FulfillmentState | None = None
    search: str | None = Field(default=None, max_length=80)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class ReadinessOrder(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    orderId: int
    orderNumber: str
    customerName: str
    placedAt: str
    status: OrderStatus
    fulfillmentState: FulfillmentState
    paymentState: PaymentState
    itemCount: int
    orderTotal: Decimal
    blockerCount: int
    readinessExplanation: str


class PageMeta(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int


class ReadinessResponse(BaseModel):
    data: list[ReadinessOrder]
    meta: PageMeta
