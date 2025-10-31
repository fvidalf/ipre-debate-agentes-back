"""
Document management API routes for the document library system.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlmodel import Session

from app.api.schemas import (
    DocumentLibraryResponse, 
    DocumentsListResponse,
    DocumentUploadResponse
)
from app.models import User
from app.dependencies import get_db, get_current_user
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service() -> DocumentService:
    """Get document service."""
    return DocumentService()


@router.get("", response_model=DocumentsListResponse)
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """List user's documents from their document library."""
    
    if limit > 100:
        limit = 100
    
    documents, total = doc_service.list_user_documents(
        user=current_user,
        db=db,
        limit=limit,
        offset=offset
    )
    
    return DocumentsListResponse(
        documents=[
            DocumentLibraryResponse(
                id=str(doc.id),
                title=doc.title,
                description=doc.description,
                document_type=doc.document_type,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                processing_status=doc.processing_status,
                embedding_status=doc.embedding_status,
                error_message=doc.error_message,
                tags=doc.tags,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            for doc in documents
        ],
        total=total
    )


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    document_type: str = Form("general"),
    tags: str = Form(""),  # Comma-separated tags
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Upload a new document to the user's library."""
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    try:
        document = await doc_service.upload_document(
            file=file,
            title=title,
            description=description,
            document_type=document_type,
            tags=tag_list,
            user=current_user,
            db=db
        )
        
        return DocumentUploadResponse(
            id=str(document.id),
            title=document.title,
            processing_status=document.processing_status,
            embedding_status=document.embedding_status,
            message="Document uploaded successfully"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Failed to upload document: {str(e)}")


@router.get("/{document_id}", response_model=DocumentLibraryResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Get a specific document from user's library."""
    
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(400, "Invalid document ID format")
    
    document = doc_service.get_document(doc_uuid, current_user, db)
    if not document:
        raise HTTPException(404, "Document not found")
    
    return DocumentLibraryResponse(
        id=str(document.id),
        title=document.title,
        description=document.description,
        document_type=document.document_type,
        original_filename=document.original_filename,
        file_size=document.file_size,
        mime_type=document.mime_type,
        processing_status=document.processing_status,
        embedding_status=document.embedding_status,
        error_message=document.error_message,
        tags=document.tags,
        content=document.content,  # Include full content in single-item view
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Delete a document from user's library."""
    
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(400, "Invalid document ID format")
    
    success = doc_service.delete_document(doc_uuid, current_user, db)
    if not success:
        raise HTTPException(404, "Document not found")
    
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Get processing status of a document."""
    
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(400, "Invalid document ID format")
    
    document = doc_service.get_document(doc_uuid, current_user, db)
    if not document:
        raise HTTPException(404, "Document not found")
    
    return {
        "document_id": str(document.id),
        "processing_status": document.processing_status,
        "embedding_status": document.embedding_status,
        "error_message": document.error_message
    }