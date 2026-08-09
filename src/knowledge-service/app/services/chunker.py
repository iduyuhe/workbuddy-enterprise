"""文本切片：按段落聚合，超长段落硬切，带 overlap。"""
import re


def chunk_blocks(blocks: list[dict], chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    chunks: list[dict] = []
    for block in blocks:
        text = block.get("text", "")
        meta = block.get("meta", {})
        if not text.strip():
            continue
        paragraphs = [p for p in re.split(r"\n+", text) if p.strip()]
        buf = ""
        for para in paragraphs:
            if len(buf) + len(para) <= chunk_size:
                buf += para + "\n"
            else:
                if buf.strip():
                    chunks.append({"text": buf.strip(), "meta": meta})
                if len(para) > chunk_size:
                    # 单段超长 → 硬切
                    step = max(1, chunk_size - overlap)
                    for i in range(0, len(para), step):
                        piece = para[i:i + chunk_size].strip()
                        if piece:
                            chunks.append({"text": piece, "meta": meta})
                    buf = ""
                else:
                    buf = para + "\n"
        if buf.strip():
            chunks.append({"text": buf.strip(), "meta": meta})
    return chunks
