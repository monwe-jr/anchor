"use client";

import { useEffect, useState } from "react";
import {
  Eye,
  Frown,
  Layers,
  PartyPopper,
  RotateCcw,
  Star,
  ThumbsUp,
} from "lucide-react";
import { EmptyState, ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { Button, Card, PageHeader, ProgressBar } from "@/app/components/ui";
import { ApiError, DueCard, Grade, api } from "@/lib/api";

const GRADES: { grade: Grade; label: string; icon: typeof RotateCcw; className: string }[] = [
  { grade: "again", label: "Again", icon: RotateCcw, className: "bg-red-600 hover:bg-red-500" },
  { grade: "hard", label: "Hard", icon: Frown, className: "bg-orange-500 hover:bg-orange-400" },
  { grade: "good", label: "Good", icon: ThumbsUp, className: "bg-green-600 hover:bg-green-500" },
  { grade: "easy", label: "Easy", icon: Star, className: "bg-blue-600 hover:bg-blue-500" },
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
      <div className="flex flex-col gap-6">
        <PageHeader icon={Layers} title="Review" />
        <EmptyState
          icon={PartyPopper}
          title={cards.length === 0 ? "No cards are due right now" : "You're all caught up!"}
          description={
            cards.length === 0
              ? "Come back later once more cards are due."
              : "No more cards due for now — nice work."
          }
        />
      </div>
    );
  }

  const card = cards[index];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={Layers}
        title="Review"
        action={
          <span className="text-sm text-muted">
            {index + 1} / {cards.length}
          </span>
        }
      />

      <ProgressBar percent={(index / cards.length) * 100} />

      {error && <ErrorBanner message={error} />}

      <Card className="flex min-h-56 flex-col justify-between gap-6 p-8">
        <div className="flex flex-col gap-4">
          <p className="text-lg text-foreground">{card.question}</p>
          {revealed && (
            <p className="border-t border-border pt-4 text-muted">{card.answer}</p>
          )}
        </div>

        {!revealed ? (
          <Button icon={Eye} onClick={() => setRevealed(true)}>
            Reveal answer
          </Button>
        ) : (
          <div className="flex gap-3">
            {GRADES.map((g) => (
              <button
                key={g.grade}
                type="button"
                disabled={grading}
                onClick={() => handleGrade(g.grade)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-white transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${g.className}`}
              >
                <g.icon className="h-4 w-4" strokeWidth={2.25} />
                {g.label}
              </button>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
