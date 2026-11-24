"use client";

import * as React from "react";
import { useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  Clock,
  Sparkles,
  Search,
  CheckCircle2,
  FileText,
  RotateCw,
  ShieldCheck,
  Send,
  ExternalLink,
  MessageSquare,
  ChevronRight,
  Eye,
  ShieldAlert,
} from "lucide-react";
import { useDashboard, useRunInvestigation, useCaseDetail, useActionDecision } from "@/lib/api";
import { formatINR, formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LoadingState,
  ErrorState,
  EmptyState,
  SuccessBanner,
} from "@/components/ui/states";
import { ApprovalModal } from "@/components/cases/approval-modal";
import type { PendingAction } from "@/lib/types";

export default function TodayPage() {
  const { data, isLoading, isError, error, refetch } = useDashboard();
  const investigationMutation = useRunInvestigation();
  const actionMutation = useActionDecision();

  // For the recommended next action approval modal
  const { data: featuredCase } = useCaseDetail("case_001");
  const [activeApprovalAction, setActiveApprovalAction] = useState<PendingAction | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const [investigationReport, setInvestigationReport] = useState<{
    scannedRecords: { orders: number; bankCredits: number; whatsappMessages: number; marketplaceSettlements: number };
    findingsCount: number;
    newAnomalies: number;
  } | null>(null);

  const handleRunInvestigation = async () => {
    try {
      const res = await investigationMutation.mutateAsync();
      setInvestigationReport(res);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const handleActionDecision = async (
    actionId: string,
    decision: "APPROVED" | "REJECTED" | "DRAFT",
    reason?: string
  ) => {
    try {
      await actionMutation.mutateAsync({ actionId, decision, rejectionReason: reason });
      setActiveApprovalAction(null);
      setSuccessBanner(
        decision === "APPROVED"
          ? "Payment link created & reminder sent successfully!"
          : decision === "DRAFT"
          ? "Saved as draft"
          : "Action proposal dismissed"
      );
      refetch();
      setTimeout(() => setSuccessBanner(null), 5000);
    } catch (err) {
      console.error(err);
    }
  };

  if (isLoading) return <LoadingState message="Checking your store's status…" />;
  if (isError) return <ErrorState message={error?.message} onRetry={() => refetch()} />;

  const metrics = data?.metrics;
  const urgentCases = data?.urgent_cases || [];

  if (!metrics) return <EmptyState title="No records yet" description="Upload your weekly records to let Jarvis assist you." />;

  // Find the primary pending action if available
  const recommendedAction = featuredCase?.pending_actions?.[0];

  return (
    <div className="p-4 lg:p-6 max-w-5xl mx-auto space-y-6 select-none animate-fade-in pb-20 lg:pb-8">
      {/* 1. Header: Greeting & Quick Scan */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-[#252F49]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#27D99A] animate-pulse" />
            <span className="text-[11px] font-semibold text-[#27D99A] uppercase tracking-wider">
              Jarvis is on duty
            </span>
            <span className="text-[#707D9E]">·</span>
            <span className="text-[11px] text-[#A0AAC4]">Aura Weaves & Jewels</span>
          </div>
          <h1 className="text-xl lg:text-2xl font-bold tracking-tight text-[#F4F6FF]">
            Good morning! Here is what needs you.
          </h1>
        </div>

        <Button
          size="sm"
          onClick={handleRunInvestigation}
          disabled={investigationMutation.isPending}
          className="bg-[#151D32] hover:bg-[#1E2945] text-[#F4F6FF] border border-[#252F49] text-xs h-8 px-3.5 shrink-0 gap-2 cursor-pointer self-start sm:self-auto"
          aria-label="Scan records for issues"
        >
          {investigationMutation.isPending ? (
            <>
              <RotateCw className="w-3.5 h-3.5 animate-spin text-[#8065FF]" aria-hidden="true" />
              <span>Scanning records…</span>
            </>
          ) : (
            <>
              <Search className="w-3.5 h-3.5 text-[#8065FF]" aria-hidden="true" />
              <span>Scan for issues</span>
            </>
          )}
        </Button>
      </div>

      {/* Success Notification Banner */}
      {successBanner && (
        <SuccessBanner message={successBanner} onDismiss={() => setSuccessBanner(null)} />
      )}

      {/* Scan Result Toast */}
      {investigationReport && (
        <div className="bg-[#27D99A]/10 border border-[#27D99A]/30 rounded-xl p-3.5 flex items-start justify-between gap-3 animate-slide-up">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-[#27D99A] shrink-0 mt-0.5" />
            <div className="text-xs">
              <span className="font-semibold text-[#27D99A]">
                Scan complete · All records checked
              </span>
              <p className="text-[11px] text-[#A0AAC4] mt-0.5">
                Checked {investigationReport.scannedRecords.orders} orders, {investigationReport.scannedRecords.bankCredits} bank payments, and {investigationReport.scannedRecords.whatsappMessages} customer messages.
              </p>
            </div>
          </div>
          <button
            onClick={() => setInvestigationReport(null)}
            className="text-[10px] text-[#A0AAC4] hover:text-[#F4F6FF] cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 2. Top Summary: 3 Crucial Figures */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Link
          href="/tasks?filter=PAYMENT_SHORTFALL"
          className="p-4 rounded-xl bg-[#101629] border border-[#252F49] hover:border-[#FF6977]/40 transition-all group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-[#A0AAC4]">
              Still owed to you
            </span>
            <span className="w-2 h-2 rounded-full bg-[#FF6977]" />
          </div>
          <div className="font-mono text-2xl font-bold text-[#FF6977] mt-1.5">
            {formatINR(metrics.uncollected_balance)}
          </div>
          <p className="text-[11px] text-[#707D9E] mt-1 flex items-center justify-between">
            <span>Customer shortfalls</span>
            <span className="text-[#8065FF] group-hover:underline text-[10px]">View &rarr;</span>
          </p>
        </Link>

        <Link
          href="/money"
          className="p-4 rounded-xl bg-[#101629] border border-[#252F49] hover:border-[#FFB547]/40 transition-all group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-[#A0AAC4]">
              Money doesn&apos;t match
            </span>
            <span className="w-2 h-2 rounded-full bg-[#FFB547]" />
          </div>
          <div className="font-mono text-2xl font-bold text-[#FFB547] mt-1.5">
            {formatINR(metrics.marketplace_variance)}
          </div>
          <p className="text-[11px] text-[#707D9E] mt-1 flex items-center justify-between">
            <span>Marketplace payout gap</span>
            <span className="text-[#8065FF] group-hover:underline text-[10px]">View &rarr;</span>
          </p>
        </Link>

        <Link
          href="/tasks?filter=AWAITING_APPROVAL"
          className="p-4 rounded-xl bg-[#101629] border border-[#8065FF]/40 bg-gradient-to-br from-[#101629] to-[#151D32] hover:border-[#8065FF] transition-all group shadow-[0_0_16px_rgba(128,101,255,0.15)]"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#8065FF]">
              Needs your approval
            </span>
            <Badge variant="primary" className="text-[10px] px-1.5 py-0">1 Ready</Badge>
          </div>
          <div className="font-mono text-2xl font-bold text-[#F4F6FF] mt-1.5">
            {metrics.pending_approvals} Action
          </div>
          <p className="text-[11px] text-[#A0AAC4] mt-1 flex items-center justify-between">
            <span>Ready for 1-tap review</span>
            <span className="text-[#8065FF] group-hover:underline text-[10px]">Review &rarr;</span>
          </p>
        </Link>
      </div>

      {/* 3. Recommended Next Action: Highlighted Card */}
      <div className="p-4 rounded-xl bg-gradient-to-br from-[#131B32] to-[#0E1528] border border-[#8065FF]/50 shadow-[0_4px_24px_rgba(128,101,255,0.18)] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-md bg-[#8065FF]/20 text-[#8065FF]">
              <Sparkles className="w-3.5 h-3.5" />
            </span>
            <span className="text-xs font-bold text-[#F4F6FF] uppercase tracking-wider">
              Recommended Next Action
            </span>
          </div>
          <span className="text-[11px] font-semibold text-[#FFB547] bg-[#FFB547]/10 px-2 py-0.5 rounded-full border border-[#FFB547]/20">
            Action Ready
          </span>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-1">
          <div className="space-y-1">
            <h2 className="text-sm font-semibold text-[#F4F6FF]">
              Priya Sharma owes ₹1,250 on Order #0847
            </h2>
            <p className="text-xs text-[#A0AAC4] leading-relaxed max-w-xl">
              Customer made an advance payment of ₹2,250 on 20 Nov, and promised on WhatsApp to clear the remaining balance today. Jarvis prepared a Razorpay payment link and a friendly WhatsApp message.
            </p>
            <div className="flex items-center gap-2 pt-1 text-[11px] text-[#27D99A]">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Verified order & WhatsApp commitment · No money lost</span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {recommendedAction ? (
              <Button
                onClick={() => setActiveApprovalAction(recommendedAction)}
                className="bg-[#8065FF] hover:bg-[#6E50FF] text-white font-semibold text-xs h-9 px-4 shadow-[0_0_16px_rgba(128,101,255,0.4)] cursor-pointer gap-1.5"
              >
                <span>Review & Send Link</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            ) : (
              <Link href="/tasks?selected=case_001">
                <Button
                  className="bg-[#8065FF] hover:bg-[#6E50FF] text-white font-semibold text-xs h-9 px-4 shadow-[0_0_16px_rgba(128,101,255,0.4)] cursor-pointer gap-1.5"
                >
                  <span>Review Details</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            )}
            <Link href="/tasks?selected=case_001">
              <Button
                variant="outline"
                size="sm"
                className="border-[#252F49] text-[#A0AAC4] hover:text-[#F4F6FF] text-xs h-9 px-3"
              >
                Details
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* 4. Three Questions Sections */}
      <div className="space-y-6">
        {/* Section 1: What needs your attention? */}
        <section aria-label="Needs your attention" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#F4F6FF] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#FF6977]" />
              Needs your attention ({urgentCases.length})
            </h2>
            <Link
              href="/tasks"
              className="text-xs text-[#8065FF] hover:underline flex items-center gap-1 font-medium"
            >
              <span>View all tasks</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {urgentCases.map((c) => {
              const isShortfall = c.case_type === "PAYMENT_SHORTFALL";
              const isVariance = c.case_type === "MARKETPLACE_VARIANCE";

              return (
                <Link
                  key={c.id}
                  href={`/tasks?selected=${c.id}`}
                  className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49] hover:border-[#8065FF]/60 hover:bg-[#131A30] transition-all group space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-[#1A2440] text-[#A0AAC4]">
                      {isShortfall
                        ? "Payment Shortfall"
                        : isVariance
                        ? "Money doesn't match"
                        : c.case_type.replace(/_/g, " ")}
                    </span>
                    {c.discrepancy_amount > 0 && (
                      <span className="font-mono text-xs font-bold text-[#FF6977]">
                        {formatINR(c.discrepancy_amount)}
                      </span>
                    )}
                  </div>

                  <div>
                    <h3 className="text-xs font-semibold text-[#F4F6FF] group-hover:text-[#8065FF] transition-colors">
                      {c.title}
                    </h3>
                    <p className="text-[11px] text-[#A0AAC4] line-clamp-2 mt-0.5">
                      {c.headline}
                    </p>
                  </div>

                  <div className="pt-1 border-t border-[#252F49]/50 flex items-center justify-between text-[10px] text-[#707D9E]">
                    <span>Suggested: {isShortfall ? "Send payment link" : "Review deductions"}</span>
                    <span className="text-[#8065FF] font-medium group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                      Open <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

        {/* Section 2: What is Jarvis doing? */}
        <section aria-label="Jarvis is working" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#F4F6FF] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#27D99A] animate-pulse" />
              Jarvis is working in the background
            </h2>
            <span className="text-[11px] text-[#707D9E]">Auto-checking 24/7</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49] space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#F4F6FF]">Bank & UPI Monitor</span>
                <span className="text-[10px] font-medium text-[#27D99A] bg-[#27D99A]/10 px-1.5 py-0.5 rounded">
                  Live
                </span>
              </div>
              <p className="text-[11px] text-[#A0AAC4]">
                Watching HDFC account for incoming UPI credits. Auto-matches order references and customer names.
              </p>
              <p className="text-[10px] text-[#707D9E] pt-1">Last checked: 4 mins ago</p>
            </div>

            <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49] space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#F4F6FF]">Message Tracker</span>
                <span className="text-[10px] font-medium text-[#27D99A] bg-[#27D99A]/10 px-1.5 py-0.5 rounded">
                  Live
                </span>
              </div>
              <p className="text-[11px] text-[#A0AAC4]">
                Tracking WhatsApp & Instagram promises for order commitments, customized requests, and promised dates.
              </p>
              <p className="text-[10px] text-[#707D9E] pt-1">3 channels connected</p>
            </div>

            <div className="p-3.5 rounded-xl bg-[#101629] border border-[#252F49] space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#F4F6FF]">Marketplace Payouts</span>
                <span className="text-[10px] font-medium text-[#27D99A] bg-[#27D99A]/10 px-1.5 py-0.5 rounded">
                  Live
                </span>
              </div>
              <p className="text-[11px] text-[#A0AAC4]">
                Reconciling Meesho and marketplace deductions against contractual fee rates to prevent excess deductions.
              </p>
              <p className="text-[10px] text-[#707D9E] pt-1">Next settlement: Friday</p>
            </div>
          </div>
        </section>

        {/* Section 3: What has been completed? */}
        <section aria-label="Recently completed" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#F4F6FF] flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#27D99A]" />
              Recently completed
            </h2>
            <Link
              href="/more?tab=activity"
              className="text-xs text-[#8065FF] hover:underline flex items-center gap-1 font-medium"
            >
              <span>See full activity</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="p-4 rounded-xl bg-[#101629] border border-[#252F49] space-y-3">
            <div className="flex items-start gap-3 pb-3 border-b border-[#252F49]/70">
              <div className="w-7 h-7 rounded-full bg-[#27D99A]/15 text-[#27D99A] flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[#F4F6FF]">
                    ₹2,250 UPI payment verified
                  </span>
                  <span className="text-[10px] text-[#707D9E]">Today, 10:14 AM</span>
                </div>
                <p className="text-[11px] text-[#A0AAC4] mt-0.5">
                  Matched UTR981240182 with Order #0847 for Priya Sharma. Receipt saved.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 pb-3 border-b border-[#252F49]/70">
              <div className="w-7 h-7 rounded-full bg-[#27D99A]/15 text-[#27D99A] flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[#F4F6FF]">
                    60 orders reconciled with bank
                  </span>
                  <span className="text-[10px] text-[#707D9E]">Yesterday</span>
                </div>
                <p className="text-[11px] text-[#A0AAC4] mt-0.5">
                  All delivered orders cross-checked with dispatch registry.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-[#27D99A]/15 text-[#27D99A] flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[#F4F6FF]">
                    Payment reminder drafted for ₹1,250
                  </span>
                  <span className="text-[10px] text-[#707D9E]">Yesterday</span>
                </div>
                <p className="text-[11px] text-[#A0AAC4] mt-0.5">
                  Prepared according to your rules and waiting for your approval above.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Approval Modal (when tapping Review & Send Link directly on Home) */}
      {activeApprovalAction && (
        <ApprovalModal
          action={activeApprovalAction}
          onApprove={() => handleActionDecision(activeApprovalAction.id, "APPROVED")}
          onReject={(reason) => handleActionDecision(activeApprovalAction.id, "REJECTED", reason)}
          onDraft={() => handleActionDecision(activeApprovalAction.id, "DRAFT")}
          onClose={() => setActiveApprovalAction(null)}
          isSubmitting={actionMutation.isPending}
        />
      )}
    </div>
  );
}
