import {
  DownloadOutlined,
  EditOutlined,
  FileTextOutlined,
  MessageOutlined,
  UserOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Empty,
  Space,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useTranslation } from "react-i18next";
import { downloadResult, downloadZip } from "../api/client";
import { useReviewStore } from "../store/reviewStore";
import MarkdownViewer from "./MarkdownViewer";

const { Text } = Typography;

export default function ReviewResults() {
  const { t } = useTranslation();
  const { results, sessionId } = useReviewStore();

  if (!results) {
    return (
      <Card size="small" title={t("results.title")}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t("results.noResults")}
        />
      </Card>
    );
  }

  const reviewItems = (results.reviews || []).map((r) => ({
    key: r.agent_name,
    label: (
      <span>
        <UserOutlined style={{ marginRight: 4 }} />
        {t(`progress.agents.${r.agent_name}`, { defaultValue: r.agent_name })}
      </span>
    ),
    children: (
      <div>
        <Tag color="geekblue" style={{ marginBottom: 8 }}>
          {r.model}
        </Tag>
        <MarkdownViewer content={r.content} />
      </div>
    ),
  }));

  const discussionItems = (results.author_discussions || []).map((d, idx) => ({
    key: String(idx),
    label: (
      <Tag color={d.author === "author_a" ? "blue" : "green"}>
        {t(`progress.agents.${d.author}`)} ·{" "}
        {t("results.roundLabel", { round: d.round })}
      </Tag>
    ),
    children: (
      <div>
        <Tag style={{ marginBottom: 8 }}>{d.model}</Tag>
        <MarkdownViewer content={d.content} />
      </div>
    ),
  }));

  const tabItems = [
    ...reviewItems,
    {
      key: "editor",
      label: (
        <span>
          <EditOutlined style={{ marginRight: 4 }} />
          {t("results.tabs.editorSummary")}
        </span>
      ),
      children: <MarkdownViewer content={results.editor_summary} />,
    },
    {
      key: "discussions",
      label: (
        <span>
          <MessageOutlined style={{ marginRight: 4 }} />
          {t("results.tabs.discussions", {
            count: results.author_discussions?.length ?? 0,
          })}
        </span>
      ),
      children:
        results.author_discussions?.length > 0 ? (
          <Tabs tabPosition="left" size="small" items={discussionItems} />
        ) : (
          <Empty description={t("results.noDiscussions")} />
        ),
    },
    {
      key: "final",
      label: (
        <span>
          <FileTextOutlined style={{ marginRight: 4 }} />
          {t("results.tabs.finalReport")}
        </span>
      ),
      children: <MarkdownViewer content={results.final_markdown} />,
    },
  ];

  const downloadExtra =
    sessionId && results.final_markdown ? (
      <Space size="small">
        <Tooltip title={t("results.downloadBtn")}>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => downloadResult(sessionId)}
          >
            Markdown
          </Button>
        </Tooltip>
        <Button
          size="small"
          type="primary"
          icon={<DownloadOutlined />}
          onClick={() => downloadZip(sessionId)}
        >
          {t("results.downloadZipBtn")}
        </Button>
      </Space>
    ) : null;

  return (
    <Card
      size="small"
      title={
        <span>
          {t("results.title")}
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            {t("results.paperLabel", { filename: results.pdf_filename })}
          </Text>
        </span>
      }
      extra={downloadExtra}
    >
      <Tabs items={tabItems} />
    </Card>
  );
}
