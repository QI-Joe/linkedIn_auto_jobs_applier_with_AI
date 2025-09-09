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
import src.utils as utils
from src.base_easy_applier import BaseEasyApplier


class JobsDBEasyApplier(BaseEasyApplier):
    """
    JobsDB-specific easy applier implementation.
    Handles JobsDB application forms with page navigation instead of modals.
    """
    
    def __init__(self, driver: Any, resume_dir: Optional[str], set_old_answers: List, gpt_answerer: Any, resume_generator_manager):
        super().__init__(driver, resume_dir, set_old_answers, gpt_answerer, resume_generator_manager)
        self.base_url = "https://hk.jobsdb.com"
        
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

    def job_apply(self, job: Any):
        """Main job application method for JobsDB"""
        try:
            # Navigate to job page
            self.driver.get(job.link)
            time.sleep(random.uniform(3, 5))
            
            # Get job description and set GPT context
            job.set_job_description(self._get_job_description())
            self.gpt_answerer.set_job(job)
            
            # Find and click apply button
            apply_button = self._find_apply_button()
            self._click_with_retry(apply_button)
            
            # Wait for page transition if needed
            time.sleep(random.uniform(2, 4))
            
            # Fill application form(s) - reuse base class logic
            self._fill_application_forms(job)
            
            # Return to job list
            self._return_to_job_list()
            
        except Exception as e:
            tb_str = traceback.format_exc()
            self._discard_application()
            raise Exception(f"Failed to apply to JobsDB job: {str(e)}\\nTraceback:\\n{tb_str}")

    def _find_apply_button(self) -> WebElement:
        """Find JobsDB apply button"""
        selectors = self.get_platform_selectors()['apply_button']
        
        # Scroll to ensure button is visible
        self._scroll_page()
        
        # Try each selector
        for selector in selectors:
            try:
                button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if button.is_displayed() and button.is_enabled():
                    utils.printyellow(f"JobsDB: Found apply button with selector: {selector}")
                    return button
            except (TimeoutException, NoSuchElementException):
                continue
        
        # Fallback: Look for any button with apply-related text
        apply_texts = ["apply now", "quick apply", "apply"]
        for text in apply_texts:
            try:
                button = self.driver.find_element(By.XPATH, 
                    f'//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{text}")]')
                if button.is_displayed() and button.is_enabled():
                    utils.printyellow(f"JobsDB: Found apply button with text: {text}")
                    return button
            except NoSuchElementException:
                continue
        
        raise Exception("No clickable JobsDB apply button found")

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
