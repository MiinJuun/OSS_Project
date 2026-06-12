package RE.VIEW.controller;

import RE.VIEW.service.ReviewService;
import RE.VIEW.service.AnalysisService;
import RE.VIEW.service.ReportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api") // 공통 경로를 위로 빼서 코드를 더 깔끔하게!
@CrossOrigin(origins = "*") // 프론트엔드 통신 허용 (네가 짠 핵심 세팅 유지!)
public class MainController {

    @Autowired
    private ReviewService reviewService;

    // 설계도에 맞추기 위해 새로 추가된 서비스들
    @Autowired
    private AnalysisService analysisService;

    @Autowired
    private ReportService reportService;

    // ▼▼▼ 프론트엔드가 호출할 바로 그 주소! (네가 짠 통신 로직 완벽 유지) ▼▼▼
    @GetMapping("/search")
    public Map<String, Object> search(@RequestParam("place") String place) {
        // 통신병(ReviewService)에게 명령 전달 및 결과 반환
        return reviewService.getReviewData(place);
    }

    // --- 아래부터는 다이어그램 설계도와 100% 맞추기 위해 추가된 뼈대 메서드들 ---

    @GetMapping("/analysis")
    public Map<String, Object> getAnalysis(@RequestParam("placeId") Long placeId) {
        // 심층 어뷰징 탐지 및 지표 보정 요청 (UC-04)
        return null;
    }

    @GetMapping("/compare")
    public Map<String, Object> comparePlaces(@RequestParam("a") String a, @RequestParam("b") String b) {
        // 타겟 장소 비교 분석 요청 (UC-09)
        return null;
    }
}