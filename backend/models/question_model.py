from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class QuestionType(str, Enum):
    """Chỉ hỗ trợ TRẮC NGHIỆM"""
    MCQ = "mcq"         # Multiple Choice - Trắc nghiệm 4 đáp án A,B,C,D


class Question(BaseModel):
    """Model cho câu hỏi TRẮC NGHIỆM"""
    question: str = Field(..., description="Nội dung câu hỏi")
    type: QuestionType = Field(default=QuestionType.MCQ, description="Loại câu hỏi (chỉ MCQ)")
    choices: List[str] = Field(..., description="4 lựa chọn A,B,C,D (BẮT BUỘC)")
    answer: str = Field(..., description="Đáp án đúng")
    explanation: Optional[str] = Field(default=None, description="Giải thích đáp án")
    difficulty: Optional[Literal["easy", "medium", "hard"]] = Field(default=None, description="Độ khó")
    tags: Optional[List[str]] = Field(default=None, description="Tags cho câu hỏi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "2 + 2 bằng bao nhiêu?",
                "type": "mcq",
                "choices": ["A. 3", "B. 4", "C. 5", "D. 6"],
                "answer": "B. 4",
                "explanation": "2 + 2 = 4",
                "difficulty": "easy",
                "tags": ["toán học", "cơ bản"]
            }
        }


class QuestionUpdateRequest(BaseModel):
    """Request update câu hỏi TRẮC NGHIỆM"""
    index: int = Field(..., ge=0, description="Index của câu hỏi cần update")
    question: Question = Field(..., description="Dữ liệu câu hỏi mới")


class QuestionGenerationResponse(BaseModel):
    """Response trả về danh sách câu hỏi TRẮC NGHIỆM"""
    success: bool
    questions: List[Question]
    total: int
    message: Optional[str] = None
