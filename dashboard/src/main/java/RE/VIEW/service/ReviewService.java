package RE.VIEW.service;

import RE.VIEW.entity.Place;
import RE.VIEW.entity.Review;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import java.util.Map;
import java.util.List;

@Service
public class ReviewService {

    private final String PYTHON_API_URL = "http://52.79.251.32:8001/api/crawl?place=";

    public Map<String, Object> getReviewData(String place) {
        RestTemplate restTemplate = new RestTemplate();

        System.out.println("파이썬 일꾼에게 [" + place + "] 수집 요청 중...");
        Map<String, Object> response = restTemplate.getForObject(PYTHON_API_URL + place, Map.class);

        return response;
    }

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