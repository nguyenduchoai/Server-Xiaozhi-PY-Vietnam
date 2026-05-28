from app.ai.providers.llm.openai.openai import LLMProvider as OpenAICompatibleLLM


class LLMProvider(OpenAICompatibleLLM):
    """Google Gemini via Gemini's OpenAI-compatible chat endpoint."""

    def __init__(self, config):
        gemini_config = dict(config or {})
        gemini_config.setdefault(
            "base_url",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        super().__init__(gemini_config)
