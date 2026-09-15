export type OrderLifecycleStatus = 'new' | 'paid' | 'processing' | 'shipped' | 'cancelled' | 'refunded';

export type FulfillmentState = 'unassigned' | 'ready' | 'blocked' | 'packed' | 'shipped' | 'cancelled';

export type PaymentState = 'unpaid' | 'attempted' | 'paid' | 'partially_refunded' | 'refunded';

export interface WorkflowFilters {
  status?: OrderLifecycleStatus | 'all';
  readiness?: FulfillmentState | 'all';
  search?: string;
  page: number;
  pageSize: number;
}

export interface ReadinessOrder {
  orderId: number;
  orderNumber: string;
  customerName: string;
  placedAt: string;
  status: OrderLifecycleStatus;
  fulfillmentState: FulfillmentState;
  paymentState: PaymentState;
  itemCount: number;
  orderTotal: string;
  blockerCount: number;
  readinessExplanation: string;
}

export interface PageMeta {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface ReadinessResponse {
  data: ReadinessOrder[];
  meta: PageMeta;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
