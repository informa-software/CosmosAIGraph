"""
LLM Query Planner

Uses Azure OpenAI to generate query strategies and executable SQL/SPARQL queries
in a single call. Provides reasoning for strategy choices and handles complex
query patterns that regex-based approaches struggle with.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
from openai import AzureOpenAI

from src.services.config_service import ConfigService
from src.services.llm_usage_tracker import LLMUsageTracker
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
    result_format: str  # "list_summary" or "full_context" or "clause_analysis"
    entities: Dict  # Entity extraction for normalization
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

**PRIMARY RULE - ALWAYS QUERY CONTRACTS COLLECTION**:
   - For ALL contract data queries, ALWAYS use the "contracts" collection
   - Entity collections (contractor_parties, contracting_parties, governing_law_states, contract_types) are for internal optimization ONLY
   - NEVER generate queries against entity collections directly
   - Use WHERE clauses on contracts collection: c.contracting_party, c.contractor_party, c.governing_law_state, c.contract_type

1. **CONTRACT_DIRECT Strategy** (PRIMARY - USE THIS FOR MOST QUERIES):
   - Use for: ALL contract queries including entity filters, text search, date ranges, any filters
   - Query the "contracts" collection with WHERE clauses
   - Use placeholders for entity values: :contractor_party_1, :contracting_party_1, etc.
   - Operators: = (single), != (negation), IN (OR list), NOT IN (multiple negations)
   - Example: SELECT TOP 50 * FROM c WHERE c.contracting_party = :party_1 AND FULLTEXTCONTAINS(c.contract_text, 'term')

2. **ENTITY_FIRST Strategy** (INTERNAL OPTIMIZATION - RARELY USED):
   - DO NOT USE for queries with text search or multiple filters
   - Only for: EXACTLY ONE positive entity with NO other filters
   - NO negations ("not", "excluding", "except")
   - NO OR lists ("California or Texas")
   - NO text search or additional filters
   - System handles this internally - prefer CONTRACT_DIRECT instead

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
   - **CRITICAL**: CosmosDB does NOT support:
     * Cross-container subqueries (SELECT ... WHERE id IN (SELECT id FROM other_container))
     * Subqueries across different containers
     * Each query must target EXACTLY ONE collection
   - **Full-Text Search**: Use FULLTEXTCONTAINS(c.contract_text, 'term') for searching within contract text
     * Example: WHERE c.contracting_party = 'acme' AND FULLTEXTCONTAINS(c.contract_text, 'liability')
     * DO NOT use CONTAINS() - it is not supported for full-text search
   - SPARQL: Include PREFIX declarations, use correct property directions
   - **Entity Normalization** (CRITICAL - ALWAYS REQUIRED):
     * **ALWAYS use placeholders** for ANY entity values (party names, states, types, clauses)
     * Party names: "Malone Forestry" → use :contractor_party_1 placeholder
     * States: "California" → use :governing_law_state_1 placeholder
     * Contract types: "MSA" → use :contract_type_1 placeholder
     * Clause types: "termination obligations" → use :clause_type_1 placeholder
     * **MUST include "entities" dict** mapping each placeholder to {{"raw_value": "...", "entity_type": "..."}}
     * Python will normalize using fuzzy matching (85% threshold) and replace placeholders

6. **Result Format Rules** (Choose carefully based on query intent):
   - **"list_summary"**: Use when query wants a LIST/OVERVIEW of multiple contracts
     * Examples: "Show all contracts...", "List contracts...", "Find contracts where...", "How many contracts..."
     * Returns summary fields only (no contract_text): id, contractor_party, contracting_party, governing_law_state, contract_type, effective_date, expiration_date, maximum_contract_value, filename
     * Avoids filling context with contract_text, clause_id arrays, chunk_id arrays

   - **"full_context"**: Use when query needs to ANALYZE/REASON about specific contract content
     * Examples:
       - "What are the risks in the contract with X?"
       - "What does the contract say about Y?"
       - "Summarize the contract with Z"
       - "Analyze the terms in X's contract"
       - "What are the key obligations for X?"
     * **CRITICAL**: Returns full contract_text for AI reasoning
     * Use when answer requires reading and analyzing the actual contract text
     * Typically returns 1-5 contracts (not large lists)

   - **"clause_analysis"**: Use when query is specifically about CLAUSES
     * Examples: "What are the termination clauses...", "Find indemnification clauses...", "Compare payment obligations..."
     * MUST query contract_clauses collection (not contracts)
     * Clause types come from clause_types entity collection (similar to contract_types, governing_law_states, etc.)
     * Common clause types: termination_obligations, indemnification, payment_obligations, confidentiality_obligations, limitation_of_liability_obligations, warranty_obligations, compliance_obligations, service_level_agreement
     * Returns clause fields: id, contract_id, clause_type, text
     * **IMPORTANT**: governing_law_state is a CONTRACT field, NOT a clause type. If user asks for "governing law", query contracts collection, not contract_clauses
     * To find clauses for specific contracts: Query contracts first to get IDs, then use multi_step to query contract_clauses

# RESPONSE FORMAT

**CRITICAL**: Return ONLY valid JSON - no markdown, no code blocks, no comments (// or #).

**Valid Values**:
- strategy: ENTITY_FIRST, CONTRACT_DIRECT, CLAUSE_DIRECT, ENTITY_AGGREGATION, GRAPH_TRAVERSAL, VECTOR_SEARCH
- fallback_strategy: Same options as strategy
- query.type: SQL or SPARQL
- result_format: list_summary, full_context, clause_analysis
- confidence: Number between 0.0 and 1.0

**CRITICAL - "entities" field is MANDATORY**:
- If your query uses ANY placeholders (:contractor_party_1, :governing_law_state_1, etc.), you MUST include entities dict
- Map EVERY placeholder to its original raw value from the user's query
- Specify the entity_type for each (contractor_party, contracting_party, governing_law_state, contract_type, clause_type)
- ONLY use empty object {{}} if your query has absolutely NO placeholders
- Example: Query has ":contractor_party_1" → entities MUST have "contractor_party_1" entry

**Example Response Format**:

{{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",

  "query": {{
    "type": "SQL",
    "text": "SELECT TOP 20 * FROM c WHERE c.contractor_party = :contractor_party_1"
  }},

  "execution_plan": {{
    "collection": "contracts",
    "estimated_ru_cost": 10,
    "estimated_results": 5
  }},

  "entities": {{
    "contractor_party_1": {{
      "raw_value": "Original name from user query",
      "entity_type": "contractor_party"
    }},
    "governing_law_state_1": {{
      "raw_value": "Original state name",
      "entity_type": "governing_law_state"
    }}
  }},

  "result_format": "list_summary",
  "confidence": 0.95,
  "reasoning": "Clear explanation of strategy choice and query structure"
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

**Example 8: Entity Extraction with Normalization (CONTRACT_DIRECT)**
User: "Show me the governing law for Malone Forestry contracts"
Response:
{{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",
  "query": {{
    "type": "SQL",
    "text": "SELECT TOP 20 c.id, c.governing_law_state, c.contractor_party, c.contracting_party FROM c WHERE c.contractor_party = :contractor_party_1 OR c.contracting_party = :contracting_party_1"
  }},
  "execution_plan": {{
    "collection": "contracts",
    "estimated_ru_cost": 10,
    "estimated_results": 5
  }},
  "entities": {{
    "contractor_party_1": {{
      "raw_value": "Malone Forestry",
      "entity_type": "contractor_party"
    }},
    "contracting_party_1": {{
      "raw_value": "Malone Forestry",
      "entity_type": "contracting_party"
    }}
  }},
  "result_format": "list_summary",
  "confidence": 0.95,
  "reasoning": "Governing_law_state is a field on contracts collection, NOT a clause type. Query contracts directly. Use placeholders for 'Malone Forestry' - Python will normalize using fuzzy matching to handle variations like 'malone forestry', 'Malone Forestry LLC', etc."
}}

**Example 9: Contract Analysis Query (CONTRACT_DIRECT with full_context)**
User: "What are the risks in the contract with Mark Conley?"
Response:
{{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",
  "query": {{
    "type": "SQL",
    "text": "SELECT TOP 5 * FROM c WHERE c.contractor_party = :contractor_party_1 OR c.contracting_party = :contracting_party_1"
  }},
  "execution_plan": {{
    "collection": "contracts",
    "estimated_ru_cost": 10,
    "estimated_results": 2
  }},
  "entities": {{
    "contractor_party_1": {{
      "raw_value": "Mark Conley",
      "entity_type": "contractor_party"
    }},
    "contracting_party_1": {{
      "raw_value": "Mark Conley",
      "entity_type": "contracting_party"
    }}
  }},
  "result_format": "full_context",
  "confidence": 0.92,
  "reasoning": "Query asks to ANALYZE contract content ('What are the risks'). Need full contract_text for AI to read and reason about. Use placeholders for party name. Returns full_context so AI gets contract_text for analysis."
}}

Analyze the user's query and generate the complete query plan.
"""

    def __init__(self,
                 schema_builder: Optional[StrategySchemaBuilder] = None,
                 azure_client: Optional[AzureOpenAI] = None,
                 cosmos_service = None):
        """
        Initialize LLM query planner.

        Args:
            schema_builder: Schema builder instance (creates new if None)
            azure_client: Azure OpenAI client (creates new if None)
            cosmos_service: CosmosDB service for usage tracking (optional)
        """
        self.schema_builder = schema_builder or StrategySchemaBuilder()

        self.client = azure_client or AzureOpenAI(
            api_key=ConfigService.azure_openai_key(),
            api_version="2024-02-15-preview",
            azure_endpoint=ConfigService.azure_openai_url()
        )

        self.deployment = ConfigService.azure_openai_completions_deployment()

        # Initialize usage tracker if cosmos service provided
        self.llm_tracker = LLMUsageTracker(cosmos_service) if cosmos_service else None

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
            if 'example' in strat_info:
                strategy_text += f"  Example: {strat_info['example']}\n"
            if 'note' in strat_info:
                strategy_text += f"  Note: {strat_info['note']}\n"

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
            t1 = time.perf_counter()

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

            t2 = time.perf_counter()

            # Track query planning usage
            if self.llm_tracker:
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",  # TODO: Get actual user email from request context
                        operation="query_planning",
                        model=response.model,
                        prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                        completion_tokens=response.usage.completion_tokens if response.usage else 0,
                        elapsed_time=t2 - t1,
                        operation_details={
                            "query_preview": natural_language_query[:100],
                            "timeout": timeout
                        },
                        success=True
                    )
                )

            # Get raw response content
            raw_content = response.choices[0].message.content
            logger.info(f"LLM raw response (first 500 chars): {raw_content[:500]}")

            # Parse JSON response
            llm_response = json.loads(raw_content)

            # Debug: Log if entities are present
            query_text = llm_response.get('query', {}).get('text', '')
            has_placeholders = ':' in query_text and any(f':{name}' in query_text for name in ['contractor_party', 'contracting_party', 'governing_law_state', 'contract_type', 'clause_type'])

            if 'entities' in llm_response and llm_response['entities']:
                logger.info(f"LLM returned entities: {llm_response['entities']}")
            elif has_placeholders:
                logger.error(f"CRITICAL: Query contains placeholders but 'entities' field is missing or empty!")
                logger.error(f"Query: {query_text}")
                logger.error(f"Entities in response: {llm_response.get('entities', 'MISSING')}")
                logger.error(f"Full LLM response:\n{json.dumps(llm_response, indent=2)}")
                logger.error("This will cause query execution to fail. LLM must include entities dict when using placeholders.")
            else:
                logger.info("No placeholders in query, entities field not needed")

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
                entities=llm_response.get('entities', {}),
                raw_response=llm_response
            )

            logger.info(f"Generated plan: strategy={plan.strategy}, "
                       f"query_type={plan.query_type}, confidence={plan.confidence:.2f}")

            return plan

        except json.JSONDecodeError as e:
            # Log the full response for debugging
            logger.error(f"Invalid JSON response from LLM: {e}")
            logger.error(f"Raw LLM response:\n{raw_content}")

            # Return error plan with raw response for trace file
            return LLMQueryPlan(
                strategy="VECTOR_SEARCH",
                fallback_strategy="VECTOR_SEARCH",
                query_type="SQL",
                query_text="",
                execution_plan={"error_response": raw_content},
                confidence=0.0,
                reasoning=f"JSON parsing error at {e}",
                result_format="list_summary",
                entities={},
                raw_response={"error": str(e), "raw_content": raw_content}
            )

        except Exception as e:
            logger.error(f"LLM query planning failed: {e}")
            # Return error plan for trace file
            return LLMQueryPlan(
                strategy="VECTOR_SEARCH",
                fallback_strategy="VECTOR_SEARCH",
                query_type="SQL",
                query_text="",
                execution_plan={"error_info": str(e)},
                confidence=0.0,
                reasoning=f"LLM planning error: {str(e)}",
                result_format="list_summary",
                entities={},
                raw_response={"error": str(e)}
            )
