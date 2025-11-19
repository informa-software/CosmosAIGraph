# Query Contracts PDF Report Example

## Visual Layout Example

This shows what a generated PDF report will look like for a natural language query across multiple contracts.

---

# Contract Query Report

## Query

> **"Which of these contracts have the broadest indemnification for the contracting party?"**

---

**Generated:** 2025-10-23 14:30:00 UTC
**Contracts Analyzed:** 5
**Query Time:** 3.2 seconds

---

## Contracts Analyzed

| Contract ID | Filename | Title |
|------------|----------|-------|
| contract_abc_123 | Westervelt_Standard_MSA.json | Westervelt Standard MSA |
| contract_def_456 | ACME_Corp_Agreement.json | ACME Corp Service Agreement |
| contract_ghi_789 | TechCorp_MSA.json | TechCorp Master Service Agreement |
| contract_jkl_012 | GlobalSoft_Contract.json | GlobalSoft Software License |
| contract_mno_345 | BuildRight_Agreement.json | BuildRight Construction Agreement |

---

## Analysis Results

### Summary

Based on the analysis of 5 contracts, the ranking below shows which contracts provide the broadest indemnification for the contracting party. The Westervelt Standard MSA provides the most comprehensive indemnification coverage, including third-party claims, IP infringement, and unlimited duration. ACME Corp Agreement follows with strong coverage but excludes certain third-party scenarios.

---

## Detailed Contract Rankings

---

### 🥇 **Rank 1** - Westervelt_Standard_MSA.json

**Score:** 95%
**Contract ID:** contract_abc_123

#### Analysis:

This contract provides the broadest indemnification for the contracting party. The indemnification clause covers all types of claims including third-party claims, intellectual property infringement, negligence, and breach of contract. The coverage has no monetary cap and extends indefinitely beyond the term of the agreement. The contracting party has no obligation to defend or reimburse for legal costs.

#### Relevant Clauses

**Indemnification**

> "Party A shall indemnify, defend, and hold harmless Party B, its affiliates, officers, directors, employees, and agents from and against any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable attorneys' fees) arising out of or relating to: (a) any breach of this Agreement by Party A; (b) any negligent or willful misconduct by Party A; (c) any infringement or alleged infringement of intellectual property rights by Party A's services or deliverables; (d) any third-party claims arising from Party A's performance under this Agreement..."

**Analysis:** Provides unlimited indemnification coverage with no monetary cap. Includes defense obligations and covers all legal costs. Extends to third-party claims and IP infringement without carve-outs.

---

### 🥈 **Rank 2** - ACME_Corp_Agreement.json

**Score:** 82%
**Contract ID:** contract_def_456

#### Analysis:

This contract offers strong indemnification protection but with some limitations. The indemnification covers breach of contract, IP infringement, and negligence, but excludes certain third-party scenarios where the contracting party contributed to the claim. Coverage is capped at $5 million and limited to the term of the agreement plus 2 years.

#### Relevant Clauses

**Indemnification**

> "Contractor agrees to indemnify and hold harmless Customer from any claims, losses, or damages arising from: (i) breach of representations or warranties; (ii) intellectual property infringement claims related to Contractor's work product; (iii) gross negligence or willful misconduct of Contractor. Indemnification obligations are limited to $5,000,000 per incident and survive for 24 months following termination..."

**Analysis:** Good coverage but with monetary cap and time limitations. Excludes scenarios where customer contributory negligence is involved.

---

### 🥉 **Rank 3** - TechCorp_MSA.json

**Score:** 71%
**Contract ID:** contract_ghi_789

#### Analysis:

Moderate indemnification coverage focused primarily on IP infringement and breach of contract. Does not cover third-party claims or extend beyond the agreement term. Includes a $2 million cap on indemnification obligations.

#### Relevant Clauses

**Indemnification**

> "Vendor will indemnify Client against direct damages resulting from: (1) breach of confidentiality obligations; (2) infringement of Client's intellectual property by Vendor's deliverables. Maximum liability under this section is $2,000,000..."

**Analysis:** Limited scope focusing on IP and confidentiality. Significant exclusions for third-party claims and indirect damages.

---

### Rank 4 - GlobalSoft_Contract.json

**Score:** 58%
**Contract ID:** contract_jkl_012

#### Analysis:

Limited indemnification focused on IP infringement only. Excludes all other types of claims including negligence and breach of contract. Short survival period of 12 months post-termination.

#### Relevant Clauses

**Indemnification**

> "Licensor shall indemnify Licensee solely for third-party claims alleging that the licensed software infringes a valid patent or copyright. This obligation terminates 12 months after agreement termination..."

**Analysis:** Very narrow scope limited to IP infringement of software only. No coverage for other types of claims.

---

### Rank 5 - BuildRight_Agreement.json

**Score:** 42%
**Contract ID:** contract_mno_345

#### Analysis:

Minimal indemnification with significant carve-outs. Only covers bodily injury and property damage occurring on construction sites. Excludes all IP, breach, and negligence claims. High monetary threshold before indemnification kicks in.

#### Relevant Clauses

**Indemnification**

> "Contractor shall indemnify Owner for physical injury to persons or damage to property occurring at the project site and directly caused by Contractor's operations, subject to a $50,000 deductible per incident..."

**Analysis:** Very limited scope focused only on site-related physical damages. High deductible significantly reduces practical value of indemnification.

---

## Report Generation Details

**Contracts Analyzed:** 5
**LLM Model:** gpt-4
**Query Execution Time:** 3.20s
**Report Generated:** 2025-10-23 14:30:00 UTC

---

*Confidential - Internal Use Only*
Page 1 of 3
