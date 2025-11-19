# Angular Frontend Updates for Azure Blob Storage

This document provides the necessary updates to the Angular frontend to support PDF access via Azure Blob Storage.

## Changes to contract.service.ts

Add these methods to `query-builder/src/app/contract-workbench/services/contract.service.ts`:

```typescript
/**
 * Get time-limited SAS URL for contract PDF from Azure Blob Storage
 *
 * @param contractId - ID of the contract
 * @returns Observable with PDF URL and expiry information
 */
getContractPdfUrl(contractId: string): Observable<{
  contract_id: string;
  pdf_url: string;
  expires_in_hours: number;
  pdf_filename: string;
}> {
  return this.http.get<any>(`${this.apiUrl}/contracts/${contractId}/pdf-url`).pipe(
    catchError(error => {
      console.error('Error getting PDF URL:', error);
      throw error;
    })
  );
}

/**
 * Open contract PDF in new browser tab
 *
 * @param contractId - ID of the contract
 */
openContractPdf(contractId: string): void {
  this.getContractPdfUrl(contractId).subscribe({
    next: (response) => {
      // Open PDF in new tab using the secure SAS URL
      window.open(response.pdf_url, '_blank');
    },
    error: (error) => {
      console.error('Error opening PDF:', error);
      const errorMessage = error.error?.message || 'Failed to open PDF. Please try again.';
      alert(`PDF Access Error: ${errorMessage}`);
    }
  });
}

/**
 * Download contract PDF to local machine
 *
 * @param contractId - ID of the contract
 * @param contractTitle - Optional title for the downloaded file
 */
downloadContractPdf(contractId: string, contractTitle?: string): void {
  this.getContractPdfUrl(contractId).subscribe({
    next: (response) => {
      // Create a temporary anchor element to trigger download
      const link = document.createElement('a');
      link.href = response.pdf_url;

      // Use contract title if provided, otherwise use the PDF filename
      const filename = contractTitle
        ? `${contractTitle.replace(/[^a-z0-9]/gi, '_')}.pdf`
        : response.pdf_filename;

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
    error: (error) => {
      console.error('Error downloading PDF:', error);
      const errorMessage = error.error?.message || 'Failed to download PDF. Please try again.';
      alert(`PDF Download Error: ${errorMessage}`);
    }
  });
}
```

## Usage in Components

### Example 1: Open PDF Button (contract-workbench.ts)

```typescript
/**
 * Open PDF viewer for the selected contract
 */
viewContractPdf(contractId: string): void {
  this.contractService.openContractPdf(contractId);
}
```

### Example 2: Download PDF Button

```typescript
/**
 * Download PDF for offline viewing
 */
downloadPdf(contract: Contract): void {
  this.contractService.downloadContractPdf(contract.id, contract.title);
}
```

## HTML Template Updates

### Add "View PDF" Button to Contract Cards

```html
<!-- In contract details modal or contract card -->
<button
  class="btn btn-primary btn-sm"
  (click)="viewContractPdf(contract.id)"
  title="Open PDF in new tab">
  📄 View PDF
</button>

<button
  class="btn btn-secondary btn-sm ml-2"
  (click)="downloadPdf(contract)"
  title="Download PDF">
  💾 Download
</button>
```

### Example: Add to Contract Details Modal

```html
<!-- In contract-workbench.html, within showContractDetailsModal -->
<div class="modal-header">
  <h5 class="modal-title">{{ selectedContractForDetails?.title }}</h5>
  <div class="ml-auto">
    <button
      class="btn btn-sm btn-outline-primary mr-2"
      (click)="viewContractPdf(selectedContractForDetails?.id)"
      *ngIf="selectedContractForDetails">
      <i class="fas fa-file-pdf"></i> View PDF
    </button>
    <button
      type="button"
      class="btn-close"
      (click)="showContractDetailsModal = false">
    </button>
  </div>
</div>
```

### Example: Add to Contract List Items

```html
<!-- In filtered contracts list -->
<div class="contract-item" *ngFor="let contract of filteredContracts">
  <div class="contract-info">
    <h6>{{ contract.title }}</h6>
    <p>{{ contract.contractor_party }}</p>
  </div>
  <div class="contract-actions">
    <button
      class="btn btn-icon"
      (click)="viewContractPdf(contract.id); $event.stopPropagation()"
      title="View PDF">
      📄
    </button>
    <button
      class="btn btn-icon"
      (click)="toggleContractSelection(contract.id)"
      [class.selected]="isContractSelected(contract.id)">
      {{ isContractSelected(contract.id) ? '☑' : '☐' }}
    </button>
  </div>
</div>
```

## Error Handling

The service methods include built-in error handling for common scenarios:

- **404 Not Found**: Contract or PDF doesn't exist
- **500 Server Error**: Backend processing error
- **503 Service Unavailable**: Blob storage not configured
- **Network Errors**: Connection issues

All errors are displayed to the user via `alert()`. For better UX, consider using your `ToastService`:

```typescript
openContractPdf(contractId: string): void {
  this.contractService.getContractPdfUrl(contractId).subscribe({
    next: (response) => {
      window.open(response.pdf_url, '_blank');
      this.toastService.success('PDF Opened', 'Opening PDF in new tab');
    },
    error: (error) => {
      console.error('Error opening PDF:', error);
      const errorMessage = error.error?.message || 'Failed to open PDF';
      this.toastService.error('PDF Access Error', errorMessage);
    }
  });
}
```

## Security Considerations

### SAS URL Expiry
- SAS URLs expire after 1 hour by default (configurable)
- URLs cannot be reused after expiry
- Generate new URL if user needs to access PDF again

### URL Handling
- SAS URLs are not stored locally
- URLs are requested on-demand when user clicks "View PDF"
- Each request generates a fresh SAS token

### Browser Compatibility
- `window.open()` works in all modern browsers
- Some browsers may block popups - instruct users to allow popups for your domain
- Download functionality uses HTML5 anchor `download` attribute

## Testing Checklist

- [ ] View PDF button opens new tab with PDF
- [ ] Download PDF saves file to local machine
- [ ] Error handling displays user-friendly messages
- [ ] PDF access works for all contract types
- [ ] SAS URL expiry is handled gracefully
- [ ] Browser popup blocker doesn't interfere
- [ ] Multiple PDF views/downloads work correctly
- [ ] Network errors are handled gracefully

## Optional Enhancements

### Loading Indicators

```typescript
isLoadingPdf = false;

viewContractPdf(contractId: string): void {
  this.isLoadingPdf = true;
  this.contractService.getContractPdfUrl(contractId).subscribe({
    next: (response) => {
      window.open(response.pdf_url, '_blank');
      this.isLoadingPdf = false;
    },
    error: (error) => {
      this.isLoadingPdf = false;
      this.toastService.error('PDF Access Error', error.error?.message);
    }
  });
}
```

```html
<button
  class="btn btn-primary"
  (click)="viewContractPdf(contract.id)"
  [disabled]="isLoadingPdf">
  <span *ngIf="!isLoadingPdf">📄 View PDF</span>
  <span *ngIf="isLoadingPdf">⏳ Loading...</span>
</button>
```

### PDF Preview Modal (Advanced)

For inline PDF viewing without new tabs, use PDF.js or an iframe:

```html
<!-- PDF Preview Modal -->
<div class="modal" *ngIf="showPdfPreviewModal">
  <div class="modal-dialog modal-xl">
    <div class="modal-content">
      <div class="modal-header">
        <h5>{{ pdfPreviewTitle }}</h5>
        <button class="btn-close" (click)="closePdfPreview()"></button>
      </div>
      <div class="modal-body">
        <iframe
          [src]="sanitizePdfUrl(pdfPreviewUrl)"
          style="width:100%; height:80vh;"
          frameborder="0">
        </iframe>
      </div>
    </div>
  </div>
</div>
```

```typescript
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

pdfPreviewUrl: string = '';
pdfPreviewTitle: string = '';
showPdfPreviewModal = false;

constructor(private sanitizer: DomSanitizer, ...) {}

viewContractPdfInline(contractId: string, title: string): void {
  this.contractService.getContractPdfUrl(contractId).subscribe({
    next: (response) => {
      this.pdfPreviewUrl = response.pdf_url;
      this.pdfPreviewTitle = title;
      this.showPdfPreviewModal = true;
    },
    error: (error) => {
      this.toastService.error('PDF Access Error', error.error?.message);
    }
  });
}

sanitizePdfUrl(url: string): SafeResourceUrl {
  return this.sanitizer.bypassSecurityTrustResourceUrl(url);
}

closePdfPreview(): void {
  this.showPdfPreviewModal = false;
  this.pdfPreviewUrl = '';
  this.pdfPreviewTitle = '';
}
```
