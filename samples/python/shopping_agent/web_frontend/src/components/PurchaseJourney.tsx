import { useEffect, useMemo, useState } from 'react';
import { BadgeCheck, Check, ChevronDown, ChevronRight, CircleAlert, Receipt, Search, Sparkles } from 'lucide-react';
import type { ChatMessage, ProtocolEvent } from '../types';
import { buildReceipt } from '../lib/receipt';
import ProductJourneyMessage, { JOURNEY_STEP_MS } from './ProductJourneyMessage';
import FadeImg from './FadeImg';
import { CopyableHash } from './ReceiptCard';

/** Pacing: how long the "Searching products..." indicator stays on screen. */
const SEARCH_INDICATOR_MS = 1500;
/** Pacing: pause after a product's journey completes, before the next search. */
const INTER_PRODUCT_PAUSE_MS = 400;

interface Props {
  /** The original agent turn message carrying every purchase protocol event. */
  msg: ChatMessage;
  /** Protocol events across all turns (receipt derivation may look back). */
  allEvents: ProtocolEvent[];
  /** Travel budget max (USD dollars) for mandate quota display. */
  budgetMax?: number;
}

/** Everything the frontend needs to render one product's journey. */
export interface ProductJourneyData {
  name: string;
  imageUrl: string;
  priceCents: number;
  reasons: string[];
  /** Real backend search duration in milliseconds (from intent_product_match event). */
  elapsedMs?: number;
  /** Number of catalog candidates scanned before filtering (search scope evidence). */
  candidates?: number;
  checkoutId?: string;
  checkoutTotal?: number;
  checkoutCurrency?: string;
  credentialReady: boolean;
  paid: boolean;
}

function asStr(v: unknown): string {
  return typeof v === 'string' ? v : '';
}

function asNum(v: unknown): number | undefined {
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Multi-item purchase presentation (AUTONOMOUS travel mode).
 *
 * The agent runs the whole purchase loop in well under a second, so every
 * protocol event arrives in one fast burst — rendering them as they land would
 * flash the final state at once. Instead this component replays the completed
 * loop as a paced conversation: for each product a "Searching products..."
 * indicator appears first, then a standalone product message walks through
 * checkout → payment credential → payment, and a final summary message with
 * the receipt closes the turn.
 *
 * Message appearance is paced here (the timeline `pos`); the step-by-step
 * reveal inside each product message is owned by ProductJourneyMessage. The
 * replay never invents progress — a unit only appears once its real events
 * have arrived.
 */
export default function PurchaseJourney({ msg, allEvents, budgetMax }: Props) {
  const events = msg.protocolEvents ?? [];

  // Group the flat protocol stream by product. Items are processed strictly
  // sequentially, so the Nth occurrence of each per-product event belongs to
  // product N.
  const products = useMemo<ProductJourneyData[]>(() => {
    const matches = events.filter((e) => e.action === 'intent_product_match');
    const checkouts = events.filter((e) => e.action === 'return_checkout');
    const credentials = events.filter((e) => e.action === 'return_payment_token');
    const payments = events.filter((e) => e.action === 'start_payment');
    return matches.map((m, i) => {
      const co = checkouts[i]?.response;
      return {
        name: asStr(m.response.selected),
        imageUrl: asStr(m.response.imageUrl),
        priceCents: asNum(m.response.price) ?? 0,
        reasons: Array.isArray(m.request.constraints)
          ? (m.request.constraints as unknown[]).map(String)
          : [],
        elapsedMs: asNum(m.response.elapsed_ms),
        candidates: asNum(m.response.candidates),
        checkoutId: co ? asStr(co.checkout_id) || undefined : undefined,
        checkoutTotal: co ? asNum(co.total_amount) : undefined,
        checkoutCurrency: co ? asStr(co.currency) || undefined : undefined,
        credentialReady: credentials.length > i,
        paid: payments.length > i,
      };
    });
  }, [events]);

  // Flat replay timeline: [search(0), product(0), search(1), product(1), ..., summary].
  // A product unit lasts long enough for its 3 journey steps plus a pause.
  const units = useMemo(() => {
    const list: { kind: 'search' | 'product' | 'summary'; productIndex: number; duration: number }[] = [];
    products.forEach((_, i) => {
      list.push({ kind: 'search', productIndex: i, duration: SEARCH_INDICATOR_MS });
      list.push({ kind: 'product', productIndex: i, duration: 3 * JOURNEY_STEP_MS + INTER_PRODUCT_PAUSE_MS });
    });
    list.push({ kind: 'summary', productIndex: -1, duration: 0 });
    return list;
  }, [products]);

  // Replay position: index of the unit currently on screen. Unit 0 (the first
  // "Searching products..." indicator) shows immediately; each unit stays for
  // its own duration, then the replay advances — but only once the real events
  // for the upcoming unit have arrived (never runs ahead of reality).
  const [pos, setPos] = useState(0);

  const readyFor = (index: number): boolean => {
    const u = units[index];
    if (!u) return false;
    if (u.kind === 'search') return true; // searching precedes the match by design
    if (u.kind === 'product') return products[u.productIndex] !== undefined;
    return msg.stopReason?.state === 'completed'; // summary waits for completion
  };

  useEffect(() => {
    const u = units[pos];
    if (!u) return;
    const next = pos + 1;
    if (next >= units.length) return; // summary is on screen; nothing follows
    if (!readyFor(next)) return; // wait for the next unit's real events
    const t = setTimeout(() => setPos(next), u.duration);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pos, units, products, msg.stopReason]);

  const budgetCents = budgetMax ? budgetMax * 100 : 0;
  const spentCents = products.reduce((acc, p) => (p.paid ? acc + p.priceCents : acc), 0);
  const allPaid = products.length > 0 && products.every((p) => p.paid);
  const txnId = msg.stopReason?.state === 'completed' ? msg.stopReason.completed.transaction_id ?? '—' : '—';
  // Reuse the shared receipt derivation for the authorization compliance checks.
  const receipt = useMemo(() => buildReceipt(msg, allEvents), [msg, allEvents]);

  return (
    <>
      {units.map((u, idx) => {
        if (idx > pos) return null; // not yet revealed

        if (u.kind === 'search') {
          const isSearching = pos === idx; // still the active unit
          const realMs = products[u.productIndex]?.elapsedMs;
          const elapsed = realMs !== undefined
            ? (realMs < 1000 ? `${realMs}ms` : `${(realMs / 1000).toFixed(1)}s`)
            : null;
          return (
            <div key={`search-${u.productIndex}`} className="message message--agent">
              <div className="message__avatar message__avatar--agent">
                <Sparkles size={18} />
              </div>
              <div className="message__body">
                <div className="message__meta">
                  <span className="message__role">Agent</span>
                  <span className="message__time">{formatTime(msg.timestamp)}</span>
                </div>
                <div className={`message__bubble${isSearching ? '' : ' message__bubble--quiet'}`}>
                  {isSearching ? (
                    <span className="search-status search-status--working">
                      <Search size={13} strokeWidth={2.5} className="search-status__icon" />
                      <span className="working-text">Searching products...</span>
                    </span>
                  ) : (
                    <SearchMatchedEvidence
                      elapsed={elapsed}
                      candidates={products[u.productIndex]?.candidates}
                    />
                  )}
                </div>
              </div>
            </div>
          );
        }

        if (u.kind === 'product') {
          const product = products[u.productIndex];
          if (!product) return null;
          const spentBeforeCents = products
            .slice(0, u.productIndex)
            .reduce((acc, p) => (p.paid ? acc + p.priceCents : acc), 0);
          return (
            <ProductJourneyMessage
              key={`product-${u.productIndex}`}
              product={product}
              budgetMax={budgetMax}
              spentBeforeCents={spentBeforeCents}
              timestamp={msg.timestamp}
            />
          );
        }

        // Summary message: per-item totals + mandate quota + receipt.
        return (
          <div key="summary" className="message message--agent">
            <div className="message__avatar message__avatar--agent">
              <Sparkles size={18} />
            </div>
            <div className="message__body">
              <div className="message__meta">
                <span className="message__role">Agent</span>
                <span className="message__time">{formatTime(msg.timestamp)}</span>
              </div>
              <div className="message__bubble">
                <span className="message__text">
                  All done — {products.length} purchases completed successfully.
                </span>
                <SummaryReceipt
                  products={products}
                  budgetCents={budgetCents}
                  spentCents={spentCents}
                  allPaid={allPaid}
                  txnId={txnId}
                  compliance={(receipt?.compliance ?? []).filter(
                    (c) => !c.label.startsWith('Payment matches checkout'),
                  )}
                />
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}

const fmtCents = (cents: number) => `$${(cents / 100).toFixed(2)}`;

/**
 * Completed search status line with an inline evidence accordion.
 *
 * Collapsed: ✓ Matched products · {elapsed} · ⌄
 * Expanded:  reveals "Scanned N candidates" (the catalog size before filtering),
 *            disclosing the search scope Perplexity-style. The chevron is only
 *            rendered when candidate evidence exists (graceful degradation).
 */
function SearchMatchedEvidence({ elapsed, candidates }: { elapsed: string | null; candidates?: number }) {
  const [open, setOpen] = useState(false);
  const hasEvidence = candidates !== undefined;
  return (
    <div className="search-evidence">
      <button
        type="button"
        className="search-status search-status--done"
        onClick={() => hasEvidence && setOpen((v) => !v)}
        aria-expanded={open}
        disabled={!hasEvidence}
      >
        <span className="search-status__check">
          <Check size={11} strokeWidth={3.5} />
        </span>
        <span className="search-status__label">Matched products</span>
        {elapsed && <span className="search-status__elapsed">{elapsed}</span>}
        {hasEvidence && (
          <ChevronDown
            size={12}
            strokeWidth={2.5}
            className={`search-evidence__chevron${open ? ' search-evidence__chevron--open' : ''}`}
          />
        )}
      </button>
      {hasEvidence && open && (
        <div className="search-evidence__detail">Scanned {candidates} candidates</div>
      )}
    </div>
  );
}

interface SummaryReceiptProps {
  products: ProductJourneyData[];
  budgetCents: number;
  spentCents: number;
  allPaid: boolean;
  txnId: string;
  compliance: { label: string; verified: boolean }[];
}

/**
 * Closing receipt for a multi-item purchase, styled like the single-purchase
 * ReceiptCard (collapsible, Order + Authorization sections) but aggregating
 * every purchased product and the total mandate quota used.
 */
function SummaryReceipt({ products, budgetCents, spentCents, allPaid, txnId, compliance }: SummaryReceiptProps) {
  const [open, setOpen] = useState(true);

  return (
    <div className="receipt">
      <button className="receipt__toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className={`receipt__toggle-icon ${open ? 'receipt__toggle-icon--open' : ''}`}>
          <ChevronRight size={12} strokeWidth={2.5} />
        </span>
        <Receipt size={14} />
        Receipt
        {open && txnId !== '—' ? (
          <CopyableHash value={txnId} className="receipt__txn" />
        ) : open ? (
          <span className="receipt__txn">{txnId}</span>
        ) : (
          <span className="receipt__summary">
            {products.length} items · {fmtCents(spentCents)}
          </span>
        )}
      </button>

      {open && (
        <div className="receipt__body">
          <div className="receipt__section">
            <div className="receipt__label">Order</div>
            {products.map((p, i) => (
              <div key={i} className="receipt__row">
                {p.imageUrl && <FadeImg className="receipt__thumb" src={p.imageUrl} alt={p.name} />}
                <span className="receipt__key">{p.name}</span>
                <span className="receipt__val">{fmtCents(p.priceCents)}</span>
              </div>
            ))}
            <div className="receipt__row">
              <span className="receipt__key">Transaction</span>
              {txnId !== '—' ? (
                <CopyableHash value={txnId} className="receipt__val receipt__val--mono" />
              ) : (
                <span className="receipt__val receipt__val--mono">{txnId}</span>
              )}
            </div>
            {budgetCents > 0 && (
              <div className="receipt__total">
                Total: {fmtCents(spentCents)} of {fmtCents(budgetCents)} mandate quota used
                {!allPaid && ' (partial)'}
              </div>
            )}
          </div>

          {compliance.length > 0 && (
            <div className="receipt__section">
              <div className="receipt__label">Authorization</div>
              {compliance.map((c) => (
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
          )}
        </div>
      )}
    </div>
  );
}
