import time
import random
from typing import Optional, Tuple, Dict, Any
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from src.base.base_authenticator import BaseAuthenticator
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, ElementNotInteractableException



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
        """
        Check if user is currently logged in to JobsDB
        Strategy 1: Direct page access verification (similar to LinkedIn approach)
        """
        try:
            print("🔍 检测 JobsDB 登录状态...")
            
            # Save current URL to restore later if needed
            original_url = self.driver.current_url
            print(f"📍 当前页面: {original_url}")
            
            # Try to access the user profile page (protected page)
            profile_url = 'https://hk.jobsdb.com/profile/me'
            print(f"🔗 尝试访问个人资料页面: {profile_url}")
            
            self.driver.get(profile_url)
            time.sleep(3)  # Wait for page load and any redirects
            
            final_url = self.driver.current_url
            print(f"📍 最终页面: {final_url}")
            
            # If redirected to login page, user is not logged in
            if '/oauth/login' in final_url or '/login' in final_url:
                print("❌ 检测结果: 未登录 (重定向到登录页面)")
                return False
            
            # If we're on a profile page, user is logged in
            if '/profile' in final_url:
                print("✅ 检测结果: 已登录 (成功访问个人资料页面)")
                return True
            
            # Unknown state
            print(f"⚠️ 检测结果: 未知状态 (页面: {final_url})")
            return False
            
        except Exception as e:
            print(f"❌ 登录检测异常: {str(e)}")
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
            
            # Step 3: Wait for manual verification code input (similar to LinkedIn security check)
            # Add a delay to allow page transition after sending verification code
            time.sleep(5)  # Wait for page to load verification code input form
            
            # Step 4: Handle verification process (manual user input with 5-minute timeout)
            self.handle_verification_wait()
            
            # Step 5: Verify login success
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

    def handle_verification_wait(self) -> None:
        """
        Handle verification code input wait - similar to LinkedIn's security check.
        Waits up to 5 minutes for user to manually enter verification code.
        """
        try:
            print("\n" + "="*70)
            print("📧 EMAIL VERIFICATION REQUIRED")
            print("="*70)
            print(f"A verification code has been sent to: {self.email}")
            print("Please check your email and enter the verification code in the browser.")
            print("The system will wait for up to 5 minutes for completion.")
            print("="*70)
            
            # Store current URL to detect changes
            current_url = self.driver.current_url
            
            # Wait for verification to complete (5 minutes timeout like LinkedIn)
            print("⏳ Waiting for verification code input...")
            print("(Timeout: 5 minutes)")
            
            # Monitor for URL changes or login indicators
            WebDriverWait(self.driver, 300).until(  # 300 seconds = 5 minutes
                lambda driver: (
                    # Check if URL changed (indicating successful verification)
                    driver.current_url != current_url or
                    # Check if we're on logged-in pages
                    any(indicator in driver.current_url.lower() 
                        for indicator in ["profile", "member", "dashboard", "feed"]) or
                    # Check for logged-in indicators on page
                    self.is_logged_in()
                )
            )
            
            print("✅ Verification completed successfully!")
            
        except TimeoutException:
            print("\n⏱️ Verification timeout (5 minutes elapsed).")
            print("Please complete the verification manually or try again.")
            print(f"Current URL: {self.driver.current_url}")
            
            # Give user another chance to complete manually
            print("\n🔄 You can still complete the verification manually.")
            print("The system will wait for your confirmation...")
            input("Press Enter after completing the verification manually...")
            
            # Check if login was successful after manual completion
            if self.is_logged_in():
                print("✅ Manual verification completed successfully!")
            else:
                print("❌ Login still not detected. Please check the browser.")
                raise Exception("Verification failed - login not completed")

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
