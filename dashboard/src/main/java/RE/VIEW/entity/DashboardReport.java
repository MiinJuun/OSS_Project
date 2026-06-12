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
    private String crossKeywords; 
    private Boolean isAbusingSuspected;
    private LocalDateTime generateAt = LocalDateTime.now();

    public void updateDiscrepancyRate() {
    }
}