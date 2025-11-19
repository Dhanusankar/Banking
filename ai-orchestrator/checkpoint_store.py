"""
Production-grade checkpoint storage for LangGraph workflows.
Supports both SQLite (development) and Redis (production) backends.
Handles workflow state persistence, recovery, and session management.
"""
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import uuid


class CheckpointBackend(ABC):
    """Abstract base class for checkpoint storage backends."""
    
    @abstractmethod
    def save(self, session_id: str, checkpoint_data: Dict[str, Any]) -> bool:
        """Save a checkpoint."""
        pass
    
    @abstractmethod
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest checkpoint for a session."""
        pass
    
    @abstractmethod
    def clear(self, session_id: str) -> bool:
        """Clear all checkpoints for a session."""
        pass
    
    @abstractmethod
    def list_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a session."""
        pass


class SQLiteCheckpointBackend(CheckpointBackend):
    """SQLite implementation of checkpoint storage."""
    
    def __init__(self, db_path: str = "checkpoints.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the checkpoints table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                checkpoint_id TEXT UNIQUE NOT NULL,
                node_id TEXT,
                state TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create indexes separately
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session 
            ON checkpoints(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoint 
            ON checkpoints(checkpoint_id)
        """)
        
        conn.commit()
        conn.close()
    
    def save(self, session_id: str, checkpoint_data: Dict[str, Any]) -> bool:
        """Save a checkpoint to SQLite."""
        try:
            checkpoint_id = checkpoint_data.get("checkpoint_id", str(uuid.uuid4()))
            node_id = checkpoint_data.get("node_id")
            state = json.dumps(checkpoint_data.get("state", {}))
            metadata = json.dumps(checkpoint_data.get("metadata", {}))
            created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO checkpoints 
                (session_id, checkpoint_id, node_id, state, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, checkpoint_id, node_id, state, metadata, created_at))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
            return False
    
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest checkpoint for a session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT checkpoint_id, node_id, state, metadata, created_at
                FROM checkpoints
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "checkpoint_id": row[0],
                    "node_id": row[1],
                    "state": json.loads(row[2]),
                    "metadata": json.loads(row[3]),
                    "created_at": row[4]
                }
            return None
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            return None
    
    def clear(self, session_id: str) -> bool:
        """Clear all checkpoints for a session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM checkpoints WHERE session_id = ?", (session_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error clearing checkpoints: {e}")
            return False
    
    def list_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT checkpoint_id, node_id, state, metadata, created_at
                FROM checkpoints
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "checkpoint_id": row[0],
                    "node_id": row[1],
                    "state": json.loads(row[2]),
                    "metadata": json.loads(row[3]),
                    "created_at": row[4]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Error listing checkpoints: {e}")
            return []


class RedisCheckpointBackend(CheckpointBackend):
    """Redis implementation of checkpoint storage for production."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 86400):
        """
        Initialize Redis backend.
        
        Args:
            redis_url: Redis connection URL
            ttl: Time-to-live for checkpoints in seconds (default: 24 hours)
        """
        try:
            import redis
            self.redis_client = redis.from_url(redis_url)
            self.ttl = ttl
        except ImportError:
            raise ImportError("redis package not installed. Run: pip install redis")
    
    def _get_key(self, session_id: str, suffix: str = "latest") -> str:
        """Generate Redis key for a checkpoint."""
        return f"checkpoint:{session_id}:{suffix}"
    
    def save(self, session_id: str, checkpoint_data: Dict[str, Any]) -> bool:
        """Save a checkpoint to Redis."""
        try:
            checkpoint_id = checkpoint_data.get("checkpoint_id", str(uuid.uuid4()))
            checkpoint_data["checkpoint_id"] = checkpoint_id
            checkpoint_data["created_at"] = datetime.now().isoformat()
            
            # Save latest checkpoint
            latest_key = self._get_key(session_id, "latest")
            self.redis_client.setex(
                latest_key,
                self.ttl,
                json.dumps(checkpoint_data)
            )
            
            # Save to history list
            history_key = self._get_key(session_id, "history")
            self.redis_client.rpush(history_key, json.dumps(checkpoint_data))
            self.redis_client.expire(history_key, self.ttl)
            
            return True
        except Exception as e:
            print(f"Error saving checkpoint to Redis: {e}")
            return False
    
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest checkpoint from Redis."""
        try:
            key = self._get_key(session_id, "latest")
            data = self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error loading checkpoint from Redis: {e}")
            return None
    
    def clear(self, session_id: str) -> bool:
        """Clear all checkpoints for a session from Redis."""
        try:
            latest_key = self._get_key(session_id, "latest")
            history_key = self._get_key(session_id, "history")
            
            self.redis_client.delete(latest_key, history_key)
            return True
        except Exception as e:
            print(f"Error clearing checkpoints from Redis: {e}")
            return False
    
    def list_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a session from Redis."""
        try:
            history_key = self._get_key(session_id, "history")
            data_list = self.redis_client.lrange(history_key, 0, -1)
            
            return [json.loads(data) for data in data_list]
        except Exception as e:
            print(f"Error listing checkpoints from Redis: {e}")
            return []


class CheckpointStore:
    """
    High-level checkpoint storage manager.
    Automatically handles serialization, metadata, and backend switching.
    """
    
    def __init__(self, backend: CheckpointBackend = None):
        """
        Initialize checkpoint store.
        
        Args:
            backend: CheckpointBackend instance (defaults to SQLite)
        """
        self.backend = backend or SQLiteCheckpointBackend()
    
    def save_checkpoint(
        self,
        session_id: str,
        node_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a workflow checkpoint.
        
        Args:
            session_id: Unique session identifier
            node_id: Current node in the workflow graph
            state: Complete workflow state
            metadata: Optional metadata (e.g., user info, timestamps)
        
        Returns:
            checkpoint_id: Unique checkpoint identifier
        """
        checkpoint_id = str(uuid.uuid4())
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "node_id": node_id,
            "state": state,
            "metadata": metadata or {}
        }
        
        success = self.backend.save(session_id, checkpoint_data)
        
        if success:
            print(f"✓ Checkpoint saved: {node_id} (session: {session_id[:8]}...)")
            return checkpoint_id
        else:
            print(f"✗ Failed to save checkpoint: {node_id}")
            return None
    
    def load_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the latest checkpoint for a session.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Checkpoint data or None if not found
        """
        checkpoint = self.backend.load(session_id)
        
        if checkpoint:
            print(f"✓ Checkpoint loaded: {checkpoint['node_id']} (session: {session_id[:8]}...)")
        else:
            print(f"✗ No checkpoint found for session: {session_id[:8]}...")
        
        return checkpoint
    
    def clear_checkpoint(self, session_id: str) -> bool:
        """
        Clear all checkpoints for a session.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            True if successful
        """
        success = self.backend.clear(session_id)
        
        if success:
            print(f"✓ Checkpoints cleared for session: {session_id[:8]}...")
        
        return success
    
    def get_checkpoint_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all checkpoints for a session in chronological order.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            List of checkpoint data
        """
        return self.backend.list_checkpoints(session_id)
    
    def restore_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore workflow state from the latest checkpoint.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Workflow state or None if no checkpoint exists
        """
        checkpoint = self.load_checkpoint(session_id)
        
        if checkpoint:
            return checkpoint.get("state")
        
        return None


# Global checkpoint store instances
checkpoint_store = CheckpointStore(SQLiteCheckpointBackend())

# For production with Redis, uncomment:
# checkpoint_store = CheckpointStore(RedisCheckpointBackend(redis_url="redis://localhost:6379"))
