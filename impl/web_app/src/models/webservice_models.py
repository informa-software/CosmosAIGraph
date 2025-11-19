from pydantic import BaseModel
from typing import Any

# This module contains the several Pydantic "models" that define both the
# request and response payloads for the web endpoints in this application.
# Think of these models as "interfaces" that define the "shapes" of actual
# objects.  Pydantic models are an interesting feature of the FastAPI
# webframework.  Using these models, FastAPI can automatically generate
# OpenAPI/Swagger request/response endpoint documentation.
#
# See the correspondig Graph Microservice JSON models in the
# impl/graph_app/src/main/java/com/microsoft/cosmosdb/caig/models/ directory.
#
# See https://fastapi.tiangolo.com/tutorial/response-model/
# See https://fastapi.tiangolo.com/tutorial/body/
#
# Chris Joakim, Microsoft, 2025
# Aleksey Savateyev, Microsoft, 2025


class PingModel(BaseModel):
    epoch: float


class LivenessModel(BaseModel):
    epoch: float
    alive: bool
    rows_read: int


class OwlInfoModel(BaseModel):
    ontology_file: str
    owl: str
    epoch: float
    error: str | None


class SparqlQueryRequestModel(BaseModel):
    sparql: str

    # Corresponding Java code
    # private String sparql;


class SparqlQueryResponseModel(BaseModel):
    sparql: str
    results: Any = None
    elapsed: int
    row_count: int
    error: str | None
    start_time: int
    finish_time: int

    # Corresponding Java code
    # private String sparql;
    # private Map<String, Object> results = new HashMap<>();
    # private long elapsed;
    # private String error;
    # private long start_time;
    # private long finish_time;


class SparqlBomQueryRequestModel(BaseModel):
    libname: str
    max_depth: int

    # Corresponding Java code
    # private String libname;
    # private int max_depth;


class SparqlBomQueryResponseModel(BaseModel):
    libname: str
    max_depth: int
    actual_depth: int
    libs: dict | None
    error: str | None
    elapsed: float
    request_time: float

    # Corresponding Java code
    # private String libname;
    # private int max_depth;
    # private int actual_depth;
    # private HashMap<String, TraversedLib> libs;
    # private String error;
    # private long elapsed;
    # private long request_time;


class SparqlGenerationRequestModel(BaseModel):
    session_id: str | None
    natural_language: str
    owl: str


class SparqlGenerationResponseModel(BaseModel):
    session_id: str | None
    natural_language: str
    completion_id: str
    completion_model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    epoch: int
    elapsed: float
    sparql: str
    error: str | None


class AiConvFeedbackModel(BaseModel):
    conversation_id: str
    feedback_last_question: str
    feedback_user_feedback: str


class DocumentsVSResultsModel(BaseModel):
    libtype: str
    libname: str
    count: int
    doc: dict | None
    results: list
    elapsed: float
    error: str | None


class VectorizeRequestModel(BaseModel):
    session_id: str | None
    text: str


class VectorizeResponseModel(BaseModel):
    session_id: str | None
    text: str
    embeddings: list
    elapsed: float
    error: str | None


class QueryContractsRequestModel(BaseModel):
    question: str
    contract_ids: list[str]


class QueryContractsResponseModel(BaseModel):
    answer: str
    contracts_analyzed: list[str]
    was_truncated: bool
    truncated_contracts: list[str] | None
    total_tokens_used: int
    elapsed: float
    error: str | None


class QueryContractsDirectRequestModel(BaseModel):
    """Request model for direct contract query (no LLM completion)"""
    query: str
    limit: int = 20
    strategy_override: str | None = None  # Optional: "db", "vector", or "graph"
    # Filter parameters for programmatic query building (bypasses LLM)
    # Support both single values and arrays for multi-select
    contractor_party: str | list[str] | None = None
    contracting_party: str | list[str] | None = None
    governing_law_state: str | list[str] | None = None
    contract_type: str | list[str] | None = None
    offset: int = 0  # For pagination


class QueryContractsDirectResponseModel(BaseModel):
    """Response model for direct contract query"""
    query: str
    result_format: str
    strategy: str
    documents: list[dict]
    document_count: int
    ru_cost: float
    execution_time_ms: float
    error: str | None
    execution_trace: dict | None

