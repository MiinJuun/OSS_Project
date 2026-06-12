package RE.VIEW.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class Review {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "place_id")
    private Place place;

    private String platform;
    @Column(columnDefinition = "TEXT")
    private String contentText;
    private Double starRating;
    private String writtenDate;
    private LocalDateTime collectedAt = LocalDateTime.now();

    public Boolean isPositive() {
        // 감성 분석 모델의 점수를 기반으로 긍정 여부 판단 로직 (임시)
        return starRating != null && starRating >= 3.5;
    }
}