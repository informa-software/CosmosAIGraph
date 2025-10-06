"""
Strategy Schema Builder

Builds unified context for LLM query planning by loading:
1. Database schema from JSON file
2. Ontology from OWL file
3. Strategy descriptions and rules

This provides the LLM with complete context to generate optimal queries.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class StrategySchemaBuilder:
    """
    Builds schema context for LLM query planning.

    Loads database schema and ontology from external files to provide
    complete context for LLM to generate accurate SQL and SPARQL queries.
    """

    def __init__(self, schema_file: Optional[str] = None, ontology_file: Optional[str] = None):
        """
        Initialize schema builder with file paths.

        Args:
            schema_file: Path to cosmos_contracts_schema.json (defaults to standard location)
            ontology_file: Path to contracts.owl (defaults to standard location)
        """
        # Default paths relative to web_app directory
        web_app_dir = Path(__file__).parent.parent.parent

        self.schema_file = schema_file or str(web_app_dir / "schemas" / "cosmos_contracts_schema.json")
        self.ontology_file = ontology_file or str(web_app_dir / "ontologies" / "contracts.owl")

        self.schema_data: Optional[Dict] = None
        self.ontology_summary: Optional[Dict] = None

    def load_schema(self) -> Dict:
        """
        Load database schema from JSON file.

        Returns:
            Dict containing schema data with collections, fields, and metadata

        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema file is invalid JSON
        """
        if self.schema_data:
            return self.schema_data

        logger.info(f"Loading database schema from: {self.schema_file}")

        if not os.path.exists(self.schema_file):
            raise FileNotFoundError(f"Schema file not found: {self.schema_file}")

        with open(self.schema_file, 'r', encoding='utf-8') as f:
            self.schema_data = json.load(f)

        logger.info(f"Loaded schema version {self.schema_data.get('schema_version')}, "
                   f"{len(self.schema_data.get('collections', {}))} collections")

        return self.schema_data

    def load_ontology(self) -> Dict:
        """
        Load and parse OWL ontology file.

        Extracts key classes, object properties, and datatype properties
        for SPARQL query generation.

        Returns:
            Dict containing ontology summary with classes and properties

        Raises:
            FileNotFoundError: If ontology file doesn't exist
        """
        if self.ontology_summary:
            return self.ontology_summary

        logger.info(f"Loading ontology from: {self.ontology_file}")

        if not os.path.exists(self.ontology_file):
            raise FileNotFoundError(f"Ontology file not found: {self.ontology_file}")

        # Parse OWL/XML
        tree = ET.parse(self.ontology_file)
        root = tree.getroot()

        # Define namespaces
        ns = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'owl': 'http://www.w3.org/2002/07/owl#'
        }

        # Extract classes
        classes = []
        for cls in root.findall('.//owl:Class', ns):
            class_id = cls.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
            label = cls.find('.//rdfs:label', ns)
            comment = cls.find('.//rdfs:comment', ns)

            if class_id:
                classes.append({
                    'id': class_id,
                    'label': label.text if label is not None else class_id,
                    'description': comment.text if comment is not None else ''
                })

        # Extract object properties (relationships)
        object_properties = []
        for prop in root.findall('.//owl:ObjectProperty', ns):
            prop_id = prop.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
            label = prop.find('.//rdfs:label', ns)
            comment = prop.find('.//rdfs:comment', ns)
            domain = prop.find('.//rdfs:domain', ns)
            range_elem = prop.find('.//rdfs:range', ns)

            if prop_id:
                object_properties.append({
                    'id': prop_id,
                    'label': label.text if label is not None else prop_id,
                    'description': comment.text if comment is not None else '',
                    'domain': domain.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '').split('#')[-1] if domain is not None else '',
                    'range': range_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '').split('#')[-1] if range_elem is not None else ''
                })

        # Extract datatype properties
        datatype_properties = []
        for prop in root.findall('.//owl:DatatypeProperty', ns):
            prop_id = prop.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
            label = prop.find('.//rdfs:label', ns)
            comment = prop.find('.//rdfs:comment', ns)
            domain = prop.find('.//rdfs:domain', ns)

            if prop_id:
                datatype_properties.append({
                    'id': prop_id,
                    'label': label.text if label is not None else prop_id,
                    'description': comment.text if comment is not None else '',
                    'domain': domain.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '').split('#')[-1] if domain is not None else ''
                })

        self.ontology_summary = {
            'namespace': 'http://cosmosdb.com/caig#',
            'prefix': 'caig',
            'classes': classes,
            'object_properties': object_properties,
            'datatype_properties': datatype_properties
        }

        logger.info(f"Loaded ontology: {len(classes)} classes, "
                   f"{len(object_properties)} object properties, "
                   f"{len(datatype_properties)} datatype properties")

        return self.ontology_summary

    def build_llm_context(self) -> Dict:
        """
        Build complete context for LLM query planning.

        Combines database schema and ontology into a unified context
        that the LLM uses to determine strategy and generate queries.

        Returns:
            Dict containing complete context for LLM prompt
        """
        schema = self.load_schema()
        ontology = self.load_ontology()

        context = {
            'database_schema': {
                'database': schema.get('database', 'CosmosDB NoSQL'),
                'schema_version': schema.get('schema_version'),
                'collections': schema.get('collections', {}),
                'normalization_rules': schema.get('normalization_rules', {}),
                'query_strategies': schema.get('query_strategies', {})
            },
            'ontology': {
                'namespace': ontology.get('namespace'),
                'prefix': ontology.get('prefix'),
                'classes': ontology.get('classes', []),
                'object_properties': ontology.get('object_properties', []),
                'datatype_properties': ontology.get('datatype_properties', [])
            }
        }

        logger.info("Built complete LLM context with schema + ontology")

        return context

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dict with collection details or None if not found
        """
        if not self.schema_data:
            self.load_schema()

        return self.schema_data.get('collections', {}).get(collection_name)

    def get_strategy_info(self, strategy_name: str) -> Optional[Dict]:
        """
        Get information about a specific query strategy.

        Args:
            strategy_name: Name of the strategy (e.g., 'ENTITY_FIRST')

        Returns:
            Dict with strategy details or None if not found
        """
        if not self.schema_data:
            self.load_schema()

        return self.schema_data.get('query_strategies', {}).get(strategy_name)

    def validate_schema_version(self, required_version: str) -> bool:
        """
        Validate that schema version meets requirements.

        Args:
            required_version: Minimum required schema version

        Returns:
            True if schema version is compatible
        """
        if not self.schema_data:
            self.load_schema()

        current_version = self.schema_data.get('schema_version', '0.0')

        # Simple version comparison (assumes semantic versioning)
        current_parts = [int(x) for x in current_version.split('.')]
        required_parts = [int(x) for x in required_version.split('.')]

        return current_parts >= required_parts
