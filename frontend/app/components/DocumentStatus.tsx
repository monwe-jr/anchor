"use client";

import { useState } from "react";
import { Badge } from "@/app/components/ui";

export type StatusVariant = "accent" | "success" | "danger" | "neutral";

const DONE_STATUSES = new Set(["done", "complete", "completed", "ready"]);
const FAILED_STATUSES = new Set(["failed", "error"]);

export function documentStatusVariant(status: string | null): StatusVariant {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  if (DONE_STATUSES.has(s)) return "success";
  if (FAILED_STATUSES.has(s)) return "danger";
  // Every other status ("pending", "chunking", "embedding", "generating", ...)
  // is some form of in-progress work, so it counts as "processing".
  return "accent";
}

export function DocumentStatusBadge({
  status,
  currentStage,
  errorMessage,
}: {
  status: string | null;
  currentStage: string | null;
  errorMessage: string | null;
}) {
  const [open, setOpen] = useState(false);
  const variant = documentStatusVariant(status);

  if (variant === "danger") {
    return (
      <div className="relative shrink-0">
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setOpen((o) => !o);
          }}
          className="inline-flex items-center rounded-full bg-danger/15 px-3 py-1 text-xs font-medium capitalize text-danger-foreground transition-colors duration-150 hover:bg-danger/25"
        >
          Failed
        </button>
        {open && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setOpen(false);
              }}
            />
            <div className="absolute right-0 top-full z-20 mt-2 w-72 rounded-xl border border-border bg-surface p-4 text-left normal-case shadow-soft-hover">
              {currentStage && (
                <p className="mb-2 text-xs text-muted">
                  Failed during{" "}
                  <span className="font-medium text-foreground">{currentStage}</span>
                </p>
              )}
              <p className="text-xs text-danger-foreground">
                {errorMessage ?? "No error details available."}
              </p>
            </div>
          </>
        )}
      </div>
    );
  }

  if (variant === "accent") {
    return <Badge variant="accent">{currentStage ?? status ?? "processing"}</Badge>;
  }

  return <Badge variant={variant}>{status ?? "unknown"}</Badge>;
}
