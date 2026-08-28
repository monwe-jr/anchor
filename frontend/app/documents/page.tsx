"use client";

import { useEffect, useState } from "react";
import { FileText, FileX2 } from "lucide-react";
import { EmptyStateLink, ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { Badge, Card, CardLink, PageHeader, Stat } from "@/app/components/ui";
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

  const readyCount =
    documents?.filter((d) => statusVariant(d.job_status) === "success").length ?? 0;
  const processingCount =
    documents?.filter((d) => statusVariant(d.job_status) === "accent").length ?? 0;

  return (
    <div className="flex flex-col gap-8">
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
        <>
          <Card className="grid grid-cols-3 gap-6 p-8">
            <Stat value={documents.length} label="Total documents" />
            <Stat value={readyCount} label="Ready" />
            <Stat value={processingCount} label="Processing" />
          </Card>

          <ul className="flex flex-col gap-4">
            {documents.map((doc) => (
              <li key={doc.id}>
                <CardLink href={`/documents/${doc.id}`} className="flex items-center gap-4 p-5">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
                    <FileText className="h-5 w-5" strokeWidth={2} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-foreground">
                      {doc.source_name}
                    </div>
                    <div className="mt-1 text-xs text-muted">
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
        </>
      )}
    </div>
  );
}
