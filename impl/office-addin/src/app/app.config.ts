import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { LocationStrategy } from '@angular/common';

import { routes } from './app.routes';
import { OfficeLocationStrategy } from './office-location-strategy';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    // Office Add-ins require custom LocationStrategy (browser APIs not available)
    provideRouter(routes),
    { provide: LocationStrategy, useClass: OfficeLocationStrategy },
    provideHttpClient()
  ]
};
