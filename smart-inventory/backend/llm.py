"""Claude layer: explains deterministic insights in plain language and answers
free-form questions about the data. Numbers always come from detection.py;
Claude never invents figures -- it only narrates what's already computed."""
import json
import os
from anthropic import Anthropic, APIError

_client = None


def _get_client():
    global _client
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    if _client is None:
        _client = Anthropic(api_key=key)
    return _client


def explain_insight(insight: dict) -> dict:
    """Return {source: 'llm'|'fallback', text: str, hindi: str|None}."""
    fallback = (f"{insight['headline']}. Recommended action: {insight['recommended_action']} "
                f"(confidence {int(insight['confidence']*100)}%, potential impact "
                f"₹{insight['impact_inr']:,}).")
    client = _get_client()
    if not client:
        return {"source": "fallback", "text": fallback}
    prompt = f"""You are explaining an inventory alert to a small shop owner in India who is busy
and not data-savvy. Use ONLY the facts given below -- never invent numbers.

Facts (JSON): {json.dumps(insight)}

Reply with strict JSON only, no markdown, no preamble:
{{"english": "<2 short sentences: what happened and why it matters, in plain English>",
 "hindi": "<same 2 sentences in simple Hindi (Devanagari script)>"}}"""
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=300,
            messages=[{"role": "user", "content": prompt}])
        data = json.loads(resp.content[0].text.strip().strip("`").removeprefix("json"))
        return {"source": "llm", "text": data.get("english", fallback), "hindi": data.get("hindi")}
    except (APIError, json.JSONDecodeError, KeyError, IndexError, Exception):
        return {"source": "fallback", "text": fallback}


def answer_question(question: str, kpis: dict, insights: list[dict]) -> dict:
    """'Ask your data' -- Claude answers using only the supplied insight/KPI context."""
    client = _get_client()
    context = {"kpis": kpis, "insights": [
        {k: v for k, v in i.items() if k in
         ("product", "type", "severity", "headline", "recommended_action", "impact_inr",
          "confidence", "metrics")} for i in insights]}
    if not client:
        return {"source": "fallback",
                "text": "AI chat needs an ANTHROPIC_API_KEY in backend/.env. Meanwhile, check "
                        "the insight cards above -- they list every flagged product with the "
                        "reason and recommended action."}
    prompt = f"""You are a retail data assistant for a small shop owner. Answer the question using
ONLY the JSON data below. If the data doesn't contain the answer, say so honestly. Be concise
(3-4 sentences max), reference specific product names and numbers from the data, and never invent
figures not present in the JSON.

Data: {json.dumps(context)}

Question: {question}"""
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=400,
            messages=[{"role": "user", "content": prompt}])
        return {"source": "llm", "text": resp.content[0].text.strip()}
    except Exception as e:
        return {"source": "fallback", "text": f"AI chat is temporarily unavailable ({type(e).__name__}). "
                                               "Please check the insight cards above instead."}
