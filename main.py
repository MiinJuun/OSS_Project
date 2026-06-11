from fastapi import FastAPI
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import Select
from database import init_db, get_db, Place, Review, SessionLocal
from database import init_db, get_db, Place, Review, SentimentResult, SessionLocal
from anomaly import calc_abusing_score, save_reviewer_profile
from keywords import extract_cross_keywords, calc_platform_bayesian, save_dashboard_report
from fastapi.middleware.cors import CORSMiddleware
import time
import uvicorn
import random
import re
import tempfile
import shutil
import os
import requests
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 곳에서 오는 요청을 허락함 (테스트용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
init_db()

NAVER_TARGET = 30
# 카카오는 20개까지 수집을 시도하되, 10개만 넘어도 충분한 것으로 판정하도록 변경
KAKAO_TARGET = 20   


# ---------------------------------------------------------
# ▼ [핵심 수정 1] --incognito 제거 → 매 요청마다 새 user-data-dir 생성
# ---------------------------------------------------------
def get_chrome_driver(profile_suffix="default"):
    profile_dir = os.path.join(tempfile.gettempdir(), f"uc_profile_{profile_suffix}")

    # 기존 프로필 삭제 후 재생성 → 이전 검색 기록 완전 초기화
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir, ignore_errors=True)
    os.makedirs(profile_dir, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument('--headless=new') # 브라우저 창 숨기기
    options.add_argument(f'--user-data-dir={profile_dir}')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-restore-session-state')  # 세션 복원 차단
    options.add_argument('--disable-session-crashed-bubble')

    driver = uc.Chrome(options=options, use_subprocess=True, version_main=148)
    driver.set_window_size(1920, 1080)
    return driver


# ---------------------------------------------------------
# 공통 노이즈 필터
# ---------------------------------------------------------
def is_real_review(text: str) -> bool:
    if not text or len(text) < 10:
        return False
    noise_patterns = [
        r"리뷰\s*[\d,]+",
        r"사진\s*[\d,]+",
        r"팔로워\s*[\d,]+",
        r"테마\s*[\d,]+",
        r"^\+\d+\s*개의 리뷰",
        r"^팔로우$",
        r"^반응 남기기$",
        r"^\d+\s*명$",
        r"^[0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}",
        r"(아침|점심|저녁|새벽)에 방문",
        r"대기\s*시간",
        r"예약\s*(없이|있이|후)",
    ]
    for pattern in noise_patterns:
        if re.search(pattern, text):
            return False
    if re.match(r'^[\d\s,\.\+\-\#\@]+$', text):
        return False
    return True


# ---------------------------------------------------------
# 네이버 리뷰 수집 헬퍼 함수들
# ---------------------------------------------------------
def collect_naver_reviews_from_dom(driver) -> list:
    elements = driver.find_elements(
        By.CSS_SELECTOR,
        "li .pui__GStJHb, li .zPfVt, li .xTzHn, li .ZZ4OK, li .YglqY, li .xtxKM, "
        "li[class*='pui__'] span[class*='text'], li[class*='review'] span[class*='text']"
    )
    seen = set()
    results = []
    for el in elements:
        try:
            text = el.text.strip().replace('\n', ' ').replace('\r', ' ')
            text = text.replace("더보기", "").replace("접기", "").replace("펼쳐보기", "").strip()
            if is_real_review(text) and text not in seen:
                results.append(text)
                seen.add(text)
        except:
            pass
    return results


def expand_review_texts(driver):
    btns = driver.find_elements(
        By.XPATH,
        "//ul[contains(@class,'list') or contains(@class,'review') or contains(@class,'Review')]"
        "//li//*[text()='더보기' or text()='펼쳐보기']"
    )
    for btn in btns:
        try:
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.2)
        except:
            pass


def click_list_more_btn(driver) -> bool:
    xpaths = [
        "//*[normalize-space(text())='펼쳐서 더보기']",
        "//*[normalize-space(text())='더 보기']",
        "//div[contains(@class,'review') or contains(@class,'Review')]//a[not(ancestor::li)][contains(text(),'더보기') or contains(text(),'더 보기')]",
        "//div[contains(@class,'review') or contains(@class,'Review')]//button[not(ancestor::li)][contains(text(),'더보기') or contains(text(),'더 보기')]",
        "//a[contains(@class,'btn_more') or contains(@class,'more_btn')]",
        "//button[contains(@class,'btn_more') or contains(@class,'more_btn')]",
    ]

    for xpath in xpaths:
        try:
            candidates = driver.find_elements(By.XPATH, xpath)
            for btn in candidates:
                try:
                    btn.find_element(By.XPATH, "ancestor::li[contains(@class,'pui') or contains(@class,'review')]")
                    continue
                except NoSuchElementException:
                    pass
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.4)
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"   → 리스트 '더보기' 클릭 성공!")
                    time.sleep(2.5)
                    return True
                except:
                    continue
        except:
            continue
    return False


def scroll_in_iframe(driver):
    try:
        items = driver.find_elements(
            By.CSS_SELECTOR,
            "li[class*='pui'], ul[class*='list'] > li, ul[class*='review'] > li"
        )
        if items:
            driver.execute_script("arguments[0].scrollIntoView({block:'end'});", items[-1])
            return
    except:
        pass
    try:
        driver.execute_script("document.body.scrollTop = document.body.scrollHeight;")
    except:
        pass
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    except:
        pass


# ---------------------------------------------------------
# 1. 네이버 지도
# ---------------------------------------------------------
def run_naver_crawler(place_name: str):
    driver = get_chrome_driver("naver")
    wait = WebDriverWait(driver, 10)
    reviews = []

    try:
        print(f"🔎 네이버 지도 '{place_name}' 검색 시작...")
        driver.get("https://map.naver.com/")
        time.sleep(2)

        search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.input_search")))
        search_box.clear()
        search_box.send_keys(place_name)
        search_box.send_keys(Keys.ENTER)
        
        # 🔥 네이버 지도는 무거워서 엔터 치고 넉넉히 기다려줘야 해! (2초 -> 4초로 변경)
        time.sleep(4)

        # 다이렉트 상세창 vs 검색 목록 분기
        try:
            # 상세창(entryIframe) 진입 대기 시간도 10초로 넉넉하게!
            WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))
            print("✅ 직접 상세창 진입.")
        except TimeoutException:
            print("⚠️ 검색 목록 감지! 첫 번째 항목 클릭 시도...")
            driver.switch_to.default_content()

            try:
                # 리스트창(searchIframe) 대기 시간 10초로 강화!
                WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))
                time.sleep(2)
            except TimeoutException:
                print("❌ searchIframe 로딩 지연 (네이버 서버 응답 늦음). 기존 검색어 유지.")
                pass

            clicked = False
            selectors = [
                "li[data-laim-exp-id='1'] a.place_bluelink",
                "li[data-laim-exp-id] a.place_bluelink",
                "#_pcmap_list_scroll_container li:first-child a.place_bluelink",
                "#_pcmap_list_scroll_container li:first-child a",
                ".place_bluelink",
            ]
            for sel in selectors:
                try:
                    el = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                    driver.execute_script("arguments[0].click();", el)
                    print(f"   → 클릭 성공: {sel}")
                    clicked = True
                    break
                except:
                    continue

            if not clicked:
                try:
                    el = driver.find_element(By.XPATH, "(//ul[contains(@id,'list') or contains(@class,'list')]//li//a)[1]")
                    driver.execute_script("arguments[0].click();", el)
                    clicked = True
                    print("   → XPath 폴백 클릭 성공")
                except:
                    print("⚠️ 첫 번째 검색 결과 클릭 실패 — 셀렉터 전부 미스")

            time.sleep(3) # 클릭 후 또 넉넉히 대기
            driver.switch_to.default_content()
            
            # 최종적으로 상세창 진입 시도
            try:
                WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))
            except TimeoutException:
                print("⚠️ 최종 상세창(entryIframe) 진입 실패.")

        # 리뷰 탭 클릭
        try:
            review_tab = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[text()='리뷰'] | //span[text()='리뷰'] | //a[span[text()='리뷰']]")
            ))
            driver.execute_script("arguments[0].click();", review_tab)
            print("✅ 리뷰 탭 클릭!")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ 리뷰 탭 클릭 실패: {e}")

        # 최신순 정렬
        print("🔃 최신순 정렬 시도...")
        try:
            latest_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((
                By.XPATH,
                "//a[text()='최신순'] | //button[text()='최신순'] | //span[text()='최신순'] | "
                "//li[contains(@class,'sort')]//a[contains(text(),'최신')]"
            )))
            driver.execute_script("arguments[0].click();", latest_btn)
            print("✅ 최신순!")
            time.sleep(2)
        except TimeoutException:
            try:
                sort_btn = driver.find_element(
                    By.XPATH,
                    "//div[contains(@class,'sort') or contains(@class,'Sort')]//button | "
                    "//div[contains(@class,'filter')]//button"
                )
                driver.execute_script("arguments[0].click();", sort_btn)
                time.sleep(0.5)
                opt = driver.find_element(
                    By.XPATH, "//a[text()='최신순'] | //li[text()='최신순'] | //span[text()='최신순']"
                )
                driver.execute_script("arguments[0].click();", opt)
                print("✅ 드롭다운 최신순!")
                time.sleep(2)
            except:
                print("⚠️ 최신순 버튼 없음.")

        # 리뷰 수집 루프
        print(f"📥 리뷰 수집 루프 시작 (목표: {NAVER_TARGET}개)...")
        max_attempts = 15
        no_change_count = 0
        prev_count = 0

        for attempt in range(max_attempts):
            expand_review_texts(driver)
            current = collect_naver_reviews_from_dom(driver)
            print(f"   [{attempt + 1}/{max_attempts}] 수집: {len(current)}개")

            if len(current) >= NAVER_TARGET:
                print("✅ 목표 달성!")
                reviews = current
                break

            if len(current) == prev_count:
                no_change_count += 1
            else:
                no_change_count = 0
            prev_count = len(current)

            if no_change_count >= 3:
                print(f"ℹ️ 새 리뷰 없음 3회 연속 → 수집 종료. 총 {len(current)}개")
                reviews = current
                break

            btn_clicked = click_list_more_btn(driver)

            if not btn_clicked:
                scroll_in_iframe(driver)
                time.sleep(2)
        else:
            reviews = collect_naver_reviews_from_dom(driver)
            print(f"ℹ️ 최대 시도 도달. 총 {len(reviews)}개.")

    except Exception as e:
        print(f"❌ 네이버 에러: {e}")
    finally:
        driver.quit()

    reviews = list(dict.fromkeys(reviews))
    print(f"✔️ 네이버 최종 {len(reviews)}개 (목표: {NAVER_TARGET})")
    return reviews[:NAVER_TARGET]


# ---------------------------------------------------------
# 2. 카카오맵
# ---------------------------------------------------------
def run_kakao_crawler(place_name: str):
    driver = get_chrome_driver("kakao")
    reviews = []
    try:
        driver.get("https://map.kakao.com/")
        time.sleep(3)

        search_box = driver.find_element(By.ID, "search.keyword.query")
        search_box.clear()
        search_box.send_keys(place_name)
        search_box.send_keys(Keys.ENTER)
        time.sleep(3)

        list_items = driver.find_elements(By.CSS_SELECTOR, "li.PlaceItem")
        target_url = None

        print(f"🔎 카카오맵 검색 결과 분석 중... (목표: {place_name})")
        
        for item in list_items:
            try:
                shop_name_el = item.find_element(By.CSS_SELECTOR, "a.link_name")
                shop_name = shop_name_el.text.strip()
                
                place_cond = place_name.replace(" ", "")
                shop_cond = shop_name.replace(" ", "")

                if place_cond in shop_cond or shop_cond in place_cond:
                    print(f"✅ 정확한 타겟 발견: {shop_name}")
                    more_btn = item.find_element(By.CSS_SELECTOR, "a[data-id='moreview']")
                    target_url = more_btn.get_attribute("href")
                    break
            except:
                continue

        if not target_url:
            print("⚠️ 텍스트 일치 항목 없음. 첫 번째 결과 강제 클릭.")
            more_views = driver.find_elements(By.CSS_SELECTOR, "a[data-id='moreview']")
            if more_views:
                target_url = more_views[0].get_attribute("href")

        if target_url:
            driver.get(target_url)
            time.sleep(3)

            try:
                review_tab = driver.find_element(
                    By.XPATH, "//a[contains(text(), '후기')] | //span[contains(text(), '후기')]"
                )
                driver.execute_script("arguments[0].click();", review_tab)
                print("✅ 카카오 후기 탭!")
                time.sleep(2)
            except:
                print("⚠️ 카카오 후기 탭 미발견.")

            try:
                latest_btn = driver.find_element(
                    By.XPATH,
                    "//a[text()='최신순'] | //button[text()='최신순'] | //span[text()='최신순'] | "
                    "//a[@data-sort='date'] | //button[@data-sort='date'] | "
                    "//a[contains(text(),'최신')] | //button[contains(text(),'최신')]"
                )
                driver.execute_script("arguments[0].click();", latest_btn)
                print("✅ 카카오 최신순!")
                time.sleep(2)
            except:
                try:
                    sort_select = driver.find_element(
                        By.XPATH, "//select[contains(@class,'sort') or contains(@name,'sort')]"
                    )
                    Select(sort_select).select_by_visible_text("최신순")
                    time.sleep(2)
                except:
                    print("⚠️ 카카오 최신순 버튼 미발견.")

            for i in range(10):
                more_btns = driver.find_elements(
                    By.XPATH,
                    "//span[text()='더보기'] | //a[text()='더보기'] | //button[text()='더보기']"
                )
                if not more_btns:
                    break
                for btn in more_btns:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.3)
                    except:
                        pass
                time.sleep(1)
                cur = driver.find_elements(By.CSS_SELECTOR, ".txt_comment, p.desc_txt")
                if len(cur) >= KAKAO_TARGET:
                    break

            review_elements = driver.find_elements(
                By.CSS_SELECTOR, ".txt_comment, p.desc_txt, .review_txt, [class*='comment_text']"
            )
            for review in review_elements:
                text = review.text.strip().replace('\n', ' ').replace('\r', ' ')
                text = text.replace("더보기", "").replace("접기", "").strip()
                if is_real_review(text):
                    reviews.append(text)

            if not reviews:
                for p in driver.find_elements(By.TAG_NAME, "p"):
                    text = p.text.strip().replace('\n', ' ').replace('\r', ' ')
                    text = text.replace("더보기", "").replace("접기", "").strip()
                    if is_real_review(text):
                        reviews.append(text)

    except Exception as e:
        print(f"❌ 카카오 에러: {e}")
    finally:
        driver.quit()

    reviews = list(dict.fromkeys(reviews))
    print(f"✔️ 카카오 최종 {len(reviews)}개 수집 완료")
    return reviews[:KAKAO_TARGET]

# 감성 분석 서버 주소
SENTIMENT_SERVER = "http://localhost:8002"

def call_sentiment_server(texts: list) -> list:
    if not texts:
        return []
    try:
        response = requests.post(
            f"{SENTIMENT_SERVER}/analyze",
            json={"texts": texts},
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.ConnectionError:
        print("⚠️ 감성 분석 서버가 꺼져 있습니다. 키워드 분석으로 대체합니다.")
    except Exception as e:
        print(f"⚠️ 감성 분석 서버 오류: {e}")
    return []


def analyze_reviews(reviews: list, platform: str) -> dict:
    if not reviews:
        return {
            "score": 0.0,
            "keywords": ["데이터 없음"],
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "analysis_type": "none"
        }

    # 1차: 감성 분석 서버 시도 (KoBERT 기반)
    sentiment_results = call_sentiment_server(reviews)

    if sentiment_results:
        total = len(sentiment_results)
        avg_positive = sum(r["positive"] for r in sentiment_results) / total
        avg_negative = sum(r["negative"] for r in sentiment_results) / total

        # 감성 점수 → 5점 척도로 변환
        score = 1.0 + (avg_positive * 4.0)

        return {
            "score": round(score, 1),
            "keywords": [],
            "positive_ratio": round(avg_positive * 100, 1),
            "negative_ratio": round(avg_negative * 100, 1),
            "analysis_type": "ai"
        }

    # 2차: 서버 오류시 기존 키워드 방식으로 폴백
    good_words = ['맛있', '좋', '친절', '최고', '분위기', '깔끔', '가성비']
    bad_words  = ['불친절', '별로', '비싸', '맛없', '최악', '오래', '냄새']

    score = 3.0
    extracted_keywords = set()
    for text in reviews:
        for gw in good_words:
            if gw in text:
                score += 0.2
                extracted_keywords.add(f"#{gw}")
        for bw in bad_words:
            if bw in text:
                score -= 0.3
                extracted_keywords.add(f"#{bw}")

    final_score = max(1.0, min(5.0, score + random.uniform(-0.5, 0.5)))
    if not extracted_keywords:
        extracted_keywords = {"#무난함", "#평범함", "#가볼만함"}

    return {
        "score": round(final_score, 1),
        "keywords": list(extracted_keywords)[:3],
        "positive_ratio": 0.0,
        "negative_ratio": 0.0,
        "analysis_type": "keyword"
    }


@app.get("/api/crawl")
def crawl(place: str):
    print(f"🚀 [RE:VIEW] '{place}' 수집 시작...")

    naver_reviews = run_naver_crawler(place)
    kakao_reviews = run_kakao_crawler(place)

    # DB 저장
    db = SessionLocal()
    try:
        place_row = db.query(Place).filter(Place.place_name == place).first()
        if not place_row:
            place_row = Place(place_name=place)
            db.add(place_row)
            db.commit()
            db.refresh(place_row)

        existing_texts = {
            r.content_text
            for r in db.query(Review).filter(Review.place_id == place_row.id).all()
        }

        new_reviews = []
        for text in naver_reviews:
            if text not in existing_texts:
                new_reviews.append(Review(place_id=place_row.id, platform="naver", content_text=text))
        for text in kakao_reviews:
            if text not in existing_texts:
                new_reviews.append(Review(place_id=place_row.id, platform="kakao", content_text=text))

        if new_reviews:
            db.bulk_save_objects(new_reviews)
            db.commit()
            print(f"💾 DB 저장: 신규 {len(new_reviews)}개 적재")
        else:
            print("ℹ️ 신규 리뷰 없음 (전부 중복)")

        # 감성 분석 결과 DB 저장
        all_reviews_in_db = db.query(Review).filter(Review.place_id == place_row.id).all()
        sentiment_all = call_sentiment_server([r.content_text for r in all_reviews_in_db])
        if sentiment_all:
            for i, review_row in enumerate(all_reviews_in_db):
                if i < len(sentiment_all):
                    exists = db.query(SentimentResult).filter(
                        SentimentResult.review_id == review_row.id
                    ).first()
                    if not exists:
                        db.add(SentimentResult(
                            review_id=review_row.id,
                            positive_prob=sentiment_all[i]["positive"],
                            negative_prob=sentiment_all[i]["negative"],
                            extracted_keywords=json.dumps([], ensure_ascii=False)
                        ))
            db.commit()
            print("💾 감성 분석 결과 DB 저장 완료") 

        # 작성자 프로필 저장 (reviewer_id 있는 리뷰만)
        all_reviews = db.query(Review).filter(Review.place_id == place_row.id).all()
        reviewer_ids = set(
            (r.reviewer_id, r.platform)
            for r in all_reviews
            if r.reviewer_id
        )
        for rid, platform in reviewer_ids:
            save_reviewer_profile(rid, platform)
        if reviewer_ids:
            print(f"💾 작성자 프로필 {len(reviewer_ids)}개 저장 완료")
    
    except Exception as e:
        db.rollback()
        print(f"❌ DB 저장 오류: {e}")
    finally:
        db.close()

    naver_analysis = analyze_reviews(naver_reviews, "naver")
    kakao_analysis = analyze_reviews(kakao_reviews, "kakao")

    diff = abs(naver_analysis['score'] - kakao_analysis['score'])
    anomaly_score = round((diff / 5.0) * 100, 1)

    abusing_result = calc_abusing_score(place_row.id)
    print(f"🔍 어뷰징 분석 완료: {abusing_result['grade']} (점수: {abusing_result['abusing_score']})")

    # 교차 키워드 추출
    print("🔍 교차 키워드 추출 중...")
    keyword_result = extract_cross_keywords(naver_reviews, kakao_reviews)

    # 베이지안 평균 계산
    naver_bayes = calc_platform_bayesian(place_row.id, "naver")
    kakao_bayes = calc_platform_bayesian(place_row.id, "kakao")
    print(f"📊 베이지안 평균 → 네이버: {naver_bayes['bayesian_avg']} / 카카오: {kakao_bayes['bayesian_avg']}")

    # 감성 괴리율 계산
    discrepancy_rate = round(
        abs(naver_bayes['bayesian_avg'] - kakao_bayes['bayesian_avg']) / 5.0 * 100, 1
    )

    # DashboardReport 저장
    save_dashboard_report(
        place_id         = place_row.id,
        discrepancy_rate = discrepancy_rate,
        cross_keywords   = keyword_result['cross_keywords'],
        is_abusing       = abusing_result['is_abusing']
    )

    return {
        "place": place,
        "naver": {
            "score": naver_analysis['score'],
            "bayesian_avg" : naver_bayes['bayesian_avg'],
            "keywords": naver_analysis['keywords'],
            "positive_ratio": naver_analysis['positive_ratio'],
            "negative_ratio": naver_analysis['negative_ratio'],
            "analysis_type": naver_analysis['analysis_type'],
            "review_count": len(naver_reviews),
            "target_count": NAVER_TARGET,
            "is_sufficient": len(naver_reviews) >= NAVER_TARGET,
            "raw_reviews": naver_reviews,
        },
        "kakao": {
            "score": kakao_analysis['score'],
            "bayesian_avg"   : kakao_bayes['bayesian_avg'],
            "keywords": kakao_analysis['keywords'],
            "positive_ratio": kakao_analysis['positive_ratio'],
            "negative_ratio": kakao_analysis['negative_ratio'],
            "analysis_type": kakao_analysis['analysis_type'],
            "review_count": len(kakao_reviews),
            "target_count": KAKAO_TARGET,
            # 🔥 10개 이상이면 프론트에서 "수집완료"로 판정하도록 10으로 고정!
            "is_sufficient": len(kakao_reviews) >= 10,
            "raw_reviews": kakao_reviews,
        },
        "cross_keywords": {
            "common"      : keyword_result['cross_keywords'],
            "naver_only"  : keyword_result['naver_only'],
            "kakao_only"  : keyword_result['kakao_only'],
            "naver_top"   : keyword_result['naver_top'],
            "kakao_top"   : keyword_result['kakao_top'],
        },
        "anomaly": {
            "score" : abusing_result['abusing_score'],
            "grade" : abusing_result['grade'],
            "is_absuing" : abusing_result['is_abusing'],
            "spike_detail" : abusing_result['spike_detail'],
            "similarity_detail" : abusing_result['similarity_detail'],
        },
        "discrepancy_rate": discrepancy_rate,
        "status": "success",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)