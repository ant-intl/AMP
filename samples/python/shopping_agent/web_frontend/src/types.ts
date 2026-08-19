/** SSE event types from the backend. */

// --- Action events ---

export interface ActionStartedEvent {
  type: 'action_started';
  action: string;
  step: number;
}

export interface ActionCompletedEvent {
  type: 'action_completed';
  action: string;
  step: number;
}

export interface ProtocolEvent {
  type: 'protocol_event';
  phase: string;
  from: string;
  to: string;
  action: string;
  request: Record<string, unknown>;
  response: Record<string, unknown>;
}

// --- Stop events ---

export interface StopInputRequired {
  state: 'input_required';
  input_required: {
    type: string;
    message: string;
    travel_intent?: TravelIntentData;
    selected_product?: ProductData;
    checkout_amount?: number;
    /** AUTONOMOUS shopping intent (mandate precedes search: intent + budget only, no product data). */
    shopping_intent?: string;
    intent_amount?: number;
    scenario?: string;
  };
}

/** Product info from search results (for ShoppingIntentCard).
 *  Mirrors the merchant catalog payload — camelCase since the API naming migration. */
export interface ProductData {
  id?: string;
  name: string;
  description?: string;
  price: number;
  currency: string;
  imageUrl?: string;
}

/** Structured travel delegation intent (P0). */
export interface TravelIntentData {
  origin: string;
  destination: string;
  departure_date: string;
  duration_days: number;
  budget_max: number;
  currency: string;
  services: string[];
  /** User-stated authorization expiry (ISO 8601 UTC) bounding the mandate. */
  expiry_time?: string;
}

export interface StopCompleted {
  state: 'completed';
  completed: {
    transaction_id?: string;
    total_steps: number;
    next?: string;       // "purchase_again" when multi-purchase is available
    message?: string;    // hint for next action
  };
}

export interface StopFailed {
  state: 'failed';
  failed: {
    error: string;
  };
}

export type StopEvent = StopInputRequired | StopCompleted | StopFailed;

// --- SSE message union ---

export type SSEMessage =
  | ActionStartedEvent
  | ActionCompletedEvent
  | ProtocolEvent
  | StopEvent;

// --- Chat message model ---

export type MessageRole = 'user' | 'agent' | 'system';

/** One orchestration action step within an agent turn. */
export interface ActionStep {
  name: string;
  status: 'running' | 'done';
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  actions?: string[];       // action names executed in this turn (legacy, superseded by steps)
  steps?: ActionStep[];     // per-turn action steps with live status
  protocolEvents?: ProtocolEvent[]; // protocol chain events
  stopReason?: StopEvent;
  streaming?: boolean;      // true while typewriter reveal is in progress
  timestamp: number;
}
