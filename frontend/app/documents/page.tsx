"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FileText, FileX2, Trash2 } from "lucide-react";
import { DocumentStatusBadge, documentStatusVariant } from "@/app/components/DocumentStatus";
import { EditableTitle } from "@/app/components/EditableTitle";
import { EmptyStateLink, ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { Button, Card, PageHeader, Stat } from "@/app/components/ui";
import { ApiError, DocumentSummary, api } from "@/lib/api";

function DocumentRow({
  doc,
  onRenamed,
  onDeleted,
}: {
  doc: DocumentSummary;
  onRenamed: (updated: DocumentSummary) => void;
  onDeleted: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleRename(newName: string) {
    const updated = await api.renameDocument(doc.id, newName);
    onRenamed(updated);
  }

  async function handleDelete() {
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteDocument(doc.id);
      onDeleted();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Failed to delete document.");
      setDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <Card className="flex items-center gap-4 p-5">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
        <FileText className="h-5 w-5" strokeWidth={2} />
      </span>

      <div className="min-w-0 flex-1">
        <EditableTitle
          value={doc.display_name}
          onSave={handleRename}
          href={`/documents/${doc.id}`}
          textClassName="text-sm font-medium text-foreground"
          inputClassName="text-sm"
        />
        <Link href={`/documents/${doc.id}`} className="mt-1 block text-xs text-muted">
          {doc.source_type} &middot; {new Date(doc.created_at).toLocaleString()}
        </Link>
      </div>

      <DocumentStatusBadge
        status={doc.job_status}
        currentStage={doc.current_stage}
        errorMessage={doc.error_message}
      />

      {confirming ? (
        <div className="flex shrink-0 items-center gap-2">
          {deleteError && <span className="text-xs text-danger-foreground">{deleteError}</span>}
          <Button
            variant="ghost"
            onClick={() => setConfirming(false)}
            disabled={deleting}
            className="px-2.5 py-1.5 text-xs"
          >
            Cancel
          </Button>
          <Button
            variant="secondary"
            onClick={handleDelete}
            disabled={deleting}
            className="border-danger/40 px-2.5 py-1.5 text-xs text-danger-foreground hover:bg-danger/10"
          >
            {deleting ? "Deleting..." : "Confirm delete"}
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          aria-label="Delete document"
          className="shrink-0 rounded-xl p-2 text-faint transition-colors duration-150 hover:bg-danger/10 hover:text-danger-foreground"
        >
          <Trash2 className="h-4 w-4" strokeWidth={2} />
        </button>
      )}
    </Card>
  );
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

  function handleRenamed(updated: DocumentSummary) {
    setDocuments((prev) => prev?.map((d) => (d.id === updated.id ? updated : d)) ?? prev);
  }

  function handleDeleted() {
    api
      .listDocuments()
      .then(setDocuments)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Failed to refresh documents.")
      );
  }

  const readyCount =
    documents?.filter((d) => documentStatusVariant(d.job_status) === "success").length ?? 0;
  const failedCount =
    documents?.filter((d) => documentStatusVariant(d.job_status) === "danger").length ?? 0;
  const processingCount = documents ? documents.length - readyCount - failedCount : 0;

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
          <Card className="grid grid-cols-4 gap-6 p-8">
            <Stat value={documents.length} label="Total documents" />
            <Stat value={readyCount} label="Ready" />
            <Stat value={processingCount} label="Processing" />
            <Stat value={failedCount} label="Failed" />
          </Card>

          <ul className="flex flex-col gap-4">
            {documents.map((doc) => (
              <li key={doc.id}>
                <DocumentRow doc={doc} onRenamed={handleRenamed} onDeleted={handleDeleted} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
