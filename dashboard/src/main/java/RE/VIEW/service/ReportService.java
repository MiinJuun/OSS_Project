package RE.VIEW.service;

import RE.VIEW.entity.Place;
import org.springframework.stereotype.Service;
import java.util.Map;

@Service
public class ReportService {
    public Map<String, Object> comparePlaces(String nameA, String nameB) {
        return null;
    }

    public Map<String, Object> buildParallelView(Place placeA, Place placeB) {
        return null;
    }

    public String rankByBayesianScore(Long placeA, Long placeB) {
        return null;
    }

    public String buildFinalHTMLTemplate(Map<String, Object> data) {
        return null;
    }

    public byte[] exportToPDF(Long placeId) {
        return null;
    }
}