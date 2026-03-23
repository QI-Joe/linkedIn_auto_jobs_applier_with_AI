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