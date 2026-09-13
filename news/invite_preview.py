import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


INVITE_PREVIEW_VERSION = 5
INVITE_PREVIEW_SIZE = (1200, 630)
INVITE_PREVIEW_ALT = "Пригласительный билет Dear Editors"
INVITE_PREVIEW_CONTENT_TYPE = "image/jpeg"

PAPER = "#f3f0e9"
INK = "#14110e"
INK_SOFT = "#8a8278"
RUBRIC = "#8e3517"
RULE = "#c9c2b4"


def _invite_numbers(invitation) -> tuple[int, int]:
    digest = hashlib.blake2s(
        invitation.token.bytes,
        digest_size=4,
        person=b"de-inv",
    ).digest()
    value = int.from_bytes(digest, "big")
    return value % 100, (value // 100) % 10_000


def invite_series(invitation) -> str:
    return "DE-I"


def invite_reference(invitation) -> str:
    series, number = _invite_numbers(invitation)
    return f"{series:02d}-{number:04d}"


def _font_candidates(*, bold: bool) -> list[Path]:
    if bold:
        names = (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
            Path("C:/Windows/Fonts/georgiab.ttf"),
            Path("C:/Windows/Fonts/timesbd.ttf"),
            Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf"),
        )
    else:
        names = (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
            Path("C:/Windows/Fonts/georgia.ttf"),
            Path("C:/Windows/Fonts/times.ttf"),
            Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
        )
    return list(names)


def _font(size: int, *, bold: bool = False):
    for candidate in _font_candidates(bold=bold):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)

    fallback_name = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"
    try:
        return ImageFont.truetype(fallback_name, size=size)
    except OSError:
        return ImageFont.load_default(size=size)


def _spaced_width(draw, text: str, font, spacing: float) -> float:
    if not text:
        return 0
    widths = [draw.textlength(char, font=font) for char in text]
    return sum(widths) + spacing * (len(text) - 1)


def _draw_spaced_text(draw, xy, text: str, *, font, fill, spacing: float):
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + spacing


def _draw_centered_spaced_text(draw, y, text: str, *, font, fill, spacing: float):
    width = _spaced_width(draw, text, font, spacing)
    _draw_spaced_text(
        draw,
        ((INVITE_PREVIEW_SIZE[0] - width) / 2, y),
        text,
        font=font,
        fill=fill,
        spacing=spacing,
    )


def _draw_invite_preview(invitation) -> Image.Image:
    image = Image.new("RGB", INVITE_PREVIEW_SIZE, PAPER)
    draw = ImageDraw.Draw(image)

    title_font = _font(38, bold=True)
    sub_font = _font(15)
    series_font = _font(16, bold=True)
    kind_font = _font(20, bold=True)
    serial_font = _font(124, bold=True)
    foot_font = _font(22)

    draw.rectangle((1, 1, 1198, 628), outline=RULE, width=2)
    draw.rectangle((28, 28, 1171, 601), outline=INK, width=2)

    draw.text((60, 52), "Dear Editors", fill=INK, font=title_font)
    _draw_spaced_text(
        draw,
        (60, 101),
        "ВНУТРЕННЕЕ ИЗДАНИЕ",
        font=sub_font,
        fill=INK_SOFT,
        spacing=2.4,
    )

    series_text = f"СЕРИЯ {invite_series(invitation)}"
    series_width = _spaced_width(draw, series_text, series_font, 2.6)
    _draw_spaced_text(
        draw,
        (1140 - series_width, 56),
        series_text,
        font=series_font,
        fill=RUBRIC,
        spacing=2.6,
    )

    _draw_centered_spaced_text(
        draw,
        176,
        "ПРИГЛАСИТЕЛЬНЫЙ БИЛЕТ",
        font=kind_font,
        fill=RUBRIC,
        spacing=4.4,
    )

    reference = invite_reference(invitation)
    reference_width = draw.textlength(reference, font=serial_font)
    mark_diameter = 22
    mark_gap = 10
    group_width = reference_width + mark_gap + mark_diameter
    number_x = (INVITE_PREVIEW_SIZE[0] - group_width) / 2
    number_y = 218
    draw.text((number_x, number_y), reference, fill=INK, font=serial_font)

    bbox = draw.textbbox((number_x, number_y), reference, font=serial_font)
    mark_left = bbox[2] + mark_gap
    mark_center_y = number_y + 79
    draw.ellipse(
        (
            mark_left,
            mark_center_y - mark_diameter / 2,
            mark_left + mark_diameter,
            mark_center_y + mark_diameter / 2,
        ),
        fill=RUBRIC,
    )

    expires = invitation.expires_at.astimezone()
    footer = f"Действует до {expires:%d.%m.%Y}. Однократный доступ."
    footer_width = draw.textlength(footer, font=foot_font)
    draw.text(
        ((INVITE_PREVIEW_SIZE[0] - footer_width) / 2, 540),
        footer,
        fill="#5a534a",
        font=foot_font,
    )

    return image


def render_invite_preview(invitation) -> bytes:
    image = _draw_invite_preview(invitation)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85, optimize=True)
    return output.getvalue()


def render_invite_preview_png(invitation) -> bytes:
    """Keep already-issued v3/v4 PNG URLs valid while v5 uses JPEG."""
    image = _draw_invite_preview(invitation)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True, compress_level=9)
    return output.getvalue()
