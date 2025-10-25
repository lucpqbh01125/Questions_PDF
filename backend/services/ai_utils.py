from openai import OpenAI, APIError, RateLimitError, AuthenticationError
import json
import logging
from typing import List, Dict, Any
from fastapi import HTTPException
from config.settings import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)


async def check_content_relevance(text: str, user_prompt: str) -> Dict[str, Any]:
    """
    Kiểm tra xem nội dung file có liên quan đến yêu cầu của người dùng không
    Trả về: {"relevant": True/False, "reason": "...", "confidence": 0.0-1.0}
    """
    try:
        system_message = {
            "role": "system",
            "content": (
                "Bạn là trợ lý PHÂN TÍCH độ liên quan giữa tài liệu và yêu cầu người dùng.\n"
                "\n"
                "NHIỆM VỤ: Xác định xem tài liệu có đủ thông tin để tạo câu hỏi theo yêu cầu không?\n"
                "\n"
                "CÁCH ĐÁNH GIÁ:\n"
                "1. ĐỌC KỸ yêu cầu → Trích xuất CHỦ ĐỀ/MÔN HỌC/NỘI DUNG cần tạo câu hỏi\n"
                "2. ĐỌC KỸ tài liệu → Xác định CHỦ ĐỀ/MÔN HỌC/NỘI DUNG có trong tài liệu\n"
                "3. SO SÁNH:\n"
                "   - LIÊN QUAN: Tài liệu chứa thông tin về chủ đề được yêu cầu\n"
                "   - KHÔNG LIÊN QUAN: Tài liệu hoàn toàn khác chủ đề\n"
                "\n"
                "VÍ DỤ:\n"
                "✅ LIÊN QUAN:\n"
                "- Yêu cầu: 'Tạo 10 câu trắc nghiệm về logarit'\n"
                "- Tài liệu: Sách toán chứa bài 'Hàm số logarit'...\n"
                "→ relevant=true vì có nội dung logarit\n"
                "\n"
                "❌ KHÔNG LIÊN QUAN:\n"
                "- Yêu cầu: 'Tạo 10 câu trắc nghiệm môn văn'\n"
                "- Tài liệu: Sách toán về logarit...\n"
                "→ relevant=false vì không có nội dung văn học\n"
                "\n"
                "⚠️ LIÊN QUAN TỪNG PHẦN:\n"
                "- Yêu cầu: 'Tạo 5 câu về logarit, 5 câu về đạo hàm'\n"
                "- Tài liệu: Chỉ có logarit, không có đạo hàm\n"
                "→ relevant=true nhưng confidence=0.5 (chỉ 50% yêu cầu)\n"
                "\n"
                "OUTPUT (CHỈ JSON, KHÔNG TEXT KHÁC):\n"
                "{\n"
                "  \"relevant\": true/false,\n"
                "  \"confidence\": 0.0-1.0,\n"
                "  \"reason\": \"Giải thích ngắn gọn\",\n"
                "  \"topics_found\": [\"chủ đề 1\", \"chủ đề 2\"],\n"
                "  \"topics_missing\": [\"chủ đề còn thiếu\"]\n"
                "}"
            )
        }
        
        user_message = {
            "role": "user",
            "content": f"""YÊU CẦU NGƯỜI DÙNG:
{user_prompt}

NỘI DUNG TÀI LIỆU (500 ký tự đầu):
{text[:500]}...

PHÂN TÍCH: Tài liệu này có đủ thông tin để tạo câu hỏi theo yêu cầu không?"""
        }
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Dùng model rẻ cho task này
            messages=[system_message, user_message],
            temperature=0.3,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        result = json.loads(content.strip())
        logger.info(f"📊 Kiểm tra độ liên quan: {result}")
        return result
        
    except Exception as e:
        logger.warning(f"⚠️ Không thể kiểm tra độ liên quan: {str(e)}, tiếp tục tạo câu hỏi...")
        # Nếu lỗi, mặc định cho phép tạo (để không block hoàn toàn)
        return {
            "relevant": True,
            "confidence": 0.5,
            "reason": "Không thể xác định, tiếp tục thử tạo",
            "topics_found": [],
            "topics_missing": []
        }


async def generate_questions_from_text(text: str, user_prompt: str, chunk_index: int = 0) -> List[Dict[str, Any]]:

    try:
        # 🔍 BƯỚC 1: KIỂM TRA ĐỘ LIÊN QUAN TRƯỚC KHI TẠO CÂU HỎI
        if chunk_index == 0:  # Chỉ kiểm tra ở chunk đầu tiên
            logger.info("🔍 Đang kiểm tra độ liên quan giữa yêu cầu và nội dung file...")
            relevance_check = await check_content_relevance(text, user_prompt)
            
            if not relevance_check.get("relevant", False) or relevance_check.get("confidence", 0) < 0.3:
                logger.warning(f"❌ Nội dung không phù hợp: {relevance_check.get('reason', 'Không rõ lý do')}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Nội dung file không phù hợp với yêu cầu",
                        "reason": relevance_check.get("reason", "Tài liệu không chứa thông tin liên quan"),
                        "topics_found": relevance_check.get("topics_found", []),
                        "topics_missing": relevance_check.get("topics_missing", []),
                        "suggestion": "Vui lòng chọn file khác có nội dung phù hợp hoặc thay đổi yêu cầu tạo câu hỏi"
                    }
                )
            else:
                logger.info(f"✅ Nội dung phù hợp (confidence: {relevance_check.get('confidence', 0):.2f})")
                if relevance_check.get("topics_missing"):
                    logger.warning(f"⚠️ Một số chủ đề còn thiếu: {relevance_check.get('topics_missing')}")

        # 🎯 BƯỚC 2: TẠO CÂU HỎI TRẮC NGHIỆM
        import re
        numbers_in_prompt = re.findall(r'\d+', user_prompt)
        total_questions = sum(int(n) for n in numbers_in_prompt) if numbers_in_prompt else 5
        
        # 🎯 MẶC ĐỊNH = TRẮC NGHIỆM (MCQ)
        required_type = "mcq"
        
        logger.info(f"🎯 Type: TRẮC NGHIỆM (mcq) | Số: {total_questions} | Yêu cầu: '{user_prompt}'")
        
        user_message = {
            "role": "user",
            "content": f"""📄 TÀI LIỆU GỐC (TOÀN BỘ NỘI DUNG):
{'='*80}
{text}
{'='*80}

YÊU CẦU CỦA NGƯỜI DÙNG: {user_prompt}

SỐ LƯỢNG CÂU HỎI CẦN TẠO: {total_questions} câu

🚨🚨🚨 LOẠI CÂU HỎI: TRẮC NGHIỆM (MCQ) - 4 ĐÁP ÁN A,B,C,D 🚨🚨🚨

✅ FORMAT BẮT BUỘC:
{{"question": "...", "type": "mcq", "choices": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "A. ..."}}

❌ CHỈ TẠO TRẮC NGHIỆM!

CÁCH LÀM:
1. ĐỌC tài liệu
2. TÌM thông tin liên quan
3. TẠO {total_questions} câu TRẮC NGHIỆM với 4 đáp án A,B,C,D
4. ĐẢM BẢO đúng format

OUTPUT - CHỈ JSON ARRAY:
[{{"question":"...", "type":"mcq", "choices":["A. ...","B. ...","C. ...","D. ..."], "answer":"A. ..."}}]"""
        }
        
        system_message = {
            "role": "system",
            "content": "TẠO CÂU HỎI TRẮC NGHIỆM với 4 đáp án A,B,C,D. Output JSON array."
        }
        
        logger.info(f"Yêu cầu tạo {total_questions} câu TRẮC NGHIỆM cho chunk {chunk_index}...")
        logger.info(f"Prompt: {user_prompt[:100]}...")
        
        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[system_message, user_message],
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens
            )
            content = response.choices[0].message.content.strip()
        except Exception as api_error:
            logger.error(f"Lỗi gọi Chat API: {str(api_error)}")
            raise

        logger.info(f"Response từ AI (100 ký tự đầu): {content[:100]}")
        questions = parse_ai_response(content)
        
        # 🔧 AUTO-FIX: BẮT BUỘC TẤT CẢ LÀ TRẮC NGHIỆM
        fixed_count = 0
        for i, q in enumerate(questions):
            actual_type = q.get("type", "")
            
            # Fix 1: BẮT BUỘC type = mcq
            if actual_type != "mcq":
                logger.warning(f"⚠️ CÂU {i+1}: type='{actual_type}' → SỬA thành 'mcq'")
                q["type"] = "mcq"
                fixed_count += 1
            
            # Fix 2: BẮT BUỘC có 4 choices A,B,C,D
            choices = q.get("choices", [])
            if not choices or len(choices) < 4:
                logger.warning(f"⚠️ CÂU {i+1}: Thiếu choices → Thêm 4 đáp án A,B,C,D")
                ans_text = str(q.get("answer", "Đáp án đúng"))
                # Xóa prefix A. B. C. D. nếu có
                for prefix in ["A. ", "B. ", "C. ", "D. "]:
                    ans_text = ans_text.replace(prefix, "")
                ans_text = ans_text.strip()
                
                q["choices"] = [
                    f"A. {ans_text}",
                    f"B. Đáp án khác 1",
                    f"C. Đáp án khác 2",
                    f"D. Đáp án khác 3"
                ]
                q["answer"] = f"A. {ans_text}"
                fixed_count += 1
        
        if fixed_count > 0:
            logger.warning(f"🔧 Đã tự động sửa {fixed_count} vấn đề về type/choices")
        
        logger.info(f"✅ Tạo được {len(questions)} câu hỏi (type={required_type}) từ chunk {chunk_index}")
        return questions
        
    except RateLimitError:
        logger.error("Hết quota OpenAI")
        raise HTTPException(
            status_code=429,
            detail="Hết quota OpenAI. Vui lòng thử lại sau hoặc kiểm tra billing."
        )
    except AuthenticationError:
        logger.error("API key không hợp lệ")
        raise HTTPException(
            status_code=401,
            detail="API key OpenAI không hợp lệ"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi gọi OpenAI API: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi tạo câu hỏi: {str(e)}"
        )


def parse_ai_response(content: str) -> List[Dict[str, Any]]:

    if not content:
        raise HTTPException(
            status_code=500,
            detail="OpenAI trả về response trống"
        )
    
    content = content.strip()
    for marker in ["```json", "```"]:
        if content.startswith(marker):
            content = content[len(marker):].lstrip()
    if content.endswith("```"):
        content = content[:-3].rstrip()
    if content.startswith('{') and '"error"' in content:
        try:
            error_obj = json.loads(content)
            if "error" in error_obj:
                error_msg = error_obj['error']
                logger.warning(f"⚠️ AI không tạo được câu hỏi từ chunk này: {error_msg}")
                return []
        except json.JSONDecodeError:
            pass
    
    start_idx = content.find('[')
    end_idx = content.rfind(']')
    
    if start_idx == -1 or end_idx == -1:
        logger.warning("Response không chứa JSON array, trả về list rỗng")
        return []  
    
    json_str = content[start_idx:end_idx + 1]
    
    try:
        questions = json.loads(json_str)
        if not isinstance(questions, list):
            raise ValueError("Response không phải là array")
        

        validated = []
        for q in questions:
            if isinstance(q, dict):

                if "question" in q:
                    if "answer" not in q:
                        q["answer"] = "Chưa cập nhật"
                    validated.append(q)
                else:

                    logger.warning(f" Câu hỏi thiếu trường 'question': {q}")
        
        if not validated:

            logger.warning(f" Validation failed nhưng response có {len(questions)} items, trả về chúng với cảnh báo")
            if questions:
                for q in questions:
                    if isinstance(q, dict):
                        if "question" not in q:
                            q["question"] = str(q)  
                        if "answer" not in q:
                            q["answer"] = "Chưa cập nhật"
                return questions
            
            raise HTTPException(
                status_code=400,
                detail="Response không chứa câu hỏi hợp lệ. Nội dung: " + str(questions)[:200]
            )
        
        return validated
        
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi parse JSON: {str(e)}\nContent: {json_str[:200]}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi parse JSON từ AI response"
        )


def validate_question_relevance(questions: List[Dict], source_text: str, threshold: float = 0.3) -> bool:
    """
    Validate độ liên quan của câu hỏi với văn bản nguồn
    Cải thiện: Kiểm tra chi tiết hơn bằng cách tìm keywords trong cả question và answer
    """
    if not questions:
        return False
    
    source_lower = source_text.lower()
    relevant_count = 0
    
    for q in questions:
        question_text = q.get("question", "").lower()
        answer_text = str(q.get("answer", "")).lower()
        choices_text = " ".join([str(c).lower() for c in q.get("choices", [])])
        
        combined_text = f"{question_text} {answer_text} {choices_text}"
        
        stopwords = {'của', 'và', 'cho', 'với', 'trong', 'trên', 'dưới', 'được', 'là', 'có', 
                     'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 'was'}
        words = [w.strip('.,?!:;"()[]{}') for w in combined_text.split()]
        keywords = [w for w in words if len(w) >= 4 and w not in stopwords]
        
        matches = sum(1 for word in keywords if word in source_lower)
        
        if keywords:
            match_ratio = matches / len(keywords)
            if match_ratio >= 0.4 or matches >= 5:
                relevant_count += 1
                logger.debug(f"✅ Câu hỏi liên quan: {question_text[:50]}... ({matches}/{len(keywords)} keywords)")
            else:
                logger.warning(f"⚠️ Câu hỏi ít liên quan: {question_text[:50]}... ({matches}/{len(keywords)} keywords)")
    
    relevance_score = relevant_count / len(questions)
    logger.info(f"📊 Độ liên quan: {relevance_score:.2f} ({relevant_count}/{len(questions)})")
    
    return relevance_score >= threshold


def check_hallucination(questions: List[Dict], source_text: str) -> List[Dict]:

    import re
    
    source_lower = source_text.lower()
    filtered_questions = []
    hallucination_count = 0
    
    source_numbers = set(re.findall(r'\d+(?:\.\d+)?', source_text))
    
    for idx, q in enumerate(questions):
        question_text = q.get("question", "")
        answer_text = str(q.get("answer", ""))
        choices = q.get("choices", [])
        
        is_hallucination = False
        reason = ""
        
        question_numbers = set(re.findall(r'\d+(?:\.\d+)?', question_text + " " + answer_text))
        if question_numbers and not question_numbers.issubset(source_numbers):
            suspicious_numbers = question_numbers - source_numbers
            if suspicious_numbers:
                is_hallucination = True
                reason = f"Số liệu không có trong tài liệu: {suspicious_numbers}"
        
        answer_keywords = [w.strip('.,?!:;"()[]{}').lower() 
                          for w in answer_text.split() 
                          if len(w) > 5]  
        
        if answer_keywords:
            matches = sum(1 for kw in answer_keywords if kw in source_lower)
            if len(answer_keywords) >= 3 and matches / len(answer_keywords) < 0.3:
                is_hallucination = True
                reason = f"Answer chứa quá nhiều từ không có trong tài liệu ({matches}/{len(answer_keywords)} keywords)"
        
        if choices and isinstance(choices, list):
            for choice in choices:
                choice_str = str(choice).lower()

                choice_numbers = set(re.findall(r'\d+(?:\.\d+)?', choice_str))
                if choice_numbers and not choice_numbers.issubset(source_numbers):
                    suspicious = choice_numbers - source_numbers
                    if suspicious:
                        is_hallucination = True
                        reason = f"Lựa chọn có số không có trong tài liệu: {suspicious}"
                        break
        
        if is_hallucination:
            hallucination_count += 1
            logger.warning(f" Loại bỏ câu {idx+1} (nghi ngờ hallucination): {question_text[:60]}...")
            logger.warning(f"   Lý do: {reason}")
        else:
            filtered_questions.append(q)
    
    if hallucination_count > 0:
        logger.info(f"Đã lọc bỏ {hallucination_count}/{len(questions)} câu hỏi nghi ngờ hallucination")
    
    return filtered_questions
