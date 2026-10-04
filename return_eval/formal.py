"""Verbatim formal Stage16/24 scoring prompt and answer rules."""
import re

SYSTEM = (
    "Judge each candidate answer against the frozen gold and accepted aliases. You do not know the model, "
    "history condition, carrier, or aggregate result. Accept semantic equivalents at the requested short-answer "
    "granularity. For reference/current answers, both facts and their role assignment must match. For MCQ, accept "
    "one unambiguous correct letter or the complete correct option; reject conflicting choices. Do not use outside "
    "media knowledge, change the gold, infer missing facts, or reward explanations that contradict the answer. "
    "For OpenQA color questions, required precision comes from the question: a correct basic color is sufficient "
    "when no exact shade is requested. Do not require optional brightness/intensity or finer shade modifiers merely "
    "because they occur in gold. Reject different basic colors and omission of a genuinely second color; explicit "
    "exact-shade questions remain strict. Do not apply hidden MCQ options to OpenQA. "
    "Return JSON only: {\"judgments\":[{\"id\":string,\"verdict\":\"equivalent\"|\"incorrect\"|\"uncertain\","
    "\"format_compliant\":boolean,\"reason\":string}]}"
)

def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()

def mcq_rule(raw, gold, choices):
    explicit = []
    for pattern in (r"^\s*([A-Da-d])\s*(?:[\.:\)]|$)", r"\b(?:answer|option|choice)\s*(?:is|:|=)?\s*([A-Da-d])\b"):
        explicit += [value.upper() for value in re.findall(pattern, str(raw).strip(), flags=re.I)]
    explicit = sorted(set(explicit))
    if len(explicit) == 1:
        return explicit[0] == gold.upper()
    mentions = [index for index, choice in enumerate(choices) if norm(choice) and norm(choice) in norm(raw)]
    return len(mentions) == 1 and "ABCD"[mentions[0]] == gold.upper()


def chstats(v):
    n=len(v);c=sum(r['C']['content_correct'] for r in v);h=sum(r['H0']['content_correct'] for r in v)
    return dict(n=n,C_correct=c,H0_correct=h,C_pct=100*c/n,H0_pct=100*h/n,gap_pp=100*(c-h)/n,harm=sum(r['C']['content_correct'] and not r['H0']['content_correct'] for r in v),rescue=sum(not r['C']['content_correct'] and r['H0']['content_correct'] for r in v))
