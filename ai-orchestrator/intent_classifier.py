"""Simple rule-based intent classifier with fuzzy matching."""
import re

def classify_intent(message: str) -> str:
    m = message.lower()
    
    # Balance inquiry - with typos
    balance_patterns = [
        r'\bbalance\b',
        r'\bbalanse\b',  # Common typo
        r'\bbalence\b',  # Common typo
        r'\bbalanc\b',   # Common typo
        r'\baccoun?t\s+balance\b',
        r'\bmy\s+balance\b',
        r'\bcheck\s+balance\b',
        r'\bshow\s+balance\b'
    ]
    if any(re.search(pattern, m) for pattern in balance_patterns):
        return "balance_inquiry"
    
    # Money transfer - with typos
    transfer_patterns = [
        r'\btransfer\b',
        r'\btansfer\b',    # Common typo
        r'\btranfer\b',    # Common typo
        r'\btransffer\b',  # Common typo
        r'\btransfar\b',   # Common typo
        r'\bsend\b',
        r'\bsnd\b',        # Common typo
        r'\bpay\b',
        r'\bmove\b',
        r'\bsend\s+money\b',
        r'\bgive\b',
        r'\b\d+\s+to\s+\w+\b'  # Pattern like "5500 to kiran"
    ]
    if any(re.search(pattern, m) for pattern in transfer_patterns):
        return "money_transfer"
    
    # Account statement - with typos
    statement_patterns = [
        r'\bstatement\b',
        r'\bstatment\b',    # Common typo
        r'\bstatemnt\b',    # Common typo
        r'\bstatmnt\b',     # Common typo
        r'\btransactions?\b',
        r'\btransaction\b',
        r'\btransacton\b',  # Common typo
        r'\bhistory\b',
        r'\bhistroy\b',     # Common typo
        r'\brecent\s+activity\b',
        r'\bshow\s+statement\b',
        r'\baccoun?t\s+statement\b'
    ]
    if any(re.search(pattern, m) for pattern in statement_patterns):
        return "account_statement"
    
    # Loan inquiry - with typos
    loan_patterns = [
        r'\bloan\b',
        r'\blon\b',         # Common typo
        r'\blone\b',        # Common typo
        r'\blaon\b',        # Common typo
        r'\bcredit\b',
        r'\bkredit\b',      # Common typo
        r'\beligible\b',
        r'\beligable\b',    # Common typo
        r'\bborrow\b',
        r'\bborow\b',       # Common typo
        r'\bapply\s+for\s+loan\b',
        r'\bloan\s+info\b',
        r'\bloan\s+inquiry\b'
    ]
    if any(re.search(pattern, m) for pattern in loan_patterns):
        return "loan_inquiry"
    
    return "fallback"

