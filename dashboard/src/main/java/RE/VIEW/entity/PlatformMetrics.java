package RE.VIEW.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class PlatformMetrics {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "place_id")
    private Place place;

    private String platform;
    private Integer totalReviewCount;
    private Double bayesianAvgScore;
    private Double recencyWeightScore;
    private LocalDateTime collectAt = LocalDateTime.now();

    public void updateBayesianScore(Double score) {
        this.bayesianAvgScore = score;
        this.collectAt = LocalDateTime.now();
    }
}