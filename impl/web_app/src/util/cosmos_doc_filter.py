# Instances of this class are used to reduce a given Cosmos DB
# JSON document to only the pertinent attributes, and truncate
# their values if they're long.
#
# Chris Joakim, Microsoft, 2025


class CosmosDocFilter:

    def __init__(self, cosmos_doc):
        self.cosmos_doc = cosmos_doc

    def filter_library(self, additional_attrs=list()):
        """
        Reduce the given Cosmos DB document to only the pertinent attributes.
        """
        filtered = dict()
        filtered_attrs = self.general_attributes()
        if self.cosmos_doc is not None:
            for attr in self.cosmos_doc.keys():
                if attr in filtered_attrs:
                    filtered[attr] = self.cosmos_doc[attr]
                if additional_attrs is not None:
                    if attr in additional_attrs:
                        filtered[attr] = self.cosmos_doc[attr]
        return filtered
    
    def general_attributes(self):
        return [
            "chunk_text",
            "doctype",
            "filename",
            "contractor_party",
            "contracting_party",
            "effective_date",
            "expiration_date",
            "contract_value",
            "contract_type",
            "governing_law",
            "jurisdiction",
            "embedding"
        ]
    
    def filter_for_rag_data(self):
        """
        Filter document for RAG data, handling both library and contract documents.
        """
        filtered = dict()
        
        if self.cosmos_doc is None:
            return filtered
        
        # Check document type
        doctype = self.cosmos_doc.get("doctype", "")
        
        if "contract" in doctype.lower():
            # Contract document filtering
            filtered_attrs = self.contract_rag_attributes()
        else:
            # Library document filtering (existing)
            filtered_attrs = self.rag_attributes()
        
        for attr in self.cosmos_doc.keys():
            if attr in filtered_attrs:
                # Handle special cases
                if attr == "chunk_text":
                    filtered[attr] = self.cosmos_doc[attr][:1024]
                elif attr == "metadata":
                    # Extract key metadata fields
                    metadata = self.cosmos_doc[attr]
                    if "ContractorPartyName" in metadata:
                        filtered["contractor_party"] = metadata.get("ContractorPartyName", {}).get("normalizedValue", "")
                    if "ContractingPartyName" in metadata:
                        filtered["contracting_party"] = metadata.get("ContractingPartyName", {}).get("normalizedValue", "")
                    if "EffectiveDate" in metadata:
                        filtered["effective_date"] = metadata.get("EffectiveDate", {}).get("value", "")
                    if "MaximumContractValue" in metadata:
                        filtered["contract_value"] = metadata.get("MaximumContractValue", {}).get("value", "")
                elif attr == "dependency_ids":
                    filtered[attr] = list()
                    for dep_id in self.cosmos_doc[attr]:
                        filtered[attr].append(
                            dep_id[5:]
                        )  # 'pypi_jinja2' becomes 'jinja2'
                elif attr == "description":
                    filtered[attr] = self.cosmos_doc[attr][:255].replace("\n", " ")
                elif attr == "summary":
                    filtered[attr] = self.cosmos_doc[attr][:255].replace("\n", " ")
                elif attr == "documentation_summary":
                    filtered[attr] = self.cosmos_doc[attr][:1024].replace("\n", " ")
                else:
                    filtered[attr] = self.cosmos_doc[attr]
        
        return filtered

    def contract_rag_attributes(self):
        """
        Attributes relevant for contract RAG data.
        """
        return [
            "id",
            "doctype",
            "filename",
            "contractor_party",
            "contracting_party",
            "effective_date",
            "expiration_date",
            "contract_value",
            "contract_type",
            "governing_law",
            "jurisdiction",
            "chunk_text",
            "metadata",
            "clause_ids",
            "chunk_ids",
            "clause_type",
            "clause_text"
        ]

    def rag_attributes(self):
         return [
            "chunk_text",
            "doctype",
            "filename",
            "contractor_party",
            "contracting_party",
            "effective_date",
            "expiration_date",
            "contract_value",
            "contract_type",
            "governing_law",
            "jurisdiction",
            "embedding"
        ]

    def filter_out_embedding(self, embedding_attr = "embedding"):
        """
        Remove embedding fromCosmos DB documents and truncate some known ones.
        """
        filtered = dict()
        #filtered_attrs = self.rag_attributes()
        if self.cosmos_doc is not None:
            for attr in self.cosmos_doc.keys():
                if attr != embedding_attr:
                    if attr == "dependency_ids":
                        filtered[attr] = list()
                        for dep_id in self.cosmos_doc[attr]:
                            filtered[attr].append(
                                dep_id[5:]
                            )  # 'pypi_jinja2' becomes 'jinja2'
                    elif attr == "chunk_text":
                        filtered[attr] = self.cosmos_doc[attr][:1024]#.replace("\n", " ")
                    elif attr == "summary":
                        filtered[attr] = self.cosmos_doc[attr][:255]#.replace("\n", " ")
                    elif attr == "documentation_summary":
                        filtered[attr] = self.cosmos_doc[attr][:1024]#.replace("\n", " ")
                    else:
                        filtered[attr] = self.cosmos_doc[attr][:1024] if isinstance(self.cosmos_doc[attr], str) else self.cosmos_doc[attr]

        return filtered


    def filter_for_vector_search(self):
        """
        Reduce the given Cosmos DB document to only the pertinent attributes
        """
        filtered = dict()
        filtered_attrs = self.vector_search_attributes()
        if self.cosmos_doc is not None:
            for attr in self.cosmos_doc.keys():
                if attr in filtered_attrs:
                    filtered[attr] = self.cosmos_doc[attr]
        return filtered

    def vector_search_attributes(self):
        """
        List the pertinant attributes in the CONTRACT_CHUNK documents that should be returned
        """
        # TO DO - Should this be different for contract vs clause?
        # Should this include the filename in addition to the IQ ID and other properties?
        return [
            "chunk_text",
            "doctype",
            "filename",
            "contractor_party",
            "contracting_party",
            "effective_date",
            "expiration_date",
            "contract_value",
            "contract_type",
            "governing_law",
            "jurisdiction",
            "embedding"
        ]
