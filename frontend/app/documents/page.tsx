"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { ApiError, DocumentSummary, api } from "@/lib/api";

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
      <h1 className="text-xl font-semibold">Documents</h1>

      {error && <ErrorBanner message={error} />}
      {!error && documents === null && <Loading label="Loading documents..." />}
      {documents !== null && documents.length === 0 && (
        <p className="text-sm text-black/60 dark:text-white/60">
          No documents yet. Go to Upload to ingest your first one.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {documents?.map((doc) => (
          <li key={doc.id}>
            <Link
              href={`/documents/${doc.id}`}
              className="flex items-center justify-between rounded border border-black/10 px-4 py-3 text-sm hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/10"
            >
              <div>
                <div className="font-medium">{doc.source_name}</div>
                <div className="text-black/50 dark:text-white/50">
                  {doc.source_type} &middot; {new Date(doc.created_at).toLocaleString()}
                </div>
              </div>
              <span className="rounded bg-black/10 px-2 py-1 text-xs dark:bg-white/15">
                {doc.job_status ?? "unknown"}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
