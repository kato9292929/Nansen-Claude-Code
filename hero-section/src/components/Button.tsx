"use client";

import { cva, type VariantProps } from "class-variance-authority";
import React from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 transition-colors duration-200 cursor-pointer",
  {
    variants: {
      variant: {
        hero: [
          "bg-[hsl(121_95%_76%)]",
          "text-[hsl(0_0%_5%)]",
          "rounded-full",
          "px-6",
          "py-3",
          "text-base",
          "font-medium",
          "hover:bg-[hsl(121_95%_68%)]",
        ],
        heroSecondary: [
          "liquid-glass",
          "text-[hsl(40_6%_95%)]",
          "rounded-full",
          "px-6",
          "py-3",
          "text-base",
          "font-normal",
          "hover:bg-white/5",
        ],
        navCta: [
          "bg-[hsl(121_95%_76%)]",
          "text-[hsl(0_0%_5%)]",
          "rounded-xl",
          "px-4",
          "py-1.5",
          "text-sm",
          "font-medium",
          "hover:bg-[hsl(121_95%_68%)]",
        ],
      },
    },
    defaultVariants: {
      variant: "hero",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  children: React.ReactNode;
}

export function Button({ variant, className = "", children, ...props }: ButtonProps) {
  return (
    <button className={buttonVariants({ variant, className })} {...props}>
      {children}
    </button>
  );
}
