import { Injectable } from '@angular/core';
import { LocationStrategy } from '@angular/common';

/**
 * Custom LocationStrategy for Office Add-ins
 *
 * Office Add-ins run in a restricted environment where browser APIs like
 * window.history.pushState are not available. This strategy provides a
 * simple in-memory routing mechanism that doesn't rely on browser APIs.
 */
@Injectable()
export class OfficeLocationStrategy extends LocationStrategy {
  private _path: string = '';
  private _listeners: ((event: any) => void)[] = [];

  override onPopState(fn: (event: any) => void): void {
    this._listeners.push(fn);
  }

  override getBaseHref(): string {
    return '';
  }

  override path(includeHash?: boolean): string {
    return this._path;
  }

  override prepareExternalUrl(internal: string): string {
    return internal;
  }

  override pushState(state: any, title: string, path: string, queryParams: string): void {
    this._path = path + (queryParams ? '?' + queryParams : '');
    console.log('OfficeLocationStrategy: pushState', this._path);
  }

  override replaceState(state: any, title: string, path: string, queryParams: string): void {
    this._path = path + (queryParams ? '?' + queryParams : '');
    console.log('OfficeLocationStrategy: replaceState', this._path);
  }

  override forward(): void {
    console.warn('OfficeLocationStrategy: forward() not supported');
  }

  override back(): void {
    console.warn('OfficeLocationStrategy: back() not supported');
  }

  override historyGo(relativePosition?: number): void {
    console.warn('OfficeLocationStrategy: historyGo() not supported');
  }

  override getState(): unknown {
    return null;
  }
}
