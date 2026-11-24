import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-xs font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8065FF] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B14] disabled:pointer-events-none disabled:opacity-50 cursor-pointer [&_svg]:pointer-events-none [&_svg]:size-3.5 [&_svg]:shrink-0 select-none",
  {
    variants: {
      variant: {
        default: "bg-[#8065FF] text-white hover:bg-[#6E50FF] shadow-sm font-semibold",
        primary: "bg-[#8065FF] text-white hover:bg-[#6E50FF] shadow-sm font-semibold",
        secondary: "bg-[#1A2440] border border-[#252F49] text-[#F4F6FF] hover:bg-[#252F49]",
        outline: "border border-[#252F49] bg-[#101629] text-[#F4F6FF] hover:bg-[#151D32] hover:border-[#3A4769]",
        ghost: "text-[#A0AAC4] hover:text-[#F4F6FF] hover:bg-[#151D32]",
        link: "text-[#8065FF] underline-offset-4 hover:underline",
        destructive: "bg-[#FF6977]/15 border border-[#FF6977]/30 text-[#FF6977] hover:bg-[#FF6977]/25",
        success: "bg-[#27D99A]/15 border border-[#27D99A]/30 text-[#27D99A] hover:bg-[#27D99A]/25 font-semibold",
        cyan: "bg-[#29D8C5]/15 border border-[#29D8C5]/30 text-[#29D8C5] hover:bg-[#29D8C5]/25 font-semibold",
      },
      size: {
        default: "h-8 px-3.5 rounded-lg",
        sm: "h-7 px-2.5 text-[11px] rounded-md",
        lg: "h-10 px-5 text-sm rounded-lg",
        icon: "h-8 w-8 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
