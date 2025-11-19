"""
Session management for workflow execution.
Handles session lifecycle, conversation history, and idempotent execution.
"""
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from checkpoint_store import checkpoint_store
from persistence import persistence


class SessionStatus(Enum):
    """Session status types."""
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ConversationMessage:
    """Represents a single message in a conversation."""
    
    def __init__(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class WorkflowSession:
    """
    Manages a workflow execution session.
    Maintains state, conversation history, and execution context.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: str = "default_user",
        workflow_type: str = "banking"
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.workflow_type = workflow_type
        self.status = SessionStatus.ACTIVE
        self.conversation_history: List[ConversationMessage] = []
        self.workflow_state: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        self.current_node: Optional[str] = None
        self.execution_count: int = 0
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to conversation history."""
        message = ConversationMessage(role, content, metadata)
        self.conversation_history.append(message)
        self._update_activity()
    
    def update_state(self, state: Dict[str, Any], node_id: Optional[str] = None):
        """Update workflow state."""
        self.workflow_state.update(state)
        if node_id:
            self.current_node = node_id
        self._update_activity()
    
    def set_status(self, status: SessionStatus):
        """Update session status."""
        self.status = status
        self._update_activity()
    
    def _update_activity(self):
        """Update last activity timestamp."""
        self.metadata["last_activity"] = datetime.now().isoformat()
    
    def increment_execution(self):
        """Increment execution counter for idempotency tracking."""
        self.execution_count += 1
    
    def is_idempotent_execution(self) -> bool:
        """Check if this is a repeated execution (for idempotency)."""
        return self.execution_count > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "workflow_type": self.workflow_type,
            "status": self.status.value,
            "conversation_history": [msg.to_dict() for msg in self.conversation_history],
            "workflow_state": self.workflow_state,
            "metadata": self.metadata,
            "current_node": self.current_node,
            "execution_count": self.execution_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowSession':
        """Deserialize session from dictionary."""
        session = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            workflow_type=data["workflow_type"]
        )
        session.status = SessionStatus(data["status"])
        session.conversation_history = [
            ConversationMessage(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata", {})
            )
            for msg in data.get("conversation_history", [])
        ]
        session.workflow_state = data.get("workflow_state", {})
        session.metadata = data.get("metadata", {})
        session.current_node = data.get("current_node")
        session.execution_count = data.get("execution_count", 0)
        return session


class SessionManager:
    """
    Manages workflow sessions across the application.
    Provides session CRUD operations and lifecycle management.
    """
    
    def __init__(self):
        self._active_sessions: Dict[str, WorkflowSession] = {}
    
    def create_session(
        self,
        user_id: str = "default_user",
        workflow_type: str = "banking"
    ) -> WorkflowSession:
        """
        Create a new workflow session.
        
        Args:
            user_id: User identifier
            workflow_type: Type of workflow
        
        Returns:
            New WorkflowSession instance
        """
        session = WorkflowSession(user_id=user_id, workflow_type=workflow_type)
        self._active_sessions[session.session_id] = session
        
        # Create session in persistence layer
        persistence.create_session(user_id, workflow_type)
        
        print(f"✓ Session created: {session.session_id[:8]}... (user: {user_id})")
        return session
    
    def get_session(self, session_id: str) -> Optional[WorkflowSession]:
        """
        Get an existing session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            WorkflowSession or None if not found
        """
        # Check in-memory cache first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        
        # Try to restore from checkpoint
        checkpoint = checkpoint_store.load_checkpoint(session_id)
        if checkpoint:
            session = WorkflowSession.from_dict(checkpoint.get("state", {}))
            self._active_sessions[session_id] = session
            print(f"✓ Session restored from checkpoint: {session_id[:8]}...")
            return session
        
        # Try to load from persistence
        session_data = persistence.get_session_status(session_id)
        if session_data:
            # Reconstruct basic session from persistence data
            session = WorkflowSession(
                session_id=session_id,
                user_id=session_data.get("user_id", "default_user"),
                workflow_type=session_data.get("workflow_type", "banking")
            )
            session.status = SessionStatus(session_data.get("status", "active"))
            self._active_sessions[session_id] = session
            print(f"✓ Session loaded from persistence: {session_id[:8]}...")
            return session
        
        print(f"✗ Session not found: {session_id[:8]}...")
        return None
    
    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: str = "default_user",
        workflow_type: str = "banking"
    ) -> WorkflowSession:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Optional session identifier
            user_id: User identifier
            workflow_type: Type of workflow
        
        Returns:
            WorkflowSession instance
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        return self.create_session(user_id, workflow_type)
    
    def save_session(self, session: WorkflowSession):
        """
        Persist session state.
        
        Args:
            session: WorkflowSession to save
        """
        # Save to checkpoint store
        checkpoint_store.save_checkpoint(
            session_id=session.session_id,
            node_id=session.current_node or "session_state",
            state=session.to_dict(),
            metadata=session.metadata
        )
        
        # Save to persistence layer
        persistence.save_state(
            session_id=session.session_id,
            state=session.workflow_state,
            status=session.status.value
        )
        
        print(f"✓ Session saved: {session.session_id[:8]}...")
    
    def delete_session(self, session_id: str):
        """
        Delete a session and its associated data.
        
        Args:
            session_id: Session identifier
        """
        # Remove from active sessions
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        
        # Clear checkpoints
        checkpoint_store.clear_checkpoint(session_id)
        
        print(f"✓ Session deleted: {session_id[:8]}...")
    
    def resume_session(self, session_id: str) -> Optional[WorkflowSession]:
        """
        Resume a paused session from checkpoint.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Restored WorkflowSession or None
        """
        session = self.get_session(session_id)
        
        if not session:
            print(f"✗ Cannot resume - session not found: {session_id[:8]}...")
            return None
        
        if session.status != SessionStatus.PENDING_APPROVAL:
            print(f"✗ Cannot resume - session not pending approval: {session_id[:8]}...")
            return None
        
        print(f"✓ Session ready for resume: {session_id[:8]}...")
        return session
    
    def get_active_sessions(self, user_id: Optional[str] = None) -> List[WorkflowSession]:
        """
        Get all active sessions, optionally filtered by user.
        
        Args:
            user_id: Optional user identifier to filter by
        
        Returns:
            List of active WorkflowSession instances
        """
        sessions = list(self._active_sessions.values())
        
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        
        return sessions
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Remove old inactive sessions from memory.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        from datetime import timedelta
        
        current_time = datetime.now()
        to_remove = []
        
        for session_id, session in self._active_sessions.items():
            last_activity = datetime.fromisoformat(session.metadata["last_activity"])
            age = current_time - last_activity
            
            if age > timedelta(hours=max_age_hours):
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self._active_sessions[session_id]
            print(f"✓ Cleaned up old session: {session_id[:8]}...")
        
        print(f"✓ Cleanup complete: {len(to_remove)} sessions removed")


# Global session manager instance
session_manager = SessionManager()
