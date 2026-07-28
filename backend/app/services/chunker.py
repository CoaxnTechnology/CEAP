import re
from app.config import RAGConfig


def chunk_text(text: str, source_name: str, file_id: str) -> list:
    paragraphs = re.split(r"\n{2,}", text)
    chunks, buffer, idx = [], "", 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(buffer) + len(para) + 2 <= RAGConfig.CHUNK_SIZE:
            buffer = (buffer + "\n\n" + para).strip()
        else:
            if buffer:
                chunks.append(
                    {
                        "text": buffer,
                        "source": source_name,
                        "file_id": file_id,
                        "chunk_index": idx,
                    }
                )
                idx += 1
                buffer = (
                    buffer[-RAGConfig.CHUNK_OVERLAP :].strip() + "\n\n" + para
                ).strip()
            else:
                for i in range(
                    0, len(para), RAGConfig.CHUNK_SIZE - RAGConfig.CHUNK_OVERLAP
                ):
                    chunks.append(
                        {
                            "text": para[i : i + RAGConfig.CHUNK_SIZE],
                            "source": source_name,
                            "file_id": file_id,
                            "chunk_index": idx,
                        }
                    )
                    idx += 1
                buffer = ""
    if buffer:
        chunks.append(
            {
                "text": buffer,
                "source": source_name,
                "file_id": file_id,
                "chunk_index": idx,
            }
        )
    return chunks
