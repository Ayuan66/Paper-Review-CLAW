import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
SESSIONS_DIR = os.path.join(STORAGE_DIR, "sessions")

DEFAULT_MODELS = {
    "reviewer_1": "moonshotai/kimi-k2",
    "reviewer_2": "google/gemini-2.0-flash-001",
    "reviewer_3": "qwen/qwen3-235b-a22b",
    "editor": "deepseek/deepseek-chat",
    "author": "deepseek/deepseek-chat",
}

# 无地区限制的可用模型列表
AVAILABLE_MODELS = [
    # DeepSeek
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3"},
    {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1 (推理)"},
    {"id": "deepseek/deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 Distill 70B"},
    # Google Gemini（全球可用）
    {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    {"id": "google/gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro"},
    # Moonshot Kimi
    {"id": "moonshotai/kimi-k2.5", "name": "Kimi K2"},
    # Qwen（阿里云）
    {"id": "qwen/qwen3-235b-a22b", "name": "Qwen3 235B"},
    {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen2.5 72B"},
    # Meta Llama（全球可用）
    {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
    {"id": "meta-llama/llama-4-maverick", "name": "Llama 4 Maverick"},
    # Mistral
    {"id": "mistralai/mistral-large", "name": "Mistral Large"},
    # 如果你有科学上网，以下模型也可使用
    {"id": "openai/gpt-4o", "name": "GPT-4o"},
    {"id": "openai/gpt-5.2", "name": "GPT-5.2"},
    {"id": "anthropic/claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
    {"id": "anthropic/claude-sonnet-4.6", "name": "Claude Sonnet 4.6"},
]

AGENT_ROLES = {
    "reviewer_1": "审稿人 1",
    "reviewer_2": "审稿人 2",
    "reviewer_3": "审稿人 3",
    "editor": "编辑",
    "author": "作者",
}

VENUES: dict[str, dict] = {
    "ICSE": {
        "name": "ICSE - International Conference on Software Engineering",
        "type": "conference",
        "urls": [
            "https://conf.researchr.org/track/icse-2026/icse-2026-research-track",
            "https://www.icse-conferences.org/",
        ],
    },
    "FSE": {
        "name": "FSE - ACM International Conference on the Foundations of Software Engineering",
        "type": "conference",
        "urls": [
            "https://conf.researchr.org/home/fse-2025",
            "https://www.sigsoft.org/events/fse.html",
        ],
    },
    "ASE": {
        "name": "ASE - IEEE/ACM International Conference on Automated Software Engineering",
        "type": "conference",
        "urls": [
            "https://conf.researchr.org/home/ase-2025",
        ],
    },
    "TSE": {
        "name": "TSE - IEEE Transactions on Software Engineering",
        "type": "journal",
        "urls": [
            "https://www.computer.org/csdl/journal/ts/about",
            "https://www.computer.org/csdl/journal/ts/write-for-us/15149",
        ],
    },
    "TOSEM": {
        "name": "TOSEM - ACM Transactions on Software Engineering and Methodology",
        "type": "journal",
        "urls": [
            "https://dl.acm.org/journal/tosem/author-guidelines",
            "https://dl.acm.org/journal/tosem",
        ],
    },
    "MoDELS": {
        "name": "MoDELS - ACM/IEEE International Conference on Model Driven Engineering Languages and Systems",
        "type": "conference",
        "urls": [
            "https://conf.researchr.org/home/models-2025",
            "https://modelsconf.org/",
        ],
    },
    "SoSym": {
        "name": "SoSym - Software and Systems Modeling (Springer)",
        "type": "journal",
        "urls": [
            "https://www.springer.com/journal/10270/submission-guidelines",
            "https://link.springer.com/journal/10270",
        ],
    },
    "IST": {
        "name": "IST - Information and Software Technology (Elsevier)",
        "type": "journal",
        "urls": [
            "https://www.sciencedirect.com/journal/information-and-software-technology/about/aims-and-scope",
            "https://www.sciencedirect.com/journal/information-and-software-technology/about/guide-for-authors",
        ],
    },
}
