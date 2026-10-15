"""Readable UI typography contract, without touching the locked PanViz figure."""
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
EDITOR = (ROOT / "editor.html").read_text(encoding="utf-8")


def _rgb(hex_color):
    return tuple(int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _luminance(color):
    def linearize(component):
        return component / 12.92 if component <= 0.04045 else (
            (component + 0.055) / 1.055
        ) ** 2.4
    red, green, blue = _rgb(color)
    return 0.2126 * linearize(red) + 0.7152 * linearize(green) + 0.0722 * linearize(blue)


def _contrast(foreground, background):
    top, bottom = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (top + 0.05) / (bottom + 0.05)


def test_theme_is_consistent_and_has_legible_text_colors():
    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())["theme"]
    assert theme["base"] == "light"
    assert theme["font"] == "sans serif"
    assert _contrast(theme["textColor"], theme["backgroundColor"]) >= 4.5
    assert _contrast("#ffffff", theme["primaryColor"]) >= 4.5


def test_text_contrast_exceeds_wcag_aa_normal_text_threshold():
    pairs = {
        "body": ("#23364d", "#ffffff"),
        "form label": ("#1b3553", "#ffffff"),
        "muted helper text": ("#40536b", "#ffffff"),
        "PDB badges": ("#294664", "#eef4fb"),
        "primary action": ("#ffffff", "#194c88"),
        "secondary action": ("#193f70", "#edf4fc"),
        "editor toolbar label": ("#304b68", "#ffffff"),
        "editor table cell": ("#24384f", "#ffffff"),
        "editor status": ("#28425e", "#f0f5fb"),
    }
    for name, (foreground, background) in pairs.items():
        assert _contrast(foreground, background) >= 4.5, name


def test_streamlit_typography_has_explicit_weights_and_focus_visibility():
    assert "PanViz reading hierarchy:" in APP
    assert '[data-testid="stWidgetLabel"] p' in APP
    assert 'font-weight:700!important' in APP
    assert '[data-testid="stRadio"] label p' in APP
    assert 'font-weight:600!important' in APP
    assert '[data-testid="stCaptionContainer"]' in APP
    assert 'button[data-testid="stBaseButton-primary"]' in APP
    assert 'button[data-testid="stBaseButton-secondary"]' in APP
    assert "button:focus-visible" in APP


def test_embedded_editor_controls_have_distinct_typography_from_scientific_svg():
    assert "UI typography contract for the embedded editor" in EDITOR
    added = EDITOR.split("/* UI typography contract for the embedded editor", 1)[1].split(
        "</style>", 1
    )[0]
    assert "#pv-toolbar button" in added
    assert "#pv-style-grid h4" in added
    assert "#pv-style-row label" in added
    assert "#pv-interaction-table th" in added
    assert "font-weight:750" in added
    assert "focus-visible" in added
    # Avoid touching the locked publication renderer's SVG styles or outputs.
    assert "#pv-svg-canvas" not in added
    assert "svg text" not in added
    assert "svg {" not in added
    assert "moleculeLayer" not in added
