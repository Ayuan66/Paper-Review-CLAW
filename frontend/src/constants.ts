export const DEFAULT_MODELS: Record<string, string> = {
  reviewer_1: "moonshotai/kimi-k2",
  reviewer_2: "google/gemini-2.0-flash-001",
  reviewer_3: "qwen/qwen3-235b-a22b",
  editor: "deepseek/deepseek-chat",
  author: "deepseek/deepseek-chat",
};

export const AGENT_LABELS: Record<string, string> = {
  prepare: "获取Venue要求",
  reviewer_1: "审稿人 1",
  reviewer_2: "审稿人 2",
  reviewer_3: "审稿人 3",
  editor: "编辑",
  author: "作者",
  finalize: "报告生成",
  system: "系统",
};

export const PHASE_LABELS: Record<string, string> = {
  preparing: "准备阶段",
  reviewing: "审稿阶段",
  editing: "编辑汇总",
  author_responding: "作者回应",
  finalizing: "生成报告",
  complete: "已完成",
  error: "出错",
};
