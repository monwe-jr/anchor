"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  ChevronRight,
  ListChecks,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
  Trophy,
  XCircle,
} from "lucide-react";
import { EmptyState, ErrorBanner, Loading } from "@/app/components/StatusMessage";
import { Badge, Button, Card } from "@/app/components/ui";
import {
  ApiError,
  Difficulty,
  QuizAttemptResult,
  QuizQuestion,
  TopicMastery,
  api,
} from "@/lib/api";

type Stage = "loading" | "setup" | "taking" | "results";

const DIFFICULTIES: { value: Difficulty; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const COUNTS = [5, 10, 15, 20];

const OPTION_LETTERS = ["A", "B", "C", "D"];

function masteryColor(percent: number) {
  if (percent >= 80) return { text: "text-green-500", bar: "bg-green-500" };
  if (percent >= 50) return { text: "text-amber-500", bar: "bg-amber-500" };
  return { text: "text-red-500", bar: "bg-red-500" };
}

export default function QuizPanel({ documentId }: { documentId: number }) {
  const [stage, setStage] = useState<Stage>("loading");
  const [error, setError] = useState<string | null>(null);

  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [difficulty, setDifficulty] = useState<Difficulty>("intermediate");
  const [count, setCount] = useState(10);
  const [generating, setGenerating] = useState(false);

  const [index, setIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [attemptResult, setAttemptResult] = useState<QuizAttemptResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [correctCount, setCorrectCount] = useState(0);

  const [mastery, setMastery] = useState<TopicMastery[] | null>(null);
  const [masteryError, setMasteryError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getQuiz(documentId)
      .then((qs) => {
        setQuestions(qs);
        setStage("setup");
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Failed to load quiz.");
        setStage("setup");
      });
  }, [documentId]);

  function startQuiz() {
    setIndex(0);
    setCorrectCount(0);
    setSelectedOption(null);
    setAttemptResult(null);
    setMastery(null);
    setStage("taking");
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const qs = await api.generateQuiz(documentId, count, difficulty);
      setQuestions(qs);
      startQuiz();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate quiz.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSelectOption(optionIndex: number) {
    if (submitting || attemptResult) return;
    const question = questions[index];
    setSelectedOption(optionIndex);
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.submitQuizAttempt(question.id, optionIndex);
      setAttemptResult(result);
      if (result.correct) setCorrectCount((c) => c + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit answer.");
      setSelectedOption(null);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleNext() {
    if (index + 1 < questions.length) {
      setIndex((i) => i + 1);
      setSelectedOption(null);
      setAttemptResult(null);
      return;
    }

    setStage("results");
    setMasteryError(null);
    try {
      const m = await api.getMastery(documentId);
      setMastery(m);
    } catch (err) {
      setMasteryError(err instanceof ApiError ? err.message : "Failed to load mastery breakdown.");
    }
  }

  if (stage === "loading") return <Loading label="Loading quiz..." />;

  if (stage === "setup") {
    const hasExistingQuiz = questions.length > 0;
    return (
      <div className="flex flex-col gap-4">
        {error && <ErrorBanner message={error} />}
        <Card className="flex flex-col gap-5 p-5">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Difficulty</h3>
            <div className="mt-2 flex gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDifficulty(d.value)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
                    difficulty === d.value
                      ? "bg-accent text-accent-foreground"
                      : "border border-border text-muted hover:bg-surface-hover hover:text-foreground"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">Number of questions</h3>
            <select
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="mt-2 w-fit rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
            >
              {COUNTS.map((c) => (
                <option key={c} value={c}>
                  {c} questions
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-2">
            {hasExistingQuiz && (
              <Button variant="secondary" icon={Play} onClick={startQuiz} disabled={generating}>
                Continue
              </Button>
            )}
            <Button
              variant={hasExistingQuiz ? "secondary" : "primary"}
              icon={generating ? undefined : hasExistingQuiz ? RotateCcw : Sparkles}
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating && <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.25} />}
              {generating ? "Generating quiz..." : hasExistingQuiz ? "Retake Quiz" : "Generate Quiz"}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (stage === "taking") {
    const question = questions[index];
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <Badge variant="accent">{question.topic}</Badge>
          <span className="text-sm text-muted">
            Question {index + 1} of {questions.length}
          </span>
        </div>

        {error && <ErrorBanner message={error} />}

        <Card className="flex flex-col gap-4 p-6">
          <p className="text-lg text-foreground">{question.question}</p>

          <div className="flex flex-col gap-2">
            {question.options.map((option, i) => {
              const isSelected = selectedOption === i;
              const isCorrectOption = attemptResult !== null && i === attemptResult.correct_option_index;
              const isWrongSelection = attemptResult !== null && isSelected && !attemptResult.correct;

              let stateClasses = "border-border hover:border-border-strong hover:bg-surface-hover";
              if (isCorrectOption) {
                stateClasses = "border-success bg-success/10 text-success";
              } else if (isWrongSelection) {
                stateClasses = "border-danger bg-danger/10 text-danger-foreground";
              } else if (isSelected) {
                stateClasses = "border-accent";
              }

              return (
                <button
                  key={i}
                  type="button"
                  disabled={submitting || attemptResult !== null}
                  onClick={() => handleSelectOption(i)}
                  className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left text-sm transition-colors duration-150 disabled:cursor-not-allowed ${stateClasses}`}
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-hover text-xs font-semibold text-muted">
                    {OPTION_LETTERS[i]}
                  </span>
                  <span className="flex-1 text-foreground">{option}</span>
                  {isCorrectOption && <CheckCircle2 className="h-4 w-4 shrink-0" strokeWidth={2.25} />}
                  {isWrongSelection && <XCircle className="h-4 w-4 shrink-0" strokeWidth={2.25} />}
                </button>
              );
            })}
          </div>

          {attemptResult && (
            <div className="flex items-center justify-between border-t border-border pt-4">
              <span
                className={`flex items-center gap-2 text-sm font-medium ${
                  attemptResult.correct ? "text-success" : "text-danger-foreground"
                }`}
              >
                {attemptResult.correct ? (
                  <CheckCircle2 className="h-4 w-4" strokeWidth={2.25} />
                ) : (
                  <XCircle className="h-4 w-4" strokeWidth={2.25} />
                )}
                {attemptResult.correct ? "Correct!" : "Incorrect"}
              </span>
              <Button icon={ChevronRight} onClick={handleNext}>
                {index + 1 < questions.length ? "Next" : "See results"}
              </Button>
            </div>
          )}
        </Card>
      </div>
    );
  }

  const total = questions.length;
  const scorePercent = total > 0 ? Math.round((correctCount / total) * 100) : 0;

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col items-center gap-2 p-6 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/15 text-accent">
          <Trophy className="h-6 w-6" strokeWidth={2} />
        </span>
        <p className="text-2xl font-semibold text-foreground">
          {correctCount} / {total}
        </p>
        <p className="text-sm text-muted">{scorePercent}% correct this attempt</p>
      </Card>

      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-foreground">Mastery by topic</h3>
        {masteryError && <ErrorBanner message={masteryError} />}
        {!masteryError && mastery === null && <Loading label="Loading mastery breakdown..." />}
        {mastery !== null && mastery.length === 0 && (
          <EmptyState icon={ListChecks} title="No mastery data yet" />
        )}
        {mastery !== null && mastery.length > 0 && (
          <Card className="flex flex-col gap-4 p-5">
            {mastery.map((m) => {
              const colors = masteryColor(m.mastery_percent);
              return (
                <div key={m.topic} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-foreground">{m.topic}</span>
                    <span className={`font-medium ${colors.text}`}>
                      {m.mastery_percent}% ({m.correct_attempts}/{m.total_attempts})
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-border">
                    <div
                      className={`h-full rounded-full ${colors.bar}`}
                      style={{ width: `${m.mastery_percent}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </Card>
        )}
      </div>

      <Button variant="secondary" icon={RotateCcw} onClick={() => setStage("setup")} className="w-fit">
        Back to setup
      </Button>
    </div>
  );
}
