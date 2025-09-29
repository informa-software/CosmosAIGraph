import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { QueryTemplate } from '../models/query.models';
import { MockDataService } from '../services/mock-data.service';

@Component({
  selector: 'app-template-selector',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatButtonModule
  ],
  templateUrl: './template-selector.html',
  styleUrls: ['./template-selector.scss'],
  providers: [MockDataService]
})
export class TemplateSelectorComponent {
  @Output() templateSelected = new EventEmitter<QueryTemplate>();
  
  templates: QueryTemplate[];
  selectedTemplate: QueryTemplate | null = null;

  constructor(private mockData: MockDataService) {
    this.templates = this.mockData.getTemplates();
  }

  selectTemplate(template: QueryTemplate): void {
    this.selectedTemplate = template;
    this.templateSelected.emit(template);
  }

  getIconColor(operation: string): string {
    switch (operation) {
      case 'comparison':
        return '#4caf50';
      case 'analysis':
        return '#2196f3';
      case 'search':
        return '#ff9800';
      default:
        return '#9e9e9e';
    }
  }

  getChipColor(operation: string): 'primary' | 'accent' | 'warn' | undefined {
    switch (operation) {
      case 'comparison':
        return 'accent';
      case 'analysis':
        return 'primary';
      case 'search':
        return 'warn';
      default:
        return undefined;
    }
  }
}
