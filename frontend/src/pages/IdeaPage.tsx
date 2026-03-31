import {
  BulbOutlined,
  DownloadOutlined,
  ReloadOutlined,
  RocketOutlined,
  StopOutlined,
} from "@ant-design/icons";
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Divider,
  Popconfirm,
  Row,
  Space,
  Steps,
  Tag,
  Typography,
} from "antd";
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  cancelIdea,
  connectIdeaSSE,
  downloadIdeaMarkdown,
  getIdeaResults,
  startIdeaDiscussion,
} from "../api/ideaClient";
import DiscussionPanel from "../components/idea/DiscussionPanel";
import IdeaInput from "../components/idea/IdeaInput";
import RevisionInput from "../components/idea/RevisionInput";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { useIdeaStore } from "../store/ideaStore";
import type { IdeaProgressEvent, IdeaStatus } from "../types";

const { Title, Text } = Typography;

function currentStep(status: IdeaStatus): number {
  if (status === "idle") return 0;
  if (status === "running") return 1;
  if (status === "waiting_for_revision") return 2;
  if (status === "complete") return 3;
  return 0;
}

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
    internalRounds,
    status,
    currentRound,
    setSessionId,
    setStatus,
    addProgressEvent,
    setResults,
    setError,
    setResearchQuestion,
    setCurrentRound,
    reset,
    error,
  } = useIdeaStore();

  const handleSSEEvent = (event: IdeaProgressEvent) => {
    addProgressEvent(event);
    if (event.type === "round_complete") {
      setCurrentRound(event.round);
      setStatus("waiting_for_revision");
      // Auto-fill refined question from arbitrator into the input box
      if (event.refined_question) {
        setResearchQuestion(event.refined_question as string);
      }
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
    setStatus("running");
    setError("");
    try {
      const { session_id } = await startIdeaDiscussion({
        research_question: researchQuestion,
        user_context: userContext,
        agent_config: agentConfig,
        max_rounds: maxRounds,
        internal_rounds: internalRounds,
      });
      setSessionId(session_id);
      connectAndListen(session_id);
    } catch (e) {
      setStatus("error");
      setError(String(e));
    }
  };

  const handleCancel = async () => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    if (sessionId) {
      try {
        await cancelIdea(sessionId);
      } catch {
        /* best-effort */
      }
    }
    setStatus("error");
    setError(t("idea.page.cancelledByUser"));
  };

  const handleReset = () => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    reset();
  };

  const isRunning = status === "running";
  const isWaitingRevision = status === "waiting_for_revision";
  const isComplete = status === "complete";
  const isError = status === "error";
  const step = currentStep(status);

  const steps = [
    { title: t("idea.steps.input") },
    { title: t("idea.steps.discussing") },
    { title: t("idea.steps.revision") },
    { title: t("idea.steps.complete") },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 16px" }}>
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        {/* Header — matches Paper Review CLAW style */}
        <Card
          style={{
            background:
              "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 60%, #d1fae5 100%)",
            borderColor: "#bbf7d0",
            borderRadius: 12,
          }}
          styles={{ body: { padding: "20px 24px" } }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <Title level={2} style={{ marginBottom: 4, color: "#15803d" }}>
                <BulbOutlined style={{ marginRight: 8 }} />
                {t("idea.page.title")}
              </Title>
              <Text style={{ fontSize: 14, color: "#16a34a" }}>
                {t("idea.page.subtitle")}
              </Text>
            </div>
            <Space>
              {isRunning && (
                <Tag color="processing">
                  {t("idea.page.statusRunning", { round: currentRound })}
                </Tag>
              )}
              {isWaitingRevision && (
                <Tag color="warning">{t("idea.page.statusRevision")}</Tag>
              )}
              {isComplete && (
                <Tag color="success">{t("idea.page.statusComplete")}</Tag>
              )}
              <LanguageSwitcher />
            </Space>
          </div>
        </Card>

        <Steps current={step} items={steps} size="small" />

        {/* Input + Config */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={10}>
            <IdeaInput />
          </Col>
          <Col xs={24} md={14}>
            {isWaitingRevision && sessionId && (
              <RevisionInput sessionId={sessionId} />
            )}
          </Col>
        </Row>

        {/* Action Buttons */}
        <div style={{ textAlign: "center" }}>
          <Space>
            {!isWaitingRevision && (
              <Button
                type="primary"
                size="large"
                onClick={handleStart}
                loading={isRunning}
                disabled={isRunning || isWaitingRevision}
                icon={<RocketOutlined />}
                style={{ minWidth: 160 }}
              >
                {isRunning
                  ? t("idea.input.starting")
                  : isComplete
                    ? t("idea.page.restart")
                    : t("idea.input.start")}
              </Button>
            )}

            {isRunning && (
              <Popconfirm
                title={t("idea.page.cancelConfirmTitle")}
                description={t("idea.page.cancelConfirmDesc")}
                onConfirm={handleCancel}
                okText={t("idea.page.cancelConfirmOk")}
                cancelText={t("idea.page.cancelConfirmCancel")}
                okButtonProps={{ danger: true }}
              >
                <Button size="large" icon={<StopOutlined />} danger>
                  {t("idea.page.cancelButton")}
                </Button>
              </Popconfirm>
            )}

            {(isError || isComplete) && (
              <Button
                size="large"
                icon={<ReloadOutlined />}
                onClick={handleReset}
              >
                {t("idea.page.resetButton")}
              </Button>
            )}

            {sessionId && (isComplete || isWaitingRevision) && (
              <Button
                size="large"
                icon={<DownloadOutlined />}
                onClick={() => downloadIdeaMarkdown(sessionId)}
              >
                {t("idea.page.downloadButton")}
              </Button>
            )}
          </Space>
        </div>

        {error && (
          <Alert
            type="error"
            message={error}
            showIcon
            closable
            onClose={() => setError("")}
          />
        )}

        <Divider style={{ margin: "8px 0" }} />

        {/* Discussion Panel */}
        <Row gutter={16}>
          <Col span={24}>
            <DiscussionPanel />
          </Col>
        </Row>
      </Space>
    </div>
  );
}
