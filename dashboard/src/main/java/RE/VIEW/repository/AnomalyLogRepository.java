package RE.VIEW.repository;
import RE.VIEW.entity.AnomalyLog;
import org.springframework.data.jpa.repository.JpaRepository;
public interface AnomalyLogRepository extends JpaRepository<AnomalyLog, Long> {}