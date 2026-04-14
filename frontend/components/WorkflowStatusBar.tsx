"use client";

import React from "react";
import { Check, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { STATE_LABELS } from "@/lib/types";

interface WorkflowStatusBarProps {
  currentState: string;
}

const STEPS = [
  "NEW_STORE",
  "DIAGNOSIS",
  "FOUNDATION",
  "DAILY_OPS",
  "WEEKLY_REPORT",
  "DONE",
];

export function WorkflowStatusBar({ currentState }: WorkflowStatusBarProps) {
  // If we are in MANUAL_REVIEW, we might want to still show progress.
  // However, without more state, we don't know where it was paused.
  // For now, we follow the instruction: show steps based on status, 
  // and show MANUAL_REVIEW as an alert bar below.
  const effectiveIndex = STEPS.indexOf(currentState);
  const isManualReview = currentState === "MANUAL_REVIEW";

  return (
    <nav className="w-full space-y-6 mb-8" aria-label="Workflow Progress">
      {/* Horizontal Step Indicator */}
      <ol className="relative flex justify-between items-start px-2 sm:px-4">
        {/* Connection Line - Positioned to hit circle centers precisely */}
        <div 
          className="absolute top-4 left-[8.33%] right-[8.33%] h-[2px] bg-border-warm -z-0" 
          aria-hidden="true"
        />

        {STEPS.map((step, index) => {
          const isCompleted = effectiveIndex > index;
          const isCurrent = effectiveIndex === index;
          const isPending = !isCompleted && !isCurrent;

          return (
            <li 
              key={step} 
              className="relative z-10 flex flex-col items-center flex-1"
              aria-current={isCurrent ? "step" : undefined}
            >
              {/* Step Circle/Icon */}
              <div 
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-500 bg-parchment",
                  isCompleted && "bg-olive-gray border-olive-gray text-ivory",
                  isCurrent && "bg-terracotta border-terracotta text-ivory shadow-[0_0_10px_rgba(201,100,66,0.3)]",
                  isPending && "border-stone-gray text-stone-gray"
                )}
              >
                {isCompleted ? (
                  <Check className="h-5 w-5" aria-hidden="true" />
                ) : isCurrent ? (
                  <span className="text-xs font-mono font-bold">{index + 1}</span>
                ) : null}
              </div>

              {/* Step Label */}
              <div className="mt-2 px-1 text-center max-w-[80px] sm:max-w-none">
                <span 
                  className={cn(
                    "block text-[9px] sm:text-[10px] md:text-xs font-medium uppercase tracking-wider transition-colors duration-300",
                    isCompleted && "text-olive-gray",
                    isCurrent && "text-terracotta font-bold",
                    isPending && "text-stone-gray"
                  )}
                >
                  {STATE_LABELS[step] || step}
                </span>
              </div>
            </li>
          );
        })}
      </ol>

      {/* Manual Review Alert Bar */}
      {isManualReview && (
        <div 
          role="alert"
          className="mx-2 sm:mx-4 bg-error-crimson text-ivory p-3 rounded-comfortably-rounded flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-500 shadow-whisper border border-white/10"
        >
          <AlertCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <p className="text-sm font-medium">Attention: Manual Review Required</p>
            <p className="text-xs opacity-90">The automated workflow has been paused for manual intervention.</p>
          </div>
        </div>
      )}
    </nav>
  );
}
