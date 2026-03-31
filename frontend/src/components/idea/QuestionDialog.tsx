import { Alert, Button, Input, Modal, Space, Typography } from "antd";
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
    } catch (e) {
      // keep dialog open on error
    } finally {
      setSubmitting(false);
    }
  }

  const agentLabel = t(`idea.agents.${pendingQuestionAgent}`, {
    defaultValue: pendingQuestionAgent,
  });

  return (
    <Modal
      open={visible}
      title={t("idea.question.title", { agent: agentLabel })}
      footer={null}
      closable={false}
      maskClosable={false}
      width={560}
    >
      <Alert
        message={<Text>{pendingQuestion}</Text>}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <TextArea
        rows={4}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder={t("idea.question.answerPlaceholder")}
        autoFocus
      />
      <Space
        style={{ marginTop: 12, justifyContent: "flex-end", width: "100%" }}
      >
        <Button
          type="primary"
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
