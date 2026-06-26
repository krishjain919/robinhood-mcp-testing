"""
The AI decision layer — where an agent actually adds edge.

A pure technical screen can tell you a chart looks like a valid swing setup.
What it can't do is read the news, understand that a "breakout" is really a
short-squeeze about to unwind, notice a pending lawsuit, or weigh whether the
momentum is healthy or a blow-off top. That qualitative judgment is exactly
what an LLM is good at.

Design rules that make this safe:
  1. The agent only sees candidates that ALREADY passed the quant screen.
  2. The agent can only CONFIRM, add CAUTION (size down), or VETO. It can
     never invent a trade or increase risk. Its conviction score is a
     multiplier in [0, 1] applied to position size — nothing more.
  3. Hard event risk (earnings inside the blackout) is vetoed before we even
     spend a token on the model.
  4. If there's no API key, a deterministic heuristic stands in so the whole
     pipeline still runs.

Model + SDK usage follows Anthropic's current guidance: the `anthropic` SDK,
`claude-opus-4-8` by default, adaptive thinking, and structured JSON output.
"""

import json

import config


SYSTEM_PROMPT = """\
You are a disciplined swing-trading risk reviewer embedded in an automated \
trading assistant. A quantitative screen has ALREADY confirmed that this \
stock has a technically valid swing-trade setup (uptrend, relative strength, \
volume, momentum). Do not re-litigate the technicals.

Your job is the qualitative layer the screen cannot see: news flow, catalysts, \
event risk, and whether the move looks healthy or exhausted. You decide \
whether the trade should proceed, proceed with reduced size, or be skipped.

Hard constraints:
- You may only CONFIRM, CAUTION (proceed smaller), or VETO. You can never \
increase risk or recommend a larger position.
- Default to caution. When evidence is thin or mixed, lower conviction.
- Treat binary events (earnings, FDA decisions, major legal/regulatory \
rulings) inside a few days as high event risk.
- A parabolic, far-extended move is a reason to reduce conviction, not chase.
- Be concise and concrete. Base claims on the dossier provided; do not invent \
facts you weren't given.

conviction is a 0.0-1.0 multiplier on position size: 1.0 = full confidence, \
0.5 = half size, 0.0 = do not trade. VETO implies conviction 0.0."""


JUDGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["CONFIRM", "CAUTION", "VETO"]},
        "conviction": {"type": "number"},
        "sentiment": {"type": "string", "enum": ["BULLISH", "NEUTRAL", "BEARISH"]},
        "event_risk": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "catalyst": {"type": "string"},
        "thesis": {"type": "string"},
        "key_risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "verdict",
        "conviction",
        "sentiment",
        "event_risk",
        "catalyst",
        "thesis",
        "key_risks",
    ],
    "additionalProperties": False,
}


# Keyword fallbacks for the no-API-key path.
_BEARISH_WORDS = [
    "downgrade", "lawsuit", "investigation", "fraud", "miss", "cut", "cuts",
    "layoff", "sec ", "recall", "plunge", "slump", "probe", "halt", "warning",
    "bankrupt", "delay", "subpoena", "guidance cut",
]
_BULLISH_WORDS = [
    "upgrade", "beat", "beats", "record", "surge", "soar", "raises", "raised",
    "buyback", "partnership", "approval", "wins", "contract", "expands",
    "outperform", "all-time high",
]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


def _finalize(judgment: dict, source: str, model: str | None) -> dict:
    """
    Apply the safety envelope to whatever the judge returned.

    No matter what the model says, CAUTION can't exceed half size and CONFIRM
    can't drop below half — and a VETO is always zero.
    """

    verdict = judgment.get("verdict", "CAUTION")
    conviction = _clamp(judgment.get("conviction", 0.0))

    if verdict == "VETO":
        conviction = 0.0
        tradeable = False
    elif verdict == "CAUTION":
        conviction = min(conviction, 0.6) or 0.5
        tradeable = True
    else:  # CONFIRM
        conviction = max(conviction, 0.5)
        tradeable = True

    return {
        "source": source,
        "model": model,
        "verdict": verdict,
        "conviction": round(conviction, 2),
        "tradeable": tradeable,
        "sentiment": judgment.get("sentiment", "NEUTRAL"),
        "event_risk": judgment.get("event_risk", "MEDIUM"),
        "catalyst": judgment.get("catalyst") or None,
        "thesis": judgment.get("thesis", ""),
        "key_risks": judgment.get("key_risks", []),
    }


def _heuristic_judgment(dossier: dict) -> dict:
    """Deterministic stand-in for the model. Conservative by construction."""

    ind = dossier.get("indicators", {})
    headlines = " ".join(h.get("title", "") for h in dossier.get("news", [])).lower()

    bearish_hits = [w.strip() for w in _BEARISH_WORDS if w in headlines]
    bullish_hits = [w.strip() for w in _BULLISH_WORDS if w in headlines]

    stretched = ind.get("rsi_14", 0) >= 82 or ind.get("dist_sma_20_pct", 0) >= 15
    risks = []

    if bearish_hits:
        sentiment = "BEARISH"
        risks.append(f"Recent headlines mention: {', '.join(sorted(set(bearish_hits)))}.")
    elif bullish_hits:
        sentiment = "BULLISH"
    else:
        sentiment = "NEUTRAL"

    if stretched:
        risks.append("Price is extended/overbought — elevated pullback risk.")

    if sentiment == "BEARISH":
        verdict, conviction = "CAUTION", 0.4
    elif stretched:
        verdict, conviction = "CAUTION", 0.6
    else:
        verdict, conviction = "CONFIRM", 1.0

    return _finalize(
        {
            "verdict": verdict,
            "conviction": conviction,
            "sentiment": sentiment,
            "event_risk": "LOW",
            "catalyst": None,
            "thesis": "Heuristic review (no AI key): "
            + dossier.get("narrative", "")[:240],
            "key_risks": risks or ["No obvious qualitative red flags in the dossier."],
        },
        source="heuristic",
        model=None,
    )


def _claude_judgment(dossier: dict) -> dict:
    """Ask Claude for a structured judgment. Raises on any failure so the
    caller can fall back."""

    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    user_prompt = (
        "Review this swing-trade candidate and return your structured judgment.\n\n"
        "DOSSIER:\n"
        + json.dumps(
            {
                "symbol": dossier.get("symbol"),
                "profile": dossier.get("profile"),
                "technical": dossier.get("technical"),
                "narrative": dossier.get("narrative"),
                "earnings": dossier.get("earnings"),
                "news": dossier.get("news"),
                "key_indicators": {
                    k: dossier.get("indicators", {}).get(k)
                    for k in (
                        "price", "rsi_14", "adx_14", "atr_pct", "volume_ratio",
                        "relative_strength_63d", "dist_sma_20_pct",
                        "pct_below_52w_high", "macd_hist",
                    )
                },
            },
            indent=2,
            default=str,
        )
    )

    response = client.messages.create(
        model=config.AI_MODEL,
        max_tokens=1500,
        thinking={"type": "adaptive"},
        output_config={
            "effort": config.AI_EFFORT,
            "format": {"type": "json_schema", "schema": JUDGMENT_SCHEMA},
        },
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("Model declined to answer.")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise RuntimeError("No text content returned.")

    data = json.loads(text)
    return _finalize(data, source="claude", model=config.AI_MODEL)


def judge(dossier: dict) -> dict:
    """
    Public entry point. Returns the final, safety-enveloped judgment.

    Order of precedence:
      1. Earnings inside the blackout -> automatic VETO (no model call).
      2. Claude, if available.
      3. Deterministic heuristic.
    """

    earnings = dossier.get("earnings", {})
    if earnings.get("blocked"):
        return _finalize(
            {
                "verdict": "VETO",
                "conviction": 0.0,
                "sentiment": "NEUTRAL",
                "event_risk": "HIGH",
                "catalyst": "Upcoming earnings report",
                "thesis": "Vetoed automatically: earnings fall inside the "
                "blackout window, so an overnight gap could blow past the stop.",
                "key_risks": [earnings.get("note", "Earnings blackout.")],
            },
            source="rule",
            model=None,
        )

    if config.ai_available():
        try:
            return _claude_judgment(dossier)
        except Exception as error:  # network, parse, refusal, missing pkg
            fallback = _heuristic_judgment(dossier)
            fallback["thesis"] = f"[AI unavailable: {error}] " + fallback["thesis"]
            return fallback

    return _heuristic_judgment(dossier)


if __name__ == "__main__":
    from dossier import build_dossier

    result = judge(build_dossier("NVDA"))
    print(json.dumps(result, indent=2))
