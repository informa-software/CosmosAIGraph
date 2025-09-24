package com.microsoft.cosmosdb.caig.util;

import com.azure.cosmos.CosmosAsyncClient;
import com.azure.cosmos.CosmosAsyncContainer;
import com.azure.cosmos.CosmosAsyncDatabase;
import com.azure.cosmos.CosmosClientBuilder;
import com.azure.cosmos.models.CosmosQueryRequestOptions;
import com.azure.cosmos.util.CosmosPagedFlux;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import reactor.core.publisher.Flux;

import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * Test utility to verify CosmosDB connectivity and document retrieval
 */
public class CosmosTestQuery {
    
    private static Logger logger = LoggerFactory.getLogger(CosmosTestQuery.class);
    
    public static void testConnection() {
        logger.warn("===== STARTING COSMOS CONNECTION TEST =====");
        
        try {
            String uri = AppConfig.getCosmosNoSqlUri();
            String key = AppConfig.getCosmosNoSqlKey1();
            String dbname = AppConfig.getGraphSourceDb();
            String cname = AppConfig.getGraphSourceContainer();
            
            logger.warn("Connecting to: {}", uri);
            logger.warn("Database: {}, Container: {}", dbname, cname);
            
            // Create client
            CosmosAsyncClient client = new CosmosClientBuilder()
                .endpoint(uri)
                .key(key)
                .gatewayMode()  // Use Gateway mode to avoid SSL issues
                .endpointDiscoveryEnabled(false)
                .buildAsyncClient();
            
            CosmosAsyncDatabase database = client.getDatabase(dbname);
            CosmosAsyncContainer container = database.getContainer(cname);
            
            // Test 1: Count ALL documents
            testQuery(container, "SELECT COUNT(1) as count FROM c", "Total Documents");
            
            // Test 2: Count by doctype
            testQuery(container, "SELECT c.doctype, COUNT(1) as count FROM c GROUP BY c.doctype", "Documents by Type");
            
            // Test 3: Get first document
            testQuery(container, "SELECT TOP 1 * FROM c", "First Document");
            
            // Test 4: Count contract_parent specifically
            testQuery(container, "SELECT COUNT(1) as count FROM c WHERE c.doctype = 'contract_parent'", "Contract Parent Count");
            
            // Test 5: Get sample contract_parent
            testQuery(container, "SELECT TOP 1 c.id, c.doctype FROM c WHERE c.doctype = 'contract_parent'", "Sample Contract Parent");
            
            // Test 6: List all doctypes
            testQuery(container, "SELECT DISTINCT c.doctype FROM c", "All Document Types");
            
            client.close();
            logger.warn("===== COSMOS CONNECTION TEST COMPLETE =====");
            
        } catch (Exception e) {
            logger.error("Connection test failed: ", e);
        }
    }
    
    private static void testQuery(CosmosAsyncContainer container, String sql, String description) {
        try {
            logger.warn("\n----- Testing: {} -----", description);
            logger.warn("Query: {}", sql);
            
            AtomicLong resultCount = new AtomicLong(0);
            CosmosQueryRequestOptions options = new CosmosQueryRequestOptions();
            CosmosPagedFlux<Map> flux = container.queryItems(sql, options, Map.class);
            
            flux.byPage(100).flatMap(response -> {
                List<Map> results = response.getResults();
                resultCount.addAndGet(results.size());
                
                logger.warn("Page received with {} results", results.size());
                
                for (Map doc : results) {
                    logger.warn("Result: {}", doc);
                }
                
                return Flux.empty();
            }).blockLast();
            
            logger.warn("Total results: {}", resultCount.get());
            
        } catch (Exception e) {
            logger.error("Query failed: ", e);
        }
    }
    
    public static void main(String[] args) {
        AppConfig.initialize();
        testConnection();
    }
}