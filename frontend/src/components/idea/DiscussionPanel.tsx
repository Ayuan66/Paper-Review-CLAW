import {
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  MessageOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { Card, Divider, Empty, Space, Tag, Typography } from "antd";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useIdeaStore } from "../../store/ideaStore";
import type { IdeaProgressEvent } from "../../types";

const { Text } = Typography;

const AGENT_COLORS: Record<
  string,
  { bg: string; border: string; tag: string }
> = {
  innovation_expert: { bg: "#e6f4ff", border: "#91caff", tag: "blue" },
  feasibility_analyst: { bg: "#f6ffed", border: "#b7eb8f", tag: "green" },
  methodology_expert: { bg: "#f9f0ff", border: "#d3adf7", tag: "purple" },
  summarizer: { bg: "#fffbe6", border: "#ffe58f", tag: "gold" },
  system: { bg: "#f5f5f5", border: "#d9d9d9", tag: "default" },
};

function StatusIcon({ event }: { event: IdeaProgressEvent }) {
  if (event.type === "error")
    return <CloseCircleOutlined style={{ color: "#ff4d4f" }} />;
  if (event.type === "complete" && event.agent !== "system")
    return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
  if (event.type === "question")
    return <MessageOutlined style={{ color: "#fa8c16" }} />;
  if (event.type === "start")
    return <LoadingOutlined style={{ color: "#1677ff" }} />;
  return null;
}

/** System-level event: round start/complete, info, error */
function SystemBanner({ event }: { event: IdeaProgressEvent }) {
  const { t } = useTranslation();

  if (event.type === "round_start") {
    return (
      <Divider style={{ margin: "12px 0", borderColor: "#1677ff" }}>
        <SyncOutlined style={{ marginRight: 6, color: "#1677ff" }} />
        <Text strong style={{ color: "#1677ff" }}>
          {t("idea.discussion.roundStart", { round: event.round })}
        </Text>
      </Divider>
    );
  }
  if (event.type === "round_complete") {
    return (
      <Divider style={{ margin: "12px 0", borderColor: "#13c2c2" }}>
        <CheckCircleOutlined style={{ marginRight: 6, color: "#13c2c2" }} />
        <Text strong style={{ color: "#13c2c2" }}>
          {t("idea.discussion.roundComplete", { round: event.round })}
        </Text>
      </Divider>
    );
  }
  if (event.type === "info") {
    return (
      <div style={{ textAlign: "center", margin: "6px 0" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />
          {event.content}
        </Text>
      </div>
    );
  }
  if (event.type === "error") {
    return (
      <div style={{ textAlign: "center", margin: "6px 0" }}>
        <Text type="danger" style={{ fontSize: 12 }}>
          <CloseCircleOutlined style={{ marginRight: 4 }} />
          {event.content}
        </Text>
      </div>
    );
  }
  return null;
}

/** Chat bubble for expert / summarizer messages */
function ChatBubble({ event }: { event: IdeaProgressEvent }) {
  const { t } = useTranslation();
  const agentLabel = t(`idea.agents.${event.agent}`, {
    defaultValue: event.agent,
  });
  const colors = AGENT_COLORS[event.agent] ?? AGENT_COLORS.system;
  const isSummarizer = event.agent === "summarizer";

  return (
    <div style={{ marginBottom: 12 }}>
      {/* Header: agent tag + status + time */}
      <div
        style={{
          marginBottom: 4,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <Tag color={colors.tag} style={{ marginRight: 0 }}>
          {agentLabel}
        </Tag>
        <StatusIcon event={event} />
        {event.type === "question" && (
          <Tag color="orange">{t("idea.discussion.tagQuestion")}</Tag>
        )}
        {event.type === "start" && (
          <Tag color="processing">{t("idea.discussion.tagStart")}</Tag>
        )}
        <Text type="secondary" style={{ fontSize: 11, marginLeft: "auto" }}>
          {event.timestamp
            ? new Date(event.timestamp).toLocaleTimeString()
            : ""}
        </Text>
      </div>

      {/* Bubble body */}
      {event.content && (
        <div
          style={{
            background: isSummarizer ? "#fffbe6" : colors.bg,
            border: `1px solid ${isSummarizer ? "#ffe58f" : colors.border}`,
            borderRadius: 10,
            padding: "10px 14px",
            ...(isSummarizer && { borderLeft: "4px solid #faad14" }),
          }}
        >
          {event.type === "start" ? (
            <Text type="secondary" style={{ fontSize: 13 }}>
              {event.content}
            </Text>
          ) : (
            <div
              className="markdown-body"
              style={{ fontSize: 13, lineHeight: 1.7 }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {event.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function DiscussionPanel() {
  const { t } = useTranslation();
  const { progressEvents, status } = useIdeaStore();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [progressEvents.length]);

  const visible = progressEvents.filter(
    (e) => e.type !== "answer_received" && e.type !== "revision_received",
  );

  if (visible.length === 0) {
    return (
      <Card size="small" title={t("idea.discussion.title")}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t("idea.discussion.empty")}
        />
      </Card>
    );
  }

  const titleContent = (
    <Space size="small">
      <BulbOutlined />
      {t("idea.discussion.titleCount", { count: visible.length })}
      {(status === "running" || status === "waiting_for_input") && (
        <Tag color="processing">{t("idea.discussion.running")}</Tag>
      )}
      {status === "waiting_for_revision" && (
        <Tag color="warning">{t("idea.discussion.waitingRevision")}</Tag>
      )}
    </Space>
  );

  return (
    <Card size="small" title={titleContent}>
      <div
        ref={containerRef}
        style={{ maxHeight: 600, overflowY: "auto", padding: "4px 0" }}
      >
        {visible.map((event, idx) => {
          const isSystem =
            event.agent === "system" ||
            event.type === "round_start" ||
            event.type === "round_complete" ||
            event.type === "info" ||
            (event.type === "error" && event.agent === "system");

          if (isSystem) {
            return <SystemBanner key={idx} event={event} />;
          }
          return <ChatBubble key={idx} event={event} />;
        })}
      </div>
    </Card>
  );
}
