import statistics
from datetime import datetime


class QualityGuardScrewAgent:
    def __init__(self, batch_id: str, material: str):
        self.batch_id = batch_id
        self.material = material
        self.inspection_logs = []

    def inspect_feature(self, feature_name: str, nominal: float, lsl: float,
                        usl: float, unit: str, measurements: list):
        """Agentic inspection tool for precision fastener quality control."""
        n = len(measurements)
        mean_val = statistics.mean(measurements)
        std_dev = statistics.stdev(measurements) if n > 1 else 0.0

        # Check against Lower (LSL) and Upper (USL) Specification Limits
        out_of_bounds = [x for x in measurements if x < lsl or x > usl]
        defect_count = len(out_of_bounds)
        defect_rate = (defect_count / n) * 100

        # Process capability (Cpk)
        if std_dev > 0:
            cpu = (usl - mean_val) / (3 * std_dev)
            cpl = (mean_val - lsl) / (3 * std_dev)
            cpk = min(cpu, cpl)
        else:
            cpk = 999.0

        # Autonomous agent decision logic
        status = "PASS"
        action = "Feature conforms to ISO 4762 standards. Accept batch sample."

        if 0 < defect_rate <= 5:
            status = "WARNING - REWORK / SORTING REQUIRED"
            action = (f"Detected {defect_count} out-of-spec part(s). Check cold-heading "
                      "die wear or thread rolling machine pressure.")
        elif defect_rate > 5:
            status = "CRITICAL - BATCH REJECTION"
            action = (f"High defect rate ({defect_rate:.1f}%). Quarantine entire batch "
                      "immediately. Inspect raw wire coil supplier lot.")
        elif cpk < 1.0:
            status = "WARNING - HIGH PROCESS VARIATION"
            action = (f"Cpk index is low ({cpk:.2f}). Machine thermal drift suspected; "
                      "recommend tool calibration.")

        log = {
            "feature": feature_name,
            "nominal": nominal,
            "units": unit,
            "inspected_count": n,
            "defects": defect_count,
            "defect_rate_pct": round(defect_rate, 2),
            "mean": round(mean_val, 4),
            "std_dev": round(std_dev, 4),
            "cpk": round(cpk, 2) if cpk != 999.0 else "N/A",
            "status": status,
            "corrective_action": action,
        }
        self.inspection_logs.append(log)
        return log

    def generate_audit_report(self):
        print("=" * 65)
        print(" QUALITYGUARD AI: FASTENER INSPECTION AUDIT REPORT")
        print(" Component: M8 x 30mm Socket Head Cap Screw (Grade 12.9)")
        print(f" Batch ID: {self.batch_id} | Material: {self.material}")
        print(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 65)

        criticals = sum(1 for log in self.inspection_logs if "CRITICAL" in log["status"])
        warnings = sum(1 for log in self.inspection_logs if "WARNING" in log["status"])

        disposition = "RELEASE TO ASSEMBLY LINE"
        if criticals > 0:
            disposition = "REJECTED (QUARANTINED)"
        elif warnings > 0:
            disposition = "PENDING ENGINEERING REVIEW / 100% SORTING"

        print(f"\n[AI Agent Disposition]: {disposition}\n")
        print("--- Inspection Metrics Summary ---")

        for log in self.inspection_logs:
            print(f"\n* Parameter: {log['feature']}")
            print(f"  - Nominal Spec: {log['nominal']} {log['units']}")
            print(f"  - Actual Mean: {log['mean']} {log['units']} (Std Dev: {log['std_dev']})")
            print(f"  - Defect Rate: {log['defect_rate_pct']}% ({log['defects']}/{log['inspected_count']} parts)")
            print(f"  - Process Capability (Cpk): {log['cpk']}")
            print(f"  - Status: {log['status']}")
            print(f"  - Agent Recommendation: {log['corrective_action']}")

        print("\n" + "=" * 65)


if __name__ == "__main__":
    agent = QualityGuardScrewAgent(batch_id="SCREW-8832-OCT2026", material="Alloy Steel 40Cr")

    # 1. Thread Pitch Diameter (Nominal 7.188 mm, tolerance 7.120 to 7.250 mm)
    pitch_data = [7.190, 7.185, 7.210, 7.195, 7.182, 7.200, 7.191, 7.188, 7.192, 7.189]
    agent.inspect_feature("Thread Pitch Diameter", 7.188, 7.120, 7.250, "mm", pitch_data)

    # 2. Shank Length (Nominal 30.00 mm, tolerance 29.75 to 30.25 mm)
    length_data = [30.02, 29.98, 30.05, 30.12, 29.91, 30.03, 30.01, 29.99, 30.04, 30.02]
    agent.inspect_feature("Shank Length", 30.00, 29.75, 30.25, "mm", length_data)

    # 3. Head Diameter (Nominal 13.00 mm, tolerance 12.70 to 13.30 mm) - simulated die wear
    head_data = [13.25, 13.28, 13.31, 13.34, 13.29, 13.32, 13.30, 13.33, 13.35, 13.31]
    agent.inspect_feature("Socket Head Diameter", 13.00, 12.70, 13.30, "mm", head_data)

    agent.generate_audit_report()
