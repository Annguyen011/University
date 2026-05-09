"""
Master Script - Run Full Evaluation and Report Generation Pipeline
"""

import subprocess
import sys
import os

def run_script(script_name, description):
    """Run a Python script and report status"""
    print('\n' + '='*70)
    print(f'RUNNING: {description}')
    print('='*70)
    print(f'Script: {script_name}\n')
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        if result.returncode == 0:
            print(f'\n✓ {description} completed successfully')
            return True
        else:
            print(f'\n✗ {description} failed with return code {result.returncode}')
            return False
    except Exception as e:
        print(f'\n✗ Error running {script_name}: {e}')
        return False

def main():
    print('='*70)
    print('PARKING SPACE COUNTING - AUTOMATED EVALUATION PIPELINE')
    print('='*70)
    print('\nThis script will:')
    print('  1. Analyze dataset statistics')
    print('  2. Evaluate models (Traditional CV, SVM)')
    print('  3. Generate visualizations')
    print('  4. Create comprehensive report')
    print('')
    input('Press Enter to start...')
    
    # Check if dataset exists
    if not os.path.exists('dataset'):
        print('\n✗ Error: dataset/ directory not found!')
        print('Please run create_dataset.py first to create the dataset.')
        return
    
    # Step 1: Evaluate dataset
    if not run_script('evaluate_dataset.py', 'Step 1: Dataset Analysis'):
        print('\nPipeline stopped due to error')
        return
    
    # Step 2: Evaluate models
    if not run_script('evaluate_models.py', 'Step 2: Model Evaluation'):
        print('\nPipeline stopped due to error')
        return
    
    # Step 3: Generate visualizations
    if not run_script('generate_visualizations.py', 'Step 3: Visualization Generation'):
        print('\nWarning: Visualization generation had issues, but continuing...')
    
    # Step 4: Generate report
    if not run_script('generate_report.py', 'Step 4: Report Generation'):
        print('\nPipeline stopped due to error')
        return
    
    print('\n' + '='*70)
    print('✓ PIPELINE COMPLETED SUCCESSFULLY!')
    print('='*70)
    print('\nGenerated files:')
    print('  - dataset_stats.json')
    print('  - model_evaluation.json')
    print('  - report_assets/ (visualizations)')
    print('  - REPORT.md (final report)')
    print('\nNext step: Open REPORT.md to view the comprehensive report')
    print('='*70)

if __name__ == '__main__':
    main()
