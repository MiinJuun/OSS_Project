# sentiment.py
from flask import Flask, request, jsonify
from transformers import pipeline
import torch

app_sentiment = Flask(__name__)

print("🤖 감성 분석 모델 로딩 중... (최초 1회 약 5~10분 소요)")

# ▼ 모델명 수정 (실제 존재하는 한국어 감성분석 모델)
sentiment_pipeline = pipeline(
    "text-classification",
    model="monologg/koelectra-base-finetuned-sentiment",
    tokenizer="monologg/koelectra-base-finetuned-sentiment",
    device=0 if torch.cuda.is_available() else -1
)

print("✅ 감성 분석 모델 로딩 완료!")


def analyze_text(text: str) -> dict:
    try:
        result = sentiment_pipeline(text[:256])[0]
        label = result["label"]   # "positive" or "negative"
        score = result["score"]

        if label == "positive":
            return {"positive": round(score, 4), "negative": round(1 - score, 4)}
        else:
            return {"positive": round(1 - score, 4), "negative": round(score, 4)}
    except Exception as e:
        print(f"분석 오류: {e}")
        return {"positive": 0.5, "negative": 0.5}


@app_sentiment.route("/analyze", methods=["POST"])
def analyze():
    texts = request.json.get("texts", [])
    if not texts:
        return jsonify([])
    print(f"📝 {len(texts)}개 텍스트 분석 중...")
    results = [analyze_text(t) for t in texts]
    print("✅ 분석 완료")
    return jsonify(results)


@app_sentiment.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app_sentiment.run(host="0.0.0.0", port=8002, debug=False)
