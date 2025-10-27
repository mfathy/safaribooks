"""Skill merger module for deduplication and consolidation."""

from dataclasses import dataclass
from typing import List, Set, Tuple, Dict
import re


@dataclass
class SkillData:
    """Data structure to hold skill information."""
    name: str
    count: int
    is_favorite: bool = False
    
    def __post_init__(self):
        """Normalize the skill name."""
        self.name = normalize_skill_name(self.name)


def normalize_skill_name(name: str) -> str:
    """
    Normalize skill names for consistent matching.
    
    Args:
        name: Raw skill name
        
    Returns:
        Normalized skill name
    """
    # Remove extra whitespace
    normalized = ' '.join(name.split())
    
    # Handle common variations
    # Convert forward slash variations
    normalized = re.sub(r'\s*/\s*', '/', normalized)
    normalized = re.sub(r'\s*-\s*', '-', normalized)
    
    # Remove trailing/leading special characters
    normalized = normalized.strip(' ,.-')
    
    return normalized


def merge_skills(skills_list: List[Tuple], favorite_skills: Set[str] = None) -> Dict[str, SkillData]:
    """
    Merge multiple lists of skills, keeping the highest count and marking favorites.
    
    Args:
        skills_list: List of skill lists with format:
                    - [(name, count), ...] for regular skills
                    - [(name, count, is_favorite), ...] for favorites
        favorite_skills: Set of skill names marked as favorites
        
    Returns:
        Dictionary mapping normalized skill names to SkillData objects
    """
    if favorite_skills is None:
        favorite_skills = set()
    
    merged = {}
    
    for skills in skills_list:
        for item in skills:
            is_favorite = False
            
            # Handle both (name, count) and (name, count, is_favorite) formats
            if len(item) == 3:
                name, count, is_favorite = item
            else:
                name, count = item
            
            normalized_name = normalize_skill_name(name)
            
            # Check if skill is in favorites set
            if name in favorite_skills or normalized_name in favorite_skills:
                is_favorite = True
            
            # Create or update skill data
            if normalized_name in merged:
                # Keep the higher count
                if count > merged[normalized_name].count:
                    merged[normalized_name].count = count
                # Mark as favorite if either source marked it
                if is_favorite:
                    merged[normalized_name].is_favorite = True
            else:
                merged[normalized_name] = SkillData(
                    name=normalized_name,
                    count=count,
                    is_favorite=is_favorite
                )
    
    return merged


def extract_favorite_skill_names(favorite_files_data: List) -> Set[str]:
    """
    Extract unique favorite skill names from favorite files.
    
    Args:
        favorite_files_data: List of skill data from favorite files
        
    Returns:
        Set of favorite skill names
    """
    favorite_names = set()
    
    for skills in favorite_files_data:
        for item in skills:
            if len(item) >= 1:
                name = item[0]
                normalized = normalize_skill_name(name)
                favorite_names.add(normalized)
                # Also add original name for matching
                favorite_names.add(name)
    
    return favorite_names


def get_all_skills_sorted(merged_skills: Dict[str, SkillData]) -> List[SkillData]:
    """
    Get all skills sorted by count (descending).
    
    Args:
        merged_skills: Dictionary of merged skills
        
    Returns:
        List of SkillData objects sorted by count descending
    """
    return sorted(
        merged_skills.values(),
        key=lambda x: (x.count, x.name),
        reverse=True
    )


def get_favorite_skills_sorted(merged_skills: Dict[str, SkillData]) -> List[SkillData]:
    """
    Get only favorite skills sorted by count (descending).
    
    Args:
        merged_skills: Dictionary of merged skills
        
    Returns:
        List of favorite SkillData objects sorted by count descending
    """
    favorites = [skill for skill in merged_skills.values() if skill.is_favorite]
    return sorted(
        favorites,
        key=lambda x: (x.count, x.name),
        reverse=True
    )
