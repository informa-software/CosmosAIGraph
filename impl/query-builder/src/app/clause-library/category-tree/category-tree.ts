import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ClauseLibraryService, Category } from '../../shared/services/clause-library.service';
import { ToastService } from '../../shared/services/toast.service';

interface TreeNode {
  category: Category;
  children: TreeNode[];
  isExpanded: boolean;
  level: number;
}

@Component({
  selector: 'app-category-tree',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './category-tree.html',
  styleUrl: './category-tree.scss'
})
export class CategoryTreeComponent implements OnInit {
  @Output() categorySelected = new EventEmitter<string>();

  // Data
  categories: Category[] = [];
  treeNodes: TreeNode[] = [];
  selectedCategoryId: string | null = null;

  // UI State
  isLoading = false;

  constructor(
    private clauseLibraryService: ClauseLibraryService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.loadCategories();
  }

  /**
   * Load categories and build tree structure
   */
  loadCategories(): void {
    this.isLoading = true;

    this.clauseLibraryService.getCategories().subscribe({
      next: (response) => {
        this.categories = response.categories;
        this.buildTree();
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading categories:', error);
        this.toastService.error('Error', 'Failed to load categories');
        this.isLoading = false;
      }
    });
  }

  /**
   * Build hierarchical tree structure from flat category list
   */
  buildTree(): void {
    // Create a map for quick lookup
    const categoryMap = new Map<string, TreeNode>();

    // First pass: create tree nodes for all categories
    this.categories.forEach(category => {
      categoryMap.set(category.id, {
        category,
        children: [],
        isExpanded: category.level === 0, // Auto-expand root level
        level: category.level
      });
    });

    // Second pass: build parent-child relationships
    const rootNodes: TreeNode[] = [];

    this.categories.forEach(category => {
      const node = categoryMap.get(category.id);
      if (!node) return;

      if (category.parent_id === null) {
        // Root level category
        rootNodes.push(node);
      } else {
        // Child category - add to parent's children
        const parentNode = categoryMap.get(category.parent_id);
        if (parentNode) {
          parentNode.children.push(node);
        }
      }
    });

    // Sort children by order or name
    const sortNodes = (nodes: TreeNode[]) => {
      nodes.sort((a, b) => {
        const orderA = a.category.order ?? 999;
        const orderB = b.category.order ?? 999;
        if (orderA !== orderB) {
          return orderA - orderB;
        }
        return a.category.name.localeCompare(b.category.name);
      });

      // Recursively sort children
      nodes.forEach(node => {
        if (node.children.length > 0) {
          sortNodes(node.children);
        }
      });
    };

    sortNodes(rootNodes);
    this.treeNodes = rootNodes;
  }

  /**
   * Toggle node expansion
   */
  toggleNode(node: TreeNode): void {
    node.isExpanded = !node.isExpanded;
  }

  /**
   * Select a category
   */
  selectCategory(node: TreeNode): void {
    this.selectedCategoryId = node.category.id;
    this.categorySelected.emit(node.category.id);
  }

  /**
   * Clear selection (show all clauses)
   */
  clearSelection(): void {
    this.selectedCategoryId = null;
    this.categorySelected.emit('');
  }

  /**
   * Check if category is selected
   */
  isSelected(node: TreeNode): boolean {
    return this.selectedCategoryId === node.category.id;
  }

  /**
   * Get icon for category
   */
  getIcon(category: Category): string {
    const iconName = category.icon;

    // If no icon or already an emoji, return as-is
    if (!iconName || this.isEmoji(iconName)) {
      return iconName || '📁';
    }

    // Map Material Icons names to emojis
    const iconMap: { [key: string]: string } = {
      // Security & Protection
      'shield': '🛡️',
      'security': '🔒',
      'lock': '🔒',
      'security_update_warning': '⚠️',
      'verified': '✅',

      // Insurance & Financial
      'medical_services': '🏥',
      'public': '👥',
      'directions_car': '🚗',
      'umbrella': '☂️',
      'payment': '💰',

      // Legal & Compliance
      'gavel': '⚖️',
      'warning': '⚠️',

      // Process & Actions
      'swap_horiz': '↔️',
      'arrow_upward': '⬆️',
      'refresh': '🔄',
      'cancel': '❌',
      'trending_up': '📈',

      // General
      'folder': '📁',
      'description': '📄',
      'document': '📄',
      'file': '📄',
      'category': '📂',
      'work': '💼',
      'business': '🏢',
      'contract': '📋',
      'legal': '⚖️',
      'clause': '📜',
      'terms': '📝',
      'agreement': '🤝'
    };

    return iconMap[iconName] || '📁';
  }

  /**
   * Check if string is an emoji
   */
  private isEmoji(str: string): boolean {
    // Simple emoji detection - checks if string contains emoji characters
    const emojiRegex = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    return emojiRegex.test(str);
  }

  /**
   * Get indentation style for tree level
   */
  getIndentStyle(level: number): any {
    return {
      'padding-left': `${level * 20}px`
    };
  }

  /**
   * Expand all nodes
   */
  expandAll(): void {
    const expandRecursive = (nodes: TreeNode[]) => {
      nodes.forEach(node => {
        node.isExpanded = true;
        if (node.children.length > 0) {
          expandRecursive(node.children);
        }
      });
    };
    expandRecursive(this.treeNodes);
  }

  /**
   * Collapse all nodes
   */
  collapseAll(): void {
    const collapseRecursive = (nodes: TreeNode[]) => {
      nodes.forEach(node => {
        node.isExpanded = false;
        if (node.children.length > 0) {
          collapseRecursive(node.children);
        }
      });
    };
    collapseRecursive(this.treeNodes);
  }
}
