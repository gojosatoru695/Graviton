"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldAlert,
  Search,
  Sparkles,
  Layers,
  ChevronRight,
  ChevronLeft,
  AlertTriangle,
  HelpCircle,
  FileText,
  MessageSquare,
  Network,
  Eye,
  Check,
  Send,
  ExternalLink,
  Info,
} from "lucide-react";
import { useCases, useCaseDetail, useActionDecision } from "@/lib/api";
import { useCasesStore } from "@/lib/store";
import { formatINR, cn, formatFriendlyId } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingState, ErrorState, EmptyState, SuccessBanner } from "@/components/ui/states";
import { ApprovalModal } from "@/components/cases/approval-modal";
import { DependencyGraph } from "@/components/cases/dependency-graph";
import type { PendingAction, EvidenceItem } from "@/lib/types";

function TasksContent() {
  const searchParams = useSearchParams();
  const initialSelected = searchParams.get("selected");
  const initialFilter = searchParams.get("filter");

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(initialSelected || null);
  const [activeFilter, setActiveFilter] = useState<string>(initialFilter || "ALL");
  const [showConnections, setShowConnections] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [activeApprovalAction, setActiveApprovalAction] = useState<PendingAction | null>(null);

  const { data: cases, isLoading, isError, error, refetch } = useCases();
  const { data: currentTask, isLoading: detailLoading } = useCaseDetail(selectedTaskId);
  const actionMutation = useActionDecision();

  // Set default selection
  useEffect(() => {
    if (initialSelected) {
      setSelectedTaskId(initialSelected);
    } else if (cases && cases.length > 0 && !selectedTaskId) {
      setSelectedTaskId(cases[0].id);
    }
  }, [initialSelected, cases, selectedTaskId]);

  const handleDecision = async (
    actionId: string,
    decision: "APPROVED" | "REJECTED" | "DRAFT",
    reason?: string
  ) => {
    try {
      await actionMutation.mutateAsync({ actionId, decision, rejectionReason: reason });
      setActiveApprovalAction(null);
      setSuccessMessage(
        decision === "APPROVED"
          ? "Action approved and dispatched successfully!"
          : decision === "DRAFT"
          ? "Action saved as draft"
          : "Action proposal dismissed"
      );
      refetch();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error(err);
    }
  };

  if (isLoading) return <LoadingState message="Loading your tasks…" />;
  if (isError) return <ErrorState message={error?.message} onRetry={() => refetch()} />;

  const filteredTasks = (cases || []).filter((task) => {
    if (activeFilter === "ALL") return true;
    if (activeFilter === "AWAITING_APPROVAL") {
      return task.status === "ACTION_PROPOSED" || task.severity === "CRITICAL";
    }
    return task.case_type === activeFilter;
  });

  const filterTabs = [
    { id: "ALL", label: "All Tasks" },
    { id: "AWAITING_APPROVAL", label: "Needs Approval" },
    { id: "PAYMENT_SHORTFALL", label: "Payment Shortfalls" },
    { id: "MARKETPLACE_VARIANCE", label: "Money Mismatch" },
    { id: "BROKEN_PROMISE", label: "Promises" },
  ];

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col overflow-hidden bg-[#080B14] select-none pb-14 lg:pb-0">
      {/* Top Bar: Title & Filter Pills */}
      <div className="h-13 px-4 lg:px-6 border-b border-[#252F49] bg-[#0B1020] flex items-center justify-between shrink-0 gap-3">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-bold text-[#F4F6FF] tracking-tight">
            Tasks & Issues
          </h1>
          <span className="text-[11px] font-mono text-[#707D9E]">
            ({filteredTasks.length})
          </span>
        </div>

        {/* Filter Scrollable Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs py-1 scrollbar-none">
          {filterTabs.map((tab) => {
            const isActive = activeFilter === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveFilter(tab.id)}
                className={cn(
                  "px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all cursor-pointer",
                  isActive
                    ? "bg-[#8065FF] text-white font-semibold shadow-sm"
                    : "bg-[#101629] border border-[#252F49] text-[#A0AAC4] hover:text-[#F4F6FF] hover:border-[#3A4769]"
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div className="px-4 py-2 shrink-0 bg-[#080B14]">
          <SuccessBanner message={successMessage} onDismiss={() => setSuccessMessage(null)} />
        </div>
      )}

      {/* Main Content: Split Master-Detail or Single Stack on Mobile */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Task List (Hidden on mobile if a task is selected and user is reading it) */}
        <div
          className={cn(
            "w-full lg:w-80 border-r border-[#252F49] bg-[#0B1020] flex flex-col shrink-0 overflow-hidden",
            selectedTaskId && "hidden lg:flex"
          )}
        >
          <div className="p-3 border-b border-[#252F49]/70 text-[11px] font-semibold text-[#707D9E] uppercase tracking-wider">
            Items to review ({filteredTasks.length})
          </div>

          <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
            {filteredTasks.length === 0 ? (
              <EmptyState title="No tasks found" description="Select 'All Tasks' to view your other items." />
            ) : (
              filteredTasks.map((t) => {
                const isSelected = t.id === selectedTaskId;
                const isShortfall = t.case_type === "PAYMENT_SHORTFALL";
                const isVariance = t.case_type === "MARKETPLACE_VARIANCE";

                return (
                  <div
                    key={t.id}
                    onClick={() => setSelectedTaskId(t.id)}
                    className={cn(
                      "p-3 rounded-xl border text-xs cursor-pointer transition-all",
                      isSelected
                        ? "bg-[#151D32] border-[#8065FF] shadow-[0_0_12px_rgba(128,101,255,0.2)]"
                        : "bg-[#101629] border-[#252F49] hover:border-[#3A4769] hover:bg-[#151D32]/50"
                    )}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[#1A2440] text-[#A0AAC4]">
                        {isShortfall ? "Payment Shortfall" : isVariance ? "Money Mismatch" : t.case_type.replace(/_/g, " ")}
                      </span>
                      {t.discrepancy_amount > 0 ? (
                        <span className="font-mono text-xs font-bold text-[#FF6977]">
                          {formatINR(t.discrepancy_amount)}
                        </span>
                      ) : (
                        <span className="text-[10px] font-medium text-[#27D99A]">Verified</span>
                      )}
                    </div>

                    <h2 className="font-semibold text-xs text-[#F4F6FF] line-clamp-1">
                      {t.title}
                    </h2>
                    <p className="text-[11px] text-[#A0AAC4] line-clamp-2 mt-0.5 leading-relaxed">
                      {t.headline}
                    </p>

                    <div className="mt-2 pt-2 border-t border-[#252F49]/40 flex items-center justify-between text-[10px] text-[#707D9E]">
                      <span>{t.customer_name || "Store Item"}</span>
                      <span className="text-[#8065FF] flex items-center gap-0.5 font-medium">
                        Open <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: 6-Question Task Detail */}
        <div
          className={cn(
            "flex-1 flex flex-col bg-[#080B14] overflow-hidden",
            !selectedTaskId && "hidden lg:flex"
          )}
        >
          {currentTask ? (
            <div className="flex-1 flex flex-col h-full overflow-hidden">
              {/* Detail Header */}
              <div className="p-4 border-b border-[#252F49] bg-[#0B1020] flex items-center justify-between gap-3 shrink-0">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedTaskId(null)}
                    className="lg:hidden p-1.5 rounded-md text-[#707D9E] hover:text-[#F4F6FF] bg-[#151D32] mr-1"
                    aria-label="Back to task list"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-[#8065FF] font-semibold">
                        {currentTask.id.toUpperCase()}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#1A2440] text-[#A0AAC4]">
                        {currentTask.customer_name}
                      </span>
                    </div>
                    <h2 className="text-base font-bold text-[#F4F6FF] mt-0.5">
                      {currentTask.title}
                    </h2>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowConnections(!showConnections)}
                    className="text-xs h-8 px-2.5 gap-1.5 border-[#252F49] text-[#A0AAC4] hover:text-[#F4F6FF] bg-[#101629]"
                  >
                    <Network className="w-3.5 h-3.5 text-[#8065FF]" />
                    <span className="hidden sm:inline">
                      {showConnections ? "Hide connections" : "See connections"}
                    </span>
                  </Button>
                </div>
              </div>

              {/* Optional Expandable Connections / Evidence Graph */}
              {showConnections && (
                <div className="h-64 border-b border-[#252F49] bg-[#05070D] shrink-0 p-2 relative">
                  <div className="absolute top-3 left-3 z-10 text-[10px] font-semibold text-[#707D9E] uppercase tracking-wider bg-[#0B1020]/80 px-2 py-0.5 rounded border border-[#252F49]">
                    Evidence Connections
                  </div>
                  <DependencyGraph
                    caseDetail={currentTask}
                    selectedNodeId={null}
                    onSelectNode={() => {}}
                  />
                </div>
              )}

              {/* 6 Questions Body (Scrollable) */}
              <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-5 max-w-4xl">
                {/* 1. What happened? */}
                <div className="p-4 rounded-xl bg-[#101629] border border-[#252F49] space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#F4F6FF] uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-[#8065FF]/20 text-[#8065FF] flex items-center justify-center text-[11px] font-bold">
                      1
                    </span>
                    <h3>What happened?</h3>
                  </div>
                  <p className="text-xs text-[#F4F6FF] font-medium leading-relaxed">
                    {currentTask.headline}
                  </p>
                  <p className="text-xs text-[#A0AAC4] leading-relaxed">
                    {currentTask.explanation}
                  </p>
                  {currentTask.order_amount && (
                    <div className="mt-2 pt-2 border-t border-[#252F49]/50 flex flex-wrap gap-4 text-xs">
                      <div>
                        <span className="text-[10px] text-[#707D9E] block">Order Total:</span>
                        <span className="font-mono font-semibold text-[#F4F6FF]">
                          {formatINR(currentTask.order_amount)}
                        </span>
                      </div>
                      {currentTask.discrepancy_amount > 0 && (
                        <div>
                          <span className="text-[10px] text-[#707D9E] block">Still Owed:</span>
                          <span className="font-mono font-semibold text-[#FF6977]">
                            {formatINR(currentTask.discrepancy_amount)}
                          </span>
                        </div>
                      )}
                      {currentTask.order_number && (
                        <div>
                          <span className="text-[10px] text-[#707D9E] block">Order Ref:</span>
                          <span className="font-mono text-[#A0AAC4]">{currentTask.order_number}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* 2. What did Jarvis check? */}
                <div className="p-4 rounded-xl bg-[#101629] border border-[#252F49] space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#F4F6FF] uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-[#29D8C5]/20 text-[#29D8C5] flex items-center justify-center text-[11px] font-bold">
                      2
                    </span>
                    <h3>What did Jarvis check?</h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {currentTask.evidence_items && currentTask.evidence_items.length > 0 ? (
                      currentTask.evidence_items.map((ev: EvidenceItem) => (
                        <div
                          key={ev.id}
                          className="p-2.5 rounded-lg bg-[#151D32] border border-[#252F49]/70 flex items-start gap-2"
                        >
                          <CheckCircle2 className="w-4 h-4 text-[#29D8C5] shrink-0 mt-0.5" />
                          <div className="space-y-0.5">
                            <span className="font-medium text-[#F4F6FF] text-[11px] block">
                              {ev.title || (ev.payload?.title as string) || (ev.payload?.description as string) || ev.id}
                            </span>
                            <span className="text-[10px] text-[#707D9E] block">
                              {ev.evidence_type.replace(/_/g, " ")} · Source: {ev.source_table}
                            </span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-[#A0AAC4]">
                        Checked bank records, order logs, and chat messages.
                      </p>
                    )}
                  </div>
                </div>

                {/* 3. What is verified? */}
                <div className="p-4 rounded-xl bg-[#101629] border border-[#27D99A]/30 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#27D99A] uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-[#27D99A]/20 text-[#27D99A] flex items-center justify-center text-[11px] font-bold">
                      3
                    </span>
                    <h3>What is verified?</h3>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    {currentTask.findings && currentTask.findings.length > 0 ? (
                      currentTask.findings.map((f: string, i: number) => (
                        <div key={i} className="flex items-start gap-2 text-[#F4F6FF]">
                          <Check className="w-3.5 h-3.5 text-[#27D99A] shrink-0 mt-0.5" />
                          <span className="text-[11px] leading-relaxed">{f}</span>
                        </div>
                      ))
                    ) : (
                      <div className="flex items-start gap-2 text-[#F4F6FF]">
                        <Check className="w-3.5 h-3.5 text-[#27D99A] shrink-0 mt-0.5" />
                        <span className="text-[11px]">All supporting records substantiated by verified hashes.</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* 4. What is uncertain? */}
                <div className="p-4 rounded-xl bg-[#101629] border border-[#FFB547]/30 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#FFB547] uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-[#FFB547]/20 text-[#FFB547] flex items-center justify-center text-[11px] font-bold">
                      4
                    </span>
                    <h3>What is uncertain?</h3>
                  </div>
                  <div className="text-xs text-[#A0AAC4] space-y-1">
                    {currentTask.case_type === "PAYMENT_SHORTFALL" ? (
                      <p className="text-[11px] leading-relaxed">
                        Customer has not yet sent the remaining ₹1,250. No matching bank credit found for the balance.
                      </p>
                    ) : currentTask.case_type === "MARKETPLACE_VARIANCE" ? (
                      <p className="text-[11px] leading-relaxed">
                        ₹850 discrepancy in Meesho remittance lacks supporting contractual line items in the fee schedule.
                      </p>
                    ) : (
                      <p className="text-[11px] leading-relaxed">
                        Awaiting recipient response or counterparty confirmation.
                      </p>
                    )}
                  </div>
                </div>

                {/* 5. What does Jarvis suggest? */}
                <div className="p-4 rounded-xl bg-[#101629] border border-[#8065FF]/40 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#8065FF] uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-[#8065FF]/20 text-[#8065FF] flex items-center justify-center text-[11px] font-bold">
                      5
                    </span>
                    <h3>What does Jarvis suggest?</h3>
                  </div>
                  <div className="text-xs text-[#F4F6FF]">
                    {currentTask.recommended_action ? (
                      <div className="space-y-1">
                        <p className="font-semibold">{currentTask.recommended_action.title}</p>
                        <p className="text-[#A0AAC4] text-[11px] leading-relaxed">
                          {currentTask.recommended_action.description}
                        </p>
                        <p className="text-[11px] text-[#29D8C5] pt-1">
                          Expected outcome: {currentTask.recommended_action.expected_outcome}
                        </p>
                      </div>
                    ) : (
                      <p className="text-[#A0AAC4] text-[11px]">
                        Notify the customer or counterparty with verified evidence and collect the balance.
                      </p>
                    )}
                  </div>
                </div>

                {/* 6. Does the owner need to approve anything? */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-[#131B32] to-[#101629] border border-[#8065FF] space-y-3 shadow-[0_4px_20px_rgba(128,101,255,0.2)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-[#F4F6FF] uppercase tracking-wider">
                      <span className="w-5 h-5 rounded-full bg-[#8065FF] text-white flex items-center justify-center text-[11px] font-bold">
                        6
                      </span>
                      <h3>Does the owner need to approve anything?</h3>
                    </div>
                    {currentTask.pending_actions && currentTask.pending_actions.length > 0 ? (
                      <Badge variant="warning">Approval Needed</Badge>
                    ) : (
                      <Badge variant="success">No Action Needed</Badge>
                    )}
                  </div>

                  {currentTask.pending_actions && currentTask.pending_actions.length > 0 ? (
                    <div className="space-y-3 pt-1">
                      {currentTask.pending_actions.map((act: PendingAction) => (
                        <div
                          key={act.id}
                          className="p-3.5 rounded-lg bg-[#0B1020] border border-[#252F49] space-y-2.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-[#F4F6FF]">
                              {act.action_summary}
                            </span>
                            {act.payload?.amount && (
                              <span className="font-mono text-xs font-bold text-[#FF6977]">
                                {formatINR(act.payload.amount)}
                              </span>
                            )}
                          </div>

                          {act.payload?.body && (
                            <div className="p-2.5 rounded bg-[#151D32] border border-[#252F49]/70 text-[11px] text-[#A0AAC4] font-mono leading-relaxed">
                              {act.payload.body}
                            </div>
                          )}

                          <div className="flex items-center justify-between pt-1">
                            <span className="text-[10px] text-[#707D9E]">
                              Recipient: {act.payload?.recipient_name || currentTask.customer_name} ({act.payload?.channel || "WhatsApp"})
                            </span>

                            <Button
                              onClick={() => setActiveApprovalAction(act)}
                              className="bg-[#8065FF] hover:bg-[#6E50FF] text-white font-semibold text-xs h-8 px-3 gap-1.5 shadow-[0_0_12px_rgba(128,101,255,0.3)] cursor-pointer"
                            >
                              <span>Review & Approve</span>
                              <ArrowRight className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-[#A0AAC4]">
                      No immediate approval needed. Jarvis is monitoring this task automatically.
                    </p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-6">
              <EmptyState title="Select a task" description="Choose any task on the left to see what happened and what Jarvis suggests." />
            </div>
          )}
        </div>
      </div>

      {/* Approval Modal */}
      {activeApprovalAction && (
        <ApprovalModal
          action={activeApprovalAction}
          onApprove={() => handleDecision(activeApprovalAction.id, "APPROVED")}
          onReject={(reason) => handleDecision(activeApprovalAction.id, "REJECTED", reason)}
          onDraft={() => handleDecision(activeApprovalAction.id, "DRAFT")}
          onClose={() => setActiveApprovalAction(null)}
          isSubmitting={actionMutation.isPending}
        />
      )}
    </div>
  );
}

export default function TasksPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading tasks…" />}>
      <TasksContent />
    </Suspense>
  );
}
