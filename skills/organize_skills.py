#!/usr/bin/env python3
"""
Main script to organize skills files.
Parses multiple skill files, merges and deduplicates them,
and generates organized JSON output files.
"""

import shutil
from pathlib import Path
from typing import List

import parsers
import skill_merger
import output_generator


def setup_folders(base_path: Path) -> None:
    """
    Create input and output folders, move files to input.
    
    Args:
        base_path: Base path for skills directory
    """
    input_dir = base_path / "input"
    output_dir = base_path / "output"
    
    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    print("✓ Folders created: input/ and output/")
    
    # Move existing files to input/ (skip if already moved)
    if not any(input_dir.glob("*")):
        files_moved = 0
        for file in base_path.glob("*.json"):
            if file.name not in {"parsers.py", "skill_merger.py", "output_generator.py", "organize_skills.py"}:
                shutil.move(str(file), str(input_dir / file.name))
                files_moved += 1
        for file in base_path.glob("*.txt"):
            if file.name != "organize_skills.py":
                shutil.move(str(file), str(input_dir / file.name))
                files_moved += 1
        
        if files_moved > 0:
            print(f"✓ Moved {files_moved} files to input/")


def parse_all_files(input_dir: Path) -> tuple:
    """
    Parse all skill files from input directory.
    
    Args:
        input_dir: Path to input directory
        
    Returns:
        Tuple of (all_skills_list, favorite_skills_list)
    """
    all_skills = []
    favorite_skills = []
    
    print("\nParsing files...")
    
    # Parse skills_with_counts.json
    file_path = input_dir / "skills_with_counts.json"
    if file_path.exists():
        skills = parsers.parse_skills_with_counts(file_path)
        all_skills.append(skills)
        print(f"  ✓ Parsed skills_with_counts.json ({len(skills)} skills)")
    
    # Parse oreilly-skills-clean.txt
    file_path = input_dir / "oreilly-skills-clean.txt"
    if file_path.exists():
        skills = parsers.parse_skills_clean_txt(file_path)
        all_skills.append(skills)
        print(f"  ✓ Parsed oreilly-skills-clean.txt ({len(skills)} skills)")
    
    # Parse skills_facets.json
    file_path = input_dir / "skills_facets.json"
    if file_path.exists():
        skills = parsers.parse_skills_facets(file_path)
        all_skills.append(skills)
        print(f"  ✓ Parsed skills_facets.json ({len(skills)} skills)")
    
    # Parse oreilly-skills.json
    file_path = input_dir / "oreilly-skills.json"
    if file_path.exists():
        skills = parsers.parse_oreilly_skills_json(file_path)
        all_skills.append(skills)
        print(f"  ✓ Parsed oreilly-skills.json ({len(skills)} skills)")
    
    # Parse favorite skills JSON files
    for file_name in ["favorite_skills_with_counts.json", "favorite_skills_with_counts_matched.json"]:
        file_path = input_dir / file_name
        if file_path.exists():
            skills = parsers.parse_favorite_skills_json(file_path)
            favorite_skills.append(skills)
            print(f"  ✓ Parsed {file_name} ({len(skills)} favorites)")
    
    # Parse my_favorite_skills.txt
    file_path = input_dir / "my_favorite_skills.txt"
    if file_path.exists():
        skills = parsers.parse_favorite_skills_txt(file_path)
        favorite_skills.append(skills)
        print(f"  ✓ Parsed my_favorite_skills.txt ({len(skills)} favorites)")
    
    return all_skills, favorite_skills


def main():
    """Main execution function."""
    print("=" * 60)
    print("Organizing Skills Files")
    print("=" * 60)
    
    # Setup
    base_path = Path(__file__).parent
    setup_folders(base_path)
    
    # Parse files
    all_skills, favorite_skills = parse_all_files(base_path / "input")
    
    # Extract favorite skill names
    print("\nProcessing favorites...")
    favorite_names = skill_merger.extract_favorite_skill_names(favorite_skills)
    print(f"  ✓ Identified {len(favorite_names)} unique favorite skill names")
    
    # Merge skills
    print("\nMerging and deduplicating...")
    all_skills_flat = []
    for skill_list in all_skills:
        all_skills_flat.extend(skill_list)
    
    merged_skills = skill_merger.merge_skills(all_skills + favorite_skills, favorite_names)
    print(f"  ✓ Merged into {len(merged_skills)} unique skills")
    
    # Get sorted skills
    all_skills_sorted = skill_merger.get_all_skills_sorted(merged_skills)
    favorite_skills_sorted = skill_merger.get_favorite_skills_sorted(merged_skills)
    
    # Validate
    print("\nValidating data...")
    all_validation = output_generator.validate_skills(all_skills_sorted)
    favorite_validation = output_generator.validate_skills(favorite_skills_sorted)
    
    if all_validation["issues"]:
        print(f"  ⚠ Found {len(all_validation['issues'])} issues in all skills")
    else:
        print("  ✓ All skills validated")
    
    if favorite_validation["issues"]:
        print(f"  ⚠ Found {len(favorite_validation['issues'])} issues in favorite skills")
    else:
        print("  ✓ Favorite skills validated")
    
    # Generate output files
    print("\nGenerating output files...")
    output_dir = base_path / "output"
    
    # All skills
    output_all = output_dir / "all_skills_organized.json"
    output_generator.write_all_skills_json(
        all_skills_sorted,
        output_all,
        metadata=output_generator.generate_metadata(
            total_skills=len(all_skills_sorted),
            description="All skills with book counts from O'Reilly platform",
            additional_info={
                "source_files": [
                    "skills_with_counts.json",
                    "oreilly-skills-clean.txt",
                    "skills_facets.json",
                    "oreilly-skills.json"
                ]
            }
        )
    )
    
    # Favorite skills
    output_favorites = output_dir / "favorite_skills_organized.json"
    output_generator.write_favorite_skills_json(
        favorite_skills_sorted,
        output_favorites,
        metadata=output_generator.generate_metadata(
            total_skills=len(favorite_skills_sorted),
            description="Favorite skills with book counts from O'Reilly platform",
            additional_info={
                "source_files": [
                    "favorite_skills_with_counts.json",
                    "favorite_skills_with_counts_matched.json",
                    "my_favorite_skills.txt"
                ]
            }
        )
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total unique skills: {len(merged_skills):,}")
    print(f"Favorite skills: {len(favorite_skills_sorted):,}")
    print(f"\nOutput files created in: {output_dir}")
    print("  - all_skills_organized.json")
    print("  - favorite_skills_organized.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
