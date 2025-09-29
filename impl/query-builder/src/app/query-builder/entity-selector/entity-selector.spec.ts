import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EntitySelector } from './entity-selector';

describe('EntitySelector', () => {
  let component: EntitySelector;
  let fixture: ComponentFixture<EntitySelector>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EntitySelector]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EntitySelector);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
