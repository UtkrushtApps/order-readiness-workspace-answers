from dataclasses import dataclass

from app.db import get_connection
from app.schemas.workflow import FulfillmentState, ReadinessOrder, WorkflowFilters


@dataclass(frozen=True)
class ReadinessQueryResult:
    rows: list[ReadinessOrder]
    total: int


class WorkflowRepository:
    def list_readiness(self, filters: WorkflowFilters) -> ReadinessQueryResult:
        # NOTE: All totals + pagination must be derived from the *same* filtered dataset.
        # We compute readiness/payment states in SQL, then apply readiness filtering,
        # then paginate while keeping count(*) OVER() aligned.
        status = filters.status
        readiness = filters.readiness
        search = filters.search
        page = filters.page
        page_size = filters.page_size

        sql = """
        WITH order_agg AS (
            SELECT
                o.id AS order_id,
                o.order_number,
                c.full_name AS customer_name,
                c.email AS customer_email,
                o.placed_at,
                o.status AS order_status,
                o.fulfillment_status AS stored_fulfillment_status,
                o.grand_total AS order_total,

                COALESCE(count(oi.id), 0) AS item_line_count,

                COALESCE(sum(p.amount) FILTER (WHERE p.status = 'succeeded'), 0) AS payment_succeeded_amount,
                COALESCE(count(p.id), 0) AS payment_attempt_count,
                COALESCE(sum(r.amount), 0) AS refund_amount_total,

                COALESCE(count(s.id), 0) AS shipment_any_count,
                COALESCE(count(*) FILTER (WHERE s.status = 'exception'), 0) AS shipment_exception_count,
                COALESCE(count(*) FILTER (WHERE s.status = 'delivered'), 0) AS shipment_delivered_count
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN payments p ON p.order_id = o.id
            LEFT JOIN refunds r ON r.order_id = o.id
            LEFT JOIN shipments s ON s.order_id = o.id
            WHERE o.deleted_at IS NULL
              AND (%(status)s::text IS NULL OR o.status = %(status)s::text)
              AND (%(search)s IS NULL OR (
                    o.order_number ILIKE ('%' || %(search)s || '%')
                    OR c.full_name ILIKE ('%' || %(search)s || '%')
                    OR c.email ILIKE ('%' || %(search)s || '%')
              ))
            GROUP BY
                o.id, o.order_number, c.full_name, c.email, o.placed_at, o.status,
                o.fulfillment_status, o.grand_total
        ),
        payment_computed AS (
            SELECT
                *,
                CASE
                    -- If refunds exist and we either have no captured succeeded amount
                    -- or refunds cover the succeeded amount => fully refunded.
                    WHEN refund_amount_total > 0
                         AND (payment_succeeded_amount = 0 OR refund_amount_total >= payment_succeeded_amount)
                    THEN 'refunded'

                    WHEN refund_amount_total > 0 THEN 'partially_refunded'
                    WHEN payment_succeeded_amount > 0 THEN 'paid'
                    WHEN payment_attempt_count > 0 THEN 'attempted'
                    ELSE 'unpaid'
                END AS payment_state
            FROM order_agg
        ),
        readiness_computed AS (
            SELECT
                *,
                (
                    (CASE WHEN item_line_count = 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN payment_state IN ('unpaid', 'attempted') THEN 1 ELSE 0 END) +
                    (CASE WHEN shipment_exception_count > 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN payment_state = 'partially_refunded' THEN 1 ELSE 0 END) +
                    (CASE WHEN stored_fulfillment_status = 'blocked' THEN 1 ELSE 0 END)
                ) AS blocker_count,

                CASE
                    WHEN order_status IN ('cancelled', 'refunded')
                         OR stored_fulfillment_status = 'cancelled'
                         OR payment_state = 'refunded'
                    THEN 'cancelled'

                    WHEN shipment_exception_count > 0
                         OR stored_fulfillment_status = 'blocked'
                         OR item_line_count = 0
                         OR payment_state IN ('unpaid', 'attempted')
                         OR payment_state = 'partially_refunded'
                    THEN 'blocked'

                    WHEN stored_fulfillment_status = 'shipped'
                         OR (shipment_any_count > 0 AND shipment_exception_count = 0)
                    THEN 'shipped'

                    WHEN stored_fulfillment_status = 'packed' THEN 'packed'

                    WHEN stored_fulfillment_status = 'ready'
                         AND payment_state = 'paid'
                    THEN 'ready'

                    WHEN stored_fulfillment_status = 'unassigned' THEN 'unassigned'

                    ELSE 'unassigned'
                END AS fulfillment_state
            FROM payment_computed
        ),
        final AS (
            SELECT
                order_id,
                order_number,
                customer_name,
                placed_at,
                order_status,
                stored_fulfillment_status,
                payment_state,
                fulfillment_state,
                item_line_count,
                order_total,
                blocker_count,

                CASE
                    WHEN order_status IN ('cancelled', 'refunded')
                         OR stored_fulfillment_status = 'cancelled'
                         OR payment_state = 'refunded'
                    THEN 'Order is cancelled/refunded.'

                    WHEN shipment_exception_count > 0
                         OR stored_fulfillment_status = 'blocked'
                         OR item_line_count = 0
                         OR payment_state IN ('unpaid', 'attempted')
                         OR payment_state = 'partially_refunded'
                    THEN (
                        array_to_string(
                            array_remove(ARRAY[
                                CASE WHEN stored_fulfillment_status = 'blocked' THEN 'Operational hold on order.' END,
                                CASE WHEN item_line_count = 0 THEN 'No purchasable items found.' END,
                                CASE WHEN payment_state IN ('unpaid', 'attempted') THEN 'Payment not captured successfully.' END,
                                CASE WHEN payment_state = 'partially_refunded' THEN 'Partial refund requires review.' END,
                                CASE WHEN shipment_exception_count > 0 THEN 'Shipment exception detected.' END
                            ], NULL),
                            ' ; '
                        )
                    )

                    WHEN stored_fulfillment_status = 'packed' THEN 'Items are packed and awaiting shipment.'
                    WHEN stored_fulfillment_status = 'ready' AND payment_state = 'paid' THEN 'Payment captured and order is ready for warehouse handoff.'
                    WHEN stored_fulfillment_status = 'shipped'
                         OR (shipment_any_count > 0 AND shipment_exception_count = 0)
                    THEN 'Shipment already created and is in transit/delivered.'

                    ELSE 'Awaiting operational assignment.'
                END AS readiness_explanation,

                count(*) OVER () AS total_count
            FROM readiness_computed
            WHERE (%(readiness)s::text IS NULL OR fulfillment_state = %(readiness)s::text)
        )
        SELECT
            order_id AS "orderId",
            order_number AS "orderNumber",
            customer_name AS "customerName",
            to_char(placed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS "placedAt",
            order_status AS "status",
            fulfillment_state AS "fulfillmentState",
            payment_state AS "paymentState",
            item_line_count AS "itemCount",
            order_total AS "orderTotal",
            blocker_count AS "blockerCount",
            readiness_explanation AS "readinessExplanation",
            total_count::int AS "total"
        FROM final
        ORDER BY placed_at DESC, order_id DESC
        LIMIT %(limit)s
        OFFSET %(offset)s;
        """

        params = {
            "status": status.value if isinstance(status, str) is False and status is not None else (status if status is not None else None),
            "readiness": readiness.value if isinstance(readiness, str) is False and readiness is not None else (readiness if readiness is not None else None),
            "search": search,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        # psycopg can't always handle enum objects as named params, so we pass plain text.
        if status is not None and not isinstance(status, str):
            params["status"] = str(status)
        if readiness is not None and not isinstance(readiness, str):
            params["readiness"] = str(readiness)

        with get_connection() as connection:
            rows = connection.execute(sql, params).fetchall()

        mapped_rows: list[ReadinessOrder] = []
        total = 0
        for row in rows:
            if total == 0:
                total = int(row.get("total") or 0)
            # Dict keys already match ReadinessOrder field names.
            mapped_rows.append(ReadinessOrder(**row))

        return ReadinessQueryResult(rows=mapped_rows, total=total)


def get_workflow_repository() -> WorkflowRepository:
    return WorkflowRepository()
