import { MessageOutlined, SendOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Modal, Space, Tag, Typography } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { submitIdeaAnswer } from "../../api/ideaClient";
import { useIdeaStore } from "../../store/ideaStore";

const { Text } = Typography;
const { TextArea } = Input;

interface Props {
  sessionId: string;
}

export default function QuestionDialog({ sessionId }: Props) {
  const { t } = useTranslation();
  const {
    status,
    pendingQuestion,
    pendingQuestionAgent,
    clearPendingQuestion,
    setStatus,
    addProgressEvent,
  } = useIdeaStore();
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const visible = status === "waiting_for_input" && !!pendingQuestion;

  async function handleSubmit() {
    if (!answer.trim()) return;
    setSubmitting(true);
    try {
      await submitIdeaAnswer(sessionId, answer.trim());
      addProgressEvent({
        type: "answer_received",
        agent: pendingQuestionAgent,
        role: pendingQuestionAgent,
        content: answer.trim(),
        timestamp: new Date().toISOString(),
        phase: "discussing",
        round: 0,
      });
      clearPendingQuestion();
      setStatus("running");
      setAnswer("");
    } catch {
      // keep dialog open on error
    } finally {
      setSubmitting(false);
    }
  }

  const agentLabel = t(`idea.agents.${pendingQuestionAgent}`, {
    defaultValue: pendingQuestionAgent,
  });
  const tagColor =
    (
      {
        innovation_expert: "blue",
        feasibility_analyst: "green",
        methodology_expert: "purple",
        summarizer: "gold",
      } as Record<string, string>
    )[pendingQuestionAgent] ?? "default";

  return (
    <Modal
      open={visible}
      title={
        <Space>
          <MessageOutlined style={{ color: "#fa8c16" }} />
          <Text strong>{t("idea.question.title")}</Text>
          <Tag color={tagColor}>{agentLabel}</Tag>
        </Space>
      }
      footer={null}
      closable={false}
      maskClosable={false}
      width={560}
    >
      <Alert
        message={pendingQuestion}
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <TextArea
        rows={4}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder={t("idea.question.answerPlaceholder")}
        autoFocus
        onPressEnter={(e) => {
          if (e.ctrlKey || e.metaKey) handleSubmit();
        }}
      />
      <Text
        type="secondary"
        style={{ fontSize: 11, display: "block", marginTop: 4 }}
      >
        {t("idea.question.ctrlEnterHint")}
      </Text>
      <Space
        style={{ marginTop: 12, justifyContent: "flex-end", width: "100%" }}
      >
        <Button
          type="primary"
          icon={<SendOutlined />}
          loading={submitting}
          disabled={!answer.trim()}
          onClick={handleSubmit}
        >
          {t("idea.question.submit")}
        </Button>
      </Space>
    </Modal>
  );
}
