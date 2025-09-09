import time
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.base_authenticator import BaseAuthenticator


class JobsDBAuthenticator(BaseAuthenticator):
    """
    JobsDB-specific authenticator implementation.
    Handles login, security challenges, and session management for JobsDB platform.
    """
    
    def __init__(self, driver=None):
        super().__init__(driver)

    def get_platform_urls(self):
        """Return JobsDB-specific URLs"""
        return (
            "https://hk.jobsdb.com",
            "https://hk.jobsdb.com/login", 
            "https://hk.jobsdb.com/member/profile"
        )

    def get_login_selectors(self):
        """Return JobsDB-specific CSS selectors for login elements"""
        return {
            'email_field': 'email',
            'password_field': 'password', 
            'submit_button': '//button[@type="submit" or contains(@class, "login-button") or contains(text(), "Login") or contains(text(), "Sign in")]'
        }

    def get_logged_in_indicator(self):
        """Return JobsDB-specific logged in indicator"""
        return {
            'selector': 'profile-menu',
            'text': 'My Profile'
        }

    def handle_security_check(self):
        """Handle JobsDB-specific security challenges"""
        try:
            # Check for captcha or other security measures
            # JobsDB might have different security checkpoint patterns
            current_url = self.driver.current_url
            
            # Wait a bit to see if there are any security challenges
            time.sleep(3)
            
            # Check for common security elements
            security_indicators = [
                '//div[contains(@class, "captcha")]',
                '//div[contains(@class, "security")]',
                '//div[contains(@class, "verification")]',
                '//input[@type="text" and contains(@placeholder, "verification")]'
            ]
            
            for indicator in security_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element.is_displayed():
                        print("Security challenge detected on JobsDB. Please complete manually.")
                        # Wait for user to complete the challenge
                        WebDriverWait(self.driver, 300).until(
                            lambda driver: driver.current_url != current_url or 
                                          "profile" in driver.current_url.lower() or
                                          "member" in driver.current_url.lower()
                        )
                        print("Security challenge completed.")
                        return
                except NoSuchElementException:
                    continue
                    
        except TimeoutException:
            print("Security check timeout. Proceeding with login attempt.")

    def is_logged_in(self):
        """Check if user is logged in to JobsDB"""
        try:
            # First check if we're already on a logged-in page
            current_url = self.driver.current_url
            if any(indicator in current_url.lower() for indicator in ['profile', 'member', 'dashboard']):
                return True
                
            # Navigate to a page that requires login to verify
            self.driver.get('https://hk.jobsdb.com/member/profile')
            time.sleep(2)
            
            # Check for login indicators
            login_indicators = [
                (By.CLASS_NAME, 'profile-menu'),
                (By.CLASS_NAME, 'user-menu'),
                (By.CLASS_NAME, 'member-nav'),
                (By.XPATH, '//a[contains(@href, "logout") or contains(@href, "signout")]'),
                (By.XPATH, '//span[contains(text(), "My Profile") or contains(text(), "Profile")]')
            ]
            
            for by_type, selector in login_indicators:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by_type, selector))
                    )
                    if element.is_displayed():
                        print("User is already logged in to JobsDB.")
                        return True
                except TimeoutException:
                    continue
                    
            # Check if we're redirected to login page
            if 'login' in self.driver.current_url.lower():
                return False
                
        except Exception as e:
            print(f"Error checking login status: {e}")
            
        return False

    def handle_login(self):
        """Enhanced login handling for JobsDB"""
        print("Navigating to JobsDB login page...")
        self.driver.get(self.login_url)
        time.sleep(random.uniform(2, 4))
        
        # Check if already logged in after navigation
        if self.is_logged_in():
            print("Already logged in to JobsDB.")
            return
            
        try:
            self.enter_credentials()
            self.submit_login_form()
            
            # Wait for login completion
            time.sleep(random.uniform(3, 6))
            
            # Handle any security checks
            self.handle_security_check()
            
            # Verify login success
            if self.is_logged_in():
                print("Successfully logged in to JobsDB.")
            else:
                print("Login may have failed. Please check credentials and try again.")
                
        except Exception as e:
            print(f"Login failed with error: {e}")

    def enter_credentials(self):
        """Enter username and password for JobsDB"""
        selectors = self.get_login_selectors()
        
        try:
            # Wait for and find email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, selectors['email_field']))
            )
            
            # Clear and enter email with human-like typing
            email_field.clear()
            self._human_like_type(email_field, self.email)
            time.sleep(random.uniform(0.5, 1.5))
            
            # Find and fill password field
            password_field = self.driver.find_element(By.ID, selectors['password_field'])
            password_field.clear()
            self._human_like_type(password_field, self.password)
            time.sleep(random.uniform(0.5, 1.5))
            
        except TimeoutException:
            print("JobsDB login form not found. The page structure may have changed.")
            raise
        except NoSuchElementException as e:
            print(f"Login form elements not found: {e}")
            raise

    def submit_login_form(self):
        """Submit the JobsDB login form"""
        selectors = self.get_login_selectors()
        
        try:
            # Find login button with multiple fallback strategies
            login_button = None
            
            # Strategy 1: Use the defined XPath
            try:
                login_button = self.driver.find_element(By.XPATH, selectors['submit_button'])
            except NoSuchElementException:
                pass
            
            # Strategy 2: Look for common button classes
            if not login_button:
                try:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, 
                        'button[type="submit"], .btn-login, .login-btn, .submit-btn')
                except NoSuchElementException:
                    pass
            
            # Strategy 3: Look for button with login text
            if not login_button:
                try:
                    login_button = self.driver.find_element(By.XPATH, 
                        '//button[contains(text(), "Log") or contains(text(), "Sign")]')
                except NoSuchElementException:
                    pass
            
            if login_button and login_button.is_enabled():
                # Scroll to button if needed
                self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                time.sleep(0.5)
                
                # Click the login button
                login_button.click()
                print("Login form submitted.")
            else:
                raise NoSuchElementException("No valid login button found")
                
        except NoSuchElementException:
            print("Login button not found. Please verify JobsDB page structure.")
            raise

    def logout(self):
        """Logout from JobsDB"""
        try:
            # Look for logout/signout links
            logout_selectors = [
                '//a[contains(@href, "logout") or contains(@href, "signout")]',
                '//button[contains(text(), "Logout") or contains(text(), "Sign out")]',
                '.logout-link',
                '.signout-link'
            ]
            
            for selector in logout_selectors:
                try:
                    if selector.startswith('//'):
                        logout_element = self.driver.find_element(By.XPATH, selector)
                    else:
                        logout_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if logout_element.is_displayed():
                        logout_element.click()
                        time.sleep(2)
                        print("Successfully logged out from JobsDB.")
                        return
                        
                except NoSuchElementException:
                    continue
                    
            print("Logout link not found. User may need to logout manually.")
            
        except Exception as e:
            print(f"Error during logout: {e}")

    def handle_cookie_consent(self):
        """Handle cookie consent popup if present"""
        try:
            # Common cookie consent selectors
            cookie_selectors = [
                '//button[contains(text(), "Accept") or contains(text(), "OK") or contains(text(), "Agree")]',
                '.cookie-accept',
                '.accept-cookies',
                '#cookie-accept'
            ]
            
            for selector in cookie_selectors:
                try:
                    if selector.startswith('//'):
                        cookie_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        cookie_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    cookie_button.click()
                    print("Cookie consent accepted.")
                    time.sleep(1)
                    return
                    
                except TimeoutException:
                    continue
                    
        except Exception:
            # No cookie consent found or error handling it - not critical
            pass

    def start(self):
        """Start authentication process for JobsDB"""
        urls = self.get_platform_urls()
        self.base_url, self.login_url, self.feed_url = urls
        
        print(f"Starting JobsDB authentication at {self.base_url}")
        self.driver.get(self.base_url)
        self.wait_for_page_load()
        
        # Handle cookie consent if present
        self.handle_cookie_consent()
        
        if not self.is_logged_in():
            self.handle_login()
        else:
            print("Already logged in to JobsDB.")
