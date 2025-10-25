from sqlalchemy.orm import Session
from models.file_model import UploadedFile
from datetime import datetime

def create_file_record(db: Session, filename: str, original_filename: str, file_path: str, user_id: int, file_size: int = None):
    db_file = UploadedFile(filename=filename, original_filename=original_filename, file_path=file_path, user_id=user_id, file_size=file_size)
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_files_by_user(db: Session, user_id: int):
    return db.query(UploadedFile).filter(UploadedFile.user_id == user_id).order_by(UploadedFile.upload_date.desc()).all()

def get_file_by_id(db: Session, file_id: int):
    return db.query(UploadedFile).filter(UploadedFile.id == file_id).first()

def delete_file_record(db: Session, file_id: int):
    db_file = get_file_by_id(db, file_id)
    if db_file:
        db.delete(db_file)
        db.commit()
        return True
    return False
