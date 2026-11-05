"""Metamorphic test case generation, plus opt-in untrusted LLM candidate proposals."""
import re
from .llm import ModelClient
from .schemas import GoldCase


def generate_metamorphic(cases: list[GoldCase], limit: int = 10) -> list[dict]:
    result: list[dict] = []
    for case in cases:
        for suffix, message in (("case", case.message.upper()), ("space", f"  {case.message}  ")):
            result.append({"id": f"{case.id}-{suffix}", "message": message,
                           "expected_category": case.expected_category,
                           "expected_severity": case.expected_severity,
                           "tags": sorted(set(case.tags) | {"metamorphic"})})
            if len(result) >= limit:
                return result
    return result


def propose_ai_cases(model: ModelClient, sample: list[GoldCase]) -> list[dict]:
    """Never promote LLM suggestions directly into trusted goldens."""
    if model.mode == "deterministic":
        raise ValueError("--ai requires AQ_MODE=ollama, nim or openai_compatible")
    examples = "; ".join(c.message[:100] for c in sample[:4])
    response = model.complete_json(
        "Generate 3 diverse, SAFE synthetic incident messages to evaluate incident-triage model quality. "
        "Output a JSON object with key 'messages' containing a list of exactly 3 strings. "
        "Include one edge case and one ambiguous case. No real customer data. Examples: " + examples
    )
    messages = response.get("messages")
    if not isinstance(messages, list) or not all(isinstance(m, str) and 5 <= len(m) <= 4000 for m in messages):
        raise ValueError("The model did not provide a validated list of synthetic messages")
    return [{"id": f"DRAFT-AI-{i:03d}", "message": re.sub(r"[\r\n]+", " ", m),
             "needs_human_review": True, "source": "model_proposal_not_ground_truth"}
            for i, m in enumerate(messages[:3], start=1)]
