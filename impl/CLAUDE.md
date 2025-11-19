# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a microservices-based knowledge graph system with AI capabilities, consisting of:
- **graph_app**: Java/Spring Boot graph service using Apache Jena for RDF/SPARQL (port 8001)
- **web_app**: Python/FastAPI web application with Azure OpenAI integration (port 8000)

## Development Commands

### Java Graph Service (graph_app/)

#### Build and Package
```bash
# Windows
.\build.ps1

# Linux/macOS
./build.sh
```

#### Run Locally
```bash
# Windows
.\graph_app.ps1

# Linux/macOS
./graph_app.sh

# Or directly with Gradle
gradle bootRun
```

#### Testing
```bash
# Run all tests
gradle test

# Run specific test class
gradle test --tests "*GraphTests"
```

#### Console Tasks
```bash
gradle consoleAppInvokeGraphBuilder    # Build graph from source
gradle consoleAppGenerateArtifacts     # Generate ontology artifacts  
gradle consoleAppPostSparqlAddDocuments # Add documents via SPARQL
```

### Contract Entity System

#### Overview
The contract entity system manages and tracks entities extracted from contracts:
- **Contractor Parties**: Companies/individuals performing work
- **Contracting Parties**: Companies/individuals initiating contracts
- **Governing Laws**: Jurisdictions that govern contracts
- **Contract Types**: MSA, NDA, SOW, etc.

#### Architecture: Option 2 - Separate Entity Collections
Uses separate CosmosDB containers for each entity type:
- `contractor_parties` container
- `contracting_parties` container
- `governing_laws` container
- `contract_types` container
- `config` container holds the reference document

#### Key Components

**ContractEntitiesService** (`web_app/src/services/contract_entities_service.py`):
- Manages entity catalogs with in-memory caching
- Provides fuzzy matching (85% threshold) for entity identification
- Tracks entity statistics (contract counts, total values)
- TODO: Implement sophisticated matching (phonetic, n-gram, ML-based)

**ContractStrategyBuilder** (`web_app/src/services/contract_strategy_builder.py`):
- Determines query strategy (db/vector/graph) for contract queries
- Identifies entities in natural language queries
- TODO: Implement NER, semantic similarity, query templates

**Entity Building During Contract Loading**:
- `main_contracts.py` automatically builds entity catalogs during ingestion
- Entities are updated in real-time as contracts are loaded
- Statistics are tracked per entity (contract count, total value)

#### Entity Normalization
- Converts to lowercase
- Removes special characters
- Replaces spaces with underscores
- Removes common suffixes (LLC, Inc, Corp) for matching

#### Usage

```bash
# Load contracts with entity building
python main_contracts.py load_contracts caig contracts data/contracts 999999
```

Entities are automatically:
1. Extracted from contract metadata
2. Normalized for consistent storage
3. Stored in separate containers
4. Cached in memory for fast lookup
5. Persisted after all contracts are loaded

### Python Web App (web_app/)

#### Setup Virtual Environment
```bash
# Windows
.\venv.ps1

# Linux/macOS
./venv.sh
```

#### Run Locally
```bash
# Windows
.\web_app.ps1

# Linux/macOS
./web_app.sh
```

#### Testing
```bash
# Windows
.\tests.ps1

# Run individual test
pytest -v tests/test_config_service.py

# With coverage
pytest -v --cov=src/ --cov-report html tests/
```

#### Entity Initialization
The web app automatically initializes `ContractEntitiesService` for contract entity management at startup.

#### Contract Data Loading
```bash
# Load contracts with embeddings generated at runtime
python main_contracts.py load_contracts caig contracts data/contracts 999999

# Preprocess contracts to generate and save embeddings
python main_contracts.py preprocess_contracts data/contracts data/contracts/processed

# Load preprocessed contracts (faster, no embedding generation)
python main_contracts.py load_contracts caig contracts data/contracts/processed 999999
```

### Docker Deployment

```bash
# Run both services
docker compose -f docker-compose.yml up

# Stop services
docker compose -f docker-compose.yml down
```

## Configuration

### Environment Setup
1. Copy `set-caig-env-vars-sample.ps1` to `set-caig-env-vars.ps1` and configure with your Azure resources
2. For Java: Copy `graph_app/example-override.properties` to `graph_app/.override.properties`
3. For Python: Create `web_app/.env` file based on `web_app/dotenv_example`

### Key Environment Variables
- `CAIG_GRAPH_SOURCE_TYPE`: One of `cosmos_nosql`, `rdf_file`, or `json_docs_file`
- `CAIG_COSMOSDB_NOSQL_URI`: Azure CosmosDB endpoint
- `CAIG_COSMOSDB_NOSQL_KEY`: CosmosDB access key
- `CAIG_AZURE_OPENAI_URL`: Azure OpenAI endpoint
- `CAIG_AZURE_OPENAI_KEY`: Azure OpenAI key
- `CAIG_AZURE_OPENAI_COMPLETIONS_DEP`: Deployment name for completions model
- `CAIG_AZURE_OPENAI_EMBEDDINGS_DEP`: Deployment name for embeddings model

## Architecture

### Graph Service (Java/Jena)
- **AppGraph**: Singleton in-memory RDF graph using Apache Jena
- **AppGraphBuilder**: Factory for building graph from CosmosDB, RDF files, or JSON documents
- **GraphRestController**: REST endpoints for SPARQL queries and graph operations
- **Triple Builders**:
  - `ContractsGraphTriplesBuilder`: For contract/contractor/governing law relationships
- **Data Sources**: 
  - `cosmos_nosql`: Live CosmosDB connection
  - `rdf_file`: Local RDF file for development
  - `json_docs_file`: Cached CosmosDB documents

### Web Application (Python/FastAPI)
- **AiService**: Azure OpenAI integration for completions and embeddings
- **CosmosNoSQLService**: CosmosDB client for document operations and vector search
  - ⚠️ **CRITICAL**: See `web_app/COSMOSDB_SERVICE_PATTERNS.md` for correct usage patterns
  - Must use `query_items()`, `parameterized_query()`, `upsert_item()` (NOT `query_documents()`, `get_document()`, `upsert_document()`)
  - Must call `set_container()` before every operation
- **RAGDataService**: RAG (Retrieval Augmented Generation) orchestration
- **AiConversation**: Conversation state management with context
- **ContractEntitiesService**: Contract entity extraction and processing
- **OntologyService**: OWL ontology management and SPARQL generation
- **ClauseLibraryService**: Clause library management with AI-powered comparison and vector search

### API Endpoints

#### Graph Service (port 8001)
- `GET /ping`: Health check
- `GET /health`: Detailed health status
- `GET /ontology`: Returns OWL/XML ontology
- `POST /sparql_query`: Execute SPARQL SELECT queries
- `POST /sparql_update`: Execute SPARQL UPDATE operations
- `POST /sparql_bom_query`: Bill of Materials query for visualizations
- `POST /add_documents`: Add CosmosDB documents to graph
- `GET /reload_graph`: Reload graph from source (dev only)

#### Web Application (port 8000)
- `GET /`: Home page
- `GET /sparql_console`: SPARQL query interface
- `GET /gen_sparql_console`: AI-powered SPARQL generation
- `GET /conv_ai_console`: Conversational AI interface
- `GET /vector_search_console`: Vector search interface
- `POST /gen_sparql`: Generate SPARQL from natural language
- `POST /invoke_sparql`: Execute SPARQL query
- `POST /vector_search`: Perform vector similarity search
- `POST /ai_completion`: Get AI completions
- `POST /liveness`: Application health check

## Testing Strategy

### Graph Service
- Unit tests with JUnit and Spring Boot Test
- Mock external dependencies when testing graph operations
- Test data in `graph_app/data/` and `graph_app/samples/`

### Web Application
- pytest framework with async support
- Tests use live services (CosmosDB, Azure OpenAI) - ensure environment configured
- Coverage target: 80% for unit tests, 70% for integration
- Test data in `web_app/samples/`

## Development Notes

### Requirements
- **Java**: 21+ (for graph service)
- **Gradle**: 8.11 or 8.12
- **Python**: 3.12.9 (for web app)
- **Docker**: For containerized deployment

### Graph Data Flow
1. Data loaded from CosmosDB/files into Apache Jena RDF model at startup
2. SPARQL queries processed against in-memory graph
3. Graph can be reloaded via `/reload_graph` endpoint (dev only)
4. Updates persisted back to CosmosDB when using `cosmos_nosql` source

### AI Integration Flow
1. User query → Entity extraction → Vector embeddings
2. Vector search in CosmosDB → Retrieve relevant documents
3. Context + documents → Azure OpenAI → Generated response
4. Conversation history maintained in CosmosDB

### Common Development Tasks

#### Add New RDF Triples
1. Update ontology in `ontologies/contracts.owl`
2. Add triples via SPARQL UPDATE or reload from data source
3. Reload graph via endpoint or restart service

#### Update Vector Index Policy
1. Modify policy in `web_app/config/cosmosdb_nosql_contract_parents_index_policy*.json`
2. Apply to CosmosDB container via Azure Portal or CLI
3. Restart web app to use new policy

#### Debug SPARQL Queries
1. Use `/sparql_console` in web app for interactive testing
2. Enable debug logging: Set `CAIG_LOG_LEVEL=debug`
3. Check `tmp/` directory for captured query/response JSON files

### Performance Considerations
- Graph service maintains entire RDF model in memory - monitor heap usage
- Use `CAIG_GRAPH_SOURCE_TYPE=json_docs_file` for faster development iteration
- Vector search performance depends on CosmosDB index configuration
- Web app uses hypercorn with configurable workers via `WEB_CONCURRENCY`