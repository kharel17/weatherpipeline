"""
Quick script to create the necessary directory structure
Run this if you get directory-related errors
"""

import os
from pathlib import Path

def create_project_directories():
    """Create all necessary directories for the project"""
    
    base_dir = Path(".")
    
    # Directories to create
    directories = [
        "data",
        "data/logs",
        "data/csv_exports", 
        "data/json_exports",
        "etl",
        "models",
        "utils",
        "frontend",
        "frontend/templates",
        "frontend/static",
        "frontend/static/css",
        "frontend/static/js"
    ]
    
    print("Creating project directories...")
    
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Create __init__.py files for Python packages
    init_files = [
        "etl/__init__.py",
        "models/__init__.py", 
        "utils/__init__.py"
    ]
    
    print("\nCreating __init__.py files...")
    
    for init_file in init_files:
        init_path = base_dir / init_file
        if not init_path.exists():
            init_path.touch()
            print(f"✅ Created: {init_file}")
        else:
            print(f"📁 Already exists: {init_file}")
    
    print("\n🎉 Directory structure created successfully!")
    print("\nYour project structure is now ready. You can run the ETL tests.")

if __name__ == "__main__":
    create_project_directories()