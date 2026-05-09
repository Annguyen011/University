"""
Visualization Generator
Creates charts, confusion matrices, and comparison tables for the report
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
from matplotlib import font_manager

# Configuration
DATASET_STATS_FILE = 'dataset_stats.json'
MODEL_EVAL_FILE = 'model_evaluation.json'
OUTPUT_DIR = 'report_assets'

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

def plot_confusion_matrix(cm, model_name, output_path):
    """Plot confusion matrix"""
    fig, ax = plt.subplots(figsize=(6, 5))
    
    # Create heatmap with matplotlib
    im = ax.imshow(cm, cmap='Blues', aspect='auto')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Count', rotation=270, labelpad=15)
    
    # Set ticks and labels
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Empty', 'Occupied'])
    ax.set_yticklabels(['Empty', 'Occupied'])
    
    # Add text annotations
    for i in range(2):
        for j in range(2):
            text = ax.text(j, i, str(cm[i, j]),
                          ha="center", va="center", color="black" if cm[i, j] < cm.max()/2 else "white",
                          fontsize=14, fontweight='bold')
    
    plt.title(f'Confusion Matrix - {model_name}', fontsize=14, fontweight='bold')
    plt.ylabel('Actual', fontsize=12)
    plt.xlabel('Predicted', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Created: {output_path}")

def plot_comparison_chart(evaluation_data, output_path):
    """Plot comparison bar chart of all metrics"""
    models = list(evaluation_data.keys())
    metrics = ['accuracy', 'precision', 'recall', 'f1_score']
    
    # Prepare data
    data = {metric: [] for metric in metrics}
    for model in models:
        for metric in metrics:
            data[metric].append(evaluation_data[model].get(metric, 0))
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(models))
    width = 0.2
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for i, (metric, color) in enumerate(zip(metrics, colors)):
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, data[metric], width, 
                     label=metric.replace('_', ' ').title(),
                     color=color)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}',
                   ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel('Models', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace('_', ' ').title() for m in models])
    ax.legend(loc='lower right')
    ax.set_ylim(0, 1.1)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Created: {output_path}")

def plot_comparison_table(evaluation_data, output_path):
    """Create comparison table as image"""
    models = list(evaluation_data.keys())
    
    # Prepare data
    rows = []
    for model in models:
        row = [
            model.replace('_', ' ').title(),
            f"{evaluation_data[model].get('accuracy', 0):.4f}",
            f"{evaluation_data[model].get('precision', 0):.4f}",
            f"{evaluation_data[model].get('recall', 0):.4f}",
            f"{evaluation_data[model].get('f1_score', 0):.4f}",
            f"{evaluation_data[model].get('fps', 0):.1f}"
        ]
        rows.append(row)
    
    # Create table
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.axis('tight')
    ax.axis('off')
    
    columns = ['Model', 'Accuracy', 'Precision', 'Recall', 'F1-Score', 'FPS']
    
    table = ax.table(cellText=rows, colLabels=columns, 
                    cellLoc='center', loc='center',
                    colWidths=[0.2, 0.16, 0.16, 0.16, 0.16, 0.16])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Style header
    for i in range(len(columns)):
        cell = table[(0, i)]
        cell.set_facecolor('#4472C4')
        cell.set_text_props(weight='bold', color='white')
    
    # Style data rows
    for i in range(1, len(rows) + 1):
        for j in range(len(columns)):
            cell = table[(i, j)]
            if i % 2 == 0:
                cell.set_facecolor('#E7E6E6')
            else:
                cell.set_facecolor('#FFFFFF')
    
    plt.title('Model Comparison Summary', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Created: {output_path}")

def plot_fps_comparison(evaluation_data, output_path):
    """Plot FPS comparison"""
    models = list(evaluation_data.keys())
    fps_values = [evaluation_data[model].get('fps', 0) for model in models]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    bars = ax.bar(range(len(models)), fps_values, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}',
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Models', fontsize=12, fontweight='bold')
    ax.set_ylabel('Frames Per Second (FPS)', fontsize=12, fontweight='bold')
    ax.set_title('Inference Speed Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([m.replace('_', ' ').title() for m in models])
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Created: {output_path}")

def plot_dataset_distribution(dataset_stats, output_path):
    """Plot dataset distribution"""
    splits = ['train', 'val', 'test']
    empty_counts = [dataset_stats['splits'][split]['empty'] for split in splits]
    occupied_counts = [dataset_stats['splits'][split]['occupied'] for split in splits]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(splits))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, empty_counts, width, label='Empty', color='#2ca02c')
    bars2 = ax.bar(x + width/2, occupied_counts, width, label='Occupied', color='#d62728')
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Dataset Split', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Samples', fontsize=12, fontweight='bold')
    ax.set_title('Dataset Distribution', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([s.upper() for s in splits])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Created: {output_path}")

if __name__ == '__main__':
    print('='*70)
    print('GENERATING VISUALIZATIONS')
    print('='*70)
    
    # Load data
    print('\nLoading evaluation data...')
    
    if not os.path.exists(MODEL_EVAL_FILE):
        print(f"Error: {MODEL_EVAL_FILE} not found!")
        print("Please run evaluate_models.py first")
        exit(1)
    
    with open(MODEL_EVAL_FILE, 'r', encoding='utf-8') as f:
        evaluation_data = json.load(f)
    
    # Load dataset stats if available
    dataset_stats = None
    if os.path.exists(DATASET_STATS_FILE):
        with open(DATASET_STATS_FILE, 'r', encoding='utf-8') as f:
            dataset_stats = json.load(f)
    
    print('\nGenerating visualizations...\n')
    
    # 1. Confusion matrices
    for model_name in evaluation_data.keys():
        if 'confusion_matrix' in evaluation_data[model_name]:
            cm = np.array(evaluation_data[model_name]['confusion_matrix'])
            output_path = os.path.join(OUTPUT_DIR, f'confusion_matrix_{model_name}.png')
            plot_confusion_matrix(cm, model_name.replace('_', ' ').title(), output_path)
    
    # 2. Comparison chart
    output_path = os.path.join(OUTPUT_DIR, 'comparison_chart.png')
    plot_comparison_chart(evaluation_data, output_path)
    
    # 3. Comparison table
    output_path = os.path.join(OUTPUT_DIR, 'comparison_table.png')
    plot_comparison_table(evaluation_data, output_path)
    
    # 4. FPS comparison
    output_path = os.path.join(OUTPUT_DIR, 'fps_comparison.png')
    plot_fps_comparison(evaluation_data, output_path)
    
    # 5. Dataset distribution
    if dataset_stats:
        output_path = os.path.join(OUTPUT_DIR, 'dataset_distribution.png')
        plot_dataset_distribution(dataset_stats, output_path)
    
    print('\n' + '='*70)
    print(f'✓ All visualizations saved to: {OUTPUT_DIR}/')
    print('='*70)
