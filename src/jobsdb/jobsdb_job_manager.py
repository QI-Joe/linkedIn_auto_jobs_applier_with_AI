import random
import time
from typing import Dict, Any, List, Optional
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
import src.utils as utils
from src.base_job_manager import BaseJobManager
from src.job import Job
from src.jobsdb_easy_applier import JobsDBEasyApplier 


class JobsDBJobManager(BaseJobManager):
    """
    JobsDB-specific job manager implementation.
    Handles job search, discovery, and application coordination for JobsDB platform.
    """
    
    def __init__(self, driver: WebDriver) -> None:
        super().__init__(driver)
        self.base_url: str = "https://hk.jobsdb.com"
        self.search_path: str = "/hk/search-jobs"
        self.last_search_url: str = ""
        
    def get_platform_name(self) -> str:
        """Return the platform name"""
        return "jobsdb"
    
    def get_base_search_url(self, parameters: Dict[str, Any]) -> str:
        """Build base search URL for JobsDB"""
        # JobsDB search URL pattern: /hk/search-jobs?q=keywords&l=location&start=0
        base_params = {
            'sortby': 'createdAt',  # Sort by newest first
            'limit': '20'           # Jobs per page
        }
        
        # Add any additional filters from parameters
        if parameters.get('remote'):
            base_params['remote'] = 'true'
            
        # Convert params to URL string
        param_string = "&".join([f"{k}={v}" for k, v in base_params.items()])
        return f"{self.base_url}{self.search_path}?{param_string}"
    
    def _format_location_url(self, location: str) -> str:
        """Format location for JobsDB URL"""
        # JobsDB uses location parameter 'l'
        return f"&l={location.replace(' ', '%20')}"
    
    def next_job_page(self, position: str, location: str, job_page: int) -> None:
        """Navigate to next page of JobsDB job results"""
        # JobsDB pagination uses 'start' parameter (jobs per page * page number)
        start_index = job_page * 20  # JobsDB typically shows 20 jobs per page
        
        # Build search URL with keywords, location, and pagination
        keywords = position.replace(' ', '%20')
        location_param = location.replace(' ', '%20')
        
        search_url = f"{self.base_url}{self.search_path}?q={keywords}&l={location_param}&start={start_index}&sortby=createdAt"
        
        # Store for potential back navigation
        self.last_search_url = search_url
        
        utils.printyellow(f"JobsDB: Navigating to {search_url}")
        self.driver.get(search_url)
        
        # Wait for page to load
        time.sleep(random.uniform(2, 4))
        
        # Wait for job results to appear
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-automation="job-list-item"], .job-item, .search-result'))
            )
        except Exception:
            utils.printred("JobsDB: Job results took too long to load")
    
    def get_job_list_elements(self) -> List[WebElement]:
        """Get job listing elements from current JobsDB page"""
        # JobsDB job listing selectors (these will need collaboration to identify)
        job_selectors = [
            '[data-automation="job-list-item"]',  # Primary selector
            '.job-item',                          # Alternative selector  
            '.search-result',                     # Fallback selector
            '[class*="job-card"]',               # Class contains job-card
            '[class*="job-item"]'                # Class contains job-item
        ]
        
        job_elements: List[WebElement] = []
        for selector in job_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    utils.printyellow(f"JobsDB: Found {len(elements)} jobs using selector: {selector}")
                    job_elements.extend(elements)
            except Exception as e:
                continue
        
        # If no jobs found, try more generic approach
        try:
            # Look for any clickable elements that might be jobs
            all_links = self.driver.find_elements(By.TAG_NAME, 'a')
            job_links = [link for link in all_links if 'job' in link.get_attribute('href').lower()]
            if job_links:
                utils.printyellow(f"JobsDB: Found {len(job_links)} potential job links")
                return job_links[:20]  # Limit to reasonable number
        except Exception:
            pass
            
        utils.printred("JobsDB: No job elements found on page")
        return []
    
    def extract_job_information_from_tile(self, job_tile) -> tuple:
        """Extract job information from JobsDB job listing tile"""
        try:
            # JobsDB job information extraction (requires collaboration for exact selectors)
            
            # Job Title - try multiple potential selectors
            title = self._extract_text_by_selectors(job_tile, [
                '[data-automation="jobTitle"]',
                '.job-title',
                'h3 a',
                'h4 a',
                '[class*="title"]',
                '.position-title'
            ], "Job Title")

            # Company Name
            company = self._extract_text_by_selectors(job_tile, [
                '[data-automation="jobCompany"]',
                '.company-name',
                '[class*="company"]',
                '.employer-name'
            ], "Company")

            # Location
            location = self._extract_text_by_selectors(job_tile, [
                '[data-automation="jobCardLocation"]',
                '.location',
                '[class*="location"]',
                '.job-location'
            ], "Location")
            
            # Job Link
            link = self._extract_link(job_tile)
            
            # Apply Method - JobsDB typically uses "Quick Apply" or "Apply Now"
            apply_method = self._extract_apply_method(job_tile)
            
            # Additional JobsDB-specific information
            salary = self._extract_text_by_selectors(job_tile, [
                '.salary',
                '[data-automation="job-salary"]',
                '[class*="salary"]'
            ], "Salary", required=False)
            
            # Return job information tuple compatible with Job dataclass
            return (title, company, location, link, apply_method)
            
        except Exception as e:
            utils.printred(f"JobsDB: Failed to extract job info: {str(e)}")
            # Return minimal info to prevent complete failure
            return ("Unknown Position", "Unknown Company", "Unknown Location", "", "Apply")
    
    def _extract_text_by_selectors(self, element, selectors, field_name, required=True):
        """Try multiple CSS selectors to extract text"""
        for selector in selectors:
            try:
                found_element = element.find_element(By.CSS_SELECTOR, selector)
                text = found_element.text.strip()
                if text:
                    return text
            except Exception:
                continue
        
        if required:
            utils.printred(f"JobsDB: Could not find {field_name}")
            return f"Unknown {field_name}"
        return ""
    
    def _extract_link(self, job_tile):
        """Extract job link from tile"""
        try:
            # Try to find link in various ways
            link_selectors = [
                'a[href*="/job/"]',
                '[data-automation="jobTitle"]',
                '.job-title a',
                'h3 a',
                'h4 a',
                'a[href*="/jobs/"]'
            ]
            
            for selector in link_selectors:
                try:
                    link_element = job_tile.find_element(By.CSS_SELECTOR, selector)
                    href = link_element.get_attribute('href')
                    if href and 'job' in href.lower():
                        # Ensure it's a full URL
                        if href.startswith('/'):
                            href = self.base_url + href
                        return href
                except Exception:
                    continue
            
            # Fallback: try to find any link
            link_element = job_tile.find_element(By.TAG_NAME, 'a')
            href = link_element.get_attribute('href')
            if href.startswith('/'):
                href = self.base_url + href
            return href
            
        except Exception:
            utils.printred("JobsDB: Could not extract job link")
            return ""
    
    def _extract_apply_method(self, job_tile):
        """Extract apply method from JobsDB job tile"""
        try:
            # Look for apply buttons or indicators
            apply_selectors = [
                '[data-automation="job-detail-apply"]',
                '.apply-button',
                '.quick-apply',
                'button[contains(text(), "Apply")]'
            ]
            
            for selector in apply_selectors:
                try:
                    apply_element = job_tile.find_element(By.CSS_SELECTOR, selector)
                    apply_text = apply_element.text.strip()
                    if apply_text:
                        return apply_text
                except Exception:
                    continue
            
            # Default for JobsDB
            return "Quick Apply"
            
        except Exception:
            return "Apply"
    
    def _create_easy_applier_component(self):
        """Create JobsDB-specific easy applier component"""
        return JobsDBEasyApplier(
            self.driver, 
            self.resume_path, 
            self.set_old_answers, 
            self.gpt_answerer, 
            self.resume_generator_manager
        )
    
    def _check_no_jobs_available(self) -> bool:
        """Check if no jobs are available on current JobsDB page"""
        no_jobs_indicators = [
            "No jobs found",
            "0 jobs found", 
            "No matching jobs",
            "No results found",
            "没有找到工作",  # Chinese
            "找不到職位"      # Traditional Chinese
        ]
        
        page_text = self.driver.page_source.lower()
        for indicator in no_jobs_indicators:
            if indicator.lower() in page_text:
                return True
        
        # Check for empty job list
        job_elements = self.get_job_list_elements()
        return len(job_elements) == 0
    
    def _scroll_job_results(self):
        """Scroll through JobsDB job results to load all jobs"""
        try:
            # Find the main content area or job results container
            scroll_selectors = [
                '.job-results',
                '.search-results', 
                '.job-list',
                'main',
                '.content'
            ]
            
            scrollable_element = None
            for selector in scroll_selectors:
                try:
                    scrollable_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except Exception:
                    continue
            
            # Fallback to body if no specific container found
            if not scrollable_element:
                scrollable_element = self.driver.find_element(By.TAG_NAME, 'body')
            
            # Scroll down and then back up to ensure all content is loaded
            utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=False)
            time.sleep(random.uniform(1, 2))
            utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=True)
            
        except Exception as e:
            utils.printred(f"JobsDB: Error scrolling job results: {str(e)}")
    
    def _should_apply_to_job(self, job: Job) -> bool:
        """Determine if we should apply to this JobsDB job"""
        # Check if it's a Quick Apply job
        if 'quick' in job.apply_method.lower() or 'apply' in job.apply_method.lower():
            return True
        
        # JobsDB specific logic - avoid external redirects
        if 'external' in job.apply_method.lower() or 'redirect' in job.apply_method.lower():
            utils.printyellow(f"JobsDB: Skipping external application for {job.title}")
            return False
        
        return True
