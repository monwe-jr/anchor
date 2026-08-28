"use client";

import { useEffect, useState } from "react";
import { Bot, ChevronDown, ChevronUp, Loader2, MessageCircle, Quote, Send } from "lucide-react";
import { EmptyState, ErrorBanner } from "@/app/components/StatusMessage";
import { Button, Card, PageHeader } from "@/app/components/ui";
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
      <PageHeader
        icon={MessageCircle}
        title="Chat"
        description="Ask grounded questions about your documents."
      />

      <Card className="p-8">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            className="w-fit rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
          >
            <option value="">All documents</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.display_name}
              </option>
            ))}
          </select>

          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your documents..."
            rows={3}
            className="w-full resize-y rounded-xl border border-border bg-background p-3 text-sm text-foreground placeholder:text-faint focus:border-accent focus:outline-none"
          />

          <Button type="submit" disabled={!question.trim() || submitting}>
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.25} />
            ) : (
              <Send className="h-4 w-4" strokeWidth={2.25} />
            )}
            {submitting ? "Thinking..." : "Ask"}
          </Button>
        </form>
      </Card>

      {error && <ErrorBanner message={error} />}

      {!result && !error && (
        <EmptyState
          icon={MessageCircle}
          title="Ask a question to get started"
          description="Answers are grounded in your ingested documents, with citations."
        />
      )}

      {result && (
        <div className="flex flex-col gap-5">
          <Card className="flex items-start gap-4 p-6">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
              <Bot className="h-4 w-4" strokeWidth={2.25} />
            </span>
            <p className="pt-1 text-sm text-foreground">{result.answer}</p>
          </Card>

          {result.citations.length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Quote className="h-4 w-4 text-accent" strokeWidth={2.25} />
                Sources
              </h2>
              <ul className="flex flex-col gap-3">
                {result.citations.map((citation, i) => {
                  const isOpen = expanded.has(i);
                  return (
                    <li key={`${citation.chunk_id}-${i}`}>
                      <Card>
                        <button
                          type="button"
                          onClick={() => toggleExpanded(i)}
                          className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left text-sm transition-colors duration-150 hover:bg-surface-hover"
                        >
                          <span className="min-w-0 truncate text-foreground">
                            Doc {citation.document_id} &middot; chunk{" "}
                            {citation.chunk_index}: &ldquo;{citation.quote}&rdquo;
                          </span>
                          {isOpen ? (
                            <ChevronUp className="h-4 w-4 shrink-0 text-faint" strokeWidth={2} />
                          ) : (
                            <ChevronDown
                              className="h-4 w-4 shrink-0 text-faint"
                              strokeWidth={2}
                            />
                          )}
                        </button>
                        {isOpen && (
                          <div className="border-t border-border px-5 py-4 text-sm text-muted">
                            {citation.chunk_text}
                          </div>
                        )}
                      </Card>
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
