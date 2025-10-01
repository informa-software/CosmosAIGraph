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

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Response, Form, status
from fastapi.responses import JSONResponse
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

# Services with Business Logic
from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.services.entities_service import EntitiesService
from src.services.contract_entities_service import ContractEntitiesService
from src.services.contract_strategy_builder import ContractStrategyBuilder
from src.services.logging_level_service import LoggingLevelService
from src.services.ontology_service import OntologyService
from src.services.rag_data_service import RAGDataService
from src.services.strategy_builder import StrategyBuilder
from src.services.rag_data_result import RAGDataResult
from src.util.fs import FS
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
rag_data_svc = RAGDataService(ai_svc, nosql_svc)


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
        
        # Initialize entities based on graph mode
        graph_mode = ConfigService.envvar("CAIG_GRAPH_MODE", "libraries").lower()
        if graph_mode == "contracts":
            await ContractEntitiesService.initialize()
            entity_stats = ContractEntitiesService.get_statistics()
            logging.error(
                "FastAPI lifespan - ContractEntitiesService initialized, stats: {}".format(
                    json.dumps(entity_stats)
                )
            )
        else:
            await EntitiesService.initialize()
            logging.error(
                "FastAPI lifespan - EntitiesService initialized, libraries_count: {}".format(
                    EntitiesService.libraries_count()
                )
            )
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
    "http://localhost:4200",  # Angular dev server
    "http://localhost:4201",  # Alternative port
    "http://127.0.0.1:4200",
    "http://127.0.0.1:4201",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        completion: Optional[AiCompletion] = AiCompletion(conv.conversation_id, None)
        completion.set_user_text(user_text)
        completion.set_rag_strategy(rdr.get_strategy())
        content_lines = list()

        # Prepare context based on RAG strategy
        context = ""
        completion_context = conv.last_completion_content()
        
        if rdr.has_db_rag_docs() == True:
            for doc in rdr.get_rag_docs():
                logging.debug("doc: {}".format(doc))
                line_parts = list()
                # TO DO - Should we include the filename in the contract_chunk in addition to the IQ ID?
                for attr in ["id", "fileName", "text", "chunk_text"]:
                    if attr in doc.keys():
                        value = doc[attr].strip()
                        if len(value) > 0:
                            line_parts.append("{}: {}".format(attr, value))
                content_lines.append(".  ".join(line_parts))
            
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
        # Check if contracts mode is enabled
        graph_mode = ConfigService.envvar("CAIG_GRAPH_MODE", "libraries").lower()
        if graph_mode != "contracts":
            return JSONResponse(
                status_code=400,
                content={"error": "Contract entities are only available in contracts mode"}
            )
        
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
        # Check if contracts mode is enabled
        graph_mode = ConfigService.envvar("CAIG_GRAPH_MODE", "libraries").lower()
        if graph_mode != "contracts":
            return JSONResponse(
                status_code=400,
                content={"error": "Contract entities are only available in contracts mode"}
            )
        
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
        # Check if we're in contracts mode
        graph_mode = ConfigService.envvar("CAIG_GRAPH_MODE", "contracts").lower()
        if graph_mode != "contracts":
            return JSONResponse(
                content={"error": "System not in contracts mode"},
                status_code=400
            )
        
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
        
        # Check if we're in contracts mode
        graph_mode = ConfigService.envvar("CAIG_GRAPH_MODE", "libraries").lower()
        if graph_mode != "contracts":
            return JSONResponse(
                content={"error": "System not in contracts mode"},
                status_code=400
            )
        
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
        clause_data = standard_data.get('clauses', {}).get(clause_type)
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
    
    # For each comparison contract, only show requested clauses
    for contract_id, data in comparison_data.items():
        prompt += f"\nCONTRACT ID: {contract_id}\nRequested Clauses:\n"
        for clause_type in selected_clauses:
            clause_data = data.get('clauses', {}).get(clause_type)
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
    
    Expected request body:
    {
        "standardContractId": "contract_xxx",
        "compareContractIds": ["contract_yyy", "contract_zzz"],
        "comparisonMode": "clauses" | "full",
        "selectedClauses": ["ClauseType1", "ClauseType2"] | "all"
    }
    """
    try:
        body = await request.json()
        
        # Extract parameters
        standard_contract_id = body.get("standardContractId")
        compare_contract_ids = body.get("compareContractIds", [])
        comparison_mode = body.get("comparisonMode", "clauses")
        selected_clauses = body.get("selectedClauses", "all")
        
        if not standard_contract_id:
            return JSONResponse(
                content={"success": False, "error": "Standard contract ID is required"},
                status_code=400
            )
        
        if not compare_contract_ids:
            return JSONResponse(
                content={"success": False, "error": "At least one comparison contract ID is required"},
                status_code=400
            )
        
        # Initialize services
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        # Use the global ai_svc instance that was initialized at startup
        
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
        
        # Use the special contract comparison method with higher token limit
        llm_response = ai_svc.get_completion_for_contracts(
            user_prompt=llm_prompt,
            system_prompt=system_prompt,
            max_tokens=4000  # Reasonable limit for contract comparisons
        )
        
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
        
        await nosql_svc.close()
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logging.error(f"Contract comparison error: {str(e)}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
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
