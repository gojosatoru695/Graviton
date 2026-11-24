import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Skeleton ───
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-[#1A2440]/80", className)}
      {...props}
    />
  );
}

// ─── Loading State ───
function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[350px] p-8" role="status" aria-label={message}>
      <div className="flex items-center gap-2.5 text-xs text-[#A0AAC4]">
        <span className="w-2 h-2 rounded-full bg-[#8065FF] animate-ping" />
        <span className="font-medium tracking-wide">{message}</span>
      </div>
    </div>
  );
}

// ─── Empty State ───
function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[320px] p-8 text-center bg-[#101629]/50 border border-[#252F49]/60 rounded-xl">
      {icon && <div className="mb-3 text-[#707D9E]">{icon}</div>}
      <h3 className="text-sm font-semibold text-[#F4F6FF] mb-1.5">{title}</h3>
      <p className="text-xs text-[#A0AAC4] max-w-sm mb-4 leading-relaxed">{description}</p>
      {action}
    </div>
  );
}

// ─── Error State ───
function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[350px] p-8 text-center bg-[#101629] border border-[#FF6977]/30 rounded-xl" role="alert">
      <div className="w-10 h-10 rounded-full bg-[#FF6977]/15 border border-[#FF6977]/30 flex items-center justify-center mb-3">
        <svg className="w-5 h-5 text-[#FF6977]" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      </div>
      <h3 className="text-sm font-semibold text-[#F4F6FF] mb-1">{title}</h3>
      {message && <p className="text-xs text-[#A0AAC4] max-w-sm mb-4">{message}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs font-semibold text-[#8065FF] hover:text-[#6E50FF] cursor-pointer"
        >
          Try again
        </button>
      )}
    </div>
  );
}

// ─── Success Banner ───
function SuccessBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div className="bg-[#27D99A]/15 border border-[#27D99A]/30 rounded-lg p-3 flex items-center justify-between animate-slide-up" role="status">
      <div className="flex items-center gap-2 text-xs text-[#27D99A] font-medium">
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
        <span>{message}</span>
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="text-[#27D99A]/60 hover:text-[#27D99A] cursor-pointer ml-2" aria-label="Dismiss">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      )}
    </div>
  );
}

// ─── Metric Card (skeleton-aware) ───
function MetricCard({
  label,
  value,
  icon,
  trend,
  loading = false,
  variant = "default",
}: {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: string;
  loading?: boolean;
  variant?: "default" | "risk" | "warning" | "success" | "primary" | "cyan";
}) {
  const variantStyles = {
    default: "text-[#F4F6FF]",
    risk: "text-[#FF6977]",
    warning: "text-[#FFB547]",
    success: "text-[#27D99A]",
    primary: "text-[#8065FF]",
    cyan: "text-[#29D8C5]",
  };

  const iconBg = {
    default: "bg-[#1A2440] text-[#A0AAC4]",
    risk: "bg-[#FF6977]/15 text-[#FF6977] border border-[#FF6977]/30",
    warning: "bg-[#FFB547]/15 text-[#FFB547] border border-[#FFB547]/30",
    success: "bg-[#27D99A]/15 text-[#27D99A] border border-[#27D99A]/30",
    primary: "bg-[#8065FF]/15 text-[#8065FF] border border-[#8065FF]/30",
    cyan: "bg-[#29D8C5]/15 text-[#29D8C5] border border-[#29D8C5]/30",
  };

  return (
    <div className="bg-[#101629] border border-[#252F49] rounded-xl p-4 shadow-[0_2px_8px_rgba(0,0,0,0.35)]">
      <div className="flex items-center justify-between text-xs text-[#A0AAC4] mb-2 font-medium">
        <span>{label}</span>
        {icon && (
          <span className={cn("p-1.5 rounded-md", iconBg[variant])} aria-hidden="true">
            {icon}
          </span>
        )}
      </div>
      {loading ? (
        <Skeleton className="h-7 w-24 mb-1.5" />
      ) : (
        <div className={cn("font-mono text-xl font-bold tracking-tight", variantStyles[variant])}>
          {value}
        </div>
      )}
      {trend && !loading && (
        <p className="text-[11px] text-[#707D9E] mt-1">{trend}</p>
      )}
      {loading && <Skeleton className="h-3 w-32 mt-1.5" />}
    </div>
  );
}

// ─── Status Dot (accessible) ───
function StatusDot({
  status,
  label,
}: {
  status: "success" | "warning" | "risk" | "primary" | "muted" | "cyan";
  label: string;
}) {
  const colors = {
    success: "bg-[#27D99A]",
    warning: "bg-[#FFB547]",
    risk: "bg-[#FF6977]",
    primary: "bg-[#8065FF]",
    cyan: "bg-[#29D8C5]",
    muted: "bg-[#707D9E]",
  };

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", colors[status])} aria-hidden="true" />
      <span className="sr-only">{`Status: ${label}`}</span>
      <span className="text-[11px] text-[#A0AAC4]">{label}</span>
    </span>
  );
}

export {
  Skeleton,
  LoadingState,
  EmptyState,
  ErrorState,
  SuccessBanner,
  MetricCard,
  StatusDot,
};
