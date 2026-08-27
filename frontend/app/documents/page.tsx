"use client";

import { useEffect, useState } from "react";
import { FileText, FileX2 } from "lucide-react";
import { EmptyStateLink, ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { Badge, CardLink, PageHeader } from "@/app/components/ui";
import { ApiError, DocumentSummary, api } from "@/lib/api";

function statusVariant(status: string | null): "accent" | "success" | "danger" | "neutral" {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  if (["done", "complete", "completed", "ready"].includes(s)) return "success";
  if (["failed", "error"].includes(s)) return "danger";
  if (["queued", "processing", "pending", "running"].includes(s)) return "accent";
  return "neutral";
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listDocuments()
      .then(setDocuments)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Failed to load documents.")
      );
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={FileText}
        title="Documents"
        description="Everything you've ingested, with generated notes and flashcards."
      />

      {error && <ErrorBanner message={error} />}
      {!error && documents === null && <Loading label="Loading documents..." />}

      {documents !== null && documents.length === 0 && (
        <EmptyStateLink
          icon={FileX2}
          title="No documents yet"
          description="Upload one to get started."
          href="/upload"
          label="Upload a document"
        />
      )}

      {documents && documents.length > 0 && (
        <ul className="flex flex-col gap-3">
          {documents.map((doc) => (
            <li key={doc.id}>
              <CardLink href={`/documents/${doc.id}`} className="flex items-center gap-4 p-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
                  <FileText className="h-5 w-5" strokeWidth={2} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-foreground">
                    {doc.source_name}
                  </div>
                  <div className="mt-0.5 text-xs text-muted">
                    {doc.source_type} &middot; {new Date(doc.created_at).toLocaleString()}
                  </div>
                </div>
                <Badge variant={statusVariant(doc.job_status)}>
                  {doc.job_status ?? "unknown"}
                </Badge>
              </CardLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
