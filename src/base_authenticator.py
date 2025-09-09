import time
import random
from abc import ABC, abstractmethod
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BaseAuthenticator(ABC):
    """
    Abstract base class for platform authentication.
    Provides common authentication patterns and methods.
    """
    
    def __init__(self, driver=None):
        self.driver = driver
        self.email = ""
        self.password = ""
        self.base_url = ""
        self.login_url = ""
        self.feed_url = ""

    def set_secrets(self, email, password):
        """Set authentication credentials"""
        self.email = email
        self.password = password

    @abstractmethod
    def get_platform_urls(self):
        """Return platform-specific URLs (base_url, login_url, feed_url)"""
        pass

    @abstractmethod
    def get_login_selectors(self):
        """Return platform-specific CSS selectors for login elements"""
        pass

    @abstractmethod
    def get_logged_in_indicator(self):
        """Return selector/method to check if user is logged in"""
        pass

    def start(self):
        """Start authentication process"""
        urls = self.get_platform_urls()
        self.base_url, self.login_url, self.feed_url = urls
        
        print(f"Starting Chrome browser to log in to {self.base_url}")
        self.driver.get(self.base_url)
        self.wait_for_page_load()
        
        if not self.is_logged_in():
            self.handle_login()

    def handle_login(self):
        """Handle the login process"""
        print(f"Navigating to the login page...")
        self.driver.get(self.login_url)
        
        if self.feed_url.split('/')[-1] in self.driver.current_url:
            print("User is already logged in.")
            return
            
        try:
            self.enter_credentials()
            self.submit_login_form()
        except NoSuchElementException:
            print("Could not log in. Please check your credentials.")
        
        time.sleep(random.uniform(30, 40))  # Human-like delay
        self.handle_security_check()

    def enter_credentials(self):
        """Enter username and password using platform-specific selectors"""
        selectors = self.get_login_selectors()
        
        try:
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, selectors['email_field']))
            )
            self._human_like_type(email_field, self.email)
            
            password_field = self.driver.find_element(By.ID, selectors['password_field'])
            self._human_like_type(password_field, self.password)
            
        except TimeoutException:
            print("Login form not found. Aborting login.")

    def _human_like_type(self, element, text):
        """Type text with human-like delays"""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

    def submit_login_form(self):
        """Submit the login form"""
        selectors = self.get_login_selectors()
        
        try:
            login_button = self.driver.find_element(By.XPATH, selectors['submit_button'])
            login_button.click()
        except NoSuchElementException:
            print("Login button not found. Please verify the page structure.")

    def handle_security_check(self):
        """Handle security challenges - can be overridden by platforms"""
        # Default implementation - platforms can override for specific security checks
        pass

    @abstractmethod
    def is_logged_in(self):
        """Check if user is currently logged in"""
        pass

    def wait_for_page_load(self, timeout=10):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        except TimeoutException:
            print("Page load timed out.")

    def logout(self):
        """Logout from the platform - can be implemented by specific platforms"""
        pass
