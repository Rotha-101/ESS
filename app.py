# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
from io import BytesIO

# ============================================================
# 1. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Energy Power Dashboard",
    page_icon="⚡",
    layout="wide",
)

# ============================================================
# 2. LOAD CSS & COVER HEADER
# ============================================================

def inject_global_css(css_path: str = "assets/style.css") -> None:
    """Load CSS from file and inject into the app."""
    path = Path(css_path)
    if not path.exists():
        st.warning(f"CSS file not found: {css_path}")
        return
    css = path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_cover(cover_path: str = "Logo/cover.png") -> None:
    """Show the big cover image as the header."""
    path = Path(cover_path)
    if path.exists():
        st.image(str(path), use_container_width=True)
    else:
        # Fallback simple title if cover is missing
        st.title("Energy Power Dashboard")
        st.write(
            "Input power values in real time, visualize behavior, explore statistics, "
            "and export your data."
        )


inject_global_css()
render_cover()

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ============================================================
# 3. SESSION STATE
# ============================================================

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Date Time", "Power"])

if "history" not in st.session_state:
    st.session_state.history = []

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = True

if "power_input" not in st.session_state:
    st.session_state.power_input = ""

if "last_input_status" not in st.session_state:
    st.session_state.last_input_status = None


# ============================================================
# 4. HELPERS
# ============================================================

POWER_MIN = -150
POWER_MAX = 150


def add_to_history(df: pd.DataFrame, name: str) -> None:
    """Save a snapshot of the current DataFrame to the in-session history."""
    if df.empty:
        return
    item = {
        "name": name,
        "df": df.copy(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    st.session_state.history.insert(0, item)
    st.session_state.history = st.session_state.history[:5]


def compute_power_stats(df: pd.DataFrame):
    """Compute descriptive statistics for the Power column."""
    if "Power" not in df.columns:
        return None
    s = pd.to_numeric(df["Power"], errors="coerce").dropna()
    if s.empty:
        return None
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "std": float(s.std(ddof=1)) if s.count() > 1 else 0.0,
        "min": float(s.min()),
        "max": float(s.max()),
        "sum": float(s.sum()),
        "q25": float(s.quantile(0.25)),
        "q75": float(s.quantile(0.75)),
    }


def prepare_plot_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare DataFrame for plotting (parse datetime & numeric)."""
    df_plot = df.copy()
    if "Date Time" in df_plot.columns:
        try:
            df_plot["Date Time"] = pd.to_datetime(df_plot["Date Time"])
        except Exception:
            pass

    df_plot["Power"] = pd.to_numeric(df_plot["Power"], errors="coerce")
    return df_plot.dropna(subset=["Power"])


def power_status_label(value: float) -> tuple[str, str]:
    """
    Return (emoji, text) based on power level.
    Range is -150 .. 150. Use absolute value for severity.
    """
    if value is None:
        return "⚪", "No data"
    v = abs(value)
    if v > 120:
        return "⚠️", "High power alert"
    elif v > 60:
        return "🟡", "Medium usage"
    else:
        return "🟢", "Normal"


def handle_add_power():
    """Callback: add value when user presses Enter in the input box."""
    text = st.session_state.power_input.strip()
    if not text:
        st.session_state.last_input_status = ("error", "Please input a value.")
        return

    try:
        power_val = float(text)
    except ValueError:
        st.session_state.last_input_status = (
            "error",
            "Please input a valid number.",
        )
        return

    if power_val < POWER_MIN or power_val > POWER_MAX:
        st.session_state.last_input_status = (
            "error",
            f"Power must be between {POWER_MIN} and {POWER_MAX}.",
        )
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = pd.DataFrame({"Date Time": [now], "Power": [power_val]})
    st.session_state.df = pd.concat(
        [st.session_state.df, new_row], ignore_index=True
    )
    st.session_state.last_input_status = (
        "success",
        f"Added: {now} | Power = {power_val}",
    )
    st.session_state.power_input = ""  # clear box


# ============================================================
# 5. TOP METRICS
# ============================================================

df = st.session_state.df
stats = compute_power_stats(df)

latest_val = None
if stats and not df.empty:
    latest_val = float(pd.to_numeric(df["Power"], errors="coerce").dropna().iloc[-1])

status_emoji, status_text = power_status_label(latest_val)

col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total Records</div>
            <div class="metric-value">{len(df)}</div>
            <div class="metric-sub">Rows in current session</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    latest_display = f"{latest_val:.2f}" if latest_val is not None else "—"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Latest Power</div>
            <div class="metric-value">{latest_display}</div>
            <div class="metric-sub">Most recent input value</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    avg = f"{stats['mean']:.2f}" if stats else "—"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Average Power</div>
            <div class="metric-value">{avg}</div>
            <div class="metric-sub">Across all numeric records</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    spread = f"{(stats['max'] - stats['min']):.2f}" if stats else "—"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Range</div>
            <div class="metric-value">{spread}</div>
            <div class="metric-sub">Max − Min of Power</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Status</div>
            <div class="metric-value">{status_emoji}</div>
            <div class="metric-sub">{status_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ============================================================
# 6. TABS
# ============================================================

tab_input, tab_visual, tab_stats, tab_history, tab_export = st.tabs(
    ["📥 Input & Table", "📈 Visualization", "📊 Statistics", "🕒 History", "💾 Export"]
)

# ------------------------------------------------------------
# TAB: INPUT & TABLE
# ------------------------------------------------------------
with tab_input:
    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">📥 Input Power Data</div>
                <div class="section-subtitle">
                    Power values are limited to -150 to 150. Type a number and press Enter.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.text_input(
        "Power value (between -150 and 150)",
        key="power_input",
        placeholder="e.g. 40, -20, 120",
        label_visibility="visible",
        on_change=handle_add_power,
    )

    status = st.session_state.last_input_status
    if status:
        level, message = status
        if level == "success":
            st.success(message)
        else:
            st.error(message)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- TABLE CONTROLS ----------
    st.markdown(
        """
        <div class="section-header">
            <div class="section-title">
                🧾 Data Table
            </div>
        </div>
        <p class="muted">
            You can edit or delete rows directly in the <strong>Editable Data Table</strong>.
            Values outside the range -150 to 150 will be marked as invalid.
        </p>
        """,
        unsafe_allow_html=True,
    )

    c_edit, c_lock, c_clear = st.columns(3)
    with c_edit:
        if st.button("✏️ Edit all", use_container_width=True):
            st.session_state.edit_mode = True
    with c_lock:
        if st.button("🔒 Lock table", use_container_width=True):
            st.session_state.edit_mode = False
    with c_clear:
        if st.button("🧹 Clear data", use_container_width=True):
            st.session_state.df = pd.DataFrame(columns=["Date Time", "Power"])
            st.session_state.last_input_status = (
                "success",
                "All data cleared from table.",
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- READ-ONLY PREVIEW ----------
    st.markdown("**Current data (preview)**")
    st.dataframe(st.session_state.df, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- EDITABLE TABLE ----------
    if st.session_state.edit_mode:
        st.markdown("**Editable Data Table**")
        st.caption(
            "Edit values, add rows, or delete rows directly. "
            "Click on the row index to delete."
        )
        edited_df = st.data_editor(
            st.session_state.df,
            num_rows="dynamic",
            use_container_width=True,
            key="data_editor",
        )

        # Validate power range
        if "Power" in edited_df.columns:
            edited_df["Power"] = pd.to_numeric(
                edited_df["Power"], errors="coerce"
            )
            invalid_mask = ~edited_df["Power"].between(POWER_MIN, POWER_MAX)
            invalid_mask &= edited_df["Power"].notna()
            if invalid_mask.any():
                st.warning(
                    "Some rows have Power outside the allowed range "
                    f"({POWER_MIN} to {POWER_MAX}). "
                    "They will be included in charts/statistics but are marked as invalid."
                )
        st.session_state.df = edited_df
    else:
        st.info("Table is locked (view only). Click **Edit all** to enable editing.")

# ------------------------------------------------------------
# TAB: VISUALIZATION
# ------------------------------------------------------------
with tab_visual:
    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">📈 Power over Time</div>
                <div class="section-subtitle">
                    Blue line shows full trend. Green points = positive values, red points = negative values.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_plot = prepare_plot_df(st.session_state.df).copy()

    if df_plot.empty:
        st.info("No data yet. Add some records in the **Input & Table** tab.")
    else:
        df_plot["Power"] = pd.to_numeric(df_plot["Power"], errors="coerce")
        df_plot = df_plot.dropna(subset=["Date Time", "Power"])

        # Layout: chart left / controls right
        chart_col, control_col = st.columns([3, 1])

        with control_col:
            st.markdown("### 🎛️ Chart Controls")

            chart_type = st.selectbox(
                "Chart type",
                ["Line", "Area", "Scatter", "Bar"],
            )

            sort_time = st.checkbox("Sort by Date Time", value=True)
            highlight_zero = st.checkbox("Highlight 0 line", value=True)

            smoothing_enabled = st.checkbox("Apply smoothing", value=False)
            smoothing_window = st.selectbox("Smoothing window", [3, 5, 7], index=1)

            power_range = st.slider(
                "Filter Power range",
                min_value=POWER_MIN,
                max_value=POWER_MAX,
                value=(POWER_MIN, POWER_MAX),
            )

        # Apply sorting
        if sort_time:
            df_plot = df_plot.sort_values("Date Time")

        # Filter
        df_plot = df_plot[df_plot["Power"].between(power_range[0], power_range[1])]

        with chart_col:
            st.caption(
                "💡 Tip: use filters on the right or edit the table to update the visualization instantly."
            )

        if df_plot.empty:
            st.warning("No rows match the selected range.")
        else:
            # ----- Smoothing -----
            if smoothing_enabled:
                df_plot["Power_plot"] = (
                    df_plot["Power"]
                    .rolling(window=smoothing_window, center=True, min_periods=1)
                    .mean()
                )
            else:
                df_plot["Power_plot"] = df_plot["Power"]

            fig = go.Figure()

            # ==================================================
            # MAIN BLUE LINE (all values)
            # ==================================================
            if chart_type in ("Line", "Area", "Scatter"):
                mode = "markers" if chart_type == "Scatter" else "lines+markers"
                fill_type = "tozeroy" if chart_type == "Area" else None

                fig.add_trace(
                    go.Scatter(
                        x=df_plot["Date Time"],
                        y=df_plot["Power_plot"],
                        mode=mode,
                        name="Power Trend",
                        line=dict(color="#2563EB", width=2.5),
                        marker=dict(color="#2563EB", size=4),
                        fill=fill_type,
                    )
                )

            else:  # Bar chart
                fig.add_trace(
                    go.Bar(
                        x=df_plot["Date Time"],
                        y=df_plot["Power_plot"],
                        name="Power",
                        marker_color="#2563EB",
                    )
                )

            # ==================================================
            # POSITIVE & NEGATIVE POINTS (markers only)
            # ==================================================
            df_pos = df_plot[df_plot["Power"] >= 0]
            df_neg = df_plot[df_plot["Power"] < 0]

            # ---- Positive (green marker only) ----
            if not df_pos.empty:
                fig.add_trace(
                    go.Scatter(
                        x=df_pos["Date Time"],
                        y=df_pos["Power_plot"],
                        mode="markers",
                        name="Positive",
                        marker=dict(color="#22C55E", size=8),
                        showlegend=True,
                    )
                )

            # ---- Negative (red marker only) ----
            if not df_neg.empty:
                fig.add_trace(
                    go.Scatter(
                        x=df_neg["Date Time"],
                        y=df_neg["Power_plot"],
                        mode="markers",
                        name="Negative",
                        marker=dict(color="#EF4444", size=8),
                        showlegend=True,
                    )
                )

            # Optional 0 line
            if highlight_zero:
                fig.add_hline(
                    y=0,
                    line=dict(color="#9CA3AF", width=1, dash="dash"),
                    annotation_text="0",
                    annotation_position="bottom left",
                )

            # ==================================================
            # LAYOUT
            # ==================================================
            fig.update_layout(
                title="Power vs Date Time",
                margin=dict(l=20, r=20, t=50, b=80),
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.25,
                    xanchor="center",
                    x=0.5,
                ),
                xaxis=dict(
                    title="Date Time",
                    showgrid=True,
                    gridcolor="#E5E7EB",
                ),
                yaxis=dict(
                    title="Power",
                    showgrid=True,
                    gridcolor="#E5E7EB",
                    zeroline=False,
                ),
            )

            chart_col.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# TAB: STATISTICS
# ------------------------------------------------------------
with tab_stats:
    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">📊 Detailed Statistics</div>
                <div class="section-subtitle">
                    Summary measures and basic distribution plots for the Power column.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stats = compute_power_stats(st.session_state.df)

    if not stats:
        st.info(
            "Statistics are available only when the **Power** column has numeric data."
        )
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Mean (Average)", f"{stats['mean']:.3f}")
        c2.metric("Median", f"{stats['median']:.3f}")
        c3.metric("Standard Deviation", f"{stats['std']:.3f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Minimum", f"{stats['min']:.3f}")
        c5.metric("Maximum", f"{stats['max']:.3f}")
        c6.metric("Total Sum", f"{stats['sum']:.3f}")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### Distribution details")
        dist_df = pd.DataFrame(
            {
                "Metric": [
                    "Count",
                    "Mean",
                    "Median",
                    "Std Dev",
                    "Min",
                    "25% (Q1)",
                    "75% (Q3)",
                    "Max",
                    "Sum",
                ],
                "Value": [
                    stats["count"],
                    round(stats["mean"], 3),
                    round(stats["median"], 3),
                    round(stats["std"], 3),
                    round(stats["min"], 3),
                    round(stats["q25"], 3),
                    round(stats["q75"], 3),
                    round(stats["max"], 3),
                    round(stats["sum"], 3),
                ],
            }
        )
        st.dataframe(dist_df, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        df_stats_plot = prepare_plot_df(st.session_state.df)

        col_hist, col_box = st.columns(2)

        with col_hist:
            st.markdown("##### Histogram")
            fig_hist = px.histogram(
                df_stats_plot,
                x="Power",
                nbins=20,
                title="Distribution of Power",
            )
            fig_hist.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                plot_bgcolor="white",
                paper_bgcolor="white",
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_box:
            st.markdown("##### Box plot")
            fig_box = px.box(
                df_stats_plot,
                y="Power",
                points="all",
                title="Box Plot of Power",
            )
            fig_box.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                plot_bgcolor="white",
                paper_bgcolor="white",
            )
            st.plotly_chart(fig_box, use_container_width=True)

# ------------------------------------------------------------
# TAB: HISTORY
# ------------------------------------------------------------
with tab_history:
    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">🕒 Last 5 Snapshots</div>
                <div class="section-subtitle">
                    Every time you export, a snapshot is stored here for this session.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.history:
        st.info(
            "When you export data in the **Export** tab, a snapshot will appear here. "
            "Only the last 5 files in this session are kept."
        )
    else:
        for i, item in enumerate(st.session_state.history):
            label = f"{i+1}. {item['name']}  •  {item['timestamp']}"
            with st.expander(label):
                st.dataframe(item["df"], use_container_width=True)
                restore = st.button(
                    f"Restore this snapshot #{i+1}",
                    key=f"restore_{i}",
                )
                if restore:
                    st.session_state.df = item["df"].copy()
                    st.success(
                        "Snapshot restored into current table. "
                        "Go to Input & Table tab to see it."
                    )

# ------------------------------------------------------------
# TAB: EXPORT
# ------------------------------------------------------------
with tab_export:
    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">💾 Export Data</div>
                <div class="section-subtitle">
                    Download the current table as CSV, Excel, or JSON.
                    A snapshot is also stored in the History tab.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.df.empty:
        st.info("Table is empty. Add some data before exporting.")
    else:
        filename_base = st.text_input(
            "Base file name (without extension)",
            value="power_data",
        )

        df_export = st.session_state.df.copy()

        csv_bytes = df_export.to_csv(index=False).encode("utf-8")

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            df_export.to_excel(writer, index=False, sheet_name="PowerData")
        excel_bytes = excel_buffer.getvalue()

        json_str = df_export.to_json(orient="records", date_format="iso")
        json_bytes = json_str.encode("utf-8")

        c_csv, c_xlsx, c_json = st.columns(3)

        downloaded_any = False

        with c_csv:
            if st.download_button(
                label="📄 Download CSV",
                data=csv_bytes,
                file_name=f"{filename_base}.csv",
                mime="text/csv",
                use_container_width=True,
            ):
                downloaded_any = True

        with c_xlsx:
            if st.download_button(
                label="📘 Download Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"{filename_base}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            ):
                downloaded_any = True

        with c_json:
            if st.download_button(
                label="🧾 Download JSON",
                data=json_bytes,
                file_name=f"{filename_base}.json",
                mime="application/json",
                use_container_width=True,
            ):
                downloaded_any = True

        if downloaded_any:
            add_to_history(df_export, f"{filename_base} (export)")
            st.success("Export completed and snapshot saved to History.")
