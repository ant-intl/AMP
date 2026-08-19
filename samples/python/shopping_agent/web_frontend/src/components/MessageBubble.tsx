import type { ChatMessage, ProtocolEvent, StopInputRequired, TravelIntentData, ProductData } from '../types';
import { Sparkles, User } from 'lucide-react';
import StepProgress from './StepProgress';
import TypingIndicator from './TypingIndicator';
import ReceiptCard from './ReceiptCard';
import ErrorActions from './ErrorActions';
import IdvConfirmCard from './IdvConfirmCard';
import WalletConnectedCard from './WalletConnectedCard';
import TravelIntentCard from './TravelIntentCard';
import ShoppingIntentCard from './ShoppingIntentCard';

interface Props {
  msg: ChatMessage;
  /** Shared send entry (Composer / EmptyState chips / error recovery). */
  onSend?: (text: string) => void;
  /** Current task ID for API calls (IDV confirm). */
  taskId?: string | null;
  /** Whether this is the latest message (only latest cards are interactive). */
  isLatest?: boolean;
  /** Called when a card Confirm is clicked (App shows new streaming bubble). */
  onProcessing?: (label: string) => void;
  /** Re-run the failed turn silently (agent re-executes, no user message). */
  onRetry?: () => void;
  /** Protocol events from ALL turns (receipt order data may predate this turn). */
  allEvents?: ProtocolEvent[];
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * One chat row: avatar + meta (role, timestamp) + bubble.
 * Agent bubbles embed the step progress (top); the typing indicator shows
 * while waiting for the first event, and a blinking cursor marks an
 * in-progress typewriter reveal.
 */
export default function MessageBubble({ msg, onSend, taskId, isLatest, onProcessing, onRetry, allEvents }: Props) {
  const isUser = msg.role === 'user';
  const hasSteps = (msg.steps?.length ?? 0) > 0;
  const showTyping = !isUser && !msg.text && !hasSteps;
  const turnLive = !isUser && !msg.stopReason;
  const idvPending =
    !isUser &&
    msg.stopReason?.state === 'input_required' &&
    msg.stopReason.input_required.type === 'idv';
  // The mandate IDV wait always shares its turn with create_mandate_session;
  // an enrollment wait never sees mandate events (linear state machine).
  const idvStage = (msg.protocolEvents ?? []).some(
    (e) => e.action === 'create_mandate_session' || e.action === 'return_mandate_session_id',
  )
    ? 'mandate'
    : 'enrollment';
  // Mandate IDV + travel intent present → show TravelIntentCard (Confirm = IDV)
  const travelIdvPending =
    idvPending &&
    idvStage === 'mandate' &&
    !!(msg.stopReason as StopInputRequired)?.input_required?.travel_intent;
  // Mandate IDV + a shopping authorization scope present → ShoppingIntentCard.
  // IMMEDIATE carries the searched product (selected_product); AUTONOMOUS carries
  // only the intent + budget (shopping_intent — mandate precedes search, so there
  // is no product data yet).
  const inputReq = (msg.stopReason as StopInputRequired)?.input_required;
  const shoppingIdvPending =
    idvPending &&
    idvStage === 'mandate' &&
    (!!inputReq?.selected_product || !!inputReq?.shopping_intent);
  // The turn where wallet binding completed emits return_payment_method_list
  // (the IMMEDIATE binding turn ends input_required=purchase_intent, not
  // completed — so gate on the event only). Render the connected badge there.
  const bindEvent = !isUser
    ? (msg.protocolEvents ?? []).find((e) => e.action === 'return_payment_method_list')
    : undefined;
  const bindCompleted = !!bindEvent;

  return (
    <div className={`message ${isUser ? 'message--user' : 'message--agent'}`}>
      <div
        className={`message__avatar ${
          isUser ? 'message__avatar--user' : 'message__avatar--agent'
        }`}
        aria-hidden="true"
      >
        {isUser ? <User size={18} /> : <Sparkles size={18} />}
      </div>
      <div className="message__body">
        <div className="message__meta">
          <span className="message__role">{isUser ? 'You' : 'Agent'}</span>
          <span className="message__time">{formatTime(msg.timestamp)}</span>
        </div>
        <div className="message__bubble">
          {hasSteps && <StepProgress steps={msg.steps!} live={turnLive} />}
          {showTyping ? (
            <TypingIndicator />
          ) : (
            <span className={`message__text${msg.streaming && msg.text && !hasSteps && !msg.stopReason ? ' working-text' : ''}`}>
              {msg.text}
              {msg.streaming && !(msg.text && !hasSteps && !msg.stopReason) && <span className="message__cursor" />}
            </span>
          )}
          {idvPending && !travelIdvPending && !shoppingIdvPending && onSend && (
            <IdvConfirmCard stage={idvStage} onProcessing={onProcessing} onConfirm={async () => {
              // Call backend /idv/confirm → MPP completeIdv (5s biometric sim)
              let ok = false;
              try {
                const res = await fetch('/api/idv/confirm', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ taskId: taskId }),
                });
                ok = res.ok;
              } catch { /* best-effort */ }
              // Trigger next Agent turn (query_payment_method_list / inquiry)
              onSend('confirm');
              return ok;
            }} />
          )}
          {travelIdvPending && onSend && (
            <TravelIntentCard
              intent={(msg.stopReason as StopInputRequired).input_required.travel_intent!}
              taskId={taskId}
              onSend={onSend}
              onProcessing={onProcessing}
            />
          )}
          {shoppingIdvPending && onSend && (
            <ShoppingIntentCard
              intent={inputReq?.shopping_intent ?? (inputReq?.selected_product as { name?: string })?.name ?? ''}
              amount={inputReq?.intent_amount ?? inputReq?.checkout_amount}
              taskId={taskId}
              onSend={onSend}
              onProcessing={onProcessing}
            />
          )}
          {bindCompleted && (
            <WalletConnectedCard
              userLoginId={bindEvent?.response?.user_login_id as string | undefined}
            />
          )}
          {msg.stopReason?.state === 'completed' && (
            <ReceiptCard msg={msg} allEvents={allEvents ?? []} />
          )}
          {msg.stopReason?.state === 'failed' && onSend && (
            <ErrorActions
              error={msg.stopReason.failed?.error ?? ''}
              onSend={onSend}
              onRetry={onRetry}
            />
          )}
        </div>
      </div>
    </div>
  );
}
