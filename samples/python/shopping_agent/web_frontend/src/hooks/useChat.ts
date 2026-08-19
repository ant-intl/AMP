/**
 * useChat — SSE streaming chat hook for AMP Shopping Agent.
 *
 * Flow:
 *   1. POST /api/task → create task, get taskId
 *   2. POST /api/task/{id}/run → SSE stream (action events + stop event)
 *   3. Parse SSE, update messages state (immutable, located by message id)
 *
 * Enhancements:
 *   - steps state machine: action_started pushes a running step,
 *     action_completed flips the matching step to done
 *   - typewriter reveal: stop-event text is rendered progressively
 *     (rAF-driven, ~60 chars/s, capped at 1.5s) with a streaming cursor
 */
import { useState, useCallback, useRef } from 'react';
import type { ChatMessage, SSEMessage, StopEvent, ProtocolEvent } from '../types';

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  taskId: string | null;
  sendMessage: (text: string) => Promise<void>;
  retryTurn: () => Promise<void>;
  beginProcessing: (label: string) => void;
  error: string | null;
}

/** Parse a single SSE line into an event type + data. */
function parseSSELine(raw: string): { event: string; data: string } | null {
  const lines = raw.split('\n');
  let event = '';
  let data = '';
  for (const line of lines) {
    if (line.startsWith('event: ')) event = line.slice(7).trim();
    else if (line.startsWith('data: ')) data = line.slice(6);
  }
  if (!data) return null;
  return { event, data };
}

/** Typewriter pacing: at least 60 chars/s, whole reveal capped at 1.5s. */
const REVEAL_MIN_CPS = 60;
const REVEAL_MAX_MS = 1500;

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const taskIdRef = useRef<string | null>(null);

  /** Immutable update of a single message, located by id (never by index). */
  const patchMessage = useCallback((id: string, patch: (m: ChatMessage) => ChatMessage) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? patch(m) : m)));
  }, []);

  /** Progressively reveal the full text of one message (typewriter effect). */
  const revealText = useCallback(
    (id: string, fullText: string) => {
      const cps = Math.max(REVEAL_MIN_CPS, fullText.length / (REVEAL_MAX_MS / 1000));
      const start = performance.now();
      patchMessage(id, (m) => ({ ...m, streaming: true }));

      const tick = (now: number) => {
        const shown = Math.min(fullText.length, Math.floor(((now - start) / 1000) * cps));
        patchMessage(id, (m) => ({ ...m, text: fullText.slice(0, shown) }));
        if (shown < fullText.length) {
          requestAnimationFrame(tick);
        } else {
          patchMessage(id, (m) => ({ ...m, streaming: false }));
        }
      };
      requestAnimationFrame(tick);
    },
    [patchMessage],
  );

  /** Create a new task session. */
  const createTask = useCallback(async (): Promise<string> => {
    const res = await fetch('/api/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error(`Failed to create task: ${res.status}`);
    const body = await res.json();
    taskIdRef.current = body.taskId;
    setTaskId(body.taskId);
    return body.taskId;
  }, []);

  /** Execute one agent turn over SSE.
   *  - sendMessage: userText provided → adds a user bubble, sends { message }
   *  - retryTurn:   no userText → re-runs the agent on existing state ({ retry:true }),
   *                 producing a fresh agent bubble with NO user message. */
  const executeTurn = useCallback(
    async (body: { message: string; retry?: boolean }, userText?: string) => {
      if (isLoading) return;
      setIsLoading(true);
      setError(null);

      // Drop any pending processing placeholder; add a user bubble only for a
      // genuine user turn (retry re-runs the agent silently, no user message).
      setMessages((prev) => {
        const rest = prev.filter((m) => !m.id.endsWith('-processing'));
        if (userText === undefined) return rest;
        const userMsg: ChatMessage = {
          id: `msg-${Date.now()}-user`,
          role: 'user',
          text: userText,
          timestamp: Date.now(),
        };
        return [...rest, userMsg];
      });

      // Ensure task exists
      let tid = taskIdRef.current;
      if (!tid) {
        try {
          tid = await createTask();
        } catch (e) {
          setError(e instanceof Error ? e.message : 'Failed to create task');
          setIsLoading(false);
          return;
        }
      }

      // Prepare agent message placeholder
      const agentMsg: ChatMessage = {
        id: `msg-${Date.now()}-agent`,
        role: 'agent',
        text: '',
        actions: [],
        steps: [],
        protocolEvents: [],
        timestamp: Date.now(),
      };
      const agentMsgId = agentMsg.id;
      setMessages((prev) => [...prev, agentMsg]);

      try {
        const res = await fetch(`/api/task/${tid}/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          throw new Error(`Server error: ${res.status}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE messages (separated by double newlines)
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || ''; // keep incomplete part

          for (const part of parts) {
            if (!part.trim() || part.startsWith(':')) continue; // skip comments / heartbeats

            const parsed = parseSSELine(part);
            if (!parsed) continue;

            let msg: SSEMessage;
            try {
              msg = JSON.parse(parsed.data);
            } catch {
              continue;
            }

            if ('type' in msg) {
              if (msg.type === 'action_started') {
                patchMessage(agentMsgId, (m) => ({
                  ...m,
                  actions: [...(m.actions || []), msg.action],
                  steps: [...(m.steps || []), { name: msg.action, status: 'running' }],
                }));
              } else if (msg.type === 'action_completed') {
                patchMessage(agentMsgId, (m) => {
                  let flipped = false;
                  const steps = (m.steps || []).map((s) => {
                    if (!flipped && s.name === msg.action && s.status === 'running') {
                      flipped = true;
                      return { ...s, status: 'done' as const };
                    }
                    return s;
                  });
                  return { ...m, steps };
                });
              } else if (msg.type === 'protocol_event') {
                patchMessage(agentMsgId, (m) => ({
                  ...m,
                  protocolEvents: [...(m.protocolEvents || []), msg as ProtocolEvent],
                }));
              }
            } else if ('state' in msg) {
              // Stop event → freeze stopReason, then typewriter-reveal the final text
              const stopEvt = msg as StopEvent;
              let fullText: string;
              if (stopEvt.state === 'input_required') {
                fullText = stopEvt.input_required.message;
              } else if (stopEvt.state === 'completed') {
                fullText =
                  'Payment successful. Your order has been placed and will be delivered soon.';
              } else if (stopEvt.state === 'failed') {
                fullText = `Error: ${stopEvt.failed?.error ?? 'Unknown error'}`;
              } else {
                // deadlocked or any unexpected state — use raw msg to avoid never narrowing
                const raw = msg as unknown as Record<string, unknown>;
                const stateKey = String(raw.state ?? 'unknown');
                const detail = raw[stateKey] as Record<string, unknown> | undefined;
                fullText = `Error: ${detail?.message ?? detail?.error ?? `Unexpected state: ${stateKey}`}`;
              }
              patchMessage(agentMsgId, (m) => ({ ...m, stopReason: stopEvt }));
              revealText(agentMsgId, fullText);
            }
          }
        }
      } catch (e) {
        const errMsg = e instanceof Error ? e.message : 'Unknown error';
        setError(errMsg);
        // Settle the turn with a failed stopReason so step spinners stop
        patchMessage(agentMsgId, (m) => ({
          ...m,
          text: `Error: ${errMsg}`,
          streaming: false,
          stopReason: { state: 'failed', failed: { error: errMsg } },
        }));
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, createTask, patchMessage, revealText],
  );

  /** User-driven turn: adds a user bubble, then runs the agent. */
  const sendMessage = useCallback(
    (text: string) => executeTurn({ message: text }, text),
    [executeTurn],
  );

  /** Retry the last failed turn: agent re-executes on existing state, no user bubble. */
  const retryTurn = useCallback(
    () => executeTurn({ message: '', retry: true }),
    [executeTurn],
  );

  /** Immediately show a new agent bubble with a task-aware status line. */
  const beginProcessing = useCallback((label: string) => {
    const placeholder: ChatMessage = {
      id: `msg-${Date.now()}-processing`,
      role: 'agent',
      text: label,
      actions: [],
      steps: [],
      protocolEvents: [],
      timestamp: Date.now(),
      streaming: true,
    };
    setMessages((prev) => [...prev, placeholder]);
  }, []);

  return { messages, isLoading, taskId, sendMessage, retryTurn, beginProcessing, error };
}
