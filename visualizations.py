import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── LOAD & FILTER ─────────────────────────────────────────────────────────────
df = pd.read_csv("opioid_incidents_clean.csv")
df = df[df["YEAR"] <= 2025]   # drop partial 2026 data
df["OCCURRED_ON_DATE"] = pd.to_datetime(df["OCCURRED_ON_DATE"])

# shared color palette (navy → red, consistent across all figs)
NAVY   = "#1a3a5c"
RED    = "#c0392b"
COLORS = ["#1a3a5c","#2e6da4","#5b9bd5","#e07b54","#c0392b","#8e1a1a"]

# ── FIG 1: MONTHLY TREND LINE (static, matplotlib) ───────────────────────────
monthly = (df.groupby("MONTH_YEAR")
             .size()
             .reset_index(name="count"))
monthly["MONTH_YEAR"] = pd.to_datetime(monthly["MONTH_YEAR"])
monthly = monthly.sort_values("MONTH_YEAR")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(monthly["MONTH_YEAR"], monthly["count"],
        color=NAVY, linewidth=2, marker="o", markersize=3)
ax.fill_between(monthly["MONTH_YEAR"], monthly["count"],
                alpha=0.15, color=NAVY)

# shade covid period
ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-06-01"),
           alpha=0.08, color=RED, label="COVID-19 period")

ax.set_title("Monthly Narcotic Incident Trend in Boston (2020–2025)",
             fontsize=14, fontweight="bold", color=NAVY)
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Number of Incidents", fontsize=11)
ax.yaxis.set_major_locator(ticker.MultipleLocator(25))
ax.legend()
ax.spines[["top","right"]].set_visible(False)
plt.tight_layout()
plt.savefig("fig1_monthly_trend.png", dpi=150)
plt.show()
print("saved fig1_monthly_trend.png")

# ── FIG 2: NEIGHBORHOOD BAR CHART (static, matplotlib) ───────────────────────
nbhd = (df[df["NEIGHBORHOOD"] != "Unknown"]
          .groupby("NEIGHBORHOOD")
          .size()
          .reset_index(name="count")
          .sort_values("count", ascending=True))

fig, ax = plt.subplots(figsize=(10, 7))
bars = ax.barh(nbhd["NEIGHBORHOOD"], nbhd["count"],
               color=NAVY, edgecolor="white")

# highlight top 3 in red
top3 = nbhd.nlargest(3, "count").index
for i, bar in enumerate(bars):
    if nbhd.index[i] in top3:
        bar.set_color(RED)

ax.set_title("Narcotic Incidents by Boston Neighborhood (2020–2025)",
             fontsize=14, fontweight="bold", color=NAVY)
ax.set_xlabel("Number of Incidents", fontsize=11)
ax.spines[["top","right"]].set_visible(False)
for bar in bars:
    ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
            str(int(bar.get_width())), va="center", fontsize=9)
plt.tight_layout()
plt.savefig("fig2_neighborhood_bar.png", dpi=150)
plt.show()
print("saved fig2_neighborhood_bar.png")

# ── FIG 3: ALTAIR — YEAR-OVER-YEAR BY NEIGHBORHOOD (interactive) ─────────────
# dropdown to select neighborhood, bars show monthly counts for that year
top_nbhd = (df[df["NEIGHBORHOOD"] != "Unknown"]
              .groupby("NEIGHBORHOOD")
              .size()
              .nlargest(8)
              .index.tolist())

df_top = df[df["NEIGHBORHOOD"].isin(top_nbhd)].copy()
yearly_nbhd = (df_top.groupby(["YEAR","NEIGHBORHOOD"])
                     .size()
                     .reset_index(name="count"))

nbhd_select = alt.selection_point(fields=["NEIGHBORHOOD"], bind="legend")

chart3 = (
    alt.Chart(yearly_nbhd)
    .mark_bar()
    .encode(
        x=alt.X("YEAR:O", title="Year"),
        y=alt.Y("count:Q", title="Number of Incidents"),
        color=alt.Color("NEIGHBORHOOD:N",
                        scale=alt.Scale(scheme="tableau10"),
                        title="Neighborhood"),
        opacity=alt.condition(nbhd_select, alt.value(1), alt.value(0.15)),
        tooltip=["NEIGHBORHOOD:N","YEAR:O","count:Q"]
    )
    .add_params(nbhd_select)
    .properties(
        title="Narcotic Incidents by Neighborhood and Year",
        width=600, height=350
    )
)
chart3.save("fig3_yearly_neighborhood.html")
print("saved fig3_yearly_neighborhood.html")

# ── FIG 4: ALTAIR — TIME OF DAY HEATMAP (interactive) ────────────────────────
heatmap_data = (df.groupby(["DAY_OF_WEEK","HOUR"])
                  .size()
                  .reset_index(name="count"))

day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# brush selection on hour range
brush = alt.selection_interval(encodings=["x"])

heatmap = (
    alt.Chart(heatmap_data)
    .mark_rect()
    .encode(
        x=alt.X("HOUR:O", title="Hour of Day (0–23)"),
        y=alt.Y("DAY_OF_WEEK:O", sort=day_order, title="Day of Week"),
        color=alt.Color("count:Q",
                        scale=alt.Scale(scheme="reds"),
                        title="Incidents"),
        opacity=alt.condition(brush, alt.value(1), alt.value(0.4)),
        tooltip=["DAY_OF_WEEK:N","HOUR:O","count:Q"]
    )
    .add_params(brush)
    .properties(
        title="When Do Narcotic Incidents Occur? (Day × Hour Heatmap)",
        width=600, height=250
    )
)

bar_hour = (
    alt.Chart(heatmap_data)
    .mark_bar(color=NAVY)
    .encode(
        x=alt.X("HOUR:O", title="Hour"),
        y=alt.Y("sum(count):Q", title="Total Incidents"),
        tooltip=["HOUR:O","sum(count):Q"]
    )
    .transform_filter(brush)
    .properties(width=600, height=150,
                title="Incidents in Selected Hours")
)

chart4 = heatmap & bar_hour
chart4.save("fig4_time_heatmap.html")
print("saved fig4_time_heatmap.html")

# ── FIG 5: ALTAIR — SEASONAL TREND BY YEAR (interactive, extra Altair) ────────
seasonal = (df.groupby(["YEAR","SEASON"])
              .size()
              .reset_index(name="count"))

season_order = ["Winter","Spring","Summer","Fall"]
year_select = alt.selection_point(fields=["YEAR"], bind="legend")

chart5 = (
    alt.Chart(seasonal)
    .mark_line(point=True)
    .encode(
        x=alt.X("SEASON:O", sort=season_order, title="Season"),
        y=alt.Y("count:Q", title="Number of Incidents"),
        color=alt.Color("YEAR:O",
                        scale=alt.Scale(scheme="viridis"),
                        title="Year"),
        opacity=alt.condition(year_select, alt.value(1), alt.value(0.1)),
        tooltip=["YEAR:O","SEASON:N","count:Q"]
    )
    .add_params(year_select)
    .properties(
        title="Seasonal Patterns in Narcotic Incidents by Year",
        width=500, height=350
    )
)
chart5.save("fig5_seasonal.html")
print("saved fig5_seasonal.html")

# ── FIG 6: ALTAIR — OFFENSE TYPE BREAKDOWN (extra Altair) ─────────────────────
offense_counts = (df.groupby("OFFENSE_DESCRIPTION")
                    .size()
                    .reset_index(name="count")
                    .nlargest(15, "count"))

chart6 = (
    alt.Chart(offense_counts)
    .mark_bar()
    .encode(
        x=alt.X("count:Q", title="Number of Incidents"),
        y=alt.Y("OFFENSE_DESCRIPTION:N",
                sort="-x", title="Offense Type"),
        color=alt.Color("count:Q",
                        scale=alt.Scale(scheme="blues"),
                        legend=None),
        tooltip=["OFFENSE_DESCRIPTION:N","count:Q"]
    )
    .properties(
        title="Top 15 Narcotic Offense Types in Boston (2020–2025)",
        width=550, height=400
    )
)
chart6.save("fig6_offense_types.html")
print("saved fig6_offense_types.html")

print("\nall figures saved!")
print("png files → embed directly in index.html")
print("html files → iframe embed in index.html")