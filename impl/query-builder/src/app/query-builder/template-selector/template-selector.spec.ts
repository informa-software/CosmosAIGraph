import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TemplateSelector } from './template-selector';

describe('TemplateSelector', () => {
  let component: TemplateSelector;
  let fixture: ComponentFixture<TemplateSelector>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TemplateSelector]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TemplateSelector);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
