import PyPDF2
import io
import re
from typing import List
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)


async def extract_text_from_pdf(file: UploadFile) -> str:

    try:
        pdf_bytes = await file.read()
        
        # Mở PDF từ bytes
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        
        # Trích xuất text từ tất cả các trang
        text_parts = []
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            page_text = page.extract_text()
            if page_text.strip():
                text_parts.append(page_text)
                logger.info(f"Đã trích xuất trang {page_num}: {len(page_text)} ký tự")
        
        if not text_parts:
            raise HTTPException(
                status_code=400,
                detail="Không thể trích xuất văn bản từ PDF. File có thể là ảnh scan hoặc bị mã hóa."
            )
        
        # Ghép text và làm sạch
        full_text = "\n\n".join(text_parts)
        cleaned_text = clean_text(full_text)
        
        logger.info(f"✅ Đã trích xuất {len(text_parts)} trang, tổng {len(cleaned_text)} ký tự")
        return cleaned_text
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi đọc PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý PDF: {str(e)}"
        )


def clean_text(text: str) -> str:

    text = re.sub(r'[\r\t\f\v]', ' ', text)
    
    text = re.sub(r' +', ' ', text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    return text.strip()


def chunk_text(text: str, max_chars: int = 4000, overlap: int = 200) -> List[str]:

    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        if end < len(text):
            for sep in ['\n\n', '. ', '。', '! ', '? ', '\n']:
                last_sep = text.rfind(sep, start, end)
                if last_sep != -1:
                    end = last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            logger.debug(f"Chunk {len(chunks)}: {len(chunk)} ký tự")

        start = end - overlap if end < len(text) else end
    
    logger.info(f"Đã chia thành {len(chunks)} chunks")
    return chunks


def estimate_tokens(text: str) -> int:
    return len(text) // 4
