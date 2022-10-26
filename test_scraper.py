""" PyTest for price_checker.py. """
import price_checker as pc
import pytest

def test_get_microcenter_price():
    """ Test for get_microcenter_price. """
    scraper = pc.PriceScraper()
    price = scraper.get_microcenter_price(
        'https://www.microcenter.com/product/639544/msi-nvidia-geforce-rtx-3080-gaming-z-trio-lhr-triple-fan-10gb-gddr6x-pcie-40-graphics-card'
    )
    scraper.close()
    assert price == 779.99

def test_get_amazon_price():
    """ Test for get_amazon_price. """
    scraper = pc.PriceScraper()
    price = scraper.get_amazon_price(
        'https://www.amazon.com/HYTE-Revolt-Factor-Premium-Computer/dp/B09HZ2NCNT/?content-id=amzn1.sym.8cf3b8ef-6a74-45dc-9f0d-6409eb523603'
    )
    scraper.close()
    assert price == 129.99

if __name__ == '__main__':
    pytest.main()
