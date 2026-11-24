"use client";

import React, { useState, useMemo } from "react";
import {
  Package,
  FileText,
  CreditCard,
  Handshake,
  AlertTriangle,
  CheckCircle2,
  Clock,
  HelpCircle,
  Truck,
  TrendingDown,
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { CaseDetail, GraphViewMode } from "@/lib/types";

export type NodeStateType = "VERIFIED" | "POTENTIAL" | "MISSING" | "DISPUTED" | "PENDING" | "UNVERIFIABLE";
export type EntityType = "ORDER" | "INVOICE" | "PROMISE" | "PAYMENT" | "VARIANCE" | "DELIVERY" | "SETTLEMENT" | "DEDUCTION" | "CASE";

export interface GraphNodeData {
  id: string;
  type: EntityType;
  title: string;
  subtitle: string;
  value?: string;
  state: NodeStateType;
  meta: Record<string, any>;
  x?: number;
  y?: number;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  label?: string;
  state: NodeStateType;
}

interface DependencyGraphProps {
  caseDetail: CaseDetail;
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNodeData) => void;
  viewMode?: GraphViewMode;
  onViewModeChange?: (mode: GraphViewMode) => void;
}

const STATE_CONFIG: Record<NodeStateType, { label: string; border: string; bg: string; text: string; dot: string }> = {
  VERIFIED: {
    label: "Verified",
    border: "border-[#29D8C5]/50 hover:border-[#29D8C5]",
    bg: "bg-[#101629]",
    text: "text-[#29D8C5]",
    dot: "bg-[#29D8C5]",
  },
  POTENTIAL: {
    label: "Potential Match",
    border: "border-[#8065FF]/50 hover:border-[#8065FF]",
    bg: "bg-[#101629]",
    text: "text-[#8065FF]",
    dot: "bg-[#8065FF]",
  },
  MISSING: {
    label: "Missing Record",
    border: "border-[#FFB547]/50 hover:border-[#FFB547]",
    bg: "bg-[#101629]",
    text: "text-[#FFB547]",
    dot: "bg-[#FFB547]",
  },
  DISPUTED: {
    label: "Disputed Gap",
    border: "border-[#FF6977]/60 hover:border-[#FF6977]",
    bg: "bg-[#101629]",
    text: "text-[#FF6977]",
    dot: "bg-[#FF6977]",
  },
  PENDING: {
    label: "Awaiting Action",
    border: "border-[#5B7CFA]/50 hover:border-[#5B7CFA]",
    bg: "bg-[#101629]",
    text: "text-[#5B7CFA]",
    dot: "bg-[#5B7CFA]",
  },
  UNVERIFIABLE: {
    label: "Unconfirmed",
    border: "border-[#707D9E]/40 hover:border-[#707D9E]",
    bg: "bg-[#101629]",
    text: "text-[#707D9E]",
    dot: "bg-[#707D9E]",
  },
};

export function DependencyGraph({
  caseDetail,
  selectedNodeId,
  onSelectNode,
  viewMode = "graph",
  onViewModeChange = () => {},
}: DependencyGraphProps) {
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  // Build deterministic nodes and edges based on case structure
  const { nodes, edges } = useMemo(() => {
    const isMarketplace = caseDetail.case_type === "MARKETPLACE_VARIANCE";
    const nodeList: GraphNodeData[] = [];
    const edgeList: GraphEdgeData[] = [];

    if (isMarketplace) {
      // Marketplace Remittance Graph Layout
      nodeList.push({
        id: "node_order_group",
        type: "ORDER",
        title: "Platform Orders (60)",
        subtitle: "Gross Sales Value",
        value: "₹48,500.00",
        state: "VERIFIED",
        meta: {
          period: "01 Oct 2026 – 15 Oct 2026",
          platform: "Meesho Marketplace",
          verified_orders: 60,
          delivered: 58,
          rto_returns: 2,
        },
        x: 40,
        y: 110,
      });

      nodeList.push({
        id: "node_settlement_report",
        type: "SETTLEMENT",
        title: "Settlement Report",
        subtitle: "MEESHO-SETTLE-OCT2026",
        value: "₹34,465.00 Expected",
        state: "VERIFIED",
        meta: {
          report_id: "MEESHO-SETTLE-OCT2026",
          issued_at: "2026-10-18",
          total_lines: 60,
          remittance_period: "Bi-weekly payout",
        },
        x: 270,
        y: 40,
      });

      nodeList.push({
        id: "node_deductions",
        type: "DEDUCTION",
        title: "Contractual Deductions",
        subtitle: "Commission, Logistics, GST",
        value: "- ₹14,035.00",
        state: "VERIFIED",
        meta: {
          commission: "₹7,275.00 (15%)",
          shipping_logistics: "₹4,850.00",
          rto_penalties: "₹1,200.00",
          taxes_tcs_tds: "₹710.00",
        },
        x: 270,
        y: 180,
      });

      nodeList.push({
        id: "node_bank_credit",
        type: "PAYMENT",
        title: "Bank Remittance Deposit",
        subtitle: "HDFC A/C ••4012 (UTR98124)",
        value: "₹33,615.00 Actual",
        state: "VERIFIED",
        meta: {
          bank_utr: "UTR981247012B",
          received_date: "2026-10-19",
          status: "MATCHED_CREDIT",
          matched_amount: 33615.0,
        },
        x: 510,
        y: 40,
      });

      nodeList.push({
        id: "node_residual_variance",
        type: "VARIANCE",
        title: "Unexplained Residual",
        subtitle: "Unsubstantiated Payout Gap",
        value: "₹850.00 Gap",
        state: "DISPUTED",
        meta: {
          calculated_net: "₹34,465.00",
          actual_received: "₹33,615.00",
          discrepancy: "₹850.00",
          classification: "UNEXPLAINED_RESIDUAL",
          evidence_note: "No matching invoice, penalty clause, or RTO adjustment in settlement lines.",
        },
        x: 510,
        y: 180,
      });

      nodeList.push({
        id: "node_active_case",
        type: "CASE",
        title: "Dispute Pack Prepared",
        subtitle: "TKT_MEESHO_SETTLE_OCT",
        value: "Dispute Action",
        state: "PENDING",
        meta: {
          case_id: caseDetail.id,
          target: "Meesho Merchant Support",
          recommended_action: "Submit evidence dossier claiming ₹850 residual recovery",
          approval_required: true,
        },
        x: 740,
        y: 110,
      });

      // Connections
      edgeList.push({ id: "e1", source: "node_order_group", target: "node_settlement_report", label: "Remitted Under", state: "VERIFIED" });
      edgeList.push({ id: "e2", source: "node_order_group", target: "node_deductions", label: "Fee Schedule", state: "VERIFIED" });
      edgeList.push({ id: "e3", source: "node_settlement_report", target: "node_bank_credit", label: "Paid to Bank", state: "VERIFIED" });
      edgeList.push({ id: "e4", source: "node_deductions", target: "node_residual_variance", label: "Residual", state: "DISPUTED" });
      edgeList.push({ id: "e5", source: "node_bank_credit", target: "node_residual_variance", label: "Shortfall", state: "DISPUTED" });
      edgeList.push({ id: "e6", source: "node_residual_variance", target: "node_active_case", label: "Awaiting Action", state: "PENDING" });
    } else {
      // Direct Customer Order Flow (Shortfall, Broken Promise, Duplicate)
      const ordNum = caseDetail.order_number || "ORD-2024-1042";
      const discAmt = caseDetail.discrepancy_amount || 1200;

      nodeList.push({
        id: "node_order",
        type: "ORDER",
        title: `Order ${ordNum}`,
        subtitle: caseDetail.customer_name || "Customer Order",
        value: `₹${(caseDetail.order_amount || 3500).toLocaleString()}`,
        state: "VERIFIED",
        meta: {
          order_id: ordNum,
          customer: caseDetail.customer_name,
          phone: caseDetail.customer_phone || "+91 98765 43210",
          channel: "WhatsApp / Direct",
          order_amount: caseDetail.order_amount || 3500,
        },
        x: 40,
        y: 110,
      });

      nodeList.push({
        id: "node_invoice",
        type: "INVOICE",
        title: "Tax Invoice",
        subtitle: `INV-${ordNum.replace("ORD-", "")}`,
        value: "Tax Compliant",
        state: "VERIFIED",
        meta: {
          invoice_number: `INV-${ordNum.replace("ORD-", "")}`,
          gst_treatment: "Intrastate B2C",
          items: "Handloom Banarasi Saree",
        },
        x: 270,
        y: 35,
      });

      nodeList.push({
        id: "node_payment",
        type: "PAYMENT",
        title: "Bank Credit (UPI)",
        subtitle: "HDFC Credit · Ananya Sharma",
        value: `₹${((caseDetail.order_amount || 3500) - discAmt).toLocaleString()}`,
        state: discAmt > 0 ? "POTENTIAL" : "VERIFIED",
        meta: {
          utr_reference: "UTR20241018UPI001",
          amount: (caseDetail.order_amount || 3500) - discAmt,
          match_type: "PARTIAL_CREDIT",
          sender: caseDetail.customer_name,
        },
        x: 270,
        y: 185,
      });

      nodeList.push({
        id: "node_delivery",
        type: "DELIVERY",
        title: "Courier Proof",
        subtitle: "Delhivery Express (Delivered)",
        value: "Delivered",
        state: caseDetail.case_type === "BROKEN_PROMISE" ? "DISPUTED" : "VERIFIED",
        meta: {
          tracking_number: "DEL987654321",
          delivered_date: "2026-10-21",
          promised_date: "2026-10-17 (Karwa Chauth)",
          status: caseDetail.case_type === "BROKEN_PROMISE" ? "3 Days Late" : "On-Time",
        },
        x: 500,
        y: 35,
      });

      nodeList.push({
        id: "node_shortfall",
        type: "VARIANCE",
        title: caseDetail.case_type === "BROKEN_PROMISE" ? "Broken Commitment" : "Uncollected Balance",
        subtitle: caseDetail.case_type === "BROKEN_PROMISE" ? "Delayed Delivery Promise" : "Customer Shortfall",
        value: discAmt > 0 ? `₹${discAmt.toLocaleString()}` : "Promise Broken",
        state: "DISPUTED",
        meta: {
          discrepancy_amount: discAmt,
          evidence: "Chat commitment vs courier delivery manifest",
          risk_level: "HIGH",
        },
        x: 500,
        y: 185,
      });

      nodeList.push({
        id: "node_case_action",
        type: "CASE",
        title: "Proposed Resolution",
        subtitle: caseDetail.case_type === "BROKEN_PROMISE" ? "Apology & Goodwill Voucher" : "Razorpay Payment Link",
        value: "Awaiting Approval",
        state: "PENDING",
        meta: {
          case_id: caseDetail.id,
          target_recipient: caseDetail.customer_phone || "+91 98765 43210",
          action_type: caseDetail.case_type === "BROKEN_PROMISE" ? "SEND_APOLOGY_EMAIL" : "RAZORPAY_PAYMENT_LINK",
          policy_gate: "Requires human approval",
        },
        x: 730,
        y: 110,
      });

      edgeList.push({ id: "e1", source: "node_order", target: "node_invoice", label: "Billed", state: "VERIFIED" });
      edgeList.push({ id: "e2", source: "node_order", target: "node_payment", label: "Partial Paid", state: "POTENTIAL" });
      edgeList.push({ id: "e3", source: "node_order", target: "node_delivery", label: "Fulfillment", state: "VERIFIED" });
      edgeList.push({ id: "e4", source: "node_payment", target: "node_shortfall", label: "Residual", state: "DISPUTED" });
      edgeList.push({ id: "e5", source: "node_delivery", target: "node_shortfall", label: "Verified Gap", state: "DISPUTED" });
      edgeList.push({ id: "e6", source: "node_shortfall", target: "node_case_action", label: "Resolution", state: "PENDING" });
    }

    return { nodes: nodeList, edges: edgeList };
  }, [caseDetail]);

  const getNodeIcon = (type: EntityType) => {
    switch (type) {
      case "ORDER":
        return <Package className="w-3.5 h-3.5" />;
      case "INVOICE":
        return <FileText className="w-3.5 h-3.5" />;
      case "PAYMENT":
        return <CreditCard className="w-3.5 h-3.5" />;
      case "PROMISE":
        return <Handshake className="w-3.5 h-3.5" />;
      case "DELIVERY":
        return <Truck className="w-3.5 h-3.5" />;
      case "VARIANCE":
        return <TrendingDown className="w-3.5 h-3.5" />;
      case "SETTLEMENT":
        return <Layers className="w-3.5 h-3.5" />;
      case "DEDUCTION":
        return <AlertTriangle className="w-3.5 h-3.5" />;
      case "CASE":
        return <ShieldAlert className="w-3.5 h-3.5" />;
      default:
        return <HelpCircle className="w-3.5 h-3.5" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#080B14] border-r border-[#252F49] overflow-hidden select-none">
      {/* Graph Toolbar / View Controller */}
      <div className="h-10 px-4 border-b border-[#252F49] bg-[#0B1020] flex items-center justify-between text-xs shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-semibold text-[#A0AAC4] uppercase tracking-wider flex items-center gap-1.5 mr-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#8065FF]" />
            Evidence Map
          </span>

          {/* View Modes */}
          <div className="flex items-center bg-[#101629] border border-[#252F49] rounded-md p-0.5" role="tablist">
            <button
              onClick={() => onViewModeChange("graph")}
              className={cn(
                "px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer",
                viewMode === "graph"
                  ? "bg-[#1A2440] text-[#F4F6FF] font-semibold shadow-sm"
                  : "text-[#707D9E] hover:text-[#F4F6FF]"
              )}
            >
              Graph View
            </button>
            <button
              onClick={() => onViewModeChange("timeline")}
              className={cn(
                "px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer",
                viewMode === "timeline"
                  ? "bg-[#1A2440] text-[#F4F6FF] font-semibold shadow-sm"
                  : "text-[#707D9E] hover:text-[#F4F6FF]"
              )}
            >
              Timeline
            </button>
            <button
              onClick={() => onViewModeChange("evidence")}
              className={cn(
                "px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer",
                viewMode === "evidence"
                  ? "bg-[#1A2440] text-[#F4F6FF] font-semibold shadow-sm"
                  : "text-[#707D9E] hover:text-[#F4F6FF]"
              )}
            >
              Evidence List ({caseDetail.evidence_items.length})
            </button>
          </div>
        </div>

        {/* Zoom & Fit Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoomLevel((z) => Math.min(z + 0.1, 1.4))}
            className="w-6 h-6 rounded flex items-center justify-center text-[#707D9E] hover:text-[#F4F6FF] hover:bg-[#151D32] transition-colors cursor-pointer"
            title="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoomLevel((z) => Math.max(z - 0.1, 0.7))}
            className="w-6 h-6 rounded flex items-center justify-center text-[#707D9E] hover:text-[#F4F6FF] hover:bg-[#151D32] transition-colors cursor-pointer"
            title="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoomLevel(1)}
            className="w-6 h-6 rounded flex items-center justify-center text-[#707D9E] hover:text-[#F4F6FF] hover:bg-[#151D32] transition-colors cursor-pointer"
            title="Reset zoom"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
          <span className="text-[10px] font-mono text-[#707D9E] ml-1.5">
            {Math.round(zoomLevel * 100)}%
          </span>
        </div>
      </div>

      {/* Main View Area */}
      {viewMode === "graph" && (
        <div className="flex-1 relative overflow-auto p-6 bg-[#080B14]">
          {/* Subtle static grid lines background */}
          <div
            className="absolute inset-0 pointer-events-none opacity-[0.04]"
            style={{
              backgroundImage: `linear-gradient(#252F49 1px, transparent 1px), linear-gradient(90deg, #252F49 1px, transparent 1px)`,
              backgroundSize: "24px 24px",
            }}
          />

          <div
            className="relative min-w-[950px] min-h-[300px] transition-transform duration-100 origin-top-left"
            style={{ transform: `scale(${zoomLevel})` }}
          >
            {/* SVG Connecting Edges */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none z-0"
              style={{ overflow: "visible" }}
            >
              <defs>
                <marker
                  id="arrow-verified"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#29D8C5" opacity="0.8" />
                </marker>
                <marker
                  id="arrow-disputed"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#FF6977" opacity="0.9" />
                </marker>
                <marker
                  id="arrow-pending"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#8065FF" opacity="0.8" />
                </marker>
              </defs>

              {edges.map((edge) => {
                const sourceNode = nodes.find((n) => n.id === edge.source);
                const targetNode = nodes.find((n) => n.id === edge.target);
                if (!sourceNode || !targetNode) return null;

                const sx = (sourceNode.x || 0) + 180;
                const sy = (sourceNode.y || 0) + 38;
                const tx = targetNode.x || 0;
                const ty = (targetNode.y || 0) + 38;
                const mx = (sx + tx) / 2;

                const pathData = `M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}`;

                const strokeColor =
                  edge.state === "DISPUTED"
                    ? "#FF6977"
                    : edge.state === "PENDING"
                    ? "#8065FF"
                    : edge.state === "POTENTIAL"
                    ? "#5B7CFA"
                    : "#29D8C5";

                const markerId =
                  edge.state === "DISPUTED"
                    ? "url(#arrow-disputed)"
                    : edge.state === "PENDING"
                    ? "url(#arrow-pending)"
                    : "url(#arrow-verified)";

                return (
                  <g key={edge.id}>
                    <path
                      d={pathData}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={1.75}
                      strokeDasharray={edge.state === "POTENTIAL" ? "4 4" : undefined}
                      opacity={0.75}
                      markerEnd={markerId}
                    />
                    {edge.label && (
                      <text
                        x={mx}
                        y={(sy + ty) / 2 - 4}
                        textAnchor="middle"
                        fill="#707D9E"
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="600"
                        className="select-none bg-[#080B14]"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Interactive Nodes */}
            {nodes.map((node) => {
              const cfg = STATE_CONFIG[node.state] || STATE_CONFIG.VERIFIED;
              const isSelected = selectedNodeId === node.id;

              return (
                <div
                  key={node.id}
                  onClick={() => onSelectNode(node)}
                  style={{
                    position: "absolute",
                    left: `${node.x || 0}px`,
                    top: `${node.y || 0}px`,
                    width: "190px",
                  }}
                  className={cn(
                    "p-3 rounded-xl border bg-[#101629] transition-all cursor-pointer shadow-[0_4px_16px_rgba(0,0,0,0.5)] z-10 group",
                    cfg.border,
                    isSelected
                      ? "ring-2 ring-[#8065FF] border-[#8065FF] shadow-[0_0_20px_rgba(128,101,255,0.35)] scale-[1.02]"
                      : "hover:scale-[1.01]"
                  )}
                >
                  <div className="flex items-center justify-between gap-1 mb-1.5">
                    <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#A0AAC4]">
                      <span className={cn("p-1 rounded-md bg-[#151D32]", cfg.text)}>
                        {getNodeIcon(node.type)}
                      </span>
                      <span>{node.type}</span>
                    </span>
                    <span
                      className={cn(
                        "w-1.5 h-1.5 rounded-full shrink-0",
                        cfg.dot
                      )}
                      title={cfg.label}
                    />
                  </div>

                  <h4 className="text-xs font-semibold text-[#F4F6FF] truncate">
                    {node.title}
                  </h4>
                  <p className="text-[10px] text-[#707D9E] truncate mt-0.5">
                    {node.subtitle}
                  </p>

                  {node.value && (
                    <div className="mt-2 pt-1.5 border-t border-[#252F49]/70 flex items-center justify-between text-[11px]">
                      <span className="text-[9px] uppercase font-mono text-[#707D9E]">
                        {cfg.label}
                      </span>
                      <span className={cn("font-mono font-bold text-xs", cfg.text)}>
                        {node.value}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Alternative View Mode: Timeline */}
      {viewMode === "timeline" && (
        <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-[#080B14]">
          <h4 className="text-xs font-semibold text-[#F4F6FF] mb-2 uppercase tracking-wider">
            Chronological Evidence Sequence
          </h4>
          {caseDetail.timeline && caseDetail.timeline.length > 0 ? (
            caseDetail.timeline.map((evt, idx) => (
              <div
                key={evt.id || idx}
                className="flex items-start gap-3 p-3 rounded-lg bg-[#101629] border border-[#252F49] text-xs"
              >
                <div className="w-6 h-6 rounded-full bg-[#1A2440] border border-[#252F49] text-[#8065FF] flex items-center justify-center shrink-0 text-[10px] font-bold">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="font-semibold text-[#F4F6FF]">{evt.event}</span>
                    <span className="font-mono text-[10px] text-[#707D9E]">{evt.timestamp}</span>
                  </div>
                  <p className="text-[11px] text-[#A0AAC4]">{evt.detail || `Recorded by ${evt.actor}`}</p>
                </div>
              </div>
            ))
          ) : (
            <div className="text-xs text-[#707D9E]">No timeline events recorded.</div>
          )}
        </div>
      )}

      {/* Alternative View Mode: Evidence List */}
      {viewMode === "evidence" && (
        <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-[#080B14]">
          <h4 className="text-xs font-semibold text-[#F4F6FF] mb-2 uppercase tracking-wider">
            Linked Evidence Artifacts ({caseDetail.evidence_items.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {caseDetail.evidence_items.map((ev) => (
              <div
                key={ev.id}
                className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49] space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-[#29D8C5] bg-[#29D8C5]/10 px-1.5 py-0.5 rounded border border-[#29D8C5]/20">
                    {ev.evidence_type}
                  </span>
                  <span className="font-mono text-[9px] text-[#707D9E]">{ev.id}</span>
                </div>
                <div className="text-[11px] text-[#A0AAC4] font-medium">
                  Source: <span className="font-mono text-[#F4F6FF]">{ev.source_table}</span>
                </div>
                <pre className="p-2 rounded bg-[#080B14] border border-[#252F49]/80 text-[10px] font-mono text-[#A0AAC4] overflow-x-auto max-h-32">
                  {JSON.stringify(ev.payload, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
