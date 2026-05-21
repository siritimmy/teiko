import csv
import sqlite3
import os

DB_PATH = "cell_counts.db"
CSV_PATH = "cell-count.csv"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def drop_tables(conn):
    conn.executescript("""
        DROP TABLE IF EXISTS cell_counts;
        DROP TABLE IF EXISTS samples;
        DROP TABLE IF EXISTS subjects;
    """)


def create_tables(conn):
    conn.executescript("""
        CREATE TABLE subjects (
            subject_id  TEXT PRIMARY KEY,
            project     TEXT NOT NULL,
            condition   TEXT NOT NULL,
            age         INTEGER NOT NULL,
            sex         TEXT NOT NULL,
            treatment   TEXT NOT NULL,
            response    TEXT  -- NULL for healthy/untreated subjects
        );

        CREATE TABLE samples (
            sample_id                   TEXT PRIMARY KEY,
            subject_id                  TEXT NOT NULL,
            sample_type                 TEXT NOT NULL,
            time_from_treatment_start   INTEGER NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
        );

        CREATE TABLE cell_counts (
            sample_id   TEXT PRIMARY KEY,
            b_cell      INTEGER NOT NULL,
            cd8_t_cell  INTEGER NOT NULL,
            cd4_t_cell  INTEGER NOT NULL,
            nk_cell     INTEGER NOT NULL,
            monocyte    INTEGER NOT NULL,
            FOREIGN KEY (sample_id) REFERENCES samples (sample_id)
        );
    """)


def load_csv(conn, csv_path):
    subjects_seen = set()

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            subject_id = row["subject"]

            # Insert subject once — skip duplicates we've already handled
            if subject_id not in subjects_seen:
                conn.execute(
                    """
                    INSERT INTO subjects
                        (subject_id, project, condition, age, sex, treatment, response)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        subject_id,
                        row["project"],
                        row["condition"],
                        int(row["age"]),
                        row["sex"],
                        row["treatment"],
                        row["response"] or None,  # empty string -> NULL
                    ),
                )
                subjects_seen.add(subject_id)

            conn.execute(
                """
                INSERT INTO samples
                    (sample_id, subject_id, sample_type, time_from_treatment_start)
                VALUES (?, ?, ?, ?)
                """,
                (
                    row["sample"],
                    subject_id,
                    row["sample_type"],
                    int(row["time_from_treatment_start"]),
                ),
            )

            conn.execute(
                """
                INSERT INTO cell_counts
                    (sample_id, b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["sample"],
                    int(row["b_cell"]),
                    int(row["cd8_t_cell"]),
                    int(row["cd4_t_cell"]),
                    int(row["nk_cell"]),
                    int(row["monocyte"]),
                ),
            )


def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    conn = get_connection()

    with conn:
        print("Dropping existing tables...")
        drop_tables(conn)

        print("Creating tables...")
        create_tables(conn)

        print(f"Loading data from {CSV_PATH}...")
        load_csv(conn, CSV_PATH)

    # Quick sanity check
    with conn:
        subject_count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        sample_count = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        print(f"Done. Loaded {subject_count} subjects and {sample_count} samples.")

    conn.close()


if __name__ == "__main__":
    main()