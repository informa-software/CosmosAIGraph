import { Component, OnInit } from '@angular/core';
import { RouterOutlet, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

declare const Office: any;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  template: `
    <div class="office-addin-container">
      <router-outlet></router-outlet>
    </div>
  `,
  styles: [`
    .office-addin-container {
      height: 100vh;
      overflow: auto;
    }
  `]
})
export class App implements OnInit {
  constructor(private router: Router) {}

  ngOnInit(): void {
    // Auto-route based on Office host
    if (typeof Office !== 'undefined' && Office.context) {
      const host = Office.context.host;

      if (host === Office.HostType.Word) {
        console.log('Detected Word - routing to /word');
        this.router.navigate(['/word']);
      } else if (host === Office.HostType.Excel) {
        console.log('Detected Excel - routing to /excel');
        // Future: this.router.navigate(['/excel']);
      } else if (host === Office.HostType.PowerPoint) {
        console.log('Detected PowerPoint - routing to /powerpoint');
        // Future: this.router.navigate(['/powerpoint']);
      } else {
        console.log('Unknown Office host:', host);
        this.router.navigate(['/home']);
      }
    } else {
      console.log('Not in Office context - showing home page');
    }
  }
}
