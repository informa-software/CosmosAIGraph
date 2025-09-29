import { ComponentFixture, TestBed } from '@angular/core/testing';

import { QueryBuilderMain } from './query-builder-main';

describe('QueryBuilderMain', () => {
  let component: QueryBuilderMain;
  let fixture: ComponentFixture<QueryBuilderMain>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QueryBuilderMain]
    })
    .compileComponents();

    fixture = TestBed.createComponent(QueryBuilderMain);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
