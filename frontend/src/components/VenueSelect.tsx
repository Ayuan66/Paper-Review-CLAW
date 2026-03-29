import { BookOutlined, TrophyOutlined } from '@ant-design/icons';
import { Card, Select, Space, Tag, Tooltip, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getVenues } from '../api/client';
import { useReviewStore } from '../store/reviewStore';
import type { VenueOption } from '../types';

const { Text, Title } = Typography;

export default function VenueSelect() {
  const { t } = useTranslation();
  const { venue, setVenue, status } = useReviewStore();
  const [venues, setVenues] = useState<VenueOption[]>([]);
  const disabled = status === 'running';

  useEffect(() => {
    getVenues().then(setVenues).catch(() => {});
  }, []);

  const options = [
    { value: '', label: <Text type="secondary">{t('venue.generic')}</Text> },
    ...venues.map((v) => ({
      value: v.id,
      label: (
        <Space>
          {v.type === 'conference'
            ? <TrophyOutlined style={{ color: '#1677ff' }} />
            : <BookOutlined style={{ color: '#52c41a' }} />}
          <Text strong>{v.id}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {v.name.replace(/^[A-Za-z]+\s-\s/, '')}
          </Text>
        </Space>
      ),
    })),
  ];

  const selected = venues.find((v) => v.id === venue);

  return (
    <Card size="small" title={<Title level={5} style={{ margin: 0 }}>{t('venue.title')}</Title>}>
      <Tooltip title={t('venue.hint')}>
        <Select
          style={{ width: '100%' }}
          disabled={disabled}
          value={venue}
          onChange={setVenue}
          options={options}
          placeholder={t('venue.placeholder')}
          optionLabelProp="label"
        />
      </Tooltip>
      {selected && (
        <div style={{ marginTop: 8 }}>
          <Tag color={selected.type === 'conference' ? 'blue' : 'green'}>
            {t(`venue.${selected.type}`)}
          </Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('venue.selectedHint', { id: selected.id })}
          </Text>
        </div>
      )}
      {!venue && (
        <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
          {t('venue.noVenueHint')}
        </Text>
      )}
    </Card>
  );
}
