import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

// Angular Material Imports
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { MatListModule } from '@angular/material/list';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatBadgeModule } from '@angular/material/badge';

// Components
import { QueryBuilderMainComponent } from './components/query-builder-main/query-builder-main.component';
import { TemplateSelectorComponent } from './components/template-selector/template-selector.component';
import { EntitySelectorComponent } from './components/entity-selector/entity-selector.component';
import { QueryPreviewComponent } from './components/query-preview/query-preview.component';

// Services
import { QueryBuilderService } from './services/query-builder.service';
import { EntityService } from './services/entity.service';
import { MockDataService } from './services/mock-data.service';

@NgModule({
  declarations: [
    QueryBuilderMainComponent,
    TemplateSelectorComponent,
    EntitySelectorComponent,
    QueryPreviewComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatToolbarModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatAutocompleteModule,
    MatChipsModule,
    MatListModule,
    MatTabsModule,
    MatExpansionModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatBadgeModule
  ],
  providers: [
    QueryBuilderService,
    EntityService,
    MockDataService
  ],
  exports: [
    QueryBuilderMainComponent
  ]
})
export class QueryBuilderModule { }