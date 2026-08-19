import { useEffect, useState } from 'react';
import { Check, Loader2, Sparkles } from 'lucide-react';
import type { ProductJourneyData } from './PurchaseJourney';
import FadeImg from './FadeImg';

/** Pacing: interval between journey step reveals within one product message. */
export const JOURNEY_STEP_MS = 1200;

interface Props {
  product: ProductJourneyData;
  /** Travel budget max (USD dollars) for the mandate quota line. */
  budgetMax?: number;
  /** Cumulative cents already spent on earlier products in this turn. */
  spentBeforeCents: number;
  timestamp: number;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * One standalone agent message for a single purchased product.
 *
 * Layout: product card (image / name / price) with the intent-matching reasons,
 * followed by a three-step journey — checkout → payment credential → payment —
 * revealed one step at a time. The step reveal is paced by a local timer but
 * gated on the real protocol data, so it never shows a step as done before the
 * corresponding event actually arrived.
 */
export default function ProductJourneyMessage({ product, budgetMax, spentBeforeCents, timestamp }: Props) {
  // Number of journey steps completed (0..3). Advances on a timer, gated on
  // the real data for the step about to complete.
  const [step, setStep] = useState(0);

  const dataReady = (k: number): boolean => {
    if (k === 1) return product.checkoutId !== undefined;
    if (k === 2) return product.credentialReady;
    if (k === 3) return product.paid;
    return false;
  };

  useEffect(() => {
    if (step >= 3) return;
    if (!dataReady(step + 1)) return; // wait for the real event
    const t = setTimeout(() => setStep((s) => s + 1), JOURNEY_STEP_MS);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, product]);

  const fmt = (cents: number) => `$${(cents / 100).toFixed(2)}`;
  const budgetCents = budgetMax ? budgetMax * 100 : 0;
  const remainingCents = budgetCents - spentBeforeCents - product.priceCents;

  const checkoutDone =
    product.checkoutId !== undefined
      ? `Checkout created · ${product.checkoutId} · $${(product.checkoutTotal ?? product.priceCents / 100).toFixed(2)}`
      : 'Checkout created';

  // The three journey steps. A step is done once `step` passes it, and is the
  // active (spinner) step while `step` sits just before it.
  const steps = [
    { working: 'Creating checkout...', done: checkoutDone },
    { working: 'Applying for payment credential...', done: 'Payment credential ready · 3-layer authorization chain verified' },
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
          <span className="message__time">{formatTime(timestamp)}</span>
        </div>
        <div className="message__bubble">
          {/* Product card */}
          <div className="product-journey__card">
            {product.imageUrl && (
              <FadeImg className="product-journey__img" src={product.imageUrl} alt={product.name} />
            )}
            <div className="product-journey__info">
              <div className="product-journey__name">{product.name}</div>
              <div className="product-journey__price">{fmt(product.priceCents)}</div>
            </div>
          </div>

          {/* Intent-matching reasons */}
          {product.reasons.length > 0 && (
            <div className="product-journey__match">
              <Check size={12} strokeWidth={3} />
              Matched — {product.reasons.join(' · ')}
            </div>
          )}

          {/* Journey: checkout → payment credential → payment */}
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
                  <span
                    className={`product-journey__step-text${isDone ? '' : ' product-journey__step-text--active'}`}
                  >
                    {isDone ? s.done : s.working}
                  </span>
                </div>
              );
            })}

            {/* Mandate quota deduction, shown once this product is paid */}
            {step >= 3 && budgetCents > 0 && (
              <div className="product-journey__quota">
                Mandate quota: {fmt(remainingCents)} remaining of {fmt(budgetCents)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
