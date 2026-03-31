import {
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getModels } from "../../api/client";
import { useIdeaStore } from "../../store/ideaStore";
import type { ModelOption } from "../../types";

const { Title } = Typography;
const { TextArea } = Input;

const IDEA_ROLE_KEYS = [
  "innovation_expert",
  "feasibility_analyst",
  "methodology_expert",
  "summarizer",
];

export default function IdeaInput() {
  const { t } = useTranslation();
  const {
    researchQuestion,
    userContext,
    agentConfig,
    maxRounds,
    status,
    setResearchQuestion,
    setUserContext,
    updateAgentRole,
    setMaxRounds,
  } = useIdeaStore();
  const [models, setModels] = useState<ModelOption[]>([]);
  const disabled =
    status === "running" ||
    status === "waiting_for_input" ||
    status === "waiting_for_revision";

  useEffect(() => {
    getModels()
      .then((res) => setModels(res.models))
      .catch(() => {});
  }, []);

  const modelOptions = models.map((m) => ({ value: m.id, label: m.name }));

  return (
    <Card
      size="small"
      title={
        <Title level={5} style={{ margin: 0 }}>
          {t("idea.input.title")}
        </Title>
      }
    >
      <Form layout="vertical" size="small">
        <Form.Item label={t("idea.input.questionLabel")} required>
          <TextArea
            rows={3}
            disabled={disabled}
            value={researchQuestion}
            onChange={(e) => setResearchQuestion(e.target.value)}
            placeholder={t("idea.input.questionPlaceholder")}
          />
        </Form.Item>

        <Form.Item label={t("idea.input.contextLabel")}>
          <TextArea
            rows={3}
            disabled={disabled}
            value={userContext}
            onChange={(e) => setUserContext(e.target.value)}
            placeholder={t("idea.input.contextPlaceholder")}
          />
        </Form.Item>

        <Form.Item label={t("idea.input.maxRounds")}>
          <InputNumber
            min={1}
            max={5}
            disabled={disabled}
            value={maxRounds}
            onChange={(v) => setMaxRounds(v ?? 3)}
          />
        </Form.Item>
      </Form>

      <Title level={5} style={{ marginTop: 4, marginBottom: 8 }}>
        {t("idea.input.agentConfig")}
      </Title>
      <Form layout="vertical" size="small">
        <Row gutter={[12, 0]}>
          {IDEA_ROLE_KEYS.map((role) => (
            <Col span={12} key={role}>
              <Form.Item
                label={t(`idea.agents.${role}`)}
                style={{ marginBottom: 8 }}
              >
                <Select
                  disabled={disabled}
                  value={agentConfig[role]}
                  onChange={(val) => updateAgentRole(role, val)}
                  options={modelOptions}
                  showSearch
                  placeholder={t("agentConfig.selectModel")}
                  filterOption={(input, option) =>
                    (option?.label ?? "")
                      .toLowerCase()
                      .includes(input.toLowerCase())
                  }
                />
              </Form.Item>
            </Col>
          ))}
        </Row>
      </Form>
    </Card>
  );
}
