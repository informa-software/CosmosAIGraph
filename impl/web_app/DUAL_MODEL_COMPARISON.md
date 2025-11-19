# Dual-Model Comparison Feature

## Overview

The dual-model comparison feature allows you to compare the performance and quality of two different LLM models side-by-side on the same clause comparison tasks. This is useful for:

- Evaluating cost vs. quality trade-offs
- Benchmarking different model versions
- Validating model selection decisions
- Analyzing performance characteristics

**Quick Start**: After running tests, see `DUAL_MODEL_OUTPUT_GUIDE.md` for a practical guide to reviewing and interpreting the results.

## Configuration

### Primary Model (Default)

The primary model is configured using existing environment variables:

```bash
CAIG_AZURE_OPENAI_URL="https://your-primary-resource.openai.azure.com/"
CAIG_AZURE_OPENAI_KEY="your-primary-api-key"
CAIG_AZURE_OPENAI_COMPLETIONS_DEP="gpt-4.1"
CAIG_AZURE_OPENAI_VERSION="2025-01-01-preview"
```

### Secondary Model (For Comparison)

The secondary model requires additional environment variables in `.env`:

```bash
CAIG_AZURE_OPENAI_URL_SECONDARY="https://your-secondary-resource.openai.azure.com/"
CAIG_AZURE_OPENAI_KEY_SECONDARY="your-secondary-api-key"
CAIG_AZURE_OPENAI_COMPLETIONS_DEP_SECONDARY="gpt-4.1-mini"
CAIG_AZURE_OPENAI_VERSION_SECONDARY="2025-01-01-preview"
```

**Note**: The secondary model can use the same Azure OpenAI resource (same URL) or a different one. If using the same resource, you only need different deployment names.

### Example Configuration (Same Resource)

```bash
# Primary model
CAIG_AZURE_OPENAI_URL="https://myresource.openai.azure.com/"
CAIG_AZURE_OPENAI_KEY="abc123..."
CAIG_AZURE_OPENAI_COMPLETIONS_DEP="gpt-4.1"

# Secondary model (same resource, different deployment)
CAIG_AZURE_OPENAI_URL_SECONDARY="https://myresource.openai.azure.com/"
CAIG_AZURE_OPENAI_KEY_SECONDARY="abc123..."  # Can be same key
CAIG_AZURE_OPENAI_COMPLETIONS_DEP_SECONDARY="gpt-4.1-mini"
```

## Usage

### Running the Test Suite

Use the PowerShell script to run comprehensive side-by-side tests:

```powershell
cd web_app
.\test_dual_model_comparison.ps1
```

This will:
1. Create a test clause in the database
2. Run multiple comparison tests with both models
3. Compare performance metrics (time, tokens, quality)
4. Generate a detailed report

### Test Output

The test suite produces:

1. **Console Output**: Real-time comparison results with metrics
2. **JSON Summary**: Aggregated metrics saved to `dual_model_comparison_results.json`
3. **Detailed Analysis Files**: Full LLM responses for each test case in `dual_model_comparison_details/`

#### Output Structure

```
web_app/
├── dual_model_comparison_results.json          # Summary metrics and statistics
└── dual_model_comparison_details/              # Detailed analysis files
    ├── test_01_Exact_match_comparison/
    │   ├── primary_model_response.txt          # Full primary model analysis
    │   ├── secondary_model_response.txt        # Full secondary model analysis
    │   └── side_by_side_comparison.txt         # Quick comparison summary
    ├── test_02_Substantial_match_with_/
    │   ├── primary_model_response.txt
    │   ├── secondary_model_response.txt
    │   └── side_by_side_comparison.txt
    └── ... (one directory per test case)
```

#### Detailed Response Files

Each test case directory contains three files:

**1. primary_model_response.txt / secondary_model_response.txt**
- Complete LLM analysis including:
  - Similarity analysis with score and match type
  - Key differences identified
  - Risk analysis with severity levels
  - Detailed recommendations with suggested text
  - Processing time and token usage

**2. side_by_side_comparison.txt**
- Quick reference comparing both models:
  - Performance metrics table
  - Difference calculations
  - Winner identification (faster/more efficient)

Example console output:

```
[Test 1] Exact match comparison
  Expected similarity: exact_match

  Running with PRIMARY model...
    Model: gpt-4.1
    Time: 2.345s
    Tokens: 1234
    Similarity: 0.950
    Risk Level: low

  Running with SECONDARY model...
    Model: gpt-4.1-mini
    Time: 1.567s
    Tokens: 892
    Similarity: 0.945
    Risk Level: low

  COMPARISON:
    Time difference: -0.778s (-33.2%)
    Token difference: -342 (-27.7%)
    Similarity difference: 0.005
```

### API Usage

You can also use the feature programmatically via the API:

```python
from src.models.clause_library_models import CompareClauseRequest

# Compare with primary model
request = CompareClauseRequest(
    clause_id="clause-123",
    contract_text="The Contractor shall indemnify...",
    contract_id="contract-456"
)

comparison_primary = await clause_service.compare_clause(
    request=request,
    user_email="user@example.com",
    model_selection="primary"  # Use GPT-4.1
)

# Compare with secondary model
comparison_secondary = await clause_service.compare_clause(
    request=request,
    user_email="user@example.com",
    model_selection="secondary"  # Use GPT-4.1-mini
)

# Compare results
print(f"Primary: {comparison_primary.ai_analysis.model} - {comparison_primary.ai_analysis.completion_tokens} tokens")
print(f"Secondary: {comparison_secondary.ai_analysis.model} - {comparison_secondary.ai_analysis.completion_tokens} tokens")
```

## Reviewing Analysis Quality

### Manual Quality Assessment

After running the test suite, review the detailed response files to assess qualitative differences:

#### 1. Risk Identification Quality
Compare how well each model identifies and assesses risks:
- **Completeness**: Does the model identify all relevant risks?
- **Specificity**: Are risk descriptions detailed and actionable?
- **Severity Assessment**: Are severity levels (high/medium/low) appropriate?
- **Mitigation Suggestions**: Are mitigation strategies practical and specific?

**Review in**: `primary_model_response.txt` and `secondary_model_response.txt` under "RISK ANALYSIS"

#### 2. Recommendation Quality
Evaluate the quality and usefulness of recommendations:
- **Relevance**: Are recommendations directly related to identified issues?
- **Specificity**: Do recommendations include concrete suggested text?
- **Prioritization**: Is priority level (high/medium/low) appropriate?
- **Rationale**: Are explanations clear and well-reasoned?
- **Completeness**: Does suggested text fully address the issue?

**Review in**: Response files under "RECOMMENDATIONS"

#### 3. Similarity Analysis Depth
Compare the depth and accuracy of similarity assessments:
- **Key Differences**: Does the model identify all significant variations?
- **Match Type Accuracy**: Is the overall match type (exact/substantial/partial/minimal) correct?
- **Summary Quality**: Is the summary clear and comprehensive?
- **Score Calibration**: Does the similarity score align with the differences found?

**Review in**: Response files under "SIMILARITY ANALYSIS"

#### 4. Overall Analysis Insight
Assess the overall quality of analysis:
- **Contextual Understanding**: Does the model understand legal context?
- **Technical Accuracy**: Are technical terms and concepts used correctly?
- **Practical Value**: Would the analysis help a contract reviewer?
- **Consistency**: Are conclusions logically consistent throughout?

### Comparison Checklist

Use this checklist when reviewing detailed response files:

```
Test Case: _______________

□ Risk Identification
  □ Primary model found ___ risks
  □ Secondary model found ___ risks
  □ Quality winner: ________

□ Recommendations
  □ Primary model provided ___ recommendations
  □ Secondary model provided ___ recommendations
  □ More actionable: ________

□ Similarity Analysis
  □ Primary score: ___
  □ Secondary score: ___
  □ More accurate: ________

□ Overall Assessment
  □ Better analysis: ________
  □ Worth extra cost? ________
  □ Use case fit: ________
```

### Example Quality Comparison

When reviewing `test_01_Exact_match_comparison/`:

**Primary Model (GPT-4.1)**:
- May provide more detailed risk descriptions
- Likely to offer more comprehensive recommendations
- Could identify subtle nuances in contract language
- Uses more tokens for thorough analysis

**Secondary Model (GPT-4.1-mini)**:
- Provides concise but complete risk identification
- Offers practical, actionable recommendations
- Captures main similarity issues efficiently
- More cost-effective for routine comparisons

**Decision Factors**:
- If both models identify the same risks → Use secondary for cost savings
- If primary provides significantly better insights → Use primary for critical contracts
- If quality difference is minimal → Use secondary for most cases, primary for high-stakes

## Comparison Metrics

The test suite compares models across multiple dimensions:

### Performance Metrics
- **Processing Time**: Total time to complete analysis
- **Token Usage**: Number of completion tokens consumed
- **Cost Efficiency**: Tokens per comparison (lower is better)

### Quality Metrics
- **Similarity Score**: Agreement with expected results
- **Risk Detection**: Ability to identify risks
- **Recommendation Quality**: Number and relevance of recommendations

### Aggregate Statistics
- Average processing time across all tests
- Total token consumption
- Average similarity scores
- Risk detection patterns

## Caching Behavior

**Important**: Comparisons are cached separately per model!

- Cache key includes model selection
- Same comparison request with different models = 2 separate cache entries
- This ensures fair performance comparison without cache interference

Example:
```
Cache key: hash(clause_id + contract_text + "primary")
Cache key: hash(clause_id + contract_text + "secondary")
```

## Cost Analysis

Use the comparison results to estimate cost differences:

### GPT-4.1 (Primary)
- Higher quality analysis
- More detailed recommendations
- Higher token consumption
- Slower processing time

### GPT-4.1-mini (Secondary)
- Good quality analysis
- Concise recommendations
- Lower token consumption (typically 20-30% fewer tokens)
- Faster processing time (typically 30-40% faster)

### Cost Calculation Example

If your test results show:
- Primary: 1500 tokens average
- Secondary: 1050 tokens average
- Difference: 450 tokens (30% reduction)

For 1000 comparisons per month:
- Primary: 1,500,000 tokens
- Secondary: 1,050,000 tokens
- Savings: 450,000 tokens (30%)

Actual cost savings depend on your Azure OpenAI pricing tier.

## Recommendations

Based on comparison results:

### Use Primary Model (GPT-4.1) When:
- Maximum accuracy is critical
- Complex legal analysis required
- Cost is secondary to quality
- Comprehensive recommendations needed

### Use Secondary Model (GPT-4.1-mini) When:
- Good accuracy is sufficient
- High volume of comparisons
- Cost optimization is important
- Faster response time is valuable

### Hybrid Approach:
1. Use secondary model for initial screening
2. Use primary model for flagged high-risk cases
3. Optimize cost while maintaining quality for critical decisions

## Troubleshooting

### Secondary Model Not Configured

If you see this error:
```
WARNING: Secondary model not configured!
```

Ensure all four secondary environment variables are set in `.env`:
- CAIG_AZURE_OPENAI_URL_SECONDARY
- CAIG_AZURE_OPENAI_KEY_SECONDARY
- CAIG_AZURE_OPENAI_COMPLETIONS_DEP_SECONDARY
- CAIG_AZURE_OPENAI_VERSION_SECONDARY

### Authentication Errors

If you see authentication errors for the secondary model:
- Verify the API key is correct
- Ensure the key has access to the specified deployment
- Check that the deployment name matches your Azure OpenAI resource

### Deployment Not Found

If you see "deployment not found" errors:
- Verify the deployment exists in your Azure OpenAI resource
- Check the deployment name spelling
- Ensure the deployment is in a "succeeded" state

## Implementation Details

### Service Architecture

```
ClauseLibraryService
├── compare_clause(model_selection="primary"|"secondary")
│   ├── Select client based on model_selection
│   ├── Use separate cache keys per model
│   └── Return comparison with model name in results
│
AiService
├── aoai_client (primary)
├── completions_deployment (primary)
├── aoai_client_secondary
└── completions_deployment_secondary
```

### Cache Separation

Comparisons are cached with model-specific keys:

```python
cache_key = hash(clause_id, contract_text) + ":" + model_selection
```

This ensures:
- No cache interference between models
- Fair performance comparison
- Independent cache management

### Configuration Loading

Configuration is loaded in this order:
1. Environment variables (from shell)
2. `.env` file (via python-dotenv)
3. Default values in ConfigService

The secondary model is optional - if not configured, only the primary model is available.

## Future Enhancements

Potential improvements:
- Support for more than 2 models
- Automated A/B testing
- Quality scoring algorithms
- Cost optimization recommendations
- Historical comparison tracking
- Model performance trends
