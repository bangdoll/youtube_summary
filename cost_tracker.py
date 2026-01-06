import os
import json
from datetime import datetime
import logging

class CostTracker:
    # Pricing constants (USD)
    # Updated as of 2024-05 (GPT-4o)
    PRICE_GPT4O_INPUT_1K = 0.0025  # $2.50 / 1M tokens
    PRICE_GPT4O_OUTPUT_1K = 0.0100 # $10.00 / 1M tokens
    
    # Whisper API
    PRICE_WHISPER_MIN = 0.006      # $0.006 / minute ($0.36 / hour)
    
    DATA_FILE = "usage_data.json"
    
    def __init__(self):
        self._load_data()
        
    def _load_data(self):
        """Loads usage data from JSON file."""
        self.data = {}
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, 'r') as f:
                    self.data = json.load(f)
            except Exception as e:
                logging.error(f"Error loading usage data: {e}")
                self.data = {}
    
    def _save_data(self):
        """Saves usage data to JSON file."""
        try:
            with open(self.DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving usage data: {e}")

    def _get_current_month_key(self):
        """Returns key for current month (YYYY-MM)."""
        return datetime.now().strftime("%Y-%m")
        
    def track_chat(self, model, prompt_tokens, completion_tokens):
        """Tracks cost for a chat completion request."""
        cost = 0.0
        
        # Simple pricing logic (can be expanded)
        if "gpt-4o" in model:
            cost += (prompt_tokens / 1000) * self.PRICE_GPT4O_INPUT_1K
            cost += (completion_tokens / 1000) * self.PRICE_GPT4O_OUTPUT_1K
        
        self._record_usage("chat", cost, {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        })
        
        return cost

    def track_audio(self, duration_seconds):
        """Tracks cost for Whisper audio transcription."""
        duration_minutes = duration_seconds / 60.0
        cost = duration_minutes * self.PRICE_WHISPER_MIN
        
        self._record_usage("whisper", cost, {
            "duration_seconds": duration_seconds
        })
        
        return cost
        
    def _record_usage(self, type, cost, details):
        """Internal method to update data structure."""
        month_key = self._get_current_month_key()
        
        if month_key not in self.data:
            self.data[month_key] = {
                "total_cost": 0.0,
                "breakdown": []
            }
            
        self.data[month_key]["total_cost"] += cost
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": type,
            "cost": cost,
            "details": details
        }
        
        self.data[month_key]["breakdown"].append(entry)
        self._save_data()
        
    def get_total_cost(self, month=None):
        """Returns total cost for a specific month (default: current)."""
        if not month:
            month = self._get_current_month_key()
            
        return self.data.get(month, {}).get("total_cost", 0.0)
        
    def is_limit_exceeded(self, limit=20.0):
        """Checks if current month's cost exceeds the limit."""
        return self.get_total_cost() > limit

# Singleton instance
tracker = CostTracker()
