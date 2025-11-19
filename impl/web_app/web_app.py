# This is the entry-point for this web application, built with the
# FastAPI web framework.
#
# This implementation contains several 'FS.write_json(...)' calls
# to write out JSON files to the 'tmp' directory for understanding
# and debugging purposes.
#
# Chris Joakim, Aleksey Savateyev
 
import asyncio
import json
import logging
import sys
import textwrap
import time
import traceback

import httpx

from contextlib import asynccontextmanager
from openai import AsyncAzureOpenAI

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Response, Form, status, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from markdown import markdown
from jinja2 import Environment

# next three lines for authentication with MSAL
from fastapi import Depends
from starlette.middleware.sessions import SessionMiddleware

# Pydantic models defining the "shapes" of requests and responses
from src.models.webservice_models import PingModel
from src.models.webservice_models import LivenessModel
from src.models.webservice_models import AiConvFeedbackModel
from src.models.webservice_models import QueryContractsDirectRequestModel
from src.models.webservice_models import QueryContractsDirectResponseModel

# Services with Business Logic
from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.services.contract_entities_service import ContractEntitiesService
from src.services.contract_strategy_builder import ContractStrategyBuilder
from src.services.logging_level_service import LoggingLevelService
from src.services.ontology_service import OntologyService
from src.services.rag_data_service import RAGDataService
from src.services.rag_data_result import RAGDataResult
from src.services.blob_storage_service import BlobStorageService
from src.services.content_understanding_service import ContentUnderstandingService
from src.util.fs import FS

# Routers
from routers.compliance_router import router as compliance_router
from routers.rule_sets_router import router as rule_sets_router
from routers.word_addin_router import router as word_addin_router
from routers.analysis_results_router import router as analysis_results_router
from routers.clause_library_router import router as clause_library_router, set_clause_service
from routers.user_preferences_router import router as user_prefs_router, set_cosmos_service as set_prefs_cosmos_service
from routers.analytics_router import router as analytics_router, set_cosmos_service as set_analytics_cosmos_service
from routers.jobs_router import router as jobs_router
from src.services.clause_library_service import ClauseLibraryService
from src.util.sparql_formatter import SparqlFormatter
from src.util.sparql_query_response import SparqlQueryResponse
from typing import Optional

import debugpy
import os

if os.getenv("CAIG_WAIT_FOR_DEBUGGER") is not None:
    # Allow other computers to attach to debugpy at this IP address and port.
    debugpy.listen(("0.0.0.0", 5678))

    logging.info("CAIG_WAIT_FOR_DEBUGGER: " + os.getenv("CAIG_WAIT_FOR_DEBUGGER"))
    # This will ensure that the debugger waits for you to attach before running the code.
    if os.getenv("CAIG_WAIT_FOR_DEBUGGER").lower() == "true":
        print("Waiting for debugger attach...")
        debugpy.wait_for_client()
        print("Debugger attached, starting FastAPI app...")


# standard initialization
load_dotenv(override=True)
logging.basicConfig(
    format="%(asctime)s - %(message)s", level=LoggingLevelService.get_level()
)

if sys.platform == "win32":
    logging.warning("Windows platform detected, setting WindowsSelectorEventLoopPolicy")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    logging.warning(
        "platform is {}, not Windows.  Not setting event_loop_policy".format(
            sys.platform
        )
    )

ai_svc = AiService()
nosql_svc = CosmosNoSQLService()
rag_data_svc = RAGDataService(ai_svc, nosql_svc, OntologyService)
blob_storage_service: Optional[BlobStorageService] = None
content_understanding_service: Optional[ContentUnderstandingService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Automated startup and shutdown logic for the FastAPI app.
    See https://fastapi.tiangolo.com/advanced/events/#lifespan
    """
    try:
        ConfigService.log_defined_env_vars()
        logging.error(
            "FastAPI lifespan - application_version: {}".format(
                ConfigService.application_version()
            )
        )
        await OntologyService.initialize()
        logging.info(
            "FastAPI lifespan - OntologyService initialized, ontology length: {}".format(
                len(OntologyService.get_owl_content()) if OntologyService.get_owl_content() is not None else 0)
            )
        
        # logging.error("owl:\n{}".format(OntologyService.get_owl_content()))
        await ai_svc.initialize()
        logging.error("FastAPI lifespan - AiService initialized")
        await nosql_svc.initialize()
        logging.error("FastAPI lifespan - CosmosNoSQLService initialized")
        
        # Initialize contract entities
        await ContractEntitiesService.initialize()
        entity_stats = ContractEntitiesService.get_statistics()
        logging.error(
            "FastAPI lifespan - ContractEntitiesService initialized, stats: {}".format(
                json.dumps(entity_stats)
            )
        )

        # Initialize clause library service
        clause_library_svc = ClauseLibraryService(nosql_svc, ai_svc)
        await clause_library_svc.initialize()
        set_clause_service(clause_library_svc)
        logging.error("FastAPI lifespan - ClauseLibraryService initialized")

        # Initialize user preferences router with cosmos service
        set_prefs_cosmos_service(nosql_svc)
        logging.error("FastAPI lifespan - UserPreferencesRouter initialized with CosmosDB service")

        # Initialize analytics router with cosmos service
        set_analytics_cosmos_service(nosql_svc)
        logging.error("FastAPI lifespan - AnalyticsRouter initialized with CosmosDB service")

        # Initialize Blob Storage Service for contract PDFs
        global blob_storage_service
        try:
            conn_str = ConfigService.azure_storage_connection_string()
            if conn_str:
                blob_storage_service = BlobStorageService(
                    connection_string=conn_str,
                    container_name=ConfigService.azure_storage_container(),
                    folder_prefix=ConfigService.azure_storage_folder_prefix()
                )
                logging.error("FastAPI lifespan - BlobStorageService initialized successfully")
            else:
                logging.warning("FastAPI lifespan - Blob storage connection string not configured - PDF access will not be available")
        except Exception as e:
            logging.error(f"FastAPI lifespan - Failed to initialize BlobStorageService: {e}")
            blob_storage_service = None

        # Initialize Content Understanding Service for contract extraction
        global content_understanding_service
        try:
            endpoint = ConfigService.content_understanding_endpoint()
            key = ConfigService.content_understanding_key()
            analyzer_id = ConfigService.content_understanding_analyzer_id()
            api_version = ConfigService.content_understanding_api_version()

            if endpoint and key and analyzer_id:
                content_understanding_service = ContentUnderstandingService(
                    endpoint=endpoint,
                    api_version=api_version,
                    subscription_key=key,
                    analyzer_id=analyzer_id
                )
                logging.error("FastAPI lifespan - ContentUnderstandingService initialized successfully")
            else:
                logging.warning("FastAPI lifespan - Content Understanding not configured - contract upload will not be available")
        except Exception as e:
            logging.error(f"FastAPI lifespan - Failed to initialize ContentUnderstandingService: {e}")
            content_understanding_service = None

        logging.error("ConfigService.graph_service_url():  {}".format(ConfigService.graph_service_url()))
        logging.error("ConfigService.graph_service_port(): {}".format(ConfigService.graph_service_port()))                  
                    
    except Exception as e:
        logging.error("FastAPI lifespan exception: {}".format(str(e)))
        logging.error(traceback.format_exc())

    yield

    logging.info("FastAPI lifespan, shutting down...")
    await nosql_svc.close()
    logging.info("FastAPI lifespan, pool closed")

def markdown_filter(text):
    return markdown(text)

def tojson_pretty(value):
    return json.dumps(value, indent=2, ensure_ascii=False)

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
views = Jinja2Templates(directory="views")
views.env.filters['markdown'] = markdown_filter
views.env.filters['tojson'] = tojson_pretty

# Add CORS middleware to allow Angular app to access the API
origins = [
    "http://localhost:4200",  # Angular dev server (HTTP)
    "http://localhost:4201",  # Alternative port (HTTP)
    "http://127.0.0.1:4200",
    "http://127.0.0.1:4201",
    "https://localhost:4200",  # Angular dev server (HTTPS)
    "https://localhost:4201",  # Office Add-in (HTTPS)
    "https://127.0.0.1:4200",
    "https://127.0.0.1:4201",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.error(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logging.error(f"Response status: {response.status_code}")
    return response

# Enable server-side session to persist conversation_id across posts
try:
    session_secret = os.getenv("CAIG_SESSION_SECRET") or "change-me-dev"
    app.add_middleware(SessionMiddleware, secret_key=session_secret)
except Exception as e:
    logging.warning("Session middleware not added: {}".format(str(e)))

# web service authentication with shared secrets
websvc_auth_header = ConfigService.websvc_auth_header()
websvc_auth_value = ConfigService.websvc_auth_value()
websvc_headers = dict()
websvc_headers["Content-Type"] = "application/json"
websvc_headers[websvc_auth_header] = websvc_auth_value
logging.debug(
    "webapp.py websvc_headers: {}".format(json.dumps(websvc_headers, sort_keys=False))
)
logging.error("webapp.py started")

# Include routers
app.include_router(compliance_router)
logging.error("Included compliance_router")
app.include_router(rule_sets_router)
logging.error("Included rule_sets_router")
app.include_router(word_addin_router)
logging.error("Included word_addin_router")
app.include_router(analysis_results_router)
logging.error("Included analysis_results_router")
logging.error(f"About to include clause_library_router: id={id(clause_library_router)}, prefix={clause_library_router.prefix}, routes={len(clause_library_router.routes)}")
app.include_router(clause_library_router)
logging.error(f"Included clause_library_router successfully")
app.include_router(user_prefs_router)
logging.error("Included user_preferences_router")
app.include_router(analytics_router)
logging.error("Included analytics_router")
app.include_router(jobs_router)
logging.error("Included jobs_router")

# Debug: Check all registered routes
all_routes = [r for r in app.routes if hasattr(r, 'path')]
clause_routes = [r for r in all_routes if 'clause' in str(r.path)]
logging.error(f"Total app routes: {len(all_routes)}, Clause routes: {len(clause_routes)}")

# Log the actual clause routes
logging.error("Registered clause library routes:")
for route in clause_routes:
    methods = getattr(route, 'methods', ['*'])
    logging.error(f"  {list(methods)[0] if methods else 'GET'} {route.path}")


@app.get("/ping")
async def get_ping() -> PingModel:
    resp = dict()
    resp["epoch"] = str(time.time())
    return resp


@app.get("/liveness")
async def get_liveness(req: Request, resp: Response) -> LivenessModel:
    """
    Return a LivenessModel indicating the health of this web app.
    This endpoint is invoked by the Azure Container Apps (ACA) service.
    The implementation validates the environment variable and url configuration.
    """
    alive = True
    if graph_microsvc_sparql_query_url().startswith("http"):
        alive = True
    else:
        alive = False  # unable to reach the graph service due to url config

    if alive == True:
        resp.status_code = status.HTTP_200_OK
    else:
        resp.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    liveness_data = dict()
    liveness_data["alive"] = alive
    liveness_data["rows_read"] = 0
    liveness_data["epoch"] = time.time()
    logging.info("liveness_check: {}".format(liveness_data))
    return liveness_data


@app.get("/")
async def get_home(req: Request):
    global nosql_svc
    # Use the same logic as conv_ai_console to make it the default page
    conv = None
    conversation_id = None
    
    # Check if there's an existing conversation in the session
    try:
        conversation_id = str(req.session.get("conversation_id") or "").strip()
        if conversation_id:
            logging.info("Found existing conversation_id in session: {}".format(conversation_id))
            # Try to load the existing conversation
            try:
                conv = await nosql_svc.load_conversation(conversation_id)
                if conv:
                    logging.info("Loaded existing conversation with {} completions".format(len(conv.completions)))
                else:
                    # Try file-based storage fallback
                    import os
                    import json
                    conv_file_path = f"tmp/conv_{conversation_id}.json"
                    if os.path.exists(conv_file_path):
                        with open(conv_file_path, 'r') as f:
                            conv_data = json.load(f)
                        conv = AiConversation()
                        conv.conversation_id = conversation_id
                        conv.completions = conv_data.get("completions", [])
                        logging.info("Loaded conversation from file with {} completions".format(len(conv.completions)))
            except Exception as e:
                logging.warning("Failed to load existing conversation: {}".format(e))
                conv = None
    except Exception:
        pass
    
    # If no existing conversation found or loading failed, create a new one
    if not conv:
        conv = AiConversation()
        logging.info(
            "get_home (/) - new conversation_id: {}".format(conv.conversation_id)
        )
        # Store the new conversation_id in session
        try:
            req.session["conversation_id"] = conv.conversation_id
        except Exception:
            pass
    
    view_data = dict()
    view_data["conv"] = conv.get_data()
    view_data["conversation_id"] = conv.conversation_id
    view_data["conversation_data"] = ""
    view_data["prompts_text"] = "no prompts yet"
    view_data["last_user_question"] = ""
    view_data["rag_strategy"] = "auto"
    view_data["current_page"] = "conv_ai_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="conv_ai_console.html", context=view_data
    )


@app.get("/about")
async def get_about(req: Request):
    view_data = dict()
    view_data["application_version"] = ConfigService.application_version()
    view_data["application_build"] = ConfigService.application_build()
    view_data["graph_source"] = ConfigService.graph_source()
    view_data["graph_source_db"] = ConfigService.graph_source_db()
    view_data["graph_source_container"] = ConfigService.graph_source_container()
    view_data["current_page"] = "about"  # Set active page for navbar
    return views.TemplateResponse(request=req, name="about.html", context=view_data)


@app.get("/sparql_console")
async def get_sparql_console(req: Request):
    view_data = get_sparql_console_view_data()
    view_data["current_page"] = "sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="sparql_console.html", context=view_data
    )


@app.post("/sparql_console")
async def post_sparql_console(req: Request):
    form_data = await req.form()  # <class 'starlette.datastructures.FormData'>
    logging.info("/sparql_console form_data: {}".format(form_data))
    view_data = post_libraries_sparql_console(form_data)
    view_data["current_page"] = "sparql_console"  # Set active page for navbar
    
    if (LoggingLevelService.get_level() == logging.DEBUG):
        try:
            FS.write_json(view_data, "tmp/sparql_console_view_data.json")
        except Exception as e:
            pass
    return views.TemplateResponse(
        request=req, name="sparql_console.html", context=view_data
    )


@app.get("/gen_sparql_console")
async def get_ai_console(req: Request):
    view_data = gen_sparql_console_view_data()
    view_data["natural_language"] = ""
    view_data["sparql"] = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10"
    view_data["current_page"] = "gen_sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.post("/gen_sparql_console_generate_sparql")
async def ai_post_gen_sparql(req: Request):
    form_data = await req.form()
    logging.info("/gen_sparql_console_generate_sparql form_data: {}".format(form_data))
    natural_language = form_data.get("natural_language").strip()
    view_data = gen_sparql_console_view_data()
    view_data["natural_language"] = natural_language
    view_data["generating_nl"] = natural_language
    sparql: str = ""

    resp_obj = dict()
    resp_obj["session_id"] = (
        ""  # Note: not currently used, populate with the HTTP session ID
    )
    resp_obj["natural_language"] = natural_language
    resp_obj["owl"] = OntologyService.get_owl_content()
    resp_obj["completion_id"] = ""
    resp_obj["completion_model"] = ""
    resp_obj["prompt_tokens"] = -1
    resp_obj["completion_tokens"] = -1
    resp_obj["total_tokens"] = -1
    resp_obj["sparql"] = ""
    resp_obj["error"] = ""

    try:
        resp_obj = ai_svc.generate_sparql_from_user_prompt(resp_obj)
        sparql = resp_obj["sparql"]
        view_data["sparql"] = SparqlFormatter().pretty(sparql)
    except Exception as e:
        resp_obj["error"] = str(e)
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)

    view_data["results"] = resp_obj#json.dumps(resp_obj, sort_keys=False, indent=2)
    view_data["results_message"] = "Generative AI Response"
    view_data["current_page"] = "gen_sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.post("/gen_sparql_console_execute_sparql")
async def gen_sparql_console_execute_sparql(req: Request):
    form_data = await req.form()
    logging.info("/gen_sparql_console_execute_sparql form_data: {}".format(form_data))
    view_data = gen_sparql_console_view_data()
    sparql = form_data.get("sparql")
    view_data["sparql"] = sparql
    # Prefer the actual textarea value if present, else fallback to generating_nl
    nl_val = form_data.get("natural_language")
    if nl_val is not None and len(nl_val.strip()) > 0:
        view_data["natural_language"] = nl_val
    else:
        view_data["natural_language"] = form_data.get("generating_nl")

    sqr: SparqlQueryResponse = post_sparql_query_to_graph_microsvc(sparql)

    if sqr.has_errors():
        view_data["results"] = dict()
        view_data["results_message"] = "SPARQL Query Error"
    else:
        view_data["results"] = sqr.response_obj#json.dumps(sqr.response_obj, sort_keys=False, indent=2)
        view_data["count"] = sqr.count
        view_data["results_message"] = "SPARQL Query Results"
    view_data["current_page"] = "gen_sparql_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="gen_sparql_console.html", context=view_data
    )


@app.get("/vector_search_console")
async def get_vector_search_console(req: Request):
    view_data = vector_search_view_data()
    
    # Test session functionality
    req.session["test_session"] = "session_working"
    test_value = req.session.get("test_session")
    logging.info(f"Session test - stored: 'session_working', retrieved: '{test_value}'")
    
    # Debug: Log session contents
    logging.info(f"Session keys: {list(req.session.keys())}")
    logging.info(f"Full session contents: {dict(req.session)}")
    
    # Restore previous search data from session if available
    try:
        last_entrypoint = str(req.session.get("vector_search_entrypoint") or "").strip()
        if last_entrypoint:
            view_data["entrypoint"] = last_entrypoint
            logging.info(f"Restored entrypoint from session: {last_entrypoint}")
        else:
            logging.info("No entrypoint found in session")
            
        # Restore search method
        last_search_method = str(req.session.get("vector_search_method") or "vector").strip()
        view_data["search_method"] = last_search_method
        logging.info(f"Restored search method from session: {last_search_method}")
        
        # Restore search limit
        last_search_limit = req.session.get("vector_search_limit")
        if last_search_limit is not None:
            try:
                search_limit = int(last_search_limit)
                if 1 <= search_limit <= 100:  # Validate bounds
                    view_data["search_limit"] = search_limit
                    logging.info(f"Restored search limit from session: {search_limit}")
                else:
                    view_data["search_limit"] = 4  # Default if out of bounds
            except (ValueError, TypeError):
                view_data["search_limit"] = 4  # Default if invalid
        else:
            view_data["search_limit"] = 4  # Default if not found
            
        # Restore previous results if available
        last_results = req.session.get("vector_search_results")
        logging.info(f"Session results type: {type(last_results)}, value: {last_results}")
        
        if last_results is not None and len(last_results) > 0:
            view_data["results"] = last_results
            view_data["results_message"] = "Vector Search Results (from session)"
            logging.info(f"Restored {len(last_results)} results from session")
        else:
            logging.info("No results found in session or results are empty")
            
        # Restore previous embedding if available
        last_embedding = req.session.get("vector_search_embedding")
        last_embedding_message = req.session.get("vector_search_embedding_message")
        if last_embedding:
            view_data["embedding"] = last_embedding
            view_data["embedding_message"] = last_embedding_message or "Embedding (from session)"
            logging.info(f"Restored embedding from session")
        else:
            logging.info("No embedding found in session")
            
    except Exception as e:
        logging.error(f"Error restoring vector search session data: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    view_data["current_page"] = "vector_search_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


@app.post("/vector_search_console")
async def post_vector_search_console(req: Request):
    global nosql_svc
    form_data = await req.form()
    logging.info("/vector_search_console form_data: {}".format(form_data))
    
    # Safely get entrypoint and search method from form data
    entrypoint_raw = form_data.get("entrypoint")
    if entrypoint_raw is None:
        entrypoint = ""
    else:
        entrypoint = str(entrypoint_raw).strip()
    
    search_method_raw = form_data.get("search_method")
    if search_method_raw is None:
        search_method = "vector"  # Default to vector search
    else:
        search_method = str(search_method_raw).strip()
    
    # Safely get search limit from form data
    search_limit_raw = form_data.get("search_limit")
    if search_limit_raw is None or str(search_limit_raw).strip() == "":
        search_limit = 4  # Default limit
    else:
        try:
            search_limit = int(str(search_limit_raw).strip())
            # Ensure limit is within reasonable bounds
            if search_limit < 1:
                search_limit = 1
            elif search_limit > 100:
                search_limit = 100
        except ValueError:
            search_limit = 4  # Default if invalid
    
    logging.debug("vector_search_console; entrypoint: {}, search_method: {}, limit: {}".format(entrypoint, search_method, search_limit))
    view_data = vector_search_view_data()
    view_data["entrypoint"] = entrypoint
    view_data["search_method"] = search_method
    view_data["search_limit"] = search_limit

    if entrypoint and entrypoint.startswith("text:"):
        text = entrypoint[5:]
        logging.info(f"post_vector_search_console; text: {text}")
        
        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())
        
        if search_method == "fulltext":
            # Full-text search only
            results_obj = await nosql_svc.vector_search(search_text=text, search_method="fulltext", limit=search_limit)
            view_data["results_message"] = "Full-text Search Results"
        elif search_method == "rrf":
            # RRF search - need both vector and text
            try:
                logging.info("vectorize: {}".format(text))
                ai_svc_resp = ai_svc.generate_embeddings(text)
                vector = ai_svc_resp.data[0].embedding
                view_data["embedding_message"] = "Embedding from Text"
                view_data["embedding"] = json.dumps(vector, sort_keys=False, indent=2)
                logging.warning(f"post_vector_search_console; vector: {vector}")
                
                results_obj = await nosql_svc.vector_search(embedding_value=vector, search_text=text, search_method="rrf", limit=search_limit)
                view_data["results_message"] = "RRF (Hybrid) Search Results"
            except Exception as e:
                logging.critical((str(e)))
                logging.exception(e, stack_info=True, exc_info=True)
                results_obj = list()
        else:
            # Vector search (default)
            try:
                logging.info("vectorize: {}".format(text))
                ai_svc_resp = ai_svc.generate_embeddings(text)
                vector = ai_svc_resp.data[0].embedding
                view_data["embedding_message"] = "Embedding from Text"
                view_data["embedding"] = json.dumps(vector, sort_keys=False, indent=2)
                logging.warning(f"post_vector_search_console; vector: {vector}")
                
                results_obj = await nosql_svc.vector_search(embedding_value=vector, search_method="vector", limit=search_limit)
                view_data["results_message"] = "Vector Search Results"
            except Exception as e:
                logging.critical((str(e)))
                logging.exception(e, stack_info=True, exc_info=True)
                results_obj = list()
                
    elif entrypoint:
        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())
        docs = await nosql_svc.get_documents_by_name([entrypoint])
        logging.debug("vector_search_console - docs count: {}".format(len(docs)))

        if len(docs) > 0:
            doc = docs[0]
            if search_method == "fulltext":
                # For entity search with fulltext, use the entity name as search text
                results_obj = await nosql_svc.vector_search(search_text=entrypoint, search_method="fulltext", limit=search_limit)
                view_data["results_message"] = "Full-text Search Results"
            elif search_method == "rrf":
                # For RRF with entity, use both embedding and entity name
                results_obj = await nosql_svc.vector_search(embedding_value=doc["embedding"], search_text=entrypoint, search_method="rrf", limit=search_limit)
                view_data["results_message"] = "RRF (Hybrid) Search Results"
            else:
                # Vector search (default)
                results_obj = await nosql_svc.vector_search(embedding_value=doc["embedding"], search_method="vector", limit=search_limit)
                view_data["results_message"] = "Vector Search Results"
        else:
            results_obj = list()
    else:
        # Empty entrypoint - return empty results
        results_obj = list()

    # Set default results message if not already set
    if "results_message" not in view_data:
        view_data["results_message"] = "Search Results"
    
    view_data["results"] = results_obj
    view_data["current_page"] = "vector_search_console"  # Set active page for navbar
    
    # Store search data in session for persistence between navigations
    try:
        req.session["vector_search_entrypoint"] = entrypoint
        req.session["vector_search_method"] = search_method
        req.session["vector_search_limit"] = search_limit
        
        # Convert results to JSON serializable format
        if results_obj:
            # Convert to list if it's not already, and ensure it's JSON serializable
            serializable_results = list(results_obj) if results_obj else []
            req.session["vector_search_results"] = serializable_results
        else:
            req.session["vector_search_results"] = []
            
        logging.info(f"Stored entrypoint '{entrypoint}', method '{search_method}', limit '{search_limit}', and {len(results_obj) if results_obj else 0} results in session")
        
        if "embedding" in view_data and view_data["embedding"]:
            req.session["vector_search_embedding"] = view_data["embedding"]
            req.session["vector_search_embedding_message"] = view_data["embedding_message"]
            logging.info(f"Stored embedding data in session")
        else:
            # Clear embedding data if not present
            req.session.pop("vector_search_embedding", None)
            req.session.pop("vector_search_embedding_message", None)
            
    except Exception as e:
        logging.error(f"Error storing vector search session data: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    return views.TemplateResponse(
        request=req, name="vector_search_console.html", context=view_data
    )


def vector_search_view_data():
    view_data = dict()
    view_data["entrypoint"] = ""
    view_data["search_method"] = "vector"  # Default to vector search
    view_data["results_message"] = ""
    view_data["results"] = {}
    view_data["embedding_message"] = ""
    view_data["embedding"] = ""
    return view_data


@app.get("/conv_ai_console")
async def conv_ai_console(req: Request):
    global nosql_svc
    conv = None
    conversation_id = None
    
    # Check if there's an existing conversation in the session
    try:
        conversation_id = str(req.session.get("conversation_id") or "").strip()
        if conversation_id:
            logging.info("Found existing conversation_id in session: {}".format(conversation_id))
            # Try to load the existing conversation
            try:
                conv = await nosql_svc.load_conversation(conversation_id)
                if conv:
                    logging.info("Loaded existing conversation with {} completions".format(len(conv.completions)))
                else:
                    # Try file-based storage fallback
                    import os
                    import json
                    conv_file_path = f"tmp/conv_{conversation_id}.json"
                    if os.path.exists(conv_file_path):
                        with open(conv_file_path, 'r') as f:
                            conv_data = json.load(f)
                        conv = AiConversation()
                        conv.conversation_id = conversation_id
                        conv.completions = conv_data.get("completions", [])
                        logging.info("Loaded conversation from file with {} completions".format(len(conv.completions)))
            except Exception as e:
                logging.warning("Failed to load existing conversation: {}".format(e))
                conv = None
    except Exception:
        pass
    
    # If no existing conversation found or loading failed, create a new one
    if not conv:
        conv = AiConversation()
        logging.info(
            "conv_ai_console - new conversation_id: {}".format(conv.conversation_id)
        )
        # Store the new conversation_id in session
        try:
            req.session["conversation_id"] = conv.conversation_id
        except Exception:
            pass
    
    view_data = dict()
    view_data["conv"] = conv.get_data()
    view_data["conversation_id"] = conv.conversation_id
    view_data["conversation_data"] = ""
    view_data["prompts_text"] = "no prompts yet"
    view_data["last_user_question"] = ""
    view_data["rag_strategy"] = "auto"
    view_data["current_page"] = "conv_ai_console"  # Set active page for navbar
    return views.TemplateResponse(
        request=req, name="conv_ai_console.html", context=view_data
    )


@app.post("/conv_ai_console")
async def conv_ai_console_post(req: Request):
    global ai_svc
    global nosql_svc
    global ontology_svc
    global rag_data_svc

    form_data = await req.form()
    logging.info("/conv_ai_console form_data: {}".format(form_data))
    conversation_id = str(form_data.get("conversation_id") or "").strip()
    if not conversation_id:
        try:
            conversation_id = str(req.session.get("conversation_id") or "").strip()
            logging.info("conversation_id restored from session: {}".format(conversation_id))
        except Exception:
            pass
    user_text = str(form_data.get("user_text") or "").strip()
    rag_strategy_choice = str(form_data.get("rag_strategy") or '').strip().lower()
    print(f"[DEBUG] conversation_id: {conversation_id}, user_text: {user_text}")
    logging.info(
        "conversation_id: {}, user_text: {}".format(conversation_id, user_text)
    )
    
    # Try database first, fall back to file-based storage if database fails
    import os
    import json
    
    conv_file_path = f"tmp/conv_{conversation_id}.json"
    conv = None
    use_file_storage = False
    
    # Try to load from database first
    try:
        conv = await nosql_svc.load_conversation(conversation_id)
        if conv:
            print(f"[DEBUG] LOADED FROM DATABASE: {len(conv.completions)} completions")
        else:
            print(f"[DEBUG] NO DATABASE RECORD found for conversation_id: {conversation_id}")
    except Exception as e:
        print(f"[DEBUG] DATABASE LOAD FAILED: {e}")
        logging.warning(f"Database load failed, falling back to file storage: {e}")
        use_file_storage = True
    
    # If database failed or returned None, try file-based storage
    if conv is None:
        if os.path.exists(conv_file_path):
            try:
                with open(conv_file_path, 'r') as f:
                    conv_data = json.load(f)
                conv = AiConversation(conv_data)
                print(f"[DEBUG] LOADED FROM FILE (fallback): {len(conv.completions)} completions")
                use_file_storage = True
            except Exception as e:
                print(f"[DEBUG] FILE LOAD ALSO FAILED: {e}")
                conv = None
        else:
            print(f"[DEBUG] NO FILE found either for conversation_id: {conversation_id}")
            use_file_storage = True  # Use file storage for new conversations if DB failed

    # DEBUGGING: Log completions immediately after loading
    if conv:
        print(f"[DEBUG] LOADED CONVERSATION: {len(conv.completions)} completions")
        logging.info(f"LOADED CONVERSATION: {len(conv.completions)} completions")
        for i, c in enumerate(conv.completions):
            print(f"[DEBUG]   Loaded completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
            logging.info(f"  Loaded completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
    else:
        print(f"[DEBUG] LOADED CONVERSATION: None (new conversation)")
        logging.info("LOADED CONVERSATION: None (new conversation)")

    if conv is None:
        conv = AiConversation()
        # Only set the id if provided; otherwise keep the generated one
        if conversation_id is not None and len(conversation_id) > 0:
            conv.set_conversation_id(conversation_id)
        logging.info("new conversation created")
    else:
        logging.info(
            "conversation loaded: {} {}".format(conversation_id, conv.serialize())
        )

    if len(user_text) > 0:
        # Always record the user's message first so each turn shows in order
        conv.add_user_message(user_text)
        prompt_text = ai_svc.generic_prompt_template()

        override = None if rag_strategy_choice in ("", "auto") else rag_strategy_choice
        rdr: RAGDataResult = await rag_data_svc.get_rag_data(user_text, 20, override)
        if (LoggingLevelService.get_level() == logging.DEBUG):
            FS.write_json(rdr.get_data(), "tmp/ai_conv_rdr.json")

            # Save execution trace if available
            tracker = rdr.get_execution_tracker()
            if tracker:
                # Save ASCII visualization to file
                ascii_trace = tracker.visualize_ascii()
                logging.debug("\n" + ascii_trace)
                FS.write(f"tmp/execution_trace_{int(time.time())}.txt", ascii_trace)
                # Save structured trace data
                FS.write_json(tracker.to_dict(), f"tmp/execution_trace_{int(time.time())}.json")

        completion: Optional[AiCompletion] = AiCompletion(conv.conversation_id, None)
        completion.set_user_text(user_text)
        completion.set_rag_strategy(rdr.get_strategy())
        content_lines = list()

        # Prepare context based on RAG strategy
        context = ""
        completion_context = conv.last_completion_content()
        
        if rdr.has_db_rag_docs() == True:
            # Check result format to determine which fields to include
            result_format = rdr.get_result_format()
            logging.info(f"Result format: {result_format}")

            for doc in rdr.get_rag_docs():
                logging.debug("doc: {}".format(doc))

                if result_format == "list_summary":
                    # For list results, include summary fields based on document type
                    # Detect if this is a chunk document or contract document
                    is_chunk = "chunk_index" in doc or "chunk_text" in doc or "text" in doc

                    if is_chunk:
                        # Chunk documents contain both chunk fields AND contract metadata
                        summary_fields = [
                            "id", "filename", "contract_id", "chunk_index",
                            "chunk_text", "text", "similarity_score",
                            # Contract metadata fields also present in chunks
                            "contractor_party", "contracting_party",
                            "governing_law_state", "contract_type",
                            "effective_date", "expiration_date",
                            "contract_value", "maximum_contract_value",
                            "jurisdiction"
                        ]
                    else:
                        # Contract document fields
                        summary_fields = [
                            "id", "contractor_party", "contracting_party",
                            "governing_law_state", "contract_type",
                            "effective_date", "expiration_date",
                            "maximum_contract_value", "filename", "similarity_score"
                        ]

                    filtered_doc = {k: v for k, v in doc.items() if k in summary_fields}
                    content_lines.append(json.dumps(filtered_doc))
                elif result_format == "clause_analysis":
                    # For clause analysis, include clause-specific fields
                    clause_fields = ["id", "contract_id", "clause_type", "text"]
                    filtered_doc = {k: v for k, v in doc.items() if k in clause_fields}
                    content_lines.append(json.dumps(filtered_doc))
                else:
                    # For full_context, include ALL fields (excluding embedding)
                    doc_copy = dict(doc)
                    doc_copy.pop("embedding", None)
                    content_lines.append(json.dumps(doc_copy))
            
            # For DB RAG, set the context but don't set completion content yet
            conv.set_context(rdr.get_context())
            rag_data = "\n".join(content_lines)
            
            if conv.has_context():
                context = "Found context: {}\n{}\n{}".format(
                    conv.get_context(), completion_context, rag_data
                )
            else:
                context = "{}\n{}".format(completion_context, rag_data)
                
            try:
                logging.info("conv save (db path) completions: {}".format(len(conv.get_data().get("completions", []))))
            except Exception:
                pass
                
        elif rdr.has_graph_rag_docs() == True:
            for doc in rdr.get_rag_docs():
                content_lines.append(json.dumps(doc))
            
            # For Graph RAG, set the context but don't set completion content yet
            graph_content = ", ".join(content_lines)
            conv.set_context(graph_content)
            conv.add_diagnostic_message("sparql: {}".format(rdr.get_sparql()))

            if conv.has_context():
                context = "Found context: {}\n{}\n".format(
                    conv.get_context(), completion_context
                )
            else:
                context = "{}\n".format(completion_context)
        else:
            # No specific RAG docs, use system prompt
            rag_data = rdr.as_system_prompt_text()

            if conv.has_context():
                context = "Found context: {}\n{}\n{}".format(
                    conv.get_context(), completion_context, rag_data
                )
            else:
                context = "{}\n{}".format(completion_context, rag_data)

        # Always run AI inference to generate the actual response
        max_tokens = ConfigService.invoke_kernel_max_tokens()
        temperature = ConfigService.invoke_kernel_temperature()
        top_p = ConfigService.invoke_kernel_top_p()
        comp_result = await ai_svc.invoke_kernel(
            conv,
            prompt_text,
            user_text,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        if comp_result is not None:
            completion = comp_result
            completion.set_rag_strategy(rdr.get_strategy())
        else:
            completion.set_content("No results found")

        # Add completion exactly once at the end
        conv.add_completion(completion)
        
        print(f"[DEBUG] AFTER ADD_COMPLETION: {len(conv.completions)} completions")
        # DEBUGGING: Log completions immediately after adding
        logging.info(f"AFTER ADD_COMPLETION: {len(conv.completions)} completions")
        for i, c in enumerate(conv.completions):
            print(f"[DEBUG]   After add completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
            logging.info(f"  After add completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
        
        # Save conversation - try database first, fall back to file if database fails
        save_success = False
        
        # Try database save first (unless we're already using file storage)
        if not use_file_storage:
            try:
                await nosql_svc.save_conversation(conv)
                print(f"[DEBUG] SAVED TO DATABASE: {len(conv.completions)} completions")
                logging.info(f"SAVED TO DATABASE: {len(conv.completions)} completions")
                save_success = True
            except Exception as e:
                print(f"[DEBUG] DATABASE SAVE FAILED: {e}")
                logging.warning(f"Database save failed, falling back to file storage: {e}")
                use_file_storage = True
        
        # If database save failed or we're using file storage, save to file
        if not save_success or use_file_storage:
            try:
                with open(conv_file_path, 'w') as f:
                    json.dump(conv.get_data(), f, indent=2)
                print(f"[DEBUG] SAVED TO FILE: {len(conv.completions)} completions")
                logging.info(f"SAVED TO FILE: {len(conv.completions)} completions")
                save_success = True
            except Exception as e:
                print(f"[DEBUG] FILE SAVE ALSO FAILED: {e}")
                logging.error(f"Both database and file save failed: {e}")
        
        if not save_success:
            logging.error("CRITICAL: Conversation could not be saved to either database or file!")

        # DEBUGGING: Log completions immediately after save
        storage_type = "DATABASE" if not use_file_storage else "FILE"
        print(f"[DEBUG] AFTER SAVE_CONVERSATION ({storage_type}): {len(conv.completions)} completions")
        logging.info(f"AFTER SAVE_CONVERSATION ({storage_type}): {len(conv.completions)} completions")
        for i, c in enumerate(conv.completions):
            print(f"[DEBUG]   After save completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
            logging.info(f"  After save completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")

        logging.info(f"Completions after add_completion: {len(conv.completions)}")
        save_method = "database" if not use_file_storage else "file"
        logging.info(f"Conversation saved successfully using {save_method} storage.")

    #textformat_conversation(conv)
    # Disable optional reload to prevent issues with conversation state
    # The in-memory conversation should be the source of truth after save
    logging.info(f"Final conversation has {len(conv.get_data().get('completions', []))} completions")

    if (LoggingLevelService.get_level() == logging.DEBUG):
        FS.write_json(conv.get_data(), "tmp/ai_conv_{}.json".format(
            conv.get_message_count()))

    view_data = dict()
    # Backfill indices for stable ordering in the UI
    try:
        conv.ensure_indices()
    except Exception:
        pass
    view_data["conv"] = conv.get_data()
    view_data["conversation_id"] = conv.conversation_id
    
    # DEBUGGING: Log completions before rendering template
    completions_data = conv.get_data().get("completions", [])
    logging.info(f"BEFORE TEMPLATE RENDER: {len(completions_data)} completions")
    for i, c in enumerate(completions_data):
        logging.info(f"  Template completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
    
    try:
        req.session["conversation_id"] = conv.conversation_id
    except Exception:
        pass
    view_data["conversation_data"] = conv.serialize()
    view_data["prompts_text"] = conv.formatted_prompts_text()
    view_data["last_user_question"] = conv.get_last_user_message()
    view_data["rag_strategy"] = rag_strategy_choice or (rdr.get_strategy() if 'rdr' in locals() and rdr else "auto")
    view_data["current_page"] = "conv_ai_console"  # Set active page for navbar
    
    # Debugging: Log the state of completions before rendering the template
    logging.debug("Final completions before rendering: {}".format(conv.get_data().get("completions", [])))
    # Debugging: Log the final state of completions before rendering the template
    logging.debug("Final state of completions before rendering:")
    for c in conv.get_data().get("completions", []):
        logging.debug(f"Completion ID: {c.get('completion_id')}, Index: {c.get('index')}, Content: {c.get('content')}")

    return views.TemplateResponse(
        request=req, name="conv_ai_console.html", context=view_data
    )


@app.post("/conv_ai_feedback")
async def post_sparql_query(
    req_model: AiConvFeedbackModel,
) -> AiConvFeedbackModel:
    global nosql_svc
    conversation_id = req_model.conversation_id
    feedback_last_question = req_model.feedback_last_question
    feedback_user_feedback = req_model.feedback_user_feedback
    logging.info("/conv_ai_feedback conversation_id: {}".format(conversation_id))
    logging.info(
        "/conv_ai_feedback feedback_last_question: {}".format(feedback_last_question)
    )
    logging.info(
        "/conv_ai_feedback feedback_user_feedback: {}".format(feedback_user_feedback)
    )
    await nosql_svc.save_feedback(req_model)
    return req_model


@app.post("/query_contracts_direct")
async def post_query_contracts_direct(
    req_model: QueryContractsDirectRequestModel,
) -> QueryContractsDirectResponseModel:
    """
    Execute contract query with programmatic SQL generation (bypasses LLM entirely).
    Returns list of contracts matching the provided filters.

    Behavior:
    - No filters provided: Returns all contracts (up to limit)
    - Filters provided: Returns contracts matching ALL filter criteria
    - Builds SQL query programmatically for fast, cost-effective queries
    - No LLM invocation, no AI completion

    Filter parameters:
    - contractor_party: Filter by contractor party name
    - contracting_party: Filter by contracting party name
    - governing_law_state: Filter by governing law state
    - contract_type: Filter by contract type
    - limit: Maximum number of contracts to return (default: 20)
    - offset: Pagination offset (default: 0)
    """
    global rag_data_svc, nosql_svc

    try:
        start_time = time.time()
        query = req_model.query
        limit = req_model.limit if req_model.limit else 20
        strategy_override = req_model.strategy_override if req_model.strategy_override else None

        # Always use programmatic mode - bypass LLM entirely
        # Build filter dictionary from provided filters (empty dict = return all contracts)
        filter_dict = {}
        if req_model.contractor_party:
            filter_dict['contractor_party'] = req_model.contractor_party
        if req_model.contracting_party:
            filter_dict['contracting_party'] = req_model.contracting_party
        if req_model.governing_law_state:
            filter_dict['governing_law_state'] = req_model.governing_law_state
        if req_model.contract_type:
            filter_dict['contract_type'] = req_model.contract_type

        # Get offset for pagination
        offset = req_model.offset if req_model.offset else 0

        logging.info(f"POST /query_contracts_direct (programmatic) - filters: {filter_dict}, limit={limit}, offset={offset}")

        # Execute programmatic query with pagination support
        # Returns tuple of (documents, total_count)
        documents, total_count = await nosql_svc.query_contracts_with_filter(
            filter_dict,
            max_count=limit,
            offset=offset,
            return_total_count=True
        )

        # Filter to summary fields
        contract_summary_fields = [
            "id", "contractor_party", "contracting_party",
            "governing_law_state", "contract_type",
            "effective_date", "expiration_date",
            "contract_value", "maximum_contract_value", "filename"
        ]

        filtered_documents = []
        for doc in documents:
            filtered_doc = {k: v for k, v in doc.items() if k in contract_summary_fields}
            filtered_documents.append(filtered_doc)

        execution_time_ms = (time.time() - start_time) * 1000

        logging.info(f"Programmatic query successful - {len(filtered_documents)} documents returned, {total_count} total, {execution_time_ms:.0f}ms")

        return QueryContractsDirectResponseModel(
            query=query,
            result_format="list_summary",
            strategy="db_programmatic",
            documents=filtered_documents,
            document_count=total_count,  # Return total count for pagination
            ru_cost=0.0,  # No RU tracking for programmatic queries yet
            execution_time_ms=execution_time_ms,
            error=None,
            execution_trace=None
        )

        # OLD MODE 2: LLM strategy determination (no longer used)
        # logging.info(f"POST /query_contracts_direct (LLM) - query: {query}, limit: {limit}, strategy: {strategy_override}")

        # Execute RAG data retrieval (LLM determines strategy and executes query)
        rdr: RAGDataResult = await rag_data_svc.get_rag_data(query, limit, strategy_override)

        # Get result format from LLM plan
        result_format = rdr.get_result_format()
        strategy = rdr.get_strategy()

        logging.info(f"Query executed - result_format: {result_format}, strategy: {strategy}")

        # Check if result format is list_summary (only format that doesn't need AI analysis)
        if result_format != "list_summary":
            error_msg = f"Query requires AI analysis (result_format: {result_format}). This endpoint only supports list_summary queries. Use /conv_ai_console for analysis queries."
            logging.warning(error_msg)

            return QueryContractsDirectResponseModel(
                query=query,
                result_format=result_format,
                strategy=strategy,
                documents=[],
                document_count=0,
                ru_cost=0.0,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=error_msg,
                execution_trace=None
            )

        # Get raw documents
        documents = rdr.get_rag_docs()

        # Define fields for different document types
        # Contract documents (from contracts collection)
        contract_summary_fields = [
            "id", "contractor_party", "contracting_party",
            "governing_law_state", "contract_type",
            "effective_date", "expiration_date",
            "contract_value", "maximum_contract_value", "filename", "similarity_score"
        ]

        # Chunk documents (from contract_chunks collection)
        # Chunks contain both chunk-specific fields AND contract metadata
        chunk_summary_fields = [
            "id", "filename", "contract_id", "chunk_index",
            "chunk_text", "text", "similarity_score",
            # Contract metadata fields also present in chunks
            "contractor_party", "contracting_party",
            "governing_law_state", "contract_type",
            "effective_date", "expiration_date",
            "contract_value", "maximum_contract_value",
            "jurisdiction"
        ]

        filtered_documents = []
        for doc in documents:
            # Detect document type by checking for chunk-specific fields
            is_chunk = "chunk_index" in doc or "chunk_text" in doc or "text" in doc

            if is_chunk:
                # Filter chunk document
                filtered_doc = {k: v for k, v in doc.items() if k in chunk_summary_fields}
            else:
                # Filter contract document
                filtered_doc = {k: v for k, v in doc.items() if k in contract_summary_fields}

            filtered_documents.append(filtered_doc)

        # Get execution trace if available
        execution_trace = None
        tracker = rdr.get_execution_tracker()
        if tracker:
            execution_trace = tracker.to_dict()

        # Calculate RU cost from execution trace
        ru_cost = 0.0
        if execution_trace and "steps" in execution_trace:
            for step in execution_trace["steps"]:
                if "ru_cost" in step:
                    ru_cost += step["ru_cost"]

        execution_time_ms = (time.time() - start_time) * 1000

        logging.info(f"Query successful - {len(filtered_documents)} documents, {ru_cost:.1f} RUs, {execution_time_ms:.0f}ms")

        return QueryContractsDirectResponseModel(
            query=query,
            result_format=result_format,
            strategy=strategy,
            documents=filtered_documents,
            document_count=len(filtered_documents),
            ru_cost=ru_cost,
            execution_time_ms=execution_time_ms,
            error=None,
            execution_trace=execution_trace
        )

    except Exception as e:
        logging.error(f"Error in /query_contracts_direct: {str(e)}")
        logging.error(traceback.format_exc())

        return QueryContractsDirectResponseModel(
            query=req_model.query,
            result_format="unknown",
            strategy="unknown",
            documents=[],
            document_count=0,
            ru_cost=0.0,
            execution_time_ms=0.0,
            error=str(e),
            execution_trace=None
        )


@app.post("/clear_session")
async def clear_session(request: Request):
    """
    Clear server-side session; optionally delete a conversation document.
    Frontend may pass: { "conversation_id": "<id>", "ignore_missing": true }
    """
    global nosql_svc
    
    # Get current conversation_id from session before clearing
    conversation_id = None
    try:
        conversation_id = str(request.session.get("conversation_id") or "").strip()
    except Exception:
        pass
    
    # Attempt to parse JSON payload
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    conv_id = (payload.get("conversation_id") or "").strip() or None
    ignore_missing = bool(payload.get("ignore_missing"))

    # Example: remove server-side stored conversation id (if using session)
    try:
        request.session.pop("conversation_id", None)
    except Exception:
        pass

    delete_status = "skipped"
    if conv_id:
        try:
            # Assuming conversations_container already initialized
            conversations_container.delete_item(item=conv_id, partition_key=conv_id)
            delete_status = "deleted"
        except CosmosResourceNotFoundError:
            if ignore_missing:
                delete_status = "not_found_ignored"
            else:
                delete_status = "not_found"
        except Exception as e:
            # Log and continue to return success flag=false
            logging.warning("Unexpected error deleting conversation %s: %s", conv_id, e)
            return JSONResponse({"success": False, "delete_status": "error", "error": str(e)})

    # Optionally clear any other in-memory caches here
    return JSONResponse({"success": True, "delete_status": delete_status})


@app.post("/api/save_ontology")
async def save_ontology(request: Request):
    data = await request.json()
    content = data.get("content", "")
    path = os.environ.get("CAIG_GRAPH_SOURCE_OWL_FILENAME")
    if not path:
        return JSONResponse({"success": False, "error": "Ontology path not configured."})
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


def gen_sparql_console_view_data():
    view_data = dict()
    view_data["natural_language"] = "What is the total count of nodes?"
    view_data["sparql"] = ""
    view_data["owl"] = OntologyService.get_owl_content()
    view_data["results_message"] = ""
    view_data["results"] = ""
    view_data["generating_nl"] = ""
    view_data["count"] = ""
    return view_data


def graph_microsvc_sparql_query_url():
    return "{}:{}/sparql_query".format(
        ConfigService.graph_service_url(), ConfigService.graph_service_port()
    )


def graph_microsvc_bom_query_url():
    return "{}:{}/sparql_bom_query".format(
        ConfigService.graph_service_url(), ConfigService.graph_service_port()
    )


def get_sparql_console_view_data() -> dict:
    """Return the view data for the libraries SPARQL console"""
    sparql = """SELECT * WHERE { ?s ?p ?o . } LIMIT 10"""
    view_data = dict()
    view_data["method"] = "get"
    view_data["sparql"] = sparql
    view_data["bom_query"] = ""
    view_data["results_message"] = ""
    view_data["results"] = {}
    view_data["visualization_message"] = ""
    view_data["bom_json_str"] = "{}"
    view_data["inline_bom_json"] = "{}"
    view_data["libtype"] = ""
    return view_data


def filter_numeric_nodes(bom_obj):
    """
    Filter out nodes that are purely numeric values, GUIDs, or other technical identifiers.
    These are likely properties/attributes rather than actual meaningful graph entities.
    """
    if not isinstance(bom_obj, dict) or "nodes" not in bom_obj:
        return bom_obj
    
    def is_technical_identifier(name):
        """Check if a node name represents a technical value that should be filtered out"""
        if not isinstance(name, str):
            return False
        
        name = name.strip()
        
        # Skip empty names
        if not name:
            return True
            
        # Check if it's a pure decimal number (like "1600.0", "0.28575", "301.0")
        try:
            float(name)
            return True
        except ValueError:
            pass
        
        # Check if it's a GUID/UUID (like "11AF48DE79124AED8210C92F7EF8DF36")
        # These are technical identifiers, not meaningful entities for visualization
        if len(name) >= 32 and all(c in '0123456789ABCDEFabcdef' for c in name):
            return True
            
        # Check if it's mostly numeric with minimal text (measurement values)
        if len(name) <= 15:  # Short strings that might be measurements
            numeric_chars = sum(1 for c in name if c.isdigit() or c in '.-')
            if numeric_chars / len(name) > 0.6:  # More than 60% numeric characters
                return True
        
        # Check for URI fragments that start with schema references
        if name.startswith("http://") or name.startswith("https://"):
            return True
            
        return False
    
    def is_meaningful_entity(name, node_data):
        """Determine if a node represents a meaningful engineering entity"""
        if not isinstance(name, str):
            return False
            
        name = name.strip()
        
        # Keep well-formed equipment tags (like "1011-VES-301")
        if "-" in name and len(name) > 5:
            return True
            
        # Keep descriptive names with spaces
        if " " in name and len(name) > 10:
            return True
            
        # Keep file paths (engineering drawings, symbols)
        if "\\" in name or "/" in name:
            return True
            
        # Keep short meaningful codes (like "VES", "Equipment")
        if len(name) <= 15 and name.isalpha():
            return True
            
        # Reject technical identifiers
        if is_technical_identifier(name):
            return False
            
        return True
    
    def should_keep_node(name, node_data):
        """Determine if a node should be kept in the graph"""
        # First check if it's a meaningful entity
        if not is_meaningful_entity(name, node_data):
            return False
            
        # Additional check: nodes with no dependencies and short names are likely values
        if isinstance(node_data, dict):
            dependencies = node_data.get("dependencies", [])
            if not dependencies and len(name) < 5:
                return False
                
        return True
    
    # Create filtered copy of the BOM object
    filtered_bom_obj = {
        key: value for key, value in bom_obj.items() 
        if key != "nodes"
    }
    
    # Filter the nodes
    filtered_nodes = {}
    original_nodes = bom_obj.get("nodes", {})
    
    # First pass: determine which nodes to keep
    nodes_to_keep = set()
    for node_name, node_data in original_nodes.items():
        if should_keep_node(node_name, node_data):
            nodes_to_keep.add(node_name)
    
    # Second pass: create filtered nodes with cleaned dependencies
    for node_name, node_data in original_nodes.items():
        if node_name in nodes_to_keep:
            # Filter the dependencies to only include meaningful entities
            if isinstance(node_data, dict) and "dependencies" in node_data:
                filtered_dependencies = [
                    dep for dep in node_data["dependencies"] 
                    if is_meaningful_entity(dep, {}) and not is_technical_identifier(dep)
                ]
                
                # Create a copy of node_data with filtered dependencies
                filtered_node_data = node_data.copy()
                filtered_node_data["dependencies"] = filtered_dependencies
                filtered_nodes[node_name] = filtered_node_data
            else:
                filtered_nodes[node_name] = node_data
    
    filtered_bom_obj["nodes"] = filtered_nodes
    return filtered_bom_obj


def post_libraries_sparql_console(form_data):
    global websvc_headers

    sparql = form_data.get("sparql").strip()
    bom_query = form_data.get("bom_query").strip()
    logging.info("sparql: {}".format(sparql))
    logging.info("bom_query: {}".format(bom_query))

    view_data = dict()
    view_data["method"] = "post"
    view_data["sparql"] = sparql
    view_data["bom_query"] = bom_query
    view_data["results_message"] = "Results"
    view_data["results"] = {}
    view_data["visualization_message"] = ""
    view_data["bom_json_str"] = "{}"
    view_data["inline_bom_json"] = "{}"
    view_data["libtype"] = ""
    if sparql == "count":
        view_data["sparql"] = (
            "SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o } LIMIT 10"
        )
    elif sparql == "triples":
        view_data["sparql"] = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10"
    else:
        # execute either a BOM query or a simple SPARQL query, per Form input
        if len(bom_query) > 0:
            tokens = bom_query.split()
            if len(tokens) > 1:
                bom_obj = None
                url = graph_microsvc_bom_query_url()
                logging.info("url: {}".format(url))
                postdata = dict()
                postdata["entrypoint"] = tokens[0]
                postdata["max_depth"] = tokens[1]
                logging.info("postdata: {}".format(postdata))
                r = httpx.post(
                    url,
                    headers=websvc_headers,
                    content=json.dumps(postdata),
                    timeout=120.0,
                )
                bom_obj = json.loads(r.text)
                
                # Filter out numeric nodes that are likely measurement values
                filtered_bom_obj = filter_numeric_nodes(bom_obj)
                
                view_data["results"] = filtered_bom_obj
                view_data["inline_bom_json"] = view_data["results"]
                view_data["visualization_message"] = "Graph Visualization"
                # Derive a count for the header if possible
                try:
                    count_val = 0
                    if isinstance(filtered_bom_obj, dict):
                        # Prefer 'nodes' map count (new format)
                        if "nodes" in filtered_bom_obj and isinstance(filtered_bom_obj["nodes"], dict):
                            count_val = len(filtered_bom_obj["nodes"].keys())
                        # Legacy 'libs' map count
                        elif "libs" in filtered_bom_obj and isinstance(filtered_bom_obj["libs"], dict):
                            count_val = len(filtered_bom_obj["libs"].keys())
                        # Fallbacks: actual_depth/max_depth don't reflect rows, skip
                    view_data["count"] = count_val
                except Exception:
                    # Don't break UI if counting fails
                    view_data["count"] = 0
                if (LoggingLevelService.get_level() == logging.DEBUG):
                    try:
                        FS.write_json(
                            view_data["inline_bom_json"], "tmp/inline_bom.json"
                        )
                    except Exception as e:
                        pass
            else:
                view_data["results"] = "Invalid BOM query: {}".format(bom_query)
        else:
            sqr: SparqlQueryResponse = post_sparql_query_to_graph_microsvc(sparql)
            if sqr.has_errors():
                view_data["results"] = dict()
                view_data["results_message"] = "SPARQL Query Error"
            else:
                view_data["results"] = sqr.response_obj# json.dumps(
                #     sqr.response_obj, sort_keys=False, indent=2
                # )
                view_data["count"] = sqr.count
                view_data["results_message"] = "SPARQL Query Results"
    return view_data


def post_sparql_query_to_graph_microsvc(sparql: str) -> SparqlQueryResponse:
    """
    Execute a HTTP POST to the graph microservice with the given SPARQL query.
    Return the HTTP response JSON object.
    """
    global websvc_headers
    try:
        url = graph_microsvc_sparql_query_url()
        postdata = dict()
        postdata["sparql"] = sparql
        r = httpx.post(
            url, headers=websvc_headers, content=json.dumps(postdata), timeout=120.0
        )
        resp_obj = json.loads(r.text)
        print(
            "POST SPARQL RESPONSE:\n" + json.dumps(resp_obj, sort_keys=False, indent=2)
        )
        sqr = SparqlQueryResponse(r)
        sqr.parse()
        return sqr
    except Exception as e:
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)
        sqr = SparqlQueryResponse(None)
        sqr.parse()
        return sqr


def textformat_conversation(conv: AiConversation) -> None:
    """
    do an in-place reformatting of the conversation text, such as completion content
    """
    try:
        for comp in conv.completions:
            if "content" in comp.keys():
                content = comp["content"]
                if content is not None and len(content) > 0:
                    stripped = content.strip()
                    if stripped.startswith("{") and stripped.endswith("}"):
                        obj = json.loads(stripped)
                        comp["content"] = json.dumps(
                            obj, sort_keys=False, indent=2
                        ).replace("\n", "")
                    elif stripped.startswith("[") and stripped.endswith("]"):
                        obj = json.loads(stripped)
                        comp["content"] = json.dumps(
                            obj, sort_keys=False, indent=2
                        ).replace("\n", "")
                    else:
                        content_lines = list()
                        wrapped_lines = textwrap.wrap(stripped, width=80)
                        for line in wrapped_lines:
                            content_lines.append(line)
                        comp["content"] = "\n".join(content_lines)
    except Exception as e:
        logging.critical((str(e)))
        logging.exception(e, stack_info=True, exc_info=True)

# ============================================================================
# Contract Query Builder API Endpoints
# ============================================================================

# IMPORTANT: The /api/entities/search route must be defined BEFORE /api/entities/{entity_type}
# Otherwise FastAPI will match "search" as an entity_type parameter

@app.get("/api/entities/search")
async def search_entities(
    q: str,
    entity_type: Optional[str] = None,
    limit: int = 20
):
    """
    Search entities with fuzzy matching.
    Query params:
    - q: search query
    - entity_type: optional filter by type
    - limit: max results (default 20)
    """
    try:
        # If no query, return all entities grouped by type
        if not q or len(q.strip()) == 0:
            # Return all entities when no search query
            all_results = []
            entity_catalogs = []
            
            if not entity_type or entity_type == "contractor_parties":
                entity_catalogs.append(("contractor_parties", ContractEntitiesService.get_contractor_parties_catalog()))
            if not entity_type or entity_type == "contracting_parties":
                entity_catalogs.append(("contracting_parties", ContractEntitiesService.get_contracting_parties_catalog()))
            if not entity_type or entity_type == "governing_laws":
                entity_catalogs.append(("governing_laws", ContractEntitiesService.get_governing_laws_catalog()))
            if not entity_type or entity_type == "contract_types":
                entity_catalogs.append(("contract_types", ContractEntitiesService.get_contract_types_catalog()))
            
            grouped_results = {}
            for catalog_type, catalog in entity_catalogs:
                # Get top entities by contract count
                entities_list = []
                for normalized_name, entity_data in catalog.items():
                    entities_list.append({
                        "normalizedName": normalized_name,
                        "displayName": entity_data.get("display_name", normalized_name),
                        "contractCount": entity_data.get("contract_count", 0),
                        "totalValue": entity_data.get("total_value", 0),
                        "type": catalog_type,
                        "score": 1.0
                    })
                
                # Sort by contract count and take top N
                entities_list.sort(key=lambda x: x["contractCount"], reverse=True)
                entities_list = entities_list[:limit]
                
                if entities_list:
                    grouped_results[catalog_type] = {
                        "type": catalog_type,
                        "displayName": get_entity_type_display_name(catalog_type),
                        "entities": entities_list
                    }
            
            return JSONResponse(content={
                "results": list(grouped_results.values()),
                "query": q,
                "total": sum(len(g["entities"]) for g in grouped_results.values())
            })
        
        # Normalize the search query
        search_query = q.strip().lower()
        results = []
        
        # Define entity catalogs to search
        entity_catalogs = []
        if not entity_type or entity_type == "contractor_parties":
            entity_catalogs.append(("contractor_parties", ContractEntitiesService.get_contractor_parties_catalog()))
        if not entity_type or entity_type == "contracting_parties":
            entity_catalogs.append(("contracting_parties", ContractEntitiesService.get_contracting_parties_catalog()))
        if not entity_type or entity_type == "governing_laws":
            entity_catalogs.append(("governing_laws", ContractEntitiesService.get_governing_laws_catalog()))
        if not entity_type or entity_type == "contract_types":
            entity_catalogs.append(("contract_types", ContractEntitiesService.get_contract_types_catalog()))
        
        # Search through each catalog
        for catalog_type, catalog in entity_catalogs:
            for normalized_name, entity_data in catalog.items():
                display_name = entity_data.get("display_name", normalized_name)
                
                # Calculate match score (simple substring matching for now)
                score = 0
                if search_query in normalized_name:
                    score = 0.9
                elif search_query in display_name.lower():
                    score = 0.85
                elif any(word in normalized_name for word in search_query.split()):
                    score = 0.7
                elif any(word in display_name.lower() for word in search_query.split()):
                    score = 0.65
                
                # Add to results if score is above threshold
                if score >= 0.65:
                    results.append({
                        "normalizedName": normalized_name,
                        "displayName": display_name,
                        "contractCount": entity_data.get("contract_count", 0),
                        "totalValue": entity_data.get("total_value", 0),
                        "type": catalog_type,
                        "score": score
                    })
        
        # Sort by score and contract count
        results.sort(key=lambda x: (x["score"], x["contractCount"]), reverse=True)
        
        # Apply limit
        results = results[:limit]
        
        # Group results by type for frontend
        grouped_results = {}
        for result in results:
            entity_type = result["type"]
            if entity_type not in grouped_results:
                grouped_results[entity_type] = {
                    "type": entity_type,
                    "displayName": get_entity_type_display_name(entity_type),
                    "entities": []
                }
            grouped_results[entity_type]["entities"].append(result)
        
        return JSONResponse(content={
            "results": list(grouped_results.values()),
            "query": q,
            "total": len(results)
        })
        
    except Exception as e:
        logging.error(f"Error searching entities: {str(e)}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to search entities: {str(e)}"}
        )


@app.get("/api/entities/{entity_type}")
async def get_entities(entity_type: str):
    """
    Get all entities of a specific type with their statistics.
    Entity types: contractor_parties, contracting_parties, governing_laws, contract_types, clause_types
    """
    try:
        # Map entity type to catalog method
        entity_methods = {
            "contractor_parties": ContractEntitiesService.get_contractor_parties_catalog,
            "contracting_parties": ContractEntitiesService.get_contracting_parties_catalog,
            "governing_laws": ContractEntitiesService.get_governing_law_states_catalog,
            "contract_types": ContractEntitiesService.get_contract_types_catalog,
            "clause_types": ContractEntitiesService.get_clause_types_catalog
        }
        
        if entity_type not in entity_methods:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid entity type: {entity_type}"}
            )
        
        # Get entities from the cache
        entities = entity_methods[entity_type]()
        
        # Format response with normalized and display names
        result = []
        for normalized_name, entity_data in entities.items():
            # Handle clause_types differently as they have different fields
            if entity_type == "clause_types":
                result.append({
                    "normalizedName": normalized_name,
                    "displayName": entity_data.get("displayName", entity_data.get("display_name", normalized_name)),
                    "type": entity_data.get("type", normalized_name),
                    "icon": entity_data.get("icon", "description"),
                    "description": entity_data.get("description", ""),
                    "category": entity_data.get("category", ""),
                    "entityType": entity_type
                })
            else:
                result.append({
                    "normalizedName": normalized_name,
                    "displayName": entity_data.get("display_name", normalized_name),
                    "contractCount": entity_data.get("contract_count", 0),
                    "totalValue": entity_data.get("total_value", 0),
                    "type": entity_type
                })
        
        # Sort by contract count descending (or by displayName for clause_types)
        if entity_type == "clause_types":
            result.sort(key=lambda x: x["displayName"])
        else:
            result.sort(key=lambda x: x["contractCount"], reverse=True)
        
        return JSONResponse(content={
            "entities": result,
            "total": len(result),
            "type": entity_type
        })
        
    except Exception as e:
        logging.error(f"Error getting entities: {str(e)}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get entities: {str(e)}"}
        )






@app.get("/api/query-templates")
async def get_query_templates():
    """
    Get available query templates with their configurations.
    """
    templates = [
        {
            "id": "COMPARE_CLAUSES",
            "name": "Compare Clauses",
            "description": "Compare specific clauses across multiple contractors",
            "operation": "compare",
            "target": "clauses",
            "icon": "compare_arrows",
            "requiredFields": ["clauseTypes", "contractorParties"],
            "optionalFields": ["contractingParty"],
            "supportedClauseTypes": [
                {"type": "payment_terms", "displayName": "Payment Terms", "icon": "payment"},
                {"type": "termination", "displayName": "Termination", "icon": "cancel"},
                {"type": "liability", "displayName": "Liability", "icon": "warning"},
                {"type": "ip_ownership", "displayName": "IP Ownership", "icon": "copyright"},
                {"type": "confidentiality", "displayName": "Confidentiality", "icon": "lock"},
                {"type": "warranty", "displayName": "Warranty", "icon": "verified_user"},
                {"type": "indemnification", "displayName": "Indemnification", "icon": "shield"},
                {"type": "force_majeure", "displayName": "Force Majeure", "icon": "report_problem"},
                {"type": "dispute_resolution", "displayName": "Dispute Resolution", "icon": "gavel"},
                {"type": "governing_law", "displayName": "Governing Law", "icon": "account_balance"}
            ]
        },
        {
            "id": "FIND_CONTRACTS",
            "name": "Find Contracts",
            "description": "Search for contracts based on entities",
            "operation": "search",
            "target": "contracts",
            "icon": "search",
            "requiredFields": [],
            "optionalFields": ["contractingParty", "contractorParty", "governingLaw", "contractType"]
        },
        {
            "id": "ANALYZE_CONTRACT",
            "name": "Analyze Contract",
            "description": "Deep analysis of a single contract",
            "operation": "analyze",
            "target": "contract",
            "icon": "analytics",
            "requiredFields": ["contractId"],
            "optionalFields": ["analysisType"]
        },
        {
            "id": "COMPARE_CONTRACTS",
            "name": "Compare Contracts",
            "description": "Compare multiple contracts comprehensively",
            "operation": "compare",
            "target": "contracts",
            "icon": "difference",
            "requiredFields": ["contractIds"],
            "optionalFields": []
        }
    ]
    
    return JSONResponse(content={"templates": templates})


def get_entity_type_display_name(entity_type: str) -> str:
    """Helper function to get display names for entity types"""
    display_names = {
        "contractor_parties": "Contractor Parties",
        "contracting_parties": "Contracting Parties",
        "governing_laws": "Governing Laws",
        "contract_types": "Contract Types"
    }
    return display_names.get(entity_type, entity_type)


# Contract Workbench Routes
@app.get("/contract_workbench")
async def get_contract_workbench(req: Request):
    """Render the Contract Intelligence Workbench page"""
    view_data = {
        "current_page": "contract_workbench"
    }
    return views.TemplateResponse(
        request=req, name="contract_workbench.html", context=view_data
    )


@app.get("/api/contracts")
async def get_contracts(
    contract_type: Optional[str] = None,
    contractor_party: Optional[str] = None,
    contracting_party: Optional[str] = None,
    contracting_parties: Optional[str] = None,  # Comma-separated list
    governing_law: Optional[str] = None,
    governing_laws: Optional[str] = None,  # Comma-separated list
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    Get contracts with optional filtering.
    Returns contract summaries for the workbench.
    """
    try:
        # Query CosmosDB for contracts
        query = "SELECT * FROM c WHERE c.doctype = 'contract_parent'"
        params = []
        
        # Add filters if provided
        if contract_type and contract_type != "Any":
            query += " AND c.contract_type = @contract_type"
            params.append({"name": "@contract_type", "value": contract_type})
            logging.info(f"Filtering by contract_type: {contract_type}")
        
        if contractor_party:
            query += " AND c.contractor_party = @contractor_party"
            params.append({"name": "@contractor_party", "value": contractor_party})
            
        # Handle single contracting_party or multiple contracting_parties
        if contracting_parties:
            # Split comma-separated values
            parties_list = [p.strip() for p in contracting_parties.split(',')]
            if len(parties_list) == 1:
                query += " AND c.contracting_party = @contracting_party"
                params.append({"name": "@contracting_party", "value": parties_list[0]})
            else:
                # Use IN clause for multiple values
                in_clause_params = []
                for i, party in enumerate(parties_list):
                    param_name = f"@contracting_party_{i}"
                    in_clause_params.append(param_name)
                    params.append({"name": param_name, "value": party})
                query += f" AND c.contracting_party IN ({','.join(in_clause_params)})"
        elif contracting_party:
            # Backward compatibility - single value
            query += " AND c.contracting_party = @contracting_party"
            params.append({"name": "@contracting_party", "value": contracting_party})
            
        # Handle single governing_law or multiple governing_laws
        if governing_laws:
            # Split comma-separated values
            laws_list = [l.strip() for l in governing_laws.split(',')]
            if len(laws_list) == 1:
                query += " AND c.governing_law_state = @governing_law"
                params.append({"name": "@governing_law", "value": laws_list[0]})
            else:
                # Use IN clause for multiple values
                in_clause_params = []
                for i, law in enumerate(laws_list):
                    param_name = f"@governing_law_{i}"
                    in_clause_params.append(param_name)
                    params.append({"name": param_name, "value": law})
                query += f" AND c.governing_law_state IN ({','.join(in_clause_params)})"
        elif governing_law:
            # Backward compatibility - single value
            query += " AND c.governing_law_state = @governing_law"
            params.append({"name": "@governing_law", "value": governing_law})
            
        if date_from:
            query += " AND c.effective_date >= @date_from"
            params.append({"name": "@date_from", "value": date_from})
            
        if date_to:
            query += " AND c.effective_date <= @date_to"
            params.append({"name": "@date_to", "value": date_to})
        
        # Execute query
        nosql_svc.set_db("caig")
        nosql_svc.set_container("contracts")
        
        logging.info(f"Executing query: {query}")
        logging.info(f"With parameters: {params}")
        
        # Use parameterized_query to properly handle SQL parameters
        items = await nosql_svc.parameterized_query(
            sql_template=query,
            sql_parameters=params if params else [],
            cross_partition=True
        )
        
        logging.info(f"Query returned {len(items)} items")
        
        # Log the first item to check structure
        if items and len(items) > 0:
            logging.info(f"First item keys: {list(items[0].keys())}")
            logging.info(f"First item has clause_ids: {'clause_ids' in items[0]}")
            if 'clause_ids' in items[0]:
                logging.info(f"Number of clause_ids in first item: {len(items[0]['clause_ids'])}")
        
        # Transform contracts for UI
        contracts = []
        for item in items:
            # Use the id field directly - it already has the "contract_" prefix
            contract_id = item.get("id", "")
            
            contract = {
                "id": contract_id,  # Use the full ID with "contract_" prefix
                "title": item.get("filename", "Unknown"),
                "contractor_party": item.get("contractor_party", "Unknown"),
                "contracting_party": item.get("contracting_party", "Unknown"),
                "effective_date": item.get("effective_date", ""),
                "expiration_date": item.get("expiration_date", ""),
                "governing_law_state": item.get("governing_law_state", "Unknown"),
                "contract_type": item.get("contract_type", "Unknown"),
                "contract_value": item.get("contract_value", ""),
                "clauses": {}
            }
            
            # Extract clause IDs to know what clauses are available
            # The actual clause text is stored separately, but we can indicate
            # which clauses are present in this contract
            clause_ids = item.get("clause_ids", [])
            
            # Parse clause types from the clause IDs
            # Format: contract_{contract_id}_clause_{clause_type}
            for clause_id in clause_ids:
                if "_clause_" in clause_id:
                    # Get everything after the last "_clause_"
                    clause_type = clause_id.split("_clause_")[-1]
                    
                    # Create a more readable version of the clause type
                    # Convert from lowercase like "indemnification" or "workerscompensationinsurance"
                    # to readable format like "Indemnification" or "Workers Compensation Insurance"
                    
                    # Map of known clause types to their display names
                    clause_type_map = {
                        "indemnification": "Indemnification",
                        "indemnificationobligations": "Indemnification Obligations",
                        "workerscompensationinsurance": "Workers Compensation Insurance",
                        "commercialpublicliability": "Commercial Public Liability",
                        "automobileinsurance": "Automobile Insurance",
                        "umbrellainsurance": "Umbrella Insurance",
                        "assignability": "Assignability",
                        "databreachobligations": "Data Breach Obligations",
                        "complianceobligations": "Compliance Obligations",
                        "confidentialityobligations": "Confidentiality Obligations",
                        "escalationobligations": "Escalation Obligations",
                        "limitationofliabilityobligations": "Limitation of Liability Obligations",
                        "paymentobligations": "Payment Obligations",
                        "renewalnotification": "Renewal Notification",
                        "servicelevelagreement": "Service Level Agreement",
                        "terminationobligations": "Termination Obligations",
                        "warrantyobligations": "Warranty Obligations",
                        "governinglaw": "Governing Law"
                    }
                    
                    # Use the mapped name if available, otherwise create a readable version
                    readable_clause_type = clause_type_map.get(
                        clause_type.lower(),
                        clause_type.replace("_", " ").title()
                    )
                    
                    # Just indicate the clause exists - actual text will be fetched separately
                    contract["clauses"][readable_clause_type] = "present"
            
            # Include the contract markdown and token count if needed
            if item.get("contract_text"):
                contract["has_full_text"] = True
                contract["text_tokens"] = item.get("contract_text_tokens", 0)
            
            contracts.append(contract)
        
        return JSONResponse(content={"contracts": contracts})

    except Exception as e:
        logging.error(f"Error getting contracts: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/contracts/{contract_id}")
async def get_contract_by_id(contract_id: str):
    """
    Get a single contract by ID.
    Returns contract details including metadata.

    Args:
        contract_id: Contract document ID (e.g., "contract_abc123")

    Returns:
        Contract document with all fields
    """
    global nosql_svc

    try:
        # Set to contracts container
        nosql_svc.set_container("contracts")

        # Query for the specific contract
        query = f"SELECT * FROM c WHERE c.id = '{contract_id}'"

        contract = None
        items = nosql_svc._ctrproxy.query_items(query=query, parameters=[])
        async for item in items:
            contract = item
            break

        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")

        # Remove embedding field to reduce response size
        if "embedding" in contract:
            del contract["embedding"]

        return contract

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting contract {contract_id}: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contracts/{contract_id}/clauses")
async def get_contract_clauses(contract_id: str):
    """
    Get available clause types for a specific contract.
    Returns list of clause types that can be used for clause-by-clause comparison.

    Response format:
    [
        {
            "type": "indemnification",
            "display_name": "Indemnification",
            "description": "Indemnification clause details"
        },
        ...
    ]
    """
    try:
        logging.info(f"Getting clauses for contract: {contract_id}")

        # Initialize CosmosDB service
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        nosql_svc.set_db("caig")
        nosql_svc.set_container("contracts")

        # Query for the specific contract
        query = "SELECT c.clause_ids FROM c WHERE c.id = @contract_id AND c.doctype = 'contract_parent'"
        params = [{"name": "@contract_id", "value": contract_id}]

        items = await nosql_svc.parameterized_query(
            sql_template=query,
            sql_parameters=params,
            cross_partition=True
        )

        if not items or len(items) == 0:
            logging.warning(f"Contract not found: {contract_id}")
            return JSONResponse(
                content={"error": f"Contract not found: {contract_id}"},
                status_code=404
            )

        contract = items[0]
        clause_ids = contract.get("clause_ids", [])

        logging.info(f"Found {len(clause_ids)} clause_ids in contract")

        # Extract unique clause types from clause_ids
        # Format: contract_{contract_id}_clause_{clause_type}
        clause_types_set = set()
        for clause_id in clause_ids:
            if "_clause_" in clause_id:
                # Get everything after the last "_clause_"
                clause_type = clause_id.split("_clause_")[-1]
                clause_types_set.add(clause_type)

        # Map of known clause types to their display names
        clause_type_map = {
            "indemnification": "Indemnification",
            "indemnificationobligations": "Indemnification Obligations",
            "workerscompensationinsurance": "Workers Compensation Insurance",
            "commercialpublicliability": "Commercial Public Liability",
            "automobileinsurance": "Automobile Insurance",
            "umbrellainsurance": "Umbrella Insurance",
            "assignability": "Assignability",
            "databreachobligations": "Data Breach Obligations",
            "complianceobligations": "Compliance Obligations",
            "confidentialityobligations": "Confidentiality Obligations",
            "escalationobligations": "Escalation Obligations",
            "limitationofliabilityobligations": "Limitation of Liability Obligations",
            "paymentobligations": "Payment Obligations",
            "renewalnotification": "Renewal Notification",
            "servicelevelagreement": "Service Level Agreement",
            "terminationobligations": "Termination Obligations",
            "warrantyobligations": "Warranty Obligations",
            "governinglaw": "Governing Law"
        }

        # Build response
        clauses = []
        for clause_type in sorted(clause_types_set):
            # Use the mapped name if available, otherwise create a readable version
            display_name = clause_type_map.get(
                clause_type.lower(),
                clause_type.replace("_", " ").title()
            )

            clauses.append({
                "type": clause_type,
                "display_name": display_name,
                "description": f"{display_name} clause from the contract"
            })

        logging.info(f"Returning {len(clauses)} unique clause types")

        # Close DB connection
        await nosql_svc.close()

        return JSONResponse(content=clauses)

    except Exception as e:
        logging.error(f"Error getting contract clauses: {str(e)}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/contracts/{contract_id}/pdf-url")
async def get_contract_pdf_url(contract_id: str):
    """
    Generate a time-limited SAS URL for downloading a contract PDF.

    This endpoint provides secure access to contract PDFs stored in Azure Blob Storage
    by generating time-limited Shared Access Signature (SAS) URLs.

    Args:
        contract_id: Contract ID (e.g., "contract_123")

    Returns:
        JSON response with:
        - contract_id: The requested contract ID
        - pdf_url: Secure time-limited URL to access the PDF
        - expires_in_hours: Number of hours until the URL expires
        - pdf_filename: Name of the PDF file in blob storage

    Status Codes:
        200: Success - SAS URL generated
        404: Contract not found or PDF not available
        500: Server error during URL generation
        503: Blob storage service not configured
    """
    # Check if blob storage service is initialized
    if not blob_storage_service:
        logging.error("Blob storage service not available")
        return JSONResponse(
            status_code=503,
            content={
                "error": "PDF access not configured",
                "message": "Blob storage service is not initialized. Please contact administrator."
            }
        )

    try:
        # Set the container for contract queries
        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())

        # Query to find the contract and get its PDF filename
        query = "SELECT c.id, c.filename, c.pdf_filename FROM c WHERE c.id = @contract_id AND c.doctype = 'contract_parent'"
        parameters = [{"name": "@contract_id", "value": contract_id}]

        results = await nosql_svc.parameterized_query(
            sql_template=query,
            sql_parameters=parameters,
            cross_partition=True
        )

        if not results or len(results) == 0:
            logging.warning(f"Contract not found: {contract_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Contract not found",
                    "message": f"No contract found with ID: {contract_id}"
                }
            )

        contract = results[0]

        # Get PDF filename - try pdf_filename first, fall back to filename
        pdf_filename = contract.get('pdf_filename') or contract.get('filename')

        if not pdf_filename:
            logging.error(f"PDF filename not found for contract: {contract_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "PDF not available",
                    "message": f"No PDF filename found for contract: {contract_id}"
                }
            )

        # Ensure filename has .pdf extension
        if not pdf_filename.lower().endswith('.pdf'):
            pdf_filename = f"{pdf_filename}.pdf"

        # Check if file exists in blob storage
        if not blob_storage_service.file_exists(pdf_filename):
            logging.warning(f"PDF file not found in blob storage: {pdf_filename}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "PDF file not found",
                    "message": f"PDF file not found in storage: {pdf_filename}"
                }
            )

        # Generate SAS URL with configured expiry time
        expiry_hours = ConfigService.blob_sas_expiry_hours()
        sas_url = blob_storage_service.generate_sas_url(
            filename=pdf_filename,
            expiry_hours=expiry_hours
        )

        logging.info(f"Generated SAS URL for contract {contract_id} (PDF: {pdf_filename})")

        return {
            "contract_id": contract_id,
            "pdf_url": sas_url,
            "expires_in_hours": expiry_hours,
            "pdf_filename": pdf_filename
        }

    except Exception as e:
        logging.error(f"Error generating PDF URL for contract {contract_id}: {e}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to generate PDF URL",
                "message": str(e)
            }
        )


@app.post("/api/contracts/check-duplicate")
async def check_duplicate_contract(filename: str = Form(...)):
    """
    Check if a contract filename already exists in blob storage.

    Args:
        filename: Contract filename to check

    Returns:
        JSON response with:
        - exists: Boolean indicating if file exists
        - filename: Original filename provided
        - suggested_filename: Unique filename if duplicate exists
    """
    if not blob_storage_service:
        raise HTTPException(status_code=503, detail="Blob storage not configured")

    try:
        exists = blob_storage_service.check_duplicate(filename)
        suggested_filename = blob_storage_service.get_unique_filename(filename) if exists else filename

        logging.info(f"Duplicate check for {filename}: exists={exists}, suggested={suggested_filename}")

        return {
            "exists": exists,
            "filename": filename,
            "suggested_filename": suggested_filename
        }
    except Exception as e:
        logging.error(f"Error checking duplicate for {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/contracts/upload")
async def upload_contract(
    file: UploadFile = File(...),
    uploaded_by: str = Form(default=None)
):
    """
    Upload a contract PDF file for processing.

    Flow:
    1. Validate file (PDF, size)
    2. Upload to blob storage
    3. Create processing job
    4. Return job ID for tracking

    Args:
        file: PDF file to upload
        uploaded_by: User ID (optional, defaults to system_admin)

    Returns:
        JSON response with:
        - success: Boolean indicating success
        - job_id: Job ID for tracking processing status
        - filename: Filename of uploaded file
        - message: Success message
    """
    # Import job models locally
    from src.models.job_models import JobType, ContractUploadJobRequest
    from src.services.job_service import JobService

    if not blob_storage_service:
        raise HTTPException(status_code=503, detail="Blob storage not configured")
    if not content_understanding_service:
        raise HTTPException(status_code=503, detail="Content Understanding not configured")

    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read file bytes
        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        # Validate file size
        max_size_mb = ConfigService.contract_upload_max_size_mb()
        if file_size_mb > max_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum ({max_size_mb}MB)"
            )

        # Use default user if not provided
        uploader = uploaded_by or ConfigService.contract_upload_default_user()

        logging.info(f"Uploading contract: {file.filename} ({file_size_mb:.2f}MB) by {uploader}")

        # Check for duplicate and get unique filename if needed
        final_filename = file.filename
        if blob_storage_service.check_duplicate(file.filename):
            final_filename = blob_storage_service.get_unique_filename(file.filename)
            logging.info(f"Duplicate detected, using unique filename: {final_filename}")

        # Upload to blob storage with unique filename
        blob_url = blob_storage_service.upload_from_bytes(
            file_bytes=file_bytes,
            filename=final_filename,
            overwrite=False
        )

        logging.info(f"Contract uploaded to blob storage: {blob_url}")

        # Create upload job
        job_svc = JobService(nosql_svc)

        job_request = ContractUploadJobRequest(
            filename=final_filename,  # Use the unique filename
            original_filename=file.filename,  # Keep track of original name
            blob_url=blob_url,
            uploaded_by=uploader,
            file_size_bytes=len(file_bytes)
        )

        job_id = await job_svc.create_job(
            user_id=uploader,
            job_type=JobType.CONTRACT_UPLOAD,
            request=job_request.model_dump(),
            priority=7  # Higher priority for user-initiated uploads
        )

        logging.info(f"Contract upload job created: {job_id} for file: {file.filename}")

        # Start background processing
        # Worker creates its own services to avoid connection lifecycle issues
        from src.services.background_worker import BackgroundWorker

        worker = BackgroundWorker()

        # Execute background task (worker will create its own DB connection)
        asyncio.create_task(worker.process_job(job_id, uploader))
        logging.info(f"Background worker started for upload job: {job_id}")

        return {
            "success": True,
            "job_id": job_id,
            "filename": final_filename,  # Return the actual filename used
            "original_filename": file.filename,  # Include original for reference
            "message": "Contract uploaded successfully and queued for processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error uploading contract: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contracts/upload-job/{job_id}")
async def get_upload_job_status(job_id: str, user_id: str = None):
    """
    Get status of contract upload job.

    Args:
        job_id: Job identifier
        user_id: User ID (optional, defaults to system_admin)

    Returns:
        Job status information including progress
    """
    from src.services.job_service import JobService

    try:
        # Use default user if not provided
        user = user_id or ConfigService.contract_upload_default_user()

        job_svc = JobService(nosql_svc)
        job = await job_svc.get_job(job_id, user)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job.model_dump(mode='json')

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting job status: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/contract_query")
async def contract_query(req: Request):
    """
    Process natural language contract queries.
    Combines graph search, vector search, and AI completion.
    """
    try:
        data = await req.json()
        question = data.get("question", "")
        filters = data.get("filters", {})
        selected_contracts = data.get("selected_contracts", [])

        # Use ContractStrategyBuilder to determine query strategy
        strategy_builder = ContractStrategyBuilder(question)
        strategy = strategy_builder.get_strategy()
        
        answer_parts = []
        
        # Execute based on strategy
        if strategy["use_db"]:
            # Query CosmosDB directly for entity-based questions
            db_results = await query_contracts_db(strategy["entities"], filters, selected_contracts)
            answer_parts.append(db_results)
        
        if strategy["use_vector"]:
            # Perform vector search for semantic queries
            vector_results = await vector_search_contracts(question, filters, selected_contracts)
            answer_parts.append(vector_results)
        
        if strategy["use_graph"]:
            # Query graph for relationship-based questions
            graph_results = await query_contract_graph(question, strategy["entities"])
            answer_parts.append(graph_results)
        
        # Combine results and generate final answer using AI
        context = "\n".join(answer_parts)
        
        if context:
            # Use AI to synthesize the answer
            prompt = f"""Based on the following contract information, answer this question: {question}
            
            Context:
            {context}
            
            Provide a clear, concise answer that directly addresses the question."""
            
            ai_response = await ai_svc.generate_completion(prompt)
            answer = ai_response.get("content", "Unable to generate answer.")
        else:
            # Fallback answer when no results found
            answer = "No relevant contracts found matching your query criteria."
        
        return JSONResponse(content={
            "answer": answer,
            "strategy": strategy,
            "context_used": len(context) if context else 0
        })
        
    except Exception as e:
        logging.error(f"Error processing contract query: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


async def query_contracts_db(entities, filters, selected_contracts):
    """Query CosmosDB for contracts based on entities"""
    try:
        nosql_svc.set_db("caig")
        nosql_svc.set_container("contracts")
        
        query = "SELECT * FROM c WHERE c.doctype = 'contract_parent'"
        params = []
        
        # Add entity filters
        if entities.get("contractor_parties"):
            query += " AND c.contractor_party IN (@contractors)"
            params.append({
                "name": "@contractors",
                "value": entities["contractor_parties"]
            })
        
        if entities.get("governing_laws"):
            query += " AND c.governing_law IN (@laws)"
            params.append({
                "name": "@laws", 
                "value": entities["governing_laws"]
            })
        
        # Add selected contract filter if specified
        if selected_contracts:
            # Frontend now sends full IDs with "contract_" prefix
            query += " AND c.id IN (@selected)"
            params.append({
                "name": "@selected",
                "value": selected_contracts
            })
        
        # Use parameterized_query to properly handle SQL parameters
        items = await nosql_svc.parameterized_query(
            sql_template=query,
            sql_parameters=params if params else [],
            cross_partition=True
        )
        
        # Format results
        results = []
        for item in items:
            results.append(f"Contract {item['id']}: {item.get('contractor_party', 'Unknown')} - Governed by {item.get('governing_law', 'Unknown')}")
        
        return "\n".join(results) if results else "No contracts found."
        
    except Exception as e:
        logging.error(f"Error querying contracts DB: {str(e)}")
        return ""


async def vector_search_contracts(question, filters, selected_contracts):
    """Perform vector search on contract clauses and chunks"""
    try:
        # Generate embedding for the question
        embedding_response = ai_svc.generate_embeddings(question)
        query_embedding = embedding_response.data[0].embedding
        
        # Search contract clauses
        nosql_svc.set_db("caig")
        nosql_svc.set_container("contract_clauses")
        
        # Build filter for selected contracts if specified
        filter_clause = None
        if selected_contracts:
            # Frontend now sends full IDs with "contract_" prefix
            filter_clause = f"c.parent_id IN ({','.join(['\"' + cid + '\"' for cid in selected_contracts])})"
        
        # Perform vector search
        results = await nosql_svc.vector_search(
            query_embedding,
            limit=10,
            filter_clause=filter_clause
        )
        
        # Format results
        clause_results = []
        for result in results:
            clause_results.append(
                f"Clause from {result.get('parent_id', 'Unknown')}: "
                f"{result.get('clause_type', 'Unknown')} - "
                f"{result.get('clause_text', '')[:200]}..."
            )
        
        return "\n".join(clause_results) if clause_results else "No relevant clauses found."
        
    except Exception as e:
        logging.error(f"Error in vector search: {str(e)}")
        return ""


async def query_contract_graph(question, entities):
    """Query the contract graph for relationships"""
    try:
        # Build SPARQL query based on entities
        sparql_query = build_contract_sparql(question, entities)
        
        # Execute SPARQL query against graph service
        graph_url = f"{ConfigService.graph_service_url()}/sparql_query"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                graph_url,
                json={"sparql": sparql_query},
                headers=websvc_headers
            )
            
        if response.status_code == 200:
            data = response.json()
            # Format graph results
            results = []
            for binding in data.get("results", {}).get("bindings", []):
                result_line = []
                for var, value in binding.items():
                    result_line.append(f"{var}: {value.get('value', '')}")
                results.append(" | ".join(result_line))
            
            return "\n".join(results) if results else "No graph relationships found."
        else:
            return "Unable to query graph."
            
    except Exception as e:
        logging.error(f"Error querying contract graph: {str(e)}")
        return ""


def build_contract_sparql(question, entities):
    """Build SPARQL query for contract graph based on question and entities"""
    # This is a simplified version - would need more sophisticated query building
    base_query = """
    PREFIX caig: <http://cosmosdb.com/caig#>
    SELECT ?contract ?contractor ?law
    WHERE {
        ?contract a caig:Contract .
        ?contract caig:hasContractor ?contractor .
        ?contract caig:governedBy ?law .
    """
    
    filters = []
    if entities.get("contractor_parties"):
        contractors = " ".join([f'"{c}"' for c in entities["contractor_parties"]])
        filters.append(f"FILTER(?contractor IN ({contractors}))")
    
    if entities.get("governing_laws"):
        laws = " ".join([f'"{l}"' for l in entities["governing_laws"]])
        filters.append(f"FILTER(?law IN ({laws}))")
    
    query = base_query + "\n".join(filters) + "\n} LIMIT 100"
    return query


# ============================================================================
# Contract Clause Retrieval Functions for Comparison
# ============================================================================

async def get_clause_by_id(nosql_svc: CosmosNoSQLService, clause_id: str):
    """
    Retrieve a specific clause document by its ID from the contract_clauses collection.
    
    Args:
        nosql_svc: The CosmosDB service instance
        clause_id: The ID of the clause to retrieve
    
    Returns:
        The clause document or None if not found
    """
    try:
        nosql_svc.set_container("contract_clauses")
        clause_doc = await nosql_svc.point_read(clause_id, "contract_clauses")
        return clause_doc
    except Exception as e:
        logging.warning(f"Clause not found with ID {clause_id}: {e}")
        return None


async def get_clauses_for_contract(nosql_svc: CosmosNoSQLService, contract_id: str, clause_types: list = None):
    """
    Retrieve all clauses for a specific contract, optionally filtered by clause types.
    
    Args:
        nosql_svc: The CosmosDB service instance
        contract_id: The contract ID (format: "contract_xxxxxxxxxx")
        clause_types: Optional list of clause types to filter by (if None, returns all)
                     Can be display names that will be converted to normalized names
    
    Returns:
        Dictionary mapping clause_type to clause document
    """
    # Reverse mapping of the clause_type_map from line 1831
    # Maps display names back to their normalized database names
    display_to_normalized = {
        "Indemnification": "Indemnification",
        "Indemnification Obligations": "IndemnificationObligations",
        "Workers Compensation Insurance": "WorkersCompensationInsurance",
        "Commercial Public Liability": "CommercialPublicLiability",
        "Automobile Insurance": "AutomobileInsurance",
        "Umbrella Insurance": "UmbrellaInsurance",
        "Assignability": "Assignability",
        "Data Breach Obligations": "DataBreachObligations",
        "Compliance Obligations": "ComplianceObligations",
        "Confidentiality Obligations": "ConfidentialityObligations",
        "Escalation Obligations": "EscalationObligations",
        "Limitation of Liability Obligations": "LimitationOfLiabilityObligations",
        "Payment Obligations": "PaymentObligations",
        "Renewal Notification": "RenewalNotification",
        "Service Level Agreement": "ServiceLevelAgreement",
        "Termination Obligations": "TerminationObligations",
        "Warranty Obligations": "WarrantyObligations",
        "Insurance Obligations": "InsuranceObligations",
        "Governing Law": "GoverningLaw"
    }
    
    # Normalize clause types if provided
    normalized_clause_types = None
    if clause_types is not None:
        normalized_clause_types = []
        for ct in clause_types:
            # Convert display name to normalized name
            normalized = display_to_normalized.get(ct, ct)  # Use ct as-is if not in mapping
            normalized_clause_types.append(normalized)
        logging.info(f"Normalized clause types from {clause_types} to {normalized_clause_types}")
    
    try:
        # First get the contract document to get clause IDs
        nosql_svc.set_container(ConfigService.graph_source_container())
        
        # Use point_read with the contract_id as document id and "contracts" as partition key
        contract_doc = await nosql_svc.point_read(contract_id, "contracts")
        
        if not contract_doc:
            logging.warning(f"Contract not found: {contract_id}")
            return {}
        
        clause_ids = contract_doc.get("clause_ids", [])
        clauses_by_type = {}
        
        # Retrieve each clause document
        nosql_svc.set_container("contract_clauses")
        for clause_id in clause_ids:
            try:
                clause_doc = await nosql_svc.point_read(clause_id, "contract_clauses")
                if clause_doc:
                    clause_type = clause_doc.get("clause_type", "")
                    
                    # If filtering by types, check if this type is included
                    # Use normalized types for comparison
                    if normalized_clause_types is None or clause_type in normalized_clause_types:
                        clauses_by_type[clause_type] = {
                            "clause_id": clause_id,
                            "clause_text": clause_doc.get("clause_text", ""),
                            "clause_type": clause_type,
                            "confidence": clause_doc.get("confidence", 0),
                            "parent_id": clause_doc.get("parent_id", "")
                        }
            except Exception as e:
                logging.warning(f"Could not retrieve clause {clause_id}: {e}")
                continue
        
        return clauses_by_type
        
    except Exception as e:
        logging.error(f"Error retrieving clauses for contract {contract_id}: {e}")
        return {}


async def get_contract_full_text(nosql_svc: CosmosNoSQLService, contract_id: str):
    """
    Retrieve the full contract text from the contracts collection.
    
    Args:
        nosql_svc: The CosmosDB service instance
        contract_id: The contract ID (format: "contract_xxxxxxxxxx")
    
    Returns:
        The contract text or None if not found
    """
    try:
        nosql_svc.set_container(ConfigService.graph_source_container())
        
        # Use point_read with the contract_id as document id and "contracts" as partition key
        contract_doc = await nosql_svc.point_read(contract_id, "contracts")
        
        if contract_doc:
            return contract_doc.get("contract_text", None)
        return None
        
    except Exception as e:
        logging.error(f"Error retrieving full text for contract {contract_id}: {e}")
        return None


async def retrieve_comparison_data(
    nosql_svc: CosmosNoSQLService,
    standard_contract_id: str,
    compare_contract_ids: list,
    comparison_mode: str,
    selected_clauses: list = None
):
    """
    Retrieve all necessary data for contract comparison.
    
    Args:
        nosql_svc: The CosmosDB service instance
        standard_contract_id: The ID of the standard contract
        compare_contract_ids: List of contract IDs to compare against
        comparison_mode: Either "full" or "clauses"
        selected_clauses: List of clause types to compare, or "all", or None for full mode
    
    Returns:
        Tuple of (standard_data, comparison_data, clause_cache)
    """
    clause_cache = {}  # Cache for storing clause documents by ID
    
    if comparison_mode == "full":
        # Get full contract texts
        standard_text = await get_contract_full_text(nosql_svc, standard_contract_id)
        standard_data = {
            "contract_id": standard_contract_id,
            "mode": "full",
            "content": standard_text
        }
        
        comparison_data = {}
        for contract_id in compare_contract_ids:
            contract_text = await get_contract_full_text(nosql_svc, contract_id)
            comparison_data[contract_id] = {
                "contract_id": contract_id,
                "mode": "full",
                "content": contract_text
            }
            
    else:  # clauses mode
        # Determine which clause types to retrieve
        clause_types_to_retrieve = None
        if selected_clauses and selected_clauses != "all":
            clause_types_to_retrieve = selected_clauses
        
        # Get clauses for standard contract
        standard_clauses = await get_clauses_for_contract(
            nosql_svc, standard_contract_id, clause_types_to_retrieve
        )
        
        # Store standard clauses in cache
        for clause_type, clause_data in standard_clauses.items():
            clause_cache[clause_data["clause_id"]] = clause_data
        
        standard_data = {
            "contract_id": standard_contract_id,
            "mode": "clauses",
            "clauses": standard_clauses
        }
        
        # Get clauses for comparison contracts
        comparison_data = {}
        for contract_id in compare_contract_ids:
            # If "all" is selected, get all clauses from comparison contracts
            # Otherwise, get the same clause types as the standard
            if selected_clauses == "all":
                contract_clauses = await get_clauses_for_contract(nosql_svc, contract_id, None)
            else:
                contract_clauses = await get_clauses_for_contract(
                    nosql_svc, contract_id, clause_types_to_retrieve
                )
            
            # Store comparison clauses in cache
            for clause_type, clause_data in contract_clauses.items():
                clause_cache[clause_data["clause_id"]] = clause_data
            
            comparison_data[contract_id] = {
                "contract_id": contract_id,
                "mode": "clauses",
                "clauses": contract_clauses
            }
    
    return standard_data, comparison_data, clause_cache


def create_comparison_prompt(standard_data, comparison_data, comparison_mode, selected_clauses=None):
    """
    Create a structured prompt for the LLM to compare contracts.
    Now delegates to specialized functions based on mode.
    
    Args:
        standard_data: Dictionary with standard contract data
        comparison_data: Dictionary with comparison contracts data
        comparison_mode: Either "full" or "clauses"
        selected_clauses: List of specific clause types to compare (for clauses mode)
    
    Returns:
        Formatted prompt string for the LLM
    """
    if comparison_mode == "full":
        return create_full_contract_comparison_prompt(standard_data, comparison_data)
    else:
        # For clauses mode, we need to know which specific clauses to compare
        if not selected_clauses:
            # If no specific clauses provided, use all clauses from standard contract
            selected_clauses = list(standard_data.get('clauses', {}).keys())
        return create_clause_comparison_prompt(standard_data, comparison_data, selected_clauses)


def create_clause_comparison_prompt(standard_data, comparison_data, selected_clauses):
    """
    Create a prompt specifically for clause-by-clause comparison.
    ONLY analyzes the specific clauses requested.
    
    Args:
        standard_data: Dictionary with standard contract data
        comparison_data: Dictionary with comparison contracts data
        selected_clauses: List of specific clause types to compare
    
    Returns:
        Formatted prompt string for the LLM
    """
    prompt = f"""
You are a legal contract analyst performing a CLAUSE-SPECIFIC comparison.

CRITICAL INSTRUCTIONS:
1. ONLY analyze the specific clauses listed below: {', '.join(selected_clauses)}
2. DO NOT analyze or mention any clauses not in this list
3. DO NOT suggest missing clauses beyond those requested
4. DO NOT provide critical findings about issues outside these specific clauses
5. If a requested clause is missing, note it but don't analyze alternatives

REQUESTED CLAUSES FOR COMPARISON: {', '.join(selected_clauses)}

STANDARD CONTRACT (ID: {standard_data['contract_id']}):
Requested Clauses:
"""
    
    # Only include the requested clauses from standard contract
    for clause_type in selected_clauses:
        clause_data = standard_data.get('clauses', {}).get(clause_type.replace(" ", ""))
        if clause_data:
            prompt += f"""
- {clause_type} (ID: {clause_data.get('clause_id', 'N/A')}):
  {clause_data.get('clause_text', 'Text not available')[:500]}...
"""
        else:
            prompt += f"""
- {clause_type}: NOT PRESENT IN STANDARD CONTRACT
"""
    
    prompt += "\n\nCONTRACTS TO COMPARE:\n"

    # For each comparison contract, handle both structured clauses and full text
    for contract_id, data in comparison_data.items():
        prompt += f"\nCONTRACT ID: {contract_id}\n"

        # Check if this is full text mode (Word Add-in hybrid mode)
        if data.get('mode') == 'full_as_clauses':
            # Word document with full text - LLM needs to extract clauses
            prompt += f"""
IMPORTANT: This is a raw document text. You need to:
1. Search for and extract the following clause types from the text: {', '.join(selected_clauses)}
2. If a clause type is not found, mark it as missing
3. Compare each found clause against the corresponding standard clause

Full Document Text:
{data.get('content', 'Text not available')}

Analyze and extract the following clauses from the above text:
"""
            for clause_type in selected_clauses:
                prompt += f"- {clause_type}\n"
        else:
            # Standard mode with pre-extracted clauses
            prompt += "Requested Clauses:\n"
            for clause_type in selected_clauses:
                clause_data = data.get('clauses', {}).get(clause_type.replace(" ", ""))
                if clause_data:
                    prompt += f"""
- {clause_type} (ID: {clause_data.get('clause_id', 'N/A')}):
  {clause_data.get('clause_text', 'Text not available')[:500]}...
"""
                else:
                    prompt += f"""
- {clause_type}: NOT PRESENT IN THIS CONTRACT
"""
    
    prompt += f"""

Provide your analysis in the following JSON structure:
{{
    "comparisons": [
        {{
            "contract_id": "<contract_id>",
            "overall_similarity_score": <0.0-1.0 based ONLY on the {len(selected_clauses)} requested clauses>,
            "risk_level": "<low|medium|high based ONLY on requested clauses>",
            "clause_analyses": [
                {{
                    "clause_type": "<ONLY from: {', '.join(selected_clauses)}>",
                    "standard_clause_id": "<clause_id or null>",
                    "compared_clause_id": "<clause_id or null>",
                    "exists_in_standard": <true|false>,
                    "exists_in_compared": <true|false>,
                    "similarity_score": <0.0-1.0, use 0.0 if missing>,
                    "key_differences": ["<differences in THIS clause only>"],
                    "risks": ["<risks for THIS clause only>"],
                    "summary": "<comparison of THIS specific clause>"
                }}
            ],
            "missing_clauses": ["<ONLY from requested list if missing>"],
            "additional_clauses": [],
            "critical_findings": ["<ONLY about the requested clauses>"]
        }}
    ]
}}

STRICT REQUIREMENTS:
- ONLY analyze these clauses: {', '.join(selected_clauses)}
- clause_analyses should have EXACTLY {len(selected_clauses)} entries (one per requested clause)
- missing_clauses should ONLY list clauses from the requested list that don't exist
- DO NOT mention any other clauses or contract sections
- overall_similarity_score should reflect ONLY the requested clauses
- critical_findings should be ONLY about the requested clauses

Return ONLY valid JSON, no additional text.
"""
    
    return prompt


def create_full_contract_comparison_prompt(standard_data, comparison_data):
    """
    Create a prompt for comprehensive full contract comparison.
    Analyzes the entire contract text and all aspects.
    
    Args:
        standard_data: Dictionary with standard contract data
        comparison_data: Dictionary with comparison contracts data
    
    Returns:
        Formatted prompt string for the LLM
    """
    prompt = f"""
You are a legal contract analyst performing a COMPREHENSIVE contract comparison.

INSTRUCTIONS:
1. Analyze the ENTIRE contracts comprehensively
2. Identify ALL differences, risks, and issues across the full text
3. Evaluate completeness and identify any missing standard provisions
4. Consider all legal, commercial, and operational implications

STANDARD CONTRACT (ID: {standard_data['contract_id']}):
{standard_data.get('content', 'Full contract text not available')}

CONTRACTS TO COMPARE:
"""
    
    for contract_id, data in comparison_data.items():
        prompt += f"""
CONTRACT ID: {contract_id}
{data.get('content', 'Full contract text not available')}
"""
    
    prompt += """

Provide your comprehensive analysis in the following JSON structure:
{
    "comparisons": [
        {
            "contract_id": "<contract_id>",
            "overall_similarity_score": <0.0-1.0 for ENTIRE contract>,
            "risk_level": "<low|medium|high overall assessment>",
            "clause_analyses": [
                {
                    "clause_type": "<any clause or section identified>",
                    "standard_clause_id": "<if applicable>",
                    "compared_clause_id": "<if applicable>",
                    "exists_in_standard": <true|false>,
                    "exists_in_compared": <true|false>,
                    "similarity_score": <0.0-1.0>,
                    "key_differences": ["<difference1>", "<difference2>"],
                    "risks": ["<risk1>", "<risk2>"],
                    "summary": "<comparison summary>"
                }
            ],
            "missing_clauses": ["<any important missing provisions>"],
            "additional_clauses": ["<provisions in compared but not standard>"],
            "critical_findings": ["<any critical issues found>"]
        }
    ]
}

Comprehensive Analysis Focus:
1. Legal completeness and compliance
2. Risk exposure across all terms
3. Missing standard provisions
4. Non-standard or unusual terms
5. Payment and performance obligations
6. Liability and indemnification
7. Termination and remedies
8. Intellectual property and confidentiality
9. Insurance requirements
10. Dispute resolution and governing law
11. Warranties and representations
12. Any other material terms

Return ONLY valid JSON, no additional text.
"""
    
    return prompt


async def enhance_comparison_response(comparison_results, clause_cache):
    """
    Enhance the LLM response by adding the actual clause texts back.
    
    Args:
        comparison_results: The parsed JSON response from the LLM
        clause_cache: Dictionary of clause_id -> clause_data
    
    Returns:
        Enhanced comparison results with clause texts
    """
    try:
        # Add clause texts back to the response
        for comparison in comparison_results.get("comparisons", []):
            for clause_analysis in comparison.get("clause_analyses", []):
                # Add standard clause text if available
                standard_clause_id = clause_analysis.get("standard_clause_id")
                if standard_clause_id and standard_clause_id in clause_cache:
                    clause_analysis["standard_clause_text"] = clause_cache[standard_clause_id].get("clause_text", "")
                
                # Add compared clause text if available
                compared_clause_id = clause_analysis.get("compared_clause_id")
                if compared_clause_id and compared_clause_id in clause_cache:
                    clause_analysis["compared_clause_text"] = clause_cache[compared_clause_id].get("clause_text", "")
        
        return comparison_results
    except Exception as e:
        logging.error(f"Error enhancing comparison response: {e}")
        return comparison_results


@app.post("/api/compare-contracts")
async def compare_contracts(request: Request):
    """
    Compare contracts endpoint that analyzes differences between a standard contract
    and one or more comparison contracts.

    Expected request body (contract IDs):
    {
        "standardContractId": "contract_xxx",
        "compareContractIds": ["contract_yyy", "contract_zzz"],
        "comparisonMode": "clauses" | "full",
        "selectedClauses": ["ClauseType1", "ClauseType2"] | "all"
    }

    OR (inline text - for Word Add-in track changes):
    {
        "originalText": "Full text of original version...",
        "revisedText": "Full text of revised version...",
        "comparisonMode": "full"
    }

    OR (hybrid - for Word Add-in compare with standard):
    {
        "standardContractId": "contract_xxx",
        "currentDocumentText": "Full text of current Word document...",
        "comparisonMode": "clauses" | "full",
        "selectedClauses": ["ClauseType1", "ClauseType2"] | "all"
    }
    """
    try:
        body = await request.json()

        # Check if using inline text (Word Add-in track changes mode)
        original_text = body.get("originalText")
        revised_text = body.get("revisedText")
        current_document_text = body.get("currentDocumentText")

        if original_text and revised_text:
            # INLINE TEXT MODE - for Word Add-in track changes
            logging.info("Contract comparison using inline text (track changes mode)")
            logging.info(f"  - Original text length: {len(original_text)} characters")
            logging.info(f"  - Revised text length: {len(revised_text)} characters")
            logging.info(f"  - Original text preview (first 500 chars): {original_text[:500]}")
            logging.info(f"  - Revised text preview (first 500 chars): {revised_text[:500]}")

            # Log character difference
            length_diff = len(revised_text) - len(original_text)
            logging.info(f"  - Text length difference: {'+' if length_diff > 0 else ''}{length_diff} characters")

            comparison_mode = "full"  # Only full mode supported for inline text

            # Create data structures for inline text
            standard_data = {
                "contract_id": "word_original",
                "mode": "full",
                "content": original_text
            }

            comparison_data = {
                "word_revised": {
                    "contract_id": "word_revised",
                    "mode": "full",
                    "content": revised_text
                }
            }

            clause_cache = {}
            # Initialize CosmosDB service for usage tracking (even for inline text)
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()
            standard_contract_id = "word_original"
            compare_contract_ids = ["word_revised"]
            model_selection = body.get("modelSelection", "primary")  # Get model selection for inline text mode
            user_email = body.get("userEmail", "default@user.com")  # Get user email for inline text mode

        elif current_document_text and body.get("standardContractId"):
            # HYBRID MODE - for Word Add-in compare with standard
            # Combines CosmosDB standard contract with inline Word document text
            logging.info("Contract comparison using hybrid mode (Word Add-in compare with standard)")

            standard_contract_id = body.get("standardContractId")
            comparison_mode = body.get("comparisonMode", "clauses")
            selected_clauses = body.get("selectedClauses", "all")
            model_selection = body.get("modelSelection", "primary")
            user_email = body.get("userEmail", "default@user.com")

            # Validate document size (1MB limit for POC)
            MAX_DOC_SIZE = 1 * 1024 * 1024  # 1MB in bytes
            doc_size = len(current_document_text.encode('utf-8'))

            if doc_size > MAX_DOC_SIZE:
                logging.warning(f"Document too large: {doc_size} bytes (limit: {MAX_DOC_SIZE})")
                return JSONResponse(
                    content={
                        "success": False,
                        "error": "Document too large. Coming Soon: support for documents over 1MB."
                    },
                    status_code=400
                )

            logging.info(f"  - Standard contract ID: {standard_contract_id}")
            logging.info(f"  - Current document length: {len(current_document_text)} characters ({doc_size} bytes)")
            logging.info(f"  - Comparison mode: {comparison_mode}")
            logging.info(f"  - Selected clauses: {selected_clauses}")
            logging.info(f"  - Document preview (first 500 chars): {current_document_text[:500]}")

            # Initialize CosmosDB service
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()

            # Fetch standard contract data based on comparison mode
            if comparison_mode == "full":
                # Get full text of standard contract
                standard_text = await get_contract_full_text(nosql_svc, standard_contract_id)
                standard_data = {
                    "contract_id": standard_contract_id,
                    "mode": "full",
                    "content": standard_text
                }

                # Create temporary contract for Word document
                comparison_data = {
                    "word_current": {
                        "contract_id": "word_current",
                        "mode": "full",
                        "content": current_document_text
                    }
                }

                clause_cache = {}

            else:  # clauses mode
                # Determine which clause types to retrieve
                clause_types_to_retrieve = None
                if selected_clauses and selected_clauses != "all":
                    clause_types_to_retrieve = selected_clauses

                # Get clauses for standard contract
                standard_clauses = await get_clauses_for_contract(
                    nosql_svc, standard_contract_id, clause_types_to_retrieve
                )

                # Initialize clause cache with standard clauses
                clause_cache = {}
                for clause_type, clause_data in standard_clauses.items():
                    clause_cache[clause_data["clause_id"]] = clause_data

                standard_data = {
                    "contract_id": standard_contract_id,
                    "mode": "clauses",
                    "clauses": standard_clauses
                }

                # For Word document, we need to extract clauses from the text
                # For now, treat it as full text and let the LLM extract clause-level analysis
                # TODO: Future enhancement - implement clause extraction from raw text
                comparison_data = {
                    "word_current": {
                        "contract_id": "word_current",
                        "mode": "full_as_clauses",  # Special mode: full text analyzed as clauses
                        "content": current_document_text,
                        "note": "Clause extraction from text will be performed by LLM"
                    }
                }

            compare_contract_ids = ["word_current"]

        else:
            # CONTRACT ID MODE - existing functionality
            # Extract parameters
            standard_contract_id = body.get("standardContractId")
            compare_contract_ids = body.get("compareContractIds", [])
            comparison_mode = body.get("comparisonMode", "clauses")
            selected_clauses = body.get("selectedClauses", "all")
            model_selection = body.get("modelSelection", "primary")  # Get model selection
            user_email = body.get("userEmail", "default@user.com")  # Get user email

            if not standard_contract_id:
                return JSONResponse(
                    content={"success": False, "error": "Standard contract ID or originalText is required"},
                    status_code=400
                )

            if not compare_contract_ids:
                return JSONResponse(
                    content={"success": False, "error": "At least one comparison contract ID or revisedText is required"},
                    status_code=400
                )

            # Check if batch mode should be used
            # Batch mode triggers: explicit request OR ≥3 contracts to compare
            force_batch = body.get("forceBatch", False)
            should_batch = force_batch or len(compare_contract_ids) >= 3

            if should_batch:
                # BATCH MODE: Create job and return job_id
                logging.info(f"Using BATCH MODE for comparison (contracts: {len(compare_contract_ids)})")

                # Initialize job service
                from src.services.job_service import JobService
                from src.models.job_models import JobType

                nosql_svc = CosmosNoSQLService()
                await nosql_svc.initialize()
                job_svc = JobService(nosql_svc)

                # Create job
                job_request = {
                    "standardContractId": standard_contract_id,
                    "compareContractIds": compare_contract_ids,
                    "comparisonMode": comparison_mode,
                    "selectedClauses": selected_clauses,
                    "modelSelection": model_selection,
                    "userEmail": user_email
                }

                job_id = await job_svc.create_job(
                    user_id=user_email,
                    job_type=JobType.CONTRACT_COMPARISON,
                    request=job_request,
                    priority=5
                )

                # Close DB connection (job created, worker will create its own connection)
                await nosql_svc.close()

                # Start background processing
                from src.services.background_worker import BackgroundWorker
                import asyncio

                # Worker creates its own services to avoid connection lifecycle issues
                worker = BackgroundWorker()

                # Execute background task
                asyncio.create_task(worker.process_job(job_id, user_email))

                # Return job_id immediately
                return JSONResponse(content={
                    "success": True,
                    "batch_mode": True,
                    "job_id": job_id,
                    "message": f"Comparison job submitted successfully. Job ID: {job_id}",
                    "status": "queued"
                })

            # REAL-TIME MODE: Continue with existing processing
            logging.info(f"Using REAL-TIME MODE for comparison (contracts: {len(compare_contract_ids)})")

            # Initialize services
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()

            # Log the request for debugging
            logging.info(f"Contract comparison request - Standard: {standard_contract_id}, Compare: {compare_contract_ids}, Mode: {comparison_mode}, Clauses: {selected_clauses}")

            # Retrieve comparison data
            standard_data, comparison_data, clause_cache = await retrieve_comparison_data(
                nosql_svc,
                standard_contract_id,
                compare_contract_ids,
                comparison_mode,
                selected_clauses if comparison_mode == "clauses" else None
            )
        
        # Check if we got data
        if comparison_mode == "clauses":
            if not standard_data.get("clauses"):
                logging.warning(f"No clauses found for standard contract {standard_contract_id}")
                return JSONResponse(
                    content={
                        "success": False, 
                        "error": f"No clauses found for standard contract {standard_contract_id}"
                    },
                    status_code=404
                )
        else:
            if not standard_data.get("content"):
                logging.warning(f"No contract text found for standard contract {standard_contract_id}")
                return JSONResponse(
                    content={
                        "success": False,
                        "error": f"No contract text found for standard contract {standard_contract_id}"
                    },
                    status_code=404
                )
        
        # Create LLM prompt with selected clauses for clause mode
        if comparison_mode == "clauses" and selected_clauses != "all":
            # Pass the specific clauses requested
            llm_prompt = create_comparison_prompt(standard_data, comparison_data, comparison_mode, selected_clauses)
        else:
            # For full mode or when all clauses requested, let the function determine
            llm_prompt = create_comparison_prompt(standard_data, comparison_data, comparison_mode)
        
        # Log prompt length for monitoring
        logging.info(f"LLM prompt length: {len(llm_prompt)} characters")
        
        # Send to LLM for analysis
        system_prompt = "You are a legal contract analysis expert. Provide detailed, accurate comparisons in JSON format."
        
        # For full contract mode, we may need to truncate to avoid token limits
        if comparison_mode == "full":
            # Log token counts if available
            logging.info(f"Full contract comparison - checking token limits")
            # Truncate prompt if it's too long (rough estimate: 4 chars = 1 token)
            # Increased limit to handle larger contracts
            max_prompt_chars = 100000  # Approximately 25,000 tokens for input
            if len(llm_prompt) > max_prompt_chars:
                logging.warning(f"Prompt too long ({len(llm_prompt)} chars), truncating to {max_prompt_chars}")
                # Keep the structure but truncate the contract texts
                # This is a simple truncation - in production you'd want smarter truncation
                llm_prompt = llm_prompt[:max_prompt_chars] + "\n... [TRUNCATED FOR LENGTH]" + llm_prompt[-2000:]
        
        # Track start time for usage metrics
        import time
        start_time = time.time()

        # Use the special contract comparison method with higher token limit
        llm_response = ai_svc.get_completion_for_contracts(
            user_prompt=llm_prompt,
            system_prompt=system_prompt,
            max_tokens=6000,  # Reasonable limit for contract comparisons
            model_selection=model_selection  # Pass model selection
        )

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        # Parse LLM response as JSON
        try:
            # Extract JSON from the response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                comparison_results = json.loads(json_str)
            else:
                # Try parsing the entire response
                comparison_results = json.loads(llm_response)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse LLM response as JSON: {e}")
            logging.error(f"LLM response: {llm_response[:1000]}...")  # Log first 1000 chars
            
            # Return a structured error response
            comparison_results = {
                "comparisons": [{
                    "contract_id": cid,
                    "error": "Failed to parse comparison results",
                    "raw_response": llm_response[:500]
                } for cid in compare_contract_ids]
            }
        
        # Enhance response with clause texts (if in clauses mode)
        if comparison_mode == "clauses":
            comparison_results = await enhance_comparison_response(comparison_results, clause_cache)

        # Add metadata to response
        response = {
            "success": True,
            "standardContractId": standard_contract_id,
            "compareContractIds": compare_contract_ids,
            "comparisonMode": comparison_mode,
            "selectedClauses": selected_clauses if comparison_mode == "clauses" else None,
            "results": comparison_results
        }

        # Close DB connection if it was opened (not used for inline text mode)
        if nosql_svc:
            await nosql_svc.close()

        return JSONResponse(content=response)
        
    except Exception as e:
        logging.error(f"Contract comparison error: {str(e)}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/query_contracts")
async def query_contracts(request: Request):
    """
    Process natural language questions against selected contracts.
    Retrieves full contract text, truncates if needed, and returns AI-generated
    analysis in markdown format.

    Expected request body:
    {
        "question": "What are the payment terms?",
        "contract_ids": ["contract_xxx", "contract_yyy"]
    }
    """
    import time
    t1 = time.perf_counter()

    print(f"\n{'='*80}")
    print(f"[TIMING] 🚀 Query Contracts Request Started")
    print(f"{'='*80}")

    try:
        body = await request.json()

        # Extract parameters
        question = body.get("question", "")
        contract_ids = body.get("contract_ids", [])

        print(f"[TIMING] Question: {question[:100]}...")
        print(f"[TIMING] Contract IDs: {len(contract_ids)} contracts")

        if not question or not question.strip():
            return JSONResponse(
                content={"error": "Question is required"},
                status_code=400
            )

        if not contract_ids or len(contract_ids) == 0:
            return JSONResponse(
                content={"error": "At least one contract ID is required"},
                status_code=400
            )

        # Check if batch mode should be used (based on token threshold or explicit request)
        force_batch = body.get("forceBatch", False)
        model_selection = body.get("modelSelection", "primary")
        user_email = body.get("userEmail", "system")

        # Calculate estimated tokens (frontend sends this if available)
        estimated_tokens = body.get("estimatedTokens", 0)

        # Token threshold: 42,000 tokens (50K budget - 8K reserved)
        # This matches the frontend threshold in contract-workbench.component.ts
        TOKEN_THRESHOLD = 42000
        should_batch = force_batch or estimated_tokens > TOKEN_THRESHOLD

        if should_batch:
            # BATCH MODE: Create job and return job_id
            logging.info(f"Using BATCH MODE for query (estimated tokens: {estimated_tokens})")

            # Initialize services
            from src.services.job_service import JobService
            from src.models.job_models import JobType

            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()
            job_svc = JobService(nosql_svc)

            # Create job
            job_request = {
                "question": question,
                "contract_ids": contract_ids,
                "modelSelection": model_selection,
                "userEmail": user_email
            }

            job_id = await job_svc.create_job(
                user_id=user_email,
                job_type=JobType.CONTRACT_QUERY,
                request=job_request,
                priority=5
            )

            # Close DB connection (job created, worker will create its own connection)
            await nosql_svc.close()

            # Start background processing
            from src.services.background_worker import BackgroundWorker
            import asyncio

            # Worker creates its own services to avoid connection lifecycle issues
            worker = BackgroundWorker()

            # Execute background task
            asyncio.create_task(worker.process_job(job_id, user_email))

            # Return job_id immediately
            return JSONResponse(content={
                "success": True,
                "batch_mode": True,
                "job_id": job_id,
                "message": f"Query job submitted successfully. Job ID: {job_id}",
                "status": "queued",
                "estimated_tokens": estimated_tokens
            })

        # REAL-TIME MODE: Continue with existing processing
        logging.info(f"Using REAL-TIME MODE for query (estimated tokens: {estimated_tokens})")

        # Initialize services
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        nosql_svc.set_container(ConfigService.graph_source_container())

        logging.info(f"Query contracts request - Question: '{question}', Contracts: {contract_ids}")

        # Retrieve contracts and their text
        contracts_data = []
        contracts_analyzed = []
        truncated_contracts = []

        # Token budget: 128K context window, reserve 8K for system prompt and response
        available_tokens = 120000
        tokens_per_contract_budget = available_tokens // len(contract_ids)

        logging.info(f"Token budget: {available_tokens} total, ~{tokens_per_contract_budget} per contract")

        print(f"[TIMING] Retrieving {len(contract_ids)} contracts from database...")
        contract_retrieval_start = time.perf_counter()

        for contract_id in contract_ids:
            try:
                # Retrieve contract document
                contract_doc = await nosql_svc.point_read(contract_id, "contracts")

                if not contract_doc:
                    logging.warning(f"Contract {contract_id} not found")
                    continue

                contract_text = contract_doc.get("contract_text", "")
                contract_title = contract_doc.get("title", contract_id)

                if not contract_text:
                    logging.warning(f"Contract {contract_id} has no contract_text")
                    continue

                # Calculate tokens
                token_count = ai_svc.num_tokens_from_string(contract_text)
                logging.info(f"Contract {contract_id}: {token_count} tokens")

                # Truncate if needed
                was_truncated = False
                if token_count > tokens_per_contract_budget:
                    # Truncate to budget (approximate by character count)
                    # Roughly 4 characters per token
                    max_chars = tokens_per_contract_budget * 4
                    contract_text = contract_text[:max_chars]
                    was_truncated = True
                    truncated_contracts.append(contract_id)
                    logging.info(f"Contract {contract_id} truncated from {token_count} to ~{tokens_per_contract_budget} tokens")

                contracts_data.append({
                    "id": contract_id,
                    "title": contract_title,
                    "text": contract_text,
                    "was_truncated": was_truncated
                })
                contracts_analyzed.append(contract_id)

            except Exception as e:
                logging.error(f"Error retrieving contract {contract_id}: {str(e)}")
                continue

        contract_retrieval_end = time.perf_counter()
        contract_retrieval_elapsed = contract_retrieval_end - contract_retrieval_start
        print(f"[TIMING] ✅ Contract retrieval completed in {contract_retrieval_elapsed:.2f}s - {len(contracts_data)} contracts loaded")
        logging.info(f"Contract retrieval completed in {contract_retrieval_elapsed:.2f}s - {len(contracts_data)} contracts loaded")

        if not contracts_data:
            return JSONResponse(
                content={
                    "answer": "No contract text could be retrieved for analysis.",
                    "contracts_analyzed": [],
                    "was_truncated": False,
                    "truncated_contracts": None,
                    "total_tokens_used": 0,
                    "elapsed": 0,
                    "error": "No contracts found or no contract_text available"
                },
                status_code=404
            )

        # Build system prompt
        system_prompt = """You are a legal contract analysis expert. Analyze the provided contracts and answer the user's question.

**Instructions:**
- Provide a clear, well-structured response in **Markdown format**
- Break out your analysis **by contract**, using headings (## Contract Title)
- **Cite specific sections** from the contract text to support your findings
- Use bullet points or numbered lists for clarity
- If a contract was truncated, note that the analysis may be incomplete
- Be precise and professional in your language

**Response Format:**
```markdown
# Analysis

## Contract 1: [Title]
[Your analysis with specific citations]

## Contract 2: [Title]
[Your analysis with specific citations]

# Summary
[Brief summary of findings across all contracts]
```"""

        # Build user prompt with all contract texts
        user_prompt = f"""**Question:** {question}

---

"""

        for contract in contracts_data:
            user_prompt += f"""## Contract: {contract['title']} (ID: {contract['id']})

"""
            if contract['was_truncated']:
                user_prompt += "**Note:** This contract text was truncated due to size limitations. Analysis may be incomplete.\n\n"

            user_prompt += f"""**Contract Text:**
{contract['text']}

---

"""

        user_prompt += f"""\n**Question to Answer:** {question}

Please analyze each contract and provide your response in the markdown format specified."""

        # Calculate total tokens
        total_tokens = ai_svc.num_tokens_from_string(system_prompt + user_prompt)
        print(f"[TIMING] Total prompt tokens: {total_tokens}")
        logging.info(f"Total prompt tokens: {total_tokens}")

        # Call LLM (use async client for better performance)
        # Create async Azure OpenAI client
        print(f"[TIMING] Creating async Azure OpenAI client...")
        client_create_start = time.perf_counter()
        async_client = AsyncAzureOpenAI(
            azure_endpoint=ai_svc.aoai_endpoint,
            api_key=ai_svc.aoai_api_key,
            api_version=ai_svc.aoai_version,
        )
        client_create_end = time.perf_counter()
        client_create_elapsed = client_create_end - client_create_start
        print(f"[TIMING]   → Client creation: {client_create_elapsed:.4f}s")
        logging.info(f"Client creation: {client_create_elapsed:.4f}s")

        print(f"[TIMING] Starting LLM async call...")
        print(f"[TIMING]   → Model: {ai_svc.completions_deployment}")
        print(f"[TIMING]   → Endpoint: {ai_svc.aoai_endpoint}")
        print(f"[TIMING]   → Max tokens: 4000")

        llm_start = time.perf_counter()
        completion = await async_client.chat.completions.create(
            model=ai_svc.completions_deployment,
            temperature=ConfigService.get_completion_temperature(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4000  # Reserve enough for detailed response
        )
        llm_end = time.perf_counter()
        llm_elapsed = llm_end - llm_start
        print(f"[TIMING] ✅ LLM async call completed in {llm_elapsed:.2f}s")
        logging.info(f"LLM async call completed in {llm_elapsed:.2f}s")

        # Extract response content
        print(f"[TIMING] Extracting response content...")
        extract_start = time.perf_counter()
        answer = completion.choices[0].message.content

        # Log Azure's reported metrics if available
        if hasattr(completion, 'usage'):
            print(f"[TIMING]   → Prompt tokens: {completion.usage.prompt_tokens}")
            print(f"[TIMING]   → Completion tokens: {completion.usage.completion_tokens}")
            print(f"[TIMING]   → Total tokens: {completion.usage.total_tokens}")

        extract_end = time.perf_counter()
        extract_elapsed = extract_end - extract_start
        print(f"[TIMING]   → Content extraction: {extract_elapsed:.4f}s")

        # Close the async client
        print(f"[TIMING] Closing async client...")
        close_start = time.perf_counter()
        await async_client.close()
        close_end = time.perf_counter()
        close_elapsed = close_end - close_start
        print(f"[TIMING]   → Client close: {close_elapsed:.4f}s")

        t2 = time.perf_counter()
        elapsed = (t2 - t1)

        await nosql_svc.close()

        print(f"[TIMING] ✅ Query contracts TOTAL completed in {elapsed:.2f}s")
        logging.info(f"Query contracts completed in {elapsed:.2f}s")

        return JSONResponse(content={
            "answer": answer,
            "contracts_analyzed": contracts_analyzed,
            "was_truncated": len(truncated_contracts) > 0,
            "truncated_contracts": truncated_contracts if truncated_contracts else None,
            "total_tokens_used": total_tokens,
            "elapsed": elapsed,
            "error": None
        })

    except Exception as e:
        logging.error(f"Error in query_contracts: {str(e)}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            content={
                "answer": "",
                "contracts_analyzed": [],
                "was_truncated": False,
                "truncated_contracts": None,
                "total_tokens_used": 0,
                "elapsed": 0,
                "error": str(e)
            },
            status_code=500
        )


@app.post("/api/query_contracts_stream")
async def query_contracts_stream(request: Request):
    """
    Stream natural language questions against selected contracts using SSE.
    Provides progressive response display for better user experience.

    Expected request body:
    {
        "question": "What are the payment terms?",
        "contract_ids": ["contract_xxx", "contract_yyy"]
    }

    Returns Server-Sent Events (SSE) stream with events:
    - metadata: Initial request information
    - content: Progressive response chunks
    - complete: Final completion with timing metrics
    - error: Error information if something fails
    """
    # Read request body BEFORE creating streaming response
    try:
        body = await request.json()
        question = body.get("question", "")
        contract_ids = body.get("contract_ids", [])
    except Exception as e:
        logging.error(f"Error parsing request body: {str(e)}")
        return JSONResponse(
            content={"error": f"Invalid request body: {str(e)}"},
            status_code=400
        )

    async def generate_stream(question: str, contract_ids: list):
        """Generator function for SSE streaming"""
        import time
        t1 = time.perf_counter()

        print(f"\n{'='*80}")
        print(f"[TIMING] 🚀 Query Contracts STREAMING Request Started")
        print(f"{'='*80}")

        try:
            print(f"[TIMING] Question: {question[:100]}...")
            print(f"[TIMING] Contract IDs: {len(contract_ids)} contracts")

            # Send initial metadata event
            yield f"event: metadata\n"
            yield f"data: {json.dumps({'contracts_count': len(contract_ids), 'question': question})}\n\n"

            if not question or not question.strip():
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': 'Question is required'})}\n\n"
                return

            if not contract_ids or len(contract_ids) == 0:
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': 'At least one contract ID is required'})}\n\n"
                return

            # Initialize services
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()
            nosql_svc.set_container(ConfigService.graph_source_container())

            logging.info(f"Query contracts streaming request - Question: '{question}', Contracts: {contract_ids}")

            # Retrieve contracts and their text
            contracts_data = []
            contracts_analyzed = []
            truncated_contracts = []

            # Token budget: 128K context window, reserve 8K for system prompt and response
            available_tokens = 120000
            tokens_per_contract_budget = available_tokens // len(contract_ids)

            logging.info(f"Token budget: {available_tokens} total, ~{tokens_per_contract_budget} per contract")

            print(f"[TIMING] Retrieving {len(contract_ids)} contracts from database...")
            contract_retrieval_start = time.perf_counter()

            for contract_id in contract_ids:
                try:
                    # Retrieve contract document
                    contract_doc = await nosql_svc.point_read(contract_id, "contracts")

                    if not contract_doc:
                        logging.warning(f"Contract {contract_id} not found")
                        continue

                    contract_text = contract_doc.get("contract_text", "")
                    contract_title = contract_doc.get("title", contract_id)

                    if not contract_text:
                        logging.warning(f"Contract {contract_id} has no contract_text")
                        continue

                    # Calculate tokens
                    token_count = ai_svc.num_tokens_from_string(contract_text)
                    logging.info(f"Contract {contract_id}: {token_count} tokens")

                    # Truncate if needed
                    was_truncated = False
                    if token_count > tokens_per_contract_budget:
                        max_chars = tokens_per_contract_budget * 4
                        contract_text = contract_text[:max_chars]
                        was_truncated = True
                        truncated_contracts.append(contract_id)
                        logging.info(f"Contract {contract_id} truncated from {token_count} to ~{tokens_per_contract_budget} tokens")

                    contracts_data.append({
                        "id": contract_id,
                        "title": contract_title,
                        "text": contract_text,
                        "was_truncated": was_truncated
                    })
                    contracts_analyzed.append(contract_id)

                except Exception as e:
                    logging.error(f"Error retrieving contract {contract_id}: {str(e)}")
                    continue

            contract_retrieval_end = time.perf_counter()
            contract_retrieval_elapsed = contract_retrieval_end - contract_retrieval_start
            print(f"[TIMING] ✅ Contract retrieval completed in {contract_retrieval_elapsed:.2f}s - {len(contracts_data)} contracts loaded")
            logging.info(f"Contract retrieval completed in {contract_retrieval_elapsed:.2f}s - {len(contracts_data)} contracts loaded")

            if not contracts_data:
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': 'No contract text could be retrieved for analysis.'})}\n\n"
                await nosql_svc.close()
                return

            # Build system prompt
            system_prompt = """You are a legal contract analysis expert. Analyze the provided contracts and answer the user's question.

**Instructions:**
- Provide a clear, well-structured response in **Markdown format**
- Break out your analysis **by contract**, using headings (## Contract Title)
- **Cite specific sections** from the contract text to support your findings
- Use bullet points or numbered lists for clarity
- If a contract was truncated, note that the analysis may be incomplete
- Be precise and professional in your language

**Response Format:**
```markdown
# Analysis

## Contract 1: [Title]
[Your analysis with specific citations]

## Contract 2: [Title]
[Your analysis with specific citations]

# Summary
[Brief summary of findings across all contracts]
```"""

            # Build user prompt with all contract texts
            user_prompt = f"""**Question:** {question}

---

"""

            for contract in contracts_data:
                user_prompt += f"""## Contract: {contract['title']} (ID: {contract['id']})

"""
                if contract['was_truncated']:
                    user_prompt += "**Note:** This contract text was truncated due to size limitations. Analysis may be incomplete.\n\n"

                user_prompt += f"""**Contract Text:**
{contract['text']}

---

"""

            user_prompt += f"""\n**Question to Answer:** {question}

Please analyze each contract and provide your response in the markdown format specified."""

            # Calculate total tokens
            total_tokens = ai_svc.num_tokens_from_string(system_prompt + user_prompt)
            print(f"[TIMING] Total prompt tokens: {total_tokens}")
            logging.info(f"Total prompt tokens: {total_tokens}")

            # Create async Azure OpenAI client for streaming
            print(f"[TIMING] Creating async Azure OpenAI client for streaming...")
            client_create_start = time.perf_counter()
            async_client = AsyncAzureOpenAI(
                azure_endpoint=ai_svc.aoai_endpoint,
                api_key=ai_svc.aoai_api_key,
                api_version=ai_svc.aoai_version,
            )
            client_create_end = time.perf_counter()
            client_create_elapsed = client_create_end - client_create_start
            print(f"[TIMING]   → Client creation: {client_create_elapsed:.4f}s")
            logging.info(f"Client creation: {client_create_elapsed:.4f}s")

            print(f"[TIMING] Starting LLM streaming call...")
            print(f"[TIMING]   → Model: {ai_svc.completions_deployment}")
            print(f"[TIMING]   → Endpoint: {ai_svc.aoai_endpoint}")
            print(f"[TIMING]   → Max tokens: 4000")

            llm_start = time.perf_counter()
            first_token_received = False

            # Stream the response
            stream = await async_client.chat.completions.create(
                model=ai_svc.completions_deployment,
                temperature=ConfigService.get_completion_temperature(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                stream=True  # Enable streaming
            )

            full_response = ""
            token_count = 0

            async for chunk in stream:
                if not first_token_received:
                    first_token_time = time.perf_counter() - llm_start
                    print(f"[TIMING] ⚡ First token received in {first_token_time:.2f}s")
                    logging.info(f"First token received in {first_token_time:.2f}s")
                    first_token_received = True

                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_response += content
                        token_count += 1

                        # Send content chunk as SSE
                        yield f"data: {json.dumps({'content': content})}\n\n"

            llm_end = time.perf_counter()
            llm_elapsed = llm_end - llm_start
            print(f"[TIMING] ✅ LLM streaming completed in {llm_elapsed:.2f}s")
            print(f"[TIMING]   → Streamed {token_count} chunks")
            logging.info(f"LLM streaming completed in {llm_elapsed:.2f}s - {token_count} chunks")

            # Close the async client
            print(f"[TIMING] Closing async client...")
            await async_client.close()
            await nosql_svc.close()

            # Send completion event
            t2 = time.perf_counter()
            total_elapsed = t2 - t1

            print(f"[TIMING] ✅ Query contracts streaming TOTAL completed in {total_elapsed:.2f}s")
            logging.info(f"Query contracts streaming completed in {total_elapsed:.2f}s")

            # Build completion data as a proper dictionary
            completion_data = {
                'elapsed': round(total_elapsed, 2),
                'llm_time': round(llm_elapsed, 2),
                'contracts_analyzed': contracts_analyzed,
                'was_truncated': len(truncated_contracts) > 0,
                'truncated_contracts': truncated_contracts if truncated_contracts else None,
                'total_tokens_used': total_tokens
            }

            yield f"event: complete\n"
            yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            print(f"[ERROR] Streaming error: {str(e)}")
            logging.error(f"Error in query_contracts_stream: {str(e)}")
            logging.error(traceback.format_exc())
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(question, contract_ids),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering if behind proxy
        }
    )


# Test endpoint for clause retrieval
@app.get("/api/test-clause-retrieval/{contract_id}")
async def test_clause_retrieval(contract_id: str):
    """
    Test endpoint to verify clause retrieval functions work correctly.
    This is temporary and should be removed after testing.
    """
    try:
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        
        # First, let's check if we can find the contract document
        nosql_svc.set_container(ConfigService.graph_source_container())
        
        # Try different ID formats
        contract_doc = None
        found_method = None
        
        # Try to read the contract document using the correct partition key
        try:
            contract_doc = await nosql_svc.point_read(contract_id, "contracts")
            found_method = "point_read_with_contracts_pk"
        except Exception as e:
            logging.debug(f"Could not find contract with ID {contract_id}: {e}")
        
        contract_info = {
            "found": contract_doc is not None,
            "method": found_method,
            "id": contract_doc.get("id") if contract_doc else None,
            "imageQuestDocumentId": contract_doc.get("imageQuestDocumentId") if contract_doc else None,
            "has_clause_ids": "clause_ids" in contract_doc if contract_doc else False,
            "clause_ids_count": len(contract_doc.get("clause_ids", [])) if contract_doc else 0,
            "sample_clause_ids": contract_doc.get("clause_ids", [])[:3] if contract_doc else []
        }
        
        # Test 1: Get all clauses for the contract
        all_clauses = await get_clauses_for_contract(nosql_svc, contract_id, None)
        
        # Test 2: Get specific clauses
        specific_clauses = await get_clauses_for_contract(
            nosql_svc, contract_id, ["Indemnification", "PaymentObligations"]
        )
        
        # Test 3: Get full contract text
        full_text = await get_contract_full_text(nosql_svc, contract_id)
        
        await nosql_svc.close()
        
        return {
            "success": True,
            "contract_id": contract_id,
            "contract_info": contract_info,
            "all_clauses_count": len(all_clauses),
            "all_clauses_types": list(all_clauses.keys()),
            "specific_clauses_count": len(specific_clauses),
            "specific_clauses_types": list(specific_clauses.keys()),
            "has_full_text": full_text is not None,
            "full_text_length": len(full_text) if full_text else 0,
            "sample_clause": list(all_clauses.values())[0] if all_clauses else None
        }
        
    except Exception as e:
        logging.error(f"Test clause retrieval error: {str(e)}")
        logging.error(traceback.format_exc())
        return {"success": False, "error": str(e)}
