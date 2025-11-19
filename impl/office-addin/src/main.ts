import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

declare const Office: any;

// Function to bootstrap Angular
function startAngular() {
  console.log('Bootstrapping Angular application...');
  bootstrapApplication(App, appConfig)
    .catch((err) => console.error('Angular bootstrap error:', err));
}

// Office Add-ins MUST wait for Office.js to initialize
if (typeof Office !== 'undefined') {
  console.log('Office.js detected - waiting for Office to be ready');

  Office.onReady((info: any) => {
    console.log('Office.js initialized:', {
      host: info.host,
      platform: info.platform
    });
    startAngular();
  });
} else {
  // Fallback for development/testing outside Office
  console.warn('Office.js not loaded - this add-in requires Office context');
  console.log('Bootstrapping anyway for development purposes');
  startAngular();
}
