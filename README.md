# teiko

Clinical trial dashboard and analysis pipeline for understanding how a drug candidate affects immune cell populations.

---

## Getting Started

> _Instructions will be added once the pipeline and dashboard are finalized._

<!-- TODO: Fill in setup and run instructions for GitHub Codespaces -->

```bash
make setup      # Install dependencies
make pipeline   # Run full data pipeline (DB init, load, analysis, plots)
make dashboard  # Start the interactive dashboard
```

---

## Database Schema

The data is modelled as three normalized tables in SQLite:

### `subjects`
One row per unique patient. Stores all attributes that are intrinsic to the subject and do not change across samples.

| Column | Type | Notes |
|---|---|---|
| `subject_id` | TEXT | Primary key (e.g. `sbj000`) |
| `project` | TEXT | Project the subject belongs to |
| `condition` | TEXT | Disease indication (e.g. `melanoma`) |
| `age` | INTEGER | Subject age |
| `sex` | TEXT | Subject sex (`M` / `F`) |
| `treatment` | TEXT | Treatment received (e.g. `miraclib`) |
| `response` | TEXT | Treatment response (`yes` / `no`) |

### `samples`
One row per biological sample. Links back to the subject and captures the collection context.

| Column | Type | Notes |
|---|---|---|
| `sample_id` | TEXT | Primary key (e.g. `sample00000`) |
| `subject_id` | TEXT | Foreign key → `subjects.subject_id` |
| `sample_type` | TEXT | Sample type (e.g. `PBMC`) |
| `time_from_treatment_start` | INTEGER | Days since treatment started |

### `cell_counts`
One row per sample. Stores the raw cell count for each of the five immune populations.

| Column | Type | Notes |
|---|---|---|
| `sample_id` | TEXT | Primary key + Foreign key → `samples.sample_id` |
| `b_cell` | INTEGER | B cell count |
| `cd8_t_cell` | INTEGER | CD8+ T cell count |
| `cd4_t_cell` | INTEGER | CD4+ T cell count |
| `nk_cell` | INTEGER | NK cell count |
| `monocyte` | INTEGER | Monocyte count |

### Rationale
 
**Why normalize into three tables?**
Subject-level attributes (`condition`, `age`, `sex`, `treatment`, `response`) are identical across every sample from the same subject. Storing them once in `subjects` eliminates redundancy, reduces storage, and ensures that updating a subject's metadata only requires touching one row.
 
**How does this scale?**
- *Hundreds of projects:* `project` can be promoted to its own table with a foreign key on `subjects` if projects gain their own metadata, with no changes needed elsewhere.
- *Thousands of samples:* Indexing `samples.subject_id` and `cell_counts.sample_id` keeps joins fast. The schema is identical if migrating from SQLite to PostgreSQL.
- *New cell types:* `cell_counts` can be migrated to long format — `(sample_id, cell_type, count)` — to handle a growing or variable panel. A view preserves the wide-format interface for existing queries.
- *New analytics:* The normalized structure supports arbitrary joins across subject, sample, and count dimensions without denormalization.

---

## Code Structure

> _Will be filled in once all scripts are written._

<!-- TODO: Describe each file and the reasoning behind the structure -->

---

## Dashboard

> _Link will be added once the dashboard is deployed._

<!-- TODO: Add dashboard URL -->