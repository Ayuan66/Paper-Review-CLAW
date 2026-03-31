import axios from "axios";
import type { IdeaProgressEvent, IdeaSessionResults } from "../types";

const http = axios.create({ baseURL: "/api/idea" });

export async function startIdeaDiscussion(params: {
  research_question: string;
  user_context?: string;
  agent_config?: Record<string, string>;
  max_rounds?: number;
}): Promise<{ session_id: string }> {
  const res = await http.post("/start", params);
  return res.data;
}

export async function getIdeaResults(
  sessionId: string,
): Promise<IdeaSessionResults> {
  const res = await http.get(`/sessions/${sessionId}/results`);
  return res.data;
}

export async function submitIdeaAnswer(
  sessionId: string,
  answer: string,
): Promise<void> {
  await http.post(`/sessions/${sessionId}/answer`, { answer });
}

export async function submitIdeaRevision(
  sessionId: string,
  research_question: string,
  user_context: string,
): Promise<void> {
  await http.post(`/sessions/${sessionId}/revise`, {
    research_question,
    user_context,
  });
}

export async function finishIdeaEarly(sessionId: string): Promise<void> {
  await http.post(`/sessions/${sessionId}/finish`);
}

export async function cancelIdea(sessionId: string): Promise<void> {
  await http.post(`/sessions/${sessionId}/cancel`);
}

export function connectIdeaSSE(
  sessionId: string,
  onEvent: (event: IdeaProgressEvent) => void,
  onComplete: () => void,
  onError: (err: string) => void,
): EventSource {
  const es = new EventSource(`/api/idea/sessions/${sessionId}/stream`);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as IdeaProgressEvent;
      if (data.type === "complete" && data.phase === "complete") {
        es.close();
        onComplete();
      } else {
        onEvent(data);
      }
    } catch {
      // ignore parse errors
    }
  };

  es.onerror = () => {
    es.close();
    onError("SSE 连接断开");
  };

  return es;
}
