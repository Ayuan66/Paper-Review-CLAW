import {
  DownloadOutlined,
  EditOutlined,
  FileTextOutlined,
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

  // Round 1 reviewer tabs
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

  // Round 2 reviewer tabs
  const reviewItems2 = (results.reviews_round2 || []).map((r) => ({
    key: `r2_${r.agent_name}`,
    label: (
      <span>
        <UserOutlined style={{ marginRight: 4 }} />
        {t(`progress.agents.${r.agent_name}`, { defaultValue: r.agent_name })}
      </span>
    ),
    children: (
      <div>
        <Tag color="purple" style={{ marginBottom: 8 }}>
          {r.model}
        </Tag>
        <MarkdownViewer content={r.content} />
      </div>
    ),
  }));

  const tabItems = [
    // Round 1 reviews
    ...reviewItems,
    // Round 1 editor summary
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
    // Author response
    ...(results.author_response
      ? [
          {
            key: "author_response",
            label: (
              <span>
                <UserOutlined style={{ marginRight: 4 }} />
                {t("results.tabs.authorResponse")}
              </span>
            ),
            children: (
              <MarkdownViewer
                content={
                  results.author_response_edited || results.author_response
                }
              />
            ),
          },
        ]
      : []),
    // Round 2 reviews
    ...(reviewItems2.length > 0
      ? [
          {
            key: "reviews_round2",
            label: (
              <span>
                <UserOutlined style={{ marginRight: 4 }} />
                {t("results.tabs.reviewsRound2")}
              </span>
            ),
            children: (
              <Tabs tabPosition="left" size="small" items={reviewItems2} />
            ),
          },
        ]
      : []),
    // Round 2 editor summary
    ...(results.editor_summary_round2
      ? [
          {
            key: "editor_round2",
            label: (
              <span>
                <EditOutlined style={{ marginRight: 4 }} />
                {t("results.tabs.editorSummaryRound2")}
              </span>
            ),
            children: (
              <MarkdownViewer content={results.editor_summary_round2} />
            ),
          },
        ]
      : []),
    // Final report
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
