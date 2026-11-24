"use client";

import { useState } from "react";
import {
  MessageSquare,
  Search,
  Send,
  Sparkles,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldAlert,
  ExternalLink,
  ChevronRight,
  User,
  ShoppingBag,
  CreditCard,
  Gift,
  Check,
} from "lucide-react";
import { cn, formatINR } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApprovalModal } from "@/components/cases/approval-modal";
import { useCaseDetail, useActionDecision } from "@/lib/api";
import { SuccessBanner } from "@/components/ui/states";
import type { PendingAction } from "@/lib/types";

interface MessageItem {
  id: string;
  sender: "customer" | "seller" | "jarvis";
  text: string;
  time: string;
  hasAttachment?: boolean;
}

interface Thread {
  id: string;
  customerName: string;
  platform: "WhatsApp" | "Instagram" | "Gmail";
  phoneOrHandle: string;
  avatarColor: string;
  lastMessage: string;
  lastTime: string;
  unreadCount?: number;
  hasPromiseAlert?: boolean;
  orderNumber: string;
  orderAmount: number;
  paidAmount: number;
  unpaidAmount: number;
  items: string[];
  messages: MessageItem[];
  suggestedReply?: {
    text: string;
    actionSummary: string;
    hasLink?: boolean;
  };
}

const THREADS: Thread[] = [
  {
    id: "thread_1",
    customerName: "Priya Sharma",
    platform: "WhatsApp",
    phoneOrHandle: "+91 98765 43210",
    avatarColor: "bg-[#25D366]/20 text-[#25D366] border-[#25D366]/40",
    lastMessage: "Can I pay the remaining ₹1,250 once the parcel is out for delivery?",
    lastTime: "10:14 AM",
    unreadCount: 1,
    hasPromiseAlert: true,
    orderNumber: "ORD-2026-0847",
    orderAmount: 3500,
    paidAmount: 2250,
    unpaidAmount: 1250,
    items: ["Kanjivaram Silk Saree (Crimson & Gold)", "Handloom Cotton Blouse"],
    messages: [
      {
        id: "m1",
        sender: "customer",
        text: "Hi! I placed the order on your store for the Kanjivaram saree.",
        time: "10:10 AM",
      },
      {
        id: "m2",
        sender: "seller",
        text: "Hello Priya! Thank you for ordering from Aura Weaves. Total comes to ₹3,500.",
        time: "10:11 AM",
      },
      {
        id: "m3",
        sender: "customer",
        text: "I have transferred ₹2,250 via GPay just now. Reference UTR981240182.",
        time: "10:12 AM",
      },
      {
        id: "m4",
        sender: "customer",
        text: "Can I pay the remaining ₹1,250 once the parcel is out for delivery on Friday?",
        time: "10:14 AM",
      },
    ],
    suggestedReply: {
      text: "Hi Priya! We received your advance of ₹2,250. Here is your secure payment link for the remaining ₹1,250: https://rzp.io/i/auraw_0847. Your saree is packed and ready!",
      actionSummary: "Send ₹1,250 Razorpay link via WhatsApp",
      hasLink: true,
    },
  },
  {
    id: "thread_2",
    customerName: "Ananya Verma",
    platform: "Instagram",
    phoneOrHandle: "@ananya_v",
    avatarColor: "bg-[#E1306C]/20 text-[#E1306C] border-[#E1306C]/40",
    lastMessage: "Could you please add a pink silk scrunchie as gift wrap?",
    lastTime: "Yesterday",
    hasPromiseAlert: true,
    orderNumber: "ORD-2026-0842",
    orderAmount: 1800,
    paidAmount: 1800,
    unpaidAmount: 0,
    items: ["Handcrafted Silver Jhumkas", "Pink Silk Scrunchie (Gift Promise)"],
    messages: [
      {
        id: "m21",
        sender: "customer",
        text: "Hey! Loved the earrings on your reels, just bought them on your site! ✨",
        time: "Yesterday, 3:30 PM",
      },
      {
        id: "m22",
        sender: "customer",
        text: "Could you please add a pink silk scrunchie as gift wrap if possible?",
        time: "Yesterday, 3:32 PM",
      },
      {
        id: "m23",
        sender: "seller",
        text: "Sure thing Ananya! We'll include a complimentary pink silk scrunchie in your parcel. 💖",
        time: "Yesterday, 3:45 PM",
      },
    ],
    suggestedReply: {
      text: "Packing alert: Complimentary pink silk scrunchie verified and added to dispatch box for Ananya.",
      actionSummary: "Confirm gift scrunchie in packing checklist",
      hasLink: false,
    },
  },
  {
    id: "thread_3",
    customerName: "Rahul Mehra",
    platform: "Gmail",
    phoneOrHandle: "rahul.m@outlook.com",
    avatarColor: "bg-[#4285F4]/20 text-[#4285F4] border-[#4285F4]/40",
    lastMessage: "Could you send over the formal GST invoice for corporate filing?",
    lastTime: "22 Nov",
    orderNumber: "ORD-2026-0839",
    orderAmount: 4900,
    paidAmount: 4900,
    unpaidAmount: 0,
    items: ["Pure Zari Silk Dupatta", "Silk Gift Box Packaging"],
    messages: [
      {
        id: "m31",
        sender: "customer",
        text: "Hi Aura Weaves team, could you send over the formal GST invoice with GSTIN for our corporate expense filing?",
        time: "22 Nov, 11:20 AM",
      },
    ],
    suggestedReply: {
      text: "Dear Rahul, please find attached the verified GST Tax Invoice (INV-2026-0839) for your order.",
      actionSummary: "Email PDF GST Invoice to rahul.m@outlook.com",
      hasLink: false,
    },
  },
];

export default function MessagesPage() {
  const [selectedThreadId, setSelectedThreadId] = useState<string>("thread_1");
  const [filterPlatform, setFilterPlatform] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [replyInput, setReplyInput] = useState<string>("");
  const [activeApprovalAction, setActiveApprovalAction] = useState<PendingAction | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Connect to actual backend for Priya Sharma's pending action
  const { data: featuredCase } = useCaseDetail("case_001");
  const actionMutation = useActionDecision();

  const currentThread = THREADS.find((t) => t.id === selectedThreadId) || THREADS[0];

  const filteredThreads = THREADS.filter((t) => {
    if (filterPlatform !== "ALL" && t.platform !== filterPlatform) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        t.customerName.toLowerCase().includes(q) ||
        t.orderNumber.toLowerCase().includes(q) ||
        t.phoneOrHandle.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleOpenApproval = () => {
    if (featuredCase?.pending_actions?.[0]) {
      setActiveApprovalAction(featuredCase.pending_actions[0]);
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
          ? "Payment link generated & sent to Priya Sharma!"
          : "Draft saved"
      );
      setTimeout(() => setSuccessBanner(null), 5000);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col overflow-hidden bg-[#080B14] select-none pb-14 lg:pb-0">
      {/* Success Notification */}
      {successBanner && (
        <div className="px-4 py-2 shrink-0 bg-[#080B14]">
          <SuccessBanner message={successBanner} onDismiss={() => setSuccessBanner(null)} />
        </div>
      )}

      {/* Main 3-Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Thread List */}
        <div className="w-full sm:w-80 border-r border-[#252F49] bg-[#0B1020] flex flex-col shrink-0 overflow-hidden">
          {/* Header & Filter */}
          <div className="p-3 border-b border-[#252F49] space-y-2.5">
            <div className="flex items-center justify-between">
              <h1 className="text-sm font-bold text-[#F4F6FF]">Messages</h1>
              <span className="text-[10px] text-[#27D99A] bg-[#27D99A]/15 px-2 py-0.5 rounded-full font-semibold">
                3 Channels Active
              </span>
            </div>

            {/* Channel Filters */}
            <div className="flex items-center gap-1 overflow-x-auto text-xs scrollbar-none">
              {["ALL", "WhatsApp", "Instagram", "Gmail"].map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterPlatform(p)}
                  className={cn(
                    "px-2 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer",
                    filterPlatform === p
                      ? "bg-[#8065FF] text-white"
                      : "bg-[#151D32] text-[#A0AAC4] hover:text-[#F4F6FF]"
                  )}
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#707D9E] absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search customers or orders…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-7 pl-8 pr-3 bg-[#101629] border border-[#252F49] rounded-md text-xs text-[#F4F6FF] placeholder-[#707D9E] focus:outline-none focus:border-[#8065FF]"
              />
            </div>
          </div>

          {/* Threads Scrollable */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {filteredThreads.map((t) => {
              const isSelected = t.id === selectedThreadId;
              return (
                <div
                  key={t.id}
                  onClick={() => setSelectedThreadId(t.id)}
                  className={cn(
                    "p-3 rounded-xl border text-xs cursor-pointer transition-all",
                    isSelected
                      ? "bg-[#151D32] border-[#8065FF] shadow-[0_0_12px_rgba(128,101,255,0.2)]"
                      : "bg-[#101629] border-[#252F49] hover:border-[#3A4769] hover:bg-[#151D32]/50"
                  )}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cn(
                          "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border",
                          t.avatarColor
                        )}
                      >
                        {t.platform[0]}
                      </span>
                      <span className="font-semibold text-xs text-[#F4F6FF]">
                        {t.customerName}
                      </span>
                    </div>
                    <span className="text-[10px] text-[#707D9E] font-mono">{t.lastTime}</span>
                  </div>

                  <p className="text-[11px] text-[#A0AAC4] line-clamp-1 leading-relaxed">
                    {t.lastMessage}
                  </p>

                  <div className="mt-2 pt-1.5 border-t border-[#252F49]/40 flex items-center justify-between text-[10px]">
                    <span className="text-[#707D9E] font-mono">{t.orderNumber}</span>
                    {t.unpaidAmount > 0 ? (
                      <span className="font-mono text-[#FF6977] font-semibold">
                        Owes {formatINR(t.unpaidAmount)}
                      </span>
                    ) : (
                      <span className="text-[#27D99A] font-medium">Fully Paid</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Center: Conversation View */}
        <div className="flex-1 flex flex-col bg-[#080B14] overflow-hidden">
          {/* Conversation Header */}
          <div className="p-3.5 border-b border-[#252F49] bg-[#0B1020] flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-2.5">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs border",
                  currentThread.avatarColor
                )}
              >
                {currentThread.customerName[0]}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xs font-bold text-[#F4F6FF]">
                    {currentThread.customerName}
                  </h2>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#1A2440] text-[#A0AAC4]">
                    {currentThread.platform} · {currentThread.phoneOrHandle}
                  </span>
                </div>
                <p className="text-[10px] text-[#707D9E]">
                  Order: {currentThread.orderNumber} ({formatINR(currentThread.orderAmount)})
                </p>
              </div>
            </div>

            {currentThread.unpaidAmount > 0 && (
              <div className="text-right">
                <span className="text-[10px] text-[#707D9E] block">Balance Due</span>
                <span className="font-mono text-xs font-bold text-[#FF6977]">
                  {formatINR(currentThread.unpaidAmount)}
                </span>
              </div>
            )}
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {currentThread.messages.map((m) => {
              const isCustomer = m.sender === "customer";
              return (
                <div
                  key={m.id}
                  className={cn("flex flex-col max-w-[80%]", isCustomer ? "self-start" : "self-end items-end")}
                >
                  <div
                    className={cn(
                      "p-3 rounded-2xl text-xs leading-relaxed",
                      isCustomer
                        ? "bg-[#151D32] border border-[#252F49] text-[#F4F6FF] rounded-tl-sm"
                        : "bg-[#8065FF] text-white rounded-tr-sm shadow-[0_2px_12px_rgba(128,101,255,0.3)]"
                    )}
                  >
                    {m.text}
                  </div>
                  <span className="text-[9px] text-[#707D9E] font-mono mt-1 px-1">
                    {m.time}
                  </span>
                </div>
              );
            })}

            {/* Jarvis Smart Suggestion Box */}
            {currentThread.suggestedReply && (
              <div className="mt-4 p-3.5 rounded-xl bg-gradient-to-br from-[#131B32] to-[#0E1528] border border-[#8065FF]/60 shadow-[0_4px_16px_rgba(128,101,255,0.15)] space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#8065FF]" />
                    <span className="text-[11px] font-bold text-[#F4F6FF] uppercase tracking-wider">
                      Jarvis Prepared Response
                    </span>
                  </div>
                  <Badge variant="primary" className="text-[9px]">
                    Verified Commitment
                  </Badge>
                </div>

                <div className="p-2.5 rounded bg-[#080B14] border border-[#252F49] text-xs text-[#A0AAC4] leading-relaxed">
                  {currentThread.suggestedReply.text}
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-[#707D9E]">
                    {currentThread.suggestedReply.actionSummary}
                  </span>

                  {currentThread.suggestedReply.hasLink ? (
                    <Button
                      size="sm"
                      onClick={handleOpenApproval}
                      className="bg-[#8065FF] hover:bg-[#6E50FF] text-white font-semibold text-xs h-7 px-3 gap-1.5 cursor-pointer shadow-[0_0_12px_rgba(128,101,255,0.35)]"
                    >
                      <span>Review & Send Link</span>
                      <ArrowRight className="w-3 h-3" />
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => setSuccessBanner("Checklist confirmed.")}
                      className="bg-[#27D99A] hover:bg-[#20B882] text-black font-semibold text-xs h-7 px-3 gap-1.5 cursor-pointer"
                    >
                      <Check className="w-3 h-3" />
                      <span>Confirm Note</span>
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Quick Reply Bar */}
          <div className="p-3 border-t border-[#252F49] bg-[#0B1020] flex items-center gap-2 shrink-0">
            <input
              type="text"
              placeholder={`Reply to ${currentThread.customerName} on ${currentThread.platform}…`}
              value={replyInput}
              onChange={(e) => setReplyInput(e.target.value)}
              className="flex-1 h-8 px-3 bg-[#101629] border border-[#252F49] rounded-md text-xs text-[#F4F6FF] placeholder-[#707D9E] focus:outline-none focus:border-[#8065FF]"
            />
            <Button
              size="sm"
              disabled={!replyInput}
              onClick={() => {
                setReplyInput("");
                setSuccessBanner(`Message queued for ${currentThread.customerName}`);
                setTimeout(() => setSuccessBanner(null), 3000);
              }}
              className="h-8 px-3 bg-[#8065FF] hover:bg-[#6E50FF] text-white text-xs gap-1 cursor-pointer"
            >
              <Send className="w-3 h-3" />
              <span>Send</span>
            </Button>
          </div>
        </div>

        {/* Right Sidebar: Order & Customer Context (Hidden on small mobile) */}
        <div className="hidden xl:flex w-72 border-l border-[#252F49] bg-[#0B1020] flex-col shrink-0 p-4 space-y-4 overflow-y-auto">
          <div className="flex items-center gap-2 pb-2 border-b border-[#252F49]">
            <ShoppingBag className="w-4 h-4 text-[#8065FF]" />
            <h2 className="text-xs font-bold text-[#F4F6FF] uppercase tracking-wider">
              Order Context
            </h2>
          </div>

          {/* Customer Card */}
          <div className="p-3 rounded-xl bg-[#101629] border border-[#252F49] space-y-1.5 text-xs">
            <span className="text-[10px] text-[#707D9E] uppercase font-semibold">Customer</span>
            <p className="font-semibold text-[#F4F6FF]">{currentThread.customerName}</p>
            <p className="text-[11px] text-[#A0AAC4] font-mono">{currentThread.phoneOrHandle}</p>
          </div>

          {/* Order Details */}
          <div className="p-3 rounded-xl bg-[#101629] border border-[#252F49] space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#707D9E] uppercase font-semibold">Order Details</span>
              <span className="font-mono text-[10px] text-[#8065FF]">{currentThread.orderNumber}</span>
            </div>

            <div className="space-y-1 pt-1">
              {currentThread.items.map((item, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-[11px] text-[#F4F6FF]">
                  <span className="text-[#8065FF]">·</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-[#252F49]/60 space-y-1 text-[11px]">
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Total Amount:</span>
                <span className="font-mono text-[#F4F6FF] font-semibold">{formatINR(currentThread.orderAmount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#707D9E]">Paid (UPI):</span>
                <span className="font-mono text-[#27D99A] font-semibold">{formatINR(currentThread.paidAmount)}</span>
              </div>
              {currentThread.unpaidAmount > 0 && (
                <div className="flex justify-between pt-1 border-t border-[#252F49]/40">
                  <span className="text-[#FF6977] font-medium">Still Owed:</span>
                  <span className="font-mono text-[#FF6977] font-bold">{formatINR(currentThread.unpaidAmount)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Connected Rules */}
          <div className="p-3 rounded-xl bg-[#101629] border border-[#252F49] space-y-1 text-xs">
            <span className="text-[10px] text-[#707D9E] uppercase font-semibold">Active Rules</span>
            <p className="text-[11px] text-[#A0AAC4]">
              Payment reminders require your approval before sending payment links to customers.
            </p>
          </div>
        </div>
      </div>

      {/* Approval Modal */}
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
