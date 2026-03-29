import { DownloadOutlined } from '@ant-design/icons';
import { Button, Card, Empty, Tabs, Tag, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { downloadResult } from '../api/client';
import { useReviewStore } from '../store/reviewStore';
import MarkdownViewer from './MarkdownViewer';

const { Text } = Typography;

export default function ReviewResults() {
  const { t } = useTranslation();
  const { results, sessionId } = useReviewStore();

  if (!results) {
    return (
      <Card size="small" title={t('results.title')}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('results.noResults')} />
      </Card>
    );
  }

  const reviewItems = (results.reviews || []).map((r) => ({
    key: r.agent_name,
    label: t(`progress.agents.${r.agent_name}`, { defaultValue: r.agent_name }),
    children: (
      <div>
        <Tag color="geekblue" style={{ marginBottom: 8 }}>{r.model}</Tag>
        <MarkdownViewer content={r.content} />
      </div>
    ),
  }));

  const discussionItems = (results.author_discussions || []).map((d, idx) => ({
    key: String(idx),
    label: (
      <Tag color={d.author === 'author_a' ? 'blue' : 'green'}>
        {t(`progress.agents.${d.author}`)} · {t('results.roundLabel', { round: d.round })}
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
      key: 'editor',
      label: t('results.tabs.editorSummary'),
      children: <MarkdownViewer content={results.editor_summary} />,
    },
    {
      key: 'discussions',
      label: t('results.tabs.discussions', { count: results.author_discussions?.length ?? 0 }),
      children:
        results.author_discussions?.length > 0 ? (
          <Tabs tabPosition="left" size="small" items={discussionItems} />
        ) : (
          <Empty description={t('results.noDiscussions')} />
        ),
    },
    {
      key: 'final',
      label: t('results.tabs.finalReport'),
      children: (
        <div>
          {sessionId && results.final_markdown && (
            <Button
              icon={<DownloadOutlined />}
              onClick={() => downloadResult(sessionId)}
              style={{ marginBottom: 16 }}
            >
              {t('results.downloadBtn')}
            </Button>
          )}
          <MarkdownViewer content={results.final_markdown} />
        </div>
      ),
    },
  ];

  return (
    <Card
      size="small"
      title={
        <span>
          {t('results.title')}
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            {t('results.paperLabel', { filename: results.pdf_filename })}
          </Text>
        </span>
      }
    >
      <Tabs items={tabItems} />
    </Card>
  );
}
