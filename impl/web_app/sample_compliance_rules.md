# Sample Compliance Rules for Testing

These curl commands create a comprehensive set of compliance rules covering common contract requirements. Import these into Postman or run them directly from command line.

**Base URL:** `http://localhost:8000`

---

## Payment & Financial Rules

### 1. Payment Terms Window
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Payment Terms Window",
    "description": "Contract must specify payment terms between 14 and 30 days from invoice date",
    "severity": "high",
    "category": "payment_terms",
    "active": true
  }'
```

### 2. Late Payment Penalties
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Late Payment Penalties",
    "description": "Contract must include provisions for late payment penalties or interest charges",
    "severity": "medium",
    "category": "payment_terms",
    "active": true
  }'
```

### 3. Payment Currency Specification
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Payment Currency Specification",
    "description": "Contract must clearly specify the currency for all payments (USD, EUR, GBP, etc.)",
    "severity": "medium",
    "category": "payment_terms",
    "active": true
  }'
```

---

## Confidentiality & Data Protection

### 4. Confidentiality Clause Required
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Confidentiality Clause Required",
    "description": "Contract must include confidentiality obligations covering proprietary information and trade secrets",
    "severity": "critical",
    "category": "confidentiality",
    "active": true
  }'
```

### 5. Data Privacy Compliance
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Privacy Compliance",
    "description": "Contract must reference compliance with GDPR, CCPA, or other applicable data protection regulations",
    "severity": "critical",
    "category": "data_protection",
    "active": true
  }'
```

### 6. Data Breach Notification
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Breach Notification",
    "description": "Contract must include data breach notification requirements with specific timeframes (e.g., 72 hours)",
    "severity": "high",
    "category": "data_protection",
    "active": true
  }'
```

---

## Liability & Indemnification

### 7. Limitation of Liability Cap
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Limitation of Liability Cap",
    "description": "Contract must include a cap on liability, typically not exceeding 2x the contract value",
    "severity": "high",
    "category": "liability",
    "active": true
  }'
```

### 8. No Liquidated Damages
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "No Liquidated Damages",
    "description": "Contract must NOT contain liquidated damages provisions that exceed actual damages",
    "severity": "critical",
    "category": "liability",
    "active": true
  }'
```

### 9. Mutual Indemnification
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mutual Indemnification",
    "description": "Contract must include mutual indemnification provisions protecting both parties from third-party claims",
    "severity": "high",
    "category": "liability",
    "active": true
  }'
```

---

## Termination & Renewal

### 10. Termination for Convenience
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Termination for Convenience",
    "description": "Contract must allow either party to terminate for convenience with at least 30 days notice",
    "severity": "medium",
    "category": "termination",
    "active": true
  }'
```

### 11. Termination for Cause
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Termination for Cause",
    "description": "Contract must specify grounds for termination for cause including material breach and cure periods",
    "severity": "high",
    "category": "termination",
    "active": true
  }'
```

### 12. Auto-Renewal Notification Period
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auto-Renewal Notification Period",
    "description": "If contract auto-renews, must provide at least 60 days notice before renewal date",
    "severity": "medium",
    "category": "termination",
    "active": true
  }'
```

---

## Insurance Requirements

### 13. General Liability Insurance
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "General Liability Insurance",
    "description": "Contractor must maintain commercial general liability insurance with minimum $2M coverage",
    "severity": "high",
    "category": "insurance",
    "active": true
  }'
```

### 14. Workers Compensation Insurance
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Workers Compensation Insurance",
    "description": "Contractor must maintain workers compensation insurance as required by applicable law",
    "severity": "high",
    "category": "insurance",
    "active": true
  }'
```

### 15. Certificate of Insurance Required
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Certificate of Insurance Required",
    "description": "Contract must require contractor to provide certificates of insurance before work commences",
    "severity": "medium",
    "category": "insurance",
    "active": true
  }'
```

---

## Governing Law & Dispute Resolution

### 16. Governing Law Specification
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Governing Law Specification",
    "description": "Contract must specify the governing law jurisdiction (e.g., State of Delaware, New York)",
    "severity": "high",
    "category": "governing_law",
    "active": true
  }'
```

### 17. Dispute Resolution Process
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dispute Resolution Process",
    "description": "Contract must outline dispute resolution process including negotiation, mediation, or arbitration",
    "severity": "medium",
    "category": "dispute_resolution",
    "active": true
  }'
```

### 18. Arbitration vs Litigation
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Arbitration vs Litigation",
    "description": "Contract should prefer binding arbitration over litigation to reduce legal costs",
    "severity": "low",
    "category": "dispute_resolution",
    "active": true
  }'
```

---

## Intellectual Property

### 19. IP Ownership Clarity
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "IP Ownership Clarity",
    "description": "Contract must clearly define ownership of intellectual property created during the engagement",
    "severity": "critical",
    "category": "intellectual_property",
    "active": true
  }'
```

### 20. License Grant Terms
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "License Grant Terms",
    "description": "If licensing IP, contract must specify license scope, territory, duration, and exclusivity",
    "severity": "high",
    "category": "intellectual_property",
    "active": true
  }'
```

---

## Compliance & Audit

### 21. Audit Rights
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Audit Rights",
    "description": "Contract must grant audit rights with reasonable notice (10-15 business days)",
    "severity": "medium",
    "category": "compliance",
    "active": true
  }'
```

### 22. Regulatory Compliance
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Regulatory Compliance",
    "description": "Contractor must comply with all applicable federal, state, and local laws and regulations",
    "severity": "critical",
    "category": "compliance",
    "active": true
  }'
```

---

## Force Majeure

### 23. Force Majeure Clause
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Force Majeure Clause",
    "description": "Contract must include force majeure provisions covering unforeseeable circumstances beyond control",
    "severity": "medium",
    "category": "force_majeure",
    "active": true
  }'
```

---

## Service Level Agreements (SLA)

### 24. Service Level Requirements
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Service Level Requirements",
    "description": "Service contracts must include measurable SLAs with uptime guarantees (e.g., 99.9% availability)",
    "severity": "high",
    "category": "service_level",
    "active": true
  }'
```

### 25. Performance Remedies
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Performance Remedies",
    "description": "Contract must specify remedies for SLA failures (e.g., service credits, refunds)",
    "severity": "medium",
    "category": "service_level",
    "active": true
  }'
```

---

## Assignment & Subcontracting

### 26. Assignment Restrictions
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Assignment Restrictions",
    "description": "Contract must restrict assignment without prior written consent from the other party",
    "severity": "medium",
    "category": "general_terms",
    "active": true
  }'
```

### 27. Subcontractor Approval
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Subcontractor Approval",
    "description": "Contract must require approval before engaging subcontractors for key deliverables",
    "severity": "medium",
    "category": "general_terms",
    "active": true
  }'
```

---

## Warranties

### 28. Service Warranty Period
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Service Warranty Period",
    "description": "Contract must include warranty period for services (minimum 90 days from completion)",
    "severity": "medium",
    "category": "warranties",
    "active": true
  }'
```

### 29. No Warranty Disclaimers
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "No Warranty Disclaimers",
    "description": "Contract must NOT contain broad warranty disclaimers or AS IS provisions for core deliverables",
    "severity": "high",
    "category": "warranties",
    "active": true
  }'
```

---

## Testing Rules (Mixed Severity)

### 30. Test Rule - Should Pass
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Rule - Should Pass",
    "description": "Test rule: Contract should contain the word contract or agreement",
    "severity": "low",
    "category": "testing",
    "active": true
  }'
```

### 31. Test Rule - Should Fail
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Rule - Should Fail",
    "description": "Test rule: Contract must NOT contain any terms or provisions (will always fail)",
    "severity": "low",
    "category": "testing",
    "active": false
  }'
```

---

## Verification Commands

### List All Rules
```bash
curl -X GET http://localhost:8000/api/compliance/rules
```

### List Active Rules Only
```bash
curl -X GET "http://localhost:8000/api/compliance/rules?active_only=true"
```

### Get Rules by Category
```bash
curl -X GET "http://localhost:8000/api/compliance/rules?category=payment_terms"
```

### Get Rules by Severity
```bash
curl -X GET "http://localhost:8000/api/compliance/rules?severity=critical"
```

### Get Compliance Summary Dashboard
```bash
curl -X GET http://localhost:8000/api/compliance/summary
```

### List All Categories
```bash
curl -X GET http://localhost:8000/api/compliance/categories
```

---

## Rule Statistics Summary

**Total Rules:** 31

**By Severity:**
- Critical: 5 rules
- High: 12 rules
- Medium: 12 rules
- Low: 2 rules

**By Category:**
- payment_terms: 3
- confidentiality: 1
- data_protection: 2
- liability: 3
- termination: 3
- insurance: 3
- governing_law: 1
- dispute_resolution: 2
- intellectual_property: 2
- compliance: 2
- force_majeure: 1
- service_level: 2
- general_terms: 2
- warranties: 2
- testing: 2

---

## Postman Import Instructions

1. Open Postman
2. Click "Import" button
3. Select "Raw text" tab
4. Copy and paste any curl command above
5. Click "Continue" → "Import"
6. Repeat for all rules you want to test

**Or use Postman Collection:**
1. Create new Collection named "Compliance Rules"
2. Add all curl commands as individual requests
3. Set Collection variable `base_url` = `http://localhost:8000`
4. Run entire collection to create all rules at once
