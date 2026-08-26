const API_BASE = "http://localhost:8000";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError("Could not reach the backend. Is it running on localhost:8000?");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type DocumentSummary = {
  id: number;
  source_name: string;
  source_type: string;
  created_at: string;
  job_status: string | null;
};

export type Note = {
  id: number;
  content: string;
};

export type Flashcard = {
  id: number;
  question: string;
  answer: string;
};

export type DueCard = {
  id: number;
  document_id: number;
  question: string;
  answer: string;
};

export type Grade = "again" | "hard" | "good" | "easy";

export type ChatCitation = {
  chunk_id: number;
  document_id: number;
  chunk_index: number;
  quote: string;
  chunk_text: string;
};

export type ChatResponse = {
  answer: string;
  citations: ChatCitation[];
};

export type IngestResponse = {
  document_id: number;
  job_id: number;
};

export const api = {
  listDocuments: () => request<DocumentSummary[]>("/documents"),

  getDocumentNotes: (documentId: number) =>
    request<Note[]>(`/documents/${documentId}/notes`),

  getDocumentFlashcards: (documentId: number) =>
    request<Flashcard[]>(`/documents/${documentId}/flashcards`),

  getDueCards: (limit = 20) => request<DueCard[]>(`/review/due?limit=${limit}`),

  submitReview: (flashcardId: number, grade: Grade) =>
    request<{ status: string }>(`/review/${flashcardId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grade }),
    }),

  ingestText: (text: string) =>
    request<IngestResponse>("/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),

  ingestFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<IngestResponse>("/ingest", { method: "POST", body: form });
  },

  chat: (question: string, documentId: number | null) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, document_id: documentId }),
    }),
};
