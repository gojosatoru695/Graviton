"use client";

import React from "react";
import {
  FileText,
  CreditCard,
  Package,
  Handshake,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Lock,
  Layers,
  Sparkles,
  Info,
} from "lucide-react";
import { cn, formatINR, formatDateTime, formatFriendlyId } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { CaseDetail, PendingAction } from "@/lib/types";
import type { GraphNodeData } from "./dependency-graph";

interface EvidenceInspectorProps {
  caseDetail: CaseDetail;
  selectedNode: GraphNodeData | null;
  onOpenApproval: (action: PendingAction) => void;
  onQuickDecision?: (actionId: string, decision: "APPROVED" | "REJECTED") => void;
  isProcessing?: boolean;
}

export function EvidenceInspector({
  caseDetail,
  selectedNode,
  onOpenApproval,
  onQuickDecision,
  isProcessing = false,
}: EvidenceInspectorProps) {
  // If no node is selected, provide the default selected case overview
  const pendingAction = caseDetail.pending_actions?.[0];

  return (
    <div className="flex flex-col h-full bg-[#0B1020] text-xs overflow-y-auto select-none">
      {/* Inspector Header */}
      <div className="p-4 border-b border-[#252F49] bg-[#101629] shrink-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-semibold text-[#8065FF] uppercase tracking-wider flex items-center gap-1.5 font-mono">
            <Info className="w-3.5 h-3.5" />
            {selectedNode ? `${selectedNode.type} Inspector` : "Case Overview"}
          </span>
          <span className="text-[10px] font-mono text-[#707D9E]">
            {selectedNode ? selectedNode.id : formatFriendlyId(caseDetail.id, "Case")}
          </span>
        </div>
        <h3 className="text-sm font-semibold text-[#F4F6FF] truncate">
          {selectedNode ? selectedNode.title : caseDetail.title}
        </h3>
        <p className="text-[11px] text-[#A0AAC4] mt-0.5 leading-relaxed">
          {selectedNode ? selectedNode.subtitle : caseDetail.headline}
        </p>
      </div>

      {/* Dynamic Content based on selected entity */}
      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {selectedNode ? (
          <RenderNodeSpecificInspector node={selectedNode} caseDetail={caseDetail} />
        ) : (
          <RenderDefaultCaseInspector caseDetail={caseDetail} />
        )}
      </div>

      {/* Next Best Action Footer (Mandatory in Inspector) */}
      <div className="p-4 border-t border-[#252F49] bg-[#101629] shrink-0 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold text-[#A0AAC4] uppercase tracking-wider flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-[#29D8C5]" />
            Mandate Clearance
          </span>
          <Badge variant="cyan" className="text-[9px]">
            Policy Checked
          </Badge>
        </div>

        {pendingAction ? (
          <div className="p-3 rounded-lg bg-[#151D32] border border-[#8065FF]/30 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-[11px] font-semibold text-[#F4F6FF]">
                  {pendingAction.action_summary}
                </p>
                <p className="text-[10px] text-[#707D9E] mt-0.5">
                  Target: <span className="font-mono text-[#A0AAC4]">{pendingAction.payload.recipient || pendingAction.payload.recipient_name || "Merchant"}</span>
                </p>
              </div>
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-[#8065FF]/20 text-[#8065FF] shrink-0">
                HITL GATE
              </span>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <Button
                size="sm"
                variant="default"
                onClick={() => onOpenApproval(pendingAction)}
                disabled={isProcessing}
                className="flex-1 h-7 text-xs bg-[#8065FF] hover:bg-[#6E50FF] font-semibold gap-1.5"
              >
                <span>Review & Approve</span>
                <ArrowRight className="w-3 h-3" />
              </Button>
            </div>
          </div>
        ) : (
          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] text-center text-[11px] text-[#A0AAC4]">
            Investigation verified. No pending owner action required at this step.
          </div>
        )}
      </div>
    </div>
  );
}

// ── Node Specific Renderers ──

function RenderNodeSpecificInspector({
  node,
  caseDetail,
}: {
  node: GraphNodeData;
  caseDetail: CaseDetail;
}) {
  const meta = node.meta || {};

  switch (node.type) {
    case "ORDER":
      return (
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-2">
            <div className="text-[11px] font-semibold text-[#F4F6FF]">Order Master Record</div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-[#707D9E] block text-[10px]">Customer:</span>
                <span className="text-[#F4F6FF] font-medium">{meta.customer || caseDetail.customer_name}</span>
              </div>
              <div>
                <span className="text-[#707D9E] block text-[10px]">Order Value:</span>
                <span className="font-mono text-[#F4F6FF] font-bold">
                  {meta.order_amount ? formatINR(meta.order_amount) : node.value}
                </span>
              </div>
              <div>
                <span className="text-[#707D9E] block text-[10px]">Channel:</span>
                <span className="text-[#A0AAC4]">{meta.channel || meta.platform || "Direct"}</span>
              </div>
              <div>
                <span className="text-[#707D9E] block text-[10px]">Contact:</span>
                <span className="font-mono text-[#A0AAC4]">{meta.phone || "+91 98765 43210"}</span>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-1.5">
            <span className="text-[10px] font-semibold text-[#A0AAC4] uppercase">Linked Records</span>
            <ul className="space-y-1 text-[11px] text-[#A0AAC4]">
              <li className="flex items-center gap-1.5 font-mono">
                <CheckCircle2 className="w-3 h-3 text-[#29D8C5]" />
                Tax Invoice INV-2024-1042
              </li>
              <li className="flex items-center gap-1.5 font-mono">
                <CheckCircle2 className="w-3 h-3 text-[#29D8C5]" />
                Delhivery Waybill DEL987654321
              </li>
            </ul>
          </div>
        </div>
      );

    case "PAYMENT":
      return (
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-2">
            <div className="text-[11px] font-semibold text-[#F4F6FF]">Payment Verification</div>
            <div className="space-y-2 text-[11px]">
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Amount Credited:</span>
                <span className="font-mono font-bold text-[#27D99A]">{node.value}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#707D9E]">UTR Reference:</span>
                <span className="font-mono text-[#F4F6FF]">{meta.bank_utr || meta.utr_reference || "UTR20241018UPI001"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Matching Method:</span>
                <span className="text-[#29D8C5] font-medium">{meta.match_type || "Deterministic UTR + Sender Name"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Bank Record:</span>
                <span className="text-[#A0AAC4]">HDFC Bank Statement Line #42</span>
              </div>
            </div>
          </div>
        </div>
      );

    case "VARIANCE":
    case "DEDUCTION":
      return (
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-[#151D32] border border-[#FF6977]/30 space-y-2">
            <div className="text-[11px] font-semibold text-[#FF6977] flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Variance Calculation
            </div>
            <p className="text-[11px] text-[#A0AAC4] leading-relaxed">
              {meta.evidence_note || "A discrepancy exists between contractual fulfillment terms and observed settlement/bank credits."}
            </p>
            <div className="p-2 rounded bg-[#080B14] border border-[#252F49] text-[10px] font-mono space-y-1">
              <div className="flex justify-between text-[#A0AAC4]">
                <span>Confirmed Contract:</span>
                <span className="text-[#F4F6FF]">{meta.calculated_net || "₹3,500.00"}</span>
              </div>
              <div className="flex justify-between text-[#A0AAC4]">
                <span>Actual Deposited:</span>
                <span className="text-[#27D99A]">{meta.actual_received || "₹2,300.00"}</span>
              </div>
              <div className="flex justify-between text-[#FF6977] font-bold pt-1 border-t border-[#252F49]">
                <span>Unexplained Gap:</span>
                <span>{meta.discrepancy || node.value}</span>
              </div>
            </div>
          </div>
        </div>
      );

    case "DELIVERY":
      return (
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-2">
            <div className="text-[11px] font-semibold text-[#F4F6FF]">Fulfillment Evidence</div>
            <div className="space-y-1.5 text-[11px]">
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Courier:</span>
                <span className="text-[#F4F6FF]">Delhivery Express</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Tracking Number:</span>
                <span className="font-mono text-[#F4F6FF]">{meta.tracking_number || "DEL987654321"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Delivered Date:</span>
                <span className="font-mono text-[#FFB547]">{meta.delivered_date || "2026-10-21"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Promised Date:</span>
                <span className="font-mono text-[#29D8C5]">{meta.promised_date || "2026-10-17"}</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-[#252F49]">
                <span className="text-[#707D9E]">Promise Status:</span>
                <span className="font-semibold text-[#FF6977]">{meta.status || "3 Days Late"}</span>
              </div>
            </div>
          </div>
        </div>
      );

    default:
      return (
        <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-2">
          <div className="text-[11px] font-semibold text-[#F4F6FF]">{node.title}</div>
          <p className="text-[11px] text-[#A0AAC4]">{node.subtitle}</p>
          <pre className="p-2 rounded bg-[#080B14] text-[10px] font-mono text-[#A0AAC4] overflow-x-auto">
            {JSON.stringify(meta, null, 2)}
          </pre>
        </div>
      );
  }
}

function RenderDefaultCaseInspector({ caseDetail }: { caseDetail: CaseDetail }) {
  return (
    <div className="space-y-3">
      {/* Investigation Findings */}
      <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-2">
        <span className="text-[10px] font-semibold text-[#8065FF] uppercase tracking-wider">
          Verified Findings ({caseDetail.findings?.length || 0})
        </span>
        <ul className="space-y-2">
          {(caseDetail.findings || [caseDetail.explanation]).map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-[11px] text-[#F4F6FF] leading-relaxed">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#29D8C5] shrink-0 mt-0.5" />
              <span>{f}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Case Facts Summary */}
      <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-2">
        <span className="text-[10px] font-semibold text-[#A0AAC4] uppercase tracking-wider">
          Case Information
        </span>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between">
            <span className="text-[#707D9E]">Discrepancy:</span>
            <span className="font-mono font-bold text-[#FF6977]">
              {caseDetail.discrepancy_amount > 0 ? formatINR(caseDetail.discrepancy_amount) : "Commitment Gap"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#707D9E]">Severity Rating:</span>
            <span className="font-bold text-[#FFB547]">{caseDetail.severity}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#707D9E]">Counterparty:</span>
            <span className="text-[#F4F6FF]">{caseDetail.customer_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#707D9E]">Detected At:</span>
            <span className="font-mono text-[#A0AAC4]">{formatDateTime(caseDetail.created_at)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
