from openai import OpenAI
from typing import List, Dict, Any
import logging
import json
import time

logger = logging.getLogger(__name__)

class VectorStoreManager:
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.vector_store_id = None
        self.assistant_id = None
    
    def create_vector_store(self, name: str = "PDF Documents") -> str:

        vector_store = self.client.beta.vector_stores.create(name=name)
        self.vector_store_id = vector_store.id
        logger.info(f"✅ Đã tạo Vector Store: {vector_store.id}")
        return vector_store.id
    
    def upload_file_to_vector_store(self, file_path: str) -> str:

        with open(file_path, "rb") as f:
            file = self.client.files.create(file=f, purpose="assistants")
        
        self.client.beta.vector_stores.files.create(
            vector_store_id=self.vector_store_id,
            file_id=file.id
        )
        
        logger.info(f"✅ Đã upload file {file_path} (ID: {file.id})")
        return file.id
    
    def upload_file_bytes(self, file_bytes: bytes, filename: str) -> str:

        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        try:
            file_id = self.upload_file_to_vector_store(tmp_path)
            return file_id
        finally:
            os.unlink(tmp_path)
    
    def create_assistant(
        self,
        model: str = "gpt-4-turbo-preview",
        instructions: str = None
    ) -> str:

        if not instructions:
            instructions = (
                "Bạn là chuyên gia tạo câu hỏi từ tài liệu. "
                "CHỈ tạo câu hỏi dựa trên nội dung trong files được cung cấp. "
                "KHÔNG bịa đặt thông tin ngoài tài liệu. "
                "Khi trả về câu hỏi, sử dụng format JSON array: "
                '[{"question":"...", "type":"mcq", "choices":["A","B","C","D"], "answer":"..."}]'
            )
        
        assistant = self.client.beta.assistants.create(
            name="Trợ lý tạo câu hỏi",
            instructions=instructions,
            model=model,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [self.vector_store_id]
                }
            }
        )
        self.assistant_id = assistant.id
        logger.info(f"✅ Đã tạo Assistant: {assistant.id}")
        return assistant.id
    
    def generate_questions(self, prompt: str, max_retries: int = 3) -> List[Dict[str, Any]]:

        if not self.assistant_id:
            raise ValueError("Chưa tạo Assistant. Gọi create_assistant() trước.")
        
        for attempt in range(max_retries):
            try:

                thread = self.client.beta.threads.create()
                
                self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=prompt
                )
                
                logger.info(f" Đang chạy Assistant (attempt {attempt + 1})...")
                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id,
                    timeout=120  
                )
                
                if run.status == "completed":
                    messages = self.client.beta.threads.messages.list(thread_id=thread.id)
                    response = messages.data[0].content[0].text.value
                    
                    logger.info(f" Received response: {response[:200]}...")

                    questions = self._parse_questions_from_response(response)
                    
                    if questions:
                        logger.info(f" Tạo được {len(questions)} câu hỏi")
                        return questions
                    else:
                        logger.warning("Không tìm thấy câu hỏi trong response")
                        
                elif run.status == "failed":
                    logger.error(f"Run failed: {run.last_error}")
                    
                else:
                    logger.warning(f"Run status: {run.status}")
                
            except Exception as e:
                logger.error(f"Lỗi khi tạo câu hỏi (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        return []
    
    def _parse_questions_from_response(self, response: str) -> List[Dict[str, Any]]:

        response = response.strip()
        for marker in ["```json", "```"]:
            if response.startswith(marker):
                response = response[len(marker):].lstrip()
        if response.endswith("```"):
            response = response[:-3].rstrip()
        
        start_idx = response.find('[')
        end_idx = response.rfind(']')
        
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx:end_idx + 1]
            try:
                questions = json.loads(json_str)
                if isinstance(questions, list):
                    return questions
            except json.JSONDecodeError as e:
                logger.error(f"Lỗi parse JSON: {str(e)}")
        
        return []
    
    def list_files_in_vector_store(self) -> List[Dict]:
        """Liệt kê các files trong Vector Store"""
        if not self.vector_store_id:
            return []
        
        files = self.client.beta.vector_stores.files.list(
            vector_store_id=self.vector_store_id
        )
        
        return [
            {
                "id": f.id,
                "created_at": f.created_at,
                "status": f.status
            }
            for f in files.data
        ]
    
    def delete_vector_store(self):
        """Xóa Vector Store"""
        if self.vector_store_id:
            self.client.beta.vector_stores.delete(self.vector_store_id)
            logger.info(f" Đã xóa Vector Store: {self.vector_store_id}")
            self.vector_store_id = None
    
    def delete_assistant(self):
        """Xóa Assistant"""
        if self.assistant_id:
            self.client.beta.assistants.delete(self.assistant_id)
            logger.info(f" Đã xóa Assistant: {self.assistant_id}")
            self.assistant_id = None
