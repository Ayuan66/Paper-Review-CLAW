import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { Card, Empty, Tag, Timeline, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useReviewStore } from '../store/reviewStore';
import type { ProgressEvent } from '../types';

const { Text } = Typography;

function typeIcon(type: ProgressEvent['type']) {
  if (type === 'complete') return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
  if (type === 'error') return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
  return <LoadingOutlined style={{ color: '#1677ff' }} />;
}

function EventCard({ event }: { event: ProgressEvent }) {
  const { t } = useTranslation();
  const label = t(`progress.agents.${event.agent}`, { defaultValue: event.agent });
  const phaseLabel = t(`progress.phases.${event.phase}`, { defaultValue: event.phase });
  const color = event.type === 'error' ? 'red' : event.type === 'complete' ? 'green' : 'blue';

  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ marginBottom: 2 }}>
        <Tag color={color}>{label}</Tag>
        <Tag color="default">{phaseLabel}</Tag>
        <Text type="secondary" style={{ fontSize: 11 }}>
          {new Date(event.timestamp).toLocaleTimeString()}
        </Text>
      </div>
      {event.preview && (
        <Text
          type={event.type === 'error' ? 'danger' : 'secondary'}
          style={{ fontSize: 12, display: 'block', marginTop: 2 }}
        >
          {event.preview}{event.type === 'complete' ? '…' : ''}
        </Text>
      )}
    </div>
  );
}

export default function ProgressPanel() {
  const { t } = useTranslation();
  const { progressEvents, status } = useReviewStore();

  if (progressEvents.length === 0) {
    return (
      <Card size="small" title={t('progress.title')}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={status === 'idle' ? t('progress.waitUpload') : t('progress.waitStart')}
        />
      </Card>
    );
  }

  const items = progressEvents.map((event, idx) => ({
    key: String(idx),
    dot: typeIcon(event.type),
    children: <EventCard event={event} />,
  }));

  return (
    <Card
      size="small"
      title={t('progress.titleCount', { count: progressEvents.length })}
      style={{ maxHeight: 520, overflowY: 'auto' }}
    >
      <Timeline items={items} />
    </Card>
  );
}
