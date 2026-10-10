"""
QualityGuard AI - Agentic quality-control agent for M8 x 30 mm socket head cap screws.

Agent loop:  OBSERVE (read CMM data + memory)  ->  REASON (tools: tolerance, Cpk, trend)
             ->  ACT (disposition, corrective action, report, chart)  ->  REMEMBER (save to memory)
"""
import argparse
import csv
import json
import os
import statistics
from datetime import datetime

LEVELS = {"PASS": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}

# ----------------------------------------------------------------------------
# TOOLS (small, single-purpose functions the agent can call)
# ----------------------------------------------------------------------------
def load_specs(path="specs.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_cmm_csv(path, specs):
    """Tool 1: read CMM measurements (one row per part) and validate the columns."""
    data = {key: [] for key in specs["features"]}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [k for k in data if k not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV is missing required column(s): {missing}")
        for row in reader:
            for key in data:
                data[key].append(float(row[key]))
    if not any(data.values()):
        raise ValueError("CSV contains no measurement rows")
    return data


def calculate_stats(values):
    """Tool 2: mean and sample standard deviation."""
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, sd


def calculate_cpk(mean, sd, lsl, usl):
    """Tool 3: process capability index. Returns None when sd == 0."""
    if sd == 0:
        return None
    return min((usl - mean) / (3 * sd), (mean - lsl) / (3 * sd))


def check_tolerance(values, lsl, usl):
    """Tool 4: return the out-of-specification measurements."""
    return [v for v in values if v < lsl or v > usl]


def detect_trend(history, key, current_mean, current_sd):
    """Tool 5 (uses memory): detect drift over the last 3 batches (2 stored + current)."""
    prev = [h["features"][key]["mean"] for h in history[-2:] if key in h["features"]]
    if len(prev) < 2:
        return None
    m = prev + [current_mean]
    shift = m[2] - m[0]
    if m[0] < m[1] < m[2] and shift > current_sd:
        return "UPWARD drift toward USL"
    if m[0] > m[1] > m[2] and -shift > current_sd:
        return "DOWNWARD drift toward LSL"
    return None


def llm_explain(findings):
    """Optional tool: ask Claude for a root-cause explanation. Returns None if unavailable."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-5-5",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": "You are a manufacturing quality engineer. Given these CMM inspection "
                           "findings for M8x30 socket head cap screws, give a short root-cause "
                           "analysis and corrective actions (max 120 words):\n"
                           + json.dumps(findings, indent=2),
            }],
        )
        return msg.content[0].text
    except Exception:
        return None


# ----------------------------------------------------------------------------
# MEMORY
# ----------------------------------------------------------------------------
class Memory:
    def __init__(self, path="memory/history.json"):
        self.path = path
        self.history = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.history = json.load(f)

    def previous(self, batch_id):
        return [h for h in self.history if h["batch_id"] != batch_id]

    def save(self, record):
        self.history = self.previous(record["batch_id"]) + [record]
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)


# ----------------------------------------------------------------------------
# THE AGENT
# ----------------------------------------------------------------------------
class QualityGuardAgent:
    def __init__(self, specs, memory, material="Alloy Steel 40Cr", use_llm=True):
        self.specs = specs
        self.memory = memory
        self.material = material
        self.use_llm = use_llm

    # --- REASON: decide status for one feature --------------------------------
    def reason_about_feature(self, key, values, history):
        spec = self.specs["features"][key]
        lsl, usl = spec["lsl"], spec["usl"]
        mean, sd = calculate_stats(values)
        cpk = calculate_cpk(mean, sd, lsl, usl)
        bad = check_tolerance(values, lsl, usl)
        rate = len(bad) / len(values) * 100
        trend = detect_trend(history, key, mean, sd)

        level, action = "PASS", "Feature conforms to specification. Accept."
        if rate > 5:
            level = "CRITICAL"
            side = "oversize" if mean > spec["nominal"] else "undersize"
            action = (f"{rate:.1f}% of parts out of tolerance ({side}). Quarantine the batch, "
                      "check tooling wear (heading die / thread-rolling dies) and the wire-coil lot.")
        elif rate > 0:
            level = "WARNING"
            action = f"{len(bad)} out-of-spec part(s). 100% sort the batch and inspect tooling."
        elif cpk is not None and cpk < 1.0:
            level = "WARNING"
            action = f"Process not capable (Cpk {cpk:.2f} < 1.00). Recalibrate the machine / re-centre the process."
        elif trend:
            level = "WARNING"
            action = f"{trend} across the last 3 batches. Inspect tool wear before it produces defects."
        elif cpk is not None and cpk < 1.33:
            level = "WATCH"
            action = f"Marginal capability (Cpk {cpk:.2f} < 1.33). Increase sampling frequency."

        return {
            "feature": spec["label"], "key": key, "unit": spec["unit"],
            "nominal": spec["nominal"], "lsl": lsl, "usl": usl,
            "n": len(values), "defects": len(bad), "defect_rate_pct": round(rate, 2),
            "mean": round(mean, 4), "std_dev": round(sd, 4),
            "cpk": round(cpk, 2) if cpk is not None else None,
            "trend": trend, "status": level, "corrective_action": action,
        }

    # --- ACT: batch disposition ------------------------------------------------
    @staticmethod
    def decide_disposition(results):
        worst = max(LEVELS[r["status"]] for r in results)
        if worst == LEVELS["CRITICAL"]:
            return "REJECTED (QUARANTINED)"
        if worst == LEVELS["WARNING"]:
            return "PENDING ENGINEERING REVIEW / 100% SORTING"
        if worst == LEVELS["WATCH"]:
            return "RELEASE WITH MONITORING"
        return "RELEASE TO ASSEMBLY LINE"

    # --- THE LOOP --------------------------------------------------------------
    def run(self, csv_path, batch_id=None):
        batch_id = batch_id or os.path.splitext(os.path.basename(csv_path))[0]
        # 1. OBSERVE
        data = read_cmm_csv(csv_path, self.specs)
        history = self.memory.previous(batch_id)
        # 2. REASON
        results = [self.reason_about_feature(k, v, history) for k, v in data.items()]
        disposition = self.decide_disposition(results)
        report = {
            "batch_id": batch_id, "material": self.material,
            "component": self.specs["component"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "disposition": disposition, "features": results,
            "batches_in_memory": len(history),
        }
        # 3. ACT
        if self.use_llm:
            report["llm_analysis"] = llm_explain(
                {"disposition": disposition, "features": results})
        # 4. REMEMBER
        self.memory.save({
            "batch_id": batch_id, "timestamp": report["timestamp"], "disposition": disposition,
            "features": {r["key"]: {"mean": r["mean"], "cpk": r["cpk"],
                                    "defect_rate_pct": r["defect_rate_pct"]} for r in results},
        })
        report["_raw"] = data
        return report


# ----------------------------------------------------------------------------
# OUTPUT
# ----------------------------------------------------------------------------
def print_report(report):
    line = "=" * 70
    print(line)
    print(" QUALITYGUARD AI - FASTENER INSPECTION AUDIT REPORT")
    print(f" Component : {report['component']}")
    print(f" Batch ID  : {report['batch_id']}   Material: {report['material']}")
    print(f" Timestamp : {report['timestamp']}   (batches in memory: {report['batches_in_memory']})")
    print(line)
    print(f"\n[Agent Disposition]: {report['disposition']}\n")
    for r in report["features"]:
        cpk = r["cpk"] if r["cpk"] is not None else "N/A"
        print(f"* {r['feature']}  [{r['lsl']} - {r['usl']} {r['unit']}]")
        print(f"    Mean {r['mean']} | SD {r['std_dev']} | Cpk {cpk} | "
              f"Defects {r['defects']}/{r['n']} ({r['defect_rate_pct']}%)")
        if r["trend"]:
            print(f"    Trend : {r['trend']}")
        print(f"    Status: {r['status']}")
        print(f"    Action: {r['corrective_action']}\n")
    if report.get("llm_analysis"):
        print("--- LLM root-cause analysis ---")
        print(report["llm_analysis"] + "\n")
    print(line)


def save_outputs(report, specs, out_dir="reports"):
    os.makedirs(out_dir, exist_ok=True)
    raw = report.pop("_raw")
    json_path = os.path.join(out_dir, f"{report['batch_id']}_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    paths = [json_path]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        keys = list(specs["features"])
        fig, axes = plt.subplots(len(keys), 1, figsize=(9, 3 * len(keys)))
        for ax, key in zip(axes, keys):
            s, vals = specs["features"][key], raw[key]
            mean = statistics.mean(vals)
            ax.plot(range(1, len(vals) + 1), vals, "o-", color="#1f6feb", label="Measurements")
            ax.axhline(s["usl"], color="red", ls="--", label="USL")
            ax.axhline(s["lsl"], color="red", ls="--", label="LSL")
            ax.axhline(mean, color="green", ls=":", label="Mean")
            ax.set_title(f"{s['label']} ({s['unit']})", fontsize=10)
            ax.set_xlabel("Part no.")
        axes[0].legend(loc="upper right", fontsize=8, ncol=4)
        fig.suptitle(f"Control chart - {report['batch_id']}", fontweight="bold")
        fig.tight_layout()
        png_path = os.path.join(out_dir, f"{report['batch_id']}_chart.png")
        fig.savefig(png_path, dpi=110)
        plt.close(fig)
        paths.append(png_path)
    except ImportError:
        print("(matplotlib not installed - skipping control chart)")
    return paths


def main():
    p = argparse.ArgumentParser(description="QualityGuard AI screw inspection agent")
    p.add_argument("csv", help="CMM data file, e.g. data/batch_001_SCREW-8830.csv")
    p.add_argument("--specs", default="specs.json")
    p.add_argument("--material", default="Alloy Steel 40Cr")
    p.add_argument("--no-llm", action="store_true", help="skip the optional Claude analysis")
    p.add_argument("--reset-memory", action="store_true", help="forget all previous batches")
    args = p.parse_args()

    specs = load_specs(args.specs)
    memory = Memory()
    if args.reset_memory:
        memory.history = []
    agent = QualityGuardAgent(specs, memory, args.material, use_llm=not args.no_llm)
    report = agent.run(args.csv)
    print_report(report)
    for path in save_outputs(report, specs):
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
