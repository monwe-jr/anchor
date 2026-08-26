"use client";

import { useEffect, useState } from "react";
import { ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { ApiError, DueCard, Grade, api } from "@/lib/api";

const GRADES: { grade: Grade; label: string; className: string }[] = [
  { grade: "again", label: "Again", className: "bg-red-600 hover:bg-red-700" },
  { grade: "hard", label: "Hard", className: "bg-orange-500 hover:bg-orange-600" },
  { grade: "good", label: "Good", className: "bg-green-600 hover:bg-green-700" },
  { grade: "easy", label: "Easy", className: "bg-blue-600 hover:bg-blue-700" },
];

export default function ReviewPage() {
  const [cards, setCards] = useState<DueCard[] | null>(null);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [grading, setGrading] = useState(false);

  useEffect(() => {
    api
      .getDueCards()
      .then(setCards)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Failed to load due cards.")
      );
  }, []);

  async function handleGrade(grade: Grade) {
    if (!cards || grading) return;
    const card = cards[index];
    setGrading(true);
    setError(null);
    try {
      await api.submitReview(card.id, grade);
      setRevealed(false);
      setIndex((i) => i + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit review.");
    } finally {
      setGrading(false);
    }
  }

  if (error && !cards) return <ErrorBanner message={error} />;
  if (cards === null) return <Loading label="Loading due cards..." />;

  if (index >= cards.length) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Review</h1>
        <p className="text-sm text-black/60 dark:text-white/60">
          {cards.length === 0
            ? "No cards are due right now."
            : "You're done for now — no more cards due."}
        </p>
      </div>
    );
  }

  const card = cards[index];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">Review</h1>
        <span className="text-sm text-black/50 dark:text-white/50">
          {index + 1} / {cards.length}
        </span>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="flex min-h-48 flex-col justify-between gap-6 rounded border border-black/10 p-6 dark:border-white/15">
        <div className="flex flex-col gap-4">
          <p className="text-lg">{card.question}</p>
          {revealed && (
            <p className="border-t border-black/10 pt-4 text-black/70 dark:border-white/15 dark:text-white/70">
              {card.answer}
            </p>
          )}
        </div>

        {!revealed ? (
          <button
            type="button"
            onClick={() => setRevealed(true)}
            className="w-fit rounded bg-black px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-black"
          >
            Reveal answer
          </button>
        ) : (
          <div className="flex gap-2">
            {GRADES.map((g) => (
              <button
                key={g.grade}
                type="button"
                disabled={grading}
                onClick={() => handleGrade(g.grade)}
                className={`flex-1 rounded px-3 py-2 text-sm font-medium text-white disabled:opacity-40 ${g.className}`}
              >
                {g.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
