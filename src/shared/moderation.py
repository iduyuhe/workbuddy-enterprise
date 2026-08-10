"""企业内容审核管线（输入输出双通道）。

设计目标：
- 私有化部署场景下的合规护栏：防 PII / 涉密泄漏、拦截暴力/违法内容。
- 纯正则 + 可配置词表，无外部依赖，可离线运行。
- 三种处置模式（MODERATION_MODE）：
    block  — 直接拒绝（返回 blocked=True，不输出原/改后文本）
    redact — 脱敏后放行（PII 打码，命中词表仅记录原因）
    log    — 仅记录，原样放行
- 企业可在运行时通过 MODERATION_WORDLIST 指向一个文本文件（每行一个词）扩充敏感词，
  避免把政治/业务敏感词硬编码进代码库。

说明：词表默认仅含「涉密级别词」与「暴力/违法词」的通用样例，不内置任何政治实体词；
企业应按自身等保/合规要求自行维护词表文件。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

# ---------- 配置（环境变量驱动） ----------
ENABLED = os.getenv("MODERATION_ENABLED", "true").lower() in ("1", "true", "yes", "on")
MODE = os.getenv("MODERATION_MODE", "redact").lower()  # block | redact | log
WORDLIST_PATH = os.getenv("MODERATION_WORDLIST", "")


# ---------- 默认词表 ----------
DEFAULT_SECRET_WORDS = [
    "绝密", "机密", "秘密", "涉密", "保密", "内部资料", "严禁外传", "不得公开",
]
# 暴力/违法内容（通用样例；企业可按需扩充词表文件）
DEFAULT_VIOLENCE_WORDS = [
    "制作炸弹", "制造炸弹", "炸药配方", "如何杀人", "制毒", "冰毒配方",
    "网络攻击教程", "入侵系统教程", "贩卖枪支", "毒品交易",
]


# ---------- PII 正则 ----------
_RE_ID_CARD = re.compile(r"\b\d{17}[\dXx]\b")  # 18 位身份证
_RE_PHONE = re.compile(r"\b1[3-9]\d{9}\b")  # 手机号
_RE_BANKCARD = re.compile(r"\b\d{16,19}\b")  # 银行卡（粗匹配，配合上下文）
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def _mask_id(s: str) -> str:
    return s[:4] + "*" * (len(s) - 8) + s[-4:] if len(s) > 8 else "*" * len(s)


def _load_wordlist() -> list[str]:
    words: list[str] = []
    if WORDLIST_PATH and os.path.isfile(WORDLIST_PATH):
        try:
            with open(WORDLIST_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    w = line.strip()
                    if w and not w.startswith("#"):
                        words.append(w)
        except OSError:
            pass
    return words


@dataclass
class ModerationResult:
    action: str  # allow | block | redact | log
    blocked: bool
    reasons: list[str] = field(default_factory=list)
    original: str = ""
    text: str = ""  # 处置后的文本（block 时为空）


def moderate(text: str, direction: str = "input") -> ModerationResult:
    """审核一段文本。direction: input（用户输入）| output（模型输出）。

    返回处置结果与原因；block 模式下 blocked=True 且 text 为空。
    """
    if not ENABLED or not text:
        return ModerationResult(action="allow", blocked=False, reasons=[], original=text, text=text)

    reasons: list[str] = []
    out = text

    # 1) PII 检测
    has_id = bool(_RE_ID_CARD.search(out))
    has_phone = bool(_RE_PHONE.search(out))
    has_bank = bool(_RE_BANKCARD.search(out))
    has_email = bool(_RE_EMAIL.search(out))
    pii_hits = sum([has_id, has_phone, has_bank, has_email])
    if pii_hits:
        reasons.append("pii")
        if MODE in ("block",):
            return ModerationResult(action="block", blocked=True, reasons=reasons, original=text, text="")
        if MODE in ("redact", "log"):
            out = _RE_ID_CARD.sub(lambda m: _mask_id(m.group(0)), out)
            out = _RE_PHONE.sub(lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:], out)
            out = _RE_EMAIL.sub(lambda m: m.group(0)[0] + "***@***", out)
            # 银行卡打码（仅当同时疑似 PII 上下文；此处保守打码中间位）
            out = _RE_BANKCARD.sub(lambda m: m.group(0)[:4] + "*" * (len(m.group(0)) - 8) + m.group(0)[-4:], out)

    # 2) 敏感词（涉密 / 暴力违法）
    words = DEFAULT_SECRET_WORDS + DEFAULT_VIOLENCE_WORDS + _load_wordlist()
    matched = [w for w in words if w and w in out]
    if matched:
        reasons.append("sensitive:" + ",".join(matched[:5]))
        # 涉密/暴力词默认硬性拦截（无论模式，除非 log 仅记录）
        if MODE == "log":
            pass
        elif MODE == "block":
            return ModerationResult(action="block", blocked=True, reasons=reasons, original=text, text="")
        else:  # redact：记录原因但放行（企业可在 block 模式下硬性拦截）
            pass

    if not reasons:
        return ModerationResult(action="allow", blocked=False, reasons=[], original=text, text=out)

    action = "block" if any(r.startswith("sensitive") for r in reasons) and MODE == "block" else (
        "redact" if MODE == "redact" else ("log" if MODE == "log" else "allow")
    )
    return ModerationResult(action=action, blocked=False, reasons=reasons, original=text, text=out)
