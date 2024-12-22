# management/commands/crawl_ranking.py
from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from django.db import connection
import time
import logging

# 로깅 설정
logging.basicConfig(
    filename='crawling.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Command(BaseCommand):
    help = '올리브영 랭킹 페이지 크롤링'

    def handle(self, *args, **options):
        try:
            self.crawl_oliveyoung_ranking()
            self.stdout.write(self.style.SUCCESS('크롤링 완료'))
            logging.info('크롤링 작업 성공')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'크롤링 실패: {str(e)}'))
            logging.error(f'크롤링 작업 실패: {str(e)}')

    def crawl_oliveyoung_ranking(self):
        """올리브영 랭킹 페이지 크롤링 메서드"""
        # 크롬 드라이버 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        try:
            # 올리브영 랭킹 페이지 URL
            ranking_url = "https://www.oliveyoung.co.kr/store/main/getBestList.do?t_page=%EB%A9%94%EC%9D%B4%ED%81%AC%EC%97%85%20%3E%20%EC%95%84%EC%9D%B4%EB%A9%94%EC%9D%B4%ED%81%AC%EC%97%85&t_click=GNB&t_gnb_type=%EB%9E%AD%ED%82%B9&t_swiping_type=N"
            driver.get(ranking_url)
            time.sleep(3)

            products_data = []
            product_count = 0

            while product_count < 100:
                # 페이지 스크롤
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                time.sleep(2)
                
                products = driver.find_elements(By.CLASS_NAME, 'prd_info')
                
                for product in products:
                    if product_count >= 100:
                        break
                    try:
                        product_data = self.extract_product_data(product)
                        if product_data:
                            products_data.append(product_data)
                            product_count += 1
                            logging.info(f'제품 데이터 추출 성공: {product_data["cosmetic_name"]}')
                    except Exception as e:
                        logging.error(f'제품 데이터 추출 실패: {str(e)}')
                        continue

            self.save_to_database(products_data)
            logging.info(f'총 {len(products_data)}개의 제품 데이터 저장 완료')

        except Exception as e:
            logging.error(f'크롤링 중 오류 발생: {str(e)}')
            raise e
        finally:
            driver.quit()

    def extract_product_data(self, product):
        """개별 제품 정보 추출"""
        try:
            brand = product.find_element(By.CLASS_NAME, 'tx_brand').text
            cosmetic_name = product.find_element(By.CLASS_NAME, 'tx_name').text
            
            oy_price = product.find_element(By.CLASS_NAME, 'tx_cur').text

            try:
                price = product.find_element(By.CLASS_NAME, 'tx_org').text
            except NoSuchElementException:
                price = oy_price
                logging.info(f'정상가격 없음, 할인가격으로 대체: {cosmetic_name}')
            
            cosmetic_url = product.find_element(By.CLASS_NAME, 'prd_thumb').get_attribute('href')
            image_element = product.find_element(By.CLASS_NAME, 'prd_thumb').find_element(By.TAG_NAME, 'img')
            image_url = image_element.get_attribute('src')

            return {
                'brand': brand,
                'cosmetic_name': cosmetic_name,
                'price': price,
                'oy_price': oy_price,
                'cosmetic_url': cosmetic_url,
                'image_url': image_url
            }
        except Exception as e:
            logging.error(f'데이터 추출 중 오류: {str(e)}')
            return None

    def save_to_database(self, products_data):
        """데이터베이스 저장"""
        with connection.cursor() as cursor:
            try:
                # 기존 데이터 삭제
                cursor.execute("TRUNCATE TABLE ranking")
                logging.info('기존 랭킹 데이터 삭제 완료')
                
                # 새로운 데이터 저장
                for product in products_data:
                    if product:
                        cursor.execute("""
                            INSERT INTO ranking (brand, cosmetic_name, price, oy_price, cosmetic_url, image_url)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, [
                            str(product['brand']),
                            str(product['cosmetic_name']),
                            str(product['price']) if product['price'] is not None else None,
                            str(product['oy_price']),
                            str(product['cosmetic_url']),
                            str(product['image_url'])
                        ])
                connection.commit()
                logging.info('새로운 데이터 저장 완료')
            except Exception as e:
                connection.rollback()
                logging.error(f'데이터베이스 저장 중 오류: {str(e)}')
                raise e
