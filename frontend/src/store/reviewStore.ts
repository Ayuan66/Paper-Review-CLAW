import { create } from 'zustand';
import type { ProgressEvent, ReviewStatus, SessionResults } from '../types';
import { DEFAULT_MODELS } from '../constants';

interface ReviewStore {
  sessionId: string | null;
  agentConfig: Record<string, string>;
  maxIterations: number;
  venue: string;
  status: ReviewStatus;
  progressEvents: ProgressEvent[];
  results: SessionResults | null;
  error: string;

  setSessionId: (id: string) => void;
  setAgentConfig: (config: Record<string, string>) => void;
  updateAgentRole: (role: string, model: string) => void;
  setMaxIterations: (n: number) => void;
  setVenue: (v: string) => void;
  setStatus: (s: ReviewStatus) => void;
  addProgressEvent: (event: ProgressEvent) => void;
  setResults: (results: SessionResults) => void;
  setError: (msg: string) => void;
  reset: () => void;
}

export const useReviewStore = create<ReviewStore>((set) => ({
  sessionId: null,
  agentConfig: { ...DEFAULT_MODELS },
  maxIterations: 5,
  venue: '',
  status: 'idle',
  progressEvents: [],
  results: null,
  error: '',

  setSessionId: (id) => set({ sessionId: id }),
  setAgentConfig: (config) => set({ agentConfig: config }),
  updateAgentRole: (role, model) =>
    set((s) => ({ agentConfig: { ...s.agentConfig, [role]: model } })),
  setMaxIterations: (n) => set({ maxIterations: n }),
  setVenue: (venue) => set({ venue }),
  setStatus: (status) => set({ status }),
  addProgressEvent: (event) =>
    set((s) => ({ progressEvents: [...s.progressEvents, event] })),
  setResults: (results) => set({ results }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      sessionId: null,
      agentConfig: { ...DEFAULT_MODELS },
      maxIterations: 5,
      venue: '',
      status: 'idle',
      progressEvents: [],
      results: null,
      error: '',
    }),
}));
