import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, base64, json
from pathlib import Path
from datetime import datetime

DB = Path(__file__).parent.parent / "database"

def generate_comparison_render(parsed: dict, parts_db: dict) -> str:
    """Returns base64 PNG of Before/After cross-section comparison."""
    changes = parsed.get("changes", [])
    if not changes: return None

    pid = changes[0].get("part_id", "PART-001")
    part = parts_db.get(pid, {})
    orig = part.get("dimensions", {}).copy()
    updated = orig.copy()
    for c in changes:
        if c.get("part_id") == pid and c.get("parameter") and c.get("new_value") is not None:
            updated[c["parameter"]] = c["new_value"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 7), facecolor="#0D1117")
    fig.suptitle(f"CAD MODIFICATION: {part.get('name', pid)} ({pid})",
                 color="white", fontsize=14, fontweight="bold", fontfamily="monospace", y=0.98)

    for ax, dims, label, color in zip(axes,
            [orig, updated], ["ORIGINAL (Before)", "MODIFIED (After)"], ["#3a86ff", "#06d6a0"]):
        ax.set_facecolor("#161b22")
        ax.set_aspect("equal")
        ax.set_xlim(-220, 220); ax.set_ylim(-220, 220)

        od = dims.get("outer_diameter_mm", dims.get("diameter_mm", 100))
        id_ = dims.get("inner_diameter_mm", od * 0.84)
        wall = dims.get("wall_thickness_mm", (od - id_) / 2)
        scale = 190 / max(od, 1)
        ro, ri = (od / 2) * scale, (id_ / 2) * scale

        ax.add_patch(plt.Circle((0, 0), ro, fill=True, facecolor=color, alpha=0.2, edgecolor=color, linewidth=2.5))
        ax.add_patch(plt.Circle((0, 0), ri, fill=True, facecolor="#0D1117", alpha=1.0, edgecolor="#e6edf3", linewidth=1.5, linestyle="--"))

        ax.annotate("", xy=(ro, 25), xytext=(ri, 25),
                    arrowprops=dict(arrowstyle="<->", color="#ffd60a", lw=2))
        ax.text((ro + ri) / 2, 38, f"t = {wall:.1f}mm", color="#ffd60a", ha="center",
                fontsize=11, fontweight="bold", fontfamily="monospace")
        ax.annotate("", xy=(-ro, -35), xytext=(ro, -35),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.5))
        ax.text(0, -52, f"OD = {od:.1f}mm", color=color, ha="center", fontsize=10, fontfamily="monospace")
        ax.annotate("", xy=(-ri, -80), xytext=(ri, -80),
                    arrowprops=dict(arrowstyle="<->", color="#8b949e", lw=1.5))
        ax.text(0, -97, f"ID = {id_:.1f}mm", color="#8b949e", ha="center", fontsize=10, fontfamily="monospace")

        ax.set_title(label, color=color, fontsize=12, fontfamily="monospace", fontweight="bold", pad=12)
        ax.tick_params(colors="#8b949e")
        for spine in ax.spines.values(): spine.set_edgecolor("#30363d")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0D1117")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def run_cad_analysis(parsed: dict, parts_db: dict) -> dict:
    """Phase 2: validate changes and generate comparison render."""
    changes = parsed.get("changes", [])
    results = []
    for c in changes:
        pid = c.get("part_id")
        part = parts_db.get(pid, {})
        new_val = c.get("new_value")
        param = c.get("parameter", "")
        checks = []

        if "wall_thickness" in param and new_val and part.get("category") == "pressure_retaining":
            od = part["dimensions"].get("outer_diameter_mm", 150)
            dp = part.get("design_pressure_bar", 150)
            S = 138
            pmax = (2 * S * (new_val / 1000)) / (od / 1000) * 10
            sf = pmax / dp
            checks.append({"check": "Barlow Pressure Analysis",
                           "status": "PASS" if sf >= 2.5 else "FAIL",
                           "detail": f"Pmax = {pmax:.0f} bar, Safety Factor = {sf:.2f} ({'≥' if sf >= 2.5 else '<'} 2.5)"})
            checks.append({"check": "Minimum Wall Thickness",
                           "status": "PASS" if new_val >= 6.0 else "FAIL",
                           "detail": f"{new_val}mm {'≥' if new_val >= 6 else '<'} 6mm minimum"})
        results.append({"part_id": pid, "part_name": part.get("name", pid),
                        "changes_applied": {c["parameter"]: c["new_value"]},
                        "original_dimensions": part.get("dimensions", {}),
                        "updated_dimensions": {**part.get("dimensions", {}), c.get("parameter", ""): c.get("new_value")},
                        "validation": {"overall": "PASS" if all(ch["status"] == "PASS" for ch in checks) else "FAIL",
                                       "checks": checks}})

    render_b64 = generate_comparison_render(parsed, parts_db)
    return {"modified_parts": results, "render_base64": f"data:image/png;base64,{render_b64}" if render_b64 else None}
