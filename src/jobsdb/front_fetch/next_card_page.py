from src.jobsdb.front_fetch.web_library import *

def click_next_page(driver: webdriver, log: logBase):
    """
    Click the JobsDB pagination "Next" control on the main listing page.

    Returns:
        bool: True when navigation to the next page succeeds, False otherwise.
    """
    try:
        current_url = driver.current_url

        # Guard: this helper should run only on the main listing page.
        if "/job/" in str(current_url):
            log.add_log_job({
                "timestamp": time.time(),
                "action": "click_next_page",
                "status": "failure",
                "error": "not_on_main_listing_page",
                "url": current_url,
            })
            return False

        selectors = [
            "a[aria-label='Next'][rel~='next']",
            "a[data-automation^='page-'][aria-label='Next']",
            "a[title='Next'][aria-label='Next']",
        ]

        next_page_el = None
        for selector in selectors:
            try:
                candidate = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if candidate and candidate.is_displayed() and candidate.is_enabled():
                    next_page_el = candidate
                    break
            except Exception:
                continue

        if next_page_el is None:
            log.add_log_job({
                "timestamp": time.time(),
                "action": "click_next_page",
                "status": "failure",
                "error": "next_button_not_found_or_not_clickable",
                "url": current_url,
            })
            return False

        href = next_page_el.get_attribute("href")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_page_el)

        clicked = False
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[aria-label='Next']"))
            )
            next_page_el.click()
            clicked = True
        except Exception:
            if href:
                driver.get(href)
                clicked = True

        if not clicked:
            log.add_log_job({
                "timestamp": time.time(),
                "action": "click_next_page",
                "status": "failure",
                "error": "next_click_failed",
                "url": current_url,
            })
            return False

        WebDriverWait(driver, 10).until(lambda d: d.current_url != current_url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article[data-testid="job-card"]'))
        )
        # 3) 触发懒加载：缓慢滚动到底再回到顶
        last_count = 0
        for _ in range(6):
            driver.execute_script("window.scrollBy(0, document.body.scrollHeight/3);")
            time.sleep(0.6)
            cur = len(driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="job-card"]'))
            if cur == last_count:
                break
            last_count = cur
        driver.execute_script("window.scrollTo(0, 0);")
        
        log.add_log_job({
            "timestamp": time.time(),
            "action": "click_next_page",
            "status": "success",
            "from_url": current_url,
            "to_url": driver.current_url,
        })
        return True
    except Exception as e:
        log.add_log_job({
            "timestamp": time.time(),
            "action": "click_next_page",
            "status": "failure",
            "error": str(e),
            "url": getattr(driver, "current_url", "unknown"),
        })
        return False
    
def wait_for_page_load(driver: webdriver, timeout=10):
    """
    Wait for the page to load by checking for the presence of job cards.

    Returns:
        bool: True if job cards are found within the timeout, False otherwise.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.job-card"))
        )
        return True
    except Exception:
        return False