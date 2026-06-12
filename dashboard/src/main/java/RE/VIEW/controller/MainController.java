package RE.VIEW.controller;

import RE.VIEW.service.ReviewService;
import RE.VIEW.service.AnalysisService;
import RE.VIEW.service.ReportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api") 
@CrossOrigin(origins = "*") 
public class MainController {

    @Autowired
    private ReviewService reviewService;

    @Autowired
    private AnalysisService analysisService;

    @Autowired
    private ReportService reportService;

    @GetMapping("/search")
    public Map<String, Object> search(@RequestParam("place") String place) {
        return reviewService.getReviewData(place);
    }


    @GetMapping("/analysis")
    public Map<String, Object> getAnalysis(@RequestParam("placeId") Long placeId) {
        return null;
    }

    @GetMapping("/compare")
    public Map<String, Object> comparePlaces(@RequestParam("a") String a, @RequestParam("b") String b) {
        return null;
    }
}