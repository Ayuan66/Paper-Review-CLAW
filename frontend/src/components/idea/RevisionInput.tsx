import {
  ArrowRightOutlined,
  CheckOutlined,
  EditOutlined,
} from "@ant-design/icons";
import { Alert, Button, Card, Form, Input, Space, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { finishIdeaEarly, submitIdeaRevision } from "../../api/ideaClient";
import { useIdeaStore } from "../../store/ideaStore";

const { Title, Text } = Typography;
const { TextArea } = Input;

interface Props {
  sessionId: string;
}

export default function RevisionInput({ sessionId }: Props) {
  const { t } = useTranslation();
  const {
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

  // Sync editedQuestion when store is updated by arbitrator's refined question
  useEffect(() => {
    setEditedQuestion(researchQuestion);
  }, [researchQuestion]);

  // Find the latest arbitrator output for this round
  const summaryEvent = [...progressEvents]
    .reverse()
    .find((e) => e.agent === "arbitrator" && e.type === "complete");

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

  const hasMoreRounds = currentRound < maxRounds;

  return (
    <Card
      size="small"
      title={
        <Space>
          <EditOutlined style={{ color: "#d97706" }} />
          <Title level={5} style={{ margin: 0 }}>
            {t("idea.revision.title", { round: currentRound })}
          </Title>
          <Tag color="warning">
            {t("idea.revision.roundProgress", {
              current: currentRound,
              max: maxRounds,
            })}
          </Tag>
        </Space>
      }
      style={{ borderColor: "#fbbf24" }}
    >
      {summaryEvent && (
        <Alert
          type="info"
          showIcon
          message={<Text strong>{t("idea.revision.summaryLabel")}</Text>}
          description={
            <Text style={{ fontSize: 12, whiteSpace: "pre-wrap" }}>
              {summaryEvent.content.slice(0, 400)}
              {summaryEvent.content.length > 400 ? "…" : ""}
            </Text>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <Form layout="vertical" size="small">
        <Form.Item
          label={<Text strong>{t("idea.revision.questionLabel")}</Text>}
        >
          <TextArea
            rows={3}
            value={editedQuestion}
            onChange={(e) => setEditedQuestion(e.target.value)}
          />
        </Form.Item>

        <Form.Item
          label={<Text strong>{t("idea.revision.contextLabel")}</Text>}
        >
          <TextArea
            rows={2}
            value={editedContext}
            onChange={(e) => setEditedContext(e.target.value)}
          />
        </Form.Item>
      </Form>

      <Space>
        <Button
          type="primary"
          icon={<ArrowRightOutlined />}
          loading={submitting}
          disabled={!hasMoreRounds || !editedQuestion.trim()}
          onClick={handleContinue}
        >
          {t("idea.revision.continue")}
        </Button>
        <Button
          icon={<CheckOutlined />}
          loading={finishing}
          onClick={handleFinish}
        >
          {t("idea.revision.finish")}
        </Button>
      </Space>
    </Card>
  );
}
