"""
Alternative web scraping methods for e-commerce sites like Allegro.
This module provides additional scraping techniques if the primary method fails.
"""
import requests
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_user_agent():
    """Return a random user agent string to avoid detection."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    return random.choice(user_agents)


def scrape_with_selenium(url):
    """
    Scrape a website using Selenium webdriver.
    This method can bypass some anti-bot mechanisms but requires Chrome and chromedriver.
    
    Note: This requires Selenium and Chrome/chromedriver to be installed.
    pip install selenium
    
    Returns:
        dict: Product details if successful, error message otherwise
    """
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument(f"user-agent={get_user_agent()}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Initialize the driver
        # Note: You'll need to specify the path to chromedriver if it's not in your PATH
        driver = webdriver.Chrome(options=chrome_options)
        
        # Add a random delay to seem more human-like
        time.sleep(random.uniform(1, 3))
        
        # Navigate to the URL
        driver.get(url)
        
        # Wait for the page to load (wait for title to be present)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        
        # Extract the product information
        title = driver.find_element(By.TAG_NAME, "h1").text
        
        # Try different methods to get price
        price = None
        price_selectors = [
            'div[data-box-name="Price box"] div > div > span',
            'meta[itemprop="price"]',
            'div[data-analytics-view-custom-price]'
        ]
        
        for selector in price_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    if selector == 'meta[itemprop="price"]':
                        price = elements[0].get_attribute('content')
                    else:
                        price = elements[0].text
                    break
            except Exception:
                continue
        
        # Try to get description
        description = None
        description_selectors = [
            'div[data-box-name="Description"]',
            'div[itemprop="description"]'
        ]
        
        for selector in description_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    description = elements[0].text
                    break
            except Exception:
                continue
        
        # Get HTML for BeautifulSoup parsing (for more complex extractions)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract manufacturer and model (simplified approach)
        manufacturer = None
        model = None
        
        params = soup.select('div[data-box-name="Parameters"] li')
        for param in params:
            param_text = param.get_text().lower()
            if 'marka' in param_text or 'producent' in param_text:
                parts = param_text.split(':')
                if len(parts) > 1:
                    manufacturer = parts[1].strip()
            if 'model' in param_text:
                parts = param_text.split(':')
                if len(parts) > 1:
                    model = parts[1].strip()
        
        # Clean up
        driver.quit()
        
        # Check if we got at least the title
        if not title:
            return {'error': 'Could not extract product title'}
        
        # Format and return the data
        result = {
            'title': title,
            'price': price,
            'description': description,
            'manufacturer': manufacturer,
            'model': model,
            'source_url': url,
            'method': 'selenium'
        }
        
        return result
    
    except Exception as e:
        try:
            if 'driver' in locals():
                driver.quit()
        except Exception:
            pass
        
        return {'error': f'Selenium scraping error: {str(e)}'}


# This is only an example function and would require setting up a proxy service
def scrape_with_proxy(url, proxy_url=None):
    """
    Scrape a website using a proxy to avoid IP-based blocking.
    
    Args:
        url: The URL to scrape
        proxy_url: Proxy server URL (e.g., "http://username:password@proxy-server:port")
        
    Returns:
        dict: Product details or error message
    """
    if not proxy_url:
        return {'error': 'No proxy URL provided'}
    
    try:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        headers = {
            'User-Agent': get_user_agent(),
            'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        
        if response.status_code != 200:
            return {'error': f'HTTP Error: {response.status_code}'}
        
        # Process the response similar to the main scraper...
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract basic product info (simplified)
        title = soup.find('h1')
        title = title.text.strip() if title else None
        
        if not title:
            return {'error': 'Could not extract product title'}
        
        return {
            'title': title,
            'source_url': url,
            'method': 'proxy'
            # Add other extracted fields as needed
        }
    
    except Exception as e:
        return {'error': f'Proxy scraping error: {str(e)}'}
