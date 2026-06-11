# keywords.py
from konlpy.tag import Okt
from collections import Counter
from database import SessionLocal, Review, DashboardReport
import json

okt = Okt()

# -------------------------------------------------------
# 불용어 목록 (분석에서 제외할 단어들)
# -------------------------------------------------------
STOPWORDS = {
    # 1글자
    '것', '수', '때', '곳', '점', '분', '거', '등', '번', '잔', '집', '맛', '곳',
    # 일반 명사 (리뷰에서 의미 없는 단어)
    '방문', '매장', '메뉴', '음식', '가게', '식당', '주문', '서비스', '이용',
    '느낌', '정도', '생각', '경우', '부분', '자리', '테이블', '직원', '손님',
    # 지시어/접속어
    '이번', '다음', '여기', '저기', '이거', '저거', '이게', '저게',
}


# -------------------------------------------------------
# UC-7: 교차 검증 키워드 추출
# -------------------------------------------------------

def extract_keywords_from_reviews(reviews: list, top_n: int = 20) -> Counter:
    """
    리뷰 텍스트 리스트에서 형태소 분석 후
    명사 위주 다빈도 키워드 Counter 반환
    """
    word_counts = Counter()

    for text in reviews:
        try:
            # 명사 추출 (일반명사 + 고유명사)
            nouns = okt.nouns(text)
            filtered = [
                word for word in nouns
                if len(word) >= 2 and word not in STOPWORDS
            ]
            word_counts.update(filtered)
        except Exception as e:
            print(f"⚠️ 형태소 분석 오류 (스킵): {e}")
            continue

    return word_counts


def extract_cross_keywords(
    naver_reviews: list,
    kakao_reviews: list,
    top_n: int = 10
) -> dict:
    """
    양 플랫폼에서 공통으로 언급된 교차 검증 키워드 추출

    반환값:
    {
        "cross_keywords"  : ["돈까스", "육즙", ...],  ← 양쪽 공통
        "naver_only"      : ["주차", ...],             ← 네이버에만 있는 상위 키워드
        "kakao_only"      : ["훈연", ...],             ← 카카오에만 있는 상위 키워드
        "naver_top"       : {"돈까스": 15, ...},
        "kakao_top"       : {"육즙": 8, ...}
    }
    """
    print("🔍 형태소 분석 중...")

    naver_counter = extract_keywords_from_reviews(naver_reviews, top_n)
    kakao_counter = extract_keywords_from_reviews(kakao_reviews, top_n)

    naver_top_keys = set(dict(naver_counter.most_common(top_n)).keys())
    kakao_top_keys = set(dict(kakao_counter.most_common(top_n)).keys())

    # 교집합: 양쪽 모두 상위에 등장한 키워드
    common_keys = naver_top_keys & kakao_top_keys

    # 교차 키워드를 두 플랫폼 빈도 합산 기준으로 정렬
    cross_keywords = sorted(
        common_keys,
        key=lambda w: naver_counter[w] + kakao_counter[w],
        reverse=True
    )

    # 각 플랫폼 단독 키워드 (교차 키워드에 없는 것)
    naver_only = [k for k in naver_top_keys - common_keys][:5]
    kakao_only = [k for k in kakao_top_keys - common_keys][:5]

    print(f"✅ 교차 키워드 {len(cross_keywords)}개 추출 완료")

    return {
        "cross_keywords": cross_keywords[:top_n],
        "naver_only"    : naver_only,
        "kakao_only"    : kakao_only,
        "naver_top"     : dict(naver_counter.most_common(top_n)),
        "kakao_top"     : dict(kakao_counter.most_common(top_n)),
    }


# -------------------------------------------------------
# UC-9: 베이지안 평균 (표본 수 불균형 보정)
# -------------------------------------------------------

def bayesian_average(
    scores: list,
    global_mean: float = 3.5,
    confidence: int = 10
) -> float:
    """
    베이지안 평균으로 표본 수 불균형 보정

    원리:
    - 리뷰가 적을수록 전체 평균(global_mean)으로 수렴
    - 리뷰가 많을수록 실제 평균에 가까워짐

    예시:
    - 리뷰 3개, 평균 5.0  →  베이지안 평균 ≈ 4.1  (극단값 보정됨)
    - 리뷰 100개, 평균 5.0 → 베이지안 평균 ≈ 4.9  (신뢰도 높아 실제값에 근접)

    scores     : 점수 리스트 (1.0~5.0 척도)
    global_mean: 전체 평균 사전값 (기본 3.5)
    confidence : 사전 신뢰 샘플 수 (높을수록 보수적, 기본 10)
    """
    n = len(scores)
    if n == 0:
        return round(global_mean, 2)

    raw_avg = sum(scores) / n
    bayes_avg = (confidence * global_mean + n * raw_avg) / (confidence + n)

    return round(bayes_avg, 2)


def calc_platform_bayesian(place_id: int, platform: str) -> dict:
    """
    DB에 저장된 감성 점수를 기반으로 베이지안 평균 계산

    리뷰의 positive_prob을 1~5 척도로 변환 후 베이지안 평균 적용
    """
    db = SessionLocal()
    try:
        from database import SentimentResult

        # 해당 장소 + 플랫폼의 리뷰 감성 결과 조회
        results = (
            db.query(SentimentResult)
            .join(Review, SentimentResult.review_id == Review.id)
            .filter(
                Review.place_id == place_id,
                Review.platform == platform
            )
            .all()
        )

        if not results:
            return {
                "raw_avg"    : 0.0,
                "bayesian_avg": 0.0,
                "review_count": 0
            }

        # positive_prob → 1.0~5.0 척도 변환
        scores = [1.0 + (r.positive_prob * 4.0) for r in results]

        raw_avg    = round(sum(scores) / len(scores), 2)
        bayes_avg  = bayesian_average(scores)

        return {
            "raw_avg"     : raw_avg,
            "bayesian_avg": bayes_avg,
            "review_count": len(scores)
        }

    finally:
        db.close()


# -------------------------------------------------------
# DashboardReport DB 저장
# -------------------------------------------------------

def save_dashboard_report(
    place_id        : int,
    discrepancy_rate: float,
    cross_keywords  : list,
    is_abusing      : bool
):
    """
    최종 분석 결과를 DashboardReport 테이블에 저장
    같은 장소 기존 리포트는 최신 데이터로 UPDATE
    """
    db = SessionLocal()
    try:
        existing = db.query(DashboardReport).filter(
            DashboardReport.place_id == place_id
        ).first()

        keywords_json = json.dumps(cross_keywords, ensure_ascii=False)

        if existing:
            existing.discrepancy_rate     = discrepancy_rate
            existing.cross_keywords       = keywords_json
            existing.is_abusing_suspected = is_abusing
        else:
            db.add(DashboardReport(
                place_id             = place_id,
                discrepancy_rate     = discrepancy_rate,
                cross_keywords       = keywords_json,
                is_abusing_suspected = is_abusing
            ))

        db.commit()
        print("💾 DashboardReport 저장 완료")

    finally:
        db.close()
