"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import { ApiError } from "@/lib/api";

export function EditableTitle({
  value,
  onSave,
  href,
  textClassName = "",
  inputClassName = "",
}: {
  value: string;
  onSave: (newValue: string) => Promise<void>;
  href?: string;
  textClassName?: string;
  inputClassName?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  function startEditing() {
    setDraft(value);
    setError(null);
    setEditing(true);
  }

  async function commit() {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === value) {
      setEditing(false);
      setDraft(value);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(trimmed);
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to rename.");
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <input
          ref={inputRef}
          value={draft}
          disabled={saving}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
            if (e.key === "Escape") {
              e.preventDefault();
              setDraft(value);
              setEditing(false);
              setError(null);
            }
          }}
          className={`min-w-0 flex-1 rounded-lg border border-accent bg-background px-2 py-1 text-foreground focus:outline-none disabled:opacity-60 ${inputClassName}`}
        />
        {error && <span className="shrink-0 text-xs text-danger-foreground">{error}</span>}
      </div>
    );
  }

  return (
    <span className="group flex min-w-0 items-center gap-1.5">
      {href ? (
        <Link href={href} className={`truncate hover:underline ${textClassName}`}>
          {value}
        </Link>
      ) : (
        <span className={`truncate ${textClassName}`}>{value}</span>
      )}
      <button
        type="button"
        onClick={startEditing}
        aria-label="Rename document"
        className="shrink-0 rounded p-0.5 text-faint opacity-0 transition-opacity duration-150 hover:text-foreground group-hover:opacity-100"
      >
        <Pencil className="h-3.5 w-3.5" strokeWidth={2} />
      </button>
    </span>
  );
}
