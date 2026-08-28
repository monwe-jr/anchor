"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { FileUp, Loader2, Type, UploadCloud } from "lucide-react";
import { ErrorBanner } from "@/app/components/StatusMessage";
import { Button, Card, PageHeader } from "@/app/components/ui";
import { ApiError, api } from "@/lib/api";

type Mode = "text" | "file";

export default function UploadPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = mode === "text" ? text.trim().length > 0 : file !== null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      const result =
        mode === "text" ? await api.ingestText(text) : await api.ingestFile(file!);
      router.push(`/documents/${result.document_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ingestion failed.");
      setSubmitting(false);
    }
  }

  const modeTabs: { mode: Mode; label: string; icon: typeof Type }[] = [
    { mode: "text", label: "Paste text", icon: Type },
    { mode: "file", label: "Upload file", icon: FileUp },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={UploadCloud}
        title="Upload"
        description="Paste text or upload a PDF/DOCX file to generate notes and flashcards."
      />

      <Card className="p-8">
        <div className="flex gap-2">
          {modeTabs.map(({ mode: m, label, icon: Icon }) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
                mode === m
                  ? "bg-accent text-accent-foreground"
                  : "border border-border text-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" strokeWidth={2.25} />
              {label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-5">
          {mode === "text" ? (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste source text here..."
              rows={12}
              className="w-full resize-y rounded-xl border border-border bg-background p-3 text-sm text-foreground placeholder:text-faint focus:border-accent focus:outline-none"
            />
          ) : (
            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-border bg-background px-4 py-14 text-center transition-colors duration-150 hover:border-border-strong">
              <FileUp className="h-6 w-6 text-faint" strokeWidth={1.75} />
              <span className="text-sm text-foreground">
                {file ? file.name : "Choose a PDF or DOCX file"}
              </span>
              <span className="text-xs text-muted">Click to browse</span>
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="hidden"
              />
            </label>
          )}

          {error && <ErrorBanner message={error} />}

          <Button type="submit" disabled={!canSubmit || submitting}>
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.25} />
            ) : (
              <UploadCloud className="h-4 w-4" strokeWidth={2.25} />
            )}
            {submitting ? "Processing your document..." : "Ingest"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
