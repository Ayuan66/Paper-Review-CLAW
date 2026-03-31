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
