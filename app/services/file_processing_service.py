"""
File processing service for handling document content extraction, chunking, and embedding generation.
"""

import hashlib
import mimetypes
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from io import BytesIO

from fastapi import UploadFile, HTTPException
from sqlmodel import Session
import numpy as np

from app.models import DocumentLibrary, Embedding
from app.services.embedding_service import get_embedding_service


class FileProcessingService:
    """Service for processing uploaded files and generating embeddings efficiently."""
    
    def __init__(self):
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.supported_mime_types = {
            'text/plain',
            'text/markdown',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
    
    async def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        
        if not file.filename:
            raise HTTPException(400, "No filename provided")
        
        if file.content_type not in self.supported_mime_types:
            raise HTTPException(400, f"Unsupported file type: {file.content_type}")
        
        # Check file size (approximate)
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Seek back to start
        
        if size > self.max_file_size:
            raise HTTPException(400, f"File too large. Maximum size: {self.max_file_size} bytes")
    
    def calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    async def extract_text_content(self, content_bytes: bytes, mime_type: str) -> str:
        """Extract text content from uploaded file."""
        
        if mime_type == 'text/plain' or mime_type == 'text/markdown':
            return content_bytes.decode('utf-8')
        
        elif mime_type == 'application/pdf':
            try:
                import PyPDF2
                from io import BytesIO
                
                pdf_reader = PyPDF2.PdfReader(BytesIO(content_bytes))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
            except ImportError:
                raise HTTPException(400, "PDF processing not available. Please upload plain text files.")
            except Exception as e:
                raise HTTPException(400, f"Failed to extract text from PDF: {str(e)}")
        
        else:
            raise HTTPException(400, f"Text extraction not implemented for {mime_type}")
    
    def chunk_text(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """Chunk text into smaller pieces for embedding."""
        
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > max_chunk_size and current_chunk:
                # Finish current chunk
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += word_size
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def generate_embeddings_efficiently(self, document: DocumentLibrary, db: Session) -> None:
        """Generate embeddings for document content using the provider's built-in batching."""
        
        document.embedding_status = "processing"
        db.add(document)
        db.commit()
        
        try:
            # Get embedding service
            embedding_service = get_embedding_service()
            
            # Chunk document if needed
            chunks = self.chunk_text(document.content, max_chunk_size=1000)
            
            # Generate embeddings efficiently - the embed method handles batching internally
            all_embeddings = embedding_service.encode(chunks)
            
            # Convert to list format for storage
            if len(chunks) == 1:
                # Single chunk case - encode returns 2D array with 1 row
                embeddings_list = [all_embeddings[0].tolist()]
            else:
                # Multiple chunks - encode returns 2D array with multiple rows
                embeddings_list = [embedding.tolist() for embedding in all_embeddings]
            
            # Store all embeddings in batch
            embedding_objects = []
            for i, (chunk, embedding_vector) in enumerate(zip(chunks, embeddings_list)):
                embedding = Embedding(
                    source_type="document",
                    source_id=document.id,
                    text_content=chunk,
                    visibility="private",
                    owner_agent=None,  # Unassigned
                    run_id=None,  # Unassigned
                    embedding=embedding_vector,
                    embedding_model=embedding_service.model_name,
                    chunk_index=i if len(chunks) > 1 else None,
                    chunk_start=None,  # Could calculate if needed
                    chunk_end=None,
                    extra_metadata={
                        "document_title": document.title,
                        "document_type": document.document_type,
                        "total_chunks": len(chunks)
                    }
                )
                embedding_objects.append(embedding)
            
            # Add all embeddings to session in batch
            for embedding in embedding_objects:
                db.add(embedding)
            
            document.embedding_status = "completed"
            db.add(document)
            db.commit()
            
        except Exception as e:
            document.embedding_status = "failed"
            document.error_message = str(e)
            db.add(document)
            db.commit()
            raise
    
    async def process_uploaded_file(
        self,
        file: UploadFile,
        title: str,
        description: Optional[str],
        document_type: str,
        tags: List[str],
        user_id: UUID
    ) -> Tuple[str, str, int, str]:
        """
        Process an uploaded file and return extracted information.
        
        Returns:
            Tuple of (text_content, content_hash, file_size, mime_type)
        """
        # Validate file
        await self.validate_file(file)
        
        # Read file content
        content_bytes = await file.read()
        content_hash = self.calculate_hash(content_bytes)
        
        # Extract text content
        text_content = await self.extract_text_content(content_bytes, file.content_type)
        
        return text_content, content_hash, len(content_bytes), file.content_type