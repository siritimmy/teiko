import sqlite3
import pandas as pd

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
    df["total_count"] = df[CELL_POPULATIONS].sum(axis=1)

    # Melt from wide to long so each population becomes its own row
    melted = df.melt(
        id_vars=["sample_id", "total_count"],
        value_vars=CELL_POPULATIONS,
        var_name="population",
        value_name="count",
    )

    melted["percentage"] = (melted["count"] / melted["total_count"] * 100).round(4)

    # Rename sample_id to sample to match the required output column name
    melted = melted.rename(columns={"sample_id": "sample"})

    return melted[["sample", "total_count", "population", "count", "percentage"]]


def main():
    conn = get_connection()
    raw_df = load_raw_counts(conn)
    conn.close()

    frequency_table = build_frequency_table(raw_df)

    print(frequency_table.head(10).to_string(index=False))
    print(f"\nTotal rows: {len(frequency_table)}")


if __name__ == "__main__":
    main()