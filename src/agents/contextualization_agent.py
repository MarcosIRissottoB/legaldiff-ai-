from pathlib import Path

from langfuse.openai import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL

PROMPT_PATH: str = str(
    Path(__file__).parent.parent / "prompts" / "contextualization_agent.txt"
)


def _load_prompt() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read().strip()


def _get_client() -> openai.OpenAI:
    kwargs: dict[str, str] = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    return openai.OpenAI(**kwargs)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
def _call_llm(
    client: openai.OpenAI,
    system_prompt: str,
    user_content: str,
) -> tuple[str, int]:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=4096,
    )
    text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    return text.strip(), tokens


def run(
    original_text: str,
    amendment_text: str,
    langfuse_parent: object | None = None,
) -> tuple[str, int]:
    """
    Mapea secciones y correspondencias entre original y enmienda.
    NO detecta cambios.

    Returns:
        Tupla (context_map_json, tokens_usados).
    """
    system_prompt = _load_prompt()
    client = _get_client()

    user_content = (
        f"TEXTO ORIGINAL:\n{original_text}\n\n"
        f"TEXTO ENMIENDA:\n{amendment_text}"
    )

    try:
        return _call_llm(client, system_prompt, user_content)
    except Exception as e:
        raise RuntimeError(f"Error en ContextualizationAgent: {e}") from e
