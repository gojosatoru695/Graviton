import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider transition-colors select-none",
  {
    variants: {
      variant: {
        default: "bg-[#151D32] text-[#A0AAC4] border border-[#252F49]",
        primary: "bg-[#8065FF]/15 text-[#8065FF] border border-[#8065FF]/30",
        secondary: "bg-[#5B7CFA]/15 text-[#5B7CFA] border border-[#5B7CFA]/30",
        cyan: "bg-[#29D8C5]/15 text-[#29D8C5] border border-[#29D8C5]/30",
        success: "bg-[#27D99A]/15 text-[#27D99A] border border-[#27D99A]/30",
        warning: "bg-[#FFB547]/15 text-[#FFB547] border border-[#FFB547]/30",
        risk: "bg-[#FF6977]/15 text-[#FF6977] border border-[#FF6977]/30",
        solid: "bg-[#8065FF] text-white",
        outline: "border border-[#252F49] text-[#A0AAC4] bg-transparent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
