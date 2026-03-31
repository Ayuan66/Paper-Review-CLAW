import {
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  MessageOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { Card, Empty, Space, Tag, Timeline, Typography } from "antd";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useIdeaStore } from "../../store/ideaStore";
import type { IdeaProgressEvent } from "../../types";

const { Text } = Typography;

const AGENT_TAG_COLORS: Record<string, string> = {
  innovation_expert: "blue",
  feasibility_analyst: "green",
  methodology_expert: "purple",
  summarizer: "gold",
  system: "default",
};

function eventDot(event: IdeaProgressEvent) {
  if (event.type === "error")
    return <CloseCircleOutlined style={{ color: "#ff4d4f" }} />;
  if (event.type === "complete")
    return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
  if (event.type === "question")
    return <MessageOutlined style={{ color: "#fa8c16" }} />;
  if (event.type === "round_start")
    return <SyncOutlined style={{ color: "#1677ff" }} />;
  if (event.type === "round_complete")
    return <CheckCircleOutlined style={{ color: "#13c2c2" }} />;
  if (event.type === "info")
    return <InfoCircleOutlined style={{ color: "#8c8c8c" }} />;
  if (event.type === "start")
    return <LoadingOutlined style={{ color: "#1677ff" }} />;
  return <BulbOutlined style={{ color: "#722ed1" }} />;
}

function DiscussionEventCard({ event }: { event: IdeaProgressEvent }) {
  const { t } = useTranslation();
  const agentLabel = t(`idea.agents.${event.agent}`, {
    defaultValue: event.agent,
  });
  const tagColor = AGENT_TAG_COLORS[event.agent] ?? "default";

  if (event.type === "round_start") {
    return (
      <div style={{ marginBottom: 4 }}>
        <Text strong style={{ color: "#1677ff" }}>
          {t("idea.discussion.roundStart", { round: event.round })}
        </Text>
      </div>
    );
  }

  if (event.type === "round_complete") {
    return (
      <div style={{ marginBottom: 4 }}>
        <Text strong style={{ color: "#13c2c2" }}>
          {t("idea.discussion.roundComplete", { round: event.round })}
        </Text>
      </div>
    );
  }

  if (event.type === "info") {
    return (
      <div style={{ marginBottom: 4 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {event.content}
        </Text>
      </div>
    );
  }

  if (event.type === "error") {
    return (
      <div style={{ marginBottom: 4 }}>
        <Text type="danger" style={{ fontSize: 12 }}>
          {event.content}
        </Text>
      </div>
    );
  }

  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ marginBottom: 2 }}>
        <Tag color={tagColor}>{agentLabel}</Tag>
        {event.type === "question" && (
          <Tag color="orange">{t("idea.discussion.tagQuestion")}</Tag>
        )}
        {event.type === "start" && (
          <Tag color="processing">{t("idea.discussion.tagStart")}</Tag>
        )}
        <Text type="secondary" style={{ fontSize: 11 }}>
          {event.timestamp
            ? new Date(event.timestamp).toLocaleTimeString()
            : ""}
        </Text>
      </div>
      {event.content && (
        <Text
          type={event.type === "question" ? undefined : "secondary"}
          style={{ fontSize: 12, display: "block", marginTop: 2 }}
        >
          {(event.content || "").slice(0, 200)}
          {(event.content || "").length > 200 ? "…" : ""}
        </Text>
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

  const items = visible.map((event, idx) => ({
    key: String(idx),
    dot: eventDot(event),
    children: <DiscussionEventCard event={event} />,
  }));

  const titleContent = (
    <Space size="small">
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
      <div ref={containerRef} style={{ maxHeight: 520, overflowY: "auto" }}>
        <Timeline items={items} />
      </div>
    </Card>
  );
}
