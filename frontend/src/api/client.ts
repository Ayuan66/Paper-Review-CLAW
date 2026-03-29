import axios from 'axios';
import type { ModelsResponse, ProgressEvent, SessionResults, VenueOption } from '../types';

const http = axios.create({ baseURL: '/api' });

export async function uploadPdf(file: File): Promise<{ session_id: string; filename: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await http.post('/upload', form);
  return res.data;
}

export async function startReview(
  sessionId: string,
  agentConfig: Record<string, string>,
  maxIterations = 5,
  venue = ''
): Promise<void> {
  await http.post(`/sessions/${sessionId}/start`, {
    agent_config: agentConfig,
    max_iterations: maxIterations,
    venue,
  });
}

export async function getVenues(): Promise<VenueOption[]> {
  const res = await http.get('/venues');
  return res.data.venues;
}

export async function getResults(sessionId: string): Promise<SessionResults> {
  const res = await http.get(`/sessions/${sessionId}/results`);
  return res.data;
}

export async function getModels(): Promise<ModelsResponse> {
  const res = await http.get('/models');
  return res.data;
}

export function connectSSE(
  sessionId: string,
  onEvent: (event: ProgressEvent) => void,
  onComplete: () => void,
  onError: (err: string) => void
): EventSource {
  const es = new EventSource(`/api/sessions/${sessionId}/stream`);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as ProgressEvent & { phase?: string };
      if (data.phase === 'complete') {
        es.close();
        onComplete();
      } else {
        onEvent(data as ProgressEvent);
      }
    } catch {
      // ignore parse errors
    }
  };

  es.onerror = () => {
    es.close();
    onError('SSE 连接断开');
  };

  return es;
}

export async function cancelReview(sessionId: string): Promise<void> {
  await http.post(`/sessions/${sessionId}/cancel`);
}

export function downloadResult(sessionId: string): void {
  window.open(`/api/sessions/${sessionId}/download`, '_blank');
}
