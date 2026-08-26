"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Upload</h1>
        <p className="text-sm text-black/60 dark:text-white/60">
          Paste text or upload a PDF/DOCX file to generate notes and flashcards.
        </p>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode("text")}
          className={`rounded px-3 py-1.5 text-sm ${
            mode === "text"
              ? "bg-black text-white dark:bg-white dark:text-black"
              : "border border-black/15 dark:border-white/20"
          }`}
        >
          Paste text
        </button>
        <button
          type="button"
          onClick={() => setMode("file")}
          className={`rounded px-3 py-1.5 text-sm ${
            mode === "file"
              ? "bg-black text-white dark:bg-white dark:text-black"
              : "border border-black/15 dark:border-white/20"
          }`}
        >
          Upload file
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {mode === "text" ? (
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste source text here..."
            rows={12}
            className="w-full resize-y rounded border border-black/15 bg-transparent p-3 text-sm dark:border-white/20"
          />
        ) : (
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm"
          />
        )}

        {error && (
          <div className="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit || submitting}
          className="w-fit rounded bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-black"
        >
          {submitting ? "Ingesting..." : "Ingest"}
        </button>
      </form>
    </div>
  );
}
