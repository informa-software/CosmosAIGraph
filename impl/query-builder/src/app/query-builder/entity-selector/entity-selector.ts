import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { debounceTime, map, startWith, switchMap } from 'rxjs/operators';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { Entity, EntityGroup } from '../models/query.models';
import { EntityService } from '../services/entity.service';
import { ApiService } from '../services/api.service';
import { MockDataService } from '../services/mock-data.service';

@Component({
  selector: 'app-entity-selector',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    HttpClientModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule
  ],
  templateUrl: './entity-selector.html',
  styleUrls: ['./entity-selector.scss']
})
export class EntitySelectorComponent implements OnInit {
  @Input() entityType: 'contractor' | 'contracting' | 'governing_law' | 'contract_type' = 'contractor';
  @Input() label: string = 'Select Entity';
  @Input() hint: string = '';
  @Input() multiple: boolean = false;
  @Input() required: boolean = false;
  @Output() entitySelected = new EventEmitter<Entity>();
  @Output() entitiesSelected = new EventEmitter<Entity[]>();
  
  entityControl = new FormControl();
  filteredEntityGroups: Observable<EntityGroup[]>;
  selectedEntities: Entity[] = [];

  constructor(private entityService: EntityService) {
    this.filteredEntityGroups = of([]);
  }

  ngOnInit(): void {
    // Load entities once for this type when actually needed
    // Don't load immediately to avoid duplicate calls
    
    // Set up search, but don't trigger immediately
    this.filteredEntityGroups = this.entityControl.valueChanges.pipe(
      debounceTime(300),
      switchMap(value => {
        const searchText = typeof value === 'string' ? value : value?.displayName || '';
        // Load entities if not cached, then search
        return this.entityService.getEntities(this.entityType).pipe(
          switchMap(() => this.entityService.searchEntities(searchText, this.entityType))
        );
      })
    );
  }

  displayEntity(entity: Entity | string): string {
    if (!entity) return '';
    return typeof entity === 'string' ? entity : entity.displayName;
  }

  onEntitySelected(entity: Entity): void {
    if (this.multiple) {
      if (!this.selectedEntities.find(e => e.normalizedName === entity.normalizedName)) {
        this.selectedEntities.push(entity);
        this.entitiesSelected.emit(this.selectedEntities);
      }
      this.entityControl.setValue('');
    } else {
      this.entitySelected.emit(entity);
    }
  }

  removeEntity(entity: Entity): void {
    this.selectedEntities = this.selectedEntities.filter(
      e => e.normalizedName !== entity.normalizedName
    );
    this.entitiesSelected.emit(this.selectedEntities);
  }

  clearSelection(): void {
    this.entityControl.setValue('');
    this.selectedEntities = [];
    if (this.multiple) {
      this.entitiesSelected.emit([]);
    } else {
      this.entitySelected.emit(undefined);
    }
  }

  getEntityIcon(): string {
    switch (this.entityType) {
      case 'contractor':
        return 'engineering';
      case 'contracting':
        return 'business';
      case 'governing_law':
        return 'gavel';
      case 'contract_type':
        return 'description';
      default:
        return 'label';
    }
  }

  getEntityStatistics(entity: Entity): string {
    const parts = [];
    
    if (entity.contractCount) {
      parts.push(`${entity.contractCount} contracts`);
    }
    
    if (entity.totalValue) {
      const value = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0
      }).format(entity.totalValue);
      parts.push(value);
    }
    
    return parts.join(' • ');
  }

  onInputFocus(): void {
    // When input is focused, load entities and show initial list
    // This replaces the startWith('') pattern to avoid duplicate calls
    if (!this.entityControl.value) {
      this.entityService.getEntities(this.entityType).pipe(
        switchMap(() => this.entityService.searchEntities('', this.entityType))
      ).subscribe(groups => {
        // Trigger change detection to show dropdown
        this.entityControl.updateValueAndValidity();
      });
    }
  }
}
