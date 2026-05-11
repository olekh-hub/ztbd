import argparse
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from benchmarks.config import DEFAULT_REPORTS_DIR, DEFAULT_RESULTS_DIR


SIZE_ORDER = ["test", "s", "m", "l"]
VARIANT_ORDER = ["no_idx", "idx"]
SUITE_ORDER = ["CREATE", "READ", "UPDATE", "DELETE"]
DB_ORDER = ["mysql", "postgres", "mongo", "redis"]
DB_COLORS = {
    "mysql": "#00758F",
    "postgres": "#336791",
    "mongo": "#13AA52",
    "redis": "#DC382D",
}
SUITE_COLORS = {
    "CREATE": "#2E7D32",
    "READ": "#1565C0",
    "UPDATE": "#EF6C00",
    "DELETE": "#C62828",
}


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "axes.titlesize": 11,
            "axes.titleweight": "semibold",
            "axes.labelsize": 10,
            "figure.dpi": 110,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
            "font.size": 10,
            "legend.frameon": False,
        }
    )


def scenario_suite(scenario_id: str) -> str:
    prefix = scenario_id[:1].upper()
    return {"C": "CREATE", "R": "READ", "U": "UPDATE", "D": "DELETE"}.get(prefix, "OTHER")


def ordered_scenarios(scenario_ids) -> list[str]:
    def key(sid: str):
        suite = scenario_suite(sid)
        suite_idx = SUITE_ORDER.index(suite) if suite in SUITE_ORDER else 99
        try:
            num = int(sid[1:])
        except (ValueError, IndexError):
            num = 0
        return (suite_idx, num, sid)

    return sorted(set(scenario_ids), key=key)


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input CSV: {path}")
    return pd.read_csv(path)


def ok_results(results: pd.DataFrame) -> pd.DataFrame:
    status: Any = results["status"] if "status" in results else pd.Series(["ok"] * len(results), index=results.index)
    frame = cast(pd.DataFrame, results[status == "ok"].copy())
    frame["duration_ms"] = pd.to_numeric(frame["duration_ms"], errors="coerce")
    frame["rows_affected"] = pd.to_numeric(frame["rows_affected"], errors="coerce")
    frame = cast(pd.DataFrame, frame.dropna(subset=("duration_ms",)))
    frame["suite"] = frame["scenario_id"].map(scenario_suite)
    return frame


def save_figure(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def annotate_no_data(ax, message: str = "No successful timing data") -> None:
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, fontsize=11, color="#777")
    ax.set_xticks([])
    ax.set_yticks([])


def plot_failure_heatmap(summary: pd.DataFrame, out_dir: Path) -> Path:
    pivot = cast(
        pd.DataFrame,
        summary.pivot_table(index="scenario_id", columns="db", values="failure_rate", aggfunc="mean", fill_value=0),
    )
    rows = ordered_scenarios(pivot.index)
    pivot = pivot.reindex(index=rows)
    cols = [d for d in DB_ORDER if d in pivot.columns]
    pivot = pivot[cols] if cols else pivot
    fig, ax = plt.subplots(figsize=(max(5, len(pivot.columns) * 1.4), max(4, len(pivot.index) * 0.32)))
    values = pivot.values.astype(float)
    vmax = max(0.05, float(np.nanmax(values))) if values.size else 1.0
    im = ax.imshow(values, aspect="auto", cmap="Reds", vmin=0, vmax=vmax)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Failure rate")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for (i, j), v in np.ndenumerate(values):
        if v > 0:
            color = "white" if v > vmax * 0.6 else "black"
            ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=8, color=color)
    ax.set_title("Failure Rate by Scenario × Database")
    ax.grid(False)
    path = out_dir / "failure_heatmap.png"
    save_figure(fig, path)
    return path


def speedup_frame(summary: pd.DataFrame) -> pd.DataFrame:
    ok_runs = cast(Any, pd.to_numeric(summary["ok_runs"], errors="coerce")).fillna(0)
    ok = cast(pd.DataFrame, summary[ok_runs > 0].copy())
    ok["mean_ms"] = pd.to_numeric(ok["mean_ms"], errors="coerce")
    pivot = cast(
        pd.DataFrame,
        ok.pivot_table(index=["scenario_id", "db", "size"], columns="variant", values="mean_ms", aggfunc="mean"),
    )
    pivot = cast(pd.DataFrame, pivot.dropna(subset=("no_idx", "idx"), how="any").reset_index())
    pivot["speedup"] = pivot["no_idx"] / pivot["idx"]
    pivot["suite"] = pivot["scenario_id"].map(scenario_suite)
    return pivot


def plot_idx_speedup(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Heatmap: scenario × db, faceted by size, log2 speedup with diverging colormap."""
    frame = speedup_frame(summary)
    if frame.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        annotate_no_data(ax)
        path = out_dir / "idx_speedup.png"
        save_figure(fig, path)
        return path

    sizes = [s for s in SIZE_ORDER if s in frame["size"].unique()]
    scenarios = ordered_scenarios(frame["scenario_id"])
    dbs = [d for d in DB_ORDER if d in frame["db"].unique()]
    log_speed = np.log2(frame["speedup"].clip(lower=1e-9).astype(float))
    bound = max(1.0, float(np.nanpercentile(np.abs(log_speed), 95)))
    norm = mcolors.TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)

    fig, axes = plt.subplots(
        1, len(sizes), figsize=(max(5, 2.8 * len(sizes) + 2), max(5, 0.32 * len(scenarios) + 2)), sharey=True
    )
    if len(sizes) == 1:
        axes = [axes]
    im = None
    for ax, size in zip(axes, sizes):
        sub = frame[frame["size"] == size]
        pivot = cast(
            pd.DataFrame,
            sub.pivot_table(index="scenario_id", columns="db", values="speedup", aggfunc="mean"),
        )
        pivot = pivot.reindex(index=scenarios, columns=dbs)
        values = pivot.values.astype(float)
        log_values = np.log2(np.where(values > 0, values, np.nan))
        im = ax.imshow(log_values, aspect="auto", cmap="RdBu_r", norm=norm)
        ax.set_xticks(range(len(dbs)))
        ax.set_xticklabels(dbs, rotation=45, ha="right")
        ax.set_yticks(range(len(scenarios)))
        ax.set_yticklabels(scenarios)
        ax.set_title(f"size = {size}")
        for (i, j), v in np.ndenumerate(values):
            if not np.isnan(v):
                lv = np.log2(v) if v > 0 else 0
                color = "white" if abs(lv) > bound * 0.55 else "black"
                if v >= 100:
                    label = f"{v:.0f}×"
                elif v >= 10:
                    label = f"{v:.1f}×"
                else:
                    label = f"{v:.2f}×"
                ax.text(j, i, label, ha="center", va="center", fontsize=7, color=color)
        ax.grid(False)

    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
        cbar.set_label("log₂(no_idx / idx)\nred = index helps · blue = index hurts")
    fig.suptitle("Index Speedup by Scenario × DB × Size", y=1.0, fontsize=13)
    path = out_dir / "idx_speedup.png"
    save_figure(fig, path)
    return path


def plot_h1_suite_comparison(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Boxplot of speedups grouped by CRUD suite, log y, with geometric-mean marker."""
    frame = speedup_frame(summary)
    fig, ax = plt.subplots(figsize=(8, 5))
    if frame.empty:
        annotate_no_data(ax)
        path = out_dir / "h1_suite_comparison.png"
        save_figure(fig, path)
        return path
    suites = [s for s in SUITE_ORDER if s in frame["suite"].unique()]
    data: list[np.ndarray] = []
    geo_means: list[float] = []
    counts: list[int] = []
    for suite in suites:
        vals = frame.loc[frame["suite"] == suite, "speedup"].astype(float).dropna()
        vals = vals[vals > 0]
        data.append(vals.values)
        counts.append(len(vals))
        geo_means.append(float(np.exp(np.log(vals).mean())) if len(vals) else float("nan"))
    bp = ax.boxplot(
        data,
        tick_labels=suites,
        showfliers=True,
        widths=0.55,
        patch_artist=True,
        medianprops=dict(color="black", linewidth=1.5),
        flierprops=dict(marker="o", markersize=3, alpha=0.5),
    )
    for patch, suite in zip(bp["boxes"], suites):
        patch.set_facecolor(SUITE_COLORS.get(suite, "#888"))
        patch.set_alpha(0.55)
    for i, (gm, n) in enumerate(zip(geo_means, counts), start=1):
        if not np.isnan(gm):
            ax.scatter(
                [i],
                [gm],
                marker="D",
                s=70,
                color="black",
                zorder=4,
                label="Geometric mean" if i == 1 else None,
            )
            ax.annotate(
                f"  {gm:.2f}×",
                (i, gm),
                xytext=(6, 0),
                textcoords="offset points",
                fontsize=9,
                va="center",
                fontweight="semibold",
            )
    for i, n in enumerate(counts, start=1):
        ax.text(i, -0.08, f"n={n}", ha="center", va="top", transform=ax.get_xaxis_transform(), fontsize=8, color="#555")
    ax.axhline(1.0, color="black", linewidth=1, linestyle="--", alpha=0.7)
    ax.set_yscale("log")
    ax.set_ylabel("Index speedup  =  mean(no_idx) / mean(idx)   [log scale]")
    ax.set_title("H1: Index Impact by CRUD Suite\nvalues > 1× mean indexes are faster; < 1× means indexes hurt")
    ax.legend(loc="upper left")
    path = out_dir / "h1_suite_comparison.png"
    save_figure(fig, path)
    return path


def plot_scaling(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Median scenario duration vs size, faceted by CRUD suite, line per db, log y."""
    frame = summary.copy()
    p50 = pd.to_numeric(frame.get("p50_ms"), errors="coerce") if "p50_ms" in frame.columns else None
    mean = pd.to_numeric(frame["mean_ms"], errors="coerce")
    frame["_metric"] = p50 if p50 is not None else mean
    frame["_metric"] = frame["_metric"].fillna(mean)
    frame = cast(pd.DataFrame, frame[(frame["variant"] == "idx") & frame["size"].isin(SIZE_ORDER)])
    frame = cast(pd.DataFrame, cast(Any, frame).dropna(subset=["_metric"]))
    frame["suite"] = frame["scenario_id"].map(scenario_suite)
    frame = cast(pd.DataFrame, frame[frame["suite"].isin(SUITE_ORDER)])
    if frame.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax)
        path = out_dir / "scaling_by_size.png"
        save_figure(fig, path)
        return path

    suites = [s for s in SUITE_ORDER if s in frame["suite"].unique()]
    fig, axes = plt.subplots(1, len(suites), figsize=(3.6 * len(suites), 4.2), sharey=True)
    if len(suites) == 1:
        axes = [axes]
    sizes_present = [s for s in SIZE_ORDER if s in frame["size"].unique()]
    for ax, suite in zip(axes, suites):
        sub = frame[frame["suite"] == suite]
        agg = sub.groupby(["db", "size"])["_metric"].median().reset_index()
        for db in [d for d in DB_ORDER if d in agg["db"].unique()]:
            db_sub = agg[agg["db"] == db].copy()
            db_sub["_o"] = db_sub["size"].map({s: i for i, s in enumerate(SIZE_ORDER)})
            db_sub = db_sub.sort_values("_o")
            ax.plot(
                db_sub["size"],
                db_sub["_metric"],
                marker="o",
                label=db,
                color=DB_COLORS.get(db),
                linewidth=2,
                markersize=7,
            )
        ax.set_yscale("log")
        ax.set_title(suite, color=SUITE_COLORS.get(suite, "black"))
        ax.set_xlabel("dataset size")
        ax.set_xticks(range(len(sizes_present)))
        ax.set_xticklabels(sizes_present)
    axes[0].set_ylabel("Median duration (ms, log scale)")
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, title="DB", loc="center right", bbox_to_anchor=(1.02, 0.5))
    fig.suptitle("Scaling Across Dataset Sizes (IDX variant, median across scenarios)", y=1.02, fontsize=13)
    path = out_dir / "scaling_by_size.png"
    save_figure(fig, path)
    return path


def plot_duration_distribution(results: pd.DataFrame, out_dir: Path) -> Path:
    """Boxplots of per-run durations by db, faceted by CRUD suite, log y."""
    frame = ok_results(results)
    suites = [s for s in SUITE_ORDER if s in frame["suite"].unique()]
    if frame.empty or not suites:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax)
        path = out_dir / "duration_distribution.png"
        save_figure(fig, path)
        return path
    fig, axes = plt.subplots(1, len(suites), figsize=(3.4 * len(suites), 4.5), sharey=True)
    if len(suites) == 1:
        axes = [axes]
    dbs = [d for d in DB_ORDER if d in frame["db"].unique()]
    for ax, suite in zip(axes, suites):
        sub = frame[frame["suite"] == suite]
        groups: list[np.ndarray] = []
        labels: list[str] = []
        for db in dbs:
            vals = sub.loc[sub["db"] == db, "duration_ms"].astype(float)
            vals = vals[vals > 0]
            if len(vals):
                groups.append(vals.values)
                labels.append(db)
        if not groups:
            annotate_no_data(ax)
            ax.set_title(suite, color=SUITE_COLORS.get(suite, "black"))
            continue
        bp = ax.boxplot(
            groups,
            tick_labels=labels,
            showfliers=True,
            widths=0.6,
            patch_artist=True,
            medianprops=dict(color="black", linewidth=1.5),
            flierprops=dict(marker="o", markersize=3, alpha=0.4),
        )
        for patch, db in zip(bp["boxes"], labels):
            patch.set_facecolor(DB_COLORS.get(db, "#888"))
            patch.set_alpha(0.6)
        ax.set_title(suite, color=SUITE_COLORS.get(suite, "black"))
        ax.set_yscale("log")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    axes[0].set_ylabel("Per-run duration (ms, log scale)")
    fig.suptitle("Duration Distribution by Database (per CRUD suite, all sizes & variants)", y=1.02, fontsize=13)
    path = out_dir / "duration_distribution.png"
    save_figure(fig, path)
    return path


def plot_engine_leaderboard(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Average rank per (suite, db) — lower is faster — with value labels."""
    frame = summary.copy()
    frame["mean_ms"] = pd.to_numeric(frame["mean_ms"], errors="coerce")
    frame = cast(pd.DataFrame, frame.dropna(subset=("mean_ms",)))
    frame["suite"] = frame["scenario_id"].map(scenario_suite)
    frame = cast(pd.DataFrame, frame[frame["suite"].isin(SUITE_ORDER)])
    if frame.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        annotate_no_data(ax)
        path = out_dir / "engine_leaderboard.png"
        save_figure(fig, path)
        return path
    frame["rank"] = frame.groupby(["scenario_id", "size", "variant"])["mean_ms"].rank(method="average")
    leaderboard = cast(pd.DataFrame, frame.groupby(["suite", "db"])["rank"].mean().unstack("db"))
    suites = [s for s in SUITE_ORDER if s in leaderboard.index]
    dbs = [d for d in DB_ORDER if d in leaderboard.columns]
    leaderboard = leaderboard.loc[suites, dbs]

    fig, ax = plt.subplots(figsize=(max(7, 1.2 * len(suites) * max(1, len(dbs))), 5))
    n_dbs = len(dbs)
    width = 0.8 / max(1, n_dbs)
    x = np.arange(len(suites))
    for i, db in enumerate(dbs):
        offsets = x + (i - (n_dbs - 1) / 2) * width
        vals = leaderboard[db].values.astype(float)
        bars = ax.bar(offsets, vals, width=width, color=DB_COLORS.get(db, "#888"), label=db, edgecolor="white")
        for bar, val in zip(bars, vals):
            if not np.isnan(val):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    val + 0.05,
                    f"{val:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
    ax.set_xticks(x)
    ax.set_xticklabels(suites)
    ax.set_ylabel("Average rank (1 = fastest)")
    top = float(np.nanmax(leaderboard.values)) if leaderboard.size else 4.0
    ax.set_ylim(top + 0.6, 0)
    ax.axhline(1, color="#888", linestyle=":", linewidth=1)
    ax.set_title("Engine Leaderboard by CRUD Suite\n(shorter bar from the top = faster on average)")
    ax.legend(title="DB", loc="lower right", ncol=min(4, max(1, n_dbs)))
    path = out_dir / "engine_leaderboard.png"
    save_figure(fig, path)
    return path


def plot_rows_affected(results: pd.DataFrame, out_dir: Path) -> Path:
    """Mean rows affected per scenario, log y, grouped bars by db."""
    frame = ok_results(results)
    frame = cast(pd.DataFrame, frame[frame["suite"].isin(["CREATE", "UPDATE", "DELETE"])])
    frame = cast(pd.DataFrame, cast(Any, frame).dropna(subset=["rows_affected"]))
    if frame.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        annotate_no_data(ax)
        path = out_dir / "rows_affected.png"
        save_figure(fig, path)
        return path
    pivot = cast(pd.DataFrame, frame.groupby(["scenario_id", "db"])["rows_affected"].mean().unstack("db"))
    scenarios = ordered_scenarios(pivot.index)
    pivot = pivot.reindex(index=scenarios)
    dbs = [d for d in DB_ORDER if d in pivot.columns]
    pivot = pivot[dbs] if dbs else pivot

    fig, ax = plt.subplots(figsize=(max(8, 0.45 * len(scenarios) * max(1, len(dbs))), 4.5))
    n_dbs = len(dbs) or 1
    width = 0.8 / n_dbs
    x = np.arange(len(scenarios))
    for i, db in enumerate(dbs):
        offsets = x + (i - (n_dbs - 1) / 2) * width
        vals = pivot[db].values.astype(float)
        plot_vals = np.where(vals > 0, vals, np.nan)
        ax.bar(offsets, plot_vals, width=width, color=DB_COLORS.get(db, "#888"), label=db, edgecolor="white")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    ax.set_ylabel("Mean rows affected (log scale)")
    ax.set_title("Rows Affected by Mutating Scenarios (CREATE / UPDATE / DELETE)")
    if dbs:
        ax.legend(title="DB", loc="upper left", ncol=len(dbs))
    path = out_dir / "rows_affected.png"
    save_figure(fig, path)
    return path


def plot_index_tradeoff(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Log-log scatter of mean(idx) vs mean(no_idx). Above y=x ⇒ index helps."""
    frame = speedup_frame(summary)
    fig, ax = plt.subplots(figsize=(7.5, 7))
    if frame.empty:
        annotate_no_data(ax)
        path = out_dir / "index_tradeoff_scatter.png"
        save_figure(fig, path)
        return path
    db_markers = {"mysql": "o", "postgres": "s", "mongo": "^", "redis": "D"}
    for suite in [s for s in SUITE_ORDER if s in frame["suite"].unique()]:
        for db in [d for d in DB_ORDER if d in frame["db"].unique()]:
            sub = frame[(frame["suite"] == suite) & (frame["db"] == db)]
            if sub.empty:
                continue
            ax.scatter(
                sub["idx"],
                sub["no_idx"],
                color=SUITE_COLORS.get(suite, "#888"),
                marker=db_markers.get(db, "o"),
                s=55,
                alpha=0.75,
                edgecolor="white",
                linewidth=0.6,
                label=f"{suite}·{db}",
            )
    pos = pd.concat([frame["idx"], frame["no_idx"]]).astype(float)
    pos = pos[pos > 0]
    if not pos.empty:
        lo, hi = float(pos.min()) * 0.5, float(pos.max()) * 2
        ax.plot([lo, hi], [lo, hi], color="black", linestyle="--", linewidth=1, alpha=0.6)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Mean duration with IDX (ms, log)")
    ax.set_ylabel("Mean duration without IDX (ms, log)")
    ax.set_title("Index Trade-off: above the diagonal ⇒ index speeds the scenario up")
    suite_handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=SUITE_COLORS[s], markersize=9, label=s)
        for s in SUITE_ORDER
        if s in frame["suite"].unique()
    ]
    db_handles = [
        plt.Line2D([0], [0], marker=db_markers[d], color="#555", markerfacecolor="#ccc", markersize=8, linestyle="", label=d)
        for d in DB_ORDER
        if d in frame["db"].unique()
    ]
    leg1 = ax.legend(handles=suite_handles, title="suite (color)", loc="upper left")
    ax.add_artist(leg1)
    ax.legend(handles=db_handles, title="db (marker)", loc="lower right")
    path = out_dir / "index_tradeoff_scatter.png"
    save_figure(fig, path)
    return path


def plot_run_trace(results: pd.DataFrame, out_dir: Path) -> Path:
    """Median duration by run_no within each (suite, db) — surfaces warm-up effects."""
    frame = ok_results(results)
    frame = cast(pd.DataFrame, frame[frame["suite"].isin(SUITE_ORDER)])
    frame["run_no"] = pd.to_numeric(frame["run_no"], errors="coerce")
    frame = cast(pd.DataFrame, cast(Any, frame).dropna(subset=["run_no"]))
    if frame.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax)
        path = out_dir / "run_to_run_trace.png"
        save_figure(fig, path)
        return path
    suites = [s for s in SUITE_ORDER if s in frame["suite"].unique()]
    fig, axes = plt.subplots(1, len(suites), figsize=(3.4 * len(suites), 4.2), sharey=True)
    if len(suites) == 1:
        axes = [axes]
    for ax, suite in zip(axes, suites):
        sub = frame[frame["suite"] == suite]
        # ratio: per (scenario, db, size, variant) divide by run-1 mean to normalize
        keys = ["scenario_id", "db", "size", "variant"]
        baseline = sub[sub["run_no"] == 1].groupby(keys)["duration_ms"].mean().rename("base")
        merged = sub.merge(baseline, on=keys, how="left")
        merged = merged[merged["base"] > 0]
        merged["norm"] = merged["duration_ms"] / merged["base"]
        for db in [d for d in DB_ORDER if d in merged["db"].unique()]:
            db_sub = merged[merged["db"] == db]
            agg = db_sub.groupby("run_no")["norm"].median().reset_index()
            ax.plot(
                agg["run_no"],
                agg["norm"],
                marker="o",
                linewidth=2,
                markersize=7,
                color=DB_COLORS.get(db),
                label=db,
            )
        ax.axhline(1.0, color="black", linestyle="--", linewidth=1, alpha=0.6)
        ax.set_title(suite, color=SUITE_COLORS.get(suite, "black"))
        ax.set_xlabel("run #")
        ax.set_xticks(sorted(frame["run_no"].dropna().astype(int).unique()))
    axes[0].set_ylabel("Median duration ÷ run-1 duration")
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, title="DB", loc="center right", bbox_to_anchor=(1.02, 0.5))
    fig.suptitle("Warm-up Effects: per-run duration normalized to run 1", y=1.02, fontsize=13)
    path = out_dir / "run_to_run_trace.png"
    save_figure(fig, path)
    return path


def plot_scaling_exponent(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Slope of log10(p50_ms) vs log10(size_step) per (db, suite). Step≈10× rows by convention."""
    frame = summary.copy()
    frame["p50_ms"] = pd.to_numeric(frame.get("p50_ms"), errors="coerce")
    frame = cast(pd.DataFrame, frame[(frame["variant"] == "idx") & frame["size"].isin(["s", "m", "l"])])
    frame = cast(pd.DataFrame, cast(Any, frame).dropna(subset=["p50_ms"]))
    frame["suite"] = frame["scenario_id"].map(scenario_suite)
    frame = cast(pd.DataFrame, frame[frame["suite"].isin(SUITE_ORDER)])
    if frame.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax)
        path = out_dir / "scaling_exponent.png"
        save_figure(fig, path)
        return path
    size_x = {"s": 0.0, "m": 1.0, "l": 2.0}  # 1 unit ≈ 10× rows by data-gen convention
    frame["x"] = frame["size"].map(size_x)
    frame = cast(pd.DataFrame, frame[frame["p50_ms"] > 0])
    frame["logy"] = np.log10(frame["p50_ms"].astype(float))
    rows = []
    for (db, suite), sub in frame.groupby(["db", "suite"]):
        if sub["x"].nunique() < 2:
            continue
        slope, _ = np.polyfit(sub["x"].values.astype(float), sub["logy"].values.astype(float), 1)
        rows.append({"db": db, "suite": suite, "slope": float(slope)})
    if not rows:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax, "Need ≥2 sizes to fit a slope")
        path = out_dir / "scaling_exponent.png"
        save_figure(fig, path)
        return path
    slopes = pd.DataFrame(rows).pivot_table(index="suite", columns="db", values="slope")
    suites = [s for s in SUITE_ORDER if s in slopes.index]
    dbs = [d for d in DB_ORDER if d in slopes.columns]
    slopes = slopes.loc[suites, dbs]
    fig, ax = plt.subplots(figsize=(max(7, 1.4 * len(suites) * max(1, len(dbs))), 5))
    n_dbs = len(dbs) or 1
    width = 0.8 / n_dbs
    x = np.arange(len(suites))
    for i, db in enumerate(dbs):
        offsets = x + (i - (n_dbs - 1) / 2) * width
        vals = slopes[db].values.astype(float)
        bars = ax.bar(offsets, vals, width=width, color=DB_COLORS.get(db, "#888"), label=db, edgecolor="white")
        for bar, val in zip(bars, vals):
            if not np.isnan(val):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    val + (0.04 if val >= 0 else -0.04),
                    f"{10 ** val:.1f}×",
                    ha="center",
                    va="bottom" if val >= 0 else "top",
                    fontsize=8,
                )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axhline(1, color="#888", linestyle=":", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(suites)
    ax.set_ylabel("log₁₀(p50) slope per size-step  ·  label = growth factor per ~10× rows")
    ax.set_title("Scaling Exponent: how p50 grows when the dataset grows ~10×\nslope=1 ⇒ linear, <1 ⇒ sublinear (great), >1 ⇒ super-linear")
    ax.legend(title="DB", loc="upper left", ncol=len(dbs))
    path = out_dir / "scaling_exponent.png"
    save_figure(fig, path)
    return path


def plot_cv_heatmap(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Coefficient of variation (stdev/mean) per scenario × db, averaged across size & variant."""
    frame = summary.copy()
    frame["mean_ms"] = pd.to_numeric(frame["mean_ms"], errors="coerce")
    frame["stdev_ms"] = pd.to_numeric(frame["stdev_ms"], errors="coerce")
    frame = cast(pd.DataFrame, frame[(frame["mean_ms"] > 0) & frame["stdev_ms"].notna()])
    if frame.empty:
        fig, ax = plt.subplots(figsize=(6, 6))
        annotate_no_data(ax)
        path = out_dir / "coefficient_of_variation.png"
        save_figure(fig, path)
        return path
    frame["cv"] = frame["stdev_ms"] / frame["mean_ms"]
    pivot = cast(
        pd.DataFrame,
        frame.pivot_table(index="scenario_id", columns="db", values="cv", aggfunc="mean"),
    )
    rows = ordered_scenarios(pivot.index)
    pivot = pivot.reindex(index=rows)
    cols = [d for d in DB_ORDER if d in pivot.columns]
    pivot = pivot[cols] if cols else pivot
    fig, ax = plt.subplots(figsize=(max(5, len(pivot.columns) * 1.4), max(4, len(pivot.index) * 0.32)))
    values = pivot.values.astype(float)
    vmax = max(0.1, float(np.nanpercentile(values, 95))) if values.size else 1.0
    im = ax.imshow(values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=vmax)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Coefficient of variation (stdev / mean)")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for (i, j), v in np.ndenumerate(values):
        if not np.isnan(v):
            color = "white" if v > vmax * 0.6 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color=color)
    ax.set_title("Run-to-Run Stability (lower = more reproducible)")
    ax.grid(False)
    path = out_dir / "coefficient_of_variation.png"
    save_figure(fig, path)
    return path


def plot_duration_heatmap(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Mean duration heatmap per scenario × db, faceted by size, log color."""
    frame = summary.copy()
    frame["mean_ms"] = pd.to_numeric(frame["mean_ms"], errors="coerce")
    frame = cast(pd.DataFrame, frame[(frame["variant"] == "idx") & (frame["mean_ms"] > 0)])
    frame = cast(pd.DataFrame, cast(Any, frame).dropna(subset=["mean_ms"]))
    if frame.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax)
        path = out_dir / "duration_heatmap.png"
        save_figure(fig, path)
        return path
    sizes = [s for s in SIZE_ORDER if s in frame["size"].unique()]
    scenarios = ordered_scenarios(frame["scenario_id"])
    dbs = [d for d in DB_ORDER if d in frame["db"].unique()]
    log_all = np.log10(frame["mean_ms"].astype(float))
    vmin, vmax = float(np.nanmin(log_all)), float(np.nanmax(log_all))
    fig, axes = plt.subplots(
        1, len(sizes), figsize=(max(5, 2.8 * len(sizes) + 2), max(5, 0.32 * len(scenarios) + 2)), sharey=True
    )
    if len(sizes) == 1:
        axes = [axes]
    im = None
    for ax, size in zip(axes, sizes):
        sub = frame[frame["size"] == size]
        pivot = cast(
            pd.DataFrame,
            sub.pivot_table(index="scenario_id", columns="db", values="mean_ms", aggfunc="mean"),
        )
        pivot = pivot.reindex(index=scenarios, columns=dbs)
        values = pivot.values.astype(float)
        log_values = np.log10(np.where(values > 0, values, np.nan))
        im = ax.imshow(log_values, aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
        ax.set_xticks(range(len(dbs)))
        ax.set_xticklabels(dbs, rotation=45, ha="right")
        ax.set_yticks(range(len(scenarios)))
        ax.set_yticklabels(scenarios)
        ax.set_title(f"size = {size}")
        for (i, j), v in np.ndenumerate(values):
            if not np.isnan(v):
                if v >= 1000:
                    label = f"{v/1000:.1f}s"
                elif v >= 1:
                    label = f"{v:.0f}ms"
                else:
                    label = f"{v:.2f}ms"
                color = "white" if (np.log10(v) - vmin) / max(1e-9, (vmax - vmin)) > 0.55 else "black"
                ax.text(j, i, label, ha="center", va="center", fontsize=6.5, color=color)
        ax.grid(False)
    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
        cbar.set_label("log₁₀(mean duration ms)")
    fig.suptitle("Absolute Duration Heatmap (IDX variant)", y=1.0, fontsize=13)
    path = out_dir / "duration_heatmap.png"
    save_figure(fig, path)
    return path


def plot_engine_winners(summary: pd.DataFrame, out_dir: Path) -> Path:
    """Per (scenario, size) winner db using IDX variant — categorical heatmap."""
    frame = summary.copy()
    frame["mean_ms"] = pd.to_numeric(frame["mean_ms"], errors="coerce")
    frame = cast(pd.DataFrame, frame[(frame["variant"] == "idx") & (frame["mean_ms"] > 0)])
    frame = cast(pd.DataFrame, cast(Any, frame).dropna(subset=["mean_ms"]))
    if frame.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax)
        path = out_dir / "engine_winners.png"
        save_figure(fig, path)
        return path
    idx_min = frame.loc[frame.groupby(["scenario_id", "size"])["mean_ms"].idxmin()]
    pivot = cast(
        pd.DataFrame,
        idx_min.pivot_table(index="scenario_id", columns="size", values="db", aggfunc="first"),
    )
    rows = ordered_scenarios(pivot.index)
    pivot = pivot.reindex(index=rows)
    sizes = [s for s in SIZE_ORDER if s in pivot.columns]
    pivot = pivot[sizes]
    db_index = {db: i for i, db in enumerate(DB_ORDER)}
    matrix = pivot.map(lambda v: db_index.get(v, np.nan)).values.astype(float)
    cmap = mcolors.ListedColormap([DB_COLORS[d] for d in DB_ORDER])
    fig, ax = plt.subplots(figsize=(max(4, 1.2 * len(sizes) + 2), max(4, 0.32 * len(pivot.index) + 1)))
    ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=-0.5, vmax=len(DB_ORDER) - 0.5)
    ax.set_xticks(range(len(sizes)))
    ax.set_xticklabels(sizes)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for (i, j), db in np.ndenumerate(pivot.values):
        if isinstance(db, str):
            ax.text(j, i, db, ha="center", va="center", fontsize=7, color="white")
    handles = [plt.Rectangle((0, 0), 1, 1, color=DB_COLORS[d]) for d in DB_ORDER]
    ax.legend(handles, DB_ORDER, title="winner", loc="center left", bbox_to_anchor=(1.02, 0.5))
    ax.set_title("Fastest Engine per Scenario × Size (IDX variant)")
    ax.grid(False)
    path = out_dir / "engine_winners.png"
    save_figure(fig, path)
    return path


def plot_failure_breakdown(results: pd.DataFrame, out_dir: Path) -> Path:
    """Stacked bar of failure counts by error_type per db (status==failed)."""
    if "status" not in results.columns:
        fig, ax = plt.subplots(figsize=(7, 4))
        annotate_no_data(ax, "No status column")
        path = out_dir / "failure_breakdown.png"
        save_figure(fig, path)
        return path
    failed = cast(pd.DataFrame, results[results["status"] == "failed"].copy())
    if failed.empty:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        annotate_no_data(ax, "No failures recorded — every run succeeded")
        ax.set_title("Failure Breakdown by Database × Error Type")
        path = out_dir / "failure_breakdown.png"
        save_figure(fig, path)
        return path
    failed["error_type"] = failed["error_type"].fillna("Unknown").replace("", "Unknown")
    pivot = cast(
        pd.DataFrame,
        failed.pivot_table(index="db", columns="error_type", values="status", aggfunc="count", fill_value=0),
    )
    dbs = [d for d in DB_ORDER if d in pivot.index]
    pivot = pivot.loc[dbs]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bottoms = np.zeros(len(pivot))
    palette = plt.get_cmap("tab10")
    for i, err in enumerate(pivot.columns):
        vals = pivot[err].values
        ax.bar(pivot.index, vals, bottom=bottoms, label=err, color=palette(i % 10), edgecolor="white")
        for j, v in enumerate(vals):
            if v > 0:
                ax.text(j, bottoms[j] + v / 2, str(int(v)), ha="center", va="center", fontsize=8, color="white")
        bottoms += vals
    ax.set_ylabel("Failed runs")
    ax.set_title("Failure Breakdown by Database × Error Type")
    ax.legend(title="error_type", loc="upper right")
    path = out_dir / "failure_breakdown.png"
    save_figure(fig, path)
    return path


def generate_plots(results_path: Path, summary_path: Path, out_dir: Path) -> list[Path]:
    _setup_style()
    results = read_csv_if_exists(results_path)
    summary = read_csv_if_exists(summary_path)
    paths = [
        plot_failure_heatmap(summary, out_dir),
        plot_idx_speedup(summary, out_dir),
        plot_h1_suite_comparison(summary, out_dir),
        plot_scaling(summary, out_dir),
        plot_duration_distribution(results, out_dir),
        plot_engine_leaderboard(summary, out_dir),
        plot_rows_affected(results, out_dir),
        plot_index_tradeoff(summary, out_dir),
        plot_run_trace(results, out_dir),
        plot_scaling_exponent(summary, out_dir),
        plot_cv_heatmap(summary, out_dir),
        plot_duration_heatmap(summary, out_dir),
        plot_engine_winners(summary, out_dir),
        plot_failure_breakdown(results, out_dir),
    ]
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate benchmark plots from raw and summarized results.")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_DIR / "benchmark_results.csv")
    parser.add_argument("--summary", type=Path, default=DEFAULT_REPORTS_DIR / "benchmark_summary.csv")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_REPORTS_DIR / "figures")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = generate_plots(args.results, args.summary, args.out_dir)
    print(f"Wrote {len(paths)} figures to {args.out_dir}")


if __name__ == "__main__":
    main()
