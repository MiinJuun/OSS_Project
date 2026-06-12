package RE.VIEW.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Getter @Setter
public class DashboardReport {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "place_id")
    private Place place;

    private Double discrepancyRate;
    @Column(columnDefinition = "TEXT")
    private String crossKeywords; // JSON 형태 저장
    private Boolean isAbusingSuspected;
    private LocalDateTime generateAt = LocalDateTime.now();

    public void updateDiscrepancyRate() {
        // 괴리율 계산 로직을 수행하는 메서드
    }
}