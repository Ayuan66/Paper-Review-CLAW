import { App, Col, Row, Space, Typography } from "antd";
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  connectIdeaSSE,
  getIdeaResults,
  startIdeaDiscussion,
} from "../api/ideaClient";
import DiscussionPanel from "../components/idea/DiscussionPanel";
import IdeaInput from "../components/idea/IdeaInput";
import QuestionDialog from "../components/idea/QuestionDialog";
import RevisionInput from "../components/idea/RevisionInput";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { useIdeaStore } from "../store/ideaStore";
import type { IdeaProgressEvent } from "../types";

const { Title, Text } = Typography;

export default function IdeaPage() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  const esRef = useRef<EventSource | null>(null);

  const {
    sessionId,
    researchQuestion,
    userContext,
    agentConfig,
    maxRounds,
    status,
    setSessionId,
    setStatus,
    addProgressEvent,
    setResults,
    setError,
    setPendingQuestion,
    setCurrentRound,
    reset,
    error,
  } = useIdeaStore();

  const handleSSEEvent = (event: IdeaProgressEvent) => {
    addProgressEvent(event);

    if (event.type === "question") {
      setPendingQuestion(event.content, event.agent);
      setStatus("waiting_for_input");
    } else if (event.type === "round_complete") {
      setCurrentRound(event.round);
      setStatus("waiting_for_revision");
    } else if (event.type === "round_start") {
      setCurrentRound(event.round);
      setStatus("running");
    } else if (event.type === "error") {
      setStatus("error");
      setError(event.content);
    }
  };

  const connectAndListen = (sid: string) => {
    const es = connectIdeaSSE(
      sid,
      handleSSEEvent,
      async () => {
        esRef.current = null;
        try {
          const results = await getIdeaResults(sid);
          setResults(results);
          setStatus("complete");
          message.success(t("idea.page.complete"));
        } catch {
          setStatus("error");
          setError(t("idea.page.fetchResultsFailed"));
        }
      },
      (err) => {
        esRef.current = null;
        setStatus("error");
        setError(t("idea.page.connectionLost", { msg: err }));
      },
    );
    esRef.current = es;
  };

  const handleStart = async () => {
    if (!researchQuestion.trim()) {
      message.warning(t("idea.input.questionRequired"));
      return;
    }

    try {
      setStatus("running");
      const { session_id } = await startIdeaDiscussion({
        research_question: researchQuestion,
        user_context: userContext,
        agent_config: agentConfig,
        max_rounds: maxRounds,
      });
      setSessionId(session_id);
      connectAndListen(session_id);
    } catch (e) {
      setStatus("error");
      setError(String(e));
    }
  };

  const handleReset = () => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    reset();
  };

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1400, margin: "0 auto" }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Space direction="vertical" size={0}>
          <Title level={2} style={{ margin: 0 }}>
            {t("idea.page.title")}
          </Title>
          <Text type="secondary">{t("idea.page.subtitle")}</Text>
        </Space>
        <LanguageSwitcher />
      </Row>

      {error && (
        <div style={{ marginBottom: 16 }}>
          <Text type="danger">{error}</Text>
        </div>
      )}

      <Row gutter={[24, 24]}>
        {/* Left column — input + revision */}
        <Col xs={24} lg={10} xl={9}>
          <Space direction="vertical" style={{ width: "100%" }} size={16}>
            <IdeaInput onStart={handleStart} />
            {sessionId && <RevisionInput sessionId={sessionId} />}
          </Space>
        </Col>

        {/* Right column — discussion panel */}
        <Col xs={24} lg={14} xl={15}>
          <DiscussionPanel />
        </Col>
      </Row>

      {/* Question dialog (modal) */}
      {sessionId && <QuestionDialog sessionId={sessionId} />}
    </div>
  );
}
