import { create } from "zustand";
import type { ProgressEvent, ReviewStatus, SessionResults } from "../types";
import { DEFAULT_MODELS } from "../constants";

interface ReviewStore {
  sessionId: string | null;
  agentConfig: Record<string, string>;
  venue: string;
  status: ReviewStatus;
  progressEvents: ProgressEvent[];
  results: SessionResults | null;
  error: string;
  authorResponse: string;
  editedResponse: string;

  setSessionId: (id: string) => void;
  setAgentConfig: (config: Record<string, string>) => void;
  updateAgentRole: (role: string, model: string) => void;
  setVenue: (v: string) => void;
  setStatus: (s: ReviewStatus) => void;
  addProgressEvent: (event: ProgressEvent) => void;
  setResults: (results: SessionResults) => void;
  setError: (msg: string) => void;
  setAuthorResponse: (text: string) => void;
  setEditedResponse: (text: string) => void;
  reset: () => void;
}

export const useReviewStore = create<ReviewStore>((set) => ({
  sessionId: null,
  agentConfig: { ...DEFAULT_MODELS },
  venue: "",
  status: "idle",
  progressEvents: [],
  results: null,
  error: "",
  authorResponse: "",
  editedResponse: "",

  setSessionId: (id) => set({ sessionId: id }),
  setAgentConfig: (config) => set({ agentConfig: config }),
  updateAgentRole: (role, model) =>
    set((s) => ({ agentConfig: { ...s.agentConfig, [role]: model } })),
  setVenue: (venue) => set({ venue }),
  setStatus: (status) => set({ status }),
  addProgressEvent: (event) =>
    set((s) => ({ progressEvents: [...s.progressEvents, event] })),
  setResults: (results) => set({ results }),
  setError: (error) => set({ error }),
  setAuthorResponse: (authorResponse) =>
    set({ authorResponse, editedResponse: authorResponse }),
  setEditedResponse: (editedResponse) => set({ editedResponse }),
  reset: () =>
    set({
      sessionId: null,
      agentConfig: { ...DEFAULT_MODELS },
      venue: "",
      status: "idle",
      progressEvents: [],
      results: null,
      error: "",
      authorResponse: "",
      editedResponse: "",
    }),
}));
