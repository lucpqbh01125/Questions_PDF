from typing import List, Dict, Any, Optional
from models.question_model import Question
import logging

logger = logging.getLogger(__name__)


class QuestionStore:

    
    def __init__(self):
        self._questions: List[Dict[str, Any]] = []
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Lấy tất cả câu hỏi"""
        return self._questions.copy()
    
    def set_all(self, questions: List[Dict[str, Any]]) -> None:
        """Set toàn bộ danh sách câu hỏi"""
        self._questions = questions.copy()
        logger.info(f"Đã lưu {len(questions)} câu hỏi vào store")
    
    def add(self, question: Dict[str, Any]) -> None:
        """Thêm một câu hỏi"""
        self._questions.append(question)
        logger.debug(f"Đã thêm câu hỏi: {question.get('question', '')[:50]}...")
    
    def update(self, index: int, question: Dict[str, Any]) -> bool:

        if 0 <= index < len(self._questions):
            self._questions[index] = question
            logger.info(f"Đã cập nhật câu hỏi tại index {index}")
            return True
        logger.warning(f"Index {index} không hợp lệ")
        return False
    
    def delete(self, index: int) -> bool:

        if 0 <= index < len(self._questions):
            deleted = self._questions.pop(index)
            logger.info(f"Đã xóa câu hỏi tại index {index}")
            return True
        logger.warning(f"Index {index} không hợp lệ")
        return False
    
    def get(self, index: int) -> Optional[Dict[str, Any]]:
        """Lấy câu hỏi tại index"""
        if 0 <= index < len(self._questions):
            return self._questions[index]
        return None
    
    def search(self, keyword: str) -> List[Dict[str, Any]]:

        keyword_lower = keyword.lower()
        results = [
            q for q in self._questions
            if keyword_lower in q.get("question", "").lower()
            or keyword_lower in q.get("answer", "").lower()
        ]
        logger.info(f"Tìm thấy {len(results)} câu hỏi với keyword '{keyword}'")
        return results
    
    def filter_by_type(self, question_type: str) -> List[Dict[str, Any]]:
        """Lọc câu hỏi theo loại"""
        results = [
            q for q in self._questions
            if q.get("type") == question_type
        ]
        logger.info(f"Tìm thấy {len(results)} câu hỏi loại '{question_type}'")
        return results
    
    def clear(self) -> None:
        """Xóa tất cả câu hỏi"""
        count = len(self._questions)
        self._questions.clear()
        logger.info(f"Đã xóa {count} câu hỏi khỏi store")
    
    def count(self) -> int:
        """Đếm số lượng câu hỏi"""
        return len(self._questions)

question_store = QuestionStore()
