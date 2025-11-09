"""Creative helper utilities (word count, name generation, etc.)."""

from __future__ import annotations

import random
import re
from typing import Any


def calculate_word_count(text: str) -> dict[str, Any]:
    """Return statistics about the provided text."""

    cleaned = text.replace("\n", " ")
    tokens = [token for token in re.split(r"\s+", cleaned) if token]
    sentences = [s.strip() for s in re.split(r"[。！？!?\.]+", cleaned) if s.strip()]
    return {
        "characters": len(text.replace("\n", "")),
        "words": len(tokens),
        "sentences": len(sentences),
        "avg_sentence_length": (
            (sum(len(s) for s in sentences) / len(sentences)) if sentences else 0
        ),
    }


_NAME_POOLS = {
    ("xuanhuan", "male"): ["萧炎", "牧尘", "林动", "叶凡", "凌风"],
    ("xuanhuan", "female"): ["萧薰儿", "彩鳞", "小医仙", "雪芸", "牧灵儿"],
    ("urban", "male"): ["江寒", "陆锋", "秦川", "苏尘"],
    ("urban", "female"): ["夏语冰", "林婉", "苏晴", "顾晚"],
}


def random_name_generator(genre: str, gender: str, seed: int | None = None) -> str:
    """Return a pseudo-random name for the given genre/gender."""

    key = (genre.lower(), gender.lower())
    pool = _NAME_POOLS.get(key) or _NAME_POOLS.get((genre.lower(), "male")) or ["苍玄"]
    rng = random.Random(seed or hash((genre, gender)))
    return rng.choice(pool)


def style_analyzer(text: str) -> dict[str, Any]:
    """Provide simple heuristics about a text's style."""

    sentences = [s.strip() for s in re.split(r"[。！？!?\.]+", text) if s.strip()]
    avg_length = (sum(len(s) for s in sentences) / len(sentences)) if sentences else 0
    exclamations = text.count("！") + text.count("!")
    ellipsis = text.count("……") + text.count("...")
    adjectives = len(re.findall(r"[优壮美奇炫丽静柔烈沉]\w?", text))
    return {
        "avg_sentence_length": avg_length,
        "exclamation_ratio": exclamations / max(len(sentences), 1),
        "ellipsis_ratio": ellipsis / max(len(sentences), 1),
        "adjective_hits": adjectives,
        "tone": _infer_tone(avg_length, exclamations, ellipsis),
    }


def _infer_tone(avg_sentence_length: float, exclamations: int, ellipsis: int) -> str:
    if exclamations > ellipsis and exclamations > 1:
        return "激昂"
    if avg_sentence_length < 12:
        return "轻快"
    if avg_sentence_length > 30:
        return "细腻"
    return "平稳"


def dialogue_enhancer(dialogue_text: str, character_hint: str | None = None) -> str:
    """Add simple beats/动作 to dialogue text."""

    lines = [line.strip() for line in dialogue_text.splitlines() if line.strip()]
    enhanced: list[str] = []
    for line in lines:
        prefix = character_hint or "他"
        beat = "沉声" if "!" in line or "？" in line else "低声"
        # 同时删除中英文引号（U+201C/D 左右双引号，U+2018/9 左右单引号，以及英文引号）
        cleaned_line = line.strip("\"\u201c\u201d'\u2018\u2019")
        enhanced.append(prefix + beat + '道："' + cleaned_line + '"')
    return "\n".join(enhanced)


_TWIST_TEMPLATES = [
    "{hero}发现{ally}其实是{villain}布下的诱饵，真正的威胁来自{twist}。",
    "危机将至时，{hero}被迫与旧敌{ally}合作，共同揭开{twist}。",
    "所有线索指向的真相竟是——{twist}，连导师{ally}也被蒙在鼓里。",
]


def plot_twist_generator(
    current_plot: str, intensity: str = "medium", seed: int | None = None
) -> list[str]:
    rng = random.Random(seed or hash(current_plot))
    variants = []
    for template in _TWIST_TEMPLATES:
        twist = template.format(
            hero=_extract_keyword(current_plot, rng),
            ally=_extract_keyword(current_plot, rng, fallback="昔日同伴"),
            villain=_extract_keyword(current_plot, rng, fallback="幕后黑手"),
            twist=_derive_twist(current_plot, intensity, rng),
        )
        variants.append(twist)
    return variants


def _extract_keyword(text: str, rng: random.Random, fallback: str | None = None) -> str:
    words = [token for token in re.split(r"[^\w\u4e00-\u9fa5]+", text) if token]
    return rng.choice(words) if words else (fallback or "主角")


def _derive_twist(plot: str, intensity: str, rng: random.Random) -> str:
    base = [
        "主角其实拥有被封印的记忆",
        "导师为了保护众人故意演戏",
        "最弱的角色掌握终局钥匙",
        "反派来自未来，试图修正历史",
    ]
    choice = rng.choice(base)
    if intensity == "high":
        return choice + "，而这一切只是更大循环的序章"
    if intensity == "low":
        return choice.replace("其实", "可能")
    return choice


__all__ = [
    "calculate_word_count",
    "random_name_generator",
    "style_analyzer",
    "dialogue_enhancer",
    "plot_twist_generator",
]
