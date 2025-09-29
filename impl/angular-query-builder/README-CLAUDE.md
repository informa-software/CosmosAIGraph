# Angular Query Builder - Phase 1 (Mocked Data)

## Setup Instructions

```bash
# Create new Angular project
ng new angular-query-builder --routing --style=scss
cd angular-query-builder

# Install Angular Material
ng add @angular/material

# Install additional dependencies
npm install @angular/flex-layout

# Generate the query builder module
ng generate module query-builder --routing
ng generate component query-builder/template-selector
ng generate component query-builder/entity-selector  
ng generate component query-builder/clause-selector
ng generate component query-builder/query-preview
ng generate component query-builder/query-builder-main
ng generate service query-builder/services/mock-data
ng generate service query-builder/services/entity
ng generate service query-builder/services/query-builder

# Run the application
ng serve
```

## Project Structure

```
src/app/
├── query-builder/
│   ├── components/
│   │   ├── template-selector/
│   │   ├── entity-selector/
│   │   ├── clause-selector/
│   │   ├── query-preview/
│   │   └── query-builder-main/
│   ├── services/
│   │   ├── mock-data.service.ts
│   │   ├── entity.service.ts
│   │   └── query-builder.service.ts
│   ├── models/
│   │   └── query.models.ts
│   └── query-builder.module.ts
└── app.module.ts
```

## Phase 1 Features

1. Template selection interface with 4 query types
2. Entity selector with mocked autocomplete
3. Clause type selector
4. Query preview showing natural language and JSON
5. Basic query execution (returns mocked results)

All data is mocked for demonstration purposes.