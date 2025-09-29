import { Component } from '@angular/core';
import { QueryBuilderMainComponent } from './query-builder/query-builder-main/query-builder-main';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [QueryBuilderMainComponent],
  template: `<app-query-builder-main></app-query-builder-main>`,
  styles: []
})
export class App {
  title = 'query-builder';
}
