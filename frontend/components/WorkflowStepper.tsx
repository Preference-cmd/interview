"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  { key: "NEW_STORE", label: "New Store", subtitle: "新建门店" },
  { key: "DIAGNOSIS", label: "Diagnosis", subtitle: "健康诊断" },
  { key: "FOUNDATION", label: "Foundation", subtitle: "基础建设" },
  { key: "DAILY_OPS", label: "Daily Ops", subtitle: "日常运营" },
  { key: "WEEKLY_REPORT", label: "Weekly Report", subtitle: "周报生成" },
  { key: "DONE", label: "Done", subtitle: "已完成" },
] as const;

const STEP_ORDER = STEPS.map((s) => s.key);

type WorkflowStep = (typeof STEPS)[number]["key"];

interface WorkflowStepperProps {
  currentState: string;
}

function getStepStatus(
  stepKey: WorkflowStep,
  currentState: string
): "completed" | "active" | "pending" | "review" {
  if (currentState === "MANUAL_REVIEW") {
    return "pending";
  }

  const currentIdx = STEP_ORDER.indexOf(currentState as WorkflowStep);
  const stepIdx = STEP_ORDER.indexOf(stepKey);

  if (currentIdx === -1) {
    // Unknown state, all pending
    return "pending";
  }

  if (stepIdx < currentIdx) {
    return "completed";
  }
  if (stepIdx === currentIdx) {
    return "active";
  }
  return "pending";
}

export function WorkflowStepper({ currentState }: WorkflowStepperProps) {
  const isManualReview = currentState === "MANUAL_REVIEW";

  return (
    <div className="flex flex-col gap-0">
      {STEPS.map((step, idx) => {
        const status = getStepStatus(step.key, currentState);

        return (
          <div key={step.key} className="flex items-start gap-3">
            {/* Connector line above (except first) */}
            {idx > 0 && (
              <div
                className={cn(
                  "w-0.5 h-5 ml-[15px] shrink-0",
                  getStepStatus(step.key, currentState) === "completed" ||
                    (idx <= STEP_ORDER.indexOf(currentState as WorkflowStep) &&
                      getStepStatus(step.key, currentState) !== "pending")
                    ? "bg-green-500"
                    : "bg-border-warm"
                )}
              />
            )}

            {/* Step row */}
            <div className="flex items-center gap-3 py-1">
              {/* Circle node */}
              <div
                className={cn(
                  "size-7 rounded-full flex items-center justify-center shrink-0",
                  status === "completed" && "bg-green-500 text-white",
                  status === "active" &&
                    "bg-terracotta text-white shadow-[0_0_10px_rgba(201,100,66,0.3)]",
                  status === "pending" &&
                    "border-2 border-border-warm bg-transparent text-stone-gray"
                )}
              >
                {status === "completed" ? (
                  <Check className="size-4" />
                ) : status === "active" ? (
                  <span className="text-[11px] font-bold">{idx + 1}</span>
                ) : (
                  <span className="text-[11px] font-medium opacity-50">
                    {idx + 1}
                  </span>
                )}
              </div>

              {/* Labels */}
              <div className="flex flex-col gap-0">
                <span
                  className={cn(
                    "text-[13px] font-medium leading-tight",
                    status === "completed" && "text-olive-gray line-through",
                    status === "active" && "text-anthropic-near-black font-semibold",
                    status === "pending" && "text-stone-gray"
                  )}
                >
                  {step.label}
                </span>
                <span
                  className={cn(
                    "text-[11px] leading-tight",
                    status === "completed" && "text-stone-gray",
                    status === "active" && "text-olive-gray",
                    status === "pending" && "text-stone-gray opacity-60"
                  )}
                >
                  {step.subtitle}
                </span>
              </div>
            </div>
          </div>
        );
      })}

      {/* MANUAL_REVIEW row */}
      <div className="flex items-start gap-3 mt-2">
        {/* Connector line */}
        <div className="w-0.5 h-5 ml-[15px] shrink-0 bg-border-warm" />
        <div className="flex items-center gap-3 py-1">
          <div
            className={cn(
              "size-7 rounded-full flex items-center justify-center shrink-0 border-2",
              isManualReview
                ? "border-error-crimson bg-error-crimson/10 text-error-crimson"
                : "border-border-warm bg-transparent text-stone-gray opacity-50"
            )}
          >
            <span className="text-[13px] font-bold">!</span>
          </div>
          <div className="flex flex-col gap-0">
            <span
              className={cn(
                "text-[13px] font-medium leading-tight",
                isManualReview
                  ? "text-error-crimson font-semibold"
                  : "text-stone-gray opacity-50"
              )}
            >
              Manual Review
            </span>
            <span
              className={cn(
                "text-[11px] leading-tight",
                isManualReview ? "text-error-crimson/70" : "text-stone-gray opacity-60"
              )}
            >
              人工介入
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
