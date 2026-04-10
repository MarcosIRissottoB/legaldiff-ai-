import base64
from pathlib import Path

from langfuse import observe
from langfuse.openai import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL

SUPPORTED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB
PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "image_parser.txt")


def _load_prompt() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read().strip()


def _validate_input(image_bytes: bytes, filename: str) -> str:
    """Valida extensión y tamaño. Retorna el mime type."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Formato no soportado: {suffix}. "
            f"Formatos válidos: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    if len(image_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"El archivo excede el límite de 20MB ({len(image_bytes)} bytes)")
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


def _get_client() -> openai.OpenAI:
    kwargs: dict[str, str] = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    return openai.OpenAI(**kwargs)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
def _call_vision_api(
    client: openai.OpenAI,
    system_prompt: str,
    base64_image: str,
    mime_type: str,
) -> tuple[str, int]:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                    }
                ],
            },
        ],
        max_tokens=4096,
    )
    text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    return text.strip(), tokens


@observe()
def parse_contract_image(
    image_bytes: bytes,
    filename: str,
) -> tuple[str, int]:
    """
    Valida, codifica y envía una imagen de contrato a GPT-4o Vision.

    Args:
        image_bytes: Contenido del archivo en bytes.
        filename: Nombre del archivo (para validar extensión).

    Returns:
        Tupla (texto_extraido, tokens_usados).
    """
    mime_type = _validate_input(image_bytes, filename)
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    system_prompt = _load_prompt()
    client = _get_client()

    try:
        return _call_vision_api(client, system_prompt, base64_image, mime_type)
    except Exception as e:
        raise RuntimeError(f"Error en llamada a GPT-4o Vision: {e}") from e
