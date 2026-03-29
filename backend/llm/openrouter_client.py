import time
import httpx
from config import OPENROUTER_API_KEY
from llm.pdf_extractor import model_supports_vision


class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    HEADERS_BASE = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://paper-review-claw.local",
        "X-Title": "Paper Review CLAW",
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        self._client = httpx.Client(timeout=180.0)

    def _headers(self) -> dict:
        return {**self.HEADERS_BASE, "Authorization": f"Bearer {self.api_key}"}

    def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 2,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                resp = self._client.post(self.BASE_URL, json=payload, headers=self._headers())
                if resp.status_code >= 400:
                    try:
                        err_body = resp.json()
                        err_msg = err_body.get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    raise RuntimeError(
                        f"HTTP {resp.status_code} (model={model}): {err_msg}"
                    )
                data = resp.json()
                if "choices" not in data:
                    raise RuntimeError(
                        f"OpenRouter响应缺少 choices 字段 (model={model}): {data}"
                    )
                return data["choices"][0]["message"]["content"]
            except RuntimeError:
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"网络错误（模型 {model}）：{last_error}")

    def chat_with_paper(
        self,
        model: str,
        pdf_text: str,
        pdf_filename: str,
        page_images: list[str],
        user_prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send paper to LLM for review.
        - Vision models: receive all page images + extracted text
        - Text-only models: receive extracted text only
        """
        if model_supports_vision(model) and page_images:
            return self._chat_multimodal(
                model, pdf_text, pdf_filename, page_images,
                user_prompt, system_prompt, temperature, max_tokens,
            )
        else:
            return self._chat_text_only(
                model, pdf_text, pdf_filename,
                user_prompt, system_prompt, temperature, max_tokens,
            )

    def _chat_multimodal(
        self,
        model: str,
        pdf_text: str,
        pdf_filename: str,
        page_images: list[str],
        user_prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Send page images + text. Supported by GPT-4o, Claude, Gemini, Kimi."""
        content: list[dict] = [
            {"type": "text", "text": f"{user_prompt}\n\n**论文文件名**：{pdf_filename}\n\n以下是论文各页面的图像："},
        ]
        for i, img_b64 in enumerate(page_images, 1):
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            })
        # Also include extracted text for reference (helps with copy-paste accuracy)
        if pdf_text:
            content.append({
                "type": "text",
                "text": f"\n\n---\n以下是提取的论文文字内容（供参考）：\n\n{pdf_text}",
            })
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]
        return self.chat(model, messages, temperature, max_tokens)

    def _chat_text_only(
        self,
        model: str,
        pdf_text: str,
        pdf_filename: str,
        user_prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Text-only fallback for models without vision support."""
        combined = (
            f"{user_prompt}\n\n"
            f"**论文文件名**：{pdf_filename}\n\n"
            f"**论文全文**：\n\n{pdf_text}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": combined},
        ]
        return self.chat(model, messages, temperature, max_tokens)

    def chat_text(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(model, messages, temperature, max_tokens)
