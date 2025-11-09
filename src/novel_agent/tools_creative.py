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


def dialogue_enhancer(
    dialogue_text: str, character_hint: str | None = None, emotion: str | None = None
) -> str:
    """对话润色，添加动作、表情、心理描写

    Args:
        dialogue_text: 对话文本
        character_hint: 角色提示
        emotion: 情绪（如：警惕、愤怒、悲伤、喜悦、平静）

    Returns:
        润色后的对话文本

    Example:
        >>> dialogue_enhancer("你是谁？", "张三", "警惕")
        张三眉头一皱，右手按在剑柄上，警惕地问道："你是谁？"
    """
    lines = [line.strip() for line in dialogue_text.splitlines() if line.strip()]
    enhanced: list[str] = []

    # 根据情绪选择动作和语气
    emotion_map = {
        "警惕": {"action": "眉头一皱，右手按在剑柄上", "tone": "警惕地问道"},
        "愤怒": {"action": "怒目圆睁，握紧拳头", "tone": "怒声喝道"},
        "悲伤": {"action": "眼眶泛红，声音哽咽", "tone": "低声说道"},
        "喜悦": {"action": "脸上露出笑容，眼神柔和", "tone": "欣喜地说道"},
        "平静": {"action": "神色平静，语气淡然", "tone": "平静地说道"},
        "惊讶": {"action": "瞪大眼睛，倒吸一口凉气", "tone": "惊呼道"},
        "恐惧": {"action": "脸色煞白，身体颤抖", "tone": "颤声说道"},
    }

    for line in lines:
        prefix = character_hint or "他"
        # 同时删除中英文引号
        cleaned_line = line.strip("\"\u201c\u201d'\u2018\u2019")

        # 根据情绪添加动作和语气
        if emotion and emotion in emotion_map:
            action = emotion_map[emotion]["action"]
            tone = emotion_map[emotion]["tone"]
            enhanced.append(f'{prefix}{action}，{tone}："{cleaned_line}"')
        else:
            # 默认处理
            beat = "沉声" if "!" in line or "？" in line else "低声"
            enhanced.append(prefix + beat + '道："' + cleaned_line + '"')

    return "\n".join(enhanced)


_TWIST_TEMPLATES = [
    "{hero}发现{ally}其实是{villain}布下的诱饵，真正的威胁来自{twist}。",
    "危机将至时，{hero}被迫与旧敌{ally}合作，共同揭开{twist}。",
    "所有线索指向的真相竟是——{twist}，连导师{ally}也被蒙在鼓里。",
]


def plot_twist_generator(
    current_plot: str, intensity: str = "medium", seed: int | None = None
) -> str:
    """生成情节转折建议

    Args:
        current_plot: 当前情节描述
        intensity: 强度（low/medium/high）
        seed: 随机种子

    Returns:
        格式化的情节转折建议文本

    Example:
        >>> plot_twist_generator("张三与李四合作", "high")
        情节转折建议（高强度）：
        1. 李四背叛张三，原来是卧底
        2. ...
    """
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

    # 根据强度生成额外建议
    extra_twists = _generate_extra_twists(intensity, rng)
    variants.extend(extra_twists)

    # 格式化输出
    intensity_name = {"low": "低强度", "medium": "中强度", "high": "高强度"}.get(
        intensity, "中强度"
    )
    result = [f"情节转折建议（{intensity_name}）：\n"]
    for i, twist in enumerate(variants[:5], 1):
        result.append(f"{i}. {twist}")

    return "\n".join(result)


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


def _generate_extra_twists(intensity: str, rng: random.Random) -> list[str]:
    """根据强度生成额外的转折建议"""
    twists = [
        "神秘人物的真实身份揭晓，竟然是失散多年的亲人",
        "看似强大的敌人其实是虚张声势，真正的威胁另有其人",
        "关键道具被调包，导致计划全盘失败",
        "原本的目标地其实是陷阱，幕后黑手早已布局",
        "队伍中出现叛徒，关键信息被泄露",
    ]
    selected = rng.sample(twists, min(2, len(twists)))
    if intensity == "high":
        selected = [t + "，引发连锁反应" for t in selected]
    return selected


def scene_transition(from_scene: str, to_scene: str, transition_type: str = "time") -> str:
    """生成场景过渡文本

    Args:
        from_scene: 起始场景
        to_scene: 目标场景
        transition_type: 过渡类型（time/space/perspective）

    Returns:
        场景过渡文本

    Example:
        >>> scene_transition("战斗结束", "回到家中", "time")
        三天后，张三拖着疲惫的身躯回到家中。
    """
    if transition_type == "time":
        time_phrases = [
            "三天后",
            "第二天清晨",
            "一周之后",
            "当晚",
            "数日后",
            "转眼间",
            "时光荏苒",
        ]
        phrase = random.choice(time_phrases)
        return f"{phrase}，从{from_scene}到{to_scene}。"

    elif transition_type == "space":
        space_phrases = [
            "离开",
            "穿过繁华的街市",
            "一路奔波",
            "跨越千山万水",
            "快步走出",
            "悄然离去",
        ]
        phrase = random.choice(space_phrases)
        return f"{phrase}{from_scene}后，来到了{to_scene}。"

    elif transition_type == "perspective":
        perspective_phrases = [
            "与此同时",
            "另一边",
            "而在",
            "此时此刻",
            "就在同一时间",
        ]
        phrase = random.choice(perspective_phrases)
        return f"{phrase}，{to_scene}正在发生着另一番景象。"

    else:
        # 默认使用时间过渡
        return f"随后，场景从{from_scene}转移到{to_scene}。"


__all__ = [
    "calculate_word_count",
    "random_name_generator",
    "style_analyzer",
    "dialogue_enhancer",
    "plot_twist_generator",
    "scene_transition",
]
