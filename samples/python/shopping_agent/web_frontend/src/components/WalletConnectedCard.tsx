import { Check } from 'lucide-react';
import WalletMark from './WalletMark';

interface WalletConnectedCardProps {
  /** Wallet user login id returned by CP /queryPaymentMethodList (e.g. "user-demo"). */
  userLoginId?: string;
}

/**
 * "Logged-in" wallet badge rendered inside the agent bubble of the turn where
 * wallet binding completed (the login indicator): Alipay HK mark + name +
 * connected state. Shown once, right after binding succeeds.
 */
export default function WalletConnectedCard({ userLoginId }: WalletConnectedCardProps) {
  return (
    <div className="wallet-card">
      <WalletMark size={32} />
      <div className="wallet-card__body">
        <div className="wallet-card__name">Alipay HK</div>
        <div className="wallet-card__status">
          {userLoginId ? `${userLoginId} · Linked` : 'Linked successfully'}
        </div>
      </div>
      <span className="wallet-card__check">
        <Check size={14} />
      </span>
    </div>
  );
}
