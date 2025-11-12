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
from src.utils.coverLetter import CoverLetterPDF
import src.utils.strings as strings
from collections import defaultdict
import re

def charIsIn(receiver: str, examiner: list[str]):
    recvlist = receiver.split()
    for token in recvlist:
        if token.strip().upper() in examiner:
            return True, token.upper()
    return False, None

DOCUMENT_STYLE = strings.DOCUMENT_STYLE

class JobsDBEasyApplier(BaseEasyApplier):
    """
    JobsDB-specific easy applier implementation.
    Handles JobsDB application forms with page navigation instead of modals.
    """
    
    def __init__(self, driver: Any, resume_dir: Optional[str], set_old_answers: List, gpt_answerer: Any, resume_generator_manager):
        super().__init__(driver, resume_dir, set_old_answers, gpt_answerer, resume_generator_manager)
        self.base_url = "https://hk.jobsdb.com"
        self.cover_letter_operator = CoverLetterPDF()

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
            
            time.sleep(5)
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
                
                current_windows_handle = list(self.driver.window_handles)[0]
                current_windows_url = self.driver.current_url
                if self.job_title not in str(current_windows_url):
                    return True, current_windows_handle
                return False, current_windows_handle
            except Exception:
                # should add in log...
                continue
        

    def _wait_for_sidebar(self, jumped:bool) -> WebElement:
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
            'title': 'h1[data-automation="job-detail-title"]',
            'company': '[data-automation="advertiser-name"]',
            'work_style': '[data-automation="job-detail-work-type"]',
            'salary': '[data-automation="job-detail-salary"]',
            'link': self.driver.current_url,
            'detailed_page': dict(),
        }
        
        # Extract title
        for k, v in info.items():
            try:
                element = sidebar.find_element(By.CSS_SELECTOR, v)
                text = element.text.strip()
                info[k] = text
            except Exception:
                continue
        
        info["detailed_page"] = self.sidebar_job_detail(sidebar)
        
        return info

    def _el_text(self, el: WebElement) -> str:
        # More consistent text for lists: join <li> with newline
        tag = el.tag_name.lower()
        if tag == "ul" or tag == "ol":
            lis = el.find_elements(By.XPATH, "./li")
            return "\n".join(li.text.strip() for li in lis if li.text.strip())
        return el.text.strip()

    def sidebar_job_detail(self, sidebar: WebElement) -> dict:
        """
        Walk direct children (<p>, <ul>, etc.) of the job detail container.
        Detect section titles as <p><strong>Title:</strong></p> and
        collect subsequent siblings until the next title.
        Returns:
        - full_text: str
        - sections: dict { title: "joined text" }
        """
        container: WebElement = sidebar.find_element(By.CSS_SELECTOR, 'div[data-automation="jobAdDetails"]')

        # 2) Structured sections
        sections = {}
        current_title = None
        buffer, intro_idx = [], 1

        children = container.find_elements(By.XPATH, "./*")  # only direct children of the wrapper div
        for child in children:
            # Is this child a title paragraph? (contains a <strong> … >)
            strongs = child.find_elements(By.XPATH, ".//strong[normalize-space()]")
            if strongs:
                # Flush previous section
                if current_title and buffer:
                    sections[current_title] = "\n".join(b for b in buffer if b)
                buffer = []

                # New title
                title_raw = strongs[0].text.strip()
                title = title_raw.rstrip(":：")  # normalize trailing colon
                current_title = title
                # If the title paragraph has more text after <strong>, capture it too
                # (rare, but harmless)
                remaining = child.text.replace(title_raw, "", 1).strip()
                if remaining:
                    buffer.append(remaining)
            else:
                # Not a title: content line for current section (or intro if no title yet)
                txt = self._el_text(child)
                if txt:
                    if not current_title:
                        current_title = "Intro" + str(intro_idx)
                        intro_idx += 1
                    buffer.append(txt)

        # Flush last section
        if current_title and buffer:
            sections[current_title] = "\n".join(b for b in buffer if b)

        return sections
        

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
            if new_windows[0] is None:
                new_windows = set(self.driver.window_handles) - existing_windows            
                # Switch to new tab
                new_window = list(new_windows)[0]
                self.driver.switch_to.window(new_window)
            
            job_info = self.gpt_answerer.job_info_parser(job_info)
            job_info["selected_document"] = DOCUMENT_STYLE[job_info["selected_document_index"]]
            
            self.cover_letter_operator.load_and_generate(job_info=job_info)
            try:
                # Add debugging info before upload
                # utils.printyellow(f"JobsDB: Current URL before upload: {self.driver.current_url}")
                # utils.printyellow(f"JobsDB: Number of windows: {len(self.driver.window_handles)}")
                # utils.printyellow(f"JobsDB: Current window handle: {self.driver.current_window_handle}")
                
                # Wait a bit for page to fully load
                time.sleep(2)
                
                self.document_page_control() # include resume select and cover letter selection
                
                time.sleep(random.uniform(1, 3))
                current_url = self.driver.current_url
                if re.search(r'role-requirement?', str(current_url)):
                    self.fillin_form()  # include personal information fill-in
                
                    time.sleep(random.uniform(1, 4))
                    self.press_continuous_button() # press continue button in fillin form page
                
                time.sleep(random.uniform(2,5))
                
                self.press_continuous_button() # press continue button in "Update Jobsdb Profile" page
                
                time.sleep(random.uniform(2,5))
                
                self.press_continuous_button(False, True) # press continue button in "Review and Submit" page

                
                utils.printyellow(f"JobsDB: Applied to {job_info['title']} at {job_info['company']}")
                return True
                
            except Exception as e:
                utils.printred(f"JobsDB: Form filling failed: {str(e)}")
                utils.printred(f"JobsDB: Current URL when failed: {self.driver.current_url}")
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

    def document_page_control(self):
        """
        resume selection and cover letter upload
        """
        resume_upload={
            "name": "resume",
            "fieldset": "id^='resume-method-'",
            "inputset": "resume-method-upload",
            "input_click": "resume-fileFile"
        }
        coverletter_upload = {
            "name": "coverLetter",
            "fieldset": "id^='coverLetter-method-'",
            "inputset": "coverLetter-method-upload",
            "input_click": "coverLetter-fileFile"
        }

        self.info_upload(web_pattern=resume_upload)
        self.info_upload(web_pattern=coverletter_upload)

        btn = WebDriverWait(self.driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='continue-button']"))
            )
        # scroll into view (helps avoid intercepts)
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        btn.click()
        return True


    def info_upload(self, web_pattern: dict):
        """Upload document to JobsDB application form"""
        try:
            utils.printyellow(f"JobsDB: Starting {web_pattern['name']} upload...")
            wait = WebDriverWait(self.driver, 20, poll_frequency=0.2)

            # 1) Wait for the radiogroup to be visible
            group = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, f"fieldset[role='radiogroup'][{web_pattern['fieldset']}]"))
            )
            utils.printyellow("JobsDB: Found radiogroup")

            # 2) Find the upload radio and its label - click the label, not the input
            upload_radio = group.find_element(By.CSS_SELECTOR, f"input[type='radio'][data-testid={web_pattern['inputset']}]")
            radio_id = upload_radio.get_attribute("id")
            upload_label = group.find_element(By.CSS_SELECTOR, f"label[for='{radio_id}']")
            utils.printyellow(f"JobsDB: Found radio with ID: {radio_id}")

            # 3) Scroll label into view and click it
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", upload_label)
            time.sleep(0.1)

            # Check if already selected
            is_selected = upload_radio.is_selected() or upload_radio.get_attribute("aria-checked") == "true"
            
            if not is_selected:
                # Click the label (not the hidden input)
                upload_label.click()
                utils.printyellow("JobsDB: Clicked upload label")
                
                # Wait for selection to take effect
                wait.until(lambda d: upload_radio.is_selected() or upload_radio.get_attribute("aria-checked") == "true")
            
            utils.printyellow("JobsDB: Upload option selected")

            # 4) Find file input - it exists but is hidden
            file_input = group.find_element(By.CSS_SELECTOR, f"input#{web_pattern['input_click']}[data-testid='file-input'][type='file']")
            
            # 5) Make file input interactable (keep it off-screen but functional)
            self.driver.execute_script("""
                const el = arguments[0];
                el.style.display = 'block';
                el.style.visibility = 'visible';
                el.style.opacity = '1';
                el.style.position = 'fixed';
                el.style.left = '-9999px';
                el.style.top = '0';
                el.style.width = '1px';
                el.style.height = '1px';
                el.removeAttribute('hidden');
            """, file_input)
            
            # 6) Upload file
            doc_path = self.cover_letter_operator.get_cover_letter_path()
            if web_pattern['name'] == "resume":
                doc_path = self.cover_letter_operator.get_resume_path()

            if not doc_path or not os.path.exists(doc_path):
                raise Exception(f"{web_pattern['name']} file not found")

            file_input.send_keys(str(doc_path))
            utils.printyellow(f"JobsDB | Uploaded {web_pattern['name']} file: {doc_path}")

            # 7) Verify upload by checking file input value
            file_name = os.path.basename(doc_path)
            wait.until(lambda d: file_name.lower() in (file_input.get_attribute("value") or "").lower())
            utils.printyellow("JobsDB: Upload confirmed")
            
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            utils.printred(f"JobsDB: Cover letter upload failed: {str(e)}")
            raise Exception(f"Failed to upload cover letter: {str(e)}")

    def fillin_form(self):
        """
        Fill in JobsDB application form after cover letter upload
        """
        try:
            utils.printyellow("JobsDB: Starting form filling...")
            
            # Wait for form to load
            form = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "form"))
            )
            utils.printyellow("JobsDB: Form loaded successfully")
            
            # Process single select problems (radio buttons)
            self.capture_single_select_problem(form)
            
            time.sleep(random.uniform(1, 4))
            # Process dropdown problems
            self.capture_dropdown_problem(form)
            time.sleep(random.uniform(1, 4))
            self.capture_multi_select_problem()
            
            utils.printyellow("JobsDB: Form filling completed successfully")
            return True
            
        except Exception as e:
            utils.printred(f"JobsDB: Form filling failed or job not require side question answering: {str(e)}")
            raise

    def capture_single_select_problem(self, form: WebElement):
        """
        Capture and answer single select problems (radio button groups) in JobsDB form
        Based on observed structure: fieldset with role='radiogroup' containing question and options
        """
        utils.printyellow("JobsDB: Processing single select problems...")
        
        # Find all fieldset elements with role='radiogroup' (single select problems)
        fieldsets = form.find_elements(By.CSS_SELECTOR, "fieldset[role='radiogroup']")
        
        if not fieldsets:
            utils.printyellow("JobsDB: No single select problems found")
            return
        
        utils.printyellow(f"JobsDB: Found {len(fieldsets)} single select problem(s)")
        
        for i, fieldset in enumerate(fieldsets):
            try:
                utils.printyellow(f"JobsDB: Processing single select problem {i+1}")
                
                # 1. Extract question text from legend element
                question_text = ""
                try:
                    legend = fieldset.find_element(By.CSS_SELECTOR, "legend")
                    question_text = legend.text.strip()
                except:
                    utils.printred(f"JobsDB: Could not find question text for single select {i+1}")
                    continue
                
                if not question_text:
                    utils.printred(f"JobsDB: Empty question text for single select {i+1}")
                    continue
                
                # 2. Extract all radio options
                radio_inputs = fieldset.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                
                if not radio_inputs:
                    utils.printred(f"JobsDB: No radio options found for single select {i+1}")
                    continue
                
                options = {}
                option_elements = {}
                
                for j, radio in enumerate(radio_inputs):
                    try:
                        # Get radio input ID to find corresponding label
                        radio_id = radio.get_attribute("id")
                        if not radio_id:
                            continue
                        
                        # Find label for this radio button
                        label = fieldset.find_element(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                        option_text = label.text.strip()
                        
                        if option_text:
                            option_key = chr(65 + j)  # A, B, C, D...
                            options[option_key] = option_text
                            option_elements[option_key] = radio
                            
                    except Exception as e:
                        utils.printred(f"JobsDB: Error extracting option {j+1}: {str(e)}")
                        continue
                
                if not options:
                    utils.printred(f"JobsDB: No valid options found for single select {i+1}")
                    continue
                
                # 3. Prepare question for AI
                ai_question = {
                    "Question": question_text,
                    "options": options
                }
                
                utils.printyellow(f"JobsDB: Question: {question_text}")
                utils.printyellow(f"JobsDB: Options: {options}")
                
                # 4. Ask AI for answer
                try:
                    ai_answer = self.gpt_answerer.standard_simplified_profile_chain(ai_question)
                    
                    selected_option = ai_answer[0]  # Take first answer from list
                    utils.printyellow(f"JobsDB: AI selected option: {selected_option}")
                    
                    # 5. Select the corresponding radio button
                    inrelation, selected_option = charIsIn(selected_option, option_elements.keys())
                    if inrelation:
                        radio_element = option_elements[selected_option]
                        
                        # Scroll to element and click
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", radio_element)
                        time.sleep(0.2)
                        
                        # Click the radio button
                        self._click_with_retry(radio_element)
                        utils.printyellow(f"JobsDB: Successfully selected option {selected_option}: {options[selected_option]}")
                        
                    else:
                        raise Exception(f"JobsDB: AI answer '{selected_option}' not found in available options")
                        
                except Exception as e:
                    utils.printred(f"JobsDB: Error getting AI answer for single select {i+1}: {str(e)}")
                    continue
                    
            except Exception as e:
                utils.printred(f"JobsDB: Error processing single select problem {i+1}: {str(e)}")
                continue
        
        utils.printyellow("JobsDB: Finished processing all single select problems")
            

    def capture_dropdown_problem(self, form: WebElement):
        """
        Capture and answer dropdown problems in JobsDB form
        Based on markdown instructions: find label[for^='question-'] and corresponding select elements
        """
        try:
            utils.printyellow("JobsDB: Processing dropdown problems...")
            
            # Find all question labels and select elements directly
            label_section = form.find_elements(By.CSS_SELECTOR, "label[for^='question-']")
            answer_section = form.find_elements(By.CSS_SELECTOR, "select")
            
            if not label_section or not answer_section:
                utils.printyellow("JobsDB: No dropdown problems found")
                return
            
            utils.printyellow(f"JobsDB: Found {len(label_section)} question labels and {len(answer_section)} select elements")
            
            for i, (asked_question, answers) in enumerate(zip(label_section, answer_section)):
                try:
                    utils.printyellow(f"JobsDB: Processing dropdown problem {i+1}")
                    
                    # Extract options from select element
                    given_options = answers.find_elements(By.CSS_SELECTOR, "option")
                    question_text = asked_question.text.strip()
                    options = {}
                    option_values = {}
                    key_index = 0

                    for j, option in enumerate(given_options):
                        try:
                            option_value = option.get_attribute("value")
                            option_text = option.text.strip()
                            if option_value == "" or option_text.lower() == "":
                                continue
                            
                            option_key = chr(65 + key_index)  # A, B, C, D...
                            options[option_key] = option_text
                            option_values[option_key] = option_value
                            key_index += 1  # Only increment when we add a valid option
                                
                        except Exception as e:
                            utils.printred(f"JobsDB: Error extracting option {j+1}: {str(e)}")
                            continue
                    
                    if not options:
                        utils.printred(f"JobsDB: No valid options found for dropdown {i+1}")
                        continue
                    
                    # Prepare question for AI
                    ai_question = {
                        "Question": question_text,
                        "options": options
                    }
                    
                    utils.printyellow(f"JobsDB: Question: {question_text}")
                    utils.printyellow(f"JobsDB: Options: {options}")
                    
                    # Ask AI for answer
                    try:
                        ai_answer = self.gpt_answerer.standard_simplified_profile_chain(ai_question)
                            
                        selected_option = ai_answer[0]  # Take first answer from list
                        utils.printyellow(f"JobsDB: AI selected option: {selected_option}")
                        
                        # Select the corresponding option in dropdown
                        inrelation, selected_option = charIsIn(selected_option, option_values.keys())
                        if inrelation:
                            option_value = option_values[selected_option]
                            
                            # Scroll to select element
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", answers)
                            time.sleep(0.2)
                            
                            # Select the option by value
                            from selenium.webdriver.support.ui import Select
                            select = Select(answers)
                            select.select_by_value(option_value)
                            
                            utils.printyellow(f"JobsDB: Successfully selected option {selected_option}: {options[selected_option]}")
                            
                        else:
                            raise Exception(f"JobsDB: AI answer '{selected_option}' not found in available options")
                            
                    except Exception as e:
                        utils.printred(f"JobsDB: Error getting AI answer for dropdown {i+1}: {str(e)}")
                        continue
                        
                except Exception as e:
                    utils.printred(f"JobsDB: Error processing dropdown problem {i+1}: {str(e)}")
                    continue
            
            utils.printyellow("JobsDB: Finished processing all dropdown problems")
            
        except Exception as e:
            utils.printred(f"JobsDB: Error in capture_dropdown_problem: {str(e)}")
            raise

    def get_question_blocks(self, timeout=10):
        """
        Robust method to extract all questionnaire questions (both checkbox and radio)
        Returns structured data for both single-select and multi-select problems
        """
        # Wait until at least one questionnaire input is present
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[(self::input) and (@type='checkbox' or @type='radio') and starts-with(@name,'questionnaire.')]")
            )
        )

        # 1) Collect all inputs belonging to any questionnaire question
        inputs = self.driver.find_elements(
            By.XPATH,
            "//input[(self::input) and (@type='checkbox' or @type='radio') and starts-with(@name,'questionnaire.')]"
        )

        # 2) Group by the 'name' attribute (one question per distinct name)
        grouped = defaultdict(list)
        for inp in inputs:
            grouped[inp.get_attribute("name")].append(inp)

        questions = []

        for name, inps in grouped.items():
            # Representative input for locating the question prompt
            rep = inps[0]

            # 3) Find the closest ancestor DIV that contains a <strong> (the prompt lives there)
            # Then take the first <strong> inside as the prompt text.
            # This avoids brittle class selectors.
            try:
                prompt_el = rep.find_element(
                    By.XPATH,
                    "ancestor::div[.//strong][1]//strong[1]"
                )
                prompt = prompt_el.text.strip()
            except Exception:
                prompt = ""  # fallback if no strong is found

            # 4) Build options: text via <label for=id>, selected via is_selected()
            options = []
            for inp in inps:
                opt_id = inp.get_attribute("id")
                # Find the label tied to this input
                label_text = ""
                if opt_id:
                    try:
                        label_el = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{opt_id}']")
                        label_text = label_el.text.strip()
                    except Exception:
                        pass
                # Extra fallback: if label not found, try nearby text
                if not label_text:
                    try:
                        label_text = inp.find_element(By.XPATH, "following::label[1]").text.strip()
                    except Exception:
                        label_text = ""

                options.append({
                    "value_id": opt_id,
                    "text": label_text,
                    "selected": inp.is_selected(),  # same as aria-checked == 'true' for checkboxes/radios
                    "aria_checked": inp.get_attribute("aria-checked"),
                    "type": inp.get_attribute("type"),
                    "element": inp  # Keep reference to the element for clicking
                })

            questions.append({
                "name": name,
                "prompt": prompt,
                "options": options
            })

        return questions

    def capture_multi_select_problem(self):
        """
        Improved multi-select checkbox problem handler using robust question block extraction
        Maintains compatibility with existing AI question format and data structures
        """
        print("JobsDB: Processing multi-select problems...")
        
        try:
            # Use the robust method to get all question blocks
            question_blocks = self.get_question_blocks()
            
            if not question_blocks:
                print("JobsDB: No questionnaire problems found")
                return
            
            # Filter for checkbox (multi-select) questions only
            multi_select_questions = [q for q in question_blocks if any(opt["type"] == "checkbox" for opt in q["options"])]
            
            if not multi_select_questions:
                print("JobsDB: No multi-select (checkbox) problems found")
                return
            
            print(f"JobsDB: Found {len(multi_select_questions)} multi-select problem(s)")
            
            for i, question_block in enumerate(multi_select_questions):
                try:
                    print(f"JobsDB: Processing multi-select problem {i+1}")
                    
                    question_text = question_block["prompt"]
                    
                    if not question_text:
                        print(f"JobsDB: Empty question text for multi-select {i+1}")
                        continue
                    
                    # Convert to original format expected by AI
                    options = {}
                    option_elements = {}
                    key_index = 0
                    
                    for option_data in question_block["options"]:
                        if option_data["type"] == "checkbox" and option_data["text"]:
                            option_key = chr(65 + key_index)  # A, B, C, D...
                            options[option_key] = option_data["text"]
                            option_elements[option_key] = option_data["element"]
                            key_index += 1
                    
                    if not options:
                        print(f"JobsDB: No valid checkbox options found for multi-select {i+1}")
                        continue
                    
                    # 3. Prepare question for AI (maintaining original format)
                    ai_question = {
                        "Question": question_text,
                        "options": options
                    }
                    
                    print(f"JobsDB: Question: {question_text}")
                    print(f"JobsDB: Options: {options}")
                    
                    # 4. Ask AI for answer
                    ai_answer = self.gpt_answerer.standard_simplified_profile_chain(ai_question)
                    
                    if not isinstance(ai_answer, list):
                        utils.printred(f"JobsDB: AI answer format invalid for multi-select {i+1}")
                        continue
                    utils.printyellow(f"JobsDB: AI selected options: {ai_answer}")
                    
                    print(f"JobsDB: AI selected options: {ai_answer}")
                    
                    # 5. Select/deselect the corresponding checkboxes
                    for option_key, checkbox_element in option_elements.items():
                        
                        is_selected = checkbox_element.is_selected() or checkbox_element.get_attribute("aria-checked") == "true"
                        should_be_selected = option_key in ai_answer
                        
                        # Only click if state needs to change
                        if is_selected != should_be_selected:
                            # Scroll to element
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox_element)
                            time.sleep(0.2)
                            
                            # Click the checkbox to change state
                            self._click_with_retry(checkbox_element)
                            print(f"JobsDB: {'Selected' if should_be_selected else 'Deselected'} option {option_key}: {options[option_key]}")
                    
                    print(f"JobsDB: Successfully processed multi-select problem {i+1}")
                        
                        
                except Exception as e:
                    print(f"JobsDB: Error processing multi-select problem {i+1}: {str(e)}")
                    continue
            
            print("JobsDB: Finished processing all multi-select problems")
            
        except Exception as e:
            print(f"JobsDB: Error in capture_multi_select_problem: {str(e)}")
            raise
  
    def press_continuous_button(self, continuebutton: bool=True, reviewbutton: bool=False):
        button: str = ''
        
        if continuebutton:
            button='continue-button'
        elif reviewbutton:
            button='review-submit-application'
        else:
            raise Exception("Hey, button confiugration has problem")
        wait = WebDriverWait(self.driver, 20)
        btn: WebDriverWait = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f"button[data-testid='{button}']"))
        )
        btn.click()

    def _discard_application(self) -> None:
        """Discard JobsDB application and return to job listing"""
        try:
            utils.printyellow("JobsDB: Discarding application")
            self._return_to_job_list()
        except Exception as e:
            utils.printred(f"JobsDB: Error discarding application: {str(e)}")
            self.driver.get(self.base_url)
