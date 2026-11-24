// ─── Type Definitions ───

export type GraphViewMode = "graph" | "timeline" | "evidence";
export type CaseSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type CaseStatus = "OPEN" | "INVESTIGATING" | "ACTION_PROPOSED" | "ACTION_EXECUTED" | "DISMISSED";
export type CaseType = "PAYMENT_SHORTFALL" | "DUPLICATE_PAYMENT" | "MARKETPLACE_VARIANCE" | "BROKEN_PROMISE" | "UNRECORDED_GIFT";
export type PromiseStatus = "KEPT" | "BROKEN" | "AT_RISK" | "PENDING" | "UNRECORDED";
export type PromiseType = "DELIVERY_DATE" | "FREE_GIFT" | "DISCOUNT" | "CUSTOMIZATION" | "REPLACEMENT";
export type ActionStatus = "PENDING" | "APPROVED" | "REJECTED" | "DRAFT";
export type ReceiptDecision = "APPROVED" | "REJECTED";
export type PaymentMatchStatus = "MATCHED" | "PARTIAL" | "UNMATCHED" | "DUPLICATE_CANDIDATE";

export interface DashboardSummary {
  uncollected_balance: number;
  marketplace_variance: number;
  broken_promises: number;
  pending_approvals: number;
  unmatched_payments: number;
  total_open_cases: number;
  cases_needing_attention: number;
}

export interface UrgentCase {
  id: string;
  title: string;
  headline: string;
  severity: CaseSeverity;
  case_type: CaseType;
  discrepancy_amount: number;
  order_number?: string;
}

export interface CaseListItem {
  id: string;
  title: string;
  headline: string;
  severity: CaseSeverity;
  status: CaseStatus;
  case_type: CaseType;
  customer_name: string;
  discrepancy_amount: number;
  order_number?: string;
  created_at: string;
  next_action?: string;
}

export interface EvidenceItem {
  id: string;
  title?: string;
  evidence_type: string;
  source_table: string;
  payload: Record<string, unknown>;
  collected_at: string;
}

export interface TimelineEvent {
  id: string;
  event: string;
  timestamp: string;
  actor: string;
  detail?: string;
}

export interface PendingAction {
  id: string;
  action_type: string;
  action_summary: string;
  status: ActionStatus;
  approval_required: boolean;
  reversibility: "IRREVERSIBLE" | "REVERSIBLE" | "CONDITIONAL";
  payload: {
    recipient?: string;
    recipient_name?: string;
    channel?: string;
    body?: string;
    amount?: number;
    payment_link?: string;
    payment_link_expires_at?: string;
    payment_link_id?: string;
    reversible?: boolean;
    evidence_ids?: string[];
    [key: string]: unknown;
  };
}

export interface RecommendedAction {
  title: string;
  description: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  expected_outcome: string;
  auto_executable: boolean;
}

export interface CaseDetail {
  id: string;
  title: string;
  headline: string;
  explanation: string;
  severity: CaseSeverity;
  status: CaseStatus;
  case_type: CaseType;
  customer_name: string;
  customer_phone?: string;
  order_number?: string;
  order_amount?: number;
  delivery_status?: string;
  payment_status?: string;
  discrepancy_amount: number;
  created_at: string;
  timeline: TimelineEvent[];
  evidence_items: EvidenceItem[];
  findings: string[];
  variance_breakdown?: VarianceStep[];
  pending_actions: PendingAction[];
  receipts: ReceiptItem[];
  promises?: Promise[];
  recommended_action?: RecommendedAction;
}

export interface VarianceStep {
  step: string;
  amount: number;
  type: "gross" | "deduction" | "subtotal" | "actual" | "residual";
}

export interface DeductionExplanation {
  category: string;
  rateOrRule: string;
  baseAmount: number;
  deductedAmount: number;
  explanation: string;
  status: "VERIFIED" | "DISCREPANCY" | "PENALTY";
}

export interface PaymentTransaction {
  id: string;
  date: string;
  utr: string;
  sender?: string;
  description: string;
  amount: number;
  status: PaymentMatchStatus;
  matched_order?: string;
  bank_account?: string;
  reconciliation_note?: string;
}

export interface SettlementData {
  settlement_id: string;
  platform: string;
  period: string;
  order_count: number;
  gross_sales: number;
  expected_amount: number;
  received_amount: number;
  total_deductions: number;
  unexplained_residual: number;
  has_unexplained_variance: boolean;
  settlement_date: string;
  waterfall: VarianceStep[];
  deduction_explanations: DeductionExplanation[];
}

export interface MoneyReconciliation {
  summary: {
    total_credits: number;
    total_amount_received: number;
    expected_amount: number;
    matched_credits: number;
    partial_credits: number;
    unmatched_credits: number;
    duplicate_candidates: number;
  };
  expected_vs_received: {
    expected: number;
    received: number;
    variance: number;
  };
  transactions: PaymentTransaction[];
}

export interface Promise {
  id: string;
  promise_type: PromiseType;
  promise_details: string;
  customer_name: string;
  order_number?: string;
  status: PromiseStatus;
  target_date: string;
  speaker: string;
  raw_message_snippet: string;
  confidence_score: number;
  evidence_source: string;
  linked_case_id?: string;
  created_at: string;
  fulfillment_gap?: string;
}

export interface ReceiptItem {
  id: string;
  timestamp: string;
  decision: ReceiptDecision;
  actor: string;
  case_id: string;
  case_title: string;
  action_type: string;
  evidence_used: string[];
  receipt_hash: string;
  execution_result?: {
    status: string;
    short_url?: string;
    razorpay_link_id?: string;
    channel?: string;
    recipient?: string;
    details?: string;
    [key: string]: unknown;
  };
}
