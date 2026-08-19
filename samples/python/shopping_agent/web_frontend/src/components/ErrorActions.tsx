import { RotateCcw } from 'lucide-react';

interface Props {
  /** Raw error text from the failed stop event. */
  error: string;
  /** Send a message (same entry as Composer / EmptyState chips). */
  onSend: (text: string) => void;
  /** Re-run the failed turn silently (agent re-executes, no user message). */
  onRetry?: () => void;
}

/**
 * Extract actionable suggestions from a backend parse-failure message.
 * e.g. "Cannot parse intent ... Supported: bind wallet / find me XX / confirm"
 * → ["bind wallet", "find me sneakers", "confirm"]
 * The "XX" placeholder is concretized to a demo-friendly example.
 */
function parseSuggestions(error: string): string[] {
  const match = error.match(/Supported:\s*(.+)$/i);
  if (!match) return [];
  return match[1]
    .split('/')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => s.replace(/XX/gi, 'sneakers'));
}

/**
 * Recovery path for a failed turn:
 * - intent parse failure → clickable suggestion chips (error becomes guidance)
 * - network / runtime failure → Retry button re-running the agent silently
 */
export default function ErrorActions({ error, onSend, onRetry }: Props) {
  const suggestions = parseSuggestions(error);

  if (suggestions.length > 0) {
    return (
      <div className="error-actions">
        <div className="error-actions__hint">Try one of these:</div>
        <div className="error-actions__chips">
          {suggestions.map((s) => (
            <button
              key={s}
              className="error-actions__chip"
              onClick={() => onSend(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (onRetry) {
    return (
      <div className="error-actions">
        <button className="error-actions__retry" onClick={onRetry}>
          <RotateCcw size={13} />
          Retry
        </button>
      </div>
    );
  }

  return null;
}
