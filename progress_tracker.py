#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progress Tracker Module
Comprehensive progress tracking with statistics, ETA, and visualization
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import uuid


class ProgressTracker:
    """Enhanced progress tracking with statistics and ETA"""
    
    def __init__(self, progress_file: str, session_type: str = "download"):
        self.progress_file = progress_file
        self.session_type = session_type  # "download" or "discovery"
        self.data = self._load_or_create_progress()
    
    def _load_or_create_progress(self) -> Dict:
        """Load existing progress or create new structure"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                
                # Upgrade old format to new format if needed
                if 'session' not in data:
                    data = self._upgrade_format(data)
                
                return data
            except Exception as e:
                print(f"Warning: Could not load progress file: {e}")
        
        # Create new progress structure
        return self._create_new_progress()
    
    def _create_new_progress(self) -> Dict:
        """Create new progress structure"""
        return {
            "session": {
                "start_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "status": "initialized",
                "session_id": str(uuid.uuid4()),
                "type": self.session_type
            },
            "overall_stats": {
                "total_skills": 0,
                "completed_skills": 0,
                "in_progress_skill": None,
                "failed_skills": 0,
                "skipped_skills": 0
            },
            "books_stats": {
                "total_books_discovered": 0,
                "downloaded_books": 0,
                "failed_books": 0,
                "skipped_books": 0
            },
            "performance": {
                "average_items_per_minute": 0.0,
                "estimated_time_remaining_minutes": 0,
                "total_elapsed_seconds": 0,
                "last_speed_check": datetime.now().isoformat()
            },
            "current_activity": {
                "current_skill": None,
                "current_skill_progress": "0/0",
                "current_item": None,
                "current_item_id": None
            },
            "completed_items": [],
            "failed_items": {},
            "skills_completed": [],
            "skills_pending": [],
            "checkpoints": []
        }
    
    def _upgrade_format(self, old_data: Dict) -> Dict:
        """Upgrade old progress format to new format"""
        new_data = self._create_new_progress()
        
        # Migrate old data
        if "downloaded" in old_data:
            new_data["completed_items"] = old_data["downloaded"]
            new_data["books_stats"]["downloaded_books"] = len(old_data["downloaded"])
        
        if "failed" in old_data:
            new_data["failed_items"] = old_data["failed"]
            new_data["books_stats"]["failed_books"] = len(old_data["failed"])
        
        if "timestamp" in old_data:
            new_data["session"]["last_update"] = datetime.fromtimestamp(old_data["timestamp"]).isoformat()
        
        return new_data
    
    def save(self):
        """Save progress to file"""
        self.data["session"]["last_update"] = datetime.now().isoformat()
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving progress: {e}")
    
    def start_session(self, total_skills: int = 0, total_books: int = 0):
        """Start a new session"""
        self.data["session"]["status"] = "in_progress"
        self.data["session"]["start_time"] = datetime.now().isoformat()
        self.data["overall_stats"]["total_skills"] = total_skills
        self.data["books_stats"]["total_books_discovered"] = total_books
        self.save()
    
    def pause_session(self):
        """Pause the current session"""
        self.data["session"]["status"] = "paused"
        self.save()
    
    def resume_session(self):
        """Resume a paused session"""
        self.data["session"]["status"] = "in_progress"
        self.save()
    
    def complete_session(self):
        """Mark session as completed"""
        self.data["session"]["status"] = "completed"
        self.save()
    
    def update_current_skill(self, skill_name: str, current: int, total: int):
        """Update current skill progress"""
        self.data["current_activity"]["current_skill"] = skill_name
        self.data["current_activity"]["current_skill_progress"] = f"{current}/{total}"
        self.data["overall_stats"]["in_progress_skill"] = skill_name
        self.save()
    
    def update_current_item(self, item_name: str, item_id: str):
        """Update current item being processed"""
        self.data["current_activity"]["current_item"] = item_name
        self.data["current_activity"]["current_item_id"] = item_id
        self.save()
    
    def add_completed_item(self, item_id: str):
        """Add a completed item"""
        if item_id not in self.data["completed_items"]:
            self.data["completed_items"].append(item_id)
            self.data["books_stats"]["downloaded_books"] = len(self.data["completed_items"])
        
        # Remove from failed if it was there
        if item_id in self.data["failed_items"]:
            del self.data["failed_items"][item_id]
            self.data["books_stats"]["failed_books"] = len(self.data["failed_items"])
        
        self._update_performance()
        self.save()
    
    def add_failed_item(self, item_id: str, error: str):
        """Add a failed item"""
        self.data["failed_items"][item_id] = error
        self.data["books_stats"]["failed_books"] = len(self.data["failed_items"])
        self.save()
    
    def complete_skill(self, skill_name: str):
        """Mark a skill as completed"""
        if skill_name not in self.data["skills_completed"]:
            self.data["skills_completed"].append(skill_name)
            self.data["overall_stats"]["completed_skills"] = len(self.data["skills_completed"])
        
        if skill_name in self.data["skills_pending"]:
            self.data["skills_pending"].remove(skill_name)
        
        self.data["current_activity"]["current_skill"] = None
        self.data["overall_stats"]["in_progress_skill"] = None
        self.save()
    
    def set_pending_skills(self, skills: List[str]):
        """Set the list of pending skills"""
        self.data["skills_pending"] = [s for s in skills if s not in self.data["skills_completed"]]
        self.save()
    
    def _update_performance(self):
        """Update performance statistics and ETA"""
        start_time = datetime.fromisoformat(self.data["session"]["start_time"])
        now = datetime.now()
        elapsed_seconds = (now - start_time).total_seconds()
        
        self.data["performance"]["total_elapsed_seconds"] = elapsed_seconds
        
        # Calculate speed (items per minute)
        completed_count = len(self.data["completed_items"])
        if elapsed_seconds > 0 and completed_count > 0:
            items_per_second = completed_count / elapsed_seconds
            items_per_minute = items_per_second * 60
            self.data["performance"]["average_items_per_minute"] = round(items_per_minute, 2)
            
            # Calculate ETA
            total_books = self.data["books_stats"]["total_books_discovered"]
            remaining_books = total_books - completed_count
            
            if items_per_minute > 0:
                remaining_minutes = remaining_books / items_per_minute
                self.data["performance"]["estimated_time_remaining_minutes"] = round(remaining_minutes)
            else:
                self.data["performance"]["estimated_time_remaining_minutes"] = 0
        
        self.data["performance"]["last_speed_check"] = now.isoformat()
    
    def create_checkpoint(self):
        """Create a progress checkpoint"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "completed_items": len(self.data["completed_items"]),
            "completed_skills": len(self.data["skills_completed"]),
            "failed_items": len(self.data["failed_items"])
        }
        
        self.data["checkpoints"].append(checkpoint)
        
        # Keep only last 10 checkpoints
        if len(self.data["checkpoints"]) > 10:
            self.data["checkpoints"] = self.data["checkpoints"][-10:]
        
        self.save()
    
    def get_progress_percentage(self) -> Tuple[float, float]:
        """Get progress percentages (skills, books)"""
        total_skills = self.data["overall_stats"]["total_skills"]
        completed_skills = self.data["overall_stats"]["completed_skills"]
        
        total_books = self.data["books_stats"]["total_books_discovered"]
        completed_books = self.data["books_stats"]["downloaded_books"]
        
        skills_percent = (completed_skills / total_skills * 100) if total_skills > 0 else 0
        books_percent = (completed_books / total_books * 100) if total_books > 0 else 0
        
        return skills_percent, books_percent
    
    def get_eta_string(self) -> str:
        """Get formatted ETA string"""
        eta_minutes = self.data["performance"]["estimated_time_remaining_minutes"]
        
        if eta_minutes <= 0:
            return "Calculating..."
        
        if eta_minutes < 60:
            return f"{eta_minutes}m"
        elif eta_minutes < 1440:  # Less than 24 hours
            hours = eta_minutes // 60
            minutes = eta_minutes % 60
            return f"{hours}h {minutes}m"
        else:  # Days
            days = eta_minutes // 1440
            hours = (eta_minutes % 1440) // 60
            return f"{days}d {hours}h"
    
    def get_elapsed_string(self) -> str:
        """Get formatted elapsed time string"""
        elapsed_seconds = self.data["performance"]["total_elapsed_seconds"]
        
        if elapsed_seconds < 60:
            return f"{int(elapsed_seconds)}s"
        elif elapsed_seconds < 3600:
            minutes = int(elapsed_seconds // 60)
            seconds = int(elapsed_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(elapsed_seconds // 3600)
            minutes = int((elapsed_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def get_completion_time(self) -> Optional[str]:
        """Get estimated completion time"""
        eta_minutes = self.data["performance"]["estimated_time_remaining_minutes"]
        
        if eta_minutes <= 0:
            return None
        
        completion_time = datetime.now() + timedelta(minutes=eta_minutes)
        
        # Format based on how far in the future
        if completion_time.date() == datetime.now().date():
            return f"Today at {completion_time.strftime('%H:%M')}"
        elif completion_time.date() == (datetime.now() + timedelta(days=1)).date():
            return f"Tomorrow at {completion_time.strftime('%H:%M')}"
        else:
            return completion_time.strftime('%Y-%m-%d %H:%M')
    
    def get_status_icon(self) -> str:
        """Get status icon"""
        status = self.data["session"]["status"]
        icons = {
            "initialized": "⏺️",
            "in_progress": "▶️",
            "paused": "⏸️",
            "completed": "✅",
            "failed": "❌"
        }
        return icons.get(status, "❓")
    
    def print_progress_bar(self, prefix: str, current: int, total: int, width: int = 50):
        """Print a progress bar"""
        if total == 0:
            percentage = 0
            filled = 0
        else:
            percentage = current / total
            filled = int(width * percentage)
        
        bar = "█" * filled + "░" * (width - filled)
        percent_str = f"{percentage * 100:.1f}%"
        
        print(f"{prefix}: [{bar}] {current:,}/{total:,} ({percent_str})")
    
    def print_summary(self):
        """Print a comprehensive progress summary"""
        print(f"\n{'='*60}")
        print(f"📊 {self.session_type.upper()} PROGRESS SUMMARY")
        print(f"{'='*60}\n")
        
        # Status
        status_icon = self.get_status_icon()
        status = self.data["session"]["status"].upper()
        print(f"Status: {status_icon}  {status}")
        
        # Last activity
        last_update = datetime.fromisoformat(self.data["session"]["last_update"])
        time_since = datetime.now() - last_update
        if time_since.total_seconds() < 60:
            time_str = f"{int(time_since.total_seconds())} seconds ago"
        elif time_since.total_seconds() < 3600:
            time_str = f"{int(time_since.total_seconds() // 60)} minutes ago"
        else:
            time_str = f"{int(time_since.total_seconds() // 3600)} hours ago"
        print(f"Last Activity: {time_str}\n")
        
        # Overall progress
        print("Overall Progress:")
        
        # Skills progress
        total_skills = self.data["overall_stats"]["total_skills"]
        completed_skills = self.data["overall_stats"]["completed_skills"]
        skills_percent, books_percent = self.get_progress_percentage()
        
        self.print_progress_bar("Skills", completed_skills, total_skills)
        
        # Books progress
        total_books = self.data["books_stats"]["total_books_discovered"]
        completed_books = self.data["books_stats"]["downloaded_books"]
        failed_books = self.data["books_stats"]["failed_books"]
        
        self.print_progress_bar("Books", completed_books, total_books)
        
        print(f"├─ Failed: {failed_books:,} books ({failed_books/total_books*100:.1f}%)" if total_books > 0 else "├─ Failed: 0 books")
        print(f"└─ Remaining: ~{total_books - completed_books:,} books\n")
        
        # Time statistics
        print("Time Statistics:")
        print(f"├─ Elapsed: {self.get_elapsed_string()}")
        print(f"├─ Average Speed: {self.data['performance']['average_items_per_minute']:.1f} books/min")
        print(f"├─ Estimated Remaining: {self.get_eta_string()}")
        
        completion_time = self.get_completion_time()
        if completion_time:
            print(f"└─ Expected Completion: {completion_time}\n")
        else:
            print(f"└─ Expected Completion: Calculating...\n")
        
        # Current activity
        current_skill = self.data["current_activity"]["current_skill"]
        if current_skill:
            print("Current Activity:")
            skill_progress = self.data["current_activity"]["current_skill_progress"]
            current_item = self.data["current_activity"]["current_item"]
            
            print(f"├─ Skill: {current_skill} ({skill_progress})")
            if current_item:
                print(f"└─ Book: {current_item}\n")
            else:
                print()
        
        # Recent skills
        recent_skills = self.data["skills_completed"][-5:]
        if recent_skills:
            print("Recent Completions:")
            for skill in recent_skills:
                print(f"✅ {skill}")
            print()
        
        print(f"{'='*60}\n")


def format_progress_line(prefix: str, current: int, total: int, 
                        extra_info: str = "", width: int = 30) -> str:
    """Format a single-line progress indicator"""
    if total == 0:
        percentage = 0
        filled = 0
    else:
        percentage = current / total
        filled = int(width * percentage)
    
    bar = "█" * filled + "░" * (width - filled)
    percent_str = f"{percentage * 100:.1f}%"
    
    line = f"{prefix}: [{bar}] {current:,}/{total:,} ({percent_str})"
    if extra_info:
        line += f" | {extra_info}"
    
    return line

