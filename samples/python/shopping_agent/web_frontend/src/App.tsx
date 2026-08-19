import { useRef, useEffect, useState } from 'react';
import { ShoppingBag, ArrowDown, Moon, Sun } from 'lucide-react';
import { useChat } from './hooks/useChat';
import { useTheme } from './hooks/useTheme';
import MessageBubble from './components/MessageBubble';
import PurchaseJourney from './components/PurchaseJourney';
import ImmediatePurchaseJourney from './components/ImmediatePurchaseJourney';
import Composer from './components/Composer';
import type { ChatMessage, StopInputRequired } from './types';

/** A multi-item (AUTONOMOUS travel) purchase turn: replays as a paced journey
 *  of per-product messages instead of one aggregated bubble. */
function isMultiItemPurchaseTurn(msg: ChatMessage): boolean {
  return (
    msg.role === 'agent' &&
    (msg.protocolEvents ?? []).filter((e) => e.action === 'intent_product_match').length >= 2
  );
}

/** An IMMEDIATE (human-present) purchase turn: either the mandate-IDV wait
 *  that carries a selected product (Turn A: search → checkout → authorize) or
 *  the completed payment turn (Turn B: credential → paid → receipt). Both
 *  replay as a paced journey matching the AUTONOMOUS visual language.
 *  IMMEDIATE never emits intent_product_match (only the travel matcher does),
 *  which cleanly separates Turn B from an AUTONOMOUS completion. */
function isImmediatePurchaseTurn(msg: ChatMessage): boolean {
  if (msg.role !== 'agent') return false;
  const stop = msg.stopReason;
  const events = msg.protocolEvents ?? [];
  // Turn A: the shopping mandate-IDV wait (selected_product present, no travel).
  const turnA =
    stop?.state === 'input_required' &&
    stop.input_required.type === 'idv' &&
    !!(stop as StopInputRequired).input_required.selected_product;
  // Turn B: the completed payment turn with no travel-match events.
  const turnB =
    stop?.state === 'completed' &&
    events.some((e) => e.action === 'start_payment') &&
    !events.some((e) => e.action === 'intent_product_match');
  return turnA || turnB;
}

/** Derive the stage-aware default request shown in the Composer placeholder
 *  (and sent on Enter with an empty input). Mirrors the backend
 *  orchestrator._infer_next_input_type stages; only the user_input
 *  fallback gets no default. */
function deriveDefaultText(messages: ChatMessage[]): string | undefined {
  const last = messages[messages.length - 1];
  if (!last) return 'bind wallet';
  if (last.role === 'agent' && last.stopReason?.state === 'input_required') {
    const type = last.stopReason.input_required.type;
    if (type === 'idv') return 'confirm';
    if (type === 'enrollment') return 'bind wallet';
    // Purchase intent: differentiate by scenario
    if (type === 'purchase_intent') {
      const scenario = last.stopReason.input_required.scenario;
      // IMMEDIATE: original shopping template
      if (scenario === 'IMMEDIATE') return 'buy earbuds under $150';
      // AUTONOMOUS: travel template (if no travel activity yet)
      if (!hasTravelActivity(messages)) return TRAVEL_TEMPLATE_TEXT;
      return 'buy earbuds under $150';
    }
  }
  // After a completed purchase the round is over; leave the input empty so
  // the user consciously starts the next request.
  if (last.role === 'agent' && last.stopReason?.state === 'completed') {
    return undefined;
  }
  return undefined;
}

/** P0 travel delegation template shown as Composer default after wallet binding.
 *  States the authorization expiry: the AUTONOMOUS mandate lifetime comes from
 *  the user, never from a default. */
const TRAVEL_TEMPLATE_TEXT =
  "I'm planning a 3-day trip from Shanghai to Singapore, leaving on October 1. Please help me book the flights and hotel, with a total budget of no more than $1,500. The authorization is valid until October 10, 2026.";

/** Stage-aware suggestion chips shown in the empty state (click = send). */
function deriveSuggestions(messages: ChatMessage[]): string[] {
  if (messages.length === 0) return ['bind wallet'];
  const last = messages[messages.length - 1];
  if (last?.role === 'agent' && last.stopReason?.state === 'completed') {
    const isTravelPurchase = (last.protocolEvents ?? []).some(
      (e) => e.action === 'intent_product_match',
    );
    if (isTravelPurchase) return [];
    return ['buy earbuds under $150'];
  }
  return [];
}

/** Check if the latest agent turn involves active travel intent (IDV with travel data). */
function hasTravelActivity(messages: ChatMessage[]): boolean {
  // Only check the last agent message — after cancel, the new turn won't have travel_intent
  const last = messages[messages.length - 1];
  return (
    last?.role === 'agent' &&
    last.stopReason?.state === 'input_required' &&
    last.stopReason.input_required.type === 'idv' &&
    !!(last.stopReason as { input_required?: { travel_intent?: unknown } })?.input_required?.travel_intent
  );
}

export default function App() {
  const { messages, isLoading, taskId, sendMessage, retryTurn, beginProcessing, error } = useChat();
  const { theme, toggleTheme } = useTheme();
  // Full protocol event history across turns (receipt order data may live in
  // an earlier turn, e.g. IMMEDIATE checkout before the IDV wait).
  const allProtocolEvents = messages.flatMap((m) => m.protocolEvents ?? []);
  // Travel budget for mandate quota display (from the latest travel_intent stopReason)
  const travelBudget = messages.reduce<number | undefined>((acc, m) => {
    const ti = (m.stopReason as { input_required?: { travel_intent?: { budget_max?: number } } })
      ?.input_required?.travel_intent;
    return ti?.budget_max ?? acc;
  }, undefined);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLElement>(null);
  const atBottomRef = useRef(true);
  // While > Date.now(), scroll events are treated as programmatic (smooth
  // auto-scroll in flight) and must not flip the at-bottom flag.
  const programmaticUntilRef = useRef(0);
  const [showNewPill, setShowNewPill] = useState(false);
  // Demo scenario fetched from the backend (IMMEDIATE | AUTONOMOUS)
  const [scenario, setScenario] = useState<string | null>(null);

  // Fetch active demo scenario on mount (GET /api/config)
  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((d) => setScenario(d.scenario ?? null))
      .catch(() => {/* badge hidden when config unavailable */});
  }, []);

  const isAtBottom = (el: HTMLElement) =>
    el.scrollHeight - el.scrollTop - el.clientHeight < 80;

  // Follow the stream, but yield when the user scrolls up:
  // - user's own message always forces an instant scroll-to-bottom
  // - new events while scrolled up show a "New messages" pill instead
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last?.role === 'user') {
      atBottomRef.current = true;
      setShowNewPill(false);
      chatEndRef.current?.scrollIntoView({ behavior: 'auto' });
      return;
    }
    if (atBottomRef.current) {
      if (!last?.streaming) {
        // Smooth follow: suppress the intermediate scroll frames
        programmaticUntilRef.current = Date.now() + 300;
      }
      chatEndRef.current?.scrollIntoView({
        behavior: last?.streaming ? 'auto' : 'smooth',
      });
    } else {
      setShowNewPill(true);
    }
  }, [messages]);

  // Scroll handling, two lanes:
  // - wheel/touchmove: user-only gestures, always authoritative (never fired
  //   by programmatic scrollIntoView)
  // - scroll: covers keyboard / scrollbar drag, but ignores frames inside the
  //   programmatic smooth-scroll window so auto-follow is not misread
  useEffect(() => {
    const el = chatRef.current;
    if (!el) return;
    const onUserGesture = () => {
      atBottomRef.current = isAtBottom(el);
      if (atBottomRef.current) setShowNewPill(false);
    };
    el.addEventListener('wheel', onUserGesture, { passive: true });
    el.addEventListener('touchmove', onUserGesture, { passive: true });
    return () => {
      el.removeEventListener('wheel', onUserGesture);
      el.removeEventListener('touchmove', onUserGesture);
    };
  }, []);

  const handleScroll = () => {
    const el = chatRef.current;
    if (!el || Date.now() < programmaticUntilRef.current) return;
    atBottomRef.current = isAtBottom(el);
    if (atBottomRef.current) setShowNewPill(false);
  };

  const scrollToBottom = () => {
    atBottomRef.current = true;
    setShowNewPill(false);
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-inner">
          <div className="app__header-left">
            <span className="app__header-icon">
              <ShoppingBag size={16} strokeWidth={2} />
            </span>
            <h1 className="app__header-title">AMP Shopping Agent</h1>
            {scenario && (
              <span
                className={`app__scenario-badge app__scenario-badge--${scenario.toLowerCase()}`}
                title={scenario === 'IMMEDIATE' ? 'Direct Payment (Human-Present)' : 'Delegated Payment (Human-Not-Present)'}
              >
                <span className="app__scenario-dot" />
                {scenario === 'IMMEDIATE' ? 'Direct Payment (Human-Present)' : 'Delegated Payment (Human-Not-Present)'}
              </span>
            )}
          </div>
          <div className="app__header-right">
            <button
              className="app__theme-toggle"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              title={theme === 'light' ? 'Dark mode' : 'Light mode'}
            >
              {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
            </button>
            <div
              className={`app__header-status ${
                isLoading ? 'app__header-status--busy' : ''
              }`}
            >
              <span
                className={`app__status-dot ${
                  isLoading ? 'app__status-dot--busy' : ''
                }`}
              />
              {isLoading ? 'Working' : 'Online'}
            </div>
          </div>
        </div>
      </header>

      <main
        className="app__chat"
        ref={chatRef}
        onScroll={handleScroll}
        role="log"
        aria-live="polite"
        aria-label="Conversation"
      >
        <div className="app__chat-inner">
          {messages.length === 0 && (
            <div className="empty">
              <div className="empty__icon">
                <ShoppingBag size={34} strokeWidth={1.8} />
              </div>
              <h2 className="empty__title">Shop with your agent</h2>
              <p className="empty__desc">
                Bind your wallet once, then just say what you want to buy —
                the agent takes care of checkout and payment for you.
              </p>
              {deriveSuggestions(messages).length > 0 && (
                <div className="empty__chips">
                  {deriveSuggestions(messages).map((s) => (
                    <button
                      key={s}
                      className="empty__chip"
                      onClick={() => sendMessage(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {messages.map((msg, i) =>
            isMultiItemPurchaseTurn(msg) ? (
              <PurchaseJourney
                key={msg.id}
                msg={msg}
                allEvents={allProtocolEvents}
                budgetMax={travelBudget}
              />
            ) : isImmediatePurchaseTurn(msg) ? (
              <ImmediatePurchaseJourney
                key={msg.id}
                msg={msg}
                allEvents={allProtocolEvents}
                onSend={sendMessage}
                taskId={taskId}
                isLatest={i === messages.length - 1}
                onProcessing={beginProcessing}
              />
            ) : (
              <MessageBubble
                key={msg.id}
                msg={msg}
                onSend={sendMessage}
                taskId={taskId}
                isLatest={i === messages.length - 1}
                onProcessing={beginProcessing}
                onRetry={
                  msg.role === 'agent' && msg.stopReason?.state === 'failed'
                    ? retryTurn
                    : undefined
                }
                allEvents={allProtocolEvents}
              />
            ),
          )}
          <div ref={chatEndRef} />
        </div>
      </main>

      {showNewPill && (
        <button className="app__new-messages" onClick={scrollToBottom}>
          <ArrowDown size={14} />
          New messages
        </button>
      )}

      {error && <div className="app__error">{error}</div>}

      <Composer
        disabled={isLoading}
        defaultText={deriveDefaultText(messages)}
        onSend={sendMessage}
      />
    </div>
  );
}
