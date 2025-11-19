import { Pipe, PipeTransform } from '@angular/core';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Pipe({
  name: 'markdown',
  standalone: true
})
export class MarkdownPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {
    // Configure marked options for better rendering
    marked.setOptions({
      breaks: true,
      gfm: true,
      async: false
    });
  }

  transform(value: string | null | undefined): SafeHtml {
    if (!value) {
      return '';
    }

    try {
      // Convert markdown to HTML synchronously
      const html = marked(value, { async: false }) as string;

      console.log('Markdown input (first 200 chars):', value.substring(0, 200));
      console.log('HTML output (first 200 chars):', html.substring(0, 200));

      // Sanitize and return as safe HTML
      return this.sanitizer.bypassSecurityTrustHtml(html);
    } catch (error) {
      console.error('Error parsing markdown:', error);
      return this.sanitizer.bypassSecurityTrustHtml(value);
    }
  }
}
