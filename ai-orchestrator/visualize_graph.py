"""
Generate visual diagram of the Banking LangGraph workflow.
This script prints Mermaid diagram code for visualization.
"""

def visualize_workflow():
    """
    Print Mermaid diagram code for the workflow.
    """
    print("=== LangGraph Workflow Visualization ===\n")
    print("Copy the Mermaid code below to: https://mermaid.live/\n")
    print("="*50)
    print_manual_diagram()

def print_manual_diagram():
    """Print manual Mermaid diagram code"""
    mermaid_code = """
graph TD
    __start__([Start]) --> validate_input
    validate_input --> confidence_check
    
    confidence_check --> |High Confidence| route_confidence{{Route by Intent}}
    confidence_check --> |Low Confidence Transfer| money_transfer_hil
    confidence_check --> |Low Confidence Other| fallback
    
    route_confidence --> |balance_inquiry| balance_inquiry[Balance Inquiry]
    route_confidence --> |money_transfer| money_transfer_prepare
    route_confidence --> |account_statement| account_statement[Account Statement]
    route_confidence --> |loan_inquiry| loan_inquiry[Loan Inquiry]
    route_confidence --> |fallback| fallback[Fallback]
    
    money_transfer_prepare --> route_transfer{{Route Transfer}}
    route_transfer --> |High Value ≥$5000| money_transfer_hil[HIL Approval]
    route_transfer --> |Conversational| money_transfer_hil
    route_transfer --> |Auto-Approve <$5000| money_transfer_execute[Execute Transfer]
    
    money_transfer_hil --> |Approved| money_transfer_execute
    money_transfer_hil --> |Rejected| __end__([End])
    
    balance_inquiry --> __end__
    money_transfer_execute --> __end__
    account_statement --> __end__
    loan_inquiry --> __end__
    fallback --> __end__
    
    style validate_input fill:#e1f5ff
    style confidence_check fill:#fff4e6
    style money_transfer_prepare fill:#e8f5e9
    style money_transfer_hil fill:#ffebee
    style money_transfer_execute fill:#f3e5f5
    style balance_inquiry fill:#e0f2f1
    style __start__ fill:#c8e6c9
    style __end__ fill:#ffcdd2
"""
    print(mermaid_code)
    print("\n" + "="*50)
    print("Copy the above code to: https://mermaid.live/")

def print_ascii_diagram():
    """Print ASCII art diagram"""
    print("\n=== Banking Workflow ASCII Diagram ===\n")
    print("""
    ┌─────────────────┐
    │   USER INPUT    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │  1. validate_input          │
    │  • Call Llama-3 LLM         │
    │  • Extract entities         │
    │  • Merge context            │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │  2. confidence_check        │
    │  • Check confidence ≥ 0.80  │
    │  • Validate completeness    │
    │  • Store partial info       │
    └────────┬────────────────────┘
             │
      ┌──────┴───────┐
      │              │
  Conf < 0.80   Conf ≥ 0.80
      │              │
      ▼              ▼
   ┌─────┐     ┌──────────────┐
   │ HIL │     │ Route Intent │
   │  or │     └──────┬───────┘
   │Fall │            │
   └──┬──┘     ┌──────┼──────┬──────┐
      │        │      │      │      │
      │        ▼      ▼      ▼      ▼
      │    balance transfer stmt  loan
      │        │      │      │      │
      │        │      ▼      │      │
      │        │  ┌───────┐  │      │
      │        │  │prepare│  │      │
      │        │  └───┬───┘  │      │
      │        │      │      │      │
      │        │  ┌───┴────┐ │      │
      │        │  │        │ │      │
      │        │ <$5K    ≥$5K│      │
      │        │  │        │ │      │
      │        │  ▼        ▼ │      │
      │        │ exec     HIL│      │
      │        │  │        │ │      │
      └────────┴──┴────────┴─┴──────┘
                  │
                  ▼
            ┌──────────┐
            │   END    │
            └──────────┘
    
    Legend:
    • HIL = Human-in-the-Loop (Approval Required)
    • exec = money_transfer_execute
    • stmt = account_statement
    • Confidence threshold = 0.80
    • High-value threshold = $5,000
    """)

if __name__ == "__main__":
    print("🔍 Banking Workflow Visualization Tool\n")
    
    # Try to generate visualization
    visualize_workflow()
    
    # Print ASCII diagram
    print_ascii_diagram()
    
    print("\n" + "="*50)
    print("\n📊 Visualization Options:")
    print("1. Open banking_workflow.png (if generated)")
    print("2. Copy Mermaid code to https://mermaid.live/")
    print("3. Use ASCII diagram above")
    print("\n🔧 To enable PNG generation:")
    print("   pip install graphviz")
    print("   or")
    print("   pip install pygraphviz")
