"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  MessageSquare,
  CheckSquare,
  Wallet,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/store";
import { useDashboard } from "@/lib/api";

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { data: dashboardData } = useDashboard();

  const metrics = dashboardData?.metrics;
  const pendingApprovalsCount = metrics?.pending_approvals || 0;
  const openCasesCount = metrics?.total_open_cases || 0;

  const NAV_ITEMS = [
    { label: "Home", href: "/today", icon: Home },
    { label: "Messages", href: "/messages", icon: MessageSquare, badge: "3" },
    { label: "Tasks", href: "/tasks", icon: CheckSquare, badge: openCasesCount > 0 ? String(openCasesCount) : undefined },
    { label: "Money", href: "/money", icon: Wallet },
    { label: "More", href: "/more", icon: MoreHorizontal, badge: pendingApprovalsCount > 0 ? String(pendingApprovalsCount) : undefined },
  ];

  return (
    <>
      {/* Desktop Persistent Left Rail */}
      <aside
        className={cn(
          "hidden lg:flex border-r border-[#252F49] bg-[#0B1020] flex-col justify-between select-none flex-shrink-0 h-screen sticky top-0 transition-all duration-200 z-30",
          sidebarCollapsed ? "w-[68px] p-3" : "w-[220px] p-4"
        )}
        role="navigation"
        aria-label="Main navigation"
      >
        <div>
          {/* Brand Header */}
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#252F49]/70">
            <div className={cn("flex items-center gap-2.5", sidebarCollapsed && "justify-center w-full")}>
              <div className="w-8 h-8 rounded-lg bg-[#8065FF]/15 border border-[#8065FF]/40 text-[#8065FF] flex items-center justify-center font-bold text-sm shadow-[0_0_12px_rgba(128,101,255,0.25)] shrink-0">
                J
              </div>
              {!sidebarCollapsed && (
                <div className="overflow-hidden">
                  <div className="flex items-center gap-1.5">
                    <h1 className="text-sm font-bold tracking-tight text-[#F4F6FF] leading-none">
                      Jarvis
                    </h1>
                    <span className="text-[9px] px-1 py-0.2 bg-[#252F49] text-[#29D8C5] rounded font-mono font-medium">
                      v2.0
                    </span>
                  </div>
                  <p className="text-[10px] text-[#707D9E] tracking-wider uppercase mt-1 truncate font-medium">
                    Aura Weaves & Jewels
                  </p>
                </div>
              )}
            </div>
            {!sidebarCollapsed && (
              <button
                onClick={toggleSidebar}
                className="p-1 rounded-md text-[#707D9E] hover:text-[#F4F6FF] hover:bg-[#151D32] transition-colors cursor-pointer"
                aria-label="Collapse sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1" aria-label="Primary destinations">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive =
                pathname === item.href ||
                (item.href === "/today" && pathname === "/");

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium border transition-all group relative",
                    isActive
                      ? "bg-[#151D32] border-[#8065FF]/40 text-[#F4F6FF] shadow-sm font-semibold"
                      : "border-transparent text-[#A0AAC4] hover:text-[#F4F6FF] hover:bg-[#151D32]/60 hover:border-[#252F49]/40",
                    sidebarCollapsed && "justify-center px-0"
                  )}
                  aria-current={isActive ? "page" : undefined}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  <Icon
                    className={cn(
                      "w-4 h-4 shrink-0 transition-colors",
                      isActive ? "text-[#8065FF]" : "text-[#707D9E] group-hover:text-[#A0AAC4]"
                    )}
                    aria-hidden="true"
                  />
                  {!sidebarCollapsed && (
                    <>
                      <span className="flex-1 truncate">{item.label}</span>
                      {item.badge && (
                        <span
                          className={cn(
                            "px-1.5 py-0.5 rounded text-[9px] font-mono font-bold leading-none",
                            isActive
                              ? "bg-[#8065FF]/20 text-[#8065FF] border border-[#8065FF]/30"
                              : "bg-[#1A2440] text-[#707D9E]"
                          )}
                        >
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                  {isActive && (
                    <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r bg-[#8065FF]" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Section: Workspace Status & Collapse Toggle */}
        <div className="pt-3 border-t border-[#252F49]/70 space-y-2">
          {sidebarCollapsed ? (
            <button
              onClick={toggleSidebar}
              className="w-full flex items-center justify-center p-2 rounded-md text-[#707D9E] hover:text-[#F4F6FF] hover:bg-[#151D32] transition-colors cursor-pointer"
              aria-label="Expand sidebar"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <div className="bg-[#101629] border border-[#252F49] rounded-lg p-2.5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold text-[#F4F6FF] flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#27D99A]" />
                  Your Assistant
                </span>
                <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-[#27D99A]/15 text-[#27D99A]">
                  Active
                </span>
              </div>
              <p className="text-[10px] text-[#A0AAC4] font-medium leading-tight">
                Protecting orders & money
              </p>
              <div className="mt-1.5 pt-1.5 border-t border-[#252F49]/50 flex items-center justify-between text-[9px] text-[#707D9E]">
                <span>WhatsApp · Razorpay · Bank</span>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Mobile Bottom Tab Navigation */}
      <nav
        className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#0B1020]/95 backdrop-blur-md border-t border-[#252F49] flex items-center justify-around h-14 px-2"
        role="navigation"
        aria-label="Mobile navigation"
      >
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href === "/today" && pathname === "/");

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-0.5 py-1 px-3 rounded-md text-[10px] font-medium relative",
                isActive ? "text-[#8065FF]" : "text-[#707D9E] hover:text-[#A0AAC4]"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{item.label}</span>
              {isActive && (
                <span className="w-1 h-1 rounded-full bg-[#8065FF] mt-0.5" />
              )}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
