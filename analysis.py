import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

DB_PATH = "cell_counts.db"

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_raw_counts(conn):
    """Pull all sample + cell count data joined with subject metadata."""
    query = """
        SELECT
            s.sample_id,
            s.subject_id,
            s.sample_type,
            s.time_from_treatment_start,
            subj.project,
            subj.condition,
            subj.treatment,
            subj.response,
            subj.sex,
            cc.b_cell,
            cc.cd8_t_cell,
            cc.cd4_t_cell,
            cc.nk_cell,
            cc.monocyte
        FROM samples s
        JOIN subjects subj ON s.subject_id = subj.subject_id
        JOIN cell_counts cc ON s.sample_id = cc.sample_id
    """
    return pd.read_sql_query(query, conn)


def build_frequency_table(df):
    """
    For each sample, compute total cell count and the relative frequency
    of each population as a percentage. Returns a long-format summary table.
    """
    df = df.copy()
    df["total_count"] = df[CELL_POPULATIONS].sum(axis=1)

    # Melt from wide to long so each population becomes its own row
    melted = df.melt(
        id_vars=[
            "sample_id", "total_count", "sample_type", "time_from_treatment_start",
            "project", "condition", "treatment", "response", "sex",
        ],
        value_vars=CELL_POPULATIONS,
        var_name="population",
        value_name="count",
    )

    melted["percentage"] = (melted["count"] / melted["total_count"] * 100).round(4)

    # Rename sample_id to sample to match the required output column name
    melted = melted.rename(columns={"sample_id": "sample"})

    return melted


def filter_melanoma_miraclib_pbmc(df):
    """Filter to melanoma patients on miraclib with PBMC samples only."""
    mask = (
        (df["condition"] == "melanoma") &
        (df["treatment"] == "miraclib") &
        (df["sample_type"] == "PBMC")
    )
    return df[mask].copy()


def run_statistical_analysis(df):
    """
    For each cell population, run a Mann-Whitney U test comparing
    percentage frequencies between responders and non-responders.
    Returns a summary DataFrame with U statistic and p-value per population.
    """
    results = []

    for population in CELL_POPULATIONS:
        pop_df = df[df["population"] == population]
        responders = pop_df[pop_df["response"] == "yes"]["percentage"]
        non_responders = pop_df[pop_df["response"] == "no"]["percentage"]

        stat, p_value = mannwhitneyu(responders, non_responders, alternative="two-sided")

        results.append({
            "population": population,
            "responder_median": round(responders.median(), 4),
            "non_responder_median": round(non_responders.median(), 4),
            "u_statistic": round(stat, 4),
            "p_value": round(p_value, 4),
            "significant": p_value < 0.05,
        })

    return pd.DataFrame(results)


def plot_boxplots(df, output_path="boxplot_part3.png"):
    """
    Boxplot of percentage frequencies per cell population,
    comparing responders vs non-responders.
    """
    fig, axes = plt.subplots(1, len(CELL_POPULATIONS), figsize=(18, 6), sharey=False)

    for ax, population in zip(axes, CELL_POPULATIONS):
        pop_df = df[df["population"] == population]

        responders = pop_df[pop_df["response"] == "yes"]["percentage"]
        non_responders = pop_df[pop_df["response"] == "no"]["percentage"]

        ax.boxplot(
            [responders, non_responders],
            labels=["Responders", "Non-responders"],
            patch_artist=True,
            boxprops=dict(facecolor="steelblue", alpha=0.7),
        )
        ax.set_title(population, fontsize=11)
        ax.set_ylabel("Relative frequency (%)" if population == CELL_POPULATIONS[0] else "")
        ax.tick_params(axis="x", labelsize=9)

    fig.suptitle(
        "Cell population frequencies: Responders vs Non-responders\n"
        "(Melanoma, miraclib, PBMC only)",
        fontsize=13,
        y=1.02,
    )
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"Boxplot saved to {output_path}")


def run_part4_queries(conn):
    """
    Part 4: Query the DB directly for the melanoma PBMC baseline miraclib subset.
    Reports sample counts by project, responder/non-responder counts,
    sex breakdown, and average B cell count for male responders at baseline.
    """
    base_query = """
        SELECT
            subj.subject_id,
            subj.project,
            subj.sex,
            subj.response,
            cc.b_cell
        FROM samples s
        JOIN subjects subj ON s.subject_id = subj.subject_id
        JOIN cell_counts cc  ON s.sample_id = cc.sample_id
        WHERE subj.condition                = 'melanoma'
          AND s.sample_type                 = 'PBMC'
          AND s.time_from_treatment_start   = 0
          AND subj.treatment                = 'miraclib'
    """

    base_df = pd.read_sql_query(base_query, conn)

    print("=== Part 4: Melanoma PBMC Baseline Miraclib Subset ===\n")

    # Samples per project
    print("-- Samples per project --")
    print(base_df.groupby("project").size().reset_index(name="sample_count").to_string(index=False))

    # Responders vs non-responders (unique subjects)
    print("\n-- Subjects by response --")
    print(
        base_df.groupby("response")["subject_id"]
        .nunique()
        .reset_index(name="subject_count")
        .to_string(index=False)
    )

    # Males vs females (unique subjects)
    print("\n-- Subjects by sex --")
    print(
        base_df.groupby("sex")["subject_id"]
        .nunique()
        .reset_index(name="subject_count")
        .to_string(index=False)
    )

    # Average B cell count for melanoma male responders at time=0
    avg_b_cell = (
        base_df[(base_df["sex"] == "M") & (base_df["response"] == "yes")]["b_cell"].mean()
    )
    print(f"\n-- Average B cell count (melanoma, male, responders, time=0) --")
    print(f"{avg_b_cell:.2f}")


def main():
    conn = get_connection()
    raw_df = load_raw_counts(conn)

    # Part 2 — frequency table
    frequency_table = build_frequency_table(raw_df)
    summary = frequency_table[["sample", "total_count", "population", "count", "percentage"]]
    print("=== Part 2: Frequency Table (first 10 rows) ===")
    print(summary.head(10).to_string(index=False))
    print(f"Total rows: {len(summary)}\n")

    # Part 3 — filter, stats, plot
    filtered_df = filter_melanoma_miraclib_pbmc(frequency_table)

    print("=== Part 3: Statistical Analysis ===")
    print(f"Samples in analysis: {filtered_df['sample'].nunique()}")
    print(f"Responders: {filtered_df[filtered_df['response'] == 'yes']['sample'].nunique()}")
    print(f"Non-responders: {filtered_df[filtered_df['response'] == 'no']['sample'].nunique()}\n")

    stats_df = run_statistical_analysis(filtered_df)
    print(stats_df.to_string(index=False))

    plot_boxplots(filtered_df)

    # Part 4 — subset analysis via SQL
    print()
    run_part4_queries(conn)

    conn.close()


if __name__ == "__main__":
    main()