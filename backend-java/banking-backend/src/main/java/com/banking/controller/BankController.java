package com.banking.controller;

import com.banking.dto.BalanceResponse;
import com.banking.dto.TransferRequest;
import com.banking.dto.TransferResponse;
import com.banking.service.BankService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * REST controller exposing balance and transfer endpoints.
 */
@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class BankController {
    private final BankService bankService;

    public BankController(BankService bankService) {
        this.bankService = bankService;
    }

    @GetMapping("/balance")
    public ResponseEntity<BalanceResponse> getBalance(@RequestParam(name = "accountId", defaultValue = "123") String accountId) {
        BalanceResponse resp = bankService.getBalance(accountId);
        return ResponseEntity.ok(resp);
    }

    @PostMapping("/transfer")
    public ResponseEntity<TransferResponse> transfer(@RequestBody TransferRequest req) {
        TransferResponse resp = bankService.transfer(req);
        if (!resp.isSuccess()) {
            return ResponseEntity.badRequest().body(resp);
        }
        return ResponseEntity.ok(resp);
    }

    // New endpoint: account statement
    @GetMapping("/statement")
    public ResponseEntity<String> getStatement(@RequestParam(name = "accountId", defaultValue = "123") String accountId) {
        String statement = bankService.getStatement(accountId);
        return ResponseEntity.ok(statement);
    }

    // New endpoint: loan inquiry
    @GetMapping("/loan")
    public ResponseEntity<String> getLoanInfo(@RequestParam(name = "accountId", defaultValue = "123") String accountId) {
        String loanInfo = bankService.getLoanInfo(accountId);
        return ResponseEntity.ok(loanInfo);
    }
}
