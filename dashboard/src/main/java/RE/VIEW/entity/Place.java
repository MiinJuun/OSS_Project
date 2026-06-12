package RE.VIEW.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;
import java.util.List;
import java.util.ArrayList;

@Entity
@Getter @Setter
public class Place {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String placeName;
    private String naverPlaceUrl;
    private String kakaoPlaceUrl;
    private LocalDateTime createdAt = LocalDateTime.now();

    public List<String> getActivePlatforms() {
        List<String> platforms = new ArrayList<>();
        if (naverPlaceUrl != null && !naverPlaceUrl.isEmpty()) platforms.add("NAVER");
        if (kakaoPlaceUrl != null && !kakaoPlaceUrl.isEmpty()) platforms.add("KAKAO");
        return platforms;
    }
}