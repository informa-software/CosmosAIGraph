import { ComponentFixture, TestBed } from '@angular/core/testing';

import { QueryPreview } from './query-preview';

describe('QueryPreview', () => {
  let component: QueryPreview;
  let fixture: ComponentFixture<QueryPreview>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QueryPreview]
    })
    .compileComponents();

    fixture = TestBed.createComponent(QueryPreview);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
