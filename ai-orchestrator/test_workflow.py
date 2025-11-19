from persistence import persistence

# Check pending approvals
approvals = persistence.get_pending_approvals()
print(f"\n✅ Pending approvals: {len(approvals)}\n")

for a in approvals:
    print(f"Approval ID: {a['approval_id']}")
    print(f"  Amount: ${a['amount']}")
    print(f"  Recipient: {a['recipient']}")
    print(f"  Session: {a['session_id']}")
    print(f"  Requested: {a['requested_at']}")
    print()

# Test approval
if approvals:
    approval_id = approvals[0]['approval_id']
    print(f"\n🔄 Testing approval for: {approval_id}")
    result = persistence.approve_request(approval_id, "test_manager")
    print(f"✅ Approval result: {result['status']}")
    print(f"Session ID: {result['session_id']}")
    
    # Check again
    remaining = persistence.get_pending_approvals()
    print(f"\n✅ Remaining pending approvals: {len(remaining)}")
