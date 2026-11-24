"use client";

import { useState } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  X,
  FileCheck,
  AlertTriangle,
  ArrowRight,
  Database,
  Layers,
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
import { useUIStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function UploadModal() {
  const isOpen = useUIStore((s) => s.uploadModalOpen);
  const setOpen = useUIStore((s) => s.setUploadModalOpen);

  const [step, setStep] = useState<1 | 2 | 3>(1); // 1: Select files, 2: Preview & Validate, 3: Import Summary
  const [ordersFile, setOrdersFile] = useState<File | null>(null);
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [settlementFile, setSettlementFile] = useState<File | null>(null);
  const [whatsappFile, setWhatsappFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProceedToPreview = () => {
    if (!ordersFile && !bankFile && !settlementFile && !whatsappFile) {
      setError("Please select at least one file to validate.");
      return;
    }
    setError(null);
    setStep(2);
  };

  const handleConfirmImport = async () => {
    setUploading(true);
    setError(null);
    await new Promise((r) => setTimeout(r, 900));
    setUploading(false);
    setStep(3);
  };

  const handleClose = () => {
    setOpen(false);
    setStep(1);
    setOrdersFile(null);
    setBankFile(null);
    setSettlementFile(null);
    setWhatsappFile(null);
    setError(null);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setOpen}>
      <DialogContent className="max-w-xl bg-[#101629] border border-[#252F49] text-[#F4F6FF] p-6 shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
        <DialogHeader className="border-b border-[#252F49] pb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono uppercase font-bold text-[#8065FF] flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#29D8C5]" />
              Guided Data Import Wizard
            </span>
            <div className="flex items-center gap-1 text-[10px] font-mono text-[#707D9E]">
              <span className={cn(step >= 1 ? "text-[#8065FF] font-bold" : "")}>1. Select</span>
              <span>›</span>
              <span className={cn(step >= 2 ? "text-[#8065FF] font-bold" : "")}>2. Validate</span>
              <span>›</span>
              <span className={cn(step === 3 ? "text-[#27D99A] font-bold" : "")}>3. Summary</span>
            </div>
          </div>
          <DialogTitle className="text-base font-bold text-[#F4F6FF]">
            {step === 1 ? "Select Commerce & Financial Files" : step === 2 ? "Preview & Record Validation" : "Import Summary & Graph Update"}
          </DialogTitle>
          <DialogDescription className="text-xs text-[#A0AAC4]">
            Normalize orders, bank statements, settlements, and customer chats into the evidence graph.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="p-3 rounded-lg bg-[#FF6977]/15 border border-[#FF6977]/30 text-[#FF6977] text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {/* STEP 1: File Selection */}
        {step === 1 && (
          <div className="space-y-3 py-1">
            {[
              { label: "Orders Master Export", type: "CSV", desc: "Order numbers, gross amounts, dates, and delivery tracking", file: ordersFile, set: setOrdersFile },
              { label: "Bank Statement / UPI Credits", type: "CSV", desc: "HDFC / ICICI statement with UTR references and credits", file: bankFile, set: setBankFile },
              { label: "Marketplace Settlement Report", type: "CSV", desc: "Meesho / Amazon remittance lines, commission, and logistics", file: settlementFile, set: setSettlementFile },
              { label: "WhatsApp Customer Chat", type: "TXT", desc: "Exported chat history containing commitments and promises", file: whatsappFile, set: setWhatsappFile },
            ].map((f, i) => (
              <div key={i} className="p-3 rounded-lg bg-[#151D32] border border-[#252F49] flex items-center justify-between gap-3 text-xs">
                <div className="space-y-0.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[#F4F6FF]">{f.label}</span>
                    <Badge variant="outline" className="font-mono text-[9px] py-0 px-1">{f.type}</Badge>
                  </div>
                  <p className="text-[11px] text-[#707D9E] truncate">{f.desc}</p>
                  {f.file && (
                    <span className="text-[10px] text-[#29D8C5] font-mono block mt-1">
                      Selected: {f.file.name} ({(f.file.size / 1024).toFixed(1)} KB)
                    </span>
                  )}
                </div>

                <label className="shrink-0 cursor-pointer">
                  <span className="h-7 px-2.5 rounded-md bg-[#1A2440] hover:bg-[#252F49] border border-[#252F49] text-xs font-semibold text-[#F4F6FF] inline-flex items-center gap-1.5 transition-colors">
                    <UploadCloud className="w-3.5 h-3.5 text-[#8065FF]" />
                    <span>{f.file ? "Change" : "Browse"}</span>
                  </span>
                  <input
                    type="file"
                    accept={f.type === "CSV" ? ".csv" : ".txt"}
                    className="hidden"
                    onChange={(e) => f.set(e.target.files?.[0] || null)}
                  />
                </label>
              </div>
            ))}

            <div className="flex items-center justify-between pt-3 border-t border-[#252F49]">
              <span className="text-[10px] text-[#707D9E]">Supported formats: UTF-8 CSV, TXT chat export</span>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={handleClose}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleProceedToPreview} className="bg-[#8065FF] hover:bg-[#6E50FF] font-semibold">
                  <span>Preview & Validate</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Preview & Validation */}
        {step === 2 && (
          <div className="space-y-3 py-1 text-xs">
            <div className="p-3.5 rounded-lg bg-[#151D32] border border-[#252F49] space-y-2">
              <span className="font-bold text-[#F4F6FF] text-xs block">Schema Mapping & Data Integrity Check</span>
              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between items-center text-[#A0AAC4]">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#27D99A]" />
                    Orders schema validation:
                  </span>
                  <span className="font-mono text-[#F4F6FF]">60 valid rows (0 errors)</span>
                </div>
                <div className="flex justify-between items-center text-[#A0AAC4]">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#27D99A]" />
                    Bank credits UTR format:
                  </span>
                  <span className="font-mono text-[#F4F6FF]">47 credits (100% valid UTR)</span>
                </div>
                <div className="flex justify-between items-center text-[#A0AAC4]">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#27D99A]" />
                    Settlement lines:
                  </span>
                  <span className="font-mono text-[#F4F6FF]">1 bi-weekly remittance report</span>
                </div>
                <div className="flex justify-between items-center text-[#A0AAC4]">
                  <span className="flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-[#FFB547]" />
                    WhatsApp natural language scan:
                  </span>
                  <span className="font-mono text-[#FFB547]">8 commitments detected</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-[#252F49]">
              <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button size="sm" onClick={handleConfirmImport} disabled={uploading} className="bg-[#8065FF] hover:bg-[#6E50FF] font-semibold">
                {uploading ? "Normalizing Records…" : "Confirm & Ingest"}
              </Button>
            </div>
          </div>
        )}

        {/* STEP 3: Import Summary & Graph Update */}
        {step === 3 && (
          <div className="space-y-4 py-1 text-xs">
            <div className="p-4 rounded-lg bg-[#27D99A]/10 border border-[#27D99A]/30 space-y-2.5">
              <div className="flex items-center gap-2 font-bold text-[#27D99A] text-sm">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>Evidence Graph Successfully Updated</span>
              </div>
              <ul className="space-y-1.5 text-[11px] text-[#A0AAC4]">
                <li className="flex justify-between">
                  <span>Orders ingested:</span>
                  <span className="font-mono font-bold text-[#F4F6FF]">60 orders</span>
                </li>
                <li className="flex justify-between">
                  <span>Bank deposits verified:</span>
                  <span className="font-mono font-bold text-[#F4F6FF]">47 transactions</span>
                </li>
                <li className="flex justify-between">
                  <span>Commitments extracted:</span>
                  <span className="font-mono font-bold text-[#F4F6FF]">8 promises</span>
                </li>
                <li className="flex justify-between pt-1 border-t border-[#252F49] text-[#8065FF] font-semibold">
                  <span>Anomalies & Cases generated:</span>
                  <span className="font-mono font-bold">5 cases</span>
                </li>
              </ul>
            </div>

            <Button onClick={handleClose} className="w-full bg-[#8065FF] hover:bg-[#6E50FF] font-semibold h-8 text-xs">
              Done — Open Investigation Workbench
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
