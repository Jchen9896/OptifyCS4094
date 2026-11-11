"""Thin Gemini chat wrapper with function-calling support."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

from app.chat.tools import tool_declarations
from app.core.config import Settings

SYSTEM_INSTRUCTION = """You are the Optify assistant.
Explain Optify workflows, strategies, and metrics using the retrieved knowledge and the user's account data.
Cite Learn article slugs when you rely on documentation.
Treat optimization results as historical estimates for a chosen period, never as forecasts or investment advice.
Never place trades or access brokerage credentials.
Use read tools when you need live portfolio or run details.
For rename_portfolio, delete_portfolio, or run_optimization, call the tool only when the user clearly asks; the app will ask them to confirm before it runs.
Keep answers concise and practical.
"""


class GeminiChatClient:
    """Send chat turns to Gemini with Optify tool declarations."""

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for chat.")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_chat_model
        self._tools = types.Tool(function_declarations=tool_declarations())

    def generate(
        self,
        *,
        history: list[types.Content],
        user_message: str,
        context_block: str,
    ) -> types.GenerateContentResponse:
        contents = list(history)
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=f"{context_block}\n\nUser message:\n{user_message}")],
            )
        )
        return self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[self._tools],
                temperature=0.3,
            ),
        )

    def continue_with_function_responses(
        self,
        *,
        history: list[types.Content],
        function_response_parts: list[types.Part],
        context_block: str,
    ) -> types.GenerateContentResponse:
        contents = list(history)
        contents.append(types.Content(role="user", parts=[types.Part(text=context_block)]))
        contents.append(types.Content(role="user", parts=function_response_parts))
        return self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[self._tools],
                temperature=0.3,
            ),
        )


def extract_text(response: types.GenerateContentResponse) -> str:
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    return ""


def extract_function_calls(response: types.GenerateContentResponse) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    candidates = response.candidates or []
    for candidate in candidates:
        content = candidate.content
        if content is None or not content.parts:
            continue
        for part in content.parts:
            fn = getattr(part, "function_call", None)
            if fn is None:
                continue
            args = dict(fn.args or {})
            calls.append((str(fn.name), args))
    return calls
