import { Button, Card, Input, Space, Typography } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { submitAuthorResponse } from "../api/client";
import { useReviewStore } from "../store/reviewStore";
import MarkdownViewer from "./MarkdownViewer";

const { Title, Text } = Typography;
const { TextArea } = Input;

interface Props {
  onSubmitted: () => void;
}

export default function AuthorResponseEditor({ onSubmitted }: Props) {
  const { t } = useTranslation();
  const {
    sessionId,
    authorResponse,
    editedResponse,
    setEditedResponse,
    setStatus,
  } = useReviewStore();
  const [preview, setPreview] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!sessionId) return;
    setSubmitting(true);
    try {
      await submitAuthorResponse(sessionId, editedResponse);
      setStatus("running");
      onSubmitted();
    } catch {
      // error handled by caller
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setEditedResponse(authorResponse);
  };

  return (
    <Card
      title={
        <Title level={4} style={{ margin: 0 }}>
          {t("authorEditor.title")}
        </Title>
      }
      extra={
        <Space>
          <Button size="small" onClick={() => setPreview((p) => !p)}>
            {preview
              ? t("authorEditor.editMode")
              : t("authorEditor.previewMode")}
          </Button>
        </Space>
      }
    >
      <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        {t("authorEditor.editHint")}
      </Text>

      {preview ? (
        <MarkdownViewer content={editedResponse} />
      ) : (
        <TextArea
          value={editedResponse}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
            setEditedResponse(e.target.value)
          }
          rows={20}
          style={{ fontFamily: "monospace", fontSize: 13 }}
        />
      )}

      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          loading={submitting}
          onClick={handleSubmit}
          disabled={!editedResponse.trim()}
        >
          {t("authorEditor.submitBtn")}
        </Button>
        <Button onClick={handleReset}>{t("authorEditor.resetBtn")}</Button>
      </Space>
    </Card>
  );
}
