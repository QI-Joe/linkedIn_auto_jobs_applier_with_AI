"""读取 LinkedIn 的登录态搜索结果页。"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from src.utils.utils import scroll_slow


class ListingStructureError(Exception):
    """预期的职位列表结构缺失，调用方可据此区分空列表与解析失败。"""


def read_job_tiles(driver: WebDriver) -> list[WebElement]:
    """滚动已有结果区并读取卡片；不打开详情或申请弹窗。"""
    results = driver.find_elements(By.CLASS_NAME, "jobs-search-results-list")
    if not results:
        raise ListingStructureError("未找到 LinkedIn 搜索结果区 jobs-search-results-list")

    scroll_slow(driver, results[0])
    scroll_slow(driver, results[0], step=300, reverse=True)

    containers = driver.find_elements(By.CLASS_NAME, "scaffold-layout__list-container")
    if not containers:
        raise ListingStructureError("未找到 LinkedIn 卡片容器 scaffold-layout__list-container")
    return containers[0].find_elements(By.CLASS_NAME, "jobs-search-results__list-item")
