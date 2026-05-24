import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langfuse import observe
from langfuse.langchain import CallbackHandler
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL

PROMPT_PATH: str = str(Path(__file__).parent.parent / "prompts" / "contextualization_agent.txt")


def _load_prompt() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read().strip()


def _get_llm() -> ChatOpenAI:
    kwargs: dict = {
        "model": "gpt-4o",
        "api_key": OPENAI_API_KEY,
        "max_tokens": 4096,
        "model_kwargs": {"response_format": {"type": "json_object"}},
    }
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    return ChatOpenAI(**kwargs)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
def _invoke_llm(
    llm: ChatOpenAI,
    messages: list,
) -> tuple[str, int]:
    langfuse_handler = CallbackHandler()
    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
    tokens = 0
    if response.usage_metadata:
        tokens = response.usage_metadata.get("total_tokens", 0)
    return response.content.strip(), tokens


@observe(name="contextualization-agent")
def run(
    original_text: str,
    amendment_text: str,
) -> tuple[str, int]:
    """
    Mapea secciones y correspondencias entre original y enmienda.
    NO detecta cambios.

    Returns:
        Tupla (context_map_json, tokens_usados).
    """
    system_prompt = _load_prompt()
    llm = _get_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"TEXTO ORIGINAL:\n{original_text}\n\nTEXTO ENMIENDA:\n{amendment_text}"
        ),
    ]

    try:
        raw_content, tokens = _invoke_llm(llm, messages)
    except Exception as e:
        raise RuntimeError(f"Error en ContextualizationAgent: {e}") from e

    try:
        json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"ContextualizationAgent no devolvió JSON válido: {e}") from e

    return raw_content, tokens
