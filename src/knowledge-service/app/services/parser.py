"""文档解析：MinerU 优先，MVP 降级 pdfplumber / python-docx，纯文本兜底。

返回 list[{"text":..., "meta": {"page": ...}}]，供后续切片。
"""
import os
import re

from app.core.config import UPLOAD_ROOT


def parse_file(path: str) -> list[dict]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext in (".docx", ".doc"):
        return _parse_docx(path)
    # 纯文本 / 未知类型兜底
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return [{"text": f.read(), "meta": {"page": 1}}]
    except OSError:
        return []


def _parse_pdf(path: str) -> list[dict]:
    try:
        import pdfplumber
    except ImportError:
        return [{"text": "", "meta": {"page": 0, "note": "pdfplumber not installed"}}]
    out: list[dict] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            out.append({"text": page.extract_text() or "", "meta": {"page": i}})
    return out


def _parse_docx(path: str) -> list[dict]:
    try:
        import docx
    except ImportError:
        return [{"text": "", "meta": {"page": 0, "note": "python-docx not installed"}}]
    document = docx.Document(path)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return [{"text": "\n".join(paragraphs), "meta": {"page": 1}}]


# TODO(阶段2): 接入 MinerU 做高质量版面/公式/表格解析：
#   from mineru.cli import ... 或使用 mineru 命令行；解析结果统一映射到
#   [{"text", "meta": {"page", "bbox", ...}}] 结构后即可复用下游切片逻辑。
