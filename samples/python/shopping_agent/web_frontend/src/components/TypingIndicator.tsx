/** Three-dot bouncing typing indicator (pure CSS animation, see index.scss). */
export default function TypingIndicator() {
  return (
    <span className="typing" aria-label="Agent is typing">
      <span className="typing__dot" />
      <span className="typing__dot" />
      <span className="typing__dot" />
    </span>
  );
}
