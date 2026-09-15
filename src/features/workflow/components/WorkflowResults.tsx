import type { ReadinessResponse } from '../../../api/contracts';

interface Props {
  response?: ReadinessResponse;
  loading: boolean;
  error?: string;
  onPageChange?: (page: number) => void;
}

export function WorkflowResults({ response, loading, error, onPageChange }: Props) {
  if (loading) {
    return <div className="state-panel">Loading readiness data…</div>;
  }

  if (error) {
    return <div className="state-panel error">{error}</div>;
  }

  if (!response || response.data.length === 0) {
    return <div className="state-panel">No readiness results are available for this view.</div>;
  }

  const canPrev = response.meta.page > 1;
  const canNext = response.meta.page < response.meta.totalPages;

  return (
    <div className="results">
      <table>
        <thead>
          <tr>
            <th>Order</th>
            <th>Customer</th>
            <th>Placed</th>
            <th>Status</th>
            <th>Readiness</th>
            <th>Payment</th>
            <th>Items</th>
            <th>Total</th>
            <th>Blockers</th>
          </tr>
        </thead>
        <tbody>
          {response.data.map((order) => (
            <tr key={order.orderId}>
              <td>{order.orderNumber}</td>
              <td>{order.customerName}</td>
              <td>{new Date(order.placedAt).toLocaleString()}</td>
              <td>{order.status}</td>
              <td>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <span>{order.fulfillmentState}</span>
                  <span style={{ fontSize: '0.82em', color: '#5e6b83' }}>{order.readinessExplanation}</span>
                </div>
              </td>
              <td>{order.paymentState}</td>
              <td>{order.itemCount}</td>
              <td>{order.orderTotal}</td>
              <td>{order.blockerCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <footer className="pagination-copy" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <span>
          Page {response.meta.page} of {response.meta.totalPages}
        </span>
        <span style={{ display: 'flex', gap: 10 }}>
          <button type="button" className="secondary" disabled={!canPrev} onClick={() => onPageChange?.(response.meta.page - 1)}>
            Prev
          </button>
          <button type="button" className="secondary" disabled={!canNext} onClick={() => onPageChange?.(response.meta.page + 1)}>
            Next
          </button>
        </span>
      </footer>
    </div>
  );
}
