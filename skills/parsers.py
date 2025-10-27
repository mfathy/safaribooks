"""Parser module for various skill file formats."""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


def parse_skills_with_counts(file_path: Path) -> List[Tuple[str, int]]:
    """
    Parse skills_with_counts.json which has array format [skill, count, skill, count...].
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of tuples (skill_name, book_count)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    skills = []
    for i in range(0, len(data), 2):
        if i + 1 < len(data):
            skill_name = data[i]
            count = data[i + 1]
            if isinstance(skill_name, str) and isinstance(count, int):
                skills.append((skill_name, count))
    
    return skills


def parse_skills_clean_txt(file_path: Path) -> List[Tuple[str, int]]:
    """
    Parse oreilly-skills-clean.txt with format "Skill (count)".
    
    Args:
        file_path: Path to the text file
        
    Returns:
        List of tuples (skill_name, book_count)
    """
    skills = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Match pattern like "Skill Name (123)"
            match = re.match(r'^(.+?)\s+\((\d+)\)\s*$', line)
            if match:
                skill_name = match.group(1).strip()
                count = int(match.group(2))
                skills.append((skill_name, count))
    
    return skills


def parse_skills_facets(file_path: Path) -> List[Tuple[str, int]]:
    """
    Parse skills_facets.json which is a dictionary mapping.
    Note: This file doesn't have counts, so we return 0.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of tuples (skill_name, 0) since no counts available
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract skill names from dictionary keys or values
    skills = []
    for key, value in data.items():
        # Use the key as the skill name
        skills.append((key, 0))
    
    return skills


def parse_favorite_skills_json(file_path: Path) -> List[Tuple[str, int, bool]]:
    """
    Parse favorite skills JSON files with metadata and skills array.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of tuples (skill_name, book_count, is_favorite=True)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    skills = []
    if 'skills' in data:
        for skill in data['skills']:
            if 'title' in skill and 'books' in skill:
                skills.append((skill['title'], skill['books'], True))
    
    return skills


def parse_favorite_skills_txt(file_path: Path) -> List[Tuple[str, int, bool]]:
    """
    Parse plain text list of favorite skills.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        List of tuples (skill_name, 0, is_favorite=True)
    """
    skills = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                skills.append((line, 0, True))
    
    return skills


def parse_oreilly_skills_json(file_path: Path) -> List[Tuple[str, int]]:
    """
    Parse oreilly-skills.json which contains a list of skill names.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of tuples (skill_name, 0) since no counts available
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    skills = []
    if 'skills' in data:
        for skill in data['skills']:
            if isinstance(skill, str):
                skills.append((skill, 0))
    
    return skills
