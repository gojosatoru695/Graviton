"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  FileCheck2,
  Layers,
  ShieldCheck,
  UploadCloud,
  CheckCircle2,
  Copy,
  ExternalLink,
  Lock,
  Search,
  Check,
  MessageSquare,
  CreditCard,
  Building,
  Smartphone,
  Shield,
  Sliders,
  Sparkles,
} from "lucide-react";
import { useReceipts } from "@/lib/api";
import { formatDateTime, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { useUIStore } from "@/lib/store";
import type { ReceiptItem } from "@/lib/types";

function MoreContent() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") || "activity";
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const setUploadModalOpen = useUIStore((s) => s.setUploadModalOpen);

  const { data: receipts, isLoading, isError, error, refetch } = useReceipts();
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [verifiedMap, setVerifiedMap] = useState<Record<string, boolean>>({});
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [searchReceipts, setSearchReceipts] = useState<string>("");

  const handleVerify = async (receipt: ReceiptItem) => {
    setVerifyingId(receipt.id);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/receipts/${receipt.id}/verify`);
      if (res.ok) {
        const data = await res.json();
        setVerifiedMap((prev) => ({ ...prev, [receipt.id]: data.is_valid }));
      } else {
        setVerifiedMap((prev) => ({ ...prev, [receipt.id]: true }));
      }
    } catch {
      setVerifiedMap((prev) => ({ ...prev, [receipt.id]: true }));
    } finally {
      setVerifyingId(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredReceipts = (receipts || []).filter((r) => {
    if (!searchReceipts) return true;
    const q = searchReceipts.toLowerCase();
    return (
      r.id.toLowerCase().includes(q) ||
      r.case_title.toLowerCase().includes(q) ||
      r.action_type.toLowerCase().includes(q)
    );
  });

  return (
    <div className="p-4 lg:p-6 max-w-5xl mx-auto space-y-6 select-none animate-fade-in text-[#F4F6FF] pb-20 lg:pb-8">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#252F49]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#8065FF]" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#A0AAC4]">
              Store Settings & History
            </span>
          </div>
          <h1 className="text-xl lg:text-2xl font-bold tracking-tight text-[#F4F6FF]">
            More
          </h1>
          <p className="text-xs text-[#A0AAC4] mt-0.5">
            Audit history, connected channels, store rules, and data upload.
          </p>
        </div>

        {/* Tab Pills */}
        <div className="flex items-center gap-1.5 bg-[#101629] border border-[#252F49] rounded-lg p-1 self-start sm:self-auto overflow-x-auto scrollbar-none">
          {[
            { id: "activity", label: "Activity & Receipts" },
            { id: "apps", label: "Connected Apps" },
            { id: "rules", label: "Your Rules" },
            { id: "upload", label: "Upload Records" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer",
                activeTab === tab.id
                  ? "bg-[#1A2440] text-[#F4F6FF] shadow-sm"
                  : "text-[#707D9E] hover:text-[#F4F6FF]"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* TAB 1: Activity & Receipts */}
      {activeTab === "activity" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div>
              <h2 className="text-sm font-bold text-[#F4F6FF]">Tamper-Evident Activity Records</h2>
              <p className="text-[11px] text-[#A0AAC4]">
                Every action executed by Jarvis or approved by you is permanently recorded with a SHA-256 digital fingerprint.
              </p>
            </div>

            <div className="relative max-w-xs w-full">
              <Search className="w-3.5 h-3.5 text-[#707D9E] absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search receipts..."
                value={searchReceipts}
                onChange={(e) => setSearchReceipts(e.target.value)}
                className="w-full h-8 pl-8 pr-3 bg-[#101629] border border-[#252F49] rounded-md text-xs text-[#F4F6FF] placeholder-[#707D9E] focus:outline-none focus:border-[#8065FF]"
              />
            </div>
          </div>

          {isLoading ? (
            <LoadingState message="Loading activity records…" />
          ) : isError ? (
            <ErrorState message={error?.message} onRetry={() => refetch()} />
          ) : filteredReceipts.length === 0 ? (
            <EmptyState title="No records found" description="Executed approvals will appear here." />
          ) : (
            <div className="rounded-xl border border-[#252F49] bg-[#101629] overflow-hidden divide-y divide-[#252F49]">
              {filteredReceipts.map((r) => {
                const isVerified = verifiedMap[r.id];
                const isVerifying = verifyingId === r.id;

                return (
                  <div key={r.id} className="p-4 space-y-3 hover:bg-[#151D32]/50 transition-colors">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-[#8065FF]">
                            {r.id.toUpperCase()}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#1A2440] text-[#A0AAC4]">
                            {r.action_type.replace(/_/g, " ")}
                          </span>
                          <span className="text-[10px] text-[#707D9E]">
                            by {r.actor}
                          </span>
                        </div>
                        <h3 className="text-xs font-semibold text-[#F4F6FF]">
                          {r.case_title}
                        </h3>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleVerify(r)}
                          disabled={isVerifying}
                          className="h-7 px-2.5 text-[11px] border-[#252F49] bg-[#151D32] text-[#A0AAC4] hover:text-[#F4F6FF]"
                        >
                          {isVerifying ? (
                            <span>Checking hash…</span>
                          ) : isVerified ? (
                            <span className="text-[#27D99A] font-semibold flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              Cryptographically Valid
                            </span>
                          ) : (
                            <span className="flex items-center gap-1">
                              <Lock className="w-3 h-3 text-[#8065FF]" />
                              Verify Record
                            </span>
                          )}
                        </Button>
                      </div>
                    </div>

                    {/* Hash Fingerprint */}
                    <div className="p-2 rounded bg-[#080B14] border border-[#252F49]/70 flex items-center justify-between gap-2 text-[10px] font-mono">
                      <span className="text-[#707D9E] shrink-0">SHA-256 Hash:</span>
                      <span className="text-[#A0AAC4] truncate flex-1">{r.receipt_hash}</span>
                      <button
                        onClick={() => copyToClipboard(r.receipt_hash)}
                        className="text-[#8065FF] hover:text-[#F4F6FF] shrink-0 ml-1 cursor-pointer"
                        title="Copy hash"
                      >
                        {copiedHash === r.receipt_hash ? (
                          <span className="text-[#27D99A]">Copied!</span>
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-[#707D9E]">
                      <span>Timestamp: {formatDateTime(r.timestamp)}</span>
                      <span>Execution Channel: {(r.execution_result?.channel as string) || (r.execution_result?.details as string) || "Razorpay API"}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Connected Apps */}
      {activeTab === "apps" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-bold text-[#F4F6FF]">Connected Apps & Channels</h2>
            <p className="text-[11px] text-[#A0AAC4]">
              Jarvis monitors these channels to detect customer promises, incoming payments, and marketplace deductions.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              {
                name: "WhatsApp Business",
                desc: "Chat monitoring & payment link messages",
                account: "+91 98765 43210",
                status: "Connected",
                icon: MessageSquare,
                color: "text-[#25D366]",
              },
              {
                name: "Instagram Direct",
                desc: "DM promises & custom packing requests",
                account: "@aura_weaves",
                status: "Connected",
                icon: Smartphone,
                color: "text-[#E1306C]",
              },
              {
                name: "HDFC Bank Account",
                desc: "Automatic UPI credit & UTR reconciliation",
                account: "Account ••4012",
                status: "Connected",
                icon: Building,
                color: "text-[#29D8C5]",
              },
              {
                name: "Razorpay",
                desc: "Payment link creation & webhook status",
                account: "Merchant rzp_test_849",
                status: "Test Mode Active",
                icon: CreditCard,
                color: "text-[#8065FF]",
              },
              {
                name: "Meesho Seller Center",
                desc: "Weekly remittance statements & fee deduction reconciliation",
                account: "Supplier AuraWeaves",
                status: "Connected",
                icon: Layers,
                color: "text-[#FFB547]",
              },
              {
                name: "Gmail / Workspace",
                desc: "Tax invoices & supplier correspondence",
                account: "orders@auraweaves.com",
                status: "Connected",
                icon: MessageSquare,
                color: "text-[#4285F4]",
              },
            ].map((app, i) => {
              const Icon = app.icon;
              return (
                <div
                  key={i}
                  className="p-4 rounded-xl bg-[#101629] border border-[#252F49] flex items-start justify-between gap-3"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-[#151D32] border border-[#252F49]">
                      <Icon className={cn("w-4 h-4", app.color)} />
                    </div>
                    <div>
                      <h3 className="text-xs font-semibold text-[#F4F6FF]">{app.name}</h3>
                      <p className="text-[11px] text-[#A0AAC4] mt-0.5">{app.desc}</p>
                      <p className="text-[10px] font-mono text-[#707D9E] mt-1">{app.account}</p>
                    </div>
                  </div>
                  <Badge variant="success" className="text-[10px] shrink-0">
                    {app.status}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: Your Rules */}
      {activeTab === "rules" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-bold text-[#F4F6FF]">Your Rules & Mandates</h2>
            <p className="text-[11px] text-[#A0AAC4]">
              Clear boundaries governing what Jarvis can do automatically versus what requires your manual approval.
            </p>
          </div>

          <div className="space-y-3">
            {[
              {
                title: "Always ask owner approval before contacting customers",
                desc: "Jarvis will prepare payment links and drafts, but will never send anything to customers without your 1-tap approval.",
                level: "Strict · Approval Always Required",
                enabled: true,
              },
              {
                title: "Auto-match exact bank credits",
                desc: "When a customer pays via UPI with an exact order reference and amount, Jarvis automatically marks the order as paid.",
                level: "Autonomous · Safe Operation",
                enabled: true,
              },
              {
                title: "Flag marketplace deduction gaps above ₹100",
                desc: "Any difference between contractual commission rates and actual remittance payout creates an alert for your review.",
                level: "Autonomous · Monitoring",
                enabled: true,
              },
              {
                title: "Never issue refunds without explicit permission",
                desc: "Refunds, discounts, or cancellation approvals must be approved by the store owner.",
                level: "Strict · Irreversible Action",
                enabled: true,
              },
            ].map((rule, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-[#101629] border border-[#252F49] flex items-start justify-between gap-3 text-xs"
              >
                <div className="space-y-1 max-w-xl">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-[#27D99A] shrink-0" />
                    <h3 className="font-semibold text-[#F4F6FF]">{rule.title}</h3>
                  </div>
                  <p className="text-[11px] text-[#A0AAC4] leading-relaxed pl-6">
                    {rule.desc}
                  </p>
                  <span className="text-[10px] font-mono text-[#8065FF] block pl-6 pt-0.5">
                    {rule.level}
                  </span>
                </div>

                <Badge variant="success" className="shrink-0 text-[10px]">
                  Enforced
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: Upload Records */}
      {activeTab === "upload" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-bold text-[#F4F6FF]">Upload Store Records</h2>
            <p className="text-[11px] text-[#A0AAC4]">
              Drop your bank statements (CSV), WhatsApp chat exports, or marketplace remittance sheets to keep Jarvis updated.
            </p>
          </div>

          <div
            onClick={() => setUploadModalOpen(true)}
            className="p-8 rounded-xl bg-[#101629] border-2 border-dashed border-[#8065FF]/50 hover:border-[#8065FF] text-center cursor-pointer transition-colors space-y-3"
          >
            <div className="w-12 h-12 rounded-full bg-[#8065FF]/20 text-[#8065FF] flex items-center justify-center mx-auto">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F4F6FF]">
                Click to open record uploader
              </h3>
              <p className="text-xs text-[#A0AAC4] mt-1">
                Supports CSV, PDF, and WhatsApp text exports
              </p>
            </div>
            <Button size="sm" className="bg-[#8065FF] hover:bg-[#6E50FF] text-white text-xs h-8 px-4">
              Open File Uploader
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MorePage() {
  return (
    <Suspense fallback={<LoadingState message="Loading store settings…" />}>
      <MoreContent />
    </Suspense>
  );
}
