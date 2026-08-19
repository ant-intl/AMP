import { useEffect, useState } from 'react';
import { Check, Loader2, Sparkles } from 'lucide-react';
import type { ChatMessage, ProtocolEvent, StopInputRequired } from '../types';
import { JOURNEY_STEP_MS } from './ProductJourneyMessage';
import ShoppingIntentCard from './ShoppingIntentCard';
import ReceiptCard from './ReceiptCard';
import FadeImg from './FadeImg';

/** Pacing: how long the "Searching products..." indicator stays on screen. */
const SEARCH_INDICATOR_MS = 1500;

interface Props {
  msg: ChatMessage;
  /** Protocol events across all turns (product/receipt evidence may predate this turn). */
  allEvents: ProtocolEvent[];
  onSend?: (text: string) => void;
  taskId?: string | null;
  isLatest?: boolean;
  onProcessing?: (label: string) => void;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function asRecord(v: unknown): Record<string, unknown> | undefined {
  return v && typeof v === 'object' && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : undefined;
}

/**
 * IMMEDIATE (human-present) purchase journey.
 *
 * Unlike AUTONOMOUS — which replays a whole multi-item purchase inside one
 * turn — IMMEDIATE splits the purchase across two turns around the
 * interactive mandate IDV (ARCHITECTURE.md human-present flow):
 *
 *   Turn A: search → product card → checkout created → authorization card
 *           (the user completes mandate IDV via "Verify to approve")
 *   Turn B: (after IDV) payment credential → paid → receipt
 *
 * This component renders the journey half belonging to the given turn, with
 * the same paced reveal as AUTONOMOUS. The credential step is labelled
 * "2-layer" because the human-present chain is L1+L2 (no agent-signed L3).
 */
export default function ImmediatePurchaseJourney({ msg, allEvents, onSend, taskId, isLatest, onProcessing }: Props) {
  const stop = msg.stopReason;
  const events = msg.protocolEvents ?? [];

  // Turn A: the mandate-IDV wait that carries the selected product.
  const isTurnA =
    stop?.state === 'input_required' &&
    stop.input_required.type === 'idv' &&
    !!(stop as StopInputRequired).input_required.selected_product;

  // Turn B: the completed payment turn. IMMEDIATE never emits
  // intent_product_match (only the AUTONOMOUS travel matcher does), so its
  // absence distinguishes this from an AUTONOMOUS purchase completion.
  const isTurnB =
    stop?.state === 'completed' &&
    events.some((e) => e.action === 'start_payment') &&
    !events.some((e) => e.action === 'intent_product_match');

  if (isTurnA) {
    return <TurnA msg={msg} onSend={onSend} taskId={taskId} isLatest={isLatest} onProcessing={onProcessing} />;
  }
  if (isTurnB) {
    return <TurnB msg={msg} allEvents={allEvents} />;
  }
  return null;
}

/** Turn A: searching → product card → checkout created → mandate authorization card. */
function TurnA({ msg, onSend, taskId, isLatest, onProcessing }: {
  msg: ChatMessage;
  onSend?: (text: string) => void;
  taskId?: string | null;
  isLatest?: boolean;
  onProcessing?: (label: string) => void;
}) {
  const stop = msg.stopReason as StopInputRequired;
  const product = stop.input_required.selected_product!;
  const checkoutAmount = stop.input_required.checkout_amount;
  const events = msg.protocolEvents ?? [];

  const checkoutResp = asRecord(events.find((e) => e.action === 'return_checkout')?.response);
  const checkoutId = typeof checkoutResp?.checkout_id === 'string' ? checkoutResp.checkout_id : undefined;
  const checkoutTotal =
    typeof checkoutResp?.total_amount === 'number' ? checkoutResp.total_amount : checkoutAmount;

  // The mandate session request carries the raw shopping intent (the user's
  // own words), shown on the authorization card.
  const mandateReq = asRecord(events.find((e) => e.action === 'create_mandate_session')?.request);
  const intent = typeof mandateReq?.description === 'string' ? mandateReq.description : '';

  // Reveal pacing: 0 = searching indicator, 1 = product + checkout (working),
  // 2 = checkout done + authorization card. The checkout reveal is gated on
  // the real return_checkout event, so it never precedes reality.
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (step === 0) {
      const t = setTimeout(() => setStep(1), SEARCH_INDICATOR_MS);
      return () => clearTimeout(t);
    }
    if (step === 1 && checkoutId !== undefined) {
      const t = setTimeout(() => setStep(2), JOURNEY_STEP_MS);
      return () => clearTimeout(t);
    }
  }, [step, checkoutId]);

  const priceDisplay = (product.price / 100).toFixed(2);

  // Phase 0: the searching indicator, removed the moment the product appears.
  if (step === 0) {
    return (
      <div className="message message--agent">
        <div className="message__avatar message__avatar--agent" aria-hidden="true">
          <Sparkles size={18} />
        </div>
        <div className="message__body">
          <div className="message__meta">
            <span className="message__role">Agent</span>
            <span className="message__time">{formatTime(msg.timestamp)}</span>
          </div>
          <div className="message__bubble">
            <span className="message__text working-text">Searching products...</span>
          </div>
        </div>
      </div>
    );
  }

  const checkoutDone = step >= 2;

  return (
    <div className="message message--agent">
      <div className="message__avatar message__avatar--agent" aria-hidden="true">
        <Sparkles size={18} />
      </div>
      <div className="message__body">
        <div className="message__meta">
          <span className="message__role">Agent</span>
          <span className="message__time">{formatTime(msg.timestamp)}</span>
        </div>
        <div className="message__bubble">
          {/* Product card */}
          <div className="product-journey__card">
            {product.imageUrl && (
              <FadeImg className="product-journey__img" src={product.imageUrl} alt={product.name} />
            )}
            <div className="product-journey__info">
              <div className="product-journey__name">{product.name}</div>
              <div className="product-journey__price">${priceDisplay}</div>
            </div>
          </div>

          {/* Journey: checkout step */}
          <div className="product-journey__journey">
            <div className="product-journey__step">
              {checkoutDone ? (
                <span className="product-journey__step-icon product-journey__step-icon--done">
                  <Check size={12} strokeWidth={3} />
                </span>
              ) : (
                <span className="product-journey__step-icon product-journey__step-icon--active">
                  <Loader2 size={12} strokeWidth={3} className="product-journey__spin" />
                </span>
              )}
              <span className={`product-journey__step-text${checkoutDone ? '' : ' product-journey__step-text--active'}`}>
                {checkoutDone
                  ? `Checkout created · ${checkoutId ?? ''} · $${(checkoutTotal ?? 0).toFixed(2)}`
                  : 'Creating checkout...'}
              </span>
            </div>
          </div>

          {/* Mandate authorization card (user completes IDV) — revealed after checkout */}
          {checkoutDone && onSend && (
            <ShoppingIntentCard
              intent={intent}
              amount={checkoutTotal}
              taskId={taskId}
              onSend={onSend}
              onProcessing={onProcessing}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/** Turn B: (after IDV) payment credential → paid → receipt. */
function TurnB({ msg, allEvents }: { msg: ChatMessage; allEvents: ProtocolEvent[] }) {
  const events = msg.protocolEvents ?? [];
  const credentialReady = events.some((e) => e.action === 'return_payment_token');
  const paid = events.some((e) => e.action === 'start_payment');

  // Compact product reference — the product was searched in the earlier
  // Turn A, so look it up across the full event history.
  const catalogResp = asRecord(
    [...allEvents].reverse().find((e) => e.action === 'return_catalog')?.response,
  );
  const productList = Array.isArray(catalogResp?.products) ? (catalogResp!.products as unknown[]) : [];
  const refProduct = asRecord(productList[0]);
  const refName = typeof refProduct?.name === 'string' ? refProduct.name : undefined;
  const refPriceCents = typeof refProduct?.price === 'number' ? refProduct.price : undefined;

  // Reveal pacing: 0 = credential working, 1 = credential done + paying,
  // 2 = paid + receipt. Each advance is gated on the real event.
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (step === 0 && credentialReady) {
      const t = setTimeout(() => setStep(1), JOURNEY_STEP_MS);
      return () => clearTimeout(t);
    }
    if (step === 1 && paid) {
      const t = setTimeout(() => setStep(2), JOURNEY_STEP_MS);
      return () => clearTimeout(t);
    }
  }, [step, credentialReady, paid]);

  // Human-present applies L1&L2 only (no agent-signed L3) → "2-layer".
  const steps = [
    { working: 'Applying for payment credential...', done: 'Payment credential ready · 2-layer authorization chain verified' },
    { working: 'Paying...', done: 'Paid' },
  ];

  return (
    <div className="message message--agent">
      <div className="message__avatar message__avatar--agent" aria-hidden="true">
        <Sparkles size={18} />
      </div>
      <div className="message__body">
        <div className="message__meta">
          <span className="message__role">Agent</span>
          <span className="message__time">{formatTime(msg.timestamp)}</span>
        </div>
        <div className="message__bubble">
          {/* Compact product reference */}
          {refName && (
            <div className="product-journey__ref">
              {refName}
              {refPriceCents !== undefined && ` · $${(refPriceCents / 100).toFixed(2)}`}
            </div>
          )}

          {/* Journey: payment credential → paid */}
          <div className="product-journey__journey">
            {steps.map((s, i) => {
              const isDone = step >= i + 1;
              const isActive = step === i;
              if (!isDone && !isActive) return null;
              return (
                <div key={i} className="product-journey__step">
                  {isDone ? (
                    <span className="product-journey__step-icon product-journey__step-icon--done">
                      <Check size={12} strokeWidth={3} />
                    </span>
                  ) : (
                    <span className="product-journey__step-icon product-journey__step-icon--active">
                      <Loader2 size={12} strokeWidth={3} className="product-journey__spin" />
                    </span>
                  )}
                  <span className={`product-journey__step-text${isDone ? '' : ' product-journey__step-text--active'}`}>
                    {isDone ? s.done : s.working}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Receipt (order + authorization compliance) */}
          {step >= 2 && <ReceiptCard msg={msg} allEvents={allEvents} />}
        </div>
      </div>
    </div>
  );
}
