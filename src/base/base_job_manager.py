import os
import random
import time
import traceback
from abc import ABC, abstractmethod
from itertools import product
from pathlib import Path
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import src.utils.utils as utils
from src.utils.job import Job
import json


class EnvironmentKeys:
    """Environment configuration keys handler"""
    def __init__(self):
        self.skip_apply = self._read_env_key_bool("SKIP_APPLY")
        self.disable_description_filter = self._read_env_key_bool("DISABLE_DESCRIPTION_FILTER")

    @staticmethod
    def _read_env_key(key: str) -> str:
        return os.getenv(key, "")

    @staticmethod
    def _read_env_key_bool(key: str) -> bool:
        return os.getenv(key) == "True"


class BaseJobManager(ABC):
    """
    Abstract base class for job management across platforms.
    Provides common job search, filtering, and application coordination patterns.
    """
    
    def __init__(self, driver):
        self.driver = driver
        self.set_old_answers = set()
        self.easy_applier_component = None
        self.platform_name = ""

    def set_parameters(self, parameters):
        """Set job search parameters"""
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.seen_jobs = []
        
        # Handle resume path
        resume_path = parameters.get('uploads', {}).get('resume', None)
        if resume_path is not None and Path(resume_path).exists():
            self.resume_path = Path(resume_path)
        else:
            self.resume_path = None
            
        self.output_file_directory = Path(parameters['outputFileDirectory'])
        self.env_config = EnvironmentKeys()

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name"""
        pass

    @abstractmethod
    def get_base_search_url(self, parameters) -> str:
        """Build base search URL for the platform"""
        pass

    @abstractmethod
    def next_job_page(self, position: str, location: str, job_page: int):
        """Navigate to next page of job results"""
        pass

    @abstractmethod
    def extract_job_information_from_tile(self, job_tile) -> tuple:
        """Extract job information from job listing tile"""
        pass

    @abstractmethod
    def get_job_list_elements(self):
        """Get job listing elements from current page"""
        pass

    def set_gpt_answerer(self, gpt_answerer):
        """Set GPT answerer component"""
        self.gpt_answerer = gpt_answerer

    def set_resume_generator_manager(self, resume_generator_manager):
        """Set resume generator manager"""
        self.resume_generator_manager = resume_generator_manager  # Can be None if disabled

    def is_blacklisted(self, job_title: str, company: str, link: str) -> bool:
        """Check if job should be skipped based on blacklists"""
        job_title_words = job_title.lower().split(' ')
        title_blacklisted = any(word in job_title_words for word in self.title_blacklist)
        company_blacklisted = company.strip().lower() in (word.strip().lower() for word in self.company_blacklist)
        link_seen = link in self.seen_jobs
        
        if not link_seen:
            self.seen_jobs.append(link)
            
        return title_blacklisted or company_blacklisted or link_seen

    def start_applying(self):
        """Start the job application process"""
        self.platform_name = self.get_platform_name()
        utils.printyellow(f"Starting {self.platform_name} job application process...")
        
        # Create platform-specific applier component
        self.easy_applier_component = self._create_easy_applier_component()
        
        # Generate search combinations
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)
        
        page_sleep = 0
        minimum_time = 60 * 15  # 15 minutes minimum
        minimum_page_time = time.time() + minimum_time

        for position, location in searches:
            location_url = self._format_location_url(location)
            job_page_number = -1
            utils.printyellow(f"Starting the search for {position} in {location} on {self.platform_name}.")

            try:
                while True:
                    page_sleep += 1
                    job_page_number += 1
                    utils.printyellow(f"Going to job page {job_page_number}")
                    
                    self.next_job_page(position, location_url, job_page_number)
                    time.sleep(random.uniform(1.5, 3.5))
                    
                    utils.printyellow("Starting the application process for this page...")
                    self.apply_jobs()
                    utils.printyellow("Applying to jobs on this page has been completed!")

                    # Rate limiting
                    time_left = minimum_page_time - time.time()
                    if time_left > 0:
                        utils.printyellow(f"Sleeping for {time_left} seconds.")
                        time.sleep(time_left)
                        minimum_page_time = time.time() + minimum_time
                        
                    if page_sleep % 5 == 0:
                        sleep_time = random.randint(5, 34)
                        utils.printyellow(f"Sleeping for {sleep_time / 60} minutes.")
                        time.sleep(sleep_time)
                        page_sleep += 1
                        
            except Exception:
                traceback.format_exc()
                pass
                
            # Final rest period
            time_left = minimum_page_time - time.time()
            if time_left > 0:
                utils.printyellow(f"Sleeping for {time_left} seconds.")
                time.sleep(time_left)
                minimum_page_time = time.time() + minimum_time
                
            if page_sleep % 5 == 0:
                sleep_time = random.randint(50, 90)
                utils.printyellow(f"Sleeping for {sleep_time / 60} minutes.")
                time.sleep(sleep_time)
                page_sleep += 1

    @abstractmethod
    def _create_easy_applier_component(self):
        """Create platform-specific easy applier component"""
        pass

    @abstractmethod
    def _format_location_url(self, location: str) -> str:
        """Format location for URL - platform specific"""
        pass

    def apply_jobs(self):
        """Apply to jobs on current page"""
        try:
            # Check for "no jobs" message - platform specific implementation
            if self._check_no_jobs_available():
                raise Exception("No more jobs on this page")
        except NoSuchElementException:
            pass
        
        # Get job list elements
        job_list_elements = self.get_job_list_elements()
        if not job_list_elements:
            raise Exception("No job elements found on page")
        
        # Scroll through job results
        self._scroll_job_results()
        
        # Extract job information
        job_list = []
        for job_element in job_list_elements:
            try:
                job_info = self.extract_job_information_from_tile(job_element)
                job = Job(*job_info, platform=self.platform_name)
                job_list.append(job)
            except Exception as e:
                utils.printred(f"Failed to extract job information: {str(e)}")
                continue
        
        # Process each job
        for job in job_list:
            if self.is_blacklisted(job.title, job.company, job.link):
                utils.printyellow(f"Blacklisted {job.title} at {job.company}, skipping...")
                self.write_to_file(job, "skipped")
                continue
                
            try:
                if self._should_apply_to_job(job):
                    self.easy_applier_component.job_apply(job)
                    self.write_to_file(job, "success")
                else:
                    self.write_to_file(job, "skipped")
            except Exception as e:
                utils.printred(traceback.format_exc())
                self.write_to_file(job, "failed")
                continue

    @abstractmethod
    def _check_no_jobs_available(self) -> bool:
        """Check if no jobs are available on current page"""
        pass

    @abstractmethod
    def _scroll_job_results(self):
        """Scroll through job results to load all jobs"""
        pass

    @abstractmethod
    def _should_apply_to_job(self, job: Job) -> bool:
        """Determine if we should apply to this job"""
        pass

    def write_to_file(self, job: Job, file_name: str):
        """Write job application result to file"""
        pdf_path = Path(job.pdf_path).resolve() if job.pdf_path else ""
        pdf_path = pdf_path.as_uri() if pdf_path else ""
        
        data = {
            "platform": job.platform,
            "company": job.company,
            "job_title": job.title,
            "link": job.link,
            "job_recruiter": job.recruiter_link,
            "job_location": job.location,
            "pdf_path": pdf_path
        }
        
        file_path = self.output_file_directory / f"{file_name}.json"
        if not file_path.exists():
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([data], f, indent=4)
        else:
            with open(file_path, 'r+', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                    existing_data.append(data)
                    f.seek(0)
                    json.dump(existing_data, f, indent=4)
                    f.truncate()
                except json.JSONDecodeError:
                    f.seek(0)
                    json.dump([data], f, indent=4)
                    f.truncate()
