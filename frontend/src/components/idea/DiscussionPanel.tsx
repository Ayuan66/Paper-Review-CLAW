import { Badge, Card, Tag, Timeline, Typography } from "antd";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useIdeaStore } from "../../store/ideaStore";
import type { IdeaProgressEvent } from "../../types";
import MarkdownViewer from "../MarkdownViewer";

const { Text } = Typography;

const AGENT_COLORS: Record<string, string> = {
  innovation_expert: "blue",
  feasibility_analyst: "green",
  methodology_expert: "purple",
  summarizer: "gold",
  system: "default",
};

function eventColor(event: IdeaProgressEvent): string {
  if (event.type === "error") return "red";
  if (event.type === "question") return "orange";
  if (event.type === "round_start" || event.type === "round_complete")
    return "cyan";
  return AGENT_COLORS[event.agent] ?? "default";
}

export default function DiscussionPanel() {
  const { t } = useTranslation();
  const { progressEvents } = useIdeaStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [progressEvents.length]);

  if (progressEvents.length === 0) {
    return (
      <Card size="small" title={t("idea.discussion.title")}>
        <Text type="secondary">{t("idea.discussion.empty")}</Text>
      </Card>
    );
  }

  const items = progressEvents
    .filter(
      (e) => e.type !== "answer_received" && e.type !== "revision_received",
    )
    .map((event, idx) => {
      const color = eventColor(event);
      const agentLabel = t(`idea.agents.${event.agent}`, {
        defaultValue: event.agent,
      });

      let label: React.ReactNode = (
        <Text type="secondary" style={{ fontSize: 11 }}>
          {event.timestamp
            ? new Date(event.timestamp).toLocaleTimeString()
            : ""}
        </Text>
      );

      let dot: React.ReactNode;
      if (event.type === "round_start") {
        dot = <Badge color="cyan" />;
      } else if (event.type === "question") {
        dot = <Badge color="orange" />;
      }

      let children: React.ReactNode;
      if (event.type === "round_start") {
        children = (
          <Text strong style={{ color: "#0891b2" }}>
            {t("idea.discussion.roundStart", { round: event.round })}
          </Text>
        );
      } else if (event.type === "round_complete") {
        children = (
          <Text strong style={{ color: "#0891b2" }}>
            {t("idea.discussion.roundComplete", { round: event.round })}
          </Text>
        );
      } else if (event.type === "question") {
        children = (
          <div>
            <Tag color="orange">{agentLabel}</Tag>
            <Text italic>{t("idea.discussion.agentQuestion")}</Text>
            <div style={{ marginTop: 4 }}>
              <MarkdownViewer content={event.content} />
            </div>
          </div>
        );
      } else if (event.type === "complete" || event.type === "partial") {
        children = (
          <div>
            <Tag color={color}>{agentLabel}</Tag>
            <div style={{ marginTop: 4 }}>
              <MarkdownViewer content={event.content} />
            </div>
          </div>
        );
      } else if (event.type === "info" || event.type === "error") {
        children = (
          <Text type={event.type === "error" ? "danger" : "secondary"}>
            {event.content}
          </Text>
        );
      } else {
        children = (
          <div>
            <Tag color={color}>{agentLabel}</Tag>
            <Text>{event.content}</Text>
          </div>
        );
      }

      return { key: idx, label, dot, color, children };
    });

  return (
    <Card
      size="small"
      title={t("idea.discussion.titleCount", { count: progressEvents.length })}
      styles={{ body: { maxHeight: 600, overflowY: "auto" } }}
    >
      <Timeline mode="left" items={items} />
      <div ref={bottomRef} />
    </Card>
  );
}
