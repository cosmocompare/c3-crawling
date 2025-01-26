from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from django.utils import timezone
from django.db import connection
import time
import logging

logging.basicConfig(
    filename='oy_crawling.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class Command(BaseCommand):
    help = '올리브영 상품 크롤링'

    def handle(self, *args, **options):
        try:
            self.crawl_oliveyoung()
            self.stdout.write(self.style.SUCCESS('크롤링 완료'))
            logging.info('크롤링 작업 성공')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'크롤링 실패: {str(e)}'))
            logging.error(f'크롤링 작업 실패: {str(e)}')

    def crawl_oliveyoung(self):
        categories = {
            "스킨케어": ["100000100010013", "100000100010014", "100000100010015", 
                      "100000100010016", "100000100010010", "100000100010017"],
            "마스크팩": ["100000100090001", "100000100090004", "100000100090002", 
                      "100000100090005", "100000100090006"],
            "클렌징": ["100000100100001", "100000100100004", "100000100100005", 
                    "100000100100007", "100000100100008", "100000100100006"],
            "선케어": ["100000100110006", "100000100110003", "100000100110004", 
                    "100000100110005", "100000100110002"],
            "립메이크업": ["100000100020006"],
            "베이스메이크업": ["100000100020001"],
            "아이메이크업": ["100000100020007"]
        }

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        try:
            today = timezone.now().date()
            for category_name, subcategories in categories.items():
                for category_code in subcategories:
                    self.crawl_category(driver, category_name, category_code, today)
        finally:
            driver.quit()

    def crawl_category(self, driver, category_name, category_code, today):
        page_number = 1
        while True:
            try:
                search_url = f"https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo={category_code}&isLoginCnt=0&aShowCnt=0&bShowCnt=0&cShowCnt=0&pageIdx={page_number}&rowsPerPage=24&searchTypeSort=btn_thumb&plusButtonFlag=N"
                driver.get(search_url)
                time.sleep(2)

                products = driver.find_elements(By.CLASS_NAME, 'prd_info')
                if not products:
                    break

                for product in products:
                    try:
                        product_data = self.extract_product_data(product, category_name)
                        if product_data:
                            self.save_or_update_product(product_data, today)
                    except Exception as e:
                        logging.error(f'상품 처리 중 오류: {str(e)}')
                        continue

                if not self.has_next_page(driver):
                    break
                page_number += 1

            except Exception as e:
                logging.error(f'페이지 처리 중 오류: {str(e)}')
                break

    def extract_product_data(self, product, category_name):
        try:
            brand = product.find_element(By.CLASS_NAME, 'tx_brand').text
            cosmetic_name = product.find_element(By.CLASS_NAME, 'tx_name').text
            
            sale_price_raw = product.find_element(By.CLASS_NAME, 'tx_cur').text
            sale_price = ''.join(filter(str.isdigit, sale_price_raw))
            
            try:
                price_raw = product.find_element(By.CLASS_NAME, 'tx_org').text
                price = ''.join(filter(str.isdigit, price_raw))
            except NoSuchElementException:
                price = sale_price
                
            cosmetic_url = product.find_element(By.CLASS_NAME, 'prd_thumb').get_attribute('href')
            image_url = product.find_element(By.CLASS_NAME, 'prd_thumb').find_element(By.TAG_NAME, 'img').get_attribute('src')

            return {
                'category': category_name,
                'brand': brand,
                'cosmetic_name': cosmetic_name,
                'price': price,
                'sale_price': sale_price,
                'cosmetic_url': cosmetic_url,
                'image_url': image_url
            }
        except Exception as e:
            logging.error(f'데이터 추출 중 오류: {str(e)}')
            return None

    def save_or_update_product(self, product_data, today):
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT cosmetic_url, price, sale_price 
                    FROM oycosmetic 
                    WHERE cosmetic_url = %s
                """, [product_data['cosmetic_url']])
                
                existing_product = cursor.fetchone()
                
                if existing_product:
                    if (existing_product[1] != product_data['price'] or 
                        existing_product[2] != product_data['sale_price']):
                        cursor.execute("""
                            UPDATE oycosmetic 
                            SET price = %s, sale_price = %s, updated_at = %s
                            WHERE cosmetic_url = %s
                        """, [
                            product_data['price'],
                            product_data['sale_price'],
                            today,
                            product_data['cosmetic_url']
                        ])
                        logging.info(f"상품 업데이트: {product_data['cosmetic_name']}")
                else:
                    cursor.execute("""
                        INSERT INTO oycosmetic (
                            category, brand, cosmetic_name, price, 
                            sale_price, cosmetic_url, image_url, 
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        product_data['category'],
                        product_data['brand'],
                        product_data['cosmetic_name'],
                        product_data['price'],
                        product_data['sale_price'],
                        product_data['cosmetic_url'],
                        product_data['image_url'],
                        today,
                        today
                    ])
                    logging.info(f"새 상품 추가: {product_data['cosmetic_name']}")

                connection.commit()

            except Exception as e:
                connection.rollback()
                logging.error(f'데이터베이스 저장 중 오류: {str(e)}')
                raise e

    def has_next_page(self, driver):
        next_button = driver.find_elements(By.CLASS_NAME, 'next')
        return next_button and 'disabled' not in next_button[0].get_attribute('class')

