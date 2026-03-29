export interface Review {
  agent_name: string;
  model: string;
  content: string;
}

export interface AuthorDiscussion {
  round: number;
  author: 'author_a' | 'author_b';
  model: string;
  content: string;
}

export interface ProgressEvent {
  type: 'start' | 'complete' | 'error';
  agent: string;
  phase: string;
  preview: string;   // short preview text shown in progress panel
  timestamp: string;
}

export interface SessionResults {
  session_id: string;
  status: string;
  pdf_filename: string;
  agent_config: Record<string, string>;
  reviews: Review[];
  editor_summary: string;
  author_discussions: AuthorDiscussion[];
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
  type: 'conference' | 'journal';
}

export type ReviewStatus = 'idle' | 'uploading' | 'running' | 'complete' | 'error';
