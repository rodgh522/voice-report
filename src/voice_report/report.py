"""Meeting report generation using Google Gemini."""

from pathlib import Path

from google import genai
from google.genai import types

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

DEFAULT_SYSTEM_PROMPT = (
    "당신은 전문 회의록 작성자입니다. "
    "회의 녹취록을 분석하여 체계적인 회의 보고서를 마크다운 형식으로 작성해주세요. "
    "핵심 내용을 중심으로 간결하게 정리하고, 결정사항과 후속조치를 명확히 구분하세요."
)


def generate_report(
    transcript: str,
    api_key: str,
    system_prompt: str | None = None,
    model: str = "gemini-2.5-flash",
) -> str:
    """Generate a structured meeting report from a transcript."""
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=transcript,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt or DEFAULT_SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )

    return response.text


def load_template(name: str) -> str:
    """Load a prompt template by name from the templates directory."""
    template_path = TEMPLATES_DIR / f"{name}.txt"
    if not template_path.exists():
        available = [f.stem for f in TEMPLATES_DIR.glob("*.txt")]
        raise FileNotFoundError(
            f"Template '{name}' not found. "
            f"Available templates: {', '.join(available) or '(none)'}"
        )
    return template_path.read_text(encoding="utf-8").strip()
