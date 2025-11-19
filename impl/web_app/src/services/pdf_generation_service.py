"""
PDF Generation Service

Generates professional PDF reports from analysis results using xhtml2pdf.
Supports both comparison and query result types.
"""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

from src.models.analysis_results_models import AnalysisResult

logger = logging.getLogger(__name__)


class PDFGenerationService:
    """Service for generating PDF reports from analysis results"""

    def __init__(self):
        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent.parent.parent / "templates" / "pdf"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
            cache_size=0  # Disable template caching for development
        )
        logger.info(f"Initialized PDF generation service with templates from: {template_dir}")

        # Load CSS for inline styling
        css_path = template_dir / "styles.css"
        self.css_content = ""
        if css_path.exists():
            with open(css_path, 'r', encoding='utf-8') as f:
                self.css_content = f.read()
            logger.info(f"Loaded PDF styles from: {css_path}")

    async def generate_pdf(
        self,
        result: AnalysisResult,
        include_metadata: bool = True
    ) -> bytes:
        """
        Generate PDF from analysis result

        Args:
            result: AnalysisResult object containing comparison or query data
            include_metadata: Whether to include metadata footer

        Returns:
            PDF file as bytes

        Raises:
            ValueError: If result type is invalid or required data is missing
        """
        logger.info(f"Generating PDF for result: {result.result_id} (type: {result.result_type})")

        # Select template based on result type
        # Using "_full" templates with all content expanded (no accordions)
        if result.result_type == "comparison":
            if not result.comparison_data:
                raise ValueError("Comparison data is required for comparison PDF")
            template_name = "comparison_report_full.html"
            context = self._build_comparison_context(result)
        elif result.result_type == "query":
            if not result.query_data:
                raise ValueError("Query data is required for query PDF")
            template_name = "query_report_full.html"
            context = self._build_query_context(result)
        else:
            raise ValueError(f"Unknown result type: {result.result_type}")

        # Add common metadata and CSS
        context["include_metadata"] = include_metadata
        context["generated_at"] = datetime.utcnow()
        context["css_content"] = self.css_content

        # Render HTML from template
        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**context)

        logger.info(f"Rendered template: {template_name} ({len(html_content)} chars)")

        # Convert HTML to PDF using xhtml2pdf
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(
            html_content.encode('utf-8'),
            dest=pdf_buffer,
            encoding='utf-8'
        )

        if pisa_status.err:
            logger.error(f"PDF generation had {pisa_status.err} errors")
            raise ValueError(f"PDF generation failed with {pisa_status.err} errors")

        pdf_bytes = pdf_buffer.getvalue()
        logger.info(f"Generated PDF: {len(pdf_bytes)} bytes")

        return pdf_bytes

    def _build_comparison_context(self, result: AnalysisResult) -> dict:
        """Build template context for comparison reports"""
        data = result.comparison_data

        # Check if results is a Pydantic model or dict
        if hasattr(data.results, 'model_dump'):
            results_dict = data.results.model_dump()
        elif isinstance(data.results, dict):
            results_dict = data.results
        else:
            results_dict = data.results

        # Extract the actual comparison results from nested structure
        # The API response structure is: results -> results -> comparisons
        if isinstance(results_dict, dict) and 'results' in results_dict:
            actual_results = results_dict['results']
            logger.debug(f"Extracted nested results for comparison")
        else:
            actual_results = results_dict
            logger.debug(f"Using top-level results for comparison")

        context = {
            "result_id": result.result_id,
            "created_at": result.created_at,
            "title": result.metadata.title if result.metadata else "Comparison Report",
            "description": result.metadata.description if result.metadata else "",
            "standard_contract_id": data.standard_contract_id,
            "compare_contract_ids": data.compare_contract_ids,
            "comparison_mode": data.comparison_mode,
            "selected_clauses": data.selected_clauses or [],
            "results": actual_results,
            "execution_time": result.metadata.execution_time_seconds if result.metadata else None
        }

        # Log comparison count
        if isinstance(actual_results, dict) and 'comparisons' in actual_results:
            logger.info(f"Building PDF with {len(actual_results['comparisons'])} comparisons")
        else:
            logger.warning(f"No comparisons found in results structure")

        return context

    def _build_query_context(self, result: AnalysisResult) -> dict:
        """Build template context for query reports"""
        data = result.query_data

        # Extract contracts analyzed information
        contracts_analyzed = []
        for contract in data.contracts_queried:
            contracts_analyzed.append({
                "contract_id": contract.contract_id,
                "filename": contract.filename,
                "title": contract.contract_title or "N/A"
            })

        # Extract ranked results
        ranked_results = []
        if "ranked_contracts" in data.results:
            ranked_results = data.results["ranked_contracts"]

        context = {
            "result_id": result.result_id,
            "created_at": result.created_at,
            "title": result.metadata.title if result.metadata else "Query Report",
            "description": result.metadata.description if result.metadata else "",
            "query_text": data.query_text,
            "query_type": data.query_type,
            "contracts_analyzed": contracts_analyzed,
            "answer_summary": data.results.get("answer_summary", "No summary available"),
            "ranked_results": ranked_results,
            "execution_metadata": data.results.get("execution_metadata", {}),
            "execution_time": result.metadata.execution_time_seconds if result.metadata else None
        }

        return context

    async def save_pdf_metadata(
        self,
        result: AnalysisResult,
        pdf_size_bytes: int
    ):
        """
        Update result with PDF generation metadata

        Args:
            result: AnalysisResult to update
            pdf_size_bytes: Size of generated PDF

        Returns:
            Updated AnalysisResult
        """
        from src.models.analysis_results_models import PDFMetadata

        result.pdf_metadata = PDFMetadata(
            generated_at=datetime.utcnow(),
            file_size_bytes=pdf_size_bytes
        )

        logger.info(f"Updated PDF metadata for {result.result_id}: {pdf_size_bytes} bytes")
        return result
