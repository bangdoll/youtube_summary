import os
import json
from datetime import datetime
import logging
import firebase_admin
from firebase_admin import credentials, db

class CostTracker:
    # Pricing constants (USD)
    PRICE_GPT4O_INPUT_1K = 0.0025  # $2.50 / 1M tokens
    PRICE_GPT4O_OUTPUT_1K = 0.0100 # $10.00 / 1M tokens
    PRICE_WHISPER_MIN = 0.006      # $0.006 / minute
    
    DATA_FILE = "usage_data.json"
    
    def __init__(self):
        self.use_firebase = False
        self.db_ref = None
        self._init_firebase()
        self._load_data()
        
    def _init_firebase(self):
        """Initializes Firebase if credentials are present in env vars."""
        fb_creds_json = os.getenv("FIREBASE_CREDENTIALS")
        fb_db_url = os.getenv("FIREBASE_DB_URL")
        
        if fb_creds_json and fb_db_url:
            try:
                # Check if already initialized to avoid error on reload
                if not firebase_admin._apps:
                    # Parse JSON string to dict
                    cred_dict = json.loads(fb_creds_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': fb_db_url
                    })
                
                self.db_ref = db.reference('usage_data')
                self.use_firebase = True
                logging.info("🔥 Firebase initialized successfully for CostTracker.")
            except Exception as e:
                logging.error(f"❌ Failed to initialize Firebase: {e}. Falling back to local file.")
                self.use_firebase = False
        else:
            logging.info("ℹ️ No Firebase credentials found. Using local storage.")

    def _load_data(self):
        """Loads usage data from Firebase or local JSON file."""
        self.data = {}
        
        if self.use_firebase and self.db_ref:
            try:
                remote_data = self.db_ref.get()
                if remote_data:
                    self.data = remote_data
                else:
                    self.data = {}
            except Exception as e:
                 logging.error(f"Error loading data from Firebase: {e}")
                 self.data = {}
        else:
            # Local fallback
            if os.path.exists(self.DATA_FILE):
                try:
                    with open(self.DATA_FILE, 'r') as f:
                        self.data = json.load(f)
                except Exception as e:
                    logging.error(f"Error loading local usage data: {e}")
                    self.data = {}
    
    def _save_data(self):
        """Saves usage data to Firebase or local JSON file."""
        try:
            if self.use_firebase and self.db_ref:
                self.db_ref.set(self.data)
            else:
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
        
        # Ensure month key exists
        if month_key not in self.data:
            self.data[month_key] = {
                "total_cost": 0.0,
                "breakdown": []
            }
        
        # Initialize sub-structures if missing (handling potential partial data from DB)
        if "total_cost" not in self.data[month_key]:
            self.data[month_key]["total_cost"] = 0.0
        if "breakdown" not in self.data[month_key]:
            self.data[month_key]["breakdown"] = []
            
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
        
        # Handle cases where month exists but structure might be incomplete
        month_data = self.data.get(month, {})
        if isinstance(month_data, dict):
            return month_data.get("total_cost", 0.0)
        return 0.0
        
    def is_limit_exceeded(self, limit=20.0):
        """Checks if current month's cost exceeds the limit."""
        return self.get_total_cost() > limit

# Singleton instance
tracker = CostTracker()
