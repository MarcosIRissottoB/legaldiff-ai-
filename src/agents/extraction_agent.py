import json
from pathlib import Path

from langfuse.openai import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL
from src.models import ContractChangeOutput

PROMPT_PATH: str = str(
    Path(__file__).parent.parent / "prompts" / "extraction_agent.txt"
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
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    return text.strip(), tokens


def run(
    context_map: str,
    original_text: str,
    amendment_text: str,
    langfuse_parent: object | None = None,
) -> tuple[ContractChangeOutput, int]:
    """
    Detecta cambios entre original y enmienda usando el mapa de contexto.

    Returns:
        Tupla (ContractChangeOutput validado, tokens_usados).
    """
    system_prompt = _load_prompt()
    client = _get_client()

    user_content = (
        f"MAPA DE CONTEXTO:\n{context_map}\n\n"
        f"TEXTO ORIGINAL:\n{original_text}\n\n"
        f"TEXTO ENMIENDA:\n{amendment_text}"
    )

    try:
        raw_content, tokens = _call_llm(client, system_prompt, user_content)
    except Exception as e:
        raise RuntimeError(f"Error en ExtractionAgent: {e}") from e

    raw_data = json.loads(raw_content)
    result = ContractChangeOutput.model_validate(raw_data)
    return result, tokens
