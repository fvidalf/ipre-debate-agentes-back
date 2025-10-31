"""
Document service for managing document library operations.
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime

from fastapi import UploadFile, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models import DocumentLibrary, Embedding, User, AgentDocumentAccess
from app.services.file_processing_service import FileProcessingService


class DocumentService:
    """Service for managing document library operations."""
    
    def __init__(self):
        self.file_processor = FileProcessingService()
    
    async def upload_document(
        self,
        file: UploadFile,
        title: str,
        description: Optional[str],
        document_type: str,
        tags: List[str],
        user: User,
        db: Session
    ) -> DocumentLibrary:
        """Upload and process a new document."""
        
        # Process file using FileProcessingService
        text_content, content_hash, file_size, mime_type = await self.file_processor.process_uploaded_file(
            file=file,
            title=title,
            description=description,
            document_type=document_type,
            tags=tags,
            user_id=user.id
        )
        
        # Check for duplicates
        existing_doc = db.exec(
            select(DocumentLibrary)
            .where(DocumentLibrary.owner_user_id == user.id)
            .where(DocumentLibrary.content_hash == content_hash)
        ).first()
        
        if existing_doc:
            raise HTTPException(400, "Document with identical content already exists")
        
        # Create document record
        document = DocumentLibrary(
            owner_user_id=user.id,
            title=title,
            content=text_content,
            document_type=document_type,
            original_filename=file.filename,
            file_size=file_size,
            mime_type=mime_type,
            content_hash=content_hash,
            tags=tags,
            description=description,
            processing_status="completed",
            embedding_status="pending"
        )
        
        try:
            db.add(document)
            db.commit()
            db.refresh(document)
        except IntegrityError:
            db.rollback()
            raise HTTPException(400, "Document with this content already exists")
        
        try:
            self.file_processor.generate_embeddings_efficiently(document, db)
        except Exception as e:
            # Update status but don't fail the upload
            document.embedding_status = "failed"
            document.error_message = str(e)
            db.add(document)
            db.commit()
        
        return document
    
    def list_user_documents(
        self,
        user: User,
        db: Session,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[DocumentLibrary], int]:
        """List documents for a user with pagination."""
        
        # Get total count
        total_stmt = (
            select(DocumentLibrary)
            .where(DocumentLibrary.owner_user_id == user.id)
        )
        total = len(db.exec(total_stmt).all())
        
        # Get paginated results
        stmt = (
            select(DocumentLibrary)
            .where(DocumentLibrary.owner_user_id == user.id)
            .order_by(DocumentLibrary.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        documents = db.exec(stmt).all()
        
        return documents, total
    
    def get_document(
        self,
        document_id: UUID,
        user: User,
        db: Session
    ) -> Optional[DocumentLibrary]:
        """Get a specific document if user owns it."""
        
        stmt = (
            select(DocumentLibrary)
            .where(DocumentLibrary.id == document_id)
            .where(DocumentLibrary.owner_user_id == user.id)
        )
        return db.exec(stmt).first()
    
    def delete_document(
        self,
        document_id: UUID,
        user: User,
        db: Session
    ) -> bool:
        """Delete a document and all related data."""
        
        document = self.get_document(document_id, user, db)
        if not document:
            return False
        
        try:
            # Delete related embeddings
            embedding_stmt = (
                select(Embedding)
                .where(Embedding.source_type == "document")
                .where(Embedding.source_id == document_id)
            )
            embeddings = db.exec(embedding_stmt).all()
            for embedding in embeddings:
                db.delete(embedding)
            
            # Delete agent access records
            access_stmt = (
                select(AgentDocumentAccess)
                .where(AgentDocumentAccess.document_id == document_id)
            )
            access_records = db.exec(access_stmt).all()
            for access_record in access_records:
                db.delete(access_record)
            
            # Delete document
            db.delete(document)
            db.commit()
            return True
            
        except Exception:
            db.rollback()
            raise
    
    async def assign_documents_to_agent(
        self,
        document_ids: List[UUID],
        agent_name: str,
        run_id: UUID,
        db: Session
    ) -> None:
        """Assign documents to an agent for a specific run."""
        
        for document_id in document_ids:
            # Update embeddings to assign to agent
            embedding_stmt = (
                select(Embedding)
                .where(Embedding.source_type == "document")
                .where(Embedding.source_id == document_id)
                .where(Embedding.owner_agent.is_(None))
                .where(Embedding.run_id.is_(None))
            )
            embeddings = db.exec(embedding_stmt).all()
            
            for embedding in embeddings:
                embedding.owner_agent = agent_name
                embedding.run_id = run_id
                db.add(embedding)
            
            # Create access tracking record
            access_record = AgentDocumentAccess(
                run_id=run_id,
                agent_name=agent_name,
                document_id=document_id
            )
            db.add(access_record)
        
        db.commit()
    
    def release_documents_from_run(
        self,
        run_id: UUID,
        db: Session
    ) -> None:
        """Release all documents assigned to agents in a specific run."""
        
        # Reset embeddings back to unassigned state
        embedding_stmt = (
            select(Embedding)
            .where(Embedding.source_type == "document")
            .where(Embedding.run_id == run_id)
        )
        embeddings = db.exec(embedding_stmt).all()
        
        for embedding in embeddings:
            embedding.owner_agent = None
            embedding.run_id = None
            db.add(embedding)
        
        db.commit()