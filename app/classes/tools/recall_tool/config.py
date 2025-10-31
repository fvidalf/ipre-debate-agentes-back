from typing import Dict, Any, List
from uuid import UUID

class RecallToolConfig:
    def __init__(
        self,
        uses_documents: bool = False,
        uses_notes: bool = False,
        document_ids: List[UUID] = None,
    ):
        self.uses_documents = uses_documents
        self.uses_notes = uses_notes
        self.document_ids = document_ids or []

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'RecallToolConfig':
        # Parse document IDs from config
        document_ids = []
        if config.get('document_ids'):
            for doc_id in config['document_ids']:
                try:
                    document_ids.append(UUID(doc_id))
                except (ValueError, TypeError):
                    # Skip invalid UUIDs
                    pass
        
        return cls(
            uses_documents=config.get('documents_tool', {}).get('enabled', False),
            uses_notes=config.get('notes_tool', {}).get('enabled', False),
            document_ids=document_ids,
        )