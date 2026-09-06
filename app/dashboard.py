"""Interactive review of the committed reference evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "reference"

st.set_page_config(page_title="Hybrid Energy Feasibility", page_icon="☀️", layout="wide")
st.title("Hybrid Energy Feasibility")
st.caption("Solar · battery · biogas · grid | representative-year capacity planning and dispatch")

if not (RESULTS / "summary.json").exists():
    st.error("Run `hybrid-dispatch reproduce` to generate the reference evidence.")
    st.stop()

summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
financial = summary["financial"]
annual = summary["annual"]
resilience = summary["resilience"]

cards = st.columns(4)
cards[0].metric("Hybrid LCOE", f"AED {financial['lcoe_aed_per_kwh']:.3f}/kWh")
cards[1].metric("Renewable fraction", f"{annual['renewable_fraction']:.1%}")
cards[2].metric("25-year NPV", f"AED {financial['npv_aed']:,.0f}")
cards[3].metric("Outage load served", f"{resilience['outage_load_served_fraction']:.0%}")

left, right = st.columns(2)
with left:
    st.subheader("Technology comparison")
    comparison = pd.read_csv(RESULTS / "scenario_comparison.csv")
    st.bar_chart(comparison, x="scenario", y="lcoe_aed_per_kwh")
with right:
    st.subheader("Representative August dispatch")
    dispatch = pd.read_csv(RESULTS / "representative_dispatch.csv")
    august = dispatch.loc[dispatch["month"] == 8]
    st.line_chart(
        august,
        x="hour",
        y=["load_kw", "pv_generation_kw", "biogas_generation_kw", "grid_import_kw"],
    )

st.subheader("Sensitivity matrix")
st.dataframe(pd.read_csv(RESULTS / "sensitivity.csv"), use_container_width=True, hide_index=True)
st.info("Illustrative feasibility model only. Site design requires measured resource, load and vendor data.")
