# [RE:VIEW] 다중 플랫폼 리뷰 이상 탐지 대시보드

<div align="center">
  <img width="800" height="400" alt="RE:VIEW Banner" src="https://github.com/user-attachments/assets/cb3922d7-0031-47a2-b02d-bba4b990673a" />
</div>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat-square&logo=flask&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.x-6DB33F?style=flat-square&logo=springboot&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat-square&logo=sqlite&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-FFD21E?style=flat-square&logo=huggingface&logoColor=black)

</div>

> 네이버 지도 및 카카오맵의 리뷰 데이터를 실시간으로 수집하고, KoELECTRA 기반 AI 감성 분석과 통계적 이상 탐지를 통해 **플랫폼 간 평점 괴리율** 및 **어뷰징(리뷰 조작) 패턴**을 탐지하는 통합 대시보드 시스템입니다.

---

## 서비스 배포 정보 
현재 AWS EC2 환경에 무중단 배포되어 구동 중입니다.

🔗 **[RE:VIEW 웹 대시보드 접속하기](http://52.79.251.32:8080/index.html)**
* 서비스 URL: http://52.79.251.32:8080/index.html
---

## 시스템 아키텍처 (System Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                        사용자 브라우저                        │
│              Spring Boot 대시보드 (Port 8080)                │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (REST API 호출)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            FastAPI 크롤링·분석 서버 (Port 8001)              │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Selenium    │    │  anomaly.py  │    │  keywords.py │  │
│  │  Crawler     │    │  어뷰징 탐지  │    │  교차 키워드  │  │
│  │ (네이버·카카오)│    │  스파이크     │    │  베이지안 평균│  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                  │                   │           │
│         └──────────────────┴───────────────────┘           │
│                            │                               │
│                     ┌──────▼───────┐                       │
│                     │  SQLite DB   │                       │
│                     │  review.db   │                       │
│                     └──────────────┘                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (감성 분석 요청)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           Flask AI 감성 분석 서버 (Port 8002)                │
│      monologg/koelectra-base-finetuned-sentiment 모델       │
└─────────────────────────────────────────────────────────────┘
```

---

## 프로젝트 구조 (Project Structure)

```
RE_VIEW/
│
├── main.py              # FastAPI 메인 서버 (크롤링 + 분석 통합 엔드포인트)
├── sentiment.py         # Flask AI 감성 분석 서버 (KoELECTRA 모델 호스팅)
├── database.py          # SQLAlchemy ORM 모델 및 DB 세션 관리
├── anomaly.py           # 어뷰징 탐지 모듈 (스파이크·유사도 분석)
├── keywords.py          # 교차 키워드 추출 + 베이지안 평균 산출 모듈
├── review.db            # SQLite 데이터베이스 (자동 생성)
│
└── dashboard/           # Spring Boot 대시보드 서버
    ├── src/
    │   └── main/
    │       └── resources/
    │           └── static/
    │               └── index.html   # 메인 대시보드 UI (Tailwind CSS + Chart.js)
    ├── build.gradle
    └── gradlew
```

---

## 사전 요구사항 (Prerequisites)

실행 전 아래 항목이 설치되어 있는지 반드시 확인하세요.

| 항목 | 버전 | 확인 명령어 |
| :--- | :--- | :--- |
| **Python** | 3.10 이상 | `python --version` |
| **Java (JDK)** | 17 이상 | `java -version` |
| **Google Chrome** | 최신 버전 | Chrome 설정 → Chrome 정보 |
| **pip** | 최신 권장 | `pip --version` |

---

## 로컬 빌드 및 실행 (Local Setup)
*※ AWS 서버 접속 불가 등 예비 상황을 위한 로컬 구동 안내입니다. (code 브랜치 기준)*

```bash
# 0. 프로젝트 클론 (소스 코드가 있는 code 브랜치 다운로드)
git clone -b code https://github.com/MiinJuun/OSS_Project.git
cd OSS_Project

# 1. 파이썬 가상환경 생성 및 패키지 설치 
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # (또는 pip install fastapi uvicorn flask selenium 등)

# 2. 파이썬 서버 구동
nohup python3 sentiment.py > sentiment.log 2>&1 &
nohup python3 main.py > python_server.log 2>&1 &

# 3. Spring Boot 대시보드 구동
cd dashboard
./gradlew build -x test
nohup java -jar build/libs/*SNAPSHOT.jar > spring_server.log 2>&1 &
```
---

## 개발 환경 (Development Environment)

| 항목 | 내용 |
| :--- | :--- |
| OS | Windows 11 |
| IDE | VS Code (Python), IntelliJ IDEA (Spring Boot) |
| Python | 3.10+ |
| 주요 라이브러리 | FastAPI, Flask, SQLAlchemy, Selenium, Transformers, KoNLPy |
| AI 모델 | `monologg/koelectra-base-finetuned-sentiment` (HuggingFace) |
| DB | SQLite (via SQLAlchemy ORM) |
| 프론트엔드 | HTML5 + Tailwind CSS + Chart.js |

---

## 개발자 정보

| 항목 | 내용 |
| :--- | :--- |
| **이름** | 박민준 |
| **학번** | 22211988 |
| **이메일** | akio7689@naver.com |
