import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormControl } from '@angular/forms';
import { Observable, of } from 'rxjs';
import { debounceTime, map, startWith, switchMap } from 'rxjs/operators';
import { Entity, EntityGroup } from '../../models/query.models';
import { EntityService } from '../../services/entity.service';

@Component({
  selector: 'app-entity-selector',
  templateUrl: './entity-selector.component.html',
  styleUrls: ['./entity-selector.component.scss']
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
  filteredEntityGroups$: Observable<EntityGroup[]>;
  selectedEntities: Entity[] = [];

  constructor(private entityService: EntityService) {
    this.filteredEntityGroups$ = of([]);
  }

  ngOnInit(): void {
    // Load entities for this type
    this.entityService.getEntities(this.entityType).subscribe();
    
    // Setup autocomplete with search
    this.filteredEntityGroups$ = this.entityControl.valueChanges.pipe(
      startWith(''),
      debounceTime(300),
      switchMap(value => {
        const searchText = typeof value === 'string' ? value : value?.displayName || '';
        return this.entityService.searchEntities(searchText, this.entityType);
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
}