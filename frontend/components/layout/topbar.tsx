"use client";

import { useState } from "react";
import {
  UploadCloud,
  Sparkles,
  Search,
  Bell,
  Command,
  Database,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUIStore } from "@/lib/store";

export function Topbar() {
  const setUploadModalOpen = useUIStore((s) => s.setUploadModalOpen);
  const setAskJarvisOpen = useUIStore((s) => s.setAskJarvisOpen);
  const searchQuery = useUIStore((s) => s.searchQuery);
  const setSearchQuery = useUIStore((s) => s.setSearchQuery);
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="h-12 border-b border-[#252F49] bg-[#080B14]/90 backdrop-blur-md sticky top-0 z-20 flex items-center justify-between px-4 lg:px-6 select-none">
      {/* Left: Global Search & Scope */}
      <div className="flex items-center gap-3 flex-1 max-w-md">
        <div className="relative w-full max-w-xs hidden sm:block">
          <Search className="w-3.5 h-3.5 text-[#707D9E] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search orders, UTR, cases, promises..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-7 pl-8 pr-8 bg-[#101629] border border-[#252F49] rounded-md text-xs text-[#F4F6FF] placeholder-[#707D9E] focus:outline-none focus:border-[#8065FF] transition-colors"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 text-[9px] font-mono text-[#707D9E] border border-[#252F49] px-1 py-0.2 rounded bg-[#080B14]">
            <Command className="w-2.5 h-2.5" />
            <span>K</span>
          </div>
        </div>

        {/* Assistant status pill */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#101629] border border-[#252F49] text-[11px] text-[#A0AAC4]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#27D99A] animate-pulse" aria-hidden="true" />
          <span className="text-[#27D99A] font-semibold text-[10px]">JARVIS ACTIVE</span>
          <span className="text-[#707D9E]">·</span>
          <span>Aura Weaves & Jewels</span>
        </div>
      </div>

      {/* Right: Actions, Notifications & User */}
      <div className="flex items-center gap-2">
        {/* Upload Records */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setUploadModalOpen(true)}
          className="gap-1.5 h-7 px-2.5 text-xs text-[#F4F6FF] border-[#252F49] bg-[#101629] hover:bg-[#151D32]"
          aria-label="Upload records"
        >
          <UploadCloud className="w-3.5 h-3.5 text-[#8065FF]" aria-hidden="true" />
          <span className="hidden sm:inline">Upload records</span>
        </Button>

        {/* Ask Jarvis */}
        <Button
          size="sm"
          onClick={() => setAskJarvisOpen(true)}
          className="gap-1.5 h-7 px-2.5 text-xs bg-[#8065FF] text-white hover:bg-[#6E50FF] font-semibold shadow-[0_0_12px_rgba(128,101,255,0.3)]"
          aria-label="Ask Jarvis contextual assistant"
        >
          <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
          <span>Ask Jarvis</span>
        </Button>

        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="w-7 h-7 rounded-md border border-[#252F49] bg-[#101629] hover:bg-[#151D32] text-[#A0AAC4] hover:text-[#F4F6FF] flex items-center justify-center transition-colors relative cursor-pointer"
            aria-label="Notifications"
          >
            <Bell className="w-3.5 h-3.5" />
            <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-[#FFB547]" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-72 bg-[#101629] border border-[#252F49] rounded-xl shadow-[0_8px_24px_rgba(0,0,0,0.6)] p-3 text-xs z-50 animate-slide-up">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#252F49]">
                <span className="font-semibold text-[#F4F6FF]">Alerts & Approvals</span>
                <span className="text-[10px] text-[#8065FF] font-medium">3 pending</span>
              </div>
              <div className="space-y-2">
                <div className="p-2 rounded bg-[#151D32] border border-[#252F49]/80">
                  <p className="font-medium text-[#F4F6FF] text-[11px]">₹1,550 Meesho Variance</p>
                  <p className="text-[10px] text-[#A0AAC4]">Dispute dossier prepared for review.</p>
                </div>
                <div className="p-2 rounded bg-[#151D32] border border-[#252F49]/80">
                  <p className="font-medium text-[#F4F6FF] text-[11px]">Unrecorded Silk Scrunchie</p>
                  <p className="text-[10px] text-[#A0AAC4]">Promise detected for Ananya Sharma.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Seller Avatar */}
        <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-[#252F49]">
          <div className="w-6 h-6 rounded-full bg-[#1A2440] border border-[#252F49] text-[10px] font-bold text-[#8065FF] flex items-center justify-center">
            P
          </div>
          <span className="text-xs font-medium text-[#F4F6FF] hidden md:inline">
            Priya S.
          </span>
        </div>
      </div>
    </header>
  );
}
