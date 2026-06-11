from sqlalchemy import create_engine, Column, Integer, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./review.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# 1. TargetPlace
class Place(Base):
    __tablename__ = "places"
    id              = Column(Integer, primary_key=True, index=True)
    place_name      = Column(Text, nullable=False)
    category        = Column(Text, nullable=True)
    naver_place_url = Column(Text, nullable=True)
    kakao_place_url = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    reviews         = relationship("Review", back_populates="place")
    metrics         = relationship("PlatformMetrics", back_populates="place")


# 2. ReviewData
class Review(Base):
    __tablename__ = "reviews"
    id              = Column(Integer, primary_key=True, index=True)
    place_id        = Column(Integer, ForeignKey("places.id"), nullable=False)
    platform        = Column(Text, nullable=False)   # 'naver' | 'kakao'
    content_text    = Column(Text, nullable=False)
    star_rating     = Column(Float, nullable=True)
    written_date    = Column(Text, nullable=True)
    reviewer_id     = Column(Text, nullable=True)
    collected_at    = Column(DateTime, default=datetime.utcnow)

    place           = relationship("Place", back_populates="reviews")
    sentiment       = relationship("SentimentResult", back_populates="review", uselist=False)
    reviewer        = relationship(
                        "ReviewerProfile",
                        primaryjoin="Review.reviewer_id == foreign(ReviewerProfile.reviewer_id)",
                        uselist=False,
                        viewonly=True
                      )


# 3. ReviewerProfile
class ReviewerProfile(Base):
    __tablename__ = "reviewer_profiles"
    id                  = Column(Integer, primary_key=True, index=True)
    reviewer_id         = Column(Text, unique=True, nullable=False)
    platform            = Column(Text, nullable=False)
    total_review_count  = Column(Integer, default=0)
    five_star_ratio     = Column(Float, default=0.0)
    reliability_score   = Column(Float, nullable=True)   # 0.0 ~ 1.0, None = 판별 불가


# 4. SentimentResult
class SentimentResult(Base):
    __tablename__ = "sentiment_results"
    id                  = Column(Integer, primary_key=True, index=True)
    review_id           = Column(Integer, ForeignKey("reviews.id"), unique=True, nullable=False)
    positive_prob       = Column(Float, nullable=False)
    negative_prob       = Column(Float, nullable=False)
    extracted_keywords  = Column(Text, nullable=True)   # JSON 문자열로 저장 ex) '["맛있","친절"]'

    review              = relationship("Review", back_populates="sentiment")


# 5. PlatformMetrics
class PlatformMetrics(Base):
    __tablename__ = "platform_metrics"
    id                  = Column(Integer, primary_key=True, index=True)
    place_id            = Column(Integer, ForeignKey("places.id"), nullable=False)
    platform            = Column(Text, nullable=False)
    total_review_count  = Column(Integer, default=0)
    bayesian_avg_score  = Column(Float, nullable=True)
    collected_at        = Column(DateTime, default=datetime.utcnow)

    place               = relationship("Place", back_populates="metrics")


# 6. DashboardReport
class DashboardReport(Base):
    __tablename__ = "dashboard_reports"
    id                   = Column(Integer, primary_key=True, index=True)
    place_id             = Column(Integer, ForeignKey("places.id"), nullable=False)
    discrepancy_rate     = Column(Float, nullable=True)       # 감성 괴리율 (%)
    cross_keywords       = Column(Text, nullable=True)        # JSON 문자열
    is_abusing_suspected = Column(Boolean, default=False)     # UC-6 어뷰징 의심 여부
    generated_at         = Column(DateTime, default=datetime.utcnow)


# 7. AnomalyDetector (탐지 이력 로그 테이블)
class AnomalyLog(Base):
    __tablename__ = "anomaly_logs"
    id               = Column(Integer, primary_key=True, index=True)
    place_id         = Column(Integer, ForeignKey("places.id"), nullable=False)
    anomaly_type     = Column(Text, nullable=False)    # 'spike' | 'similarity' | 'profile'
    threshold        = Column(Float, nullable=True)
    detected_value   = Column(Float, nullable=True)
    detected_at      = Column(DateTime, default=datetime.utcnow)


# 테이블 전체 생성
def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
