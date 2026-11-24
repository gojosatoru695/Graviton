"use client";

import * as React from "react";
import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ShieldAlert,
  CheckCircle2,
  Lock,
  ArrowLeft,
  ExternalLink,
  Save,
  X,
  FileText,
  AlertTriangle,
  Send,
} from "lucide-react";
import { useCases, useCaseDetail, useActionDecision } from "@/lib/api";
import { formatINR } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState, SuccessBanner } from "@/components/ui/states";
import type { PendingAction, EvidenceItem } from "@/lib/types";

function ApprovalScreenContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const caseId = searchParams.get("caseId") || "case-001";
  const actionId = searchParams.get("actionId") || "act-001";

  const { data: caseDetail, isLoading } = useCaseDetail(caseId);
  const actionMutation = useActionDecision();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (isLoading || !caseDetail) {
    return <LoadingState message="Loading approval gate specifications…" />;
  }

  const action = caseDetail.pending_actions?.find((a: PendingAction) => a.id === actionId) || caseDetail.pending_actions?.[0];

  if (!action) {
    return (
      <div className="p-8 max-w-2xl mx-auto text-center space-y-4">
        <h2 className="font-serif text-xl font-bold text-ink">No Pending Action Found</h2>
        <p className="text-xs text-ink-muted">All proposed actions for this case have been settled or dismissed.</p>
        <Link href="/cases">
          <Button variant="outline" size="sm">
            <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Cases
          </Button>
        </Link>
      </div>
    );
  }

  const { payload } = action;
  const isReversible = action.reversibility === "REVERSIBLE" || payload.reversible === true;

  const handleDecision = async (decision: "APPROVED" | "REJECTED" | "DRAFT") => {
    try {
      await actionMutation.mutateAsync({ actionId: action.id, decision });
      setSuccessMessage(
        decision === "APPROVED"
          ? "Action approved and dispatched to verified recipient"
          : decision === "DRAFT"
          ? "Action draft saved to outbound queue"
          : "Action proposal cancelled"
      );
      setTimeout(() => {
        router.push(`/cases?selected=${caseDetail.id}`);
      }, 1500);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-4 lg:p-8 max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* Top Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href={`/cases?selected=${caseDetail.id}`}
          className="text-xs text-ink-muted hover:text-ink flex items-center gap-1.5 font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Case Facts</span>
        </Link>
        <Badge variant="risk" className="flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" />
          Human Approval Required
        </Badge>
      </div>

      {successMessage && <SuccessBanner message={successMessage} />}

      {/* Main Approval Screen Card */}
      <div className="bg-surface border border-hairline rounded-[var(--radius-card)] p-6 lg:p-8 shadow-card space-y-6">
        {/* Header */}
        <div className="border-b border-hairline pb-4 space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-[var(--radius-sm)] bg-primary-light text-primary">
              <Lock className="w-4 h-4" />
            </span>
            <span className="font-mono text-[10px] font-bold uppercase text-ink-muted">
              Action #{action.id} · Case #{caseDetail.id}
            </span>
          </div>
          <h1 className="font-serif text-2xl font-bold text-ink">
            Outbound Action Approval Gate
          </h1>
          <p className="text-xs text-ink-muted">
            Jarvis non-negotiable rule: Outbound messages, refunds, and payment links require deliberate authorization.
          </p>
        </div>

        {/* 1. Exact Recipient */}
        <section aria-labelledby="recipient-label" className="space-y-1.5">
          <h2 id="recipient-label" className="text-xs font-semibold uppercase tracking-wider text-ink-muted flex items-center justify-between">
            <span>1. Exact Recipient</span>
            <span className="text-[10px] font-mono text-primary lowercase">{payload.channel || "WhatsApp"}</span>
          </h2>
          <div className="bg-paper border border-hairline rounded-[var(--radius-sm)] p-3.5 flex items-center justify-between text-xs">
            <div>
              <p className="font-bold text-ink text-sm">{payload.recipient_name || caseDetail.customer_name}</p>
              <p className="font-mono text-ink-muted mt-0.5">{payload.recipient || caseDetail.customer_phone || "+91 98765 43210"}</p>
            </div>
            <Badge variant="primary">Verified Contact</Badge>
          </div>
        </section>

        {/* 2. Exact Message */}
        <section aria-labelledby="message-label" className="space-y-1.5">
          <h2 id="message-label" className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
            2. Exact Outbound Message
          </h2>
          <div className="bg-paper border border-hairline rounded-[var(--radius-sm)] p-4 text-xs">
            {payload.body ? (
              <pre className="whitespace-pre-wrap font-sans text-ink leading-relaxed text-xs">
                {payload.body}
              </pre>
            ) : (
              <p className="italic text-ink-muted">No message payload; direct webhook trigger.</p>
            )}
          </div>
        </section>

        {/* 3. Supporting Evidence */}
        <section aria-labelledby="evidence-label" className="space-y-1.5">
          <h2 id="evidence-label" className="text-xs font-semibold uppercase tracking-wider text-ink-muted flex items-center justify-between">
            <span>3. Supporting Evidence Grounding</span>
            <span className="text-[10px] text-success font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Grounded in {caseDetail.evidence_items.length} records
            </span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {caseDetail.evidence_items.map((ev: EvidenceItem) => (
              <div key={ev.id} className="bg-paper/50 border border-hairline rounded-[var(--radius-sm)] p-2.5 text-xs">
                <span className="font-semibold text-ink flex items-center gap-1 text-[11px]">
                  <FileText className="w-3 h-3 text-primary" /> {ev.evidence_type.replace(/_/g, " ")}
                </span>
                <p className="font-mono text-[10px] text-ink-muted truncate mt-0.5">
                  {JSON.stringify(ev.payload)}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* 4 & 5. Payment Link Details & Reversibility */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <section aria-labelledby="payment-details-label" className="space-y-1.5">
            <h2 id="payment-details-label" className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
              4. Payment Link Details
            </h2>
            <div className="bg-paper border border-hairline rounded-[var(--radius-sm)] p-3 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-ink-muted">Amount:</span>
                <span className="font-mono font-bold text-ink text-sm">{formatINR(payload.amount || caseDetail.discrepancy_amount)}</span>
              </div>
              {payload.payment_link && (
                <div className="pt-1.5 border-t border-hairline flex items-center justify-between">
                  <span className="text-ink-muted text-[10px]">Razorpay URL:</span>
                  <a href={payload.payment_link} target="_blank" rel="noreferrer" className="text-primary font-mono text-[11px] flex items-center gap-1 hover:underline">
                    <span>Live Checkout</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
            </div>
          </section>

          <section aria-labelledby="reversibility-label" className="space-y-1.5">
            <h2 id="reversibility-label" className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
              5. Reversibility State
            </h2>
            <div className={`border rounded-[var(--radius-sm)] p-3 text-xs space-y-1 ${
              isReversible ? "bg-success-light/40 border-success/30" : "bg-warning-light/40 border-warning/30"
            }`}>
              <div className="flex items-center gap-1.5 font-semibold text-xs">
                {isReversible ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                    <span className="text-success">Reversible Transaction</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5 text-warning" />
                    <span className="text-warning">Irreversible Outbound Message</span>
                  </>
                )}
              </div>
              <p className="text-[11px] text-ink-muted">
                {isReversible
                  ? "Can be rolled back before nightly settlement cutoff."
                  : "Message dispatch to customer phone cannot be recalled once sent."}
              </p>
            </div>
          </section>
        </div>

        {/* 6. Exact Buttons: Approve & Send, Save Draft, Cancel */}
        <div className="pt-6 border-t border-hairline flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3">
          <Button
            type="button"
            variant="ghost"
            disabled={actionMutation.isPending}
            onClick={() => handleDecision("REJECTED")}
            aria-label="Cancel and reject action"
          >
            <X className="w-4 h-4 mr-1.5" /> Cancel
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={actionMutation.isPending}
            onClick={() => handleDecision("DRAFT")}
            aria-label="Save as draft"
          >
            <Save className="w-4 h-4 mr-1.5" /> Save Draft
          </Button>
          <Button
            type="button"
            disabled={actionMutation.isPending}
            onClick={() => handleDecision("APPROVED")}
            className="bg-primary hover:bg-primary-hover font-semibold px-6"
            aria-label="Approve and send action immediately"
          >
            <Send className="w-4 h-4 mr-1.5" /> {actionMutation.isPending ? "Executing…" : "Approve & Send"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function ApprovalPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading approval screen…" />}>
      <ApprovalScreenContent />
    </Suspense>
  );
}
