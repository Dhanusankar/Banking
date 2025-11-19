package com.banking.service;

import com.banking.dto.BalanceResponse;
import com.banking.dto.TransferRequest;
import com.banking.dto.TransferResponse;
import com.banking.model.Account;
import jakarta.annotation.PostConstruct;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

/**
 * Simple in-memory bank service. Not thread-safe for production but fine for POC.
 */
@Service
public class BankService {
    private final Map<String, Account> accounts = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        // Seed some accounts
        accounts.put("123", new Account("123", 50000.00));
        accounts.put("kiran", new Account("kiran", 1000.00));
    }

    public BalanceResponse getBalance(String accountId) {
        Account a = accounts.get(accountId);
        if (a == null) {
            throw new IllegalArgumentException("Account not found: " + accountId);
        }
        return new BalanceResponse(a.getAccountId(), a.getBalance());
    }

    public TransferResponse transfer(TransferRequest req) {
        Account from = accounts.get(req.getFromAccount());
        Account to = accounts.get(req.getToAccount());

        if (from == null) {
            return new TransferResponse(false, "From account not found: " + req.getFromAccount());
        }
        if (to == null) {
            return new TransferResponse(false, "To account not found: " + req.getToAccount());
        }
        if (req.getAmount() <= 0) {
            return new TransferResponse(false, "Amount must be greater than 0");
        }
        if (from.getBalance() < req.getAmount()) {
            return new TransferResponse(false, "Insufficient funds");
        }

        // perform transfer
        from.setBalance(from.getBalance() - req.getAmount());
        to.setBalance(to.getBalance() + req.getAmount());

        return new TransferResponse(true, String.format("Transferred %.2f from %s to %s", req.getAmount(), req.getFromAccount(), req.getToAccount()));
    }
    // New method: account statement
    public String getStatement(String accountId) {
        Account a = accounts.get(accountId);
        if (a == null) {
            return "Account not found: " + accountId;
        }
        // For POC, just return a simple statement string
        return String.format("Statement for account %s: Balance %.2f", a.getAccountId(), a.getBalance());
    }

    // New method: loan inquiry
    public String getLoanInfo(String accountId) {
        Account a = accounts.get(accountId);
        if (a == null) {
            return "Account not found: " + accountId;
        }
        // For POC, return a mock loan info string
        return String.format("Loan info for account %s: Eligible for up to $%.2f", a.getAccountId(), a.getBalance() * 2);
    }
}
