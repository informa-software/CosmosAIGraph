package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.impl.PropertyImpl;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * This class builds RDF triples from Contract documents stored in CosmosDB.
 * It follows the same pattern as LibrariesGraphTriplesBuilder but for contracts domain.
 * 
 * The AppGraphBuilder creates an instance of this class at application startup
 * and invokes the "ingestDocument(...)" method for each graph source document read
 * from Azure Cosmos DB.
 * 
 * Chris Joakim, Microsoft, 2025
 */
public class ContractsGraphTriplesBuilder {

    // Constants
    public static final String CAIG_NAMESPACE = "http://cosmosdb.com/caig#";
    public static final String TYPE_CONTRACT_URI = "http://cosmosdb.com/caig#Contract";
    public static final String TYPE_CONTRACTOR_PARTY_URI = "http://cosmosdb.com/caig#ContractorParty";
    public static final String TYPE_CONTRACTING_PARTY_URI = "http://cosmosdb.com/caig#ContractingParty";
    public static final String TYPE_GOVERNING_LAW_STATE_URI = "http://cosmosdb.com/caig#GoverningLawState";
    public static final String TYPE_INDEMNIFICATION_URI = "http://cosmosdb.com/caig#Indemnification";
    public static final String TYPE_INDEMNIFICATION_OBLIGATIONS_URI = "http://cosmosdb.com/caig#IndemnificationObligations";
    public static final String TYPE_WORKERS_COMPENSATION_INSURANCE_URI = "http://cosmosdb.com/caig#WorkersCompensationInsurance";
    public static final String TYPE_COMMERCIAL_PUBLIC_LIABILITY_URI = "http://cosmosdb.com/caig#CommercialPublicLiability";
    public static final String TYPE_AUTOMOBILE_INSURANCE_URI = "http://cosmosdb.com/caig#AutomobileInsurance";
    public static final String TYPE_UMBRELLA_INSURANCE_URI = "http://cosmosdb.com/caig#UmbrellaInsurance";
    public static final String TYPE_ASSIGNABILITY_URI = "http://cosmosdb.com/caig#Asignability";
    public static final String TYPE_DATA_BREACH_OBLIGATIONS_URI = "http://cosmosdb.com/caig#DataBreachObligations";
    public static final String TYPE_COMPLIANCE_OBLIGATIONS_URI = "http://cosmosdb.com/caig#ComplianceObligations";
    public static final String TYPE_CONFIDENTIALITY_OBLIGATIONS_URI = "http://cosmosdb.com/caig#ConfidentialityObligations";
    public static final String TYPE_ESCALATION_OBLIGATIONS_URI = "http://cosmosdb.com/caig#EscalationObligations";
    public static final String TYPE_LIMITATION_OF_LIABILITY_OBLIGATIONS_URI = "http://cosmosdb.com/caig#LimitationOfLiabilityObligations";
    public static final String TYPE_PAYMENT_OBLIGATIONS_URI = "http://cosmosdb.com/caig#PaymentObligations";
    public static final String TYPE_RENEWAL_NOTIFICATION_URI = "http://cosmosdb.com/caig#RenewalNotification";
    public static final String TYPE_SERVICE_LEVEL_AGREEMENT_URI = "http://cosmosdb.com/caig#ServiceLevelAgreement";
    public static final String TYPE_TERMINATION_OBLIGATIONS_URI = "http://cosmosdb.com/caig#TerminationObligations";
    public static final String TYPE_WARRANTY_OBLIGATIONS_URI = "http://cosmosdb.com/caig#WarrantyObligations";
    public static final String TYPE_GOVERNING_LAW_URI = "http://cosmosdb.com/caig#GoverningLaw";
    private static final Map<String, String> CLAUSE_TYPE_MAPPING = new HashMap<>();
    static {
        CLAUSE_TYPE_MAPPING.put("indemnification", "Indemnification");
        CLAUSE_TYPE_MAPPING.put("indemnificationobligations", "IndemnificationObligations");
        CLAUSE_TYPE_MAPPING.put("workerscompensationinsurance", "WorkersCompensationInsurance");
        CLAUSE_TYPE_MAPPING.put("commercialpublicliability", "CommercialPublicLiability");
        CLAUSE_TYPE_MAPPING.put("automobileinsurance", "AutomobileInsurance");
        CLAUSE_TYPE_MAPPING.put("umbrellainsurance", "UmbrellaInsurance");
        CLAUSE_TYPE_MAPPING.put("assignability", "Assignability");
        CLAUSE_TYPE_MAPPING.put("databreachobligations", "DataBreachObligations");
        CLAUSE_TYPE_MAPPING.put("complianceobligations", "ComplianceObligations");
        CLAUSE_TYPE_MAPPING.put("confidentialityobligations", "ConfidentialityObligations");
        CLAUSE_TYPE_MAPPING.put("escalationobligations", "EscalationObligations");
        CLAUSE_TYPE_MAPPING.put("limitationofliabilityobligations", "LimitationOfLiabilityObligations");
        CLAUSE_TYPE_MAPPING.put("paymentobligations", "PaymentObligations");
        CLAUSE_TYPE_MAPPING.put("renewalnotification", "RenewalNotification");
        CLAUSE_TYPE_MAPPING.put("servicelevelagreement", "ServiceLevelAgreement");
        CLAUSE_TYPE_MAPPING.put("terminationobligations", "TerminationObligations");
        CLAUSE_TYPE_MAPPING.put("warrantyobligations", "WarrantyObligations");
        CLAUSE_TYPE_MAPPING.put("governinglaw", "GoverningLaw");
    }

    // Class variables
    private static Logger logger = LoggerFactory.getLogger(ContractsGraphTriplesBuilder.class);

    // Instance variables
    private AppGraph graph;
    private Model model;
    private String namespace;
    private long documentsIngested = 0;
    private ObjectMapper objectMapper;

    // Properties from the ontology
    PropertyImpl contractorPartyNameProperty;
    PropertyImpl contractingPartyNameProperty;
    PropertyImpl governingLawStateProperty;
    PropertyImpl effectiveDateProperty;
    PropertyImpl expirationDateProperty;
    PropertyImpl contractTypeProperty;
    PropertyImpl maximumContractValueProperty;
    PropertyImpl filenameProperty;
    PropertyImpl contractClauseIdProperty;
    
    // Object properties
    PropertyImpl performsProperty;
    PropertyImpl isPerformedByProperty;
    PropertyImpl initiatesProperty;
    PropertyImpl isInitiatedByProperty;
    PropertyImpl isGovernedByProperty;
    PropertyImpl governsProperty;
    PropertyImpl containsProperty;
    PropertyImpl isContainedInProperty;

    public ContractsGraphTriplesBuilder(AppGraph g) {
        this.graph = g;
        this.model = g.getModel();
        this.namespace = AppConfig.graphNamespace();
        this.objectMapper = new ObjectMapper();
        
        // Initialize datatype properties
        contractorPartyNameProperty = new PropertyImpl(namespace, "contractorPartyName");
        contractingPartyNameProperty = new PropertyImpl(namespace, "contractingPartyName");
        governingLawStateProperty = new PropertyImpl(namespace, "governingLawState");
        effectiveDateProperty = new PropertyImpl(namespace, "effectiveDate");
        expirationDateProperty = new PropertyImpl(namespace, "expirationDate");
        contractTypeProperty = new PropertyImpl(namespace, "contractType");
        maximumContractValueProperty = new PropertyImpl(namespace, "maximumContractValue");
        filenameProperty = new PropertyImpl(namespace, "filename");
        contractClauseIdProperty = new PropertyImpl(namespace, "contractClauseId");
        
        // Initialize object properties
        performsProperty = new PropertyImpl(namespace, "performs");
        isPerformedByProperty = new PropertyImpl(namespace, "is_performed_by");
        initiatesProperty = new PropertyImpl(namespace, "initiates");
        isInitiatedByProperty = new PropertyImpl(namespace, "is_initiated_by");
        isGovernedByProperty = new PropertyImpl(namespace, "is_governed_by");
        governsProperty = new PropertyImpl(namespace, "governs");
        containsProperty = new PropertyImpl(namespace, "contains");
        isContainedInProperty = new PropertyImpl(namespace, "is_contained_in"); 
    }

    public void ingestDocument(Map<String, Object> doc) {
        if (doc == null) {
            logger.info("INGEST_DOCUMENT - DOCTYPE IS NULL");
            return;
        }
        
        documentsIngested++;
        String doctype = (String) doc.get("doctype");
        logger.info("INGEST_DOCUMENT -  doctype: {}", doctype);
        if (doctype == null) {
            logger.warn("Document has no doctype field: {}", doc.get("id"));
            return;
        }
        
        try {
            switch (doctype) {
                case "contract_parent":
                    ingestContractDocument(doc);
                    break;
                case "contract_clause":
                    // Clauses are not added to the graph as separate entities for now
                    // They are embedded in the contract documents
                    break;
                case "contract_chunk":
                    // Chunks are for vector search, not for graph
                    break;
                default:
                    logger.debug("Skipping document with unknown doctype: {}", doctype);
            }
        } catch (Exception e) {
            logger.error("Error ingesting document {}: {}", doc.get("id"), e.getMessage());
        }
    }

    private void ingestContractDocument(Map<String, Object> doc) {
        String contractId = (String) doc.get("id");
        if (contractId == null) {
            logger.warn("Contract document has no id field");
            return;
        }
        
        // Create the contract resource
        String contractUri = namespace + contractId;
        Resource contractResource = model.createResource(contractUri);
        contractResource.addProperty(RDF.type, model.createResource(TYPE_CONTRACT_URI));
        
        // Add datatype properties
        addStringProperty(contractResource, effectiveDateProperty, doc, "effective_date");
        addStringProperty(contractResource, expirationDateProperty, doc, "expiration_date");
        addStringProperty(contractResource, contractTypeProperty, doc, "contract_type");
        addStringProperty(contractResource, filenameProperty, doc, "filename");
        
        // Add contract value if present
        Object value = doc.get("contract_value");
        if (value != null) {
            try {
                double contractValue = Double.parseDouble(value.toString());
                contractResource.addProperty(maximumContractValueProperty, 
                    model.createTypedLiteral(contractValue));
            } catch (NumberFormatException e) {
                logger.warn("Invalid contract value for {}: {}", contractId, value);
            }
        }
        
        // Create contractor resources and relationships
        String contractorParty = (String) doc.get("contractor_party");
        if (contractorParty != null && !contractorParty.isEmpty()) {
            Resource contractorPartyResource = createOrGetContractorParty(contractorParty);
            contractorPartyResource.addProperty(performsProperty, contractResource);
            contractResource.addProperty(isPerformedByProperty, contractorPartyResource);
        }
        
        // Create contracting party resources and relationships
        String contractingParty = (String) doc.get("contracting_party");
        if (contractingParty != null && !contractingParty.isEmpty()) {
            Resource contractingPartyResource = createOrGetContractingParty(contractingParty);
            contractingPartyResource.addProperty(initiatesProperty, contractResource);
            contractResource.addProperty(isInitiatedByProperty, contractingPartyResource);
        }
        
        // Create governing law resource and relationships
        String governingLawState = (String) doc.get("governing_law_state");
        if (governingLawState != null && !governingLawState.isEmpty()) {
            Resource governingLawStateResource = createOrGetGoverningLawState(governingLawState);
            contractResource.addProperty(isGovernedByProperty, governingLawStateResource);
            governingLawStateResource.addProperty(governsProperty, contractResource);
        }

        // Create clause resources and relationships
        @SuppressWarnings("unchecked")
        List<String> clauseIds = (List<String>) doc.get("clause_ids");
        if (clauseIds != null) {
            for (String clauseId : clauseIds) {
                if (clauseId != null && !clauseId.isEmpty()) {
                    // Extract clause type from the last segment after underscore
                    // e.g., "contract_708960bd2c6b4c7c9c7acf5d861d3d17_clause_indemnification" -> "indemnification"
                    String[] parts = clauseId.split("_");
                    String clauseType = parts[parts.length - 1];
                    
                    // Create or get clause resource based on type
                    Resource clauseResource = createOrGetClauseResource(clauseType, clauseId, model, namespace);
                    
                    // Set the contractClauseID property
                    clauseResource.addProperty(contractClauseIdProperty, clauseId);
                    
                    // Create relationships between contract and clause
                    clauseResource.addProperty(isContainedInProperty, contractResource);
                    contractResource.addProperty(containsProperty, clauseResource);

                    logger.info("ADDED_CLAUSE: {}", clauseType);

                }
            }
        }
        logger.info("Ingested contract: {} with {} triples", contractId, getTripleCount());
    }

    /**
     * Create or retrieve a clause resource based on clause type
     */
    public static Resource createOrGetClauseResource(String clauseType, String clauseId, 
                                                   Model model, String namespace) {
        // Get the ontology class name
        String ontologyClass = CLAUSE_TYPE_MAPPING.getOrDefault(clauseType.toLowerCase(), "Clause");
        
        // Create resource URI
        String clauseUri = namespace + clauseId;
        
        // Create or get the resource
        Resource clauseResource = model.createResource(clauseUri);
        Resource ontologyClassResource = model.createResource(namespace + ontologyClass);
        clauseResource.addProperty(RDF.type, ontologyClassResource);
        clauseResource.addProperty(RDFS.label, ontologyClass);
        
        return clauseResource;
    }
    
// REFACTOR THESE 2 METHODS INTO ONE METHOD
    private Resource createOrGetContractorParty(String contractorPartyName) {
        // Create a URI-safe version of the contractor party name
        String safeContractorPartyId = contractorPartyName.replaceAll("[^a-zA-Z0-9]", "_").toLowerCase();
        String contractorPartyUri = namespace + "contractorParty_" + safeContractorPartyId;
        
        // Check if resource already exists
        Resource contractorPartyResource = model.getResource(contractorPartyUri);
        if (!model.contains(contractorPartyResource, RDF.type)) {
            // New contractor Party, add type and name
            contractorPartyResource.addProperty(RDF.type, model.createResource(TYPE_CONTRACTOR_PARTY_URI));
            contractorPartyResource.addProperty(contractorPartyNameProperty, contractorPartyName);
        }
        
        return contractorPartyResource;
    }

    private Resource createOrGetContractingParty(String contractingPartyName) {
        // Create a URI-safe version of the contracting party name
        String safeContractingPartyId = contractingPartyName.replaceAll("[^a-zA-Z0-9]", "_").toLowerCase();
        String contractingPartyUri = namespace + "contractoringParty_" + safeContractingPartyId;
        
        // Check if resource already exists
        Resource contractingPartyResource = model.getResource(contractingPartyUri);
        if (!model.contains(contractingPartyResource, RDF.type)) {
            // New contracting Party, add type and name
            contractingPartyResource.addProperty(RDF.type, model.createResource(TYPE_CONTRACTING_PARTY_URI));
            contractingPartyResource.addProperty(contractingPartyNameProperty, contractingPartyName);
        }
        
        return contractingPartyResource;
    }

    private Resource createOrGetGoverningLawState(String governingLawStateName) {
        // Create a URI-safe version of the governing law
        String safeGovLawId = governingLawStateName.replaceAll("[^a-zA-Z0-9]", "_").toLowerCase();
        String govLawStateUri = namespace + "govlaw_" + safeGovLawId;
        
        // Check if resource already exists
        Resource govLawStateResource = model.getResource(govLawStateUri);
        if (!model.contains(govLawStateResource, RDF.type)) {
            // New governing law, add type
            govLawStateResource.addProperty(RDF.type, model.createResource(TYPE_GOVERNING_LAW_STATE_URI));
            govLawStateResource.addProperty(RDFS.label, governingLawStateName);
            // Could add a name property if the ontology had one
        }
        
        return govLawStateResource;
    }

    private void addStringProperty(Resource resource, PropertyImpl property, 
                                  Map<String, Object> doc, String fieldName) {
        Object value = doc.get(fieldName);
        if (value != null && !value.toString().isEmpty()) {
            resource.addProperty(property, value.toString());
        }
    }

    public long getDocumentsIngested() {
        return documentsIngested;
    }

    public long getTripleCount() {
        return model.size();
    }
}