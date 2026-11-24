"use client";

import * as React from "react";
import { useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  TrendingDown,
  ArrowRight,
  Clock,
  ShieldAlert,
  CreditCard,
  Building,
  Filter,
  FileQuestion,
  ChevronDown,
  ChevronRight,
  Search,
} from "lucide-react";
import { useMoneyReconciliation, useSettlements } from "@/lib/api";
import { useMoneyStore } from "@/lib/store";
import { formatINR, formatDate, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import type { PaymentMatchStatus } from "@/lib/types";

export default function MoneyPage() {
  const { activeTab, setActiveTab } = useMoneyStore();
  const {
    data: reconData,
    isLoading: reconLoading,
    isError: reconError,
    error: rError,
    refetch: refetchRecon,
  } = useMoneyReconciliation();

  const {
    data: settlements,
    isLoading: setLoading,
    isError: setError,
    error: sError,
    refetch: refetchSet,
  } = useSettlements();

  const [transactionFilter, setTransactionFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedTxnId, setExpandedTxnId] = useState<string | null>("txn_002");

  if (reconLoading || setLoading) {
    return <LoadingState message="Checking your bank payments and marketplace payouts…" />;
  }

  if (reconError || setError) {
    return (
      <ErrorState
        title="Unable to load payment records"
        message={rError?.message || sError?.message}
        onRetry={() => {
          refetchRecon();
          refetchSet();
        }}
      />
    );
  }

  const settlement = settlements?.[0];
  const summary = reconData?.summary;
  const expectedVsReceived = reconData?.expected_vs_received;
  const transactions = reconData?.transactions || [];

  // Filter transactions
  const filteredTransactions = transactions.filter((t) => {
    const matchesFilter =
      transactionFilter === "ALL" ||
      (transactionFilter === "UNMATCHED" && t.status === "UNMATCHED") ||
      (transactionFilter === "PARTIAL" && t.status === "PARTIAL") ||
      (transactionFilter === "DUPLICATE" && t.status === "DUPLICATE_CANDIDATE") ||
      (transactionFilter === "MATCHED" && t.status === "MATCHED");

    const matchesSearch =
      !searchQuery ||
      t.utr.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.sender && t.sender.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (t.matched_order && t.matched_order.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesFilter && matchesSearch;
  });

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-6 select-none animate-fade-in text-[#F4F6FF] pb-20 lg:pb-8">
      {/* 1. Header & Workspace Mode Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#252F49]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#27D99A]" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#A0AAC4]">
              Store Finances · HDFC & Meesho
            </span>
          </div>
          <h1 className="text-xl lg:text-2xl font-bold tracking-tight text-[#F4F6FF]">
            Money & Payouts
          </h1>
          <p className="text-xs text-[#A0AAC4] mt-0.5">
            Clear tracking of money received in your bank, customer shortfalls, and marketplace fee deductions.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-[#101629] border border-[#252F49] rounded-lg p-1 self-start sm:self-auto">
          <button
            onClick={() => setActiveTab("settlements")}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer",
              activeTab === "settlements"
                ? "bg-[#1A2440] text-[#F4F6FF] shadow-sm"
                : "text-[#707D9E] hover:text-[#F4F6FF]"
            )}
          >
            Marketplace Payouts
          </button>
          <button
            onClick={() => setActiveTab("reconciliation")}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer",
              activeTab === "reconciliation"
                ? "bg-[#1A2440] text-[#F4F6FF] shadow-sm"
                : "text-[#707D9E] hover:text-[#F4F6FF]"
            )}
          >
            Bank & UPI Payments ({transactions.length})
          </button>
        </div>
      </div>

      {/* 2. Top Summary Section (Plain Business Terms) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#707D9E] block mb-1">
            Money Received
          </span>
          <div className="font-mono text-xl font-bold text-[#27D99A]">
            {formatINR(expectedVsReceived?.received || 185000)}
          </div>
          <p className="text-[10px] text-[#A0AAC4] mt-1 font-mono">
            Expected: {formatINR(expectedVsReceived?.expected || 192000)}
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#707D9E] block mb-1">
            Still Owed to You
          </span>
          <div className="font-mono text-xl font-bold text-[#FF6977]">
            ₹1,250.00
          </div>
          <p className="text-[10px] text-[#707D9E] mt-1">Priya Sharma balance</p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#707D9E] block mb-1">
            Money Doesn&apos;t Match
          </span>
          <div className="font-mono text-xl font-bold text-[#FFB547]">
            {formatINR(settlement?.unexplained_residual || 850)}
          </div>
          <p className="text-[10px] text-[#FFB547] mt-1 font-medium">Meesho unexplained gap</p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#707D9E] block mb-1">
            Needs Order Match
          </span>
          <div className="font-mono text-xl font-bold text-[#8065FF]">
            {summary?.unmatched_credits || 1} Deposit
          </div>
          <p className="text-[10px] text-[#707D9E] mt-1">₹2,500 waiting for order link</p>
        </div>
      </div>

      {/* 3. Main Workspace: Tab 1 — Marketplace Settlement Waterfall */}
      {activeTab === "settlements" && settlement && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Step-down Remittance Waterfall */}
            <div className="lg:col-span-2 p-5 rounded-xl bg-[#101629] border border-[#252F49] space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#252F49]">
                <div>
                  <h2 className="text-sm font-bold text-[#F4F6FF]">
                    {settlement.platform} Payout Summary ({settlement.period})
                  </h2>
                  <p className="text-[11px] text-[#A0AAC4] mt-0.5">
                    Settlement ID: <span className="font-mono text-[#8065FF]">{settlement.settlement_id}</span> · {settlement.order_count} Orders remitted
                  </p>
                </div>
                <Badge variant="risk">₹850 Discrepancy Found</Badge>
              </div>

              {/* Waterfall Steps */}
              <div className="space-y-2 text-xs">
                {settlement.waterfall.map((step, idx) => {
                  const isResidual = step.type === "residual";
                  const isGross = step.type === "gross";
                  const isSubtotal = step.type === "subtotal";
                  const isActual = step.type === "actual";

                  return (
                    <div
                      key={idx}
                      className={cn(
                        "p-3 rounded-lg flex items-center justify-between font-mono",
                        isResidual
                          ? "bg-[#FF6977]/15 border border-[#FF6977]/40 text-[#FF6977]"
                          : isSubtotal
                          ? "bg-[#151D32] border border-[#252F49] text-[#F4F6FF] font-bold"
                          : isActual
                          ? "bg-[#27D99A]/15 border border-[#27D99A]/40 text-[#27D99A] font-bold"
                          : isGross
                          ? "bg-[#151D32]/80 border border-[#252F49] text-[#F4F6FF]"
                          : "bg-[#080B14] border border-[#252F49]/60 text-[#A0AAC4]"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-[#707D9E] w-4">{idx + 1}</span>
                        <span className="font-sans font-medium text-xs text-[#F4F6FF]">
                          {step.step}
                        </span>
                      </div>
                      <span className="font-bold">
                        {step.amount < 0 ? `- ${formatINR(Math.abs(step.amount))}` : formatINR(step.amount)}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Residual Callout */}
              <div className="p-3.5 rounded-lg bg-[#FF6977]/10 border border-[#FF6977]/30 text-xs text-[#A0AAC4] space-y-1">
                <span className="font-semibold text-[#FF6977] block">
                  Why this money doesn&apos;t match:
                </span>
                <p className="leading-relaxed text-[11px]">
                  Based on agreed rates (15% platform commission and shipping weight fees), your expected bank payout was ₹34,465. But Meesho deposited only ₹33,615 to your HDFC account. The remaining ₹850 has no fee explanation or return claim.
                </p>
                <div className="pt-2">
                  <Link href="/tasks?selected=case_003">
                    <Button size="sm" className="bg-[#8065FF] hover:bg-[#6E50FF] text-white text-xs h-7 px-3">
                      <span>View Task for ₹850 Discrepancy</span>
                      <ArrowRight className="w-3 h-3 ml-1.5" />
                    </Button>
                  </Link>
                </div>
              </div>
            </div>

            {/* Right 1 Col: Contractual Fee Schedule Verification */}
            <div className="p-5 rounded-xl bg-[#101629] border border-[#252F49] space-y-4 text-xs">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#A0AAC4] pb-2 border-b border-[#252F49]">
                Fee & Deduction Breakdown
              </h2>
              <div className="space-y-3">
                {settlement.deduction_explanations.map((ded, i) => (
                  <div key={i} className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#F4F6FF]">{ded.category}</span>
                      <span className="font-mono font-bold text-[#FF6977]">
                        - {formatINR(ded.deductedAmount)}
                      </span>
                    </div>
                    <div className="text-[10px] text-[#29D8C5] font-mono">{ded.rateOrRule}</div>
                    <p className="text-[11px] text-[#A0AAC4] leading-relaxed">{ded.explanation}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. Main Workspace: Tab 2 — Bank & UPI Credits Table (Expandable Rows) */}
      {activeTab === "reconciliation" && (
        <div className="space-y-4">
          {/* Controls: Search & Match Filter */}
          <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-3.5 h-3.5 text-[#707D9E] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search UTR, sender, order #..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-8 pl-8 pr-3 bg-[#151D32] border border-[#252F49] rounded-md text-xs text-[#F4F6FF] placeholder-[#707D9E] focus:outline-none focus:border-[#8065FF]"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-semibold text-[#707D9E] uppercase tracking-wider mr-1">
                Filter:
              </span>
              {[
                { id: "ALL", label: "All" },
                { id: "UNMATCHED", label: "Needs Match" },
                { id: "PARTIAL", label: "Shortfalls" },
                { id: "MATCHED", label: "Matched" },
              ].map((st) => (
                <button
                  key={st.id}
                  onClick={() => setTransactionFilter(st.id)}
                  className={cn(
                    "px-2.5 py-1 rounded text-[11px] font-semibold transition-colors cursor-pointer",
                    transactionFilter === st.id
                      ? "bg-[#8065FF] text-white"
                      : "bg-[#151D32] text-[#A0AAC4] hover:text-[#F4F6FF] border border-[#252F49]"
                  )}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>

          {/* Transactions List */}
          <div className="rounded-xl border border-[#252F49] bg-[#101629] overflow-hidden">
            <div className="divide-y divide-[#252F49]">
              {filteredTransactions.map((txn) => {
                const isExpanded = expandedTxnId === txn.id;

                return (
                  <div key={txn.id} className="transition-colors hover:bg-[#151D32]/50">
                    {/* Primary Row Header */}
                    <div
                      onClick={() => setExpandedTxnId(isExpanded ? null : txn.id)}
                      className="p-3.5 flex items-center justify-between gap-4 cursor-pointer text-xs"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-[#707D9E]">
                          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-semibold text-[#F4F6FF]">{txn.utr}</span>
                            <MatchBadge status={txn.status} />
                          </div>
                          <p className="text-[11px] text-[#A0AAC4] mt-0.5">
                            {txn.sender ? `${txn.sender} · ` : ""}{txn.description}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 text-right">
                        <div>
                          <span className="font-mono text-sm font-bold text-[#F4F6FF] block">
                            {formatINR(txn.amount)}
                          </span>
                          <span className="text-[10px] font-mono text-[#707D9E] block">
                            {txn.date}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Expandable Inspector Detail */}
                    {isExpanded && (
                      <div className="p-4 bg-[#080B14] border-t border-[#252F49] text-xs space-y-3 animate-slide-up">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-1">
                            <span className="text-[10px] font-semibold text-[#707D9E] uppercase">Associated Order</span>
                            <div className="font-mono font-semibold text-[#F4F6FF]">
                              {txn.matched_order || "No Linked Order"}
                            </div>
                            <p className="text-[10px] text-[#A0AAC4]">Bank account: {txn.bank_account || "HDFC Bank"}</p>
                          </div>

                          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-1">
                            <span className="text-[10px] font-semibold text-[#707D9E] uppercase">Matching Method</span>
                            <div className="text-[#27D99A] font-medium">
                              {txn.status === "MATCHED" ? "Verified UTR Match" : txn.status === "PARTIAL" ? "Partial Value Match" : "Unmatched Bank Credit"}
                            </div>
                            <p className="text-[10px] text-[#A0AAC4]">Cross-referenced with bank statement</p>
                          </div>

                          <div className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] space-y-1">
                            <span className="text-[10px] font-semibold text-[#707D9E] uppercase">Status Note</span>
                            <p className="text-[11px] text-[#A0AAC4] leading-relaxed">
                              {txn.reconciliation_note || "Transaction requires manual seller review or payment link settlement."}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MatchBadge({ status }: { status: PaymentMatchStatus }) {
  switch (status) {
    case "MATCHED":
      return <Badge variant="success">Matched to Order</Badge>;
    case "PARTIAL":
      return <Badge variant="risk">Shortfall</Badge>;
    case "UNMATCHED":
      return <Badge variant="warning">Needs Order Match</Badge>;
    case "DUPLICATE_CANDIDATE":
      return <Badge variant="secondary">Possible Duplicate</Badge>;
  }
}
