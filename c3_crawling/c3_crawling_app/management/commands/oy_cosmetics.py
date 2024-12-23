from django.core.management.base import BaseCommand # Django 커스텀 명령어 생성을 위한 기본 클래스
from selenium import webdriver # 웹 브라우저 자동화
from selenium.webdriver.chrome.options import Options # 크롬 브라우저 설정
from selenium.webdriver.common.by import By # 웹 요소 선택자
from selenium.common.exceptions import NoSuchElementException # 요소를 찾지 못했을 때의 예외처리
from django.utils import timezone # 시간 처리
from django.db import connection # 데이터베이스 연결
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
    help = '올리브영 상품 크롤링'

    def handle(self, *args, **options):
        """Django 커스텀 명령어 실행 메서드"""
        try:
            self.crawl_oliveyoung() # 크롤링 실행
            self.stdout.write(self.style.SUCCESS('크롤링 완료'))
            logging.info('크롤링 작업 성공')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'크롤링 실패: {str(e)}'))
            logging.error(f'크롤링 작업 실패: {str(e)}')

    def crawl_oliveyoung(self):
        """올리브영 카테고리별 상품 크롤링"""
        # 크롤링할 카테고리와 해당 코드 정의
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

        # 크롬 드라이버 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        try:
            today = timezone.now().date() # 현재 날짜 저장
            # 각 카테고리별로 크롤링 수행
            for category_name, subcategories in categories.items():
                for category_code in subcategories:
                    self.crawl_category(driver, category_name, category_code, today)
        except Exception as e:
            logging.error(f'크롤링 중 오류 발생: {str(e)}')
            raise e
        finally:
            driver.quit()

    def crawl_category(self, driver, category_name, category_code, today):
        """카테고리별 크롤링 수행"""
        page_number = 1
        while True:
            try:
                # 올리브영 카테고리별 상품 목록 URL
                search_url = f"https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo={category_code}&isLoginCnt=0&aShowCnt=0&bShowCnt=0&cShowCnt=0&pageIdx={page_number}&rowsPerPage=24&searchTypeSort=btn_thumb&plusButtonFlag=N"
                driver.get(search_url)
                time.sleep(2)

                logging.info(f"크롤링 중: {category_name} - 카테고리 {category_code} - 페이지 {page_number}")

                # 상품 목록 요소 찾기
                products = driver.find_elements(By.CLASS_NAME, 'prd_info')
                if not products:# 상품이 없으면 해당 카테고리 크롤링 종료
                    break

                # 각 상품 정보 추출 및 저장
                for product in products: 
                    try: # 상품 정보 추출
                        product_data = self.extract_product_data(product, category_name)
                        if product_data:
                            self.save_or_update_product(product_data, today)
                    except Exception as e:
                        logging.error(f'상품 처리 중 오류: {str(e)}')
                        continue

                # 다음 페이지 존재 여부 확인
                if not self.has_next_page(driver):
                    break
                page_number += 1

            except Exception as e:
                logging.error(f'페이지 처리 중 오류: {str(e)}')
                break

    def extract_product_data(self, product, category_name):
        """개별 상품 정보 추출"""
        try:
            # 상품 정보 추출
            brand = product.find_element(By.CLASS_NAME, 'tx_brand').text
            cosmetic_name = product.find_element(By.CLASS_NAME, 'tx_name').text
            sale_price = product.find_element(By.CLASS_NAME, 'tx_cur').text.replace('원', '').replace('~', '').replace(',', '')
            # 정가 정보 추출 (없으면 할인가로 대체)
            try:
                price = product.find_element(By.CLASS_NAME, 'tx_org').text.replace('원', '').replace('~', '').replace(',', '')
            except NoSuchElementException:
                price = sale_price
            cosmetic_url = product.find_element(By.CLASS_NAME, 'prd_thumb').get_attribute('href')
            image_url = product.find_element(By.CLASS_NAME, 'prd_thumb').find_element(By.TAG_NAME, 'img').get_attribute('src')

            # 추출한 정보를 딕셔너리로 반환
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
        """상품 정보 저장 또는 업데이트"""
        with connection.cursor() as cursor:
            try:
                # 기존 상품 검색
                cursor.execute("""
                    SELECT cosmetic_url, price, sale_price 
                    FROM oycosmetic 
                    WHERE cosmetic_url = %s
                """, [product_data['cosmetic_url']])
                
                existing_product = cursor.fetchone()
                
                if existing_product: # 가격 변동이 있는 경우 업데이트
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
                else: # 새로운 상품 추가
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
        """다음 페이지 존재 여부 확인"""
        next_button = driver.find_elements(By.CLASS_NAME, 'next')
        return next_button and 'disabled' not in next_button[0].get_attribute('class')
