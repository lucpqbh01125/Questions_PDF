from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from sqlalchemy.orm import Session
import asyncio
import os
import uuid
from datetime import timedelta, datetime
from config.settings import settings
from config.database import get_db, init_db
from services.pdf_utils import extract_text_from_pdf, chunk_text
from services.ai_utils import generate_questions_from_text, validate_question_relevance, check_hallucination
from services.data_store import question_store
from services.auth import create_access_token, get_current_user
from models.question_model import QuestionUpdateRequest
from models.user_model import User
from schemas.user import UserCreate, UserLogin, Token, User as UserSchema
from crud.user_crud import create_user, authenticate_user, get_user_by_username
from crud.file_crud import create_file_record, get_files_by_user

app = FastAPI(title="PDF Question Generator API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "version": "2.0.0",
        "questions_count": question_store.count()
    }

@app.post("/register", response_model=UserSchema)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản mới"""
    # Kiểm tra username đã tồn tại chưa
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username đã tồn tại"
        )
    
    # Tạo user mới
    new_user = create_user(db=db, user=user)
    
    return UserSchema(
        id=new_user.id,
        full_name=new_user.full_name,
        username=new_user.username
    )

@app.post("/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập"""
    # Xác thực user
    user = authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Username hoặc password không đúng"
        )
    
    # Tạo access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserSchema(
            id=user.id,
            full_name=user.full_name,
            username=user.username
        )
    )

@app.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại"""
    return UserSchema(
        id=current_user.id,
        full_name=current_user.full_name,
        username=current_user.username
    )

@app.get("/my-files")
async def get_my_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    files = get_files_by_user(db, current_user.id)
    
    return {
        "success": True,
        "files": [
            {
                "id": file.id,
                "filename": file.filename,
                "original_filename": file.original_filename,
                "file_path": file.file_path,
                "upload_date": file.upload_date.isoformat() if file.upload_date else None,
                "file_size": file.file_size
            }
            for file in files
        ]
    }

@app.get("/check-duplicate-file")
async def check_duplicate_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kiểm tra xem file có trùng tên không"""
    from sqlalchemy import and_
    from models.file_model import UploadedFile
    
    existing = db.query(UploadedFile).filter(
        and_(
            UploadedFile.original_filename == filename,
            UploadedFile.user_id == current_user.id
        )
    ).first()
    
    return {
        "duplicate": existing is not None,
        "file_id": existing.id if existing else None
    }


@app.delete("/delete-file/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa file đã tải lên (cả database và file thật)"""
    from crud.file_crud import get_file_by_id, delete_file_record
    
    print(f"🗑️ DELETE request for file_id: {file_id}, user: {current_user.username}")
    
    # Lấy thông tin file
    file_record = get_file_by_id(db, file_id)
    
    if not file_record:
        raise HTTPException(status_code=404, detail="Không tìm thấy file")
    
    if file_record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa file này")
    
    if os.path.exists(file_record.file_path):
        try:
            os.remove(file_record.file_path)
        except Exception as e:
            pass
    
    delete_file_record(db, file_id)
    
    return {
        "success": True,
        "message": f"Đã xóa file {file_record.original_filename}"
    }


@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(..., description="File PDF cần xử lý"),
    prompt: str = Form(..., description="Yêu cầu tạo câu hỏi"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF")
    
    try:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("uploads", unique_filename)
        
        file_content = await file.read()
        os.makedirs("uploads", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        file_record = create_file_record(
            db=db,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            user_id=current_user.id,
            file_size=len(file_content)
        )
        
        # Reset file pointer để đọc lại
        await file.seek(0)
        
        text = await extract_text_from_pdf(file)
        
        if len(text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Văn bản quá ngắn hoặc không đủ nội dung để tạo câu hỏi"
            )
        
        chunks = chunk_text(text, max_chars=settings.max_chunk_chars, overlap=settings.chunk_overlap)
        
        all_questions = []
        
        tasks = [generate_questions_from_text(chunk, prompt, idx) for idx, chunk in enumerate(chunks)]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                if isinstance(result, HTTPException):
                    if result.status_code in [401, 429]:
                        raise result
                    continue
                continue
            
            if isinstance(result, list):
                all_questions.extend(result)
        
        if len(all_questions) == 0:
            error_detail = (
                "Không tạo được câu hỏi nào từ {0} chunks.".format(len(chunks)) +
                " Nguyên nhân có thể: " +
                "1. Văn bản PDF quá ngắn hoặc không chứa nội dung phù hợp, " +
                "2. OpenAI API không hoặc bị lỗi tạm thời, " +
                "3. Yêu cầu không rõ ràng (prompt). " +
                "Hãy thử với PDF khác hoặc nhập lại yêu cầu cụ thể hơn."
            )
            raise HTTPException(status_code=400, detail=error_detail)
        
        all_questions = check_hallucination(all_questions, text)
        
        if len(all_questions) == 0:
            raise HTTPException(
                status_code=400,
                detail="AI không thể tạo câu hỏi chính xác từ tài liệu này. Hãy thử: 1) PDF rõ ràng hơn, 2) Prompt cụ thể hơn, 3) Dùng model tốt hơn (gpt-4)"
            )
        
        validate_question_relevance(all_questions, text, threshold=0.7)
        question_store.set_all(all_questions)
        
        return JSONResponse({
            "success": True,
            "questions": all_questions,
            "total": len(all_questions),
            "message": f"Đã tạo {len(all_questions)} câu hỏi từ {len(chunks)} phần văn bản"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

@app.get("/questions")
async def get_questions():
    questions = question_store.get_all()
    return JSONResponse({
        "questions": questions,
        "total": len(questions)
    })


@app.get("/questions/search")
async def search_questions(keyword: str):

    results = question_store.search(keyword)
    return JSONResponse({
        "results": results,
        "count": len(results),
        "keyword": keyword
    })


@app.post("/update-question")
async def update_question(data: QuestionUpdateRequest):

    success = question_store.update(data.index, data.question.dict())
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Index {data.index} không hợp lệ"
        )
    
    return JSONResponse({"success": True})


@app.delete("/question/{index}")
async def delete_question(index: int):

    success = question_store.delete(index)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Index {index} không hợp lệ"
        )
    
    return JSONResponse({"success": True})


@app.delete("/questions/clear")
async def clear_all_questions():
    count = question_store.count()
    question_store.clear()
    
    return JSONResponse({
        "success": True,
        "message": f"Đã xóa {count} câu hỏi"
    })

@app.get("/my-files")
async def get_my_files(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lấy danh sách file của user hiện tại"""
    files = get_files_by_user(db, current_user.id)
    
    return JSONResponse({
        "success": True,
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "original_filename": f.original_filename,
                "file_path": f.file_path,
                "upload_date": f.upload_date.isoformat() if f.upload_date else None,
                "file_size": f.file_size
            }
            for f in files
        ]
    })


@app.post("/generate-from-file")
async def generate_from_file(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tạo câu hỏi từ file đã tải lên trước đó"""
    file_id = data.get('file_id')
    prompt = data.get('prompt')
    
    if not file_id or not prompt:
        raise HTTPException(status_code=400, detail="Thiếu file_id hoặc prompt")
    
    # Lấy file từ database
    from crud.file_crud import get_file_by_id
    file_record = get_file_by_id(db, file_id)
    
    if not file_record:
        raise HTTPException(status_code=404, detail="Không tìm thấy file")
    
    if file_record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập file này")
    
    try:
        if not os.path.exists(file_record.file_path):
            raise HTTPException(status_code=404, detail="File không tồn tại trên hệ thống")
        
        with open(file_record.file_path, 'rb') as f:
            from io import BytesIO
            pdf_bytes = BytesIO(f.read())
            
            class FakeUploadFile:
                def __init__(self, file_bytes, filename):
                    self.file = file_bytes
                    self.filename = filename
                
                async def read(self):
                    return self.file.read()
                
                async def seek(self, position):
                    return self.file.seek(position)
            
            fake_file = FakeUploadFile(pdf_bytes, file_record.original_filename)
            text = await extract_text_from_pdf(fake_file)
        
        if len(text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Văn bản quá ngắn hoặc không đủ nội dung để tạo câu hỏi"
            )
        
        # Chia thành chunks
        chunks = chunk_text(
            text, max_chars=settings.max_chunk_chars, overlap=settings.chunk_overlap
        )
        
        all_questions = []
        
        tasks = [generate_questions_from_text(chunk, prompt, idx) for idx, chunk in enumerate(chunks)]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            
            if isinstance(result, list):
                all_questions.extend(result)
        
        if len(all_questions) == 0:
            raise HTTPException(status_code=400, detail="Không tạo được câu hỏi nào. Vui lòng thử lại hoặc nhập prompt khác.")
        
        all_questions = check_hallucination(all_questions, text)
        
        if len(all_questions) == 0:
            raise HTTPException(status_code=400, detail="Tất cả câu hỏi đều bị nghi ngờ hallucination (không dựa vào tài liệu)")
        
        question_store.set_all(all_questions)
        
        return JSONResponse({
            "success": True,
            "questions": all_questions,
            "total": len(all_questions),
            "message": f"Đã tạo {len(all_questions)} câu hỏi từ file {file_record.original_filename}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

@app.delete("/vector-store/clear")
async def clear_vector_store():
    try:
        count = question_store.count()
        question_store.clear()
        
        return JSONResponse({
            "success": True,
            "message": f"Đã xóa {count} câu hỏi từ Vector Store"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xóa Vector Store: {str(e)}")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info"
    )

