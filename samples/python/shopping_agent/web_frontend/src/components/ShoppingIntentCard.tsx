import { useState } from 'react';
import { LoaderCircle, ShieldCheck } from 'lucide-react';

/** Card lifecycle: idle → confirming (IDV in progress) → confirmed (PASS). */
type CardPhase = 'idle' | 'confirming' | 'confirmed';

interface Props {
  /** The user's raw shopping intent (mandate intent_raw), shown as the authorization scope. */
  intent: string;
  /** Authorized amount (USD dollars) bound to this mandate. */
  amount?: number;
  taskId?: string | null;
  onSend: (text: string) => void;
  disabled?: boolean;
  onProcessing?: (label: string) => void;
}

/**
 * Mandate authorization card (IMMEDIATE mode mandate IDV stage).
 *
 * Shows the authorization scope the user is about to grant — their shopping
 * intent plus the amount cap carried by this mandate — rather than product
 * details (the product card is rendered separately above). Confirm = complete
 * the mandate IDV (ARCHITECTURE.md human-present step 6).
 */
export default function ShoppingIntentCard({ intent, amount, taskId, onSend, disabled, onProcessing }: Props) {
  const [phase, setPhase] = useState<CardPhase>('idle');

  const handleConfirm = async () => {
    setPhase('confirming');
    onProcessing?.('Verifying identity & authorizing your purchase...');
    // Confirm = complete mandate IDV (user authorizes the purchase intent)
    let ok = false;
    try {
      const res = await fetch('/api/idv/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskId: taskId }),
      });
      ok = res.ok;
    } catch { /* best-effort */ }
    // Trigger next Agent turn (inquiry → applyCredential → startPayment)
    onSend('confirm');
    if (ok) setPhase('confirmed');
  };

  const handleCancel = () => {
    onSend('cancel travel');
  };

  return (
    <div className="shopping-card">
      <div className="shopping-card__header">
        <ShieldCheck size={16} />
        <span>Purchase Authorization</span>
      </div>

      <div className="shopping-card__mandate">
        {intent && <div className="shopping-card__intent">&ldquo;{intent}&rdquo;</div>}
        {amount !== undefined && (
          <div className="shopping-card__amount">Authorize up to ${amount.toFixed(2)}</div>
        )}
      </div>

      <div className="shopping-card__actions">
        {phase === 'confirming' ? (
          <button className="shopping-card__btn shopping-card__btn--confirm" disabled>
            <LoaderCircle size={14} className="icon-spin" />
            Verifying...
          </button>
        ) : phase === 'confirmed' ? (
          <span className="shopping-card__processing">Approved ✓</span>
        ) : (
          <>
            <button className="shopping-card__btn shopping-card__btn--confirm" onClick={handleConfirm} disabled={disabled}>
              Verify to approve
            </button>
            <button className="shopping-card__btn shopping-card__btn--cancel" onClick={handleCancel} disabled={disabled}>
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}
