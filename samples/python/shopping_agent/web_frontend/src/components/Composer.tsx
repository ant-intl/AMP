import { useRef, useState } from 'react';
import { ArrowUp } from 'lucide-react';

interface Props {
  disabled: boolean;
  /** Stage-aware default request: shown as the placeholder and sent
   *  when the user presses Enter with an empty input. */
  defaultText?: string;
  onSend: (text: string) => void;
}

/** Bottom pill composer: auto-growing multiline textarea + circular send
 *  button (arrow icon). Enter sends, Shift+Enter inserts a newline. */
export default function Composer({ disabled, defaultText, onSend }: Props) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /** Auto-grow to the content height, capped by the CSS max-height (200px). */
  const adjustHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Empty input falls back to the stage-aware default shown in the placeholder.
    const text = input.trim() || (defaultText ?? '');
    if (!text || disabled) return;
    setInput('');
    onSend(text);
    // Collapse the textarea back to one row after sending.
    requestAnimationFrame(() => {
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Enter sends; Shift+Enter falls through to a native newline.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <div className="composer__inner">
        <div className="composer__card">
          <textarea
            ref={textareaRef}
            className="composer__input"
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              adjustHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              disabled ? 'Agent is working…' : (defaultText ?? 'Type a message…')
            }
            disabled={disabled}
            aria-label="Message"
          />
          <button
            className="composer__send"
            type="submit"
            disabled={disabled || (!input.trim() && !defaultText)}
            aria-label="Send message"
          >
            <ArrowUp size={18} strokeWidth={2.2} />
          </button>
        </div>
      </div>
    </form>
  );
}
