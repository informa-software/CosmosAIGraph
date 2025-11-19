/**
 * Track Changes Service
 * Handles detection and extraction of original/revised text from Word documents with track changes
 */

import { Injectable } from '@angular/core';
import { TrackedChangesSummary } from '../models/track-changes.models';

declare const Word: any;

@Injectable({
  providedIn: 'root'
})
export class TrackChangesService {

  constructor() {}

  /**
   * Check if Word API is available
   */
  isWordAvailable(): boolean {
    return typeof Word !== 'undefined' && typeof Word.run === 'function';
  }

  /**
   * Check if track changes is enabled in the document
   */
  async isTrackChangesEnabled(): Promise<boolean> {
    if (!this.isWordAvailable()) {
      return false;
    }

    return Word.run(async (context: any) => {
      const doc = context.document;
      doc.load('changeTrackingMode');
      await context.sync();

      // Returns true if tracking is enabled (TrackAll or TrackMineOnly)
      return doc.changeTrackingMode !== Word.ChangeTrackingMode.off;
    });
  }

  /**
   * Get track changes summary
   */
  async getTrackChangesSummary(): Promise<TrackedChangesSummary> {
    if (!this.isWordAvailable()) {
      return { isEnabled: false, changeTrackingMode: 'Off' };
    }

    return Word.run(async (context: any) => {
      const doc = context.document;
      doc.load('changeTrackingMode');
      await context.sync();

      const mode = doc.changeTrackingMode;

      return {
        isEnabled: mode !== Word.ChangeTrackingMode.off,
        changeTrackingMode: this.getChangeTrackingModeString(mode)
      };
    });
  }

  /**
   * Extract original text (with all tracked changes rejected)
   * This shows what the document looked like before changes
   * Uses the built-in getReviewedText API for simplicity and reliability
   */
  async extractOriginalText(): Promise<string> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      const body = context.document.body;

      console.log('=== EXTRACTING ORIGINAL TEXT ===');

      // Use the built-in API to get text with track changes in "Original" state
      const originalTextResult = body.getReviewedText(Word.ChangeTrackingVersion.original);
      await context.sync();

      const originalText = originalTextResult.value;
      console.log('Original text length:', originalText.length);
      console.log('Original text preview:', originalText.substring(0, 200));
      console.log('=== END EXTRACTING ORIGINAL TEXT ===');

      return originalText;
    });
  }

  /**
   * Extract revised text (with all tracked changes accepted)
   * This shows what the document will look like if all changes are accepted
   * Uses the built-in getReviewedText API for simplicity and reliability
   */
  async extractRevisedText(): Promise<string> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      const body = context.document.body;

      console.log('=== EXTRACTING REVISED TEXT ===');

      // Use the built-in API to get text with track changes in "Current" state
      const revisedTextResult = body.getReviewedText(Word.ChangeTrackingVersion.current);
      await context.sync();

      const revisedText = revisedTextResult.value;
      console.log('Revised text length:', revisedText.length);
      console.log('Revised text preview:', revisedText.substring(0, 200));
      console.log('=== END EXTRACTING REVISED TEXT ===');

      return revisedText;
    });
  }

  /**
   * Helper to convert change tracking mode enum to string
   */
  private getChangeTrackingModeString(mode: any): 'Off' | 'TrackAll' | 'TrackMineOnly' {
    if (!Word) return 'Off';

    switch (mode) {
      case Word.ChangeTrackingMode.trackAll:
        return 'TrackAll';
      case Word.ChangeTrackingMode.trackMineOnly:
        return 'TrackMineOnly';
      case Word.ChangeTrackingMode.off:
      default:
        return 'Off';
    }
  }
}
