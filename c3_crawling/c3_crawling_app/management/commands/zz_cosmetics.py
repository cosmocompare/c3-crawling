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

# 로깅 설정: 파일명, 로그 레벨, 출력 형식 지정
logging.basicConfig(
    filename='crawling.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class Command(BaseCommand):
    help = '지그재그 상품 크롤링'

    def handle(self, *args, **options):
        try:
            self.crawl_zigzag()
            self.stdout.write(self.style.SUCCESS('크롤링 완료'))
            logging.info('크롤링 작업 성공')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'크롤링 실패: {str(e)}'))
            logging.error(f'크롤링 작업 실패: {str(e)}')

    def crawl_zigzag(self):
        """지그재그 카테고리별 상품 크롤링"""

        # 크롤링할 카테고리
        categories = {
            "스킨케어": "1100",
            "마스크팩": "1106",
            "클렌징": "1105", 
            "선케어": "1101",
            "립메이크업": "1104",
            "베이스메이크업": "1102",
            "아이메이크업": "1103"
        }

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        try:
            today = timezone.now().date()
            for category_name, category_code in categories.items():
                self.crawl_category(driver, category_name, category_code, today)
        except Exception as e:
            logging.error(f'크롤링 중 오류 발생: {str(e)}')
            raise e
        finally:
            driver.quit()

    def crawl_category(self, driver, category_name, category_code, today):
        """카테고리별 크롤링"""
        url = f'https://zigzag.kr/categories/1098?middle_category_id={category_code}&title={category_name}'
        driver.get(url)
        time.sleep(2)

        # 무한 스크롤 처리를 위한 변수 설정
        scroll_pause_time = 2
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            try: # 페이지 끝까지 스크롤
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)

                # 새로운 높이 계산
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height: # 더 이상 스크롤할 내용이 없으면 종료
                    break

                last_height = new_height

                # 상품 목록 요소 찾기 (명시적 대기 사용)
                products = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, 'css-5hci9z'))
                )

                # 각 상품 정보 추출 및 저장
                for product in products:
                    try:
                        product_data = self.extract_product_data(driver, product, category_name)
                        if product_data:
                            self.save_or_update_product(product_data, today)
                    except Exception as e:
                        logging.error(f'상품 처리 중 오류: {str(e)}')
                        continue

            except Exception as e:
                logging.error(f'페이지 처리 중 오류: {str(e)}')
                break

    def extract_product_data(self, driver, product, category_name):
        """개별 상품 정보 추출"""
        try:
            brand = product.find_element(By.XPATH, './/span[@class="zds4_1kdomr8"]').text
            name = product.find_element(By.XPATH, './/p[@class="zds4_1kdomrc zds4_1kdomra"]').text
            sale_price = product.find_element(By.XPATH, './/span[@class="zds4_s96ru86 zds4_s96ru8w zds4_1jsf80i3 zds4_1jsf80i5"]').text
            product_url = product.find_element(By.XPATH, './/a[@class="css-152zj1o product-card-link"]').get_attribute('href')
            image_url = product.find_element(By.XPATH, './/img[@class="zds4_11053yc2"]').get_attribute('src')

            # 상품 상세 페이지 접근하여 정가 추출
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(product_url)
            time.sleep(1)

            try:
                price = driver.find_element(By.CLASS_NAME, 'css-14j45be').text
            except:
                price = sale_price

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
        """상품 정보 데이터베이스 저장/업데이트"""
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT cosmetic_url, price, sale_price 
                    FROM zzcosmetic 
                    WHERE cosmetic_url = %s
                """, [product_data['cosmetic_url']])
                
                existing_product = cursor.fetchone()
                
                if existing_product:
                    if (existing_product[1] != product_data['price'] or 
                        existing_product[2] != product_data['sale_price']):
                        cursor.execute("""
                            UPDATE zzcosmetic 
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
                        INSERT INTO zzcosmetic (
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