import asyncio
import json
import logging
import time
import os

import tiktoken

from openai import AzureOpenAI

import semantic_kernel as sk

from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureTextEmbedding,
    OpenAITextPromptExecutionSettings,
)
from semantic_kernel.functions.kernel_arguments import (
    KernelArguments,
)
from semantic_kernel.prompt_template import (
    PromptTemplateConfig,
    InputVariable,
)

from src.models.internal_models import SparqlGenerationResult
from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.llm_usage_tracker import LLMUsageTracker
from src.services.ontology_service import OntologyService
from src.util.owl_formatter import OwlFormatter
from src.util.prompts import Prompts
from src.util.prompt_optimizer import PromptOptimizer

# Instances of this class are used to execute AzureOpenAI and
# semantic_kernel functionality.
# See docs at https://devblogs.microsoft.com/semantic-kernel/now-in-beta-explore-the-enhanced-python-sdk-for-semantic-kernel/
# Chris Joakim & Aleksey Savateyev, Microsoft, 2025


class AiService:
    """Constructor method; call initialize() immediately after this."""

    def __init__(self, opts={}):
        """
        Get the necessary environment variables and initialze an AzureOpenAI client.
        Also read the OWL file.
        """
        try:
            self.opts = opts
            self.aoai_endpoint = ConfigService.azure_openai_url()
            self.aoai_api_key = ConfigService.azure_openai_key()
            self.aoai_version = ConfigService.azure_openai_version()
            self.chat_function = None
            self.max_ntokens = ConfigService.truncate_llm_context_max_ntokens()

            # tiktoken, for token estimation, doesn't work with gpt-4 at this time
            self.tiktoken_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            self.enc = tiktoken.get_encoding("cl100k_base")
            self.nosql_svc = CosmosNoSQLService()

            self.aoai_client = AzureOpenAI(
                azure_endpoint=self.aoai_endpoint,
                api_key=self.aoai_api_key,
                api_version=self.aoai_version,
            )
            self.completions_deployment = (
                # deployment name/model = gpt4/gpt-4
                ConfigService.azure_openai_completions_deployment()
            )
            self.embeddings_deployment = (
                # deployment name/model = embeddings/text-embedding-ada-002
                ConfigService.azure_openai_embeddings_deployment()
            )

            # Initialize secondary model client if configured
            self.aoai_client_secondary = None
            self.completions_deployment_secondary = None
            secondary_url = ConfigService.azure_openai_url_secondary()
            secondary_key = ConfigService.azure_openai_key_secondary()
            secondary_deployment = ConfigService.azure_openai_completions_deployment_secondary()

            if secondary_url and secondary_key and secondary_deployment:
                logging.info(f"Initializing secondary model: {secondary_deployment}")
                self.aoai_client_secondary = AzureOpenAI(
                    azure_endpoint=secondary_url,
                    api_key=secondary_key,
                    api_version=ConfigService.azure_openai_version_secondary(),
                )
                self.completions_deployment_secondary = secondary_deployment
                logging.info("Secondary model client initialized successfully")
            else:
                logging.info("Secondary model not configured (optional for model comparison)")
            self.sk_kernel = sk.Kernel()
            self.sk_kernel.add_service(
                AzureChatCompletion(
                    service_id="chat_completion",
                    deployment_name=self.completions_deployment,
                    endpoint=self.aoai_endpoint,
                    api_key=self.aoai_api_key,
                )
            )
            self.sk_kernel.add_service(
                AzureTextEmbedding(
                    service_id="text_embedding",
                    deployment_name=self.embeddings_deployment,
                    endpoint=self.aoai_endpoint,
                    api_key=self.aoai_api_key,
                )
            )

            # Initialize LLM tracker to None (will be set in initialize())
            self.llm_tracker = None

            logging.info("aoai endpoint:     {}".format(self.aoai_endpoint))
            logging.info("aoai version:      {}".format(self.aoai_version))
            logging.info("aoai client:  {}".format(self.aoai_client))
            logging.info(
                "aoai completions_deployment: {}".format(self.completions_deployment)
            )
            logging.info(
                "aoai embeddings_deployment:  {}".format(self.embeddings_deployment)
            )
            logging.info("sk_kernel: {}".format(self.sk_kernel))
        except Exception as e:
            logging.critical("Exception in AiService#__init__: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    async def initialize(self):
        """This method should be called immediately after the constructor."""
        logging.info("AiService#initialize()")
        await self.nosql_svc.initialize()
        # Initialize LLM usage tracker
        self.llm_tracker = LLMUsageTracker(self.nosql_svc)

    def num_tokens_from_string(self, s: str) -> int:
        try:
            return len(self.tiktoken_encoding.encode(s))
        except Exception as e:
            logging.critical(
                "Exception in AiService#num_tokens_from_string: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return 10000

    def generate_sparql_from_user_prompt(
        self, resp_obj: dict
    ) -> SparqlGenerationResult:
        try:
            user_prompt = resp_obj["natural_language"]
            raw_owl = resp_obj["owl"]

            # Include normalized entities for accurate SPARQL generation
            if "normalized_entities" in resp_obj:
                user_prompt += f"\n\nNormalized Entities (use these exact values in SPARQL):\n{resp_obj['normalized_entities']}"

            # Include negations if present
            if "negations" in resp_obj:
                user_prompt += f"\n\nExclude These:\n{resp_obj['negations']}"

            #owl = OwlFormatter().minimize(raw_owl)
            logging.info(
                "AiService#generate_sparql_from_user_prompt - user_prompt: {}".format(
                    user_prompt
                )
            )
            if self.validate_sparql_gen_input(user_prompt, raw_owl):
                t1 = time.perf_counter()
                system_prompt = Prompts().generate_sparql_system_prompt(raw_owl)
                logging.info(
                    "AiService#generate_sparql_from_user_prompt - system_prompt: {}".format(
                        system_prompt
                    )
                )
                completion = self.aoai_client.chat.completions.create(
                    model=self.completions_deployment,
                    temperature=ConfigService.moderate_sparql_temperature(),
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                t2 = time.perf_counter()

                # Track LLM usage
                if self.llm_tracker:
                    asyncio.create_task(
                        self.llm_tracker.track_completion(
                            user_email="system",  # TODO: Get actual user email from request context
                            operation="sparql_generation",
                            model=completion.model,
                            prompt_tokens=completion.usage.prompt_tokens,
                            completion_tokens=completion.usage.completion_tokens,
                            elapsed_time=t2 - t1,
                            operation_details={
                                "user_query": user_prompt[:100],  # First 100 chars for context
                                "owl_provided": len(raw_owl) > 0
                            },
                            success=True
                        )
                    )

                logging.info(
                    "AiService#generate_sparql_from_user_prompt - Completion: {}".format(
                        completion.choices[0].message.content
                    )
                )
                # completion is an instance of <class 'openai.types.chat.chat_completion.ChatCompletion'>
                # https://platform.openai.com/docs/api-reference/chat/object
                sparql = json.loads(completion.choices[0].message.content).get("sparql")
                if sparql is None:
                    sparql = json.loads(completion.choices[0].message.content).get("query")
                if sparql is None:
                    sparql = json.loads(completion.choices[0].message.content).get("SPARQL")
                resp_obj["completion_id"] = completion.id
                resp_obj["completion_model"] = completion.model
                resp_obj["prompt_tokens"] = completion.usage.prompt_tokens
                resp_obj["completion_tokens"] = completion.usage.completion_tokens
                resp_obj["total_tokens"] = completion.usage.total_tokens
                resp_obj["elapsed"] = t2 - t1
                resp_obj["sparql"] = sparql
                if resp_obj["sparql"] == None:
                    resp_obj["sparql"] = ""
                logging.info(
                    "AiService#generate_sparql_from_user_prompt - sparql: {}".format(
                        sparql
                    )
                )
            else:
                resp_obj["error"] = "content moderation failed"
        except Exception as e:
            resp_obj["error"] = str(e)

            # Track failed LLM call if completion object exists
            if self.llm_tracker and 'completion' in locals():
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",
                        operation="sparql_generation",
                        model=completion.model,
                        prompt_tokens=completion.usage.prompt_tokens if hasattr(completion, 'usage') else 0,
                        completion_tokens=completion.usage.completion_tokens if hasattr(completion, 'usage') else 0,
                        elapsed_time=t2 - t1 if 't2' in locals() and 't1' in locals() else 0,
                        operation_details={"user_query": user_prompt[:100] if 'user_prompt' in locals() else ""},
                        success=False,
                        error_message=str(e)
                    )
                )

            logging.critical(
                "Exception in AiService#generate_sparql_from_user_prompt: {}".format(
                    str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return resp_obj

    def validate_sparql_gen_input(self, user_prompt, owl):
        """Return True if the input should be processed, else return False."""
        try:
            if user_prompt == None:
                return False
            if owl == None:
                return False
            if len(user_prompt.strip()) < 2:
                return False
            if len(owl.strip()) < 2:
                return False
            # Note: optionally implement content moderation for profanity, etc
            return True
        except Exception as e:
            return False

    def generate_embeddings(self, text):
        """
        Generate an embeddings array from the given text.
        Return an CreateEmbeddingResponse object or None.
        Invoke 'resp.data[0].embedding' to get the array of 1536 floats.
        """
        try:
            t1 = time.perf_counter()
            # <class 'openai.types.create_embedding_response.CreateEmbeddingResponse'>
            response = self.aoai_client.embeddings.create(
                input=text, model=self.embeddings_deployment
            )
            t2 = time.perf_counter()

            # Track embedding usage
            if self.llm_tracker:
                asyncio.create_task(
                    self.llm_tracker.track_embedding(
                        user_email="system",  # TODO: Get actual user email from request context
                        operation="rag_embedding",
                        model=response.model,
                        tokens=response.usage.total_tokens,
                        elapsed_time=t2 - t1,
                        operation_details={
                            "text_length": len(text),
                            "text_preview": text[:50]  # First 50 chars
                        },
                        success=True
                    )
                )

            return response
        except Exception as e:
            # Track failed embedding call
            if self.llm_tracker:
                asyncio.create_task(
                    self.llm_tracker.track_embedding(
                        user_email="system",
                        operation="rag_embedding",
                        model=self.embeddings_deployment,
                        tokens=0,
                        elapsed_time=0,
                        operation_details={"text_length": len(text) if 'text' in locals() else 0},
                        success=False,
                        error_message=str(e)
                    )
                )

            logging.critical(
                "Exception in AiService#generate_embeddings: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def text_to_chunks(self, text):
        max_chunk_size = 2048
        chunks = []
        current_chunk = ""
        for sentence in text.split("."):
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence + "."
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    async def invoke_kernel(
        self,
        conversation: AiConversation,
        prompt_template: str,
        user_query: str,
        context: str,
        max_tokens: int = ConfigService.invoke_kernel_max_tokens(),
        temperature: float = ConfigService.invoke_kernel_temperature(),
        top_p: float = ConfigService.invoke_kernel_top_p(),
    ) -> AiCompletion | None:

        try:
            logging.info(
                "AiService#invoke_kernel, user_query: {} {}".format(
                    user_query, len(user_query)
                )
            )
            result_obj = self.optimize_context_and_history(
                prompt_template,
                context,
                conversation.get_chat_history().serialize(),
                user_query,
                max_tokens,
            )

            # The result_obj is created by a PromptOptimizer, and is a
            # dictionary with several keys.  Some of these are for unit-testing
            # and diagnostic purposes.  The following four are the most pertinent.
            # See class PromptOptimizer for details.
            pruned_context = result_obj["pruned_context"]
            pruned_history = result_obj["pruned_history"]
            actual_prompt = result_obj["actual_prompt"]
            actual_tokens = result_obj["pruned_tokens"]

            # prev history -> conversation.get_chat_history().serialize()
            # The caller (web layer) is responsible for adding the user message
            # to avoid duplicate entries for the same turn.
            conversation.add_system_message(pruned_context)
            conversation.add_prompt(actual_prompt)
            conversation.add_diagnostic_message(
                "expected tokens: {} vs max_tokens: {}".format(
                    actual_tokens, max_tokens
                )
            )

            execution_settings = OpenAITextPromptExecutionSettings(
                service_id="chat_completion",
                ai_model_id=self.completions_deployment,
                max_tokens=abs(max_tokens),
                temperature=abs(temperature),
                top_p=abs(top_p),
            )

            # The InputVariables here must to be defined in the prompt_template
            chat_prompt_template_config = PromptTemplateConfig(
                template=prompt_template,
                name="chat",
                template_format="semantic-kernel",
                input_variables=[
                    InputVariable(
                        name="history",
                        description="The conversation ChatHistory",
                        is_required=True,
                    ),
                    InputVariable(
                        name="user_query",
                        description="The user input",
                        is_required=True,
                    ),
                    InputVariable(
                        name="context",
                        description="RAG data to augment the LLM",
                        is_required=True,
                    ),
                ],
                execution_settings=execution_settings,
            )

            if self.chat_function is None:
                self.chat_function = self.sk_kernel.add_function(
                    function_name="chat",
                    plugin_name="chatPlugin",
                    prompt_template_config=chat_prompt_template_config,
                )

            kernel_args = KernelArguments(
                user_query=user_query,
                context=pruned_context,
                history=pruned_history,
            )

            invoke_result = await self.sk_kernel.invoke(self.chat_function, kernel_args)

            conversation.add_assistant_message(str(invoke_result))
            # Create completion but don't persist or append here; let the caller handle it
            return AiCompletion(conversation.get_conversation_id(), invoke_result)
        except Exception as e:
            conversation.add_assistant_message("exception: {}".format(str(e)))
            logging.critical("Exception in AiService#invoke_kernel: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def generic_prompt_template(self) -> str:
        ptxt = """You can respond to any user queries. If there's anything in the context below, use it in favor of any general knowledge.
Context:
{{$context}}

Chat history:
{{$history}}

User: {{$user_query}}
ChatBot: """
        return ptxt

    def get_completion(self, user_prompt, system_prompt):
        # await asyncio.wait(0.1)
        completion = self.aoai_client.chat.completions.create(
            model=self.completions_deployment,
            temperature=ConfigService.get_completion_temperature(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": "Return the response as JSON only. (json)"},
                {"role": "user", "content": user_prompt},
            ],
        )
        result = completion.choices[0].message.content
        return result
    
    def get_completion_for_contracts(self, user_prompt, system_prompt, max_tokens=4000, model_selection="primary"):
        """
        Special version of get_completion for contract comparisons with configurable max_tokens.

        Args:
            user_prompt: The user's prompt text
            system_prompt: The system prompt text
            max_tokens: Maximum tokens in response (default: 4000)
            model_selection: "primary" for main model or "secondary" for cost-effective model (default: "primary")

        Returns:
            The completion response text
        """
        try:
            t1 = time.perf_counter()

            # Select the appropriate client and deployment based on model_selection
            if model_selection == "secondary" and self.aoai_client_secondary:
                client = self.aoai_client_secondary
                deployment = self.completions_deployment_secondary
                logging.info(f"Using secondary model for contract comparison: {deployment}")
            else:
                client = self.aoai_client
                deployment = self.completions_deployment
                logging.info(f"Using primary model for contract comparison: {deployment}")

            completion = client.chat.completions.create(
                model=deployment,
                temperature=ConfigService.get_completion_temperature(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": "Return the response as JSON only. (json)"},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens
            )
            t2 = time.perf_counter()

            # Track contract comparison usage
            if self.llm_tracker:
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",  # TODO: Get actual user email from request context
                        operation="contract_comparison",
                        model=completion.model,
                        prompt_tokens=completion.usage.prompt_tokens,
                        completion_tokens=completion.usage.completion_tokens,
                        elapsed_time=t2 - t1,
                        operation_details={
                            "model_selection": model_selection,
                            "max_tokens": max_tokens,
                            "user_prompt_length": len(user_prompt)
                        },
                        success=True
                    )
                )

            result = completion.choices[0].message.content
            return result

        except Exception as e:
            # Track failed contract comparison call
            if self.llm_tracker:
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",
                        operation="contract_comparison",
                        model=deployment if 'deployment' in locals() else self.completions_deployment,
                        prompt_tokens=0,
                        completion_tokens=0,
                        elapsed_time=0,
                        operation_details={"model_selection": model_selection, "max_tokens": max_tokens},
                        success=False,
                        error_message=str(e)
                    )
                )
            logging.critical(f"Exception in AiService#get_completion_for_contracts: {str(e)}")
            logging.exception(e, stack_info=True, exc_info=True)
            raise

    def optimize_context_and_history(
        self,
        prompt_template: str,
        full_context: str,
        full_history,
        user_query: str,
        max_tokens: int = ConfigService.optimize_context_and_history_max_tokens(),
    ):
        try:
            optimizer = PromptOptimizer()
            return optimizer.generate_and_truncate(
                prompt_template, full_context, full_history, user_query, max_tokens
            )
        except Exception as e:
            logging.critical(
                "Exception in AiService#optimize_context_and_history: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    async def evaluate_compliance_rules_batch(
        self,
        contract_text: str,
        rules: list
    ) -> dict:
        """
        Evaluate multiple compliance rules against contract text in a single LLM call.

        Args:
            contract_text: Full contract text to evaluate
            rules: List of rule dicts with 'id', 'name', 'description', 'severity', 'category'

        Returns:
            Dict with 'evaluations' key containing list of evaluation results

        Each evaluation result contains:
            - rule_id: The rule ID
            - result: 'pass', 'fail', 'partial', or 'not_applicable'
            - confidence: 0.0-1.0
            - explanation: Reasoning for the decision
            - evidence: List of contract excerpts supporting the finding
        """
        try:
            import time
            t1 = time.perf_counter()

            # Build system prompt
            system_prompt = """You are a legal compliance analyst. Evaluate the following contract text against multiple compliance rules simultaneously.

For each rule, provide a structured evaluation with:
1. Result: pass, fail, partial, or not_applicable
2. Confidence: 0.0-1.0 (how confident you are in this assessment)
3. Explanation: Clear reasoning for your decision (2-3 sentences)
4. Evidence: Specific contract excerpts that support your finding (limit to 2-3 most relevant excerpts per rule)

Definitions:
- pass: Contract fully complies with the rule
- fail: Contract clearly violates or does not meet the rule
- partial: Contract partially complies but has gaps or ambiguities
- not_applicable: Rule does not apply to this type of contract

Return results as a JSON object with an "evaluations" array containing one entry per rule.
Each entry must have: rule_id, result, confidence, explanation, evidence (array of strings)."""

            # Build user prompt with contract and rules
            user_prompt = f"""Contract Text:
{contract_text}

Compliance Rules to Evaluate:

"""
            for idx, rule in enumerate(rules, 1):
                user_prompt += f"""{idx}. Rule ID: {rule['id']}
   Rule: {rule['name']}
   Severity: {rule['severity']}
   Category: {rule['category']}
   Description: {rule['description']}

"""

            user_prompt += "\nEvaluate all rules and return JSON with evaluations array."

            logging.info(
                f"AiService#evaluate_compliance_rules_batch - evaluating {len(rules)} rules"
            )

            # Call Azure OpenAI
            completion = self.aoai_client.chat.completions.create(
                model=self.completions_deployment,
                temperature=ConfigService.moderate_sparql_temperature(),
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            t2 = time.perf_counter()
            elapsed = (t2 - t1) * 1000

            # Track compliance evaluation usage
            logging.info(f"[LLM_TRACK] About to track compliance_evaluation. llm_tracker exists: {self.llm_tracker is not None}")
            if self.llm_tracker:
                logging.info(f"[LLM_TRACK] Creating task to track: model={completion.model}, prompt_tokens={completion.usage.prompt_tokens}, completion_tokens={completion.usage.completion_tokens}")
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",  # TODO: Get actual user email from request context
                        operation="compliance_evaluation",
                        model=completion.model,
                        prompt_tokens=completion.usage.prompt_tokens,
                        completion_tokens=completion.usage.completion_tokens,
                        elapsed_time=t2 - t1,
                        operation_details={
                            "rule_count": len(rules),
                            "contract_length": len(contract_text),
                            "batch_evaluation": True
                        },
                        success=True
                    )
                )
                logging.info("[LLM_TRACK] Task created successfully")
            else:
                logging.warning("[LLM_TRACK] llm_tracker is None, skipping tracking")

            logging.info(
                f"AiService#evaluate_compliance_rules_batch - completed in {elapsed:.0f}ms"
            )

            # Parse response
            response_text = completion.choices[0].message.content
            result = json.loads(response_text)

            # Validate result structure
            if "evaluations" not in result:
                logging.error("LLM response missing 'evaluations' key")
                result = {"evaluations": []}

            return result

        except Exception as e:
            # Track failed compliance evaluation
            if self.llm_tracker:
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",
                        operation="compliance_evaluation",
                        model=self.completions_deployment,
                        prompt_tokens=0,
                        completion_tokens=0,
                        elapsed_time=0,
                        operation_details={
                            "rule_count": len(rules) if 'rules' in locals() else 0,
                            "batch_evaluation": True
                        },
                        success=False,
                        error_message=str(e)
                    )
                )

            logging.critical(
                f"Exception in AiService#evaluate_compliance_rules_batch: {str(e)}"
            )
            logging.exception(e, stack_info=True, exc_info=True)
            # Return empty evaluations on error
            return {"evaluations": []}

    async def generate_compliance_recommendation(
        self,
        rule_name: str,
        rule_description: str,
        contract_text: str,
        evidence: list,
        explanation: str
    ) -> dict:
        """
        Generate AI recommendation for fixing a failed/partial compliance rule.

        Args:
            rule_name: Name of the compliance rule
            rule_description: Detailed description of what the rule requires
            contract_text: Full contract text
            evidence: List of contract excerpts that show the failure
            explanation: Explanation of why the rule failed/partially passed

        Returns:
            Dict with recommendation fields:
                - original_text: Text to find and replace
                - proposed_text: Suggested replacement text
                - explanation: Why this change fixes the issue
                - location_context: Surrounding text for exact matching (~50 chars before/after)
                - confidence: AI confidence score (0.0-1.0)
        """
        try:
            import time
            t1 = time.perf_counter()

            # Build system prompt
            system_prompt = """You are a legal contract expert specializing in compliance remediation.
Your task is to provide a specific, actionable recommendation for fixing a compliance issue in a contract.

Your recommendation must include:
1. original_text: The exact problematic text that needs to be changed (copy verbatim from the contract)
2. proposed_text: The specific replacement text that will make the contract compliant
3. explanation: Clear explanation (2-3 sentences) of why this change fixes the compliance issue
4. location_context: Include ~50 characters before and after the original_text to help locate it precisely
5. confidence: Your confidence score (0.0-1.0) in this recommendation

Guidelines:
- Be specific: Provide exact text that can be found in the contract
- Be practical: Suggest realistic, legally sound changes
- Be precise: Include enough context to uniquely identify the location
- Focus on the most impactful single change that addresses the core issue

Return results as a JSON object with these exact keys: original_text, proposed_text, explanation, location_context, confidence."""

            # Build user prompt
            evidence_text = "\n".join([f"- {e}" for e in evidence])

            user_prompt = f"""Contract Text:
{contract_text}

Compliance Rule: {rule_name}
Rule Requirements: {rule_description}

Evaluation Result: {explanation}

Evidence of Non-Compliance:
{evidence_text}

Based on this evaluation, provide ONE specific recommendation to fix the compliance issue. Identify the exact problematic text in the contract and suggest a precise replacement that will make the contract compliant with this rule."""

            logging.info(
                f"AiService#generate_compliance_recommendation - generating recommendation for rule: {rule_name}"
            )

            # Call Azure OpenAI
            completion = self.aoai_client.chat.completions.create(
                model=self.completions_deployment,
                temperature=ConfigService.moderate_sparql_temperature(),
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            t2 = time.perf_counter()
            elapsed = (t2 - t1) * 1000

            # Track compliance recommendation usage
            logging.info(f"[LLM_TRACK] About to track compliance_recommendation. llm_tracker exists: {self.llm_tracker is not None}")
            if self.llm_tracker:
                logging.info(f"[LLM_TRACK] Creating task to track recommendation: model={completion.model}, prompt_tokens={completion.usage.prompt_tokens}, completion_tokens={completion.usage.completion_tokens}")
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",  # TODO: Get actual user email from request context
                        operation="compliance_recommendation",
                        model=completion.model,
                        prompt_tokens=completion.usage.prompt_tokens,
                        completion_tokens=completion.usage.completion_tokens,
                        elapsed_time=t2 - t1,
                        operation_details={
                            "rule_name": rule_name,
                            "contract_length": len(contract_text),
                            "evidence_count": len(evidence)
                        },
                        success=True
                    )
                )
                logging.info("[LLM_TRACK] Recommendation task created successfully")
            else:
                logging.warning("[LLM_TRACK] llm_tracker is None, skipping recommendation tracking")

            logging.info(
                f"AiService#generate_compliance_recommendation - completed in {elapsed:.0f}ms"
            )

            # Parse response
            response_text = completion.choices[0].message.content
            result = json.loads(response_text)

            # Validate required fields
            required_fields = ["original_text", "proposed_text", "explanation", "location_context", "confidence"]
            for field in required_fields:
                if field not in result:
                    logging.error(f"LLM response missing '{field}' key")
                    result[field] = "" if field != "confidence" else 0.5

            # Ensure confidence is a float between 0 and 1
            try:
                confidence = float(result["confidence"])
                result["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                logging.warning(f"Invalid confidence value: {result.get('confidence')}, defaulting to 0.5")
                result["confidence"] = 0.5

            return result

        except Exception as e:
            # Track failed compliance recommendation
            if self.llm_tracker:
                asyncio.create_task(
                    self.llm_tracker.track_completion(
                        user_email="system",
                        operation="compliance_recommendation",
                        model=self.completions_deployment,
                        prompt_tokens=0,
                        completion_tokens=0,
                        elapsed_time=0,
                        operation_details={
                            "rule_name": rule_name if 'rule_name' in locals() else "unknown",
                            "contract_length": len(contract_text) if 'contract_text' in locals() else 0
                        },
                        success=False,
                        error_message=str(e)
                    )
                )

            logging.critical(
                f"Exception in AiService#generate_compliance_recommendation: {str(e)}"
            )
            logging.exception(e, stack_info=True, exc_info=True)
            # Return empty recommendation on error
            return {
                "original_text": "",
                "proposed_text": "",
                "explanation": "Failed to generate recommendation due to an error.",
                "location_context": "",
                "confidence": 0.0
            }
