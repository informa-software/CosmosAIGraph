/**
 * Word Service for Office.js interactions
 * Handles extracting text and interacting with Word documents
 */

import { Injectable } from '@angular/core';

declare const Word: any;

@Injectable({
  providedIn: 'root'
})
export class WordService {

  constructor() {}

  /**
   * Check if we're running in Word context
   */
  isWordAvailable(): boolean {
    return typeof Word !== 'undefined' && typeof Word.run === 'function';
  }

  /**
   * Extract all text from the current Word document
   */
  async getDocumentText(): Promise<string> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      // Get the body of the document
      const body = context.document.body;

      // Load the text property
      body.load('text');

      // Sync to execute the queued commands
      await context.sync();

      // Return the text
      return body.text;
    });
  }

  /**
   * Get document metadata (properties)
   */
  async getDocumentProperties(): Promise<{
    title: string;
    subject: string;
    author: string;
    lastModifiedDate?: Date;
  }> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      const properties = context.document.properties;

      properties.load('title,subject,author,lastModified');

      await context.sync();

      return {
        title: properties.title || 'Untitled',
        subject: properties.subject || '',
        author: properties.author || '',
        lastModifiedDate: properties.lastModified
      };
    });
  }

  /**
   * Insert text at the current cursor position or replace selected text
   * Returns information about what was done
   */
  async insertTextAtSelection(text: string): Promise<{ replaced: boolean; selectedText: string }> {
    console.log(`📝 insertTextAtSelection() - Inserting text: "${text.substring(0, 50)}..."`);

    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      const selection = context.document.getSelection();
      selection.load('text');
      await context.sync();

      const selectedText = selection.text;
      const replaced = selectedText.length > 0;

      console.log(`📝 Current selection: "${selectedText}"`);
      console.log(`📝 Action: ${replaced ? 'Replacing selected text' : 'Inserting at cursor'}`);

      // Replace will replace selected text, or insert at cursor if nothing is selected
      selection.insertText(text, Word.InsertLocation.replace);

      await context.sync();
      console.log('📝 insertTextAtSelection() - Complete');

      return { replaced, selectedText };
    });
  }

  /**
   * Insert text at the current cursor position (legacy method)
   */
  async insertText(text: string): Promise<void> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      const selection = context.document.getSelection();
      selection.insertText(text, Word.InsertLocation.end);

      await context.sync();
    });
  }

  /**
   * Highlight text in the document using content controls
   * Content controls don't trigger track changes when properly configured
   */
  async highlightText(searchText: string, highlightColor: string = 'yellow'): Promise<number> {
    console.log(`✨ highlightText() - Searching for: "${searchText.substring(0, 50)}..."`);

    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      // Search for the text in the document
      const searchResults = context.document.body.search(searchText, {
        matchCase: false,
        matchWholeWord: false
      });

      searchResults.load('items');
      await context.sync();

      const count = searchResults.items.length;
      console.log(`✨ Found ${count} occurrence(s) of the search text`);

      let firstContentControl: any = null;

      // Wrap each occurrence in a content control
      for (let i = 0; i < count; i++) {
        const range = searchResults.items[i];
        range.load('text');
        await context.sync();

        console.log(`✨ Creating content control [${i}] for text: "${range.text}"`);

        // Insert a content control around the found text
        const contentControl = range.insertContentControl();

        // Set appearance - BoundingBox shows a clear border
        contentControl.appearance = Word.ContentControlAppearance.boundingBox;

        // Set light blue color for the bounding box
        contentControl.color = '#87CEEB'; // Sky blue - more visible than #ADD8E6

        // Set title (shows in content control header when selected)
        contentControl.title = 'Analysis Highlight';

        // Set tag for identification and removal
        contentControl.tag = 'analysis-highlight';

        // Allow editing of the content
        contentControl.cannotEdit = false;

        // Don't modify font properties - that triggers track changes
        // The bounding box appearance and color provide the visual indicator

        // Keep track of the first content control to select it
        if (i === 0) {
          firstContentControl = contentControl;
          console.log('✨ Saved first content control for selection');
        }
      }

      await context.sync();
      console.log(`✨ Created ${count} content control(s)`);

      // Verify content controls were created and persisted
      const allContentControls = context.document.contentControls;
      allContentControls.load('tag, title');
      await context.sync();
      console.log(`✨ Verification: Found ${allContentControls.items.length} total content controls in document`);
      const highlightControls = allContentControls.items.filter((cc: any) => cc.tag === 'analysis-highlight');
      console.log(`✨ Verification: Found ${highlightControls.length} analysis-highlight content controls`);

      // Select the first highlighted content control so it's visible immediately
      if (firstContentControl) {
        console.log('✨ Selecting first content control...');
        const range = firstContentControl.getRange();
        range.select();
        await context.sync();
        console.log('✨ First content control selected');
      }

      console.log('✨ highlightText() - Complete');
      return count;
    });
  }

  /**
   * Clear all analysis highlights (content controls) from the document
   * Removes the content control but preserves the text inside
   */
  async clearHighlighting(): Promise<void> {
    console.log('🧹 clearHighlighting() - Starting to clear highlights...');

    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      // IMPORTANT: Move the cursor to document start to deselect any content controls
      // This prevents issues when deleting content controls with selected text
      console.log('🧹 Moving cursor to document start...');
      const docStart = context.document.body.getRange(Word.RangeLocation.start);
      docStart.select();
      await context.sync();
      console.log('🧹 Cursor moved to document start');

      const contentControls = context.document.contentControls;
      contentControls.load('tag, text, title');
      await context.sync();

      console.log(`🧹 Found ${contentControls.items.length} total content controls`);

      // Remove all content controls with the analysis-highlight tag
      // delete(true) = Delete the content control and keep its contents
      let deletedCount = 0;
      for (let i = contentControls.items.length - 1; i >= 0; i--) {
        const cc = contentControls.items[i];
        console.log(`🧹 Content control [${i}]: tag="${cc.tag}", title="${cc.title}", text="${cc.text.substring(0, 50)}..."`);

        if (cc.tag === 'analysis-highlight') {
          console.log(`🧹 Deleting content control [${i}] with text: "${cc.text}"`);
          cc.delete(true); // true = delete control and keep contents
          deletedCount++;
        }
      }

      await context.sync();
      console.log(`🧹 Successfully deleted ${deletedCount} content controls`);
      console.log('🧹 clearHighlighting() - Complete');
    });
  }

  /**
   * Get selected text
   */
  async getSelectedText(): Promise<string> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      const selection = context.document.getSelection();
      selection.load('text');

      await context.sync();

      return selection.text;
    });
  }

  /**
   * Get document statistics
   */
  async getDocumentStats(): Promise<{
    characterCount: number;
    wordCount: number;
    paragraphCount: number;
  }> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      const body = context.document.body;

      body.load('text');
      const paragraphs = body.paragraphs;
      paragraphs.load('items');

      await context.sync();

      const text = body.text;
      const wordCount = text.trim().split(/\s+/).length;

      return {
        characterCount: text.length,
        wordCount: wordCount,
        paragraphCount: paragraphs.items.length
      };
    });
  }

  /**
   * Replace text in the document
   * Searches for originalText and replaces it with replacementText
   * Returns the number of replacements made
   */
  async replaceText(originalText: string, replacementText: string): Promise<number> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      // Search for the original text in the document body
      const searchResults = context.document.body.search(originalText, {
        matchCase: false,
        matchWholeWord: false
      });

      searchResults.load('items');
      await context.sync();

      // Replace each occurrence
      const count = searchResults.items.length;
      for (let i = 0; i < count; i++) {
        searchResults.items[i].insertText(replacementText, Word.InsertLocation.replace);
      }

      await context.sync();

      return count;
    });
  }

  /**
   * Replace text within content controls that have the 'analysis-highlight' tag
   * This keeps the content control but updates its content
   * The text is selected after replacement, simulating a user selection
   * If track changes is enabled, the replacement will be tracked for review
   * Returns the number of replacements made
   */
  async replaceTextInContentControl(originalText: string, replacementText: string): Promise<number> {
    if (!this.isWordAvailable()) {
      throw new Error('Word.js is not available');
    }

    return Word.run(async (context: any) => {
      // Get all content controls with the analysis-highlight tag
      const contentControls = context.document.contentControls;
      contentControls.load('tag, text');
      await context.sync();

      let replacementCount = 0;
      let lastReplacedRange: any = null;

      // Find and replace text in matching content controls
      for (let i = 0; i < contentControls.items.length; i++) {
        const cc = contentControls.items[i];

        if (cc.tag === 'analysis-highlight') {
          // Check if this content control contains the original text
          const ccText = cc.text;

          if (ccText.toLowerCase().includes(originalText.toLowerCase())) {
            // Get the range of the content control
            const range = cc.getRange();

            // First, select the original text (simulates user selecting with mouse)
            range.select();
            await context.sync();

            // Now insert the replacement text at the selection
            // This will properly trigger track changes as if the user typed it
            range.insertText(replacementText, Word.InsertLocation.replace);

            // Keep track of the last replaced range to select it at the end
            lastReplacedRange = range;

            replacementCount++;
          }
        }
      }

      await context.sync();

      // Select the last replaced text so user can see it
      if (lastReplacedRange) {
        lastReplacedRange.select();
        await context.sync();
      }

      return replacementCount;
    });
  }
}
