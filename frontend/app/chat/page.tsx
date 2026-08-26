"use client";

import { useEffect, useState } from "react";
import { ErrorBanner } from "@/app/components/StatusMessage";
import { ApiError, ChatResponse, DocumentSummary, api } from "@/lib/api";

export default function ChatPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentId, setDocumentId] = useState<string>("");
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(() => setDocuments([]));
  }, []);

  function toggleExpanded(index: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || submitting) return;

    setSubmitting(true);
    setError(null);
    setExpanded(new Set());
    try {
      const response = await api.chat(
        question,
        documentId ? Number(documentId) : null
      );
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chat request failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Chat</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <select
          value={documentId}
          onChange={(e) => setDocumentId(e.target.value)}
          className="w-fit rounded border border-black/15 bg-transparent px-3 py-2 text-sm dark:border-white/20"
        >
          <option value="">All documents</option>
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.source_name}
            </option>
          ))}
        </select>

        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your documents..."
          rows={3}
          className="w-full resize-y rounded border border-black/15 bg-transparent p-3 text-sm dark:border-white/20"
        />

        <button
          type="submit"
          disabled={!question.trim() || submitting}
          className="w-fit rounded bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-black"
        >
          {submitting ? "Asking..." : "Ask"}
        </button>
      </form>

      {error && <ErrorBanner message={error} />}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="rounded border border-black/10 p-4 text-sm dark:border-white/15">
            {result.answer}
          </div>

          {result.citations.length > 0 && (
            <div className="flex flex-col gap-2">
              <h2 className="text-sm font-medium text-black/60 dark:text-white/60">
                Sources
              </h2>
              <ul className="flex flex-col gap-2">
                {result.citations.map((citation, i) => {
                  const isOpen = expanded.has(i);
                  return (
                    <li
                      key={`${citation.chunk_id}-${i}`}
                      className="rounded border border-black/10 text-sm dark:border-white/15"
                    >
                      <button
                        type="button"
                        onClick={() => toggleExpanded(i)}
                        className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-black/5 dark:hover:bg-white/10"
                      >
                        <span>
                          Doc {citation.document_id} &middot; chunk{" "}
                          {citation.chunk_index}: &ldquo;{citation.quote}&rdquo;
                        </span>
                        <span className="text-black/40 dark:text-white/40">
                          {isOpen ? "−" : "+"}
                        </span>
                      </button>
                      {isOpen && (
                        <div className="border-t border-black/10 px-3 py-2 text-black/70 dark:border-white/15 dark:text-white/70">
                          {citation.chunk_text}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
