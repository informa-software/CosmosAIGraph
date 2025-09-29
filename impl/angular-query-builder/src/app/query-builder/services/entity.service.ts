import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { delay, map } from 'rxjs/operators';
import { Entity, EntityGroup } from '../models/query.models';
import { MockDataService } from './mock-data.service';

@Injectable({
  providedIn: 'root'
})
export class EntityService {
  private entityCache = new Map<string, Entity[]>();
  private entitySubject = new BehaviorSubject<{ [key: string]: Entity[] }>({});
  
  public entities$ = this.entitySubject.asObservable();

  constructor(private mockData: MockDataService) {
    // Pre-load all entities into cache
    this.initializeCache();
  }

  private initializeCache(): void {
    this.entityCache.set('contractor', this.mockData.getContractorParties());
    this.entityCache.set('contracting', this.mockData.getContractingParties());
    this.entityCache.set('governing_law', this.mockData.getGoverningLaws());
    this.entityCache.set('contract_type', this.mockData.getContractTypes());
    
    // Update subject with all cached data
    const allEntities: { [key: string]: Entity[] } = {};
    this.entityCache.forEach((value, key) => {
      allEntities[key] = value;
    });
    this.entitySubject.next(allEntities);
  }

  getEntities(type: string): Observable<Entity[]> {
    const cached = this.entityCache.get(type);
    if (cached) {
      return of(cached);
    }
    
    // Simulate API call with delay
    return of(this.mockData.searchEntities('', type)).pipe(
      delay(500)
    );
  }

  searchEntities(searchText: string, type: string): Observable<EntityGroup[]> {
    // Simulate API search with delay
    return of(this.mockData.searchEntities(searchText, type)).pipe(
      delay(300),
      map(entities => this.groupEntities(entities, searchText))
    );
  }

  private groupEntities(entities: Entity[], searchText: string): EntityGroup[] {
    if (!searchText || searchText.length < 2) {
      // Return all entities in a single group when no search
      return [{
        type: 'All Entities',
        entities: entities.slice(0, 10) // Limit for display
      }];
    }

    // Group by match quality
    const exactMatches: Entity[] = [];
    const partialMatches: Entity[] = [];
    const search = searchText.toLowerCase();

    entities.forEach(entity => {
      const displayLower = entity.displayName.toLowerCase();
      const normalizedLower = entity.normalizedName.toLowerCase();
      
      if (displayLower.startsWith(search) || normalizedLower.startsWith(search)) {
        exactMatches.push(entity);
      } else if (displayLower.includes(search) || normalizedLower.includes(search)) {
        partialMatches.push(entity);
      }
    });

    const groups: EntityGroup[] = [];
    
    if (exactMatches.length > 0) {
      groups.push({
        type: 'Best Matches',
        entities: exactMatches.slice(0, 5)
      });
    }
    
    if (partialMatches.length > 0) {
      groups.push({
        type: 'Other Matches',
        entities: partialMatches.slice(0, 5)
      });
    }

    return groups;
  }

  getEntityByNormalizedName(normalizedName: string, type: string): Entity | undefined {
    const entities = this.entityCache.get(type);
    return entities?.find(e => e.normalizedName === normalizedName);
  }

  // Get statistics for dashboard
  getEntityStatistics() {
    return {
      contractorParties: this.entityCache.get('contractor')?.length || 0,
      contractingParties: this.entityCache.get('contracting')?.length || 0,
      governingLaws: this.entityCache.get('governing_law')?.length || 0,
      contractTypes: this.entityCache.get('contract_type')?.length || 0,
      totalContracts: this.calculateTotalContracts(),
      totalValue: this.calculateTotalValue()
    };
  }

  private calculateTotalContracts(): number {
    const contractors = this.entityCache.get('contractor') || [];
    return contractors.reduce((sum, entity) => sum + entity.contractCount, 0);
  }

  private calculateTotalValue(): number {
    const contractors = this.entityCache.get('contractor') || [];
    return contractors.reduce((sum, entity) => sum + (entity.totalValue || 0), 0);
  }
}