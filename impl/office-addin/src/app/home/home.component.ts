import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

declare const Office: any;

interface OfficeInfo {
  isOfficeContext: boolean;
  host?: string;
  platform?: string;
  version?: string;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  officeInfo: OfficeInfo = { isOfficeContext: false };

  ngOnInit(): void {
    if (typeof Office !== 'undefined' && Office.context) {
      this.officeInfo = {
        isOfficeContext: true,
        host: this.getHostName(Office.context.host),
        platform: this.getPlatformName(Office.context.platform),
        version: Office.context.diagnostics?.version || 'Unknown'
      };
    }
  }

  private getHostName(host: any): string {
    const hostTypes: Record<string, string> = {
      [Office.HostType.Word]: 'Word',
      [Office.HostType.Excel]: 'Excel',
      [Office.HostType.PowerPoint]: 'PowerPoint',
      [Office.HostType.Outlook]: 'Outlook',
      [Office.HostType.OneNote]: 'OneNote',
      [Office.HostType.Project]: 'Project'
    };
    return hostTypes[host] || 'Unknown';
  }

  private getPlatformName(platform: any): string {
    const platformTypes: Record<string, string> = {
      [Office.PlatformType.PC]: 'Windows',
      [Office.PlatformType.Mac]: 'macOS',
      [Office.PlatformType.iOS]: 'iOS',
      [Office.PlatformType.Android]: 'Android',
      [Office.PlatformType.Universal]: 'Universal',
      [Office.PlatformType.OfficeOnline]: 'Office Online'
    };
    return platformTypes[platform] || 'Unknown';
  }
}
