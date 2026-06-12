from database import SessionLocal, Review, ReviewerProfile, AnomalyLog
from collections import Counter
from datetime import datetime, timedelta
import re
from typing import Optional

# UC-3: 작성자 신뢰도 지수 산출
def calc_reliability_score(reviewer_id: str, platform: str) -> Optional[float]:
    """
    작성자의 과거 활동 패턴을 분석해 신뢰도 지수(0.0~1.0) 반환
    데이터 부족 시 None 반환 (= 판별 불가)

    감점 기준:
    - 리뷰 총 수가 3개 미만     → 판별 불가 (None)
    - 5점 비율이 90% 초과       → -0.4점
    - 리뷰 총 수가 5개 미만     → -0.2점 (적은 리뷰로 극단적 평가 가능성)
    - 특정 시간대 집중 작성     → -0.3점 (추후 확장용 슬롯)
    """
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.reviewer_id == reviewer_id,
            Review.platform == platform
        ).all()

        total = len(reviews)

        if total < 3:
            return None

        rated = [r for r in reviews if r.star_rating is not None]
        five_star_ratio = (
            sum(1 for r in rated if r.star_rating == 5.0) / len(rated)
            if rated else 0.0
        )

        score = 1.0

        if five_star_ratio > 0.9:
            score -= 0.4

        if total < 5:
            score -= 0.2

        return round(max(0.0, score), 2)

    finally:
        db.close()


def save_reviewer_profile(reviewer_id: str, platform: str):
    """
    리뷰어 프로필 계산 후 DB 저장 (없으면 INSERT, 있으면 UPDATE)
    """
    if not reviewer_id:
        return

    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.reviewer_id == reviewer_id,
            Review.platform == platform
        ).all()

        total = len(reviews)
        rated = [r for r in reviews if r.star_rating is not None]
        five_star_ratio = (
            sum(1 for r in rated if r.star_rating == 5.0) / len(rated)
            if rated else 0.0
        )
        reliability = calc_reliability_score(reviewer_id, platform)

        existing = db.query(ReviewerProfile).filter(
            ReviewerProfile.reviewer_id == reviewer_id
        ).first()

        if existing:
            existing.total_review_count = total
            existing.five_star_ratio    = round(five_star_ratio, 4)
            existing.reliability_score  = reliability
        else:
            db.add(ReviewerProfile(
                reviewer_id        = reviewer_id,
                platform           = platform,
                total_review_count = total,
                five_star_ratio    = round(five_star_ratio, 4),
                reliability_score  = reliability
            ))

        db.commit()

    finally:
        db.close()

# UC-6: 시계열 스파이크 탐지 (단기간 리뷰 급증)
def detect_spike(place_id: int, window_days: int = 7, threshold: float = 3.0) -> dict:
    """
    특정 장소의 리뷰 시계열 데이터를 분석해 급증 패턴 탐지

    window_days : 최근 며칠을 '단기간'으로 볼 것인지
    threshold   : 평균 대비 몇 배 이상이면 스파이크로 판단할 것인지

    반환값:
    {
        "is_spike"       : True/False,
        "recent_count"   : 최근 window_days 내 리뷰 수,
        "monthly_avg"    : 월평균 리뷰 수,
        "spike_ratio"    : 급증 배율,
        "detected_month" : 스파이크 감지 월
    }
    """
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(Review.place_id == place_id).all()

        dates = []
        for r in reviews:
            if r.written_date:
                try:
                    month_str = r.written_date[:7]
                    dates.append(month_str)
                except:
                    pass
            else:
                dates.append(r.collected_at.strftime("%Y-%m"))

        if not dates:
            return {
                "is_spike": False,
                "recent_count": 0,
                "monthly_avg": 0.0,
                "spike_ratio": 0.0,
                "detected_month": None
            }

        monthly_counts = Counter(dates)
        avg = sum(monthly_counts.values()) / len(monthly_counts)

        recent_month = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m")
        current_month = datetime.now().strftime("%Y-%m")

        recent_count = max(
            monthly_counts.get(recent_month, 0),
            monthly_counts.get(current_month, 0)
        )
        spike_ratio = round(recent_count / avg, 2) if avg > 0 else 0.0
        is_spike = spike_ratio >= threshold and recent_count >= 5  

        if is_spike:
            db.add(AnomalyLog(
                place_id       = place_id,
                anomaly_type   = "spike",
                threshold      = threshold,
                detected_value = spike_ratio
            ))
            db.commit()

        return {
            "is_spike"      : is_spike,
            "recent_count"  : recent_count,
            "monthly_avg"   : round(avg, 1),
            "spike_ratio"   : spike_ratio,
            "detected_month": current_month
        }

    finally:
        db.close()


# UC-6: 텍스트 유사도 기반 복붙 리뷰 탐지
def detect_similar_reviews(place_id: int, similarity_threshold: float = 0.7) -> dict:
    """
    같은 장소 리뷰 중 텍스트가 지나치게 유사한 쌍을 탐지
    (마케팅 업체 복붙 리뷰 패턴 감지)

    자카드 유사도(Jaccard Similarity) 사용:
    - 두 텍스트를 어절(띄어쓰기) 단위로 쪼갠 집합의 교집합/합집합 비율
    - 1.0에 가까울수록 동일한 문장
    """
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(Review.place_id == place_id).all()

        if len(reviews) < 2:
            return {"is_suspicious": False, "similar_pairs": 0, "suspicious_reviews": []}

        def jaccard(text_a: str, text_b: str) -> float:
            set_a = set(text_a.split())
            set_b = set(text_b.split())
            if not set_a or not set_b:
                return 0.0
            return len(set_a & set_b) / len(set_a | set_b)

        similar_pairs = 0
        suspicious_ids = set()

        for i in range(len(reviews)):
            for j in range(i + 1, len(reviews)):
                sim = jaccard(reviews[i].content_text, reviews[j].content_text)
                if sim >= similarity_threshold:
                    similar_pairs += 1
                    suspicious_ids.add(reviews[i].id)
                    suspicious_ids.add(reviews[j].id)

        is_suspicious = similar_pairs >= 3  

        if is_suspicious:
            db.add(AnomalyLog(
                place_id       = place_id,
                anomaly_type   = "similarity",
                threshold      = similarity_threshold,
                detected_value = float(similar_pairs)
            ))
            db.commit()

        return {
            "is_suspicious"     : is_suspicious,
            "similar_pairs"     : similar_pairs,
            "suspicious_reviews": list(suspicious_ids)
        }

    finally:
        db.close()

def calc_abusing_score(place_id: int) -> dict:
    """
    스파이크 + 유사도 탐지 결과를 종합해
    최종 어뷰징 의심 점수(0~100)와 등급 반환

    등급 기준:
    - 0~30  : Trusted (신뢰)
    - 31~60 : Medium Risk (주의)
    - 61~100: High Risk (어뷰징 강한 의심)
    """
    spike_result     = detect_spike(place_id)
    sim_result       = detect_similar_reviews(place_id)

    score = 0.0

    if spike_result["is_spike"]:
        spike_contribution = min(50.0, spike_result["spike_ratio"] * 10)
        score += spike_contribution

    if sim_result["is_suspicious"]:
        sim_contribution = min(50.0, sim_result["similar_pairs"] * 5)
        score += sim_contribution

    score = round(min(100.0, score), 1)

    if score <= 30:
        grade = "Trusted"
    elif score <= 60:
        grade = "Medium Risk"
    else:
        grade = "High Risk"

    return {
        "abusing_score"  : score,
        "grade"          : grade,
        "is_abusing"     : score > 30,
        "spike_detail"   : spike_result,
        "similarity_detail": sim_result
    }
