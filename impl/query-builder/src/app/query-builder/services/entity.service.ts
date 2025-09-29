import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { delay, map, tap, catchError, share } from 'rxjs/operators';
import { Entity, EntityGroup } from '../models/query.models';
import { MockDataService } from './mock-data.service';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class EntityService {
  private entityCache = new Map<string, Entity[]>();
  private entitySubject = new BehaviorSubject<{ [key: string]: Entity[] }>({});
  private loadingCache = new Map<string, Observable<Entity[]>>();
  // Toggle this to switch between mock and real data
  // Set to false to use real backend API, true for mock data
  private useMockData = false;
  
  public entities$ = this.entitySubject.asObservable();

  constructor(
    private mockData: MockDataService,
    private api: ApiService
  ) {
    // Initialize cache (will use real data if available)
    this.initializeCache();
  }

  private initializeCache(): void {
    if (this.useMockData) {
      // Use mock data - load all at once
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
    // Don't load all entities on startup when using real API
    // They will be loaded on-demand
  }

  private getMockEntitiesByType(type: string): Entity[] {
    switch(type) {
      case 'contractor': return this.mockData.getContractorParties();
      case 'contracting': return this.mockData.getContractingParties();
      case 'governing_law': return this.mockData.getGoverningLaws();
      case 'contract_type': return this.mockData.getContractTypes();
      default: return [];
    }
  }

  private updateEntitySubject(): void {
    const allEntities: { [key: string]: Entity[] } = {};
    this.entityCache.forEach((value, key) => {
      allEntities[key] = value;
    });
    this.entitySubject.next(allEntities);
  }

  getEntities(type: string): Observable<Entity[]> {
    // Check cache first
    const cached = this.entityCache.get(type);
    if (cached && cached.length > 0) {
      return of(cached);
    }
    
    // Check if already loading this type
    const loading = this.loadingCache.get(type);
    if (loading) {
      return loading;
    }
    
    if (this.useMockData) {
      // Use mock data
      const entities = this.getMockEntitiesByType(type);
      this.entityCache.set(type, entities);
      this.updateEntitySubject();
      return of(entities);
    } else {
      // Load from API and cache the observable to prevent duplicate requests
      const backendType = this.mapToBackendType(type);
      const loading$ = this.api.getEntities(backendType).pipe(
        tap(entities => {
          console.log(`Loaded ${entities.length} ${type} entities`);
          this.entityCache.set(type, entities);
          this.updateEntitySubject();
          this.loadingCache.delete(type); // Remove from loading cache
        }),
        catchError(error => {
          console.error(`Error fetching ${type} entities, using mock data`, error);
          this.loadingCache.delete(type); // Remove from loading cache
          // Fallback to mock data
          const mockEntities = this.getMockEntitiesByType(type);
          this.entityCache.set(type, mockEntities);
          this.updateEntitySubject();
          return of(mockEntities);
        }),
        share() // Share the observable to prevent duplicate requests
      );
      
      // Store the loading observable to prevent duplicate requests
      this.loadingCache.set(type, loading$);
      return loading$;
    }
  }

  searchEntities(searchText: string, type: string): Observable<EntityGroup[]> {
    if (this.useMockData) {
      // Use mock data implementation
      return of(this.mockData.searchEntities(searchText, type)).pipe(
        delay(300),
        map(entities => this.groupEntities(entities, searchText))
      );
    } else {
      // Use real API
      const backendType = this.mapToBackendType(type);
      return this.api.searchEntities(searchText, backendType).pipe(
        catchError(error => {
          console.error('Search failed, using cached data', error);
          // Fallback to searching cached data
          const cached = this.entityCache.get(type) || [];
          const filtered = this.filterEntities(cached, searchText);
          return of(this.groupEntities(filtered, searchText));
        })
      );
    }
  }

  private filterEntities(entities: Entity[], searchText: string): Entity[] {
    if (!searchText || searchText.length === 0) {
      return entities;
    }

    const search = searchText.toLowerCase();
    return entities.filter(entity => {
      const displayLower = entity.displayName.toLowerCase();
      const normalizedLower = entity.normalizedName.toLowerCase();
      return displayLower.includes(search) || normalizedLower.includes(search);
    });
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

  private mapToBackendType(frontendType: string): string {
    const typeMap: { [key: string]: string } = {
      'contractor': 'contractor_parties',
      'contracting': 'contracting_parties',
      'governing_law': 'governing_laws',
      'contract_type': 'contract_types'
    };
    return typeMap[frontendType] || frontendType;
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