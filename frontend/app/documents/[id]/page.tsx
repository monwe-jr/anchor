"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { FileText, HelpCircle, Layers, ListChecks, StickyNote } from "lucide-react";
import QuizPanel from "@/app/documents/[id]/QuizPanel";
import { EmptyState, ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { Card, PageHeader, Stat } from "@/app/components/ui";
import { ApiError, Flashcard, Note, api } from "@/lib/api";

type Tab = "notes" | "flashcards" | "quiz";

const TABS: { tab: Tab; label: string; icon: typeof StickyNote }[] = [
  { tab: "notes", label: "Notes", icon: StickyNote },
  { tab: "flashcards", label: "Flashcards", icon: Layers },
  { tab: "quiz", label: "Quiz", icon: ListChecks },
];

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);

  const [tab, setTab] = useState<Tab>("notes");
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
      <PageHeader icon={FileText} title={`Document #${documentId}`} />

      <Card className="grid grid-cols-2 gap-6 p-8">
        <Stat value={notes.length} label="Notes" />
        <Stat value={flashcards.length} label="Flashcards" />
      </Card>

      <div className="flex gap-6 border-b border-border">
        {TABS.map(({ tab: t, label, icon: Icon }) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex items-center gap-2 border-b-2 px-1 pb-3 text-sm font-medium transition-colors duration-150 ${
              tab === t
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4" strokeWidth={2.25} />
            {label}
          </button>
        ))}
      </div>

      {tab === "notes" && (
        <section className="flex flex-col gap-3">
          {notes.length === 0 ? (
            <EmptyState icon={StickyNote} title="No notes generated" />
          ) : (
            <ul className="flex flex-col gap-4">
              {notes.map((note) => (
                <li key={note.id}>
                  <Card className="p-6 text-sm text-foreground">{note.content}</Card>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === "flashcards" && (
        <section className="flex flex-col gap-3">
          {flashcards.length === 0 ? (
            <EmptyState icon={Layers} title="No flashcards generated" />
          ) : (
            <ul className="flex flex-col gap-4">
              {flashcards.map((card) => {
                const isRevealed = revealed.has(card.id);
                return (
                  <li key={card.id}>
                    <Card
                      interactive
                      className="cursor-pointer p-6 text-sm"
                      onClick={() => toggleReveal(card.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          toggleReveal(card.id);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="flex items-start gap-3">
                        <HelpCircle
                          className="mt-0.5 h-4 w-4 shrink-0 text-faint"
                          strokeWidth={2}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="font-medium text-foreground">{card.question}</div>
                          {isRevealed ? (
                            <div className="mt-3 border-t border-border pt-3 text-muted">
                              {card.answer}
                            </div>
                          ) : (
                            <div className="mt-2 text-xs text-faint">Click to reveal answer</div>
                          )}
                        </div>
                      </div>
                    </Card>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      {tab === "quiz" && <QuizPanel documentId={documentId} />}
    </div>
  );
}
