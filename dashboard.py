import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import mannwhitneyu

DB_PATH = "cell_counts.db"

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_raw_counts():
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            s.sample_id,
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
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data
def build_frequency_table(df):
    df = df.copy()
    df["total_count"] = df[CELL_POPULATIONS].sum(axis=1)
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
    return melted.rename(columns={"sample_id": "sample"})


# ── Pages ─────────────────────────────────────────────────────────────────────

def page_part2(freq_table):
    st.header("Part 2 — Cell Population Frequencies")
    st.markdown("Relative frequency of each immune cell population per sample.")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        conditions = ["All"] + sorted(freq_table["condition"].dropna().unique().tolist())
        condition = st.selectbox("Condition", conditions)
    with col2:
        populations = ["All"] + CELL_POPULATIONS
        population = st.selectbox("Population", populations)
    with col3:
        treatments = ["All"] + sorted(freq_table["treatment"].dropna().unique().tolist())
        treatment = st.selectbox("Treatment", treatments)

    filtered = freq_table.copy()
    if condition != "All":
        filtered = filtered[filtered["condition"] == condition]
    if population != "All":
        filtered = filtered[filtered["population"] == population]
    if treatment != "All":
        filtered = filtered[filtered["treatment"] == treatment]

    display = filtered[["sample", "total_count", "population", "count", "percentage"]]
    st.markdown(f"**{len(display):,} rows**")
    st.dataframe(display, use_container_width=True, height=500)


def page_part3(freq_table):
    st.header("Part 3 — Responders vs Non-responders")
    st.markdown(
        "Melanoma patients on miraclib (PBMC only). "
        "Comparing cell population frequencies between responders and non-responders."
    )

    filtered = freq_table[
        (freq_table["condition"] == "melanoma") &
        (freq_table["treatment"] == "miraclib") &
        (freq_table["sample_type"] == "PBMC")
    ].copy()

    # Boxplots
    fig = go.Figure()
    colors = {"yes": "steelblue", "no": "tomato"}
    labels = {"yes": "Responders", "no": "Non-responders"}

    for response_val in ["yes", "no"]:
        for population in CELL_POPULATIONS:
            values = filtered[
                (filtered["population"] == population) &
                (filtered["response"] == response_val)
            ]["percentage"]

            fig.add_trace(go.Box(
                y=values,
                name=labels[response_val],
                x0=population,
                marker_color=colors[response_val],
                boxmean=False,
                legendgroup=labels[response_val],
                showlegend=population == CELL_POPULATIONS[0],
            ))

    fig.update_layout(
        boxmode="group",
        xaxis_title="Cell Population",
        yaxis_title="Relative Frequency (%)",
        title="Cell population frequencies by response",
        legend_title="Response",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Stats table
    st.subheader("Mann-Whitney U Test Results")
    results = []
    for population in CELL_POPULATIONS:
        pop_df = filtered[filtered["population"] == population]
        responders = pop_df[pop_df["response"] == "yes"]["percentage"]
        non_responders = pop_df[pop_df["response"] == "no"]["percentage"]
        stat, p_value = mannwhitneyu(responders, non_responders, alternative="two-sided")
        results.append({
            "Population": population,
            "Responder Median (%)": round(responders.median(), 4),
            "Non-responder Median (%)": round(non_responders.median(), 4),
            "U Statistic": round(stat, 4),
            "P-value": round(p_value, 4),
            "Significant (p<0.05)": "✅" if p_value < 0.05 else "❌",
        })

    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)


def page_part4():
    st.header("Part 4 — Baseline Subset Analysis")
    st.markdown(
        "Melanoma patients on miraclib, PBMC samples at baseline "
        "(`time_from_treatment_start = 0`)."
    )

    conn = sqlite3.connect(DB_PATH)
    base_df = pd.read_sql_query("""
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
    """, conn)
    conn.close()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Samples by project")
        st.dataframe(
            base_df.groupby("project").size().reset_index(name="Sample count"),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.subheader("Subjects by response")
        st.dataframe(
            base_df.groupby("response")["subject_id"].nunique().reset_index(name="Subject count"),
            use_container_width=True,
            hide_index=True,
        )

    with col3:
        st.subheader("Subjects by sex")
        st.dataframe(
            base_df.groupby("sex")["subject_id"].nunique().reset_index(name="Subject count"),
            use_container_width=True,
            hide_index=True,
        )

    avg_b_cell = (
        base_df[(base_df["sex"] == "M") & (base_df["response"] == "yes")]["b_cell"].mean()
    )
    st.divider()
    st.metric(
        label="Avg B cell count — melanoma male responders at baseline",
        value=f"{avg_b_cell:.2f}",
    )


# ── App entry point ───────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Immune Cell Analysis", layout="wide")
    st.title("Immune Cell Population Analysis")
    st.markdown("Clinical trial dashboard — Loblaw Bio")

    raw_df = load_raw_counts()
    freq_table = build_frequency_table(raw_df)

    page = st.sidebar.radio(
        "Navigation",
        ["Part 2 — Frequency Table", "Part 3 — Statistical Analysis", "Part 4 — Subset Analysis"],
    )

    if page == "Part 2 — Frequency Table":
        page_part2(freq_table)
    elif page == "Part 3 — Statistical Analysis":
        page_part3(freq_table)
    elif page == "Part 4 — Subset Analysis":
        page_part4()


if __name__ == "__main__":
    main()