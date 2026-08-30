"use client";

import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
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

const STAGE_LABELS: Record<string, string> = {
  pending: "Queued for processing...",
  chunking: "Splitting document into chunks...",
  embedding: "Generating embeddings...",
  generating: "Generating notes and flashcards...",
};

/** Status banner for the document detail page: shows nothing once the job is
 * done, an active/spinning banner while in progress, or an error banner (with
 * the failed stage and error message) if the job failed. */
export function DocumentStatusBanner({
  status,
  currentStage,
  errorMessage,
}: {
  status: string | null;
  currentStage: string | null;
  errorMessage: string | null;
}) {
  const variant = documentStatusVariant(status);

  if (variant === "danger") {
    return (
      <div className="flex items-start gap-3 rounded-2xl border border-danger/30 bg-danger/10 px-5 py-4 text-sm text-danger-foreground">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2.25} />
        <div>
          <p className="font-medium">
            {currentStage ? `Failed during ${currentStage}` : "Processing failed"}
          </p>
          <p className="mt-1 opacity-90">{errorMessage ?? "No error details available."}</p>
        </div>
      </div>
    );
  }

  if (variant === "accent") {
    const label = (currentStage && STAGE_LABELS[currentStage]) || `${currentStage ?? status}...`;
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-accent/30 bg-accent/10 px-5 py-4 text-sm text-accent">
        <Loader2 className="h-4 w-4 shrink-0 animate-spin" strokeWidth={2.25} />
        <span>{label}</span>
      </div>
    );
  }

  return null;
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
