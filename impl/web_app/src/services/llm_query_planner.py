"""
LLM Query Planner

Uses Azure OpenAI to generate query strategies and executable SQL/SPARQL queries
in a single call. Provides reasoning for strategy choices and handles complex
query patterns that regex-based approaches struggle with.
"""

import json
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from openai import AzureOpenAI

from src.services.config_service import ConfigService
from src.services.strategy_schema_builder import StrategySchemaBuilder

logger = logging.getLogger(__name__)


@dataclass
class LLMQueryPlan:
    """
    Complete query plan from LLM including strategy and executable query.
    """
    strategy: str
    fallback_strategy: str
    query_type: str  # "SQL" or "SPARQL"
    query_text: str
    execution_plan: Dict
    confidence: float
    reasoning: str
    result_format: str  # "list_summary" or "full_context"
    raw_response: Dict


class LLMQueryPlanner:
    """
    Plans queries using LLM to determine strategy and generate executable queries.

    Single-call approach:
    - Analyzes natural language query
    - Determines optimal strategy
    - Generates ready-to-execute SQL or SPARQL
    - Provides reasoning and confidence score
    """

    # System prompt template
    SYSTEM_PROMPT_TEMPLATE = """You are a query strategy analyzer and SQL/SPARQL query generator for a contract database system.

Your task: Analyze the user's natural language query and return a complete query plan including:
1. Optimal execution strategy
2. Ready-to-execute SQL or SPARQL query
3. Execution plan details
4. Confidence score and reasoning

# DATABASE SCHEMA

{database_schema}

# GRAPH ONTOLOGY (for SPARQL queries)

{ontology_info}

# QUERY STRATEGIES

{strategy_rules}

# CRITICAL RULES

1. **ENTITY_FIRST Requirements**:
   - EXACTLY ONE positive entity from ONE collection
   - NO negations ("not", "excluding", "except")
   - NO OR lists ("California or Texas")
   - Multi-step execution: query entity collection → get contract IDs → batch retrieve contracts

2. **CONTRACT_DIRECT Requirements**:
   - Use for: multiple entities, negations, OR lists, complex filters
   - Operators: = (single), != (negation), IN (OR list), NOT IN (multiple negations)
   - Direct SQL on contracts collection

3. **ENTITY_AGGREGATION Requirements**:
   - Count/sum/average queries on single entity
   - Use pre-computed stats_fields (contract_count, total_value)
   - Query entity collection directly for instant results

4. **GRAPH_TRAVERSAL Requirements**:
   - Relationship keywords: "between", "connected", "depends on", "related to"
   - Generate SPARQL with proper PREFIX declarations
   - Use caig: namespace for all classes and properties

5. **Query Generation Rules**:
   - SQL: Use CosmosDB SQL syntax (SELECT TOP N * FROM c WHERE ...)
   - SPARQL: Include PREFIX declarations, use correct property directions
   - Entity normalization: lowercase, underscores replace spaces, remove special chars
   - Examples: "California" → "california", "New York" → "new_york", "Microsoft Corp" → "microsoft"

6. **Result Format Rules**:
   - **"list_summary"**: Use when query returns a LIST of contracts for display
     * Examples: "Show all contracts...", "List contracts...", "Find contracts where..."
     * Only summary fields needed: id, contractor_party, contracting_party, governing_law_state, contract_type, effective_date, expiration_date, maximum_contract_value, filename
     * Avoids filling context with contract_text, clause_id arrays, chunk_id arrays

   - **"full_context"**: Use when query requires REASONING about entire contract
     * Examples: "Summarize this contract...", "What are all the key terms..."
     * Requires full contract_text for complete contract analysis
     * Used for whole contract analysis

   - **"clause_analysis"**: Use when query is specifically about CLAUSES
     * Examples: "What are the termination clauses...", "Find indemnification clauses...", "Compare payment obligations..."
     * MUST query contract_clauses collection (not contracts)
     * Clause types come from clause_types entity collection (similar to contract_types, governing_law_states, etc.)
     * Common clause types: termination_obligations, indemnification, payment_obligations, confidentiality_obligations, limitation_of_liability_obligations, warranty_obligations, compliance_obligations, service_level_agreement
     * Returns clause fields: id, contract_id, clause_type, text

# RESPONSE FORMAT

Return ONLY valid JSON (no markdown, no code blocks):

{{
  "strategy": "ENTITY_FIRST|CONTRACT_DIRECT|ENTITY_AGGREGATION|GRAPH_TRAVERSAL|VECTOR_SEARCH",
  "fallback_strategy": "strategy to use if primary fails",

  "query": {{
    "type": "SQL|SPARQL",
    "text": "complete executable query"
  }},

  "execution_plan": {{
    "collection": "collection name",
    "estimated_ru_cost": number,
    "estimated_results": number,
    "aggregation_field": "field name for aggregation queries (optional)",
    "multi_step": [  // Only for ENTITY_FIRST
      "Step 1: Query governing_law_states for 'california'",
      "Step 2: Extract contract IDs from contracts array",
      "Step 3: Batch retrieve contracts by IDs"
    ]
  }},

  "result_format": "list_summary|full_context|clause_analysis",
  "confidence": 0.0-1.0,
  "reasoning": "clear explanation of strategy choice and query structure"
}}

# EXAMPLES

**Example 1: Single Entity (ENTITY_FIRST)**
User: "Show all contracts governed by California"
Response:
{{
  "strategy": "ENTITY_FIRST",
  "fallback_strategy": "CONTRACT_DIRECT",
  "query": {{
    "type": "SQL",
    "text": "SELECT * FROM c WHERE c.id = 'california'"
  }},
  "execution_plan": {{
    "collection": "governing_law_states",
    "multi_step": [
      "Query governing_law_states for 'california'",
      "Extract contract IDs from contracts array",
      "Batch retrieve contracts by IDs"
    ],
    "estimated_ru_cost": 2,
    "estimated_results": 150
  }},
  "result_format": "list_summary",
  "confidence": 1.0,
  "reasoning": "Single positive entity (California) with no negations or OR lists. ENTITY_FIRST is optimal for low RU cost (~2 RUs vs ~15 RUs for CONTRACT_DIRECT). Result is a list of contracts, so list_summary format is used."
}}

**Example 2: Negation (CONTRACT_DIRECT)**
User: "Show all contracts not governed by Alabama"
Response:
{{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",
  "query": {{
    "type": "SQL",
    "text": "SELECT TOP 100 * FROM c WHERE c.governing_law_state != 'alabama'"
  }},
  "execution_plan": {{
    "collection": "contracts",
    "estimated_ru_cost": 10,
    "estimated_results": 85
  }},
  "result_format": "list_summary",
  "confidence": 0.98,
  "reasoning": "Negation query. ENTITY_FIRST cannot handle negations (would need all contracts except Alabama). CONTRACT_DIRECT with != operator is required. Result is a list of contracts, so list_summary format is used."
}}

**Example 3: OR List (CONTRACT_DIRECT)**
User: "Show contracts in California, Texas, or Florida"
Response:
{{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",
  "query": {{
    "type": "SQL",
    "text": "SELECT TOP 100 * FROM c WHERE c.governing_law_state IN ('california', 'texas', 'florida')"
  }},
  "execution_plan": {{
    "collection": "contracts",
    "estimated_ru_cost": 15,
    "estimated_results": 45
  }},
  "result_format": "list_summary",
  "confidence": 0.97,
  "reasoning": "OR list with 3 states. ENTITY_FIRST requires single entity. CONTRACT_DIRECT with IN operator handles multiple values efficiently. Result is a list of contracts, so list_summary format is used."
}}

**Example 4: Aggregation (ENTITY_AGGREGATION)**
User: "How many contracts are governed by California?"
Response:
{{
  "strategy": "ENTITY_AGGREGATION",
  "fallback_strategy": "CONTRACT_DIRECT",
  "query": {{
    "type": "SQL",
    "text": "SELECT * FROM c WHERE c.id = 'california'"
  }},
  "execution_plan": {{
    "collection": "governing_law_states",
    "aggregation_field": "contract_count",
    "estimated_ru_cost": 1,
    "estimated_results": 1
  }},
  "result_format": "list_summary",
  "confidence": 0.99,
  "reasoning": "Count query on single entity. Pre-computed contract_count in governing_law_states provides instant 1 RU result. Aggregation result, so list_summary format is sufficient."
}}

**Example 5: Clause Analysis (clause_analysis)**
User: "What are the termination clauses in the Microsoft contract?"
Response:
{{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",
  "query": {{
    "type": "SQL",
    "text": "SELECT TOP 20 * FROM c WHERE c.clause_type = 'termination_obligations'"
  }},
  "execution_plan": {{
    "collection": "contract_clauses",
    "estimated_ru_cost": 15,
    "estimated_results": 20
  }},
  "result_format": "clause_analysis",
  "confidence": 0.95,
  "reasoning": "Query specifically asks for termination clauses. Must query contract_clauses collection with clause_type filter. Returns clause records with id, contract_id, clause_type, and text fields for analysis. clause_analysis format is required."
}}

**Example 6: Full Contract Analysis (full_context)**
User: "Summarize the entire Microsoft contract"
Response:
{{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",
  "query": {{
    "type": "SQL",
    "text": "SELECT TOP 5 * FROM c WHERE c.contractor_party = 'microsoft' OR c.contracting_party = 'microsoft'"
  }},
  "execution_plan": {{
    "collection": "contracts",
    "estimated_ru_cost": 20,
    "estimated_results": 5
  }},
  "result_format": "full_context",
  "confidence": 0.90,
  "reasoning": "Query requires summarizing entire contract content. Need full contract_text and all fields for complete analysis. Uses contracts collection. full_context format is required."
}}

**Example 7: Clause Type Aggregation (ENTITY_AGGREGATION)**
User: "How many termination clauses are there?"
Response:
{{
  "strategy": "ENTITY_AGGREGATION",
  "fallback_strategy": "CONTRACT_DIRECT",
  "query": {{
    "type": "SQL",
    "text": "SELECT * FROM c WHERE c.id = 'termination_obligations'"
  }},
  "execution_plan": {{
    "collection": "clause_types",
    "aggregation_field": "clause_count",
    "estimated_ru_cost": 1,
    "estimated_results": 1
  }},
  "result_format": "list_summary",
  "confidence": 0.99,
  "reasoning": "Count query on single clause type entity. Pre-computed clause_count in clause_types collection provides instant 1 RU result. Similar to contract entity aggregations."
}}

Analyze the user's query and generate the complete query plan.
"""

    def __init__(self,
                 schema_builder: Optional[StrategySchemaBuilder] = None,
                 azure_client: Optional[AzureOpenAI] = None):
        """
        Initialize LLM query planner.

        Args:
            schema_builder: Schema builder instance (creates new if None)
            azure_client: Azure OpenAI client (creates new if None)
        """
        self.schema_builder = schema_builder or StrategySchemaBuilder()

        self.client = azure_client or AzureOpenAI(
            api_key=ConfigService.azure_openai_key(),
            api_version="2024-02-15-preview",
            azure_endpoint=ConfigService.azure_openai_url()
        )

        self.deployment = ConfigService.azure_openai_completions_deployment()

        # Load context once at initialization
        self.context = self.schema_builder.build_llm_context()

    def _build_system_prompt(self) -> str:
        """
        Build complete system prompt with schema and ontology context.

        Returns:
            Complete system prompt string
        """
        # Format database schema
        schema_info = self.context['database_schema']
        db_schema_text = f"""Database: {schema_info['database']}
Schema Version: {schema_info['schema_version']}

Collections:
"""
        for coll_name, coll_info in schema_info['collections'].items():
            db_schema_text += f"\n{coll_name}:\n"
            db_schema_text += f"  Description: {coll_info['description']}\n"
            db_schema_text += f"  Primary Key: {coll_info['primary_key']}\n"
            db_schema_text += "  Fields:\n"
            for field in coll_info.get('fields', []):
                db_schema_text += f"    - {field['name']} ({field['type']}): {field['description']}\n"
            if coll_info.get('supports'):
                db_schema_text += f"  Supports: {', '.join(coll_info['supports'])}\n"

        # Format ontology
        ont_info = self.context['ontology']
        ontology_text = f"""Namespace: {ont_info['namespace']}
Prefix: {ont_info['prefix']}

Classes:
"""
        for cls in ont_info['classes'][:10]:  # Limit to avoid token bloat
            ontology_text += f"  - {ont_info['prefix']}:{cls['id']}: {cls['description']}\n"

        ontology_text += "\nKey Object Properties (relationships):\n"
        for prop in ont_info['object_properties'][:10]:
            ontology_text += f"  - {ont_info['prefix']}:{prop['id']}: {prop['description']}\n"
            if prop.get('domain') and prop.get('range'):
                ontology_text += f"    {prop['domain']} → {prop['range']}\n"

        # Format strategy rules
        strategy_text = ""
        for strat_name, strat_info in schema_info.get('query_strategies', {}).items():
            strategy_text += f"\n{strat_name}:\n"
            strategy_text += f"  Description: {strat_info['description']}\n"
            strategy_text += f"  Use When: {strat_info['use_when']}\n"
            strategy_text += f"  RU Cost: {strat_info['ru_cost']}\n"
            strategy_text += f"  Example: {strat_info['example']}\n"

        return self.SYSTEM_PROMPT_TEMPLATE.format(
            database_schema=db_schema_text,
            ontology_info=ontology_text,
            strategy_rules=strategy_text
        )

    def plan_query(self, natural_language_query: str, timeout: float = 10.0) -> LLMQueryPlan:
        """
        Generate complete query plan from natural language.

        Args:
            natural_language_query: User's natural language query
            timeout: Timeout in seconds for LLM call

        Returns:
            LLMQueryPlan with strategy and executable query

        Raises:
            Exception: If LLM call fails or response is invalid
        """
        logger.info(f"Planning query: {natural_language_query}")

        system_prompt = self._build_system_prompt()

        try:
            # Single LLM call for strategy + query generation
            response = self.client.chat.completions.create(
                model=self.deployment,
                temperature=0.0,  # Deterministic
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": natural_language_query}
                ],
                timeout=timeout
            )

            # Parse JSON response
            llm_response = json.loads(response.choices[0].message.content)

            # Extract query plan
            plan = LLMQueryPlan(
                strategy=llm_response.get('strategy', 'VECTOR_SEARCH'),
                fallback_strategy=llm_response.get('fallback_strategy', 'VECTOR_SEARCH'),
                query_type=llm_response.get('query', {}).get('type', 'SQL'),
                query_text=llm_response.get('query', {}).get('text', ''),
                execution_plan=llm_response.get('execution_plan', {}),
                confidence=llm_response.get('confidence', 0.0),
                reasoning=llm_response.get('reasoning', ''),
                result_format=llm_response.get('result_format', 'list_summary'),
                raw_response=llm_response
            )

            logger.info(f"Generated plan: strategy={plan.strategy}, "
                       f"query_type={plan.query_type}, confidence={plan.confidence:.2f}")

            return plan

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from LLM: {e}")
            raise

        except Exception as e:
            logger.error(f"LLM query planning failed: {e}")
            raise
