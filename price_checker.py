# Python 3.11.0
""" Price checker for PC parts. """
import warnings
import sqlite3 as sql
import sys
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as sel_exceptions
import numpy as np
import pandas as pd

class PriceScraper(webdriver.Chrome):
    """ Selenium webdriver for price scraping. """
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        super().__init__(service=Service(ChromeDriverManager().install()), options=options)
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        self.sql_conn = sql.connect('pc_parts.db')
        with self.sql_conn:
            self.sql_conn.execute('CREATE TABLE IF NOT EXISTS prices (url TEXT, price REAL, time TEXT)')
        self.sql_conn.commit()

    def get_microcenter_price(self, url) -> float:
        """ Price scraping implementation for microcenter.com. """
        self.get(url)
        try:
            WebDriverWait(self, 10).until(
                EC.presence_of_element_located((By.XPATH, './/span[@id="pricing"]'))
            )
        except sel_exceptions.TimeoutException as the_exception:
            print(the_exception)
        price = self.find_elements(By.ID, 'pricing')
        if len(price) == 0:
            return np.inf
        price = price[0].get_attribute('content')
        # record price and time accessed in database
        return float(price)

    def get_amazon_price(self, url) -> float:
        """ Price scraping implementation for amazon.com. """
        if url is None:
            return np.inf
        self.get(url)
        try:
            WebDriverWait(self, 10).until(
                EC.presence_of_element_located((By.XPATH, './/span[@class="a-price-fraction"]'))
            )
        except sel_exceptions.TimeoutException as the_exception:
            print(the_exception)
        price_whole = self.find_elements(By.CLASS_NAME, 'a-price-whole')
        price_frac = self.find_elements(By.CLASS_NAME, 'a-price-fraction')
        if len(price_whole) == 0 or len(price_frac) == 0:
            return np.inf
        price_whole = price_whole[0].text
        price_frac = price_frac[0].text
        return float(price_whole + '.' + price_frac)

    def get_pricing(self, name, url:str) -> np.single:
        """ Returns the price of the product on the website.
        If the website is not supported, returns np.inf. """

        # check if we need to even fetch anything
        if url is None:
            return np.inf
        domain = url.split('/')[2]
        domain = domain.split('.')[1]
        sql_entry_outdated = False
        with self.sql_conn as conn:
            # get price and time from database
            cursor = conn.execute('SELECT price FROM prices WHERE url=?', (url,))
            price = cursor.fetchone()
            cursor = conn.execute('SELECT time FROM prices WHERE url=?', (url,))
            time_last = cursor.fetchone()
            time_now = conn.execute('SELECT CURRENT_TIMESTAMP').fetchone()[0]
            # if over 24 hours since last price check, update price
            if price is not None:
                # convert to datetime objects
                time_last = pd.to_datetime(time_last)
                time_now = pd.to_datetime(time_now)
                if (time_now - time_last).total_seconds() <= 86400 and price is not None:
                    print(f'Price for {name} from {domain} is still recent, skipping')
                    return price[0]
                sql_entry_outdated = True

        # if no price in database, or if price is outdated, fetch new price
        match domain:
            case 'microcenter':
                price = self.get_microcenter_price(url)
            case 'amazon':
                price = self.get_amazon_price(url)
            case _:
                warnings.warn(f'Could not get price for {name} from {domain}')
                price = sys.float_info.max

        # record price and time accessed in database
        with self.sql_conn:
            # get the current time
            time = self.sql_conn.execute('SELECT CURRENT_TIMESTAMP').fetchone()[0]
            if sql_entry_outdated:
                self.sql_conn.execute('UPDATE prices SET price=?, time=? WHERE url=?', (price, time, url))
                print(f'Updated price for {name} from {domain} (${price.round(2)})')
            else:
                self.sql_conn.execute('INSERT INTO prices VALUES (?,?,?)', (url, price, time))
                print(f'Added price for {name} from {domain} (${price.round(2)})')
            self.sql_conn.commit()
        return price

class Product:
    """ Holds the name of the product and the links to the product on different websites. """
    def __init__(self, name: str, urls: dict):
        self.name = name
        self.links: dict = urls

    def best_price(self, driver: PriceScraper) -> float:
        """ Scraps the websites for price info and returns the lowest price. """
        min_price = np.inf
        for link in self.links.values():
            price = driver.get_pricing(self.name, link)
            if price < min_price:
                min_price = price
        print(f'Best price for {self.name} is {min_price}')
        return min_price

class PCBuild:
    """ Collection of PC parts. """
    def __init__(self, name, parts):
        self.name = name
        self.parts = parts
        self.prices = {}

    def report_build(self, driver: PriceScraper, report_file: str):
        """ Prints the build info and the total price. """
        print(f'Price breakdown for {self.name}:')
        # Create a dataframe to store the build
        toal_price = 0
        for part in self.parts:
            price = part.best_price(driver)
            self.prices[part.name] = price
            toal_price += price if price < np.inf else 0
        print(self.prices)
        df_build = pd.DataFrame.from_dict(self.prices, orient='index', columns=['Price'])
        # Add total price
        df_build.loc['Total'] = toal_price
        df_build.to_csv(report_file)


def main():
    """Get the website using the webdriver"""

    scraper = PriceScraper()

    intel_build = PCBuild('Intel Build',
        [
            Product(
                name='Intel Core i7-13700K',
                urls={
                    'microcenter': 'https://www.microcenter.com/product/652626/intel-core-i7-13700k-raptor-lake-34ghz-sixteen-core-lga-1700-boxed-processor-heatsink-not-included',
                    'amazon': 'https://www.amazon.com/Intel-i7-13700K-Desktop-Processor-P-cores/dp/B0BCF57FL5'
                }
            ),
            Product(
                name='EVGA Nvidia GTX 3080Ti FTW3 Ultra',
                urls={

                }
            ),
            Product(
                name='Asus ROG STRIX B550-I GAMING',
                urls={
                    'microcenter': 'https://www.microcenter.com/product/648356/gigabyte-b660i-aorus-pro-ddr4-intel-lga-1700-mini-itx-motherboard?ob=1',
                    'amazon': 'https://www.amazon.com/B660I-AORUS-PRO-DDR4-Motherboard/dp/B083NLX6G3'
                }
            )
        ]
    )

    intel_build.report_build(scraper, 'intel_build.csv')

    # Close the scraper
    scraper.close()


if __name__ == '__main__':
    main()
