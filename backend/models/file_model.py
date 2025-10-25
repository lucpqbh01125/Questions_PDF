from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<UploadedFile(id={self.id}, filename='{self.filename}', user_id={self.user_id})>"
