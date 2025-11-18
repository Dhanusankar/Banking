package com.banking.dto;

/**
 * Response DTO for balance inquiries.
 */
public class BalanceResponse {
    private String accountId;
    private double balance;

    public BalanceResponse() {}

    public BalanceResponse(String accountId, double balance) {
        this.accountId = accountId;
        this.balance = balance;
    }

    public String getAccountId() {
        return accountId;
    }

    public void setAccountId(String accountId) {
        this.accountId = accountId;
    }

    public double getBalance() {
        return balance;
    }

    public void setBalance(double balance) {
        this.balance = balance;
    }
}
