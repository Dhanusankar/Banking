"""
Persistence layer for workflow state management and Human-in-the-Loop approvals.
Uses SQLite for simplicity - can be upgraded to PostgreSQL for production.
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List
import uuid


class WorkflowPersistence:
    """Manages workflow state persistence and approval tracking."""
    
    def __init__(self, db_path: str = "workflows.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflow sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                workflow_type TEXT,
                state TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Pending approvals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_approvals (
                approval_id TEXT PRIMARY KEY,
                session_id TEXT,
                workflow_type TEXT,
                request_data TEXT,
                status TEXT,
                amount REAL,
                recipient TEXT,
                requested_at TEXT,
                approved_at TEXT,
                approver_id TEXT,
                rejection_reason TEXT,
                FOREIGN KEY (session_id) REFERENCES workflow_sessions(session_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, user_id: str = "default_user", workflow_type: str = "banking") -> str:
        """Create a new workflow session."""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO workflow_sessions 
            (session_id, user_id, workflow_type, state, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, workflow_type, "{}", "active", timestamp, timestamp))
        conn.commit()
        conn.close()
        
        return session_id
    
    def save_state(self, session_id: str, state: Dict, status: str = "active"):
        """Save workflow state."""
        timestamp = datetime.now().isoformat()
        state_json = json.dumps(state)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE workflow_sessions 
            SET state = ?, status = ?, updated_at = ?
            WHERE session_id = ?
        """, (state_json, status, timestamp, session_id))
        conn.commit()
        conn.close()
    
    def load_state(self, session_id: str) -> Optional[Dict]:
        """Load workflow state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT state FROM workflow_sessions WHERE session_id = ?
        """, (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def create_approval_request(
        self, 
        session_id: str, 
        workflow_type: str,
        request_data: Dict,
        amount: float = None,
        recipient: str = None
    ) -> str:
        """Create a pending approval request."""
        approval_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        request_json = json.dumps(request_data)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pending_approvals 
            (approval_id, session_id, workflow_type, request_data, status, 
             amount, recipient, requested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (approval_id, session_id, workflow_type, request_json, "pending",
              amount, recipient, timestamp))
        conn.commit()
        conn.close()
        
        return approval_id
    
    def approve_request(self, approval_id: str, approver_id: str = "admin") -> Dict:
        """Approve a pending request."""
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get request data
        cursor.execute("""
            SELECT session_id, request_data FROM pending_approvals 
            WHERE approval_id = ? AND status = 'pending'
        """, (approval_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"error": "Approval request not found or already processed"}
        
        session_id, request_data = result
        
        # Update approval status
        cursor.execute("""
            UPDATE pending_approvals 
            SET status = 'approved', approver_id = ?, approved_at = ?
            WHERE approval_id = ?
        """, (approver_id, timestamp, approval_id))
        
        # Update session status
        cursor.execute("""
            UPDATE workflow_sessions 
            SET status = 'approved', updated_at = ?
            WHERE session_id = ?
        """, (timestamp, session_id))
        
        conn.commit()
        conn.close()
        
        return {
            "approval_id": approval_id,
            "session_id": session_id,
            "status": "approved",
            "request_data": json.loads(request_data)
        }
    
    def reject_request(self, approval_id: str, reason: str, approver_id: str = "admin") -> Dict:
        """Reject a pending request."""
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE pending_approvals 
            SET status = 'rejected', approver_id = ?, approved_at = ?, rejection_reason = ?
            WHERE approval_id = ? AND status = 'pending'
        """, (approver_id, timestamp, reason, approval_id))
        
        cursor.execute("""
            SELECT session_id FROM pending_approvals WHERE approval_id = ?
        """, (approval_id,))
        result = cursor.fetchone()
        
        if result:
            cursor.execute("""
                UPDATE workflow_sessions 
                SET status = 'rejected', updated_at = ?
                WHERE session_id = ?
            """, (timestamp, result[0]))
        
        conn.commit()
        conn.close()
        
        return {"approval_id": approval_id, "status": "rejected", "reason": reason}
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get all pending approval requests."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT approval_id, session_id, workflow_type, request_data, 
                   amount, recipient, requested_at
            FROM pending_approvals 
            WHERE status = 'pending'
            ORDER BY requested_at DESC
        """)
        results = cursor.fetchall()
        conn.close()
        
        approvals = []
        for row in results:
            approvals.append({
                "approval_id": row[0],
                "session_id": row[1],
                "workflow_type": row[2],
                "request_data": json.loads(row[3]),
                "amount": row[4],
                "recipient": row[5],
                "requested_at": row[6]
            })
        
        return approvals
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get session status and details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, user_id, workflow_type, status, created_at, updated_at
            FROM workflow_sessions 
            WHERE session_id = ?
        """, (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "session_id": result[0],
                "user_id": result[1],
                "workflow_type": result[2],
                "status": result[3],
                "created_at": result[4],
                "updated_at": result[5]
            }
        return None


# Global persistence instance
persistence = WorkflowPersistence()
