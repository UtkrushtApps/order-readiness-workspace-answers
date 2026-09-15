# Solution Steps

1. Update the shared data contract: add `readinessExplanation` to the backend Pydantic schema and the frontend TypeScript `ReadinessOrder` type, then render it in the results table.

2. Implement the readiness queue query in `backend/app/repositories/workflow_repository.py` using a layered SQL approach (CTEs): aggregate order/payment/refund/shipment/item facts, compute `payment_state`, compute `fulfillment_state` + `blocker_count`, then filter by the requested readiness and apply the same ordering + pagination while keeping `count(*) OVER()` for consistent totals.

3. Make sure the repository returns typed `ReadinessOrder` rows and a single `total` count that matches the filters. Pagination correctness comes from using the window count on the post-filter dataset (before `LIMIT/OFFSET`).

4. Wire pagination controls in the React UI: extend `WorkflowResults` to show Prev/Next buttons based on `meta.page` and `meta.totalPages`, and extend `WorkflowPage` to update `filters.page` accordingly.

5. Verify error/empty/loading states: keep existing UI handling for `loading`, `error`, and empty `data`, and ensure the API returns the expected shape (`{ data, meta }`) for all states. Run `npm run build` and a quick manual test by loading `/api/v1/admin/fulfillment-readiness?page=1&pageSize=10` in the browser/network tab.

