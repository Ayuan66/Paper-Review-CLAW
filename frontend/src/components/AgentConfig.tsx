import { Card, Col, Form, InputNumber, Row, Select, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getModels } from '../api/client';
import { useReviewStore } from '../store/reviewStore';
import type { ModelOption } from '../types';

const { Title } = Typography;

const ROLE_KEYS = ['reviewer_1', 'reviewer_2', 'reviewer_3', 'editor', 'author_a', 'author_b'];

export default function AgentConfig() {
  const { t } = useTranslation();
  const { agentConfig, updateAgentRole, maxIterations, setMaxIterations, status } =
    useReviewStore();
  const [models, setModels] = useState<ModelOption[]>([]);
  const disabled = status === 'running';

  useEffect(() => {
    getModels().then((res) => setModels(res.models)).catch(() => {});
  }, []);

  const modelOptions = models.map((m) => ({ value: m.id, label: m.name }));

  return (
    <Card size="small" title={<Title level={5} style={{ margin: 0 }}>{t('agentConfig.title')}</Title>}>
      <Form layout="vertical" size="small">
        <Row gutter={[12, 0]}>
          {ROLE_KEYS.map((role) => (
            <Col span={12} key={role}>
              <Form.Item label={t(`progress.agents.${role}`)} style={{ marginBottom: 8 }}>
                <Select
                  disabled={disabled}
                  value={agentConfig[role]}
                  onChange={(val) => updateAgentRole(role, val)}
                  options={modelOptions}
                  showSearch
                  placeholder={t('agentConfig.selectModel')}
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
            </Col>
          ))}
          <Col span={12}>
            <Form.Item label={t('agentConfig.maxIterations')} style={{ marginBottom: 8 }}>
              <InputNumber
                min={1}
                max={10}
                value={maxIterations}
                onChange={(v) => v && setMaxIterations(v)}
                disabled={disabled}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Card>
  );
}
