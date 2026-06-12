package RE.VIEW.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class AnomalyLog {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "place_id")
    private Place place;

    private String anomalyType;
    private Double threshold;
    private Double detectedValue;
    private LocalDateTime detectAt = LocalDateTime.now();

    public void recordDetection(String type, Double value) {
        this.anomalyType = type;
        this.detectedValue = value;
        this.detectAt = LocalDateTime.now();
    }
}
