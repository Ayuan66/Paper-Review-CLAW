import {
  CheckCircleFilled,
  DownloadOutlined,
  ExperimentOutlined,
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
  Typography,
} from "antd";
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  cancelReview,
  connectSSE,
  downloadZip,
  getResults,
  startReview,
} from "../api/client";
import AgentConfig from "../components/AgentConfig";
import AuthorResponseEditor from "../components/AuthorResponseEditor";
import LanguageSwitcher from "../components/LanguageSwitcher";
import PdfUpload from "../components/PdfUpload";
import ProgressPanel from "../components/ProgressPanel";
import ReviewResults from "../components/ReviewResults";
import VenueSelect from "../components/VenueSelect";
import { useReviewStore } from "../store/reviewStore";

const { Title, Text } = Typography;

function currentStep(status: string, sessionId: string | null): number {
  if (!sessionId) return 0;
  if (status === "idle") return 1;
  if (status === "running") return 2;
  if (status === "waiting_for_edit") return 3;
  if (status === "complete") return 4;
  return 1;
}

export default function ReviewPage() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  const esRef = useRef<EventSource | null>(null);
  const {
    sessionId,
    agentConfig,
    venue,
    status,
    setStatus,
    addProgressEvent,
    setResults,
    setError,
    setAuthorResponse,
    reset,
    error,
  } = useReviewStore();

  const connectAndListen = (sid: string) => {
    const es = connectSSE(
      sid,
      (event) => addProgressEvent(event),
      async () => {
        esRef.current = null;
        try {
          const results = await getResults(sid);
          setResults(results);
          if (results.status === "waiting_for_author_edit") {
            setAuthorResponse(results.author_response || "");
            setStatus("waiting_for_edit");
          } else {
            setStatus("complete");
            message.success(t("page.startButton") + " ✓");
          }
        } catch {
          setStatus("error");
          setError(t("errors.fetchResultsFailed"));
        }
      },
      (err) => {
        esRef.current = null;
        setStatus("error");
        setError(t("errors.connectionLost", { msg: err }));
      },
    );
    esRef.current = es;
  };

  const handleStart = async () => {
    if (!sessionId) {
      message.warning(t("page.noSession"));
      return;
    }
    setStatus("running");
    setError("");

    try {
      await startReview(sessionId, agentConfig, venue);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t("errors.startFailed");
      setStatus("error");
      setError(msg);
      message.error(msg);
      return;
    }

    connectAndListen(sessionId);
  };

  const handlePhase2Start = () => {
    if (!sessionId) return;
    connectAndListen(sessionId);
  };

  const handleCancel = async () => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    if (sessionId) {
      try {
        await cancelReview(sessionId);
      } catch {
        /* best-effort */
      }
    }
    setStatus("error");
    setError(t("errors.cancelledByUser"));
  };

  const handleReset = () => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    reset();
  };

  const step = currentStep(status, sessionId);
  const isRunning = status === "running";
  const isComplete = status === "complete";
  const isWaitingEdit = status === "waiting_for_edit";
  const canStart = !!sessionId && !isRunning && !isWaitingEdit;

  const steps = [
    { title: t("page.steps.upload") },
    { title: t("page.steps.configure") },
    { title: t("page.steps.review") },
    { title: t("page.steps.editResponse") },
    { title: t("page.steps.results") },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 16px" }}>
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        {/* Header */}
        <Card
          style={{
            background:
              "linear-gradient(135deg, #eff6ff 0%, #dbeafe 60%, #e0f2fe 100%)",
            borderColor: "#bfdbfe",
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
              <Title level={2} style={{ marginBottom: 4, color: "#1e40af" }}>
                <ExperimentOutlined style={{ marginRight: 8 }} />
                {t("page.title")}
              </Title>
              <Text style={{ fontSize: 14, color: "#3b82f6" }}>
                {t("page.subtitle")}
              </Text>
            </div>
            <LanguageSwitcher />
          </div>
        </Card>

        <Steps current={step} items={steps} size="small" />

        {/* Upload + Venue + Config */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={10}>
            <Space direction="vertical" style={{ width: "100%" }} size={12}>
              <Card size="small" title={t("upload.title")}>
                <PdfUpload />
                {sessionId && (
                  <Text
                    type="success"
                    style={{ fontSize: 12, marginTop: 8, display: "block" }}
                  >
                    <CheckCircleFilled />{" "}
                    {t("page.sessionId", { id: sessionId.slice(0, 8) })}
                  </Text>
                )}
              </Card>
              <VenueSelect />
            </Space>
          </Col>
          <Col xs={24} md={14}>
            <AgentConfig />
          </Col>
        </Row>

        {/* Action Buttons */}
        <div style={{ textAlign: "center" }}>
          <Space>
            {!isWaitingEdit && (
              <Button
                type="primary"
                size="large"
                onClick={handleStart}
                loading={isRunning}
                disabled={!canStart}
                style={{ minWidth: 160 }}
              >
                {isRunning
                  ? t("page.startingButton")
                  : isComplete
                    ? t("page.restartButton")
                    : t("page.startButton")}
              </Button>
            )}

            {isRunning && (
              <Popconfirm
                title={t("page.cancelConfirmTitle")}
                description={t("page.cancelConfirmDesc")}
                onConfirm={handleCancel}
                okText={t("page.cancelConfirmOk")}
                cancelText={t("page.cancelConfirmCancel")}
                okButtonProps={{ danger: true }}
              >
                <Button size="large" icon={<StopOutlined />} danger>
                  {t("page.cancelButton")}
                </Button>
              </Popconfirm>
            )}

            {(status === "error" || isComplete) && (
              <Button size="large" onClick={handleReset}>
                {t("page.resetButton")}
              </Button>
            )}

            {isComplete && sessionId && (
              <Button
                size="large"
                icon={<DownloadOutlined />}
                onClick={() => downloadZip(sessionId)}
              >
                {t("results.downloadZipBtn")}
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

        {/* Author Response Editor (Phase 1 → Phase 2 transition) */}
        {isWaitingEdit && (
          <AuthorResponseEditor onSubmitted={handlePhase2Start} />
        )}

        <Divider style={{ margin: "8px 0" }} />

        <Row gutter={16}>
          <Col xs={24} md={10}>
            <ProgressPanel />
          </Col>
          <Col xs={24} md={14}>
            <ReviewResults />
          </Col>
        </Row>
      </Space>
    </div>
  );
}
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

        <Row gutter={16}>
          <Col xs={24} md={10}>
            <ProgressPanel />
          </Col>
          <Col xs={24} md={14}>
            <ReviewResults />
          </Col>
        </Row>
      </Space>
    </div>
  );
}
