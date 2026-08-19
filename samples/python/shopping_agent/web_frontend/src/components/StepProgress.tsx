import { useState } from 'react';
import { Check, LoaderCircle } from 'lucide-react';
import type { ActionStep } from '../types';

/** Human-friendly labels for action steps (ChatGPT-style progress). */
const ACTION_LABELS: Record<string, string> = {
  add_payment_method: 'Binding wallet...',
  query_payment_method_list: 'Querying payment methods...',
  create_mandate_session: 'Creating authorization session...',
  inquiry_mandate_session: 'Verifying your authorization...',
  search_catalog: 'Searching for matching products...',
  create_checkout: 'Creating checkout...',
  create_l3: 'Preparing payment credentials...',
  apply_credential: 'Applying credential...',
  start_payment: 'Processing payment...',
};

function stepLabel(name: string): string {
  return ACTION_LABELS[name] || name;
}

interface Props {
  steps: ActionStep[];
  /** true while the agent turn is still running (no stop event yet). */
  live: boolean;
}

/**
 * Per-turn action step list: running steps show a spinner, done steps a green
 * check (pop animation). Once the turn settles and all steps are done, the
 * list collapses into a one-line summary that can be re-expanded.
 */
export default function StepProgress({ steps, live }: Props) {
  const [expanded, setExpanded] = useState(false);
  if (steps.length === 0) return null;

  const allDone = steps.every((s) => s.status === 'done');
  const collapsed = !live && allDone && !expanded;

  if (collapsed) {
    return (
      <div className="steps">
        <button className="steps__summary" onClick={() => setExpanded(true)}>
          <span className="steps__icon steps__icon--done">
            <Check size={10} strokeWidth={3} />
          </span>
          {steps.length} {steps.length === 1 ? 'action' : 'actions'} completed
        </button>
      </div>
    );
  }

  return (
    <div className="steps">
      {steps.map((s, i) => (
        <div key={`${s.name}-${i}`} className={`steps__item steps__item--${s.status}`}>
          <span className={`steps__icon steps__icon--${s.status}`}>
            {s.status === 'done' ? (
              <Check size={10} strokeWidth={3} />
            ) : (
              <LoaderCircle size={14} />
            )}
          </span>
          <span className="steps__name">{stepLabel(s.name)}</span>
        </div>
      ))}
      {!live && allDone && expanded && (
        <button className="steps__summary" onClick={() => setExpanded(false)}>
          Collapse
        </button>
      )}
    </div>
  );
}
