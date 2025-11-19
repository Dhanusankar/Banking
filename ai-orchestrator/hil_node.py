"""
Reusable Human-in-the-Loop (HIL) node component for LangGraph workflows.
Pauses workflow execution, saves state, and waits for human approval/rejection.
Supports automatic resume after approval decision.
"""
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from enum import Enum
import uuid

from checkpoint_store import checkpoint_store
from persistence import persistence


class HILStatus(Enum):
    """HIL approval status types."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class HILDecision:
    """Represents a human decision on a pending action."""
    
    def __init__(
        self,
        approved: bool,
        approver_id: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.approved = approved
        self.approver_id = approver_id
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()


class HILNode:
    """
    Reusable Human-in-the-Loop workflow node.
    
    Usage:
        hil_node = HILNode(
            node_id="transfer_approval",
            approval_message="Transfer requires approval",
            approval_threshold=lambda state: state['amount'] >= 5000
        )
        
        result = hil_node.execute(state)
        
        if result['status'] == 'PENDING_APPROVAL':
            # Wait for human decision
            session_id = result['session_id']
            # Later: hil_node.approve(session_id, approver_id)
    """
    
    def __init__(
        self,
        node_id: str,
        approval_message: str,
        approval_threshold: Callable[[Dict[str, Any]], bool] = None,
        auto_approve: bool = False,
        timeout_seconds: Optional[int] = None
    ):
        """
        Initialize HIL node.
        
        Args:
            node_id: Unique identifier for this HIL node
            approval_message: Message to show when approval is needed
            approval_threshold: Function that returns True if approval is needed
            auto_approve: If True, automatically approve without human input
            timeout_seconds: Optional timeout for approval (not implemented yet)
        """
        self.node_id = node_id
        self.approval_message = approval_message
        self.approval_threshold = approval_threshold or (lambda state: True)
        self.auto_approve = auto_approve
        self.timeout_seconds = timeout_seconds
    
    def execute(
        self,
        state: Dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = "default_user"
    ) -> Dict[str, Any]:
        """
        Execute the HIL node.
        
        Args:
            state: Current workflow state
            session_id: Workflow session ID
            user_id: User requesting the action
        
        Returns:
            Result with status (PENDING_APPROVAL, APPROVED, or BYPASSED)
        """
        # Check if approval is needed
        needs_approval = self.approval_threshold(state)
        
        if not needs_approval or self.auto_approve:
            return {
                "status": "BYPASSED",
                "message": "Approval not required or auto-approved",
                "state": state
            }
        
        # Generate session if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Save checkpoint before pausing
        checkpoint_id = checkpoint_store.save_checkpoint(
            session_id=session_id,
            node_id=self.node_id,
            state=state,
            metadata={
                "user_id": user_id,
                "approval_message": self.approval_message,
                "paused_at": datetime.now().isoformat()
            }
        )
        
        # Create approval request in persistence layer
        approval_id = persistence.create_approval_request(
            session_id=session_id,
            workflow_type="banking",
            request_data=state.get("request_data", {}),
            amount=state.get("amount"),
            recipient=state.get("recipient")
        )
        
        # Update session status to pending approval
        persistence.save_state(session_id, state, status="pending_approval")
        
        return {
            "status": "PENDING_APPROVAL",
            "message": self.approval_message,
            "session_id": session_id,
            "approval_id": approval_id,
            "checkpoint_id": checkpoint_id,
            "node_id": self.node_id,
            "amount": state.get("amount"),
            "recipient": state.get("recipient"),
            "paused_at": datetime.now().isoformat()
        }
    
    def approve(
        self,
        session_id: str,
        approver_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve the pending action and resume workflow.
        
        Args:
            session_id: Workflow session ID
            approver_id: ID of the person approving
            reason: Optional approval reason
        
        Returns:
            Result with resumed state
        """
        # Load checkpoint
        checkpoint = checkpoint_store.load_checkpoint(session_id)
        
        if not checkpoint:
            return {
                "status": "ERROR",
                "error": "No checkpoint found for session"
            }
        
        # Mark as approved in persistence
        # Get approval_id from pending approvals
        approvals = persistence.get_pending_approvals()
        approval_id = None
        for approval in approvals:
            if approval['session_id'] == session_id:
                approval_id = approval['approval_id']
                break
        
        if approval_id:
            persistence.approve_request(approval_id, approver_id)
        
        # Update checkpoint with approval decision
        state = checkpoint['state']
        state['hil_decision'] = {
            "approved": True,
            "approver_id": approver_id,
            "reason": reason,
            "approved_at": datetime.now().isoformat()
        }
        
        # Save new checkpoint
        checkpoint_store.save_checkpoint(
            session_id=session_id,
            node_id=f"{self.node_id}_approved",
            state=state,
            metadata={"approver_id": approver_id}
        )
        
        return {
            "status": "APPROVED",
            "session_id": session_id,
            "state": state,
            "approved_by": approver_id,
            "approved_at": datetime.now().isoformat()
        }
    
    def reject(
        self,
        session_id: str,
        approver_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Reject the pending action and terminate workflow.
        
        Args:
            session_id: Workflow session ID
            approver_id: ID of the person rejecting
            reason: Rejection reason
        
        Returns:
            Result with rejection status
        """
        # Load checkpoint
        checkpoint = checkpoint_store.load_checkpoint(session_id)
        
        if not checkpoint:
            return {
                "status": "ERROR",
                "error": "No checkpoint found for session"
            }
        
        # Mark as rejected in persistence
        approvals = persistence.get_pending_approvals()
        approval_id = None
        for approval in approvals:
            if approval['session_id'] == session_id:
                approval_id = approval['approval_id']
                break
        
        if approval_id:
            persistence.reject_request(approval_id, reason, approver_id)
        
        # Update checkpoint with rejection
        state = checkpoint['state']
        state['hil_decision'] = {
            "approved": False,
            "approver_id": approver_id,
            "reason": reason,
            "rejected_at": datetime.now().isoformat()
        }
        
        # Save final checkpoint
        checkpoint_store.save_checkpoint(
            session_id=session_id,
            node_id=f"{self.node_id}_rejected",
            state=state,
            metadata={"approver_id": approver_id, "reason": reason}
        )
        
        return {
            "status": "REJECTED",
            "session_id": session_id,
            "reason": reason,
            "rejected_by": approver_id,
            "rejected_at": datetime.now().isoformat()
        }


class HILNodeBuilder:
    """Builder pattern for creating HIL nodes with common configurations."""
    
    @staticmethod
    def create_transfer_approval_node(threshold: float = 5000.0) -> HILNode:
        """
        Create a HIL node for money transfer approvals.
        
        Args:
            threshold: Amount above which approval is required
        
        Returns:
            Configured HIL node
        """
        return HILNode(
            node_id="transfer_approval",
            approval_message=f"Transfer requires approval (threshold: ${threshold})",
            approval_threshold=lambda state: state.get("amount", 0) >= threshold
        )
    
    @staticmethod
    def create_loan_approval_node(min_amount: float = 10000.0) -> HILNode:
        """
        Create a HIL node for loan approvals.
        
        Args:
            min_amount: Minimum loan amount requiring approval
        
        Returns:
            Configured HIL node
        """
        return HILNode(
            node_id="loan_approval",
            approval_message=f"Loan requires approval (minimum: ${min_amount})",
            approval_threshold=lambda state: state.get("loan_amount", 0) >= min_amount
        )
    
    @staticmethod
    def create_account_closure_node() -> HILNode:
        """
        Create a HIL node for account closure approvals.
        
        Returns:
            Configured HIL node
        """
        return HILNode(
            node_id="account_closure_approval",
            approval_message="Account closure requires approval",
            approval_threshold=lambda state: True  # Always require approval
        )


# Global HIL node instances for common use cases
transfer_hil_node = HILNodeBuilder.create_transfer_approval_node(threshold=5000.0)
loan_hil_node = HILNodeBuilder.create_loan_approval_node(min_amount=10000.0)
account_closure_hil_node = HILNodeBuilder.create_account_closure_node()
