# Dual-Model Comparison Output Guide

Quick reference for understanding and using the dual-model comparison test outputs.

## What Gets Generated

When you run `.\test_dual_model_comparison.ps1`, the test creates:

### 1. Console Output
Real-time test progress showing:
- Which test is running
- Performance metrics for each model
- Immediate comparison results
- Final summary with recommendations

### 2. Summary JSON File
**File**: `dual_model_comparison_results.json`

Contains:
- Test metadata (date, models used)
- Results for each test case
- Aggregate statistics
- Performance comparisons

**Use for**: Quantitative analysis, tracking metrics over time, automated processing

### 3. Detailed Analysis Files
**Directory**: `dual_model_comparison_details/`

**Structure**:
```
dual_model_comparison_details/
├── README.md
├── test_01_Exact_match_comparison/
│   ├── primary_model_response.txt
│   ├── secondary_model_response.txt
│   └── side_by_side_comparison.txt
├── test_02_Substantial_match_with_minor/
│   ├── primary_model_response.txt
│   ├── secondary_model_response.txt
│   └── side_by_side_comparison.txt
├── test_03_Partial_match_with_signif/
│   ├── primary_model_response.txt
│   ├── secondary_model_response.txt
│   └── side_by_side_comparison.txt
└── ... (one directory per test case)
```

**Use for**: Qualitative analysis, reviewing LLM reasoning, comparing analysis depth

## Quick Start: Reviewing Results

### Step 1: Check Console Summary (5 minutes)

Look at the final console output:

```
DUAL-MODEL COMPARISON SUMMARY
================================================================================

Tests Run: 5
Primary Model: gpt-4.1
Secondary Model: gpt-4.1-mini

PRIMARY MODEL PERFORMANCE:
  Average Time: 2.345s
  Total Tokens: 6789
  Average Tokens: 1357.8
  Average Similarity: 0.847

SECONDARY MODEL PERFORMANCE:
  Average Time: 1.523s
  Total Tokens: 4892
  Average Tokens: 978.4
  Average Similarity: 0.843

COMPARATIVE ANALYSIS:
  Time Difference: +0.822s (+35.1%)
    Secondary model is FASTER
  Token Difference: +1897 (+28.0%)
    Secondary model uses FEWER tokens
  Similarity Difference: 0.004
    Models agree closely on similarity scores

RECOMMENDATIONS:
  Consider using secondary model for cost savings with similar performance
```

**Quick Decision**: If similarity difference is <0.1 and token savings >20%, secondary model is likely a good choice.

### Step 2: Review Detailed Files (15-30 minutes)

For quality assessment, review 2-3 test cases in detail:

1. **Open side_by_side_comparison.txt** in each test directory
   - Quick metrics comparison
   - See which model was faster/more efficient

2. **Open both response files side-by-side** in a text editor
   - Compare risk identification
   - Compare recommendation quality
   - Compare analysis depth

3. **Note quality differences**
   - Does one model consistently miss risks?
   - Are recommendations equally actionable?
   - Is one model significantly better at similarity assessment?

### Step 3: Make Decision (5 minutes)

Based on your review:

| Scenario | Recommendation |
|----------|----------------|
| Similar quality + significant cost savings | Use secondary model |
| Primary significantly better quality | Use primary for critical contracts, secondary for routine |
| Quality varies by test type | Develop routing rules based on contract characteristics |
| Need more data | Run additional tests with your specific contract types |

## What to Look For in Response Files

### Risk Analysis Quality

**Good risk identification**:
```
1. COMPLIANCE - high
   Description: Specific description of the compliance issue
   Impact: Clear explanation of potential consequences
   Location: Section 3.2 - Insurance Requirements
```

**Poor risk identification**:
```
1. GENERAL - medium
   Description: Generic concern about the clause
   Impact: May cause issues
   Location: (not specified)
```

### Recommendation Quality

**Good recommendation**:
```
1. MODIFY_LANGUAGE - Priority: high
   Description: Specifically describes what needs to change and why
   Suggested Text:
   The Contractor shall maintain comprehensive general liability insurance
   with minimum coverage of $2,000,000 per occurrence and $4,000,000 aggregate.

   Rationale: Current language lacks specific coverage amounts, creating
   ambiguity about minimum insurance requirements.
```

**Poor recommendation**:
```
1. REVIEW - Priority: medium
   Description: Consider reviewing insurance requirements
   Suggested Text: (none)
   Rationale: Insurance should be appropriate
```

### Similarity Analysis Quality

**Good analysis**:
```
Score: 0.750

Differences:
1. DIFFERENT - medium
   Location: Coverage limit section
   Library: minimum coverage of $1,000,000
   Contract: minimum coverage of $2,000,000

2. EXTRA - low
   Location: Additional insured requirements
   Library: (not specified)
   Contract: shall name Client as additional insured

3. DIFFERENT - medium
   Location: Notice requirements
   Library: 15-day written notice
   Contract: 30-day written notice
```

**Poor analysis**:
```
Score: 0.750

Differences:
1. DIFFERENT - medium
   Location: clause content
   Library: some text
   Contract: different text

2. EXTRA - low
   Location: somewhere
   Library: (not specified)
   Contract: additional content
```

## File Format Details

### Response File Format

Each model response file follows this structure:

```
================================================================================
PRIMARY MODEL ANALYSIS: gpt-4.1
================================================================================

Test Case: [Description]
Expected Similarity: [Level]
Processing Time: [Time]
Tokens Used: [Count]

--------------------------------------------------------------------------------
CONTRACT TEXT ANALYZED
--------------------------------------------------------------------------------
[Full contract text that was analyzed]

--------------------------------------------------------------------------------
SIMILARITY ANALYSIS
--------------------------------------------------------------------------------
Score: [0.0-1.0]

--------------------------------------------------------------------------------
DIFFERENCES IDENTIFIED
--------------------------------------------------------------------------------
1. [TYPE] - [severity]
   Location: [Location in text]
   Library: [Library clause text]
   Contract: [Contract clause text]
2. ...

--------------------------------------------------------------------------------
RISK ANALYSIS
--------------------------------------------------------------------------------
Overall Risk: [low|medium|high|critical]
Risk Score: [0.0-10.0]

Identified Risks:
1. [CATEGORY] - [severity]
   Description: [Details]
   Impact: [Impact description]
   Location: [Optional location]
...

--------------------------------------------------------------------------------
RECOMMENDATIONS
--------------------------------------------------------------------------------
1. [TYPE] - Priority: [high|medium|low]
   [Description]
   Suggested Text:
   [Suggested text if applicable]
   Rationale: [Explanation]
...
```

### Side-by-Side File Format

```
================================================================================
SIDE-BY-SIDE MODEL COMPARISON
================================================================================

Test Case: [Description]
Expected: [Expected similarity level]

--------------------------------------------------------------------------------
PERFORMANCE METRICS
--------------------------------------------------------------------------------
Metric                        Primary                   Secondary
--------------------------------------------------------------------------------
Model                         gpt-4.1                   gpt-4.1-mini
Time                          2.345s                    1.523s
Tokens                        1234                      892
Similarity Score              0.950                     0.945
Risk Level                    medium                    medium
Risk Count                    3                         2
Recommendations               4                         3

--------------------------------------------------------------------------------
DIFFERENCES
--------------------------------------------------------------------------------
Time: -0.822s (-35.1%)
Tokens: -342 (-27.7%)
Similarity: 0.005

Faster: gpt-4.1-mini
More Efficient: gpt-4.1-mini
```

## Common Review Workflows

### Workflow 1: Quick Assessment
**Time**: 5 minutes
**Goal**: Determine if models perform similarly

1. Check console summary
2. Look at aggregate metrics
3. If similarity difference <0.1 and token savings >20% → Use secondary model

### Workflow 2: Quality Deep-Dive
**Time**: 30-60 minutes
**Goal**: Understand qualitative differences

1. Review console summary
2. Read README in dual_model_comparison_details/
3. For each test case:
   - Read side_by_side_comparison.txt
   - Compare risk sections in both response files
   - Compare recommendation sections
   - Note quality differences
4. Document findings
5. Make informed decision

### Workflow 3: Use Case Analysis
**Time**: 1-2 hours
**Goal**: Develop routing strategy

1. Review all test cases
2. Categorize by contract type/complexity
3. Identify patterns:
   - Which model excels at which types?
   - Where is quality difference significant?
   - Where is cost savings justified?
4. Create decision matrix:
   - High-value contracts → Primary model
   - Routine contracts → Secondary model
   - Complex analysis → Primary model
   - Simple comparison → Secondary model

## Integration with Your Workflow

### Option 1: Single Model Selection
Choose one model based on test results and use it for all comparisons.

**Pros**: Simple, consistent
**Cons**: May overpay or underperform on some comparisons

### Option 2: Routing Logic
Use different models based on contract characteristics.

**Example**:
```python
def select_model(contract_value, risk_level, contract_type):
    if contract_value > 1000000:
        return "primary"  # High value = use best model
    elif risk_level == "high":
        return "primary"  # High risk = use best model
    elif contract_type in ["MSA", "NDA"]:
        return "primary"  # Critical types = use best model
    else:
        return "secondary"  # Routine = use efficient model
```

**Pros**: Optimizes cost vs quality
**Cons**: More complex to implement

### Option 3: Hybrid Approach
Use secondary for initial screening, primary for flagged cases.

**Workflow**:
1. Run comparison with secondary model
2. If risk level is "high" or similarity is "minimal_match":
   - Re-run with primary model for detailed analysis
3. Otherwise use secondary model results

**Pros**: Balance of cost and quality
**Cons**: Some comparisons run twice

## Questions to Answer

Use the detailed files to answer:

1. **Risk Detection**: Does secondary model identify the same critical risks as primary?
   - Review RISK ANALYSIS sections across multiple tests
   - Check if any high-severity risks are missed

2. **Recommendation Quality**: Are secondary model recommendations actionable?
   - Review RECOMMENDATIONS sections
   - Check if suggested text is provided
   - Assess specificity and clarity

3. **Accuracy**: Do similarity scores align with actual differences?
   - Compare scores to KEY DIFFERENCES lists
   - Check if match types are appropriate
   - Assess consistency across tests

4. **Value**: Is quality difference worth the cost difference?
   - Calculate cost savings based on token differences
   - Assess if quality gaps affect decision-making
   - Determine if secondary model meets your needs

## Next Steps

After reviewing the results:

1. **Document your findings** in a decision memo
2. **Update configuration** to use selected model(s)
3. **Monitor production usage** to validate test results
4. **Re-test periodically** as models evolve
5. **Adjust routing logic** based on real-world performance

## Support

For questions about:
- **Configuration**: See `DUAL_MODEL_COMPARISON.md`
- **File contents**: See `dual_model_comparison_details/README.md`
- **API usage**: See `DUAL_MODEL_COMPARISON.md` "API Usage" section
