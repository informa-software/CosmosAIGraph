import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { UserPreferencesService, ModelPreference, UserPreferences } from '../shared/services/user-preferences.service';
import { ToastService } from '../shared/services/toast.service';
import { ModelSelectorComponent } from '../shared/components/model-selector/model-selector';

@Component({
  selector: 'app-preferences',
  standalone: true,
  imports: [CommonModule, FormsModule, ModelSelectorComponent],
  templateUrl: './preferences.component.html',
  styleUrls: ['./preferences.component.scss']
})
export class PreferencesComponent implements OnInit {
  // State
  isLoading = false;
  isSaving = false;
  preferences: UserPreferences | null = null;

  // Form model
  selectedModel: string = 'primary';
  autoSelect: boolean = false;
  costOptimization: boolean = false;

  // User email - matches backend LLM tracking (system user until auth is implemented)
  userEmail: string = 'system';

  constructor(
    private userPreferencesService: UserPreferencesService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.userEmail = this.userPreferencesService.getCurrentUserEmail();
    this.loadPreferences();
  }

  /**
   * Load user preferences from backend
   */
  loadPreferences(): void {
    this.isLoading = true;

    this.userPreferencesService.getModelPreference(this.userEmail).subscribe({
      next: (prefs) => {
        this.preferences = prefs;

        // Populate form with loaded preferences
        if (prefs.model_preference) {
          this.selectedModel = prefs.model_preference.default_model;
          this.autoSelect = prefs.model_preference.auto_select;
          this.costOptimization = prefs.model_preference.cost_optimization;
        }

        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading preferences:', error);
        this.toastService.error('Load Failed', 'Failed to load user preferences.');
        this.isLoading = false;
      }
    });
  }

  /**
   * Handle model selection change
   */
  onModelChange(model: string): void {
    this.selectedModel = model;
  }

  /**
   * Save preferences to backend
   */
  savePreferences(): void {
    this.isSaving = true;

    const preference: ModelPreference = {
      default_model: this.selectedModel,
      auto_select: this.autoSelect,
      cost_optimization: this.costOptimization
    };

    this.userPreferencesService.saveModelPreference(this.userEmail, preference).subscribe({
      next: () => {
        this.isSaving = false;
        this.toastService.success('Saved', 'Your preferences have been saved successfully.');
      },
      error: (error) => {
        console.error('Error saving preferences:', error);
        this.isSaving = false;
        this.toastService.error('Save Failed', 'Failed to save preferences. Please try again.');
      }
    });
  }

  /**
   * Reset preferences to default
   */
  resetToDefaults(): void {
    if (confirm('Are you sure you want to reset all preferences to default values?')) {
      this.selectedModel = 'primary';
      this.autoSelect = false;
      this.costOptimization = false;

      this.savePreferences();
    }
  }

  /**
   * Navigate back to contract workbench
   */
  goBack(): void {
    this.router.navigate(['/']);
  }
}
