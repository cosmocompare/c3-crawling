from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.utils import timezone
from django.db import connection
import time
import logging

logging.basicConfig(
    filename='musinsa_crawling.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class Command(BaseCommand):
    help = '무신사 상품 크롤링'

    def handle(self, *args, **options):
        try:
            self.crawl_musinsa()
            self.stdout.write(self.style.SUCCESS('크롤링 완료'))
            logging.info('크롤링 작업 성공')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'크롤링 실패: {str(e)}'))
            logging.error(f'크롤링 작업 실패: {str(e)}')

    def crawl_musinsa(self):
        categories = {
            "스킨케어": ["104001001", "104001002", "104001003", "104001004", 
                    "104001005", "104001006", "104001007", "104001008", 
                    "104001009", "104001010", "104001012"],
            "마스크팩": ["104001011"],
            "클렌징": ["104003"],
            "선케어": ["104002"],
            "베이스메이크업": ["104004001"],
            "립메이크업": ["104004002"],
            "아이메이크업": ["104004003"]
        }

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        try:
            today = timezone.now().date()
            for category_name, category_codes in categories.items():
                if isinstance(category_codes, list):
                    for code in category_codes:
                        self.crawl_category(driver, category_name, code, today)
                else:
                    self.crawl_category(driver, category_name, category_codes, today)
        finally:
            driver.quit()

    def crawl_category(self, driver, category_name, category_code, today):
        url = f"https://www.musinsa.com/category/{category_code}?gf=A"
        driver.get(url)
        time.sleep(2)

        # 초기 상품 수집
        try:
            initial_products = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.sc-fUnNpA.iCowMw"))
            )
        
            for product in initial_products:
                try:
                    product_data = self.extract_product_data(driver, product, category_name)
                    if product_data:
                        self.save_or_update_product(product_data, today)
                except Exception as e:
                    logging.error(f'상품 처리 중 오류: {str(e)}')
                    continue
        except Exception as e:
            logging.error(f'초기 상품 목록 로딩 중 오류: {str(e)}')

        # 스크롤하면서 추가 상품 수집
        scroll_pause_time = 2
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

            try:
                products = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.sc-fUnNpA.iCowMw"))
                )

                for product in products:
                    try:
                        product_data = self.extract_product_data(driver, product, category_name)
                        if product_data:
                            self.save_or_update_product(product_data, today)
                    except Exception as e:
                        logging.error(f'상품 처리 중 오류: {str(e)}')
                        continue
            except Exception as e:
                logging.error(f'상품 목록 로딩 중 오류: {str(e)}')
                continue


    def extract_product_data(self, driver, product, category_name):
        try:
            brand = product.find_element(By.CSS_SELECTOR, "span.text-etc_11px_semibold.sc-dcJtft.sc-iGgVNO.jEEFmT.laXDWb.font-pretendard").text
            name = product.find_element(By.CSS_SELECTOR, "span.text-body_13px_reg.sc-dcJtft.sc-gsFSjX.jEEFmT.eEPdZZ.font-pretendard").text
            price_spans = product.find_elements(By.CSS_SELECTOR, "span.text-body_13px_semi.sc-fqkwJk.ioeSYE.font-pretendard")
            sale_price_raw = price_spans[1].text if len(price_spans) > 1 else price_spans[0].text
            sale_price = ''.join(filter(str.isdigit, sale_price_raw))
            
            product_url = product.find_element(By.CSS_SELECTOR, "a.gtm-select-item").get_attribute('href')
            image_url = product.find_element(By.CSS_SELECTOR, "img.max-w-full").get_attribute('src')

            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(product_url)
            time.sleep(1)

            try:
                price_selectors = [
                "span.text-xs.font-medium.mb-0\\.5.text-gray-500.font-pretendard[style='text-decoration-line: line-through;']",
                "div.sc-xz8kdb-2.gyAydn span.text-xs.font-medium.mb-0\\.5.text-gray-500.font-pretendard[style='text-decoration-line: line-through;']",
                "span.text-xs.font-medium.text-gray-500[style='text-decoration-line: line-through;']"
                ]
    
                price = None
                for selector in price_selectors:
                    try:
                        price_raw = driver.find_element(By.CSS_SELECTOR, selector).text
                        price = ''.join(filter(str.isdigit, price_raw))
                        if price:  # 가격을 찾았다면 반복 중단
                            break
                    except:
                        continue
            
                if not price:  # 모든 선택자로 시도했는데도 가격을 못 찾은 경우
                    price = sale_price
        
            except Exception as e:
                price = sale_price

            except Exception as e:
                logging.error(f'정가 추출 중 오류: {str(e)}')

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            return {
                'category': category_name,
                'brand': brand,
                'cosmetic_name': name,
                'price': price,
                'sale_price': sale_price,
                'cosmetic_url': product_url,
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
                    FROM msscosmetic 
                    WHERE cosmetic_url = %s
                """, [product_data['cosmetic_url']])
                
                existing_product = cursor.fetchone()
                
                if existing_product:
                    if (existing_product[1] != product_data['price'] or 
                        existing_product[2] != product_data['sale_price']):
                        cursor.execute("""
                            UPDATE msscosmetic 
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
                        INSERT INTO msscosmetic (
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
