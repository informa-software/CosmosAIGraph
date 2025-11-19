import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { Entity, EntityGroup, QueryTemplate, StructuredQuery, QueryResult } from '../models/query.models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'https://localhost:8000/api';

  constructor(private http: HttpClient) {}

  /**
   * Get all entities of a specific type
   */
  getEntities(entityType: string): Observable<Entity[]> {
    return this.http.get<any>(`${this.baseUrl}/entities/${entityType}`).pipe(
      map(response => {
        // Handle clause_types differently as they have different fields
        if (entityType === 'clause_types') {
          return response.entities.map((entity: any) => ({
            normalizedName: entity.normalizedName,
            displayName: entity.displayName,
            type: entity.type,
            icon: entity.icon,
            description: entity.description,
            category: entity.category
          }));
        } else {
          return response.entities.map((entity: any) => ({
            normalizedName: entity.normalizedName,
            displayName: entity.displayName,
            contractCount: entity.contractCount,
            totalValue: entity.totalValue,
            type: entity.type
          }));
        }
      }),
      catchError(error => {
        console.error('Error fetching entities:', error);
        return of([]);
      })
    );
  }

  /**
   * Search entities with fuzzy matching
   */
  searchEntities(query: string, entityType?: string): Observable<EntityGroup[]> {
    let params = new HttpParams().set('q', query);
    if (entityType) {
      params = params.set('entity_type', entityType);
    }

    return this.http.get<any>(`${this.baseUrl}/entities/search`, { params }).pipe(
      map(response => {
        return response.results.map((group: any) => ({
          type: group.type,
          displayName: group.displayName,
          entities: group.entities.map((entity: any) => ({
            normalizedName: entity.normalizedName,
            displayName: entity.displayName,
            contractCount: entity.contractCount,
            totalValue: entity.totalValue,
            type: entity.type,
            score: entity.score
          }))
        }));
      }),
      catchError(error => {
        console.error('Error searching entities:', error);
        return of([]);
      })
    );
  }

  /**
   * Get available clause types
   */
  getClauseTypes(): Observable<any[]> {
    return this.http.get<any>(`${this.baseUrl}/entities/clause_types`).pipe(
      map(response => {
        return response.entities.map((entity: any) => ({
          type: entity.type,
          displayName: entity.displayName,
          icon: entity.icon,
          description: entity.description,
          category: entity.category
        }));
      }),
      catchError(error => {
        console.error('Error fetching clause types:', error);
        return of([]);
      })
    );
  }

  /**
   * Get available query templates
   */
  getQueryTemplates(): Observable<QueryTemplate[]> {
    return this.http.get<any>(`${this.baseUrl}/query-templates`).pipe(
      map(response => response.templates),
      catchError(error => {
        console.error('Error fetching templates:', error);
        return of([]);
      })
    );
  }

  /**
   * Execute a structured query
   */
  executeQuery(query: StructuredQuery): Observable<QueryResult> {
    return this.http.post<QueryResult>(`${this.baseUrl}/query/execute`, query).pipe(
      catchError(error => {
        console.error('Error executing query:', error);
        throw error;
      })
    );
  }

  /**
   * Get natural language preview of a query
   */
  getQueryPreview(query: StructuredQuery): Observable<string> {
    return this.http.post<any>(`${this.baseUrl}/query/preview`, query).pipe(
      map(response => response.naturalLanguage),
      catchError(error => {
        console.error('Error getting query preview:', error);
        return of('Unable to generate preview');
      })
    );
  }
}