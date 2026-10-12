"""Visual layer for AJ's Academy: theme CSS and original SVG illustrations."""
import html as _html
import streamlit as st

PALETTE = {
    "sky": "#CFE8F3", "sea": "#3E8FB0", "mint": "#BFE6D3", "leaf": "#4FA37A",
    "sun": "#FFD37A", "peach": "#FFB59A", "coral": "#E8776A", "plum": "#6C5B9E",
    "ink": "#24364B", "cream": "#FFF8EC", "sand": "#F4E3C3",
}

_CSS = """
<style>
.stApp{background:linear-gradient(180deg,#FFF8EC 0%,#EEF6F4 100%);}
.block-container{max-width:1100px;padding-top:1.5rem;}
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{
  min-height:3.4rem;border-radius:18px;font-size:1.1rem;font-weight:700;
  border:2px solid #24364B22;background:#ffffffcc;color:#24364B;
  box-shadow:0 4px 0 #24364B1f;transition:transform .12s ease;}
.stButton>button:hover{transform:translateY(-2px);border-color:#3E8FB0;color:#3E8FB0;}
.stButton>button:active{transform:translateY(2px);box-shadow:0 1px 0 #24364B1f;}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{
  background:#3E8FB0;color:#FFF8EC;border-color:#3E8FB0;box-shadow:0 4px 0 #2a6c87;}
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stDateInput input{
  min-height:3rem;border-radius:14px;font-size:1.1rem;}
.stCheckbox label{font-size:1.15rem;padding:.4rem 0;}
.stTabs [data-baseweb="tab"]{min-height:3.2rem;font-size:1.05rem;font-weight:700;
  border-radius:14px 14px 0 0;padding:0 1.1rem;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:22px;}
[data-testid="stMetric"]{background:#ffffffb3;border-radius:18px;padding:.8rem 1rem;
  border:1px solid #24364B14;}
[data-testid="stSidebar"]{background:#EAF4F1;}
.aj-hero{display:flex;align-items:center;gap:1.2rem;padding:1.3rem 1.6rem;
  border-radius:26px;background:linear-gradient(120deg,#CFE8F3,#FFF1D6);
  border:1px solid #24364B14;margin-bottom:1rem;animation:ajIn .5s ease both;}
.aj-hero h1{margin:0;font-size:2.2rem;line-height:1.1;color:#24364B;}
.aj-hero p{margin:.35rem 0 0;font-size:1.15rem;color:#24364Bcc;}
.aj-hero .aj-star{flex:0 0 auto;}
.aj-ill{display:flex;justify-content:center;animation:ajIn .5s ease both;}
.aj-ill svg{max-width:100%;}
.aj-welcome{border-radius:30px;overflow:hidden;border:1px solid #24364B14;
  box-shadow:0 18px 40px -24px #24364B66;animation:ajIn .6s ease both;}
@keyframes ajIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes ajFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.aj-float{animation:ajFloat 5s ease-in-out infinite;}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
</style>
"""


def apply_theme() -> None:
    """Inject the global touch-friendly theme CSS. Call once per page run."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _svg(body: str, height: int, vb: str = "0 0 200 150", label: str | None = None) -> str:
    title = f"<title>{_html.escape(label)}</title>" if label else ""
    return (f'<div class="aj-ill"><svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
            f'height="{int(height)}" role="img">{title}{body}</svg></div>')


def _bg(color: str) -> str:
    return f'<rect x="8" y="8" width="184" height="134" rx="30" fill="{color}"/>'


_STAR = ('<svg width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30" fill="#FFD37A"/>'
         '<path d="M32 12l5.6 12.4 13.4 1.4-10 9 2.9 13.2L32 41.3 20.1 48l2.9-13.2-10-9 13.4-1.4z" '
         'fill="#FFF8EC"/></svg>')

C = PALETTE
_ART = {
    "investments": _bg(C["mint"]) +
        '<rect x="45" y="95" width="22" height="30" rx="4" fill="#4FA37A"/>'
        '<rect x="75" y="80" width="22" height="45" rx="4" fill="#3E8FB0"/>'
        '<rect x="105" y="62" width="22" height="63" rx="4" fill="#6C5B9E"/>'
        '<path d="M40 85 L80 65 L110 50 L150 30" stroke="#24364B" stroke-width="4" fill="none" stroke-linecap="round"/>'
        '<path d="M140 28 L152 29 L149 41" stroke="#24364B" stroke-width="4" fill="none" stroke-linecap="round"/>'
        '<circle cx="155" cy="105" r="20" fill="#FFD37A" stroke="#E0A94A" stroke-width="4"/>'
        '<text x="155" y="112" font-size="20" text-anchor="middle" fill="#9A6A1E" font-weight="700">$</text>',
    "college": _bg(C["sky"]) +
        '<rect x="50" y="70" width="100" height="55" fill="#FFF8EC"/>'
        '<polygon points="40,72 100,38 160,72" fill="#E8776A"/>'
        '<rect x="62" y="82" width="10" height="38" fill="#CFE8F3"/><rect x="82" y="82" width="10" height="38" fill="#CFE8F3"/>'
        '<rect x="108" y="82" width="10" height="38" fill="#CFE8F3"/><rect x="128" y="82" width="10" height="38" fill="#CFE8F3"/>'
        '<polygon points="100,20 130,30 100,40 70,30" fill="#24364B"/>'
        '<path d="M128 31 v12" stroke="#FFD37A" stroke-width="3"/><circle cx="128" cy="45" r="3" fill="#FFD37A"/>',
    "diary": _bg(C["peach"]) +
        '<rect x="55" y="30" width="90" height="95" rx="10" fill="#6C5B9E"/>'
        '<rect x="63" y="30" width="82" height="95" rx="8" fill="#8F7FC4"/>'
        '<rect x="75" y="48" width="58" height="8" rx="4" fill="#FFF8EC"/>'
        '<rect x="75" y="64" width="44" height="6" rx="3" fill="#FFF8EC" opacity=".7"/>'
        '<path d="M120 100 l25 -40 8 5 -25 40 -10 4z" fill="#FFD37A" stroke="#24364B" stroke-width="2"/>',
    "reminders": _bg(C["sand"]) +
        '<circle cx="100" cy="78" r="45" fill="#FFF8EC" stroke="#3E8FB0" stroke-width="7"/>'
        '<path d="M100 78 V50 M100 78 L120 90" stroke="#24364B" stroke-width="6" stroke-linecap="round"/>'
        '<circle cx="62" cy="38" r="12" fill="#E8776A"/><circle cx="138" cy="38" r="12" fill="#E8776A"/>'
        '<circle cx="100" cy="78" r="5" fill="#E8776A"/>',
    "soccer": _bg(C["mint"]) +
        '<rect x="20" y="110" width="160" height="22" rx="10" fill="#4FA37A"/>'
        '<circle cx="100" cy="75" r="38" fill="#FFF8EC" stroke="#24364B" stroke-width="4"/>'
        '<polygon points="100,60 114,70 109,86 91,86 86,70" fill="#24364B"/>'
        '<path d="M100 60 V38 M114 70 L134 62 M109 86 L120 104 M91 86 L80 104 M86 70 L66 62" stroke="#24364B" stroke-width="3"/>',
    "lego": _bg(C["sky"]) +
        '<rect x="40" y="80" width="80" height="40" rx="4" fill="#E8776A"/>'
        '<rect x="50" y="70" width="18" height="12" rx="3" fill="#E8776A"/><rect x="92" y="70" width="18" height="12" rx="3" fill="#E8776A"/>'
        '<rect x="95" y="45" width="65" height="35" rx="4" fill="#FFD37A"/>'
        '<rect x="103" y="35" width="16" height="12" rx="3" fill="#FFD37A"/><rect x="136" y="35" width="16" height="12" rx="3" fill="#FFD37A"/>'
        '<rect x="120" y="90" width="50" height="30" rx="4" fill="#3E8FB0"/>',
    "ai": _bg(C["sky"]) +
        '<rect x="60" y="45" width="80" height="65" rx="20" fill="#FFF8EC" stroke="#3E8FB0" stroke-width="5"/>'
        '<circle cx="85" cy="75" r="9" fill="#3E8FB0"/><circle cx="115" cy="75" r="9" fill="#3E8FB0"/>'
        '<path d="M88 95 Q100 103 112 95" stroke="#24364B" stroke-width="4" fill="none" stroke-linecap="round"/>'
        '<path d="M100 45 V28" stroke="#3E8FB0" stroke-width="5"/><circle cx="100" cy="24" r="7" fill="#FFD37A"/>'
        '<rect x="48" y="68" width="12" height="20" rx="5" fill="#6C5B9E"/><rect x="140" y="68" width="12" height="20" rx="5" fill="#6C5B9E"/>',
    "arcade": _bg(C["plum"]) +
        '<rect x="65" y="25" width="70" height="110" rx="12" fill="#E8776A"/>'
        '<rect x="74" y="36" width="52" height="40" rx="6" fill="#24364B"/>'
        '<rect x="88" y="52" width="8" height="8" fill="#FFD37A"/><rect x="104" y="48" width="8" height="8" fill="#BFE6D3"/>'
        '<path d="M88 100 V88" stroke="#24364B" stroke-width="4"/><circle cx="88" cy="86" r="6" fill="#FFD37A"/>'
        '<circle cx="108" cy="98" r="5" fill="#CFE8F3"/><circle cx="120" cy="93" r="5" fill="#BFE6D3"/>',
    "social": _bg(C["peach"]) +
        '<circle cx="75" cy="65" r="18" fill="#FFF8EC"/><rect x="50" y="88" width="50" height="35" rx="18" fill="#3E8FB0"/>'
        '<circle cx="125" cy="65" r="18" fill="#FFF8EC"/><rect x="100" y="88" width="50" height="35" rx="18" fill="#4FA37A"/>'
        '<path d="M100 40 c-6 -10 -20 -4 -12 6 l12 10 12 -10 c8 -10 -6 -16 -12 -6z" fill="#E8776A"/>',
    "home": _bg(C["sky"]) +
        '<rect x="55" y="70" width="90" height="55" fill="#FFF8EC"/>'
        '<polygon points="45,74 100,32 155,74" fill="#E8776A"/>'
        '<rect x="90" y="92" width="20" height="33" rx="3" fill="#6C5B9E"/>'
        '<rect x="64" y="84" width="16" height="16" fill="#FFD37A"/><rect x="120" y="84" width="16" height="16" fill="#FFD37A"/>'
        '<rect x="20" y="122" width="160" height="10" rx="5" fill="#4FA37A"/>',
    "car": _bg(C["sand"]) +
        '<path d="M35 100 L45 75 Q50 62 65 62 H125 Q140 62 148 75 L165 100 V112 H35z" fill="#3E8FB0"/>'
        '<path d="M62 70 H95 V88 H52z M102 70 H130 L142 88 H102z" fill="#CFE8F3"/>'
        '<circle cx="65" cy="113" r="14" fill="#24364B"/><circle cx="65" cy="113" r="5" fill="#FFF8EC"/>'
        '<circle cx="138" cy="113" r="14" fill="#24364B"/><circle cx="138" cy="113" r="5" fill="#FFF8EC"/>',
    "vacation": _bg(C["sky"]) +
        '<circle cx="150" cy="42" r="16" fill="#FFD37A"/>'
        '<path d="M8 105 Q60 95 100 105 T192 105 V112 H8z" fill="#3E8FB0"/>'
        '<path d="M8 112 H192 V112 Q192 142 162 142 H38 Q8 142 8 112z" fill="#F4E3C3"/>'
        '<path d="M70 120 Q72 80 78 50" stroke="#9A6A1E" stroke-width="6" fill="none"/>'
        '<path d="M78 50 q-25 -5 -35 10 M78 50 q25 -8 35 8 M78 50 q-10 -20 -28 -18 M78 50 q12 -20 30 -14" stroke="#4FA37A" stroke-width="7" fill="none" stroke-linecap="round"/>',
    "brush": _bg(C["mint"]) +
        '<rect x="45" y="70" width="110" height="16" rx="8" fill="#3E8FB0" transform="rotate(-20 100 78)"/>'
        '<rect x="118" y="45" width="34" height="18" rx="4" fill="#FFF8EC" stroke="#CFE8F3" stroke-width="3" transform="rotate(-20 135 54)"/>'
        '<circle cx="60" cy="110" r="8" fill="#FFF8EC"/><circle cx="78" cy="118" r="5" fill="#FFF8EC"/><circle cx="150" cy="100" r="6" fill="#FFF8EC"/>',
    "dress": _bg(C["peach"]) +
        '<path d="M80 30 L120 30 L135 50 L125 60 L120 55 V125 H80 V55 L75 60 L65 50z" fill="#3E8FB0"/>'
        '<path d="M88 30 Q100 45 112 30" fill="#FFF8EC"/><circle cx="100" cy="75" r="4" fill="#FFF8EC"/><circle cx="100" cy="95" r="4" fill="#FFF8EC"/>',
    "water": _bg(C["sky"]) +
        '<path d="M75 35 H125 L118 125 H82z" fill="#FFF8EC" stroke="#3E8FB0" stroke-width="4"/>'
        '<path d="M79 70 H121 L118 125 H82z" fill="#3E8FB0" opacity=".7"/>'
        '<path d="M150 50 q-10 15 0 22 q10 -7 0 -22z" fill="#3E8FB0"/>',
    "shoes": _bg(C["sand"]) +
        '<path d="M35 105 V75 Q50 70 65 78 L100 92 Q130 96 135 108 V115 H35z" fill="#E8776A"/>'
        '<rect x="35" y="112" width="102" height="8" rx="4" fill="#24364B"/>'
        '<path d="M70 82 l8 6 M80 86 l8 6" stroke="#FFF8EC" stroke-width="3"/>'
        '<path d="M110 70 q20 -10 40 0 q-20 10 -40 0z" fill="#4FA37A"/>',
    "clothes": _bg(C["mint"]) +
        '<path d="M100 25 q8 0 8 8 q0 6 -8 10 L40 75 H160 L100 43" stroke="#24364B" stroke-width="4" fill="none"/>'
        '<path d="M60 80 L80 74 Q100 85 120 74 L140 80 L148 100 L134 104 V128 H66 V104 L52 100z" fill="#FFD37A"/>',
    "dinner": _bg(C["peach"]) +
        '<circle cx="100" cy="85" r="42" fill="#FFF8EC" stroke="#E8776A" stroke-width="4"/>'
        '<circle cx="88" cy="80" r="12" fill="#4FA37A"/><rect x="98" y="82" width="22" height="14" rx="6" fill="#E8776A"/>'
        '<circle cx="95" cy="102" r="7" fill="#FFD37A"/>'
        '<path d="M42 50 V120 M36 50 V68 M48 50 V68" stroke="#24364B" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M158 50 q10 20 0 30 V120" stroke="#24364B" stroke-width="4" fill="none" stroke-linecap="round"/>',
    "plates": _bg(C["sky"]) +
        '<ellipse cx="100" cy="115" rx="55" ry="10" fill="#3E8FB0"/>'
        '<ellipse cx="100" cy="100" rx="50" ry="10" fill="#FFF8EC" stroke="#CFE8F3" stroke-width="3"/>'
        '<ellipse cx="100" cy="86" rx="50" ry="10" fill="#FFF8EC" stroke="#CFE8F3" stroke-width="3"/>'
        '<ellipse cx="100" cy="72" rx="50" ry="10" fill="#FFF8EC" stroke="#CFE8F3" stroke-width="3"/>'
        '<circle cx="150" cy="40" r="8" fill="#FFF8EC"/><circle cx="135" cy="30" r="5" fill="#FFF8EC"/>',
    "shower": _bg(C["sky"]) +
        '<path d="M60 30 H110 V50" stroke="#24364B" stroke-width="6" fill="none"/>'
        '<path d="M85 50 H135 Q130 65 110 65 Q90 65 85 50z" fill="#6C5B9E"/>'
        '<path d="M95 75 v12 M110 75 v18 M125 75 v12 M102 100 v12 M118 100 v12 M110 115 v10" stroke="#3E8FB0" stroke-width="5" stroke-linecap="round"/>',
    "chores": _bg(C["sand"]) +
        '<path d="M130 25 L95 100" stroke="#9A6A1E" stroke-width="6" stroke-linecap="round"/>'
        '<path d="M80 95 L115 108 L105 130 Q80 128 65 115z" fill="#FFD37A"/>'
        '<rect x="35" y="95" width="30" height="32" rx="4" fill="#3E8FB0"/>'
        '<circle cx="150" cy="110" r="5" fill="#FFF8EC"/><circle cx="160" cy="98" r="3" fill="#FFF8EC"/>',
    "toetaps": _bg(C["mint"]) +
        '<circle cx="100" cy="105" r="20" fill="#FFF8EC" stroke="#24364B" stroke-width="3"/>'
        '<polygon points="100,98 107,103 104,111 96,111 93,103" fill="#24364B"/>'
        '<path d="M55 60 Q65 75 80 85 l-6 8 -30 -12z" fill="#E8776A"/>'
        '<path d="M145 60 Q135 75 120 85 l6 8 30 -12z" fill="#3E8FB0"/>'
        '<path d="M70 40 q5 -8 10 0 M120 40 q5 -8 10 0" stroke="#24364B" stroke-width="3" fill="none"/>',
    "dribble": _bg(C["mint"]) +
        '<path d="M30 115 Q60 70 90 110 T150 105" stroke="#FFF8EC" stroke-width="4" stroke-dasharray="6 7" fill="none"/>'
        '<rect x="40" y="95" width="10" height="25" rx="3" fill="#E8776A"/><rect x="90" y="85" width="10" height="25" rx="3" fill="#E8776A"/>'
        '<rect x="135" y="95" width="10" height="25" rx="3" fill="#E8776A"/>'
        '<circle cx="160" cy="105" r="15" fill="#FFF8EC" stroke="#24364B" stroke-width="3"/>',
    "shoot": _bg(C["mint"]) +
        '<rect x="90" y="35" width="90" height="70" fill="none" stroke="#FFF8EC" stroke-width="6"/>'
        '<path d="M100 45 H170 M100 60 H170 M100 75 H170 M100 90 H170 M115 35 V105 M135 35 V105 M155 35 V105" stroke="#FFF8EC" stroke-width="1.5" opacity=".7"/>'
        '<circle cx="138" cy="62" r="13" fill="#FFF8EC" stroke="#24364B" stroke-width="3"/>'
        '<path d="M30 120 Q80 110 120 72" stroke="#24364B" stroke-width="3" stroke-dasharray="5 6" fill="none"/>'
        '<rect x="20" y="125" width="170" height="8" rx="4" fill="#4FA37A"/>',
}


def illustration(name: str, height: int = 150) -> None:
    """Render a named illustration; unknown names fall back to a star badge."""
    body = _ART.get(str(name).lower().strip())
    if body is None:
        body = _bg(C["sun"]) + '<path d="M100 30l14 31 34 3-25 23 7 33-30-17-30 17 7-33-25-23 34-3z" fill="#FFF8EC"/>'
    st.markdown(_svg(body, height), unsafe_allow_html=True)


def hero(title: str, subtitle: str = "") -> None:
    """Page header banner with escaped title and subtitle."""
    t = _html.escape(str(title or ""))
    s = _html.escape(str(subtitle or ""))
    sub = f"<p>{s}</p>" if s else ""
    st.markdown(f'<div class="aj-hero"><div class="aj-star aj-float">{_STAR}</div>'
                f'<div><h1>{t}</h1>{sub}</div></div>', unsafe_allow_html=True)


def welcome_art() -> None:
    """Polished illustrated login hero: AJ's Academy on a hill at sunrise."""
    svg = """
<div class="aj-welcome"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 340" width="100%" role="img">
<defs><linearGradient id="ajsky" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#CFE8F3"/><stop offset="1" stop-color="#FFF1D6"/></linearGradient></defs>
<rect width="800" height="340" fill="url(#ajsky)"/>
<circle cx="640" cy="90" r="48" fill="#FFD37A"/><circle cx="640" cy="90" r="70" fill="#FFD37A" opacity=".25"/>
<g fill="#FFF8EC"><ellipse cx="150" cy="70" rx="55" ry="18"/><ellipse cx="190" cy="58" rx="35" ry="16"/>
<ellipse cx="480" cy="55" rx="45" ry="14"/><ellipse cx="510" cy="46" rx="28" ry="12"/></g>
<path d="M0 250 Q200 180 400 230 T800 210 V340 H0z" fill="#BFE6D3"/>
<path d="M0 285 Q250 240 520 280 T800 270 V340 H0z" fill="#4FA37A"/>
<g transform="translate(320 120)">
<rect x="0" y="50" width="160" height="90" fill="#FFF8EC"/>
<polygon points="-15,55 80,0 175,55" fill="#E8776A"/>
<rect x="68" y="90" width="26" height="50" rx="4" fill="#6C5B9E"/>
<rect x="18" y="70" width="28" height="24" rx="3" fill="#CFE8F3"/><rect x="116" y="70" width="28" height="24" rx="3" fill="#CFE8F3"/>
<path d="M80 0 V-30" stroke="#24364B" stroke-width="4"/><path d="M80 -30 h30 l-8 8 8 8 h-30z" fill="#FFD37A"/>
<text x="80" y="42" font-size="18" text-anchor="middle" font-weight="700" fill="#FFF8EC">AJ</text></g>
<g class="aj-float"><circle cx="150" cy="250" r="26" fill="#FFF8EC" stroke="#24364B" stroke-width="4"/>
<polygon points="150,238 161,246 157,259 143,259 139,246" fill="#24364B"/></g>
<g transform="translate(600 230)"><rect x="0" y="20" width="60" height="30" rx="4" fill="#3E8FB0"/>
<rect x="8" y="10" width="14" height="12" rx="3" fill="#3E8FB0"/><rect x="38" y="10" width="14" height="12" rx="3" fill="#3E8FB0"/>
<rect x="15" y="-15" width="40" height="27" rx="4" fill="#FFD37A"/></g>
<g transform="translate(240 200)"><circle r="16" fill="#FFD37A" stroke="#E0A94A" stroke-width="3"/>
<text y="6" font-size="16" text-anchor="middle" font-weight="700" fill="#9A6A1E">$</text></g>
<g transform="translate(700 180)" class="aj-float"><path d="M0 -14l4 9 10 1-7 7 2 10-9-5-9 5 2-10-7-7 10-1z" fill="#FFF8EC"/></g>
</svg></div>"""
    st.markdown(svg, unsafe_allow_html=True)


ILLUSTRATION_NAMES = tuple(_ART.keys())


def scenario_illustration(kind: str, height: int = 180) -> None:
    """Render a fixed, decorative scene for a reviewed social-practice scenario."""
    scenes = {
        "join_game": (
            _bg(C["mint"])
            + '<circle cx="100" cy="107" r="24" fill="#FFF8EC" stroke="#24364B" stroke-width="3"/>'
            + '<circle cx="58" cy="63" r="12" fill="#FFD37A"/><circle cx="142" cy="63" r="12" fill="#FFD37A"/>'
            + '<path d="M35 116q2-31 23-31t23 31M119 116q2-31 23-31t23 31" fill="#3E8FB0"/>'
            + '<path d="M88 107h24m-12-12v24" stroke="#4FA37A" stroke-width="4" stroke-linecap="round"/>'
        ),
        "confusing_words": (
            _bg(C["sky"])
            + '<circle cx="68" cy="105" r="18" fill="#FFD37A"/><circle cx="132" cy="105" r="18" fill="#BFE6D3"/>'
            + '<path d="M38 75q0-24 30-24t30 24q0 17-18 21l-2 12-14-12q-26-2-26-21z" fill="#FFF8EC" stroke="#3E8FB0" stroke-width="3"/>'
            + '<circle cx="58" cy="75" r="3" fill="#24364B"/><circle cx="68" cy="75" r="3" fill="#24364B"/><circle cx="78" cy="75" r="3" fill="#24364B"/>'
            + '<path d="M107 62h34a12 12 0 0 1 12 12v7a12 12 0 0 1-12 12h-7l-9 9v-9h-18a12 12 0 0 1-12-12v-7a12 12 0 0 1 12-12z" fill="#FFF8EC" stroke="#6C5B9E" stroke-width="3"/>'
            + '<text x="127" y="83" text-anchor="middle" font-size="18" font-weight="700" fill="#6C5B9E">?</text>'
        ),
        "taking_turns": (
            _bg(C["sand"])
            + '<rect x="47" y="88" width="48" height="34" rx="6" fill="#E8776A"/><rect x="54" y="79" width="14" height="11" rx="3" fill="#E8776A"/><rect x="75" y="79" width="14" height="11" rx="3" fill="#E8776A"/>'
            + '<rect x="105" y="88" width="48" height="34" rx="6" fill="#3E8FB0"/><rect x="112" y="79" width="14" height="11" rx="3" fill="#3E8FB0"/><rect x="133" y="79" width="14" height="11" rx="3" fill="#3E8FB0"/>'
            + '<path d="M82 56h36m-10-10 10 10-10 10" fill="none" stroke="#24364B" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
        ),
        "ask_again": (
            _bg(C["peach"])
            + '<rect x="54" y="40" width="92" height="78" rx="12" fill="#FFF8EC" stroke="#3E8FB0" stroke-width="4"/>'
            + '<path d="M72 61h54M72 78h35M72 95h43" stroke="#6C5B9E" stroke-width="5" stroke-linecap="round"/>'
            + '<circle cx="145" cy="109" r="20" fill="#FFD37A" stroke="#24364B" stroke-width="3"/>'
            + '<path d="M145 99v12m0 7v1" stroke="#24364B" stroke-width="4" stroke-linecap="round"/>'
        ),
    }
    art = scenes.get(kind, scenes["join_game"])
    labels = {
        "join_game": "Illustration of children joining a ball game",
        "confusing_words": "Illustration of a conversation with a question mark",
        "taking_turns": "Illustration of two blocks and an arrow for taking turns",
        "ask_again": "Illustration of a note and a question mark for asking again",
    }
    st.markdown(_svg(art, height, label=labels.get(kind, "Social practice scene")), unsafe_allow_html=True)
