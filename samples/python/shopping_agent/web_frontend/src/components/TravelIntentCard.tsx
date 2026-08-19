import { useState } from 'react';
import { Plane, Hotel, Calendar, LoaderCircle, MapPin, Wallet, Clock } from 'lucide-react';
import type { TravelIntentData } from '../types';

/** Card lifecycle: idle → confirming (IDV in progress) → confirmed (PASS). */
type CardPhase = 'idle' | 'confirming' | 'confirmed';

interface Props {
  intent: TravelIntentData;
  taskId?: string | null;
  onSend: (text: string) => void;
  disabled?: boolean;
  onProcessing?: (label: string) => void;
}

const SERVICE_ICONS: Record<string, typeof Plane> = {
  flight: Plane,
  hotel: Hotel,
};

/**
 * Travel intent authorization card (mandate IDV stage).
 * Displays structured travel details; Confirm = complete mandate IDV (ARCHITECTURE.md step 6).
 */
export default function TravelIntentCard({ intent, taskId, onSend, disabled, onProcessing }: Props) {
  const [phase, setPhase] = useState<CardPhase>('idle');
  const formattedDate = new Date(intent.departure_date + 'T00:00:00').toLocaleDateString(
    'en-US',
    { month: 'long', day: 'numeric', year: 'numeric' },
  );
  // Authorization window stated by the user: the mandate (and the wallet's L2)
  // expires exactly then, so it is shown alongside the budget.
  const formattedExpiry = intent.expiry_time
    ? new Date(intent.expiry_time).toLocaleString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  const handleConfirm = async () => {
    setPhase('confirming');
    onProcessing?.('Verifying identity & authorizing your travel intent...');
    // Confirm = complete mandate IDV (ARCHITECTURE.md step 6: user authorizes intent)
    let ok = false;
    try {
      const res = await fetch('/api/idv/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskId: taskId }),
      });
      ok = res.ok;
    } catch { /* best-effort */ }
    // Trigger next Agent turn (inquiry_mandate_session → search → checkout → payment)
    onSend('confirm');
    if (ok) setPhase('confirmed');
  };

  const handleCancel = () => {
    onSend('cancel travel');
  };

  return (
    <div className="travel-card">
      <div className="travel-card__header">
        <MapPin size={16} />
        <span>Travel Delegation</span>
      </div>

      <div className="travel-card__route">
        <span className="travel-card__city">{intent.origin}</span>
        <span className="travel-card__arrow">→</span>
        <span className="travel-card__city">{intent.destination}</span>
      </div>

      <div className="travel-card__details">
        <div className="travel-card__row">
          <Calendar size={14} />
          <span>{formattedDate} · {intent.duration_days} days</span>
        </div>
        <div className="travel-card__row">
          <Wallet size={14} />
          <span>Budget: ${intent.budget_max.toLocaleString()} {intent.currency}</span>
        </div>
        {formattedExpiry && (
          <div className="travel-card__row">
            <Clock size={14} />
            <span>Authorization valid until {formattedExpiry}</span>
          </div>
        )}
        <div className="travel-card__row">
          {intent.services.map((svc) => {
            const Icon = SERVICE_ICONS[svc] ?? Plane;
            return (
              <span key={svc} className="travel-card__service">
                <Icon size={14} />
                {svc}
              </span>
            );
          })}
        </div>
      </div>

      <div className="travel-card__actions">
        {phase === 'confirming' ? (
          <button className="travel-card__btn travel-card__btn--confirm" disabled>
            <LoaderCircle size={14} className="icon-spin" />
            Verifying...
          </button>
        ) : phase === 'confirmed' ? (
          <span className="travel-card__processing">Approved ✓</span>
        ) : (
          <>
            <button className="travel-card__btn travel-card__btn--confirm" onClick={handleConfirm} disabled={disabled}>
              Verify to approve
            </button>
            <button className="travel-card__btn travel-card__btn--cancel" onClick={handleCancel} disabled={disabled}>
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}
