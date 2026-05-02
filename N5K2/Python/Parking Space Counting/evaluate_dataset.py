"""
Dataset Statistics Collector
Analyzes the parking space dataset and generates statistics
"""

import os
import json
from pathlib import Path
from collections import defaultdict

# Configuration
DATASET_DIR = 'dataset'
OUTPUT_FILE = 'dataset_stats.json'

def count_files_in_dir(directory):
    """Count number of files in a directory"""
    if not os.path.exists(directory):
        return 0
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])

def analyze_dataset():
    """Analyze dataset structure and collect statistics"""
    stats = {
        'total_samples': 0,
        'splits': {},
        'class_distribution': {
            'empty': 0,
            'occupied': 0
        }
    }
    
    splits = ['train', 'val', 'test']
    classes = ['empty', 'occupied']
    
    for split in splits:
        stats['splits'][split] = {
            'total': 0,
            'empty': 0,
            'occupied': 0
        }
        
        for cls in classes:
            dir_path = os.path.join(DATASET_DIR, split, cls)
            count = count_files_in_dir(dir_path)
            
            stats['splits'][split][cls] = count
            stats['splits'][split]['total'] += count
            stats['class_distribution'][cls] += count
            stats['total_samples'] += count
    
    # Calculate percentages
    for split in splits:
        total = stats['splits'][split]['total']
        if total > 0:
            stats['splits'][split]['empty_percent'] = round(stats['splits'][split]['empty'] / total * 100, 2)
            stats['splits'][split]['occupied_percent'] = round(stats['splits'][split]['occupied'] / total * 100, 2)
    
    total = stats['total_samples']
    if total > 0:
        stats['class_distribution']['empty_percent'] = round(stats['class_distribution']['empty'] / total * 100, 2)
        stats['class_distribution']['occupied_percent'] = round(stats['class_distribution']['occupied'] / total * 100, 2)
    
    return stats

def print_stats(stats):
    """Print statistics in formatted way"""
    print('='*70)
    print('DATASET STATISTICS')
    print('='*70)
    print(f'\nTotal samples: {stats["total_samples"]}')
    
    print('\n--- Class Distribution (Overall) ---')
    print(f'Empty:    {stats["class_distribution"]["empty"]:5d} ({stats["class_distribution"]["empty_percent"]:5.2f}%)')
    print(f'Occupied: {stats["class_distribution"]["occupied"]:5d} ({stats["class_distribution"]["occupied_percent"]:5.2f}%)')
    
    print('\n--- Split Statistics ---')
    for split in ['train', 'val', 'test']:
        split_stats = stats['splits'][split]
        print(f'\n{split.upper()}:')
        print(f'  Total:    {split_stats["total"]:5d}')
        print(f'  Empty:    {split_stats["empty"]:5d} ({split_stats.get("empty_percent", 0):5.2f}%)')
        print(f'  Occupied: {split_stats["occupied"]:5d} ({split_stats.get("occupied_percent", 0):5.2f}%)')
    
    print('\n' + '='*70)

if __name__ == '__main__':
    print('Analyzing dataset...\n')
    
    stats = analyze_dataset()
    print_stats(stats)
    
    # Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f'\n✓ Statistics saved to: {OUTPUT_FILE}')
