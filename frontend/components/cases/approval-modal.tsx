"use client";

import * as React from "react";
import {
  CheckCircle2,
  Lock,
  ArrowRight,
  Save,
  X,
  FileText,
  AlertTriangle,
  Send,
  Sparkles,
  User,
  CreditCard,
  MessageSquare,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatINR } from "@/lib/utils";
import type { PendingAction, EvidenceItem } from "@/lib/types";

interface ApprovalModalProps {
  isOpen?: boolean;
  onClose: () => void;
  action: PendingAction | null;
  caseTitle?: string;
  caseEvidence?: EvidenceItem[];
  onApprove: (actionId: string) => Promise<void> | void;
  onReject?: (reason?: string) => Promise<void> | void;
  onDraft?: () => Promise<void> | void;
  onSaveDraft?: (actionId: string) => Promise<void> | void;
  onCancel?: (actionId: string) => Promise<void> | void;
  isProcessing?: boolean;
  isSubmitting?: boolean;
}

export function ApprovalModal({
  isOpen = true,
  onClose,
  action,
  caseTitle,
  onApprove,
  onReject,
  onDraft,
  onSaveDraft,
  onCancel,
  isProcessing = false,
  isSubmitting = false,
}: ApprovalModalProps) {
  if (!action) return null;

  const busy = isProcessing || isSubmitting;
  const { payload } = action;

  const handleApprove = () => {
    onApprove(action.id);
  };

  const handleReject = () => {
    if (onReject) {
      onReject("Dismissed by owner");
    } else if (onCancel) {
      onCancel(action.id);
    } else {
      onClose();
    }
  };

  const handleDraft = () => {
    if (onDraft) {
      onDraft();
    } else if (onSaveDraft) {
      onSaveDraft(action.id);
    } else {
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto p-5 sm:p-6 space-y-4 bg-[#101629] border border-[#252F49] text-[#F4F6FF] shadow-[0_20px_60px_rgba(0,0,0,0.85)] rounded-2xl">
        {/* Header */}
        <DialogHeader className="border-b border-[#252F49] pb-3 text-left">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="p-1 rounded-md bg-[#8065FF]/20 text-[#8065FF]">
                <Sparkles className="w-4 h-4" />
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#8065FF]">
                Your Approval Needed
              </span>
            </div>
            <Badge variant="warning" className="text-[10px]">
              Ready to Send
            </Badge>
          </div>
          <DialogTitle className="text-base font-bold text-[#F4F6FF] mt-1.5">
            Review Before Sending
          </DialogTitle>
          <DialogDescription className="text-xs text-[#A0AAC4]">
            Jarvis will not contact the customer or create payment links until you approve.
          </DialogDescription>
        </DialogHeader>

        {/* 1. What Jarvis wants to do */}
        <div className="p-3.5 rounded-xl bg-[#151D32] border border-[#252F49] space-y-1">
          <span className="text-[10px] font-semibold text-[#707D9E] uppercase tracking-wider">
            What Jarvis wants to do
          </span>
          <p className="text-xs font-semibold text-[#F4F6FF]">
            {action.action_summary}
          </p>
        </div>

        {/* 2. Who it affects & Amount */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-[#151D32] border border-[#252F49] space-y-1">
            <span className="text-[10px] font-semibold text-[#707D9E] uppercase tracking-wider flex items-center gap-1">
              <User className="w-3 h-3 text-[#8065FF]" />
              Recipient
            </span>
            <p className="font-semibold text-[#F4F6FF] text-xs">
              {payload.recipient_name || "Priya Sharma"}
            </p>
            <p className="text-[10px] text-[#A0AAC4] font-mono">
              {payload.recipient || "+91 98765 43210"} ({payload.channel || "WhatsApp"})
            </p>
          </div>

          <div className="p-3 rounded-xl bg-[#151D32] border border-[#252F49] space-y-1">
            <span className="text-[10px] font-semibold text-[#707D9E] uppercase tracking-wider flex items-center gap-1">
              <CreditCard className="w-3 h-3 text-[#27D99A]" />
              Amount to Collect
            </span>
            <p className="font-mono text-base font-bold text-[#27D99A]">
              {payload.amount ? formatINR(payload.amount) : "₹1,250.00"}
            </p>
            <p className="text-[10px] text-[#A0AAC4]">
              Remaining shortfall
            </p>
          </div>
        </div>

        {/* 3. Message Preview */}
        {payload.body && (
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold text-[#707D9E] uppercase tracking-wider flex items-center gap-1">
              <MessageSquare className="w-3 h-3 text-[#8065FF]" />
              Message Preview
            </span>
            <div className="p-3 rounded-xl bg-[#080B14] border border-[#252F49] text-xs text-[#F4F6FF] leading-relaxed font-sans">
              {payload.body}
            </div>
            {payload.payment_link && (
              <p className="text-[10px] text-[#8065FF] font-mono pl-1">
                Payment Link: {payload.payment_link}
              </p>
            )}
          </div>
        )}

        {/* 4. Why recommended */}
        <div className="p-3 rounded-xl bg-[#27D99A]/10 border border-[#27D99A]/20 text-xs space-y-1">
          <span className="text-[10px] font-semibold text-[#27D99A] uppercase tracking-wider flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Why this is recommended
          </span>
          <p className="text-[11px] text-[#A0AAC4] leading-relaxed">
            Customer made an advance payment of ₹2,250 and committed on WhatsApp to settle the remaining ₹1,250. Sending a friendly link makes it fast and secure for her to complete payment.
          </p>
        </div>

        {/* Footer: Plain 3 buttons */}
        <div className="pt-3 border-t border-[#252F49] flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={busy}
            onClick={handleReject}
            className="text-xs text-[#A0AAC4] hover:text-[#F4F6FF]"
          >
            <X className="w-3.5 h-3.5 mr-1" />
            Decline
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={handleDraft}
            className="text-xs border-[#252F49] bg-[#151D32] text-[#F4F6FF] hover:bg-[#1E2945]"
          >
            <Save className="w-3.5 h-3.5 mr-1" />
            Save Draft
          </Button>

          <Button
            type="button"
            size="sm"
            disabled={busy}
            onClick={handleApprove}
            className="text-xs bg-[#8065FF] hover:bg-[#6E50FF] font-semibold text-white px-4 shadow-[0_0_16px_rgba(128,101,255,0.4)] cursor-pointer"
          >
            <Send className="w-3.5 h-3.5 mr-1" />
            {busy ? "Sending…" : "Approve & Send"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
