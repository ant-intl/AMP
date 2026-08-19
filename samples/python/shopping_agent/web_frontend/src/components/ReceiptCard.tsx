import { useState } from 'react';
import { BadgeCheck, Check, ChevronRight, CircleAlert, Copy, Receipt } from 'lucide-react';
import type { ChatMessage, ProtocolEvent } from '../types';
import { buildReceipt } from '../lib/receipt';
import FadeImg from './FadeImg';

/** Middle-truncate a long identifier: `ebd67…353c` (head 5 / tail 4). */
export function truncateHash(hash: string, head = 5, tail = 4): string {
  if (hash.length <= head + tail + 1) return hash;
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`;
}

/** Truncated hash that copies the full value on click (Copy → Check feedback).
 *  Rendered as a span with button semantics so it can nest inside the receipt
 *  toggle button (interactive-inside-button is invalid HTML).
 *  Exported for the multi-item SummaryReceipt (PurchaseJourney). */
export function CopyableHash({ value, className }: { value: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  const copy = (e: React.SyntheticEvent) => {
    // Never bubble into the receipt toggle (it would collapse the card).
    e.stopPropagation();
    e.preventDefault();
    navigator.clipboard?.writeText(value).catch(() => { /* clipboard unavailable */ });
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <span
      role="button"
      tabIndex={0}
      className={`hash-copy ${className ?? ''}`}
      onClick={copy}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') copy(e);
      }}
      title={`${value} (click to copy)`}
      aria-label={`Copy ${value}`}
    >
      <span className="hash-copy__text">{truncateHash(value)}</span>
      {copied ? (
        <Check size={11} strokeWidth={3} className="hash-copy__icon hash-copy__icon--ok" />
      ) : (
        <Copy size={11} className="hash-copy__icon" />
      )}
    </span>
  );
}

interface Props {
  msg: ChatMessage;
  /** Protocol events from all turns (order evidence may predate this turn). */
  allEvents: ProtocolEvent[];
}

/**
 * Payment receipt card embedded in a completed purchase bubble.
 * Sections — Order (what was bought) and Authorization (compliance checks
 * derived from the protocol events). Renders nothing when the turn has no
 * checkout evidence.
 */
export default function ReceiptCard({ msg, allEvents }: Props) {
  const [expanded, setExpanded] = useState(true);
  const data = buildReceipt(msg, allEvents);
  if (!data) return null;

  const summary = [
    data.product?.name,
    data.total ? `${data.total} ${data.currency ?? ''}`.trim() : undefined,
    data.transactionId,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="receipt">
      <button
        className="receipt__toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <span
          className={`receipt__toggle-icon ${
            expanded ? 'receipt__toggle-icon--open' : ''
          }`}
        >
          <ChevronRight size={12} strokeWidth={2.5} />
        </span>
        <Receipt size={14} />
        Receipt
        {expanded ? (
          <CopyableHash value={data.transactionId} className="receipt__txn" />
        ) : (
          <span className="receipt__summary">{summary}</span>
        )}
      </button>

      {expanded && (
        <div className="receipt__body">
          <div className="receipt__section">
            <div className="receipt__label">Order</div>
            {data.product && (
              <div className="receipt__row">
                {data.product.image_url && (
                  <FadeImg className="receipt__thumb" src={data.product.image_url} alt={data.product.name} />
                )}
                <span className="receipt__key">{data.product.name}</span>
                <span className="receipt__val">
                  {data.total ?? data.product.price} {data.currency ?? data.product.currency}
                </span>
              </div>
            )}
            {data.checkoutId && (
              <div className="receipt__row">
                <span className="receipt__key">Checkout</span>
                <CopyableHash value={data.checkoutId} className="receipt__val receipt__val--mono" />
              </div>
            )}
            <div className="receipt__row">
              <span className="receipt__key">Transaction</span>
              <CopyableHash value={data.transactionId} className="receipt__val receipt__val--mono" />
            </div>
          </div>

          <div className="receipt__section">
            <div className="receipt__label">Authorization</div>
            {data.compliance.map((c) => (
              <div key={c.label} className="receipt__check">
                {c.verified ? (
                  <BadgeCheck size={14} className="receipt__check-icon--ok" />
                ) : (
                  <CircleAlert size={14} className="receipt__check-icon--warn" />
                )}
                {c.label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
