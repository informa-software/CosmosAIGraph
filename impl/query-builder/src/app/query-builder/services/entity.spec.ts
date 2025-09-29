import { TestBed } from '@angular/core/testing';

import { Entity } from './entity';

describe('Entity', () => {
  let service: Entity;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Entity);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
