import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface ModelOption {
  value: string;
  label: string;
  description: string;
  badge?: string;
  pricing?: string;
}

@Component({
  selector: 'app-model-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './model-selector.html',
  styleUrls: ['./model-selector.scss']
})
export class ModelSelectorComponent {
  @Input() selectedModel: string = 'primary';
  @Input() showDescription: boolean = true;
  @Input() disabled: boolean = false;
  @Output() modelChange = new EventEmitter<string>();

  models: ModelOption[] = [
    {
      value: 'primary',
      label: 'GPT-4.1',
      description: 'Best quality, comprehensive analysis',
      badge: 'Recommended',
      pricing: '$30 / 1M tokens'
    },
    {
      value: 'secondary',
      label: 'GPT-4.1-mini',
      description: 'Good quality, faster and more cost-effective',
      badge: 'Cost Saver',
      pricing: '$10 / 1M tokens'
    }
  ];

  onModelChange(value: string): void {
    this.selectedModel = value;
    this.modelChange.emit(value);
  }

  getModelInfo(value: string): ModelOption | undefined {
    return this.models.find(m => m.value === value);
  }
}
