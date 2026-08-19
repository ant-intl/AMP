import type { ChatMessage, ProtocolEvent } from '../types';

/**
 * Derivation layer for the payment receipt card (rule-based phase).
 * Everything is derived from the SSE events the frontend already received —
 * no backend fields added, and anything not derivable is marked unverified
 * instead of being fabricated.
 */

export interface ReceiptProduct {
  name: string;
  price: string;
  currency: string;
  image_url?: string;
}

export interface ReceiptData {
  product?: ReceiptProduct;
  checkoutId?: string;
  total?: string;
  currency?: string;
  transactionId: string;
  totalSteps: number;
  compliance: { label: string; verified: boolean }[];
}

function findEvent(events: ProtocolEvent[], action: string): ProtocolEvent | undefined {
  return events.find((e) => e.action === action);
}

/** Most recent occurrence — correct when earlier purchases exist in history. */
function findLastEvent(events: ProtocolEvent[], action: string): ProtocolEvent | undefined {
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].action === action) return events[i];
  }
  return undefined;
}

function asRecord(v: unknown): Record<string, unknown> | undefined {
  return v && typeof v === 'object' && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : undefined;
}

function formatAmount(v: unknown): string | undefined {
  if (typeof v === 'number' && Number.isFinite(v)) return v.toFixed(2);
  if (typeof v === 'string' && v.trim()) return v;
  return undefined;
}

function extractProduct(events: ProtocolEvent[]): ReceiptProduct | undefined {
  const resp = findLastEvent(events, 'return_catalog')?.response;
  const list = resp?.products;
  if (!Array.isArray(list) || list.length === 0) return undefined;
  const first = asRecord(list[0]);
  const name = typeof first?.name === 'string' ? first.name : undefined;
  // price is either a {value, currency} object or a plain cents integer.
  const priceObj = asRecord(first?.price);
  const value = priceObj
    ? formatAmount(priceObj.value)
    : formatAmount(
        typeof first?.price === 'number' ? first.price / 100 : undefined,
      );
  const currency =
    (priceObj && typeof priceObj.currency === 'string'
      ? priceObj.currency
      : typeof first?.currency === 'string'
        ? first.currency
        : undefined);
  if (!name || !value || !currency) return undefined;
  // Merchant catalog payloads are camelCase (imageUrl) since the API naming migration.
  const image_url =
    typeof first?.imageUrl === 'string' && first.imageUrl ? first.imageUrl : undefined;
  return { name, price: value, currency, image_url };
}

/**
 * Build receipt data for a completed purchase turn.
 * Returns null when the turn has no checkout evidence (bind turns, idempotent
 * re-confirm turns, failures) — the card simply does not render then.
 */
export function buildReceipt(msg: ChatMessage, allEvents: ProtocolEvent[]): ReceiptData | null {
  if (msg.stopReason?.state !== 'completed') return null;
  const events = msg.protocolEvents ?? [];
  // Only the turn that actually executed payment renders a receipt —
  // otherwise any completed turn after a purchase (e.g. user says "ok")
  // re-renders the old order with all compliance checks red.
  if (!findEvent(events, 'start_payment')) return null;

  // Checkout/catalog evidence may belong to an earlier turn (IMMEDIATE flow
  // creates checkout before the IDV wait, then completes payment in the next
  // turn), so order data is searched across the full event history — most
  // recent occurrence wins. Compliance checks stay on this turn's events.
  const checkoutResp = findLastEvent(allEvents, 'return_checkout')?.response;
  const checkoutId =
    typeof checkoutResp?.checkout_id === 'string' ? checkoutResp.checkout_id : undefined;
  if (!checkoutId) return null;

  const total = formatAmount(checkoutResp?.total_amount);
  const currency =
    typeof checkoutResp?.currency === 'string' ? checkoutResp.currency : undefined;
  const product = extractProduct(allEvents);

  const phases = new Set(events.map((e) => e.phase));
  const stepNames = new Set((msg.steps ?? []).map((s) => s.name));

  // Authorization chain depth (ARCHITECTURE.md): an L3 packet is only present
  // when the agent co-signed the checkout (AUTONOMOUS, 3-layer L1+L2+L3).
  // Human-present (IMMEDIATE) has no L3 — the user confirms in person, so the
  // chain is 2-layer (L1+L2).
  const is3Layer = findEvent(events, 'return_l3_serialized') !== undefined;

  const compliance = [
    {
      label: is3Layer
        ? 'L1/L2/L3 authorization chain complete'
        : 'L1/L2 authorization chain complete',
      verified: ['mandate', 'checkout'].every((p) => phases.has(p)),
    },
    {
      label: is3Layer
        ? 'One-time credential applied (L3)'
        : 'Payment credential applied (L1&L2)',
      verified: findEvent(events, 'return_payment_token') !== undefined,
    },
    {
      label: 'Mandate verified before payment',
      verified:
        stepNames.has('inquiry_mandate_session') && stepNames.has('start_payment'),
    },
  ];

  return {
    product,
    checkoutId,
    total,
    currency,
    transactionId: msg.stopReason.completed.transaction_id ?? '—',
    totalSteps: msg.stopReason.completed.total_steps,
    compliance,
  };
}
