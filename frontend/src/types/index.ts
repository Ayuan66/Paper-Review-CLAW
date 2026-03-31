export interface Review {
  agent_name: string;
  model: string;
  content: string;
}

export interface ProgressEvent {
  type: "start" | "complete" | "error";
  agent: string;
  phase: string;
  preview: string; // short preview text shown in progress panel
  timestamp: string;
}

export interface SessionResults {
  session_id: string;
  status: string;
  pdf_filename: string;
  agent_config: Record<string, string>;
  reviews: Review[];
  editor_summary: string;
  author_response: string;
  author_response_edited: string;
  reviews_round2: Review[];
  editor_summary_round2: string;
  final_markdown: string;
  created_at: string;
}

export interface ModelOption {
  id: string;
  name: string;
}

export interface ModelsResponse {
  models: ModelOption[];
  roles: Record<string, string>;
  defaults: Record<string, string>;
}

export interface VenueOption {
  id: string;
  name: string;
  type: "conference" | "journal";
}

export type ReviewStatus =
  | "idle"
  | "uploading"
  | "running"
  | "waiting_for_edit"
  | "complete"
  | "error";

// ---------------------------------------------------------------------------
// Research Idea CLAW types
// ---------------------------------------------------------------------------

export interface IdeaDiscussion {
  round: number;
  agent: string;
  role: string;
  content: string;
  timestamp: string;
}

export interface IdeaSummary {
  round: number;
  content: string;
  timestamp: string;
}

export interface IdeaSearchResult {
  title: string;
  authors: string[];
  year: number;
  citationCount: number;
  abstract: string;
  tldr: string;
  url: string;
}

export interface IdeaSessionResults {
  session_id: string;
  status: string;
  research_question: string;
  user_context: string;
  agent_config: Record<string, string>;
  discussions: IdeaDiscussion[];
  summaries: IdeaSummary[];
  user_answers: {
    round: number;
    agent: string;
    question: string;
    answer: string;
  }[];
  search_results: IdeaSearchResult[];
  current_round: number;
  max_rounds: number;
  created_at: string;
}

export interface IdeaProgressEvent {
  type:
    | "start"
    | "complete"
    | "partial"
    | "internal_round_start"
    | "round_start"
    | "round_complete"
    | "revision_received"
    | "info"
    | "error";
  agent: string;
  role: string;
  content: string;
  timestamp: string;
  phase: string;
  round: number;
  internal_round?: number;
  refined_question?: string;
  [key: string]: unknown;
}

export type IdeaStatus =
  | "idle"
  | "running"
  | "waiting_for_revision"
  | "complete"
  | "error";
