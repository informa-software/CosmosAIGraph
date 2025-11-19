# Dual-Model Comparison Detailed Results

This directory contains detailed LLM response files for each test case in the dual-model comparison test suite.

## Directory Structure

Each test case has its own subdirectory with three files:

```
test_01_Exact_match_comparison/
├── primary_model_response.txt        # Complete analysis from primary model (GPT-4.1)
├── secondary_model_response.txt      # Complete analysis from secondary model (GPT-4.1-mini)
└── side_by_side_comparison.txt       # Quick comparison summary
```

## File Contents

### primary_model_response.txt / secondary_model_response.txt

Full LLM analysis including:

1. **Test Metadata**
   - Test case description
   - Expected similarity level
   - Processing time
   - Tokens used

2. **Contract Text Analyzed**
   - The exact contract text that was compared against the library clause

3. **Similarity Analysis**
   - Similarity score (0.0 to 1.0)
   - Match type (exact_match, substantial_match, partial_match, minimal_match)
   - Summary description
   - Key differences identified

4. **Risk Analysis**
   - Overall risk level (low, medium, high, critical)
   - Risk score (0.0 to 10.0)
   - Detailed list of identified risks:
     - Risk type (coverage, liability, compliance, etc.)
     - Severity level
     - Description
     - Impact assessment
     - Mitigation suggestions

5. **Recommendations**
   - Recommendation type (add_clause, modify_language, strengthen_protection, etc.)
   - Priority (high, medium, low)
   - Description
   - Suggested text (if applicable)
   - Rationale

### side_by_side_comparison.txt

Quick reference with:
- Performance metrics table (time, tokens, scores)
- Calculated differences
- Identification of faster/more efficient model

## How to Review

### 1. Start with side_by_side_comparison.txt
Get a quick overview of the quantitative differences between models.

### 2. Review Response Files for Quality
Open both `primary_model_response.txt` and `secondary_model_response.txt` side-by-side.

**Compare**:
- Number and quality of risks identified
- Specificity of risk descriptions
- Actionability of recommendations
- Depth of similarity analysis
- Overall insight quality

### 3. Use the Quality Checklist

For each test case, assess:

```
□ Risk Identification
  - Does each model identify all relevant risks?
  - Are severity assessments appropriate?
  - Are mitigation strategies practical?

□ Recommendations
  - Are recommendations specific and actionable?
  - Is suggested text included and complete?
  - Are priorities assigned correctly?

□ Similarity Analysis
  - Are key differences accurately identified?
  - Does the similarity score match the analysis?
  - Is the match type classification correct?

□ Overall Quality
  - Which model provides better legal insight?
  - Is the quality difference worth the cost difference?
  - Which model fits your use case better?
```

### 4. Document Your Findings

Note which model performs better for:
- **Risk detection**: Identifying potential issues
- **Recommendations**: Providing actionable guidance
- **Accuracy**: Correct similarity assessment
- **Value**: Best quality-to-cost ratio

## Quality Assessment Criteria

### Excellent Analysis
- Identifies all relevant risks with appropriate severity
- Provides specific, actionable recommendations with suggested text
- Accurately assesses similarity with clear reasoning
- Demonstrates understanding of legal context

### Good Analysis
- Identifies major risks, may miss minor issues
- Provides practical recommendations, some lack suggested text
- Reasonable similarity assessment with some gaps
- Shows adequate understanding of contract language

### Adequate Analysis
- Identifies obvious risks, misses nuanced issues
- Generic recommendations without suggested text
- Similarity score may not align with differences
- Basic understanding of contract terms

## Example Review Process

**Test Case**: test_01_Exact_match_comparison

1. **Open side_by_side_comparison.txt**
   - Note: Secondary model is 35% faster, uses 28% fewer tokens
   - Similarity scores are close (0.950 vs 0.945)

2. **Compare Risk Analysis**
   - Primary identified 3 risks, Secondary identified 2 risks
   - Question: Did secondary miss a critical risk?
   - Review risk descriptions for depth and clarity

3. **Compare Recommendations**
   - Primary provided 4 recommendations, Secondary provided 3
   - Check if both include suggested text
   - Assess which recommendations are more actionable

4. **Decision**
   - If secondary model captured all critical issues → Use secondary for cost savings
   - If primary model provides significantly better insights → Use primary for this type of case
   - Document findings for future reference

## Integration with Summary Report

These detailed files complement the summary statistics in:
- `../dual_model_comparison_results.json` - Quantitative metrics and aggregate statistics

Use both resources together:
1. Summary JSON for overall performance trends
2. Detailed files for qualitative analysis assessment

## Next Steps

Based on your quality review:

1. **Both models perform similarly**
   → Use secondary model for cost optimization

2. **Primary model significantly better**
   → Use primary model for critical contracts
   → Use secondary model for routine contracts

3. **Quality varies by test case**
   → Develop routing logic based on contract characteristics
   → Use primary for high-value/high-risk contracts
   → Use secondary for standard/low-risk contracts

4. **Need more testing**
   → Add more test cases covering your specific contract types
   → Test with actual contracts from your workflow
   → Measure quality on your domain-specific criteria
