import { create } from "zustand";
import type {
  IdeaProgressEvent,
  IdeaSearchResult,
  IdeaSessionResults,
  IdeaStatus,
} from "../types";

const DEFAULT_IDEA_MODELS: Record<string, string> = {
  safety_engineer: "deepseek/deepseek-chat",
  safety_professor: "deepseek/deepseek-chat",
  nasa_expert: "deepseek/deepseek-chat",
  arbitrator: "deepseek/deepseek-chat",
};

interface IdeaStore {
  sessionId: string | null;
  researchQuestion: string;
  userContext: string;
  agentConfig: Record<string, string>;
  maxRounds: number;
  internalRounds: number;
  status: IdeaStatus;
  progressEvents: IdeaProgressEvent[];
  results: IdeaSessionResults | null;
  error: string;
  currentRound: number;
  searchResults: IdeaSearchResult[];

  setSessionId: (id: string) => void;
  setResearchQuestion: (q: string) => void;
  setUserContext: (c: string) => void;
  setAgentConfig: (config: Record<string, string>) => void;
  updateAgentRole: (role: string, model: string) => void;
  setMaxRounds: (n: number) => void;
  setInternalRounds: (n: number) => void;
  setStatus: (s: IdeaStatus) => void;
  addProgressEvent: (event: IdeaProgressEvent) => void;
  setResults: (results: IdeaSessionResults) => void;
  setError: (msg: string) => void;
  setCurrentRound: (round: number) => void;
  setSearchResults: (results: IdeaSearchResult[]) => void;
  reset: () => void;
}

export const useIdeaStore = create<IdeaStore>((set) => ({
  sessionId: null,
  researchQuestion: "",
  userContext: "",
  agentConfig: { ...DEFAULT_IDEA_MODELS },
  maxRounds: 3,
  internalRounds: 3,
  status: "idle",
  progressEvents: [],
  results: null,
  error: "",
  currentRound: 0,
  searchResults: [],

  setSessionId: (id) => set({ sessionId: id }),
  setResearchQuestion: (researchQuestion) => set({ researchQuestion }),
  setUserContext: (userContext) => set({ userContext }),
  setAgentConfig: (agentConfig) => set({ agentConfig }),
  updateAgentRole: (role, model) =>
    set((s) => ({ agentConfig: { ...s.agentConfig, [role]: model } })),
  setMaxRounds: (maxRounds) => set({ maxRounds }),
  setInternalRounds: (internalRounds) => set({ internalRounds }),
  setStatus: (status) => set({ status }),
  addProgressEvent: (event) =>
    set((s) => ({ progressEvents: [...s.progressEvents, event] })),
  setResults: (results) => set({ results }),
  setError: (error) => set({ error }),
  setCurrentRound: (currentRound) => set({ currentRound }),
  setSearchResults: (searchResults) => set({ searchResults }),
  reset: () =>
    set({
      sessionId: null,
      researchQuestion: "",
      userContext: "",
      agentConfig: { ...DEFAULT_IDEA_MODELS },
      maxRounds: 3,
      internalRounds: 3,
      status: "idle",
      progressEvents: [],
      results: null,
      error: "",
      currentRound: 0,
      searchResults: [],
    }),
}));
