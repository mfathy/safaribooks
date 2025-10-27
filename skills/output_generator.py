"""Output generator module for creating organized JSON files."""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from skill_merger import SkillData


def generate_metadata(
    total_skills: int,
    description: str = None,
    additional_info: dict = None
) -> dict:
    """
    Generate metadata for output files.
    
    Args:
        total_skills: Total number of skills
        description: Optional description
        additional_info: Optional additional metadata
        
    Returns:
        Metadata dictionary
    """
    metadata = {
        "total_skills": total_skills,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "description": description or "Organized skills with book counts"
    }
    
    if additional_info:
        metadata.update(additional_info)
    
    return metadata


def skill_to_dict(skill: SkillData) -> dict:
    """
    Convert SkillData object to dictionary format for JSON output.
    
    Args:
        skill: SkillData object
        
    Returns:
        Dictionary with title and books keys
    """
    return {
        "title": skill.name,
        "books": skill.count
    }


def write_all_skills_json(
    skills: List[SkillData],
    output_path: Path,
    metadata: dict = None
) -> None:
    """
    Write all skills to a JSON file.
    
    Args:
        skills: List of SkillData objects
        output_path: Path to output file
        metadata: Optional metadata dictionary
    """
    if metadata is None:
        metadata = generate_metadata(
            total_skills=len(skills),
            description="All skills with book counts from O'Reilly platform"
        )
    
    output_data = {
        "metadata": metadata,
        "skills": [skill_to_dict(skill) for skill in skills]
    }
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Created: {output_path} ({len(skills)} skills)")


def write_favorite_skills_json(
    skills: List[SkillData],
    output_path: Path,
    metadata: dict = None
) -> None:
    """
    Write favorite skills to a JSON file.
    
    Args:
        skills: List of favorite SkillData objects
        output_path: Path to output file
        metadata: Optional metadata dictionary
    """
    if metadata is None:
        metadata = generate_metadata(
            total_skills=len(skills),
            description="Favorite skills with book counts from O'Reilly platform"
        )
    
    output_data = {
        "metadata": metadata,
        "skills": [skill_to_dict(skill) for skill in skills]
    }
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Created: {output_path} ({len(skills)} favorite skills)")


def validate_skills(skills: List[SkillData]) -> dict:
    """
    Validate skills data and return report.
    
    Args:
        skills: List of SkillData objects
        
    Returns:
        Dictionary with validation results
    """
    report = {
        "total": len(skills),
        "with_zero_count": 0,
        "with_empty_name": 0,
        "issues": []
    }
    
    for i, skill in enumerate(skills):
        if skill.count <= 0:
            report["with_zero_count"] += 1
            report["issues"].append(f"Skill '{skill.name}' has count {skill.count}")
        
        if not skill.name or not skill.name.strip():
            report["with_empty_name"] += 1
            report["issues"].append(f"Empty skill name at index {i}")
    
    return report
