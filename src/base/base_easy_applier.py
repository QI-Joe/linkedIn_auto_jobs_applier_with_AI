import json
import os
import random
import tempfile
import time
import traceback
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Tuple
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver import ActionChains
import src.utils as utils


class BaseEasyApplier(ABC):
    """
    Abstract base class for job application handling.
    Provides common form processing and interaction patterns.
    """
    
    def __init__(self, driver: Any, resume_dir: Optional[str], set_old_answers: List[Tuple[str, str, str]], gpt_answerer: Any, resume_generator_manager):
        if resume_dir is None or not os.path.exists(resume_dir):
            resume_dir = None
        self.driver = driver
        self.resume_path = resume_dir
        self.set_old_answers = set_old_answers
        self.gpt_answerer = gpt_answerer
        self.resume_generator_manager = resume_generator_manager
        self.all_data = self._load_questions_from_json()

    def _load_questions_from_json(self) -> List[dict]:
        """Load previously answered questions from JSON file"""
        output_file = 'answers.json'
        try:
            try:
                with open(output_file, 'r') as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, list):
                            raise ValueError("JSON file format is incorrect. Expected a list of questions.")
                    except json.JSONDecodeError:
                        data = []
            except FileNotFoundError:
                data = []
            return data
        except Exception:
            tb_str = traceback.format_exc()
            raise Exception(f"Error loading questions data from JSON file: \nTraceback:\n{tb_str}")

    @abstractmethod
    def get_platform_selectors(self):
        """Return platform-specific CSS selectors"""
        pass

    @abstractmethod
    def _find_apply_button(self) -> WebElement:
        """Find and return the apply button for the platform"""
        pass

    @abstractmethod
    def job_apply(self, job: Any):
        """Main job application method - platform specific implementation"""
        pass

    def _scroll_page(self) -> None:
        """Scroll page to ensure elements are visible - reusable across platforms"""
        scrollable_element = self.driver.find_element(By.TAG_NAME, 'html')
        utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=False)
        utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=True)

    def _human_like_type(self, element: WebElement, text: str) -> None:
        """Type text with human-like delays"""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

    def _click_with_retry(self, element: WebElement, max_attempts: int = 3) -> bool:
        """Click element with retry logic"""
        for attempt in range(max_attempts):
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(element).click().perform()
                return True
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(random.uniform(1, 2))
        return False

    def _wait_for_element(self, by: By, selector: str, timeout: int = 10) -> WebElement:
        """Wait for element to be present and return it"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def _wait_for_clickable_element(self, by: By, selector: str, timeout: int = 10) -> WebElement:
        """Wait for element to be clickable and return it"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )

    def _find_and_handle_text_question(self, section: WebElement) -> bool:
        """Handle text input questions - reusable across platforms"""
        try:
            text_fields = section.find_elements(By.TAG_NAME, 'input') + section.find_elements(By.TAG_NAME, 'textarea')
            for field in text_fields:
                if field.get_attribute('type') in ['text', 'email', 'tel'] or field.tag_name == 'textarea':
                    question_text = self._extract_question_text(section)
                    answer = self.gpt_answerer.answer_question_textual_wide_range(question_text)
                    self._human_like_type(field, answer)
                    return True
        except Exception:
            pass
        return False

    def _find_and_handle_dropdown_question(self, section: WebElement) -> bool:
        """Handle dropdown questions - reusable across platforms"""
        try:
            dropdowns = section.find_elements(By.TAG_NAME, 'select')
            for dropdown in dropdowns:
                select = Select(dropdown)
                options = [option.text for option in select.options if option.text.strip()]
                if len(options) > 1:
                    question_text = self._extract_question_text(section)
                    answer = self.gpt_answerer.answer_question_from_options(question_text, options)
                    select.select_by_visible_text(answer)
                    return True
        except Exception:
            pass
        return False

    def _find_and_handle_radio_question(self, section: WebElement) -> bool:
        """Handle radio button questions - reusable across platforms"""
        try:
            radios = section.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            if radios:
                question_text = self._extract_question_text(section)
                options = []
                for radio in radios:
                    label_element = section.find_element(By.CSS_SELECTOR, f'label[for="{radio.get_attribute("id")}"]')
                    options.append(label_element.text.strip())
                
                if options:
                    answer = self.gpt_answerer.answer_question_from_options(question_text, options)
                    self._select_radio(radios, answer)
                    return True
        except Exception:
            pass
        return False

    def _select_radio(self, radios: List[WebElement], answer: str) -> None:
        """Select radio button based on answer text"""
        for radio in radios:
            try:
                parent = radio.find_element(By.XPATH, '..')
                if answer.lower() in parent.text.lower():
                    self._click_with_retry(radio)
                    break
            except Exception:
                continue

    def _extract_question_text(self, section: WebElement) -> str:
        """Extract question text from form section"""
        try:
            # Try common question text containers
            question_selectors = [
                'label', '.form-label', '.question-text', 
                'h3', 'h4', '.field-label', '[data-test-id*="question"]'
            ]
            
            for selector in question_selectors:
                try:
                    question_element = section.find_element(By.CSS_SELECTOR, selector)
                    question_text = question_element.text.strip()
                    if question_text and len(question_text) > 3:
                        return question_text
                except NoSuchElementException:
                    continue
            
            # Fallback: use section text
            return section.text.strip()
        except Exception:
            return "Unknown question"

    def _is_upload_field(self, element: WebElement) -> bool:
        """Check if element is a file upload field"""
        try:
            file_inputs = element.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            upload_buttons = element.find_elements(By.XPATH, './/*[contains(text(), "Upload") or contains(text(), "Choose") or contains(text(), "Browse")]')
            return len(file_inputs) > 0 or len(upload_buttons) > 0
        except Exception:
            return False

    def _handle_upload_fields(self, element: WebElement, job: Any) -> None:
        """Handle file upload fields - reusable across platforms"""
        try:
            file_inputs = element.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            for file_input in file_inputs:
                if self.resume_path and os.path.exists(self.resume_path):
                    file_input.send_keys(str(self.resume_path))
                    time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"Failed to upload file: {str(e)}")

    def _check_for_errors(self) -> bool:
        """Check for form validation errors"""
        try:
            error_selectors = [
                '.error', '.field-error', '.validation-error', 
                '[role="alert"]', '.alert-danger', '.form-error'
            ]
            
            for selector in error_selectors:
                errors = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if errors:
                    error_texts = [error.text for error in errors if error.is_displayed()]
                    if error_texts:
                        print(f"Form errors detected: {error_texts}")
                        return True
            return False
        except Exception:
            return False

    def _save_questions_to_json(self, questions_data) -> None:
        """Save questions and answers to JSON file - supports both single dict and list"""
        output_file = 'answers.json'
        try:
            # Handle both single question dict and list of questions
            if isinstance(questions_data, dict):
                questions_list = [questions_data]
            else:
                questions_list = questions_data
                
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(questions_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save questions to JSON: {str(e)}")

    def _discard_application(self) -> None:
        """Discard application - should be implemented by specific platforms"""
        pass
