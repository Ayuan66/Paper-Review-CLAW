import { Button, Card, Input, Space, Typography } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { finishIdeaEarly, submitIdeaRevision } from "../../api/ideaClient";
import { useIdeaStore } from "../../store/ideaStore";
import MarkdownViewer from "../MarkdownViewer";

const { Title, Text } = Typography;
const { TextArea } = Input;

interface Props {
  sessionId: string;
}

export default function RevisionInput({ sessionId }: Props) {
  const { t } = useTranslation();
  const {
    status,
    researchQuestion,
    userContext,
    currentRound,
    maxRounds,
    progressEvents,
    setStatus,
    setResearchQuestion,
    setUserContext,
    addProgressEvent,
  } = useIdeaStore();

  const [editedQuestion, setEditedQuestion] = useState(researchQuestion);
  const [editedContext, setEditedContext] = useState(userContext);
  const [submitting, setSubmitting] = useState(false);
  const [finishing, setFinishing] = useState(false);

  const visible = status === "waiting_for_revision";

  // Find the latest summary for this round
  const summaryEvent = [...progressEvents]
    .reverse()
    .find((e) => e.agent === "summarizer" && e.type === "complete");

  if (!visible) return null;

  async function handleContinue() {
    setSubmitting(true);
    try {
      await submitIdeaRevision(
        sessionId,
        editedQuestion.trim(),
        editedContext.trim(),
      );
      setResearchQuestion(editedQuestion.trim());
      setUserContext(editedContext.trim());
      addProgressEvent({
        type: "revision_received",
        agent: "system",
        role: "system",
        content: editedQuestion.trim(),
        timestamp: new Date().toISOString(),
        phase: "discussing",
        round: currentRound,
      });
      setStatus("running");
    } catch {
      // keep visible on error
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFinish() {
    setFinishing(true);
    try {
      await finishIdeaEarly(sessionId);
      setStatus("running");
    } catch {
      // ignore
    } finally {
      setFinishing(false);
    }
  }

  return (
    <Card
      size="small"
      title={
        <Title level={5} style={{ margin: 0 }}>
          {t("idea.revision.title", { round: currentRound })}
        </Title>
      }
      style={{ borderColor: "#0891b2" }}
    >
      {summaryEvent && (
        <div style={{ marginBottom: 16 }}>
          <Text strong>{t("idea.revision.summaryLabel")}</Text>
          <MarkdownViewer content={summaryEvent.content} />
        </div>
      )}

      <Text strong>{t("idea.revision.questionLabel")}</Text>
      <TextArea
        rows={3}
        value={editedQuestion}
        onChange={(e) => setEditedQuestion(e.target.value)}
        style={{ marginTop: 4, marginBottom: 12 }}
      />

      <Text strong>{t("idea.revision.contextLabel")}</Text>
      <TextArea
        rows={2}
        value={editedContext}
        onChange={(e) => setEditedContext(e.target.value)}
        style={{ marginTop: 4, marginBottom: 12 }}
      />

      <Space>
        <Button
          type="primary"
          loading={submitting}
          disabled={currentRound >= maxRounds}
          onClick={handleContinue}
        >
          {t("idea.revision.continue")}
        </Button>
        <Button loading={finishing} onClick={handleFinish}>
          {t("idea.revision.finish")}
        </Button>
      </Space>
    </Card>
  );
}
