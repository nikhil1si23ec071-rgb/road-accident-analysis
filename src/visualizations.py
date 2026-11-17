"""Plotly theme and reusable chart builders (dark 'traffic intelligence' look).

Colour rules (validated for contrast and colour-vision deficiency on the dark
chart surface #171A21):
  * severity is an identity encoding: fatal = red, major = amber, minor = blue
  * other categories use one fixed 8-hue order and never cycle
  * magnitudes (heatmaps) use a single-hue orange ramp, dark → bright
  * correlations use a blue ↔ red diverging scale with a neutral grey midpoint
  * single-series bars use the brand accent
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from src import config

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
BG = "#0E1014"
SURFACE = "#171A21"
GRID = "#252932"
AXIS = "#3A3F4B"
TEXT = "#E7E9EE"
TEXT_2 = "#A9AFBB"
MUTED = "#7C8391"
ACCENT = "#F26B3A"         # brand orange
ACCENT_SOFT = "#8A3E24"

SEVERITY_COLORS = {"fatal": "#E5484D", "major": "#C98500", "minor": "#3987E5"}
SEVERITY_LABEL = {"fatal": "Fatal", "major": "Major", "minor": "Minor"}
CATEGORICAL = ["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#0CA30C", "#9085E9", "#E66767"]
SEQUENTIAL = [[0.0, "#1E2129"], [0.2, "#3A2620"], [0.4, "#6B3220"], [0.6, "#A3431F"],
              [0.8, "#DC5E2B"], [1.0, "#FFA477"]]
DIVERGING = [[0.0, "#1C5CAB"], [0.25, "#5598E7"], [0.5, "#3A3D45"], [0.75, "#E66767"], [1.0, "#B0282B"]]
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif"


def color_map(values) -> dict:
    """Stable colour per category (sorted), never cycling past 8."""
    vals = sorted(pd.Series(list(values)).dropna().astype(str).unique())
    return {v: CATEGORICAL[i] if i < len(CATEGORICAL) else MUTED for i, v in enumerate(vals)}


pio.templates["raa_dark"] = go.layout.Template(
    layout=dict(
        font=dict(family=FONT, color=TEXT_2, size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=CATEGORICAL,
        xaxis=dict(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, tickcolor=AXIS,
                   title=dict(font=dict(color=MUTED, size=11)), automargin=True),
        yaxis=dict(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, tickcolor=AXIS,
                   title=dict(font=dict(color=MUTED, size=11)), automargin=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_2, size=11),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
        hoverlabel=dict(bgcolor="#1F232B", bordercolor="#3A3F4B", font=dict(family=FONT, color=TEXT, size=12)),
        margin=dict(l=8, r=12, t=36, b=8),
        bargap=0.42,
    )
)
pio.templates.default = "raa_dark"

PLOTLY_CONFIG = {"displaylogo": False, "responsive": True,
                 "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
                 "toImageButtonOptions": {"format": "png", "scale": 2}}


def finish(fig: go.Figure, height: int = 340, legend: bool = True, **kw) -> go.Figure:
    fig.update_layout(height=height, showlegend=legend, **kw)
    return fig


def empty_figure(msg: str = "No data for the current filters", height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(color=MUTED, size=13))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return finish(fig, height, legend=False)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def bar(df: pd.DataFrame, cat: str, val: str, horizontal: bool = False, color: str | list = ACCENT,
        value_fmt: str = ",.0f", suffix: str = "", hover_extra: dict | None = None,
        height: int = 340, cat_title: str = "", val_title: str = "", sort: bool = False,
        text: bool = True) -> go.Figure:
    if df.empty:
        return empty_figure(height=height)
    d = df.sort_values(val, ascending=horizontal) if sort else df
    custom, hover_lines = None, [f"<b>%{{{'y' if horizontal else 'x'}}}</b>",
                                 f"{val_title or val}: %{{{'x' if horizontal else 'y'}:{value_fmt}}}{suffix}"]
    if hover_extra:
        custom = np.column_stack([d[c].values for c in hover_extra])
        for i, (c, (lab, fmt)) in enumerate(hover_extra.items()):
            hover_lines.append(f"{lab}: %{{customdata[{i}]:{fmt}}}")
    fig = go.Figure(go.Bar(
        x=d[val] if horizontal else d[cat].astype(str),
        y=d[cat].astype(str) if horizontal else d[val],
        orientation="h" if horizontal else "v",
        marker=dict(color=color, cornerradius=4, line=dict(width=0)),
        text=d[val].map(lambda v: f"{v:{value_fmt}}{suffix}") if text else None,
        textposition="outside", textfont=dict(color=TEXT_2, size=11), cliponaxis=False,
        customdata=custom, hovertemplate="<br>".join(hover_lines) + "<extra></extra>",
    ))
    vmax = float(pd.to_numeric(d[val], errors="coerce").max() or 0)
    headroom = [0, vmax * 1.16] if text and vmax > 0 else None
    if horizontal:
        fig.update_xaxes(title_text=val_title, showgrid=True, range=headroom)
        fig.update_yaxes(title_text=cat_title, showgrid=False, type="category")
    else:
        fig.update_xaxes(title_text=cat_title, showgrid=False, type="category")
        fig.update_yaxes(title_text=val_title, range=headroom)
    return finish(fig, height, legend=False)


def donut(labels, values, colors, height: int = 320, center_text: str = "") -> go.Figure:
    if sum(values) == 0:
        return empty_figure(height=height)
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.64, sort=False, direction="clockwise",
        marker=dict(colors=colors, line=dict(color=SURFACE, width=2)),
        textinfo="percent", textfont=dict(color=TEXT, size=12),
        hovertemplate="<b>%{label}</b><br>%{value:,} accidents<br>%{percent} of selection<extra></extra>",
    ))
    if center_text:
        fig.add_annotation(text=center_text, x=0.5, y=0.5, showarrow=False,
                           font=dict(size=15, color=TEXT))
    return finish(fig, height, legend=True,
                  legend_orientation="v", legend_x=1.0, legend_y=0.5, legend_yanchor="middle")


def severity_stack(mix: pd.DataFrame, col: str, horizontal: bool = False, percent: bool = True,
                   height: int = 340, cat_title: str = "") -> go.Figure:
    """Stacked bars of severity within each category (100% or counts)."""
    if mix.empty:
        return empty_figure(height=height)
    fig = go.Figure()
    for sev in config.SEVERITY_ORDER:
        d = mix[mix["accident_severity"] == sev]
        val = d["pct"] if percent else d["count"]
        cats = d[col].astype(str)
        fig.add_trace(go.Bar(
            name=SEVERITY_LABEL[sev], x=val if horizontal else cats, y=cats if horizontal else val,
            orientation="h" if horizontal else "v",
            marker=dict(color=SEVERITY_COLORS[sev], line=dict(color=SURFACE, width=1.5)),
            customdata=np.column_stack([d["count"], d["pct"], d["group_total"]]),
            hovertemplate=(f"<b>%{{{'y' if horizontal else 'x'}}}</b> · {SEVERITY_LABEL[sev]}<br>"
                           "%{customdata[0]:,} accidents<br>%{customdata[1]:.1f}% of group "
                           "(n = %{customdata[2]:,})<extra></extra>"),
            text=[f"{p:.0f}%" if percent and p >= 8 else "" for p in d["pct"]],
            textposition="inside", insidetextanchor="middle", textfont=dict(color="#FFFFFF", size=11),
        ))
    fig.update_layout(barmode="stack")
    axis_title = "% of accidents in group" if percent else "Accidents"
    if horizontal:
        fig.update_xaxes(title_text=axis_title, range=[0, 100] if percent else None)
        fig.update_yaxes(title_text=cat_title, type="category", autorange="reversed")
    else:
        fig.update_yaxes(title_text=axis_title, range=[0, 100] if percent else None)
        fig.update_xaxes(title_text=cat_title, type="category")
    return finish(fig, height)


def rate_ci(summary: pd.DataFrame, col: str, overall: float | None = None, height: int = 340,
            cat_title: str = "", sort: bool = True, color: str = SEVERITY_COLORS["fatal"]) -> go.Figure:
    """Fatality rate per group as dots with 95% Wilson confidence intervals.
    Overlapping intervals mean the groups cannot be told apart."""
    if summary.empty:
        return empty_figure(height=height)
    d = summary.sort_values("fatal_rate") if sort else summary.iloc[::-1]
    cats = d[col].astype(str)
    fig = go.Figure(go.Scatter(
        x=d["fatal_rate"], y=cats, mode="markers",
        marker=dict(size=11, color=[color if r else MUTED for r in d["reliable"]],
                    line=dict(color=SURFACE, width=2)),
        error_x=dict(type="data", symmetric=False, array=d["ci_high"] - d["fatal_rate"],
                     arrayminus=d["fatal_rate"] - d["ci_low"], color="#5A606C", thickness=2, width=0),
        customdata=np.column_stack([d["fatal"], d["accidents"], d["ci_low"], d["ci_high"]]),
        hovertemplate=("<b>%{y}</b><br>Fatality rate: %{x:.1f}%<br>95% CI: %{customdata[2]:.1f}–"
                       "%{customdata[3]:.1f}%<br>%{customdata[0]:,} fatal of %{customdata[1]:,} accidents"
                       "<extra></extra>"),
    ))
    if overall is not None and not np.isnan(overall):
        fig.add_vline(x=overall, line=dict(color=TEXT_2, dash="dot", width=1))
        fig.add_annotation(x=overall, y=1.0, yref="paper", text=f"overall {overall:.1f}%",
                           showarrow=False, yanchor="bottom", font=dict(color=TEXT_2, size=11))
    fig.update_xaxes(title_text="Fatality rate (% of accidents that were fatal)", ticksuffix="%")
    fig.update_yaxes(title_text=cat_title, type="category", showgrid=False)
    return finish(fig, height, legend=False)


def lines(df: pd.DataFrame, x: str, y: str, group: str | None = None, colors: dict | None = None,
          height: int = 340, x_title: str = "", y_title: str = "", value_fmt: str = ",.0f",
          markers: bool = True, hover_extra: dict | None = None, single_color: str = ACCENT) -> go.Figure:
    if df.empty:
        return empty_figure(height=height)
    fig = go.Figure()
    groups = [(None, df)] if group is None else list(df.groupby(group, sort=True))
    for name, d in groups:
        c = single_color if group is None else (colors or {}).get(str(name), None)
        custom, extra = None, ""
        if hover_extra:
            custom = np.column_stack([d[k].values for k in hover_extra])
            extra = "".join(f"<br>{lab}: %{{customdata[{i}]:{fmt}}}"
                            for i, (k, (lab, fmt)) in enumerate(hover_extra.items()))
        fig.add_trace(go.Scatter(
            x=d[x], y=d[y], name=str(name) if name is not None else y_title,
            mode="lines+markers" if markers else "lines",
            line=dict(width=2, color=c, shape="linear"),
            marker=dict(size=8, color=c, line=dict(color=SURFACE, width=2)),
            customdata=custom,
            hovertemplate=(f"<b>{name if name is not None else ''}</b> %{{x}}<br>"
                           f"{y_title or y}: %{{y:{value_fmt}}}{extra}<extra></extra>"),
        ))
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title_text=x_title, showgrid=False)
    if df[x].dtype == object or str(df[x].dtype).startswith("str"):
        fig.update_xaxes(type="category")
    fig.update_yaxes(title_text=y_title)
    return finish(fig, height, legend=group is not None)


def heatmap(matrix: pd.DataFrame, height: int = 340, x_title: str = "", y_title: str = "",
            z_label: str = "Accidents", value_fmt: str = ",.0f", colorscale=None, zmid=None,
            zmin=None, zmax=None, show_text: bool = False) -> go.Figure:
    if matrix.empty:
        return empty_figure(height=height)
    fig = go.Figure(go.Heatmap(
        z=matrix.values, x=[str(c) for c in matrix.columns], y=[str(i) for i in matrix.index],
        colorscale=colorscale or SEQUENTIAL, zmid=zmid, zmin=zmin, zmax=zmax, xgap=2, ygap=2,
        colorbar=dict(title=dict(text=z_label, font=dict(color=MUTED, size=11)), thickness=10,
                      outlinewidth=0, tickfont=dict(color=TEXT_2, size=10)),
        text=np.vectorize(lambda v: "" if np.isnan(v) else f"{(v + 0.0) if abs(v) >= 0.005 else 0.0:{value_fmt}}")(matrix.values.astype(float))
        if show_text else None,
        texttemplate="%{text}" if show_text else None, textfont=dict(size=10, color=TEXT),
        hovertemplate=f"<b>%{{y}}</b> · %{{x}}<br>{z_label}: %{{z:{value_fmt}}}<extra></extra>",
    ))
    fig.update_xaxes(title_text=x_title, showgrid=False, type="category")
    fig.update_yaxes(title_text=y_title, showgrid=False, type="category", autorange="reversed")
    return finish(fig, height, legend=False)


def histogram(series: pd.Series, nbins: int = 30, height: int = 320, x_title: str = "",
              color: str = ACCENT, mean_line: bool = True) -> go.Figure:
    s = series.dropna()
    if s.empty:
        return empty_figure(height=height)
    fig = go.Figure(go.Histogram(
        x=s, nbinsx=nbins, marker=dict(color=color, line=dict(color=SURFACE, width=1.5)),
        hovertemplate=f"{x_title}: %{{x}}<br>Accidents: %{{y:,}}<extra></extra>"))
    if mean_line:
        fig.add_vline(x=s.mean(), line=dict(color=TEXT, dash="dot", width=1))
        fig.add_annotation(x=s.mean(), y=1, yref="paper", text=f"mean {s.mean():.2f}",
                           showarrow=False, yanchor="bottom", font=dict(color=TEXT_2, size=11))
    fig.update_xaxes(title_text=x_title)
    fig.update_yaxes(title_text="Accidents")
    return finish(fig, height, legend=False, bargap=0.05)


def box_by(df: pd.DataFrame, value: str, group: str, order: list, colors: dict, height: int = 320,
           value_title: str = "", labels: dict | None = None) -> go.Figure:
    if df.empty:
        return empty_figure(height=height)
    fig = go.Figure()
    for g in order:
        d = df.loc[df[group] == g, value].dropna()
        if d.empty:
            continue
        fig.add_trace(go.Box(y=d, name=(labels or {}).get(g, str(g)), marker_color=colors.get(g, ACCENT),
                             line=dict(width=1.5), boxmean=True, fillcolor="rgba(0,0,0,0)",
                             hovertemplate=f"%{{y:.2f}}<extra>{(labels or {}).get(g, g)}</extra>"))
    fig.update_yaxes(title_text=value_title)
    return finish(fig, height, legend=False)


def corr_heatmap(corr: pd.DataFrame, height: int = 460) -> go.Figure:
    if corr.empty:
        return empty_figure(height=height)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    z = corr.where(~mask)
    z.index = [str(i).replace("_", " ") for i in z.index]
    z.columns = [str(c).replace("_", " ") for c in z.columns]
    fig = heatmap(z, height=height, z_label="Spearman ρ", value_fmt=".2f", colorscale=DIVERGING,
                  zmid=0, zmin=-1, zmax=1, show_text=True)
    fig.update_traces(textfont=dict(size=9), xgap=1, ygap=1)
    fig.update_xaxes(tickangle=-40)
    return fig


OFFLINE_MAP_STYLE = {"version": 8, "sources": {}, "layers": [
    {"id": "bg", "type": "background", "paint": {"background-color": "#11141A"}}]}


def map_points(df: pd.DataFrame, color_by: str = "accident_severity", height: int = 560,
               mode: str = "points", basemap: bool = True) -> go.Figure:
    d = df[df["coord_valid"] == 1]
    if d.empty:
        return empty_figure("No valid coordinates in the current selection", height)
    centre = dict(lat=float(d["latitude"].median()), lon=float(d["longitude"].median()))
    span = max(d["latitude"].max() - d["latitude"].min(), d["longitude"].max() - d["longitude"].min())
    zoom = 3.6 if span > 8 else 5 if span > 3 else 8.3 if span > 0.3 else 10
    fig = go.Figure()
    if mode == "density":
        fig.add_trace(go.Densitymap(
            lat=d["latitude"], lon=d["longitude"], radius=9,
            colorscale=SEQUENTIAL[1:], showscale=True, opacity=0.85,
            colorbar=dict(title=dict(text="Density", font=dict(color=MUTED, size=11)), thickness=10,
                          outlinewidth=0, tickfont=dict(color=TEXT_2, size=10)),
            hoverinfo="skip"))
    else:
        for sev in reversed(config.SEVERITY_ORDER):  # draw fatal last (on top)
            s = d[d[color_by] == sev]
            if s.empty:
                continue
            fig.add_trace(go.Scattermap(
                lat=s["latitude"], lon=s["longitude"], mode="markers", name=SEVERITY_LABEL[sev],
                marker=dict(size=6 if sev != "fatal" else 7, color=SEVERITY_COLORS[sev], opacity=0.75),
                customdata=np.column_stack([s["city"], s["date"].dt.strftime("%d %b %Y"), s["time"],
                                            s["cause"], s["weather"], s["road_type"], s["casualties"],
                                            s["vehicles_involved"], s["accident_id"]]),
                hovertemplate=("<b>%{customdata[0]}</b> · " + SEVERITY_LABEL[sev] +
                               "<br>%{customdata[1]} %{customdata[2]}<br>Cause: %{customdata[3]}"
                               "<br>Weather: %{customdata[4]} · Road: %{customdata[5]}"
                               "<br>Casualties: %{customdata[6]} · Vehicles: %{customdata[7]}"
                               "<br>ID %{customdata[8]}<extra></extra>")))
    fig.update_layout(map=dict(style="carto-darkmatter" if basemap else OFFLINE_MAP_STYLE,
                               center=centre, zoom=zoom),
                      margin=dict(l=0, r=0, t=0, b=0), height=height,
                      legend=dict(orientation="h", y=0.01, x=0.01, yanchor="bottom",
                                  bgcolor="rgba(14,16,20,0.75)"))
    return fig


def scatter_jitter(df: pd.DataFrame, x: str, y: str, height: int = 380, x_title: str = "",
                   y_title: str = "", max_points: int = 20000, seed: int = 7) -> go.Figure:
    """Integer-valued scatter with jitter so overlapping points stay visible,
    coloured by severity, plus a count bubble layer for exact frequencies."""
    if df.empty:
        return empty_figure(height=height)
    d = df if len(df) <= max_points else df.sample(max_points, random_state=seed)
    rng = np.random.default_rng(seed)
    fig = go.Figure()
    for sev in reversed(config.SEVERITY_ORDER):
        s = d[d["accident_severity"] == sev]
        fig.add_trace(go.Scattergl(
            x=s[x] + rng.uniform(-0.28, 0.28, len(s)), y=s[y] + rng.uniform(-0.28, 0.28, len(s)),
            mode="markers", name=SEVERITY_LABEL[sev],
            marker=dict(size=4, color=SEVERITY_COLORS[sev], opacity=0.45),
            customdata=np.column_stack([s[x], s[y]]),
            hovertemplate=f"{x_title}: %{{customdata[0]}}<br>{y_title}: %{{customdata[1]}}"
                          f"<extra>{SEVERITY_LABEL[sev]}</extra>"))
    fig.update_xaxes(title_text=x_title, dtick=1)
    fig.update_yaxes(title_text=y_title, dtick=1)
    return finish(fig, height)
