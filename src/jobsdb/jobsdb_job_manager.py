import random
import time
from typing import Dict, Any, List, Optional
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
import src.utils.utils as utils
from src.utils.job import Job
from src.jobsdb.jobsdb_easy_applier import JobsDBEasyApplier 


class JobsDBJobManager:
    """
    JobsDB-specific job manager implementation.
    Handles job search, discovery, and application coordination for JobsDB platform.
    """

    def __init__(self, driver: WebDriver) -> None:
        self.driver: WebDriver = driver
        self.set_old_answers: set = set()
        
        self.base_url: str = "https://hk.jobsdb.com"
        self.search_path: str = "/hk/search-jobs"
        self.last_search_url: str = ""
    
    def set_parameters(self, parameters):
        # Minimal parameter setup for JobsDB
        self.parameters = parameters
        self.resume_path = parameters.get('uploads', {}).get('resume', None)
        
    def set_gpt_answerer(self, gpt_answerer):
        self.gpt_answerer = gpt_answerer
        
    def set_resume_generator_manager(self, resume_generator_manager):
        self.resume_generator_manager = resume_generator_manager
    
    def _create_easy_applier_component(self):
        """Create JobsDB-specific easy applier component"""
        return JobsDBEasyApplier(
            self.driver, 
            self.resume_path, 
            self.set_old_answers, 
            self.gpt_answerer, 
            self.resume_generator_manager
        )
     
    def apply_jobs(self):
        """Apply to jobs using new card iteration method"""        
        # Use new iteration method directly - this processes all jobs on the page at once
        self.easy_applier_component = self._create_easy_applier_component()
        utils.printyellow("JobsDB: Using card iteration strategy...")
        self.easy_applier_component.iterate_and_apply_jobs()
        
        # Note: We don't call the parent apply_jobs() because that would try to
        # extract job information from tiles and call job_apply() for each job individually.
        # Instead, our iterate_and_apply_jobs() method handles everything in one go.
