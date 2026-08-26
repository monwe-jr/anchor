"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { ApiError, Flashcard, Note, api } from "@/lib/api";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);

  const [notes, setNotes] = useState<Note[] | null>(null);
  const [flashcards, setFlashcards] = useState<Flashcard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<Set<number>>(new Set());

  useEffect(() => {
    Promise.all([
      api.getDocumentNotes(documentId),
      api.getDocumentFlashcards(documentId),
    ])
      .then(([n, f]) => {
        setNotes(n);
        setFlashcards(f);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Failed to load document.")
      );
  }, [documentId]);

  function toggleReveal(id: number) {
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (error) return <ErrorBanner message={error} />;
  if (notes === null || flashcards === null)
    return <Loading label="Loading document..." />;

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">Document #{documentId}</h1>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Notes</h2>
        {notes.length === 0 && (
          <p className="text-sm text-black/60 dark:text-white/60">No notes generated.</p>
        )}
        <ul className="flex flex-col gap-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="rounded border border-black/10 px-4 py-3 text-sm dark:border-white/15"
            >
              {note.content}
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Flashcards</h2>
        {flashcards.length === 0 && (
          <p className="text-sm text-black/60 dark:text-white/60">
            No flashcards generated.
          </p>
        )}
        <ul className="flex flex-col gap-2">
          {flashcards.map((card) => {
            const isRevealed = revealed.has(card.id);
            return (
              <li
                key={card.id}
                className="cursor-pointer rounded border border-black/10 px-4 py-3 text-sm dark:border-white/15"
                onClick={() => toggleReveal(card.id)}
              >
                <div className="font-medium">{card.question}</div>
                {isRevealed ? (
                  <div className="mt-2 text-black/70 dark:text-white/70">{card.answer}</div>
                ) : (
                  <div className="mt-2 text-xs text-black/40 dark:text-white/40">
                    Click to reveal answer
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
