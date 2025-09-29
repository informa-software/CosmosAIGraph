import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ClauseSelector } from './clause-selector';

describe('ClauseSelector', () => {
  let component: ClauseSelector;
  let fixture: ComponentFixture<ClauseSelector>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ClauseSelector]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ClauseSelector);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
