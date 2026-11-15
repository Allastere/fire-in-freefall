"""Swiss Scientific Editorial V2: typography, obsidian surfaces and source-first figures."""

from html import escape
import plotly.io as pio
import streamlit as st

ORANGE = "#C88A60"
COLORS = ["#7B9DB8", "#C88A60", "#91979F", "#ECC09C", "#E8E7E3"]


def install_design():
    pio.templates["freefall"] = pio.templates["plotly_white"]
    pio.templates["freefall"].layout.update(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=COLORS, font=dict(family="Geist, Arial, sans-serif", color="#E8E7E3", size=12),
        margin=dict(l=15, r=20, t=24, b=20),
        xaxis=dict(gridcolor="#33383E", zerolinecolor="#33383E", linecolor="#33383E"),
        yaxis=dict(gridcolor="#33383E", zerolinecolor="#33383E", linecolor="#33383E"),
        legend=dict(orientation="h", y=-.22), hoverlabel=dict(bgcolor="#24282D", font_color="#E8E7E3", bordercolor="#33383E"))
    pio.templates.default = "freefall"
    st.html("""<style>
    [data-testid="stMainBlockContainer"] {max-width:1440px;padding:1.5rem 3rem 3rem;}
    [data-testid="stHeader"] {display:none;}
    [data-testid="stToolbar"] {opacity:.35;}
    h1,h2,h3 {letter-spacing:-.04em;font-weight:600;}
    h1 {font-size:3.3rem!important;line-height:1.05!important;max-width:1050px;}
    h2 {font-size:1.6rem!important;} h3 {font-size:1.05rem!important;}
    [data-testid="stCaptionContainer"] {color:#91979F;}
    [data-testid="stCaptionContainer"] p {color:#91979F;opacity:1;}
    body [data-testid="stCaptionContainer"], body [data-testid="stCaptionContainer"] * {color:#91979F!important;opacity:1!important;}
    [data-testid="stVerticalBlock"] {gap:.9rem;}
    [data-testid="stMetric"] {border:0!important;border-top:1px solid #33383E!important;padding:1rem 0;background:transparent;}
    [data-testid="stMetricLabel"] {font:10px 'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:.06em;}
    [data-testid="stMetricValue"] {font-weight:300;font-size:2.6rem;color:#E8E7E3;letter-spacing:-.04em;}
    [data-testid="stExpander"] {border:0!important;background:transparent;}
    [data-testid="stExpander"] details {border:0!important;border-top:1px solid #33383E!important;background:transparent;}
    [data-testid="stForm"] {border:0!important;padding:0!important;background:transparent;}
    .st-key-editorial_nav {border-bottom:1px solid #33383E;padding-bottom:1.2rem;}
    .st-key-editorial_nav [data-testid="stPageLink"] a {text-transform:uppercase;font-size:11px;letter-spacing:.06em;padding:.6rem .3rem;}
    .st-key-nav_active {border-bottom:2px solid #C88A60;}
    .st-key-nav_active [data-testid="stPageLink-NavLink"] {background:transparent!important;}
    .st-key-nav_active a p {color:#C88A60;}
    .ff-brand strong {font-size:19px;letter-spacing:-.05em;-webkit-text-stroke:.3px #E8E7E3;paint-order:stroke fill;}
    .ff-brand {border-bottom:2px solid #C88A60;padding-bottom:8px;width:fit-content;}
    .ff-brand small {font:9px 'JetBrains Mono',monospace;display:block;letter-spacing:.06em;margin-top:4px;}
    .ff-eyebrow,.ff-section {font:10px 'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:.09em;color:#C88A60;}
    .ff-eyebrow {padding:1rem 0;border-bottom:1px solid #33383E;margin-bottom:2rem;}
    .ff-hero h1 {margin:0;padding:0 0 14px;font-size:52px;line-height:1.04;letter-spacing:-.05em;font-weight:650;max-width:620px;}
    .ff-hero h1 {-webkit-text-stroke:.45px #E8E7E3;paint-order:stroke fill;}
    .ff-conclusion {border-left:3px solid #C88A60;padding-left:20px;}
    .ff-hero p {font-size:16px;color:#91979F;max-width:800px;line-height:1.65;margin:0 0 1.6rem;}
    .ff-section {border-top:1px solid #33383E;padding-top:1rem;margin-top:1rem;margin-bottom:.7rem;}
    .ff-conclusion {font-size:27px;line-height:1.4;letter-spacing:-.025em;font-weight:500;max-width:1000px;margin:1rem 0 1.8rem;}
    .ff-tag {font:10px 'JetBrains Mono',monospace;text-transform:uppercase;color:#ECC09C;background:#24282D;padding:5px 8px;}
    .ff-card {border-top:1px solid #33383E;padding:1rem 0;}
    .ff-card p {color:#91979F;line-height:1.6;}
    .ff-status {font:11px 'JetBrains Mono',monospace;color:#C88A60;border-bottom:1px solid #33383E;padding:.8rem 0;}
    .ff-status small {display:block;color:#91979F;margin-top:5px;}
    .ff-footer {border-top:1px solid #33383E;padding:2rem 0 .6rem;margin-top:3rem;color:#91979F;font-size:11px;}
    .ff-index {font-size:48px;font-weight:300;color:#E8E7E3;letter-spacing:-.06em;}
    @media(max-width:850px) {[data-testid="stMainBlockContainer"]{padding:1rem;} .ff-hero h1{font-size:34px;} .ff-conclusion{font-size:22px;}}
    button[kind="primary"] {color:#101214!important;}
    </style>""")


def brand():
    st.html('<div class="ff-brand"><strong>FLAME IN FREEFALL <span style="color:#C88A60">◇</span></strong><small>NASA PHYSICAL SCIENCES INFORMATICS / RESEARCH ARCHIVE</small></div>')


def page_header(title, subtitle, section="Scientific research"):
    st.html(f'<div class="ff-hero"><div class="ff-eyebrow">{escape(section)}</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>')


def section(title):
    st.html(f'<div class="ff-section">{escape(title)}</div>')


def conclusion(text):
    st.html(f'<div class="ff-conclusion">{escape(text)}</div>')


def metric_row(items):
    if not items:
        return
    for column, (label, value) in zip(st.columns(len(items)), items):
        column.metric(label, value)


def chart(fig, alt, height=380, **kwargs):
    fig.update_layout(template="freefall", height=height)
    st.plotly_chart(fig, width="stretch", theme=None, alt=alt, **kwargs)


def card(title, description, tag=""):
    st.html(f'<div class="ff-card"><span class="ff-tag">{escape(tag)}</span><h3>{escape(title)}</h3><p>{escape(description)}</p></div>')


def status_banner(status, description):
    st.html(f'<div class="ff-status">{escape(status.replace("_", " "))}<small>{escape(description)}</small></div>')
