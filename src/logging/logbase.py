import json
import threading
import os
import queue
from datetime import datetime

# I would like to consider entire logBase task is in antoher thread to run
class logBase(threading.Thread):
    def __init__(self, log_path: str):
        super(logBase, self).__init__()
        self.job_queue = queue.Queue(maxsize=16)
        self.log_path = log_path
        self._stop_event = threading.Event()
    
    def run(self):
        """Thread run method to process log jobs"""
        while not self._stop_event.is_set():
            try:
                job: dict = self.job_queue.get(timeout=1)
                self._process_and_store(job)
                self.job_queue.task_done()
            except queue.Empty:
                continue  # No job available, check stop_event again
            except Exception as e:
                print(f"Error processing log job: {e}")
    
    def _process_and_store(self, job: dict):
        """Process and store a log job in json format
        expected keys in job: [timestamp in Y-M-D, job_info, submitted, button_type]
        """

        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path, exist_ok=True)
        
        # Construct the file path after ensuring directory exists
        storage_path = os.path.join(self.log_path, f"{job['timestamp']}_log.json")
        
        # Use JSONL format (JSON Lines) for proper append functionality
        # Each line is a valid JSON object, making it easy to read line by line
        with open(storage_path, 'a', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, indent=2)
            f.write('\n')  # Newline for each log entry (JSONL format)
                
        return 

    def add_log_job(self, job: dict):

        timestamp = datetime.now().strftime("%Y-%m-%d")
        job['timestamp'] = timestamp
        self.job_queue.put(job)
    
    def stop(self):
        """Signal the thread to stop"""
        self._stop_event.set()
        self.job_queue.join()  # Wait until all jobs are processed
    
    def is_alive(self):
        return super().is_alive()