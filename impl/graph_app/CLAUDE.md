# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Build and Package
```bash
# Windows
.\build.ps1

# Linux/macOS
./build.sh

# Using Gradle directly
gradle clean
gradle build -x test
gradle jar
```

### Run the Application
```bash
# Windows
.\gradlew.bat bootRun
# or
.\graph_app.ps1

# Linux/macOS
gradle bootRun
# or
./graph_app.sh
```

### Testing
```bash
# Run all tests
gradle test

# Run specific test class
gradle test --tests "*GraphTests"
```

### Console Application Tasks
```bash
# Invoke Graph Builder
gradle consoleAppInvokeGraphBuilder

# Generate Artifacts
gradle consoleAppGenerateArtifacts

# Post SPARQL Add Documents
gradle consoleAppPostSparqlAddDocuments
```

## Configuration

### Environment Setup
1. Create tmp directory if it doesn't exist: `mkdir tmp`
2. Copy `example-override.properties` to `.override.properties`
3. Configure `.override.properties` with your specific settings:
   - **CAIG_GRAPH_SOURCE_TYPE**: One of `cosmos_nosql`, `rdf_file`, or `json_docs_file`
   - **CAIG_COSMOSDB_NOSQL_URI**: Your CosmosDB URI (if using cosmos_nosql)
   - **CAIG_COSMOSDB_NOSQL_KEY**: Your CosmosDB key (if using cosmos_nosql)
   - **CAIG_GRAPH_MODE**: Either `libraries` (default) or `contracts`
   
   For contracts mode:
   - **CAIG_GRAPH_SOURCE_DB**: Database name (e.g., `caig`)
   - **CAIG_GRAPH_SOURCE_CONTAINER**: Container name (e.g., `contracts`)
   - **CAIG_GRAPH_SOURCE_OWL_FILENAME**: Path to ontology (e.g., `ontologies/contracts.owl`)

## Architecture Overview

### Core Components

**Spring Boot Application**
- Main entry: `com.microsoft.cosmosdb.caig.WebApp` - Spring Boot application with REST API on port 8001
- Console app: `com.microsoft.cosmosdb.caig.ConsoleApp` - Command-line utility for batch operations

**Graph Management**
- `AppGraph`: Singleton graph instance containing Apache Jena RDF model in JVM memory
- `AppGraphBuilder`: Factory for building AppGraph from three sources (CosmosDB NoSQL, RDF file, or JSON documents)
- Graph loaded at startup via `AppStartup` component

**Data Sources**
- **cosmos_nosql**: Loads RDF triples from Azure CosmosDB NoSQL database
- **rdf_file**: Loads from local RDF file (development mode)
- **json_docs_file**: Loads from captured CosmosDB documents JSON file (development mode)

**REST API Endpoints** (GraphRestController)
- `GET /ontology`: Returns OWL/XML ontology
- `POST /sparql_query`: Execute SPARQL queries against the graph
- `POST /sparql_update`: Update the graph with SPARQL
- `POST /sparql_bom_query`: Bill of Materials query for D3.js visualizations
- `POST /add_documents`: Add documents from database to graph
- `GET /reload_graph`: Reload graph from source (dev environment)

**Additional REST Controllers**
- `PingRestController`: Health check endpoints
- `HealthRestController`: Application health monitoring

### Key Dependencies
- **Apache Jena 5.x**: RDF graph processing and SPARQL queries
- **Spring Boot 4.0.0-M2**: Web framework
- **Azure Cosmos SDK 4.x**: CosmosDB connectivity
- **Lombok**: Boilerplate reduction

### Requirements
- Java 21
- Gradle 8.11 or 8.12

## Development Notes

### Graph Source Configuration
The graph source is determined by `CAIG_GRAPH_SOURCE_TYPE` in `.override.properties`. The AppGraphBuilder creates the appropriate graph based on this setting during application startup.

### SPARQL Query Handling
All SPARQL queries are processed through the singleton AppGraph instance, which maintains an in-memory Apache Jena Model. The model supports both queries and updates through the REST API.

### Ontology Management
The application uses OWL ontologies stored in the `ontologies/` directory. The primary ontology file is configured via environment variables and served through the `/ontology` endpoint.

### Testing Approach
- Unit tests in `src/test/java/`
- Use JUnit and Spring Boot Test framework
- Mock external dependencies when testing graph operations