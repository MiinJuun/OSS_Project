package RE.VIEW.service;

import RE.VIEW.entity.Place;
import RE.VIEW.entity.Review;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import java.util.Map;
import java.util.List;

@Service
public class ReviewService {

    // 파이썬 서버 주소 (네가 작성한 기존 코드 유지)
    private final String PYTHON_API_URL = "http://52.79.251.32:8001/api/crawl?place=";

    public Map<String, Object> getReviewData(String place) {
        RestTemplate restTemplate = new RestTemplate();

        // 파이썬에게 전화를 걸어 데이터를 받아옵니다. (기존 로직 유지)
        System.out.println("📞 파이썬 일꾼에게 [" + place + "] 수집 요청 중...");
        Map<String, Object> response = restTemplate.getForObject(PYTHON_API_URL + place, Map.class);

        return response;
    }

    // --- 아래부터는 다이어그램 설계도와 100% 맞추기 위해 추가된 뼈대 메서드들 ---

    public Place savePlace(Map<String, Object> data) {
        return null;
    }

    public void saveReviews(Map<String, Object> data, Place place) {
    }

    public void saveDashboardReport(Place place, double score) {
    }

    public List<Review> getReviewsByPlatform(Long placeId, String platform) {
        return null;
    }
}