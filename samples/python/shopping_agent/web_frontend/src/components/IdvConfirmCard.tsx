import { useState } from 'react';
import { LoaderCircle } from 'lucide-react';
import WalletMark from './WalletMark';

/** Which protocol stage is waiting for IDV confirmation. */
type IdvStage = 'enrollment' | 'mandate';

/** Card lifecycle: idle → confirming (IDV in progress) → confirmed (PASS). */
type CardPhase = 'idle' | 'confirming' | 'confirmed';

interface Props {
  /** Called when the user clicks the confirm button; resolves true when IDV passed. */
  onConfirm: () => Promise<boolean>;
  /** Stage-aware guidance: wallet linking (enrollment) vs intent authorization (mandate). */
  stage?: IdvStage;
  /** Whether the card is non-interactive (historical message). */
  disabled?: boolean;
  /** Called immediately on click so App can show a new streaming bubble. */
  onProcessing?: (label: string) => void;
}

const STAGE_DESC: Record<IdvStage, string> = {
  enrollment: 'Open your wallet to verify your identity and link Alipay HK.',
  mandate: 'Open your wallet to verify your identity and authorize your purchase intent.',
};

const STAGE_WORKING: Record<IdvStage, string> = {
  enrollment: 'Verifying identity & linking your wallet...',
  mandate: 'Verifying identity & authorizing your intent...',
};

/**
 * Identity verification card shown inside an agent bubble while the flow
 * waits at an IDV node (ARCHITECTURE.md: wallet binding / mandate grant).
 * Shows the integrated wallet's brand mark (Alipay HK) so the user knows
 * which wallet is asking for confirmation. The flow resumes only after the
 * user explicitly confirms here.
 */
export default function IdvConfirmCard({ onConfirm, stage = 'enrollment', disabled, onProcessing }: Props) {
  const [phase, setPhase] = useState<CardPhase>('idle');

  const handleClick = async () => {
    setPhase('confirming');
    onProcessing?.(STAGE_WORKING[stage]);
    const ok = await onConfirm();
    if (ok) setPhase('confirmed');
  };

  return (
    <div className="idv-card">
      <div className="idv-card__icon">
        <WalletMark size={38} />
      </div>
      <div className="idv-card__body">
        <div className="idv-card__title">Identity verification</div>
        <div className="idv-card__desc">{STAGE_DESC[stage]}</div>
      </div>
      {phase === 'idle' && (
        <button className="idv-card__confirm" onClick={handleClick} disabled={disabled}>
          Open wallet to authorize
        </button>
      )}
      {phase === 'confirming' && (
        <button className="idv-card__confirm" disabled>
          <LoaderCircle size={14} className="icon-spin" />
          Authorizing...
        </button>
      )}
      {phase === 'confirmed' && (
        <span className="idv-card__done">Authorized ✓</span>
      )}
    </div>
  );
}
