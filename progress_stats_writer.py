#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progress Stats Writer Module
Handles real-time progress statistics for tail viewing in separate terminal
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, Optional


class ProgressStatsWriter:
    """Writes live progress statistics to a file for tail viewing"""
    
    def __init__(self, stats_file: str = "output/download_progress_live.txt"):
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread safety for file writes
        self.write_lock = threading.Lock()
        
        # Current stats
        self.total_books = 0
        self.downloaded_books = 0
        self.failed_books = 0
        self.skipped_books = 0
        self.current_skill = "Initializing..."
        self.start_time = time.time()
        self.last_update = time.time()
        
        # Initialize the stats file
        self._write_initial_stats()
    
    def _write_initial_stats(self):
        """Write initial stats to file"""
        with self.write_lock:
            with open(self.stats_file, 'w') as f:
                f.write("=" * 60 + "\n")
                f.write("O'Reilly Books Download Progress\n")
                f.write("=" * 60 + "\n")
                f.write(f"Status: Initializing...\n")
                f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Current Skill: {self.current_skill}\n")
                f.write(f"Total Books: {self.total_books}\n")
                f.write(f"Downloaded: {self.downloaded_books}\n")
                f.write(f"Failed: {self.failed_books}\n")
                f.write(f"Skipped: {self.skipped_books}\n")
                f.write(f"Progress: 0.0%\n")
                f.write(f"Elapsed: 00:00:00\n")
                f.write(f"ETA: Calculating...\n")
                f.write("=" * 60 + "\n")
                f.write("Last Updated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
    
    def update_session_start(self, total_skills: int, total_books: int):
        """Update stats when download session starts"""
        with self.write_lock:
            self.total_books = total_books
            self.start_time = time.time()
            self.last_update = time.time()
            self._write_stats()
    
    def update_current_skill(self, skill_name: str):
        """Update current skill being processed"""
        with self.write_lock:
            self.current_skill = skill_name
            self._write_stats()
    
    def update_book_completed(self, was_downloaded: bool, was_successful: bool):
        """Update stats when a book download completes"""
        with self.write_lock:
            if was_successful:
                if was_downloaded:
                    self.downloaded_books += 1
                else:
                    self.skipped_books += 1
            else:
                self.failed_books += 1
            
            self.last_update = time.time()
            self._write_stats()
    
    def update_skill_completed(self, skill_name: str, skill_results: Dict):
        """Update stats when a skill is completed"""
        with self.write_lock:
            self.current_skill = f"Completed: {skill_name}"
            self._write_stats()
    
    def _write_stats(self):
        """Write current stats to file"""
        try:
            # Calculate progress percentage
            if self.total_books > 0:
                progress_pct = ((self.downloaded_books + self.skipped_books + self.failed_books) / self.total_books) * 100
            else:
                progress_pct = 0.0
            
            # Calculate elapsed time
            elapsed_seconds = time.time() - self.start_time
            elapsed_str = self._format_duration(elapsed_seconds)
            
            # Calculate ETA
            eta_str = self._calculate_eta(elapsed_seconds, progress_pct)
            
            # Write to file
            with open(self.stats_file, 'w') as f:
                f.write("=" * 60 + "\n")
                f.write("O'Reilly Books Download Progress\n")
                f.write("=" * 60 + "\n")
                f.write(f"Status: {'Running' if progress_pct < 100 else 'Completed'}\n")
                f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}\n")
                f.write(f"Current Skill: {self.current_skill}\n")
                f.write(f"Total Books: {self.total_books:,}\n")
                f.write(f"Downloaded: {self.downloaded_books:,}\n")
                f.write(f"Failed: {self.failed_books:,}\n")
                f.write(f"Skipped: {self.skipped_books:,}\n")
                f.write(f"Progress: {progress_pct:.1f}%\n")
                f.write(f"Elapsed: {elapsed_str}\n")
                f.write(f"ETA: {eta_str}\n")
                f.write("=" * 60 + "\n")
                f.write("Last Updated: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n")
                
        except Exception as e:
            # Don't let stats writing errors break the main download process
            pass
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _calculate_eta(self, elapsed_seconds: float, progress_pct: float) -> str:
        """Calculate estimated time to completion"""
        if progress_pct <= 0:
            return "Calculating..."
        
        if progress_pct >= 100:
            return "Completed"
        
        # Calculate rate (books per second)
        books_processed = self.downloaded_books + self.skipped_books + self.failed_books
        if books_processed > 0 and elapsed_seconds > 0:
            rate = books_processed / elapsed_seconds
            remaining_books = self.total_books - books_processed
            eta_seconds = remaining_books / rate
            return self._format_duration(eta_seconds)
        
        return "Calculating..."
    
    def finalize(self, final_results: Dict):
        """Write final stats when download session completes"""
        with self.write_lock:
            self.current_skill = "Session Completed"
            self._write_stats()
            
            # Add final summary
            with open(self.stats_file, 'a') as f:
                f.write("\n" + "=" * 60 + "\n")
                f.write("FINAL SUMMARY\n")
                f.write("=" * 60 + "\n")
                f.write(f"Skills Processed: {final_results.get('skills_processed', 0)}\n")
                f.write(f"Total Books: {final_results.get('total_books', 0):,}\n")
                f.write(f"Successfully Downloaded: {final_results.get('total_downloaded', 0):,}\n")
                f.write(f"Failed Downloads: {final_results.get('total_failed', 0):,}\n")
                f.write(f"Skipped (Already Downloaded): {final_results.get('total_skipped', 0):,}\n")
                f.write(f"Total Time: {self._format_duration(time.time() - self.start_time)}\n")
                f.write("=" * 60 + "\n")
