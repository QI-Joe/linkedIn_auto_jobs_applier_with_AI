import os
import random
import time
import traceback
from typing import List, Optional, Any
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import src.utils.utils as utils
from src.base.base_easy_applier import BaseEasyApplier


class JobsDBEasyApplier(BaseEasyApplier):
    """
    JobsDB-specific easy applier implementation.
    Handles JobsDB application forms with page navigation instead of modals.
    """
    
    def __init__(self, driver: Any, resume_dir: Optional[str], set_old_answers: List, gpt_answerer: Any, resume_generator_manager):
        super().__init__(driver, resume_dir, set_old_answers, gpt_answerer, resume_generator_manager)
        self.base_url = "https://hk.jobsdb.com"
    
    def get_job_search_url(self):
        self.job_title, self.job_posting_date_range = "ai-engineer-jobs", 14
        target_url=f"{self.base_url}/{self.job_title}?daterange={self.job_posting_date_range}"
        return target_url
    
    def get_platform_selectors(self):
        """Return JobsDB-specific CSS selectors"""
        return {
            'apply_button': [
                '[data-automation="job-detail-apply"]',
                '.apply-button',
                '.quick-apply',
                'button.apply-btn',
                '.btn-apply',
                'button[contains(text(), "Apply Now")]',
                'button[contains(text(), "Quick Apply")]'
            ],
            'submit_button': [
                'button[type="submit"]',
                'button[contains(text(), "Submit")]',
                'button[contains(text(), "Send")]'
            ],
            'next_button': [
                'button[contains(text(), "Next")]',
                'button[contains(text(), "Continue")]'
            ]
        }

    def iterate_and_apply_jobs(self):
        """Main method: iterate through all job cards on current page and apply"""
        seen_job_ids = set()
        max_iterations = 50
        
        utils.printyellow("JobsDB: Starting job card iteration...")
        
        job_list_url = self.get_job_search_url()
        self.driver.get(job_list_url)
        
        for iteration in range(max_iterations):
            job_cards = self._get_all_job_cards()
            current_count = len(job_cards)
            
            utils.printyellow(f"JobsDB: Iteration {iteration+1}, found {current_count} job cards")
            
            new_jobs_processed = 0
            for card_index in range(len(job_cards)):
                try:
                    # Re-fetch cards to avoid stale elements
                    job_cards = self._get_all_job_cards()
                    if card_index >= len(job_cards):
                        break
                        
                    card = job_cards[card_index]
                    job_id = self._extract_job_id_from_card(card)
                    
                    if job_id in seen_job_ids:
                        continue
                    
                    success = self._process_single_job_card(card, job_id)
                    seen_job_ids.add(job_id)
                    
                    if success:
                        new_jobs_processed += 1
                        
                    time.sleep(random.uniform(1, 2))
                    
                except Exception as e:
                    utils.printred(f"JobsDB: Error processing card {card_index}: {str(e)}")
                    continue
            
            utils.printyellow(f"JobsDB: Processed {new_jobs_processed} new jobs this round")
                
            # If no new jobs found, stop
            if new_jobs_processed == 0:
                utils.printyellow("JobsDB: No new jobs found, iteration complete")
                break
        
        utils.printyellow(f"JobsDB: Iteration complete, processed {len(seen_job_ids)} total jobs")

    def job_apply(self, job: Any):
        """Deprecated - use iterate_and_apply_jobs instead"""
        utils.printred("JobsDB: job_apply method is deprecated, use iterate_and_apply_jobs instead")
        raise Exception("Use iterate_and_apply_jobs method for JobsDB")

    def _find_apply_button(self):
        """depreciated - used to fullfill abstract method implementation"""
        utils.printred("JobsDB: _find_apply_button function is depreciated")
        raise Exception("Use _get_all_job_cards method instead")

    def _get_all_job_cards(self) -> List[WebElement]:
        """Get all job cards on current page"""
        selectors = [
            'article[data-testid="job-card"]',
            'article[data-card-type="JobCard"]',
            '.job-card'
        ]
        
        for selector in selectors:
            try:
                cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    utils.printyellow(f"JobsDB: Found {len(cards)} cards with selector: {selector}")
                    return cards
            except Exception:
                continue
        
        return []

    def _extract_job_id_from_card(self, card: WebElement) -> str:
        """Extract job ID from card"""
        try:
            # Try data attribute first
            job_id = card.get_attribute("data-job-id")
            if job_id:
                return job_id
                
            # Try href extraction
            link_selectors = [
                'a[data-automation="job-list-item-link-overlay"]',
                'a[data-automation="jobTitle"]',
                'a[href*="/job/"]'
            ]
            
            for selector in link_selectors:
                try:
                    link = card.find_element(By.CSS_SELECTOR, selector)
                    href = link.get_attribute("href")
                    if href and "/job/" in href:
                        import re
                        match = re.search(r'/job/(\d+)', href)
                        if match:
                            return match.group(1)
                except Exception:
                    continue
                    
            # Use card hash as fallback ID
            return f"card_{hash(card.get_attribute('outerHTML'))}"
            
        except Exception:
            return f"unknown_{time.time()}"

    def _process_single_job_card(self, card: WebElement, job_id: str) -> bool:
        """Process single job card"""
        try:
            utils.printyellow(f"JobsDB: Processing job card {job_id}")
            
            # Scroll to card
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
            time.sleep(random.uniform(1, 2))
            
            # Click card to open sidebar
            jumped, job_list_search_archive_windows = self._click_card_to_open_sidebar(card)
            new_windows = None
            # Wait for sidebar
            sidebar = self._wait_for_sidebar(jumped)
            
            # Extract job info
            job_info = self._extract_job_info_from_sidebar(sidebar, job_id)
            
            # Find apply button
            apply_button = self._find_apply_button_in_sidebar(sidebar)
            
            button_text = apply_button.text.strip()
            utils.printyellow(f"JobsDB: Found apply button: {button_text}")
            
            if jumped:
                """
                job_list_search_archive_windows: main windows should always be remained, show overall qualifed jobs
                new_windows: the current windows after jumped
                """
                new_windows, job_list_search_archive_windows = job_list_search_archive_windows, self.get_job_search_url()
            
            if self._should_apply_by_button_text(button_text):
                return self._handle_job_application(apply_button, job_info, [new_windows], job_list_search_archive_windows)
            else:
                utils.printyellow(f"JobsDB: Skipping - button type: {button_text}")
                
            return False
            
        except Exception as e:
            utils.printred(f"JobsDB: Error processing card {job_id}: {str(e)}")
            return False

    def _click_card_to_open_sidebar(self, card: WebElement):
        """Click card to open sidebar"""
        link_selectors = [
            'a[data-automation="job-list-item-link-overlay"]',
            'a[data-automation="jobTitle"]'
        ]
        
        for selector in link_selectors:
            try:
                link = card.find_element(By.CSS_SELECTOR, selector)
                self._click_with_retry(link)
                
                current_windows_url = self.driver.current_url
                if self.job_title not in str(current_windows_url).split('/'):
                    return True, current_windows_url
                return False, current_windows_url
            except Exception:
                # should add in log...
                continue
        

    def _wait_for_sidebar(self, jumped: bool) -> WebElement:
        """Wait for sidebar to appear"""
        selectors = [
            'div[data-automation="splitViewJobDetailsWrapper"]',
        ]
        if jumped:
            selectors=[
                'div[data-automation="jobDetailsPage"]',
            ]
        
        for selector in selectors:
            try:
                sidebar = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                )
                utils.printyellow(f"JobsDB: Sidebar loaded with selector: {selector}")
                return sidebar
            except Exception:
                continue
        
        raise Exception("Sidebar load timeout")

    def _find_apply_button_in_sidebar(self, sidebar: WebElement) -> Optional[WebElement]:
        """Find apply button in sidebar"""
        selectors = [
            'a[data-automation="job-detail-apply"]',
            'button[data-automation="job-detail-apply"]',
            '.apply-button',
            'a[href*="/apply"]'
        ]
        
        for selector in selectors:
            try:
                button = sidebar.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed() and button.is_enabled():
                    return button
            except Exception:
                continue
        
        return None

    def _extract_job_info_from_sidebar(self, sidebar: WebElement, job_id: str) -> dict:
        """Extract job info from sidebar"""
        info = {
            'job_id': job_id,
            'title': 'Unknown',
            'company': 'Unknown',
            'link': self.driver.current_url
        }
        
        # Extract title
        title_selectors = ['h1[data-automation="jobTitle"]', '.job-title', 'h1', 'h2']
        for selector in title_selectors:
            try:
                title_element = sidebar.find_element(By.CSS_SELECTOR, selector)
                info['title'] = title_element.text.strip()
                break
            except Exception:
                continue
        
        # Extract company
        company_selectors = ['[data-automation="jobCompany"]', '.company-name', 'a[href*="/companies/"]']
        for selector in company_selectors:
            try:
                company_element = sidebar.find_element(By.CSS_SELECTOR, selector)
                info['company'] = company_element.text.strip()
                break
            except Exception:
                continue
        
        return info

    def _should_apply_by_button_text(self, button_text: str) -> bool:
        """Decide whether to apply based on button text"""
        button_text = button_text.lower().strip()
        apply_keywords = ['quick apply', 'easy apply']
        
        return any(keyword in button_text for keyword in apply_keywords)

    def _handle_job_application(self, apply_button: WebElement, job_info: dict, new_windows: list[str], job_list_windows: str) -> bool:
        """Handle job application"""
        try:
            main_window = job_list_windows
            existing_windows = set(self.driver.window_handles)
            
            # Click apply button
            self._click_with_retry(apply_button)
            time.sleep(random.uniform(2, 4))
            
            # Check for new tab
            if new_windows is None:
                new_windows = set(self.driver.window_handles) - existing_windows
            
            # Switch to new tab
            new_window = list(new_windows)[0]
            self.driver.switch_to.window(new_window)
            
            try:
                # Create fake job object for form filling
                fake_job = self._create_job_object_from_info(job_info)
                fake_job.set_job_description(job_info.get('title', 'Unknown'))
                self.gpt_answerer.set_job(fake_job)
                
                # Fill application forms
                self._fill_application_forms(fake_job)
                
                utils.printyellow(f"JobsDB: Applied to {job_info['title']} at {job_info['company']}")
                return True
                
            except Exception as e:
                utils.printred(f"JobsDB: Form filling failed: {str(e)}")
                return False
            finally:
                # Close new tab and return to main
                try:
                    self.driver.close()
                except Exception:
                    pass
                self.driver.switch_to.window(main_window)
                
        except Exception as e:
            utils.printred(f"JobsDB: Application failed: {str(e)}")
            return False

    def _create_job_object_from_info(self, job_info: dict):
        """Create job object from info"""
        from src.utils.job import Job
        
        return Job(
            title=job_info.get('title', 'Unknown'),
            company=job_info.get('company', 'Unknown'),
            location='Unknown',
            apply_method='Quick Apply',
            link=job_info.get('link', ''),
            platform='jobsdb'
        )


    def _get_job_description(self) -> str:
        """Extract job description from JobsDB job page"""
        try:
            description_selectors = [
                '[data-automation="jobDescription"]',
                '.job-description',
                '.job-details',
                '#job-description'
            ]
            
            for selector in description_selectors:
                try:
                    description_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    description_text = description_element.text.strip()
                    if description_text and len(description_text) > 50:
                        return description_text
                except NoSuchElementException:
                    continue
            
            # Fallback: get page text
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            return page_text[:2000]
            
        except Exception as e:
            utils.printred(f"JobsDB: Could not extract job description: {str(e)}")
            return "Job description not available"

    def _fill_application_forms(self, job):
        """Fill JobsDB application forms with multi-page support"""
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            utils.printyellow(f"JobsDB: Processing form page {attempt + 1}")
            
            # Process form elements on current page using base class methods
            form_sections = self._get_form_sections()
            for section in form_sections:
                self._process_section(section, job)
            
            # Check for validation errors
            if self._check_for_errors():
                utils.printred("JobsDB: Form validation errors detected")
                break
            
            # Try to proceed - return True if submitted, False if next page
            if self._try_next_or_submit():
                utils.printyellow("JobsDB: Application submitted successfully")
                return
            
            attempt += 1
            time.sleep(random.uniform(2, 4))
        
        if attempt >= max_attempts:
            raise Exception("JobsDB: Maximum form pages exceeded")

    def _get_form_sections(self) -> List[WebElement]:
        """Get form sections to process"""
        # Try to find form container first
        containers = [
            'form', '.form-container', '.application-form', 
            '.job-apply-form', 'main', 'body'
        ]
        
        container = None
        for selector in containers:
            try:
                container = self.driver.find_element(By.CSS_SELECTOR, selector)
                break
            except NoSuchElementException:
                continue
        
        if not container:
            container = self.driver.find_element(By.TAG_NAME, 'body')
        
        # Find sections with form elements - using multiple selectors since :has() is not widely supported
        sections = []
        section_selectors = [
            '.form-group', '.field-group', '.form-section', '.question-group',
            'div[class*="form"]', 'div[class*="field"]', 'div[class*="question"]'
        ]
        
        for selector in section_selectors:
            try:
                found_sections = container.find_elements(By.CSS_SELECTOR, selector)
                sections.extend(found_sections)
            except Exception:
                continue
        
        # Fallback: individual form elements
        if not sections:
            sections = container.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
        
        return sections[:15]  # Reasonable limit
    
    def _process_section(self, section: WebElement, job):
        """Process form section using base class methods"""
        try:
            # Handle upload fields first
            if self._is_upload_field(section):
                self._handle_upload_fields(section, job)
                return
            
            # Use base class methods for standard form elements
            if self._find_and_handle_text_question(section):
                return
            if self._find_and_handle_dropdown_question(section):
                return
            if self._find_and_handle_radio_question(section):
                return
            
            # Handle checkboxes (common in JobsDB for terms/conditions)
            self._handle_checkboxes(section)
                
        except Exception as e:
            utils.printred(f"JobsDB: Error processing section: {str(e)}")

    def _handle_checkboxes(self, section: WebElement):
        """Handle checkbox elements"""
        try:
            checkboxes = section.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
            for checkbox in checkboxes:
                # Auto-accept terms and conditions
                parent_text = section.text.lower()
                if any(term in parent_text for term in ['terms', 'privacy', 'policy', 'agreement']):
                    if not checkbox.is_selected():
                        self._click_with_retry(checkbox)
        except Exception:
            pass

    def _try_next_or_submit(self) -> bool:
        """Try to click next or submit button - returns True if submitted"""
        # Look for submit button first
        submit_selectors = self.get_platform_selectors()['submit_button']
        for selector in submit_selectors:
            try:
                button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed() and button.is_enabled():
                    utils.printyellow("JobsDB: Clicking submit button")
                    self._click_with_retry(button)
                    time.sleep(random.uniform(2, 4))
                    return True
            except NoSuchElementException:
                continue
        
        # Look for next button
        next_selectors = self.get_platform_selectors()['next_button']
        for selector in next_selectors:
            try:
                button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed() and button.is_enabled():
                    utils.printyellow("JobsDB: Clicking next button")
                    self._click_with_retry(button)
                    time.sleep(random.uniform(2, 4))
                    return False  # Continue to next page
            except NoSuchElementException:
                continue
        
        # Fallback: look for any relevant button
        button_texts = ['submit', 'send', 'apply', 'next', 'continue']
        for text in button_texts:
            try:
                button = self.driver.find_element(By.XPATH, 
                    f'//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{text}")]')
                if button.is_displayed() and button.is_enabled():
                    utils.printyellow(f"JobsDB: Clicking button: {button.text}")
                    self._click_with_retry(button)
                    time.sleep(random.uniform(2, 4))
                    return text in ['submit', 'send', 'apply']
            except NoSuchElementException:
                continue
        
        raise Exception("JobsDB: No next or submit button found")

    def _return_to_job_list(self):
        """Navigate back to job search results"""
        try:
            # Try browser back first
            self.driver.back()
            time.sleep(random.uniform(2, 3))
            
            # If back doesn't work, navigate to search page
            current_url = self.driver.current_url.lower()
            if 'search' not in current_url and 'jobs' not in current_url:
                search_url = f"{self.base_url}/hk/search-jobs"
                utils.printyellow("JobsDB: Navigating to search page")
                self.driver.get(search_url)
                time.sleep(random.uniform(2, 4))
                
        except Exception as e:
            utils.printred(f"JobsDB: Error returning to job list: {str(e)}")
            self.driver.get(self.base_url)
            time.sleep(random.uniform(2, 4))

    def _discard_application(self) -> None:
        """Discard JobsDB application and return to job listing"""
        try:
            utils.printyellow("JobsDB: Discarding application")
            self._return_to_job_list()
        except Exception as e:
            utils.printred(f"JobsDB: Error discarding application: {str(e)}")
            self.driver.get(self.base_url)
