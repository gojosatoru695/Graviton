"use client";

import React from "react";
import { CheckCircle2, Clock, CircleDot, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CaseStatus } from "@/lib/types";

interface CaseActionStripProps {
  status: CaseStatus;
  hasPendingAction?: boolean;
}

const STAGES = [
  { id: "DETECTED", label: "Case Detected" },
  { id: "EVIDENCE", label: "Evidence Collected" },
  { id: "INVESTIGATION", label: "Investigation" },
  { id: "VERIFICATION", label: "Verification" },
  { id: "APPROVAL", label: "Awaiting Approval" },
  { id: "COMPLETED", label: "Action Completed" },
];

export function CaseActionStrip({ status, hasPendingAction }: CaseActionStripProps) {
  // Determine current active step index based on CaseStatus
  let activeIndex = 3; // Default at verification
  if (status === "OPEN") activeIndex = 1;
  else if (status === "INVESTIGATING") activeIndex = 2;
  else if (status === "ACTION_PROPOSED" || hasPendingAction) activeIndex = 4;
  else if (status === "ACTION_EXECUTED") activeIndex = 5;
  else if (status === "DISMISSED") activeIndex = 5;

  return (
    <div className="h-9 px-4 bg-[#101629] border-b border-[#252F49] flex items-center justify-between text-xs overflow-x-auto select-none shrink-0">
      <div className="flex items-center gap-1 sm:gap-2">
        <span className="text-[10px] uppercase font-mono font-bold text-[#707D9E] mr-1 hidden sm:inline">
          Workflow:
        </span>
        {STAGES.map((stage, idx) => {
          const isDone = idx < activeIndex;
          const isCurrent = idx === activeIndex;
          const isFuture = idx > activeIndex;

          return (
            <React.Fragment key={stage.id}>
              <div
                className={cn(
                  "flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium transition-colors whitespace-nowrap",
                  isDone && "text-[#29D8C5]",
                  isCurrent && "bg-[#8065FF]/15 text-[#8065FF] font-semibold border border-[#8065FF]/30",
                  isFuture && "text-[#707D9E]"
                )}
              >
                {isDone ? (
                  <CheckCircle2 className="w-3 h-3 text-[#29D8C5] shrink-0" />
                ) : isCurrent ? (
                  <CircleDot className="w-3 h-3 text-[#8065FF] animate-pulse shrink-0" />
                ) : (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#252F49] shrink-0" />
                )}
                <span>{stage.label}</span>
              </div>
              {idx < STAGES.length - 1 && (
                <span className="text-[#252F49] text-[10px]">›</span>
              )}
            </React.Fragment>
          );
        })}
      </div>

      <div className="hidden md:flex items-center gap-1.5 text-[10px] font-mono text-[#A0AAC4]">
        <span className="text-[#707D9E]">Next:</span>
        <span className="text-[#F4F6FF] font-semibold">
          {activeIndex === 4 ? "Owner Human Approval" : activeIndex === 5 ? "Archived Receipt" : "Synthesizing Evidence"}
        </span>
      </div>
    </div>
  );
}
