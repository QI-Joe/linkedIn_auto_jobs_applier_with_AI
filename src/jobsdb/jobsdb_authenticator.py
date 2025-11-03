import time
import random
from typing import Optional, Tuple, Dict, Any
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from src.base.base_authenticator import BaseAuthenticator


class JobsDBAuthenticator(BaseAuthenticator):
    """
    JobsDB-specific authenticator implementation.
    Handles email verification-based login flow for JobsDB platform.
    
    Authentication Flow:
    1. Navigate to login page
    2. Enter email address
    3. Request verification code
    4. Monitor URL changes while user completes verification manually
    5. Complete login process
    """
    
    def __init__(self, driver: Optional[WebDriver] = None) -> None:
        super().__init__(driver)

    def get_platform_urls(self) -> Tuple[str, str, str]:
        """Return JobsDB-specific URLs"""
        return (
            "https://hk.jobsdb.com",
            "https://hk.jobsdb.com/oauth/login/?returnUrl=%2F", 
            "https://hk.jobsdb.com/"  # feed_url - main dashboard after login
        )

    def get_login_selectors(self) -> Dict[str, str]:
        """Return JobsDB-specific CSS selectors for email verification flow"""
        return {
            'email_field': 'input[type="email"], input[id="emailAddress"], #email, #emailAddress',
            'send_code_button': 'button[type="submit"], .continue-button, button:contains("Continue"), button:contains("Send")',
            'verification_code_field': 'input[name="code"], input[type="text"][placeholder*="code"], #verification-code',
            'verify_button': 'button[type="submit"], .verify-button, button:contains("Verify"), button:contains("Sign in")'
        }

    def get_logged_in_indicator(self) -> Dict[str, str]:
        """Return JobsDB-specific logged in indicator"""
        return {
            'selector': '[data-automation="member-menu"], .profile-menu, a[href*="/member/"], a[href*="/profile/"]',
            'text': 'My Profile'
        }

    def is_logged_in(self) -> bool:
        """Check if user is currently logged in to JobsDB"""
        try:
            # Check if we're on a member/profile page
            current_url = self.driver.current_url
            if any(indicator in current_url for indicator in ["/member/", "/profile/", "/dashboard/"]):
                return True
            
            # Check for profile menu or member indicators
            profile_indicators = [
                '[data-automation="member-menu"]',
                '.profile-menu',
                'a[href*="/member/"]',
                'a[href*="/profile/"]',
                '[class*="profile"]',
                '[class*="member"]'
            ]
            
            for indicator in profile_indicators:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                    if element.is_displayed():
                        return True
                except NoSuchElementException:
                    continue
                    
            return False
            
        except Exception as e:
            print(f"Error checking login status: {e}")
            return False

    def handle_login(self) -> None:
        """Handle JobsDB email verification login flow"""
        print("Starting JobsDB authentication process...")
        
        # Navigate to login page
        print("Navigating to JobsDB login page...")
        self.driver.get(self.login_url)
        
        # Check if already logged in
        if self.is_logged_in():
            print("User is already logged in to JobsDB.")
            return
        
        try:
            # Step 1: Enter email address
            self.enter_email()
            
            # Step 2: Request verification code
            self.request_verification_code()
            
            # Step 3: Handle verification process (manual user input with URL monitoring)
            self.handle_security_check()
            
            # Step 4: Verify login success
            self.verify_login_success()
            
        except Exception as e:
            print(f"JobsDB login failed: {e}")
            raise

    def enter_email(self) -> None:
        """Enter email address in the login form"""
        try:
            print("Entering email address...")
            
            # Wait for email field to be present
            email_selectors = [
                'input[type="email"]',
                'input[name="emailAddress_seekanz"]',
                'input[autocomplete="seekanz username"]'
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not email_field:
                raise NoSuchElementException("Email field not found on JobsDB login page")
            
            # Clear and enter email
            email_field.clear()
            email_field.send_keys(self.email)
            print(f"Email entered: {self.email}")
            
            # Add human-like delay
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error entering email: {e}")
            raise

    def request_verification_code(self) -> None:
        """Click button to request verification code"""
        try:
            print("Requesting verification code...")
            
            # Find and click the send code button
            button_selectors = [
                'button[type="submit"]',
                'button[data-cy="login"]'
                '.continue-button',
                'button:contains("Email me a sign in code")',
                'button:contains("sign in code")',
                'button:contains("Email me")',
                '.btn-primary'
            ]
            
            send_button = None
            for selector in button_selectors:
                try:
                    if ":contains(" in selector:
                        # Convert to XPath for text-based selectors
                        text = selector.split(':contains("')[1].split('")')[0]
                        xpath_selector = f"//button[contains(text(), '{text}')]"
                        send_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, xpath_selector))
                        )
                    else:
                        send_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    break
                except TimeoutException:
                    continue
            
            if not send_button:
                raise NoSuchElementException("Send code button not found")
            
            send_button.click()
            print("Verification code request sent")
            
            # Wait for page transition
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            print(f"Error requesting verification code: {e}")
            raise



    def verify_login_success(self) -> None:
        """Verify that login was successful"""
        try:
            # Wait for redirect to dashboard/profile
            WebDriverWait(self.driver, 15).until(
                lambda d: self.is_logged_in()
            )
            
            print("✅ JobsDB login successful!")
            print(f"Current URL: {self.driver.current_url}")
            
        except TimeoutException:
            print("❌ Login verification timed out")
            print(f"Current URL: {self.driver.current_url}")
            raise Exception("Failed to verify successful login")

    def login_and_go(self, current_url: str):
        try:
            print("\n" + "="*60)
            print("VERIFICATION CODE REQUIRED")
            print("="*60)
            print(f"A verification code has been sent to: {self.email}")
            print("Please check your email and enter the verification code directly in the browser.")
            print("The system will monitor for successful login completion.")
            print("="*60)
            
            # Wait for user to complete verification and login
            print("Waiting for you to complete the verification process...")
            print("(Timeout: 5 minutes)")
            
            WebDriverWait(self.driver, 300).until(
                lambda driver: (
                    driver.current_url != current_url and
                    any(indicator in driver.current_url.lower() 
                        for indicator in ["profile", "member", "dashboard", "feed"]) or
                    self.is_logged_in()
                )
            )
            
            print("✅ Verification completed successfully!")
            
        except TimeoutException:
            print("⏱️ Verification timeout. Please try again or complete manually.")
            print(f"Current URL: {self.driver.current_url}")
            
            # Give user another chance to complete manually
            print("\nYou can still complete the verification manually.")
            input("Press Enter after completing the verification manually...")
            

    def handle_security_check(self) -> None:
        """Handle JobsDB-specific security challenges"""
        try:
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()
            
            # Check for common security challenges
            security_indicators = [
                "captcha",
                "verification", 
                "challenge",
                "security-check",
                "verify",
                "suspicious"
            ]
            
            for indicator in security_indicators:
                if indicator in current_url.lower() or indicator in page_source:
                    print(f"🔒 Security challenge detected: {indicator}")
                    print("Please complete the security check manually in the browser...")
                    
                    # Wait for user to complete security check
                    input("Press Enter after completing the security check...")
                    break
            
            # Additional wait for any post-login processing
            time.sleep(random.uniform(2, 4))
            
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
