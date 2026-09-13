import hashlib
import io
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


INVITE_PREVIEW_VERSION = 1
INVITE_PREVIEW_SIZE = (1200, 630)
INVITE_PREVIEW_ALT = "Пригласительный билет Dear Editors. Редакция приглашает к чтению внутреннего издания."

PAPER = "#f3f0e9"
INK = "#14110e"
INK_SOFT = "#575049"
RUBRIC = "#8e3517"
RULE = "#c9c2b4"


def invite_reference(invitation) -> str:
    digest = hashlib.blake2s(
        invitation.token.bytes,
        digest_size=4,
        person=b"de-inv",
    ).digest()
    value = int.from_bytes(digest, "big")
    series = value % 100
    number = (value // 100) % 10_000
    return f"DE-I-{series:02d}-{number:04d}"


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

    # Pillow can resolve the DejaVu family by name on most development systems.
    fallback_name = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"
    try:
        return ImageFont.truetype(fallback_name, size=size)
    except OSError:
        return ImageFont.load_default(size=size)


def render_invite_preview(invitation) -> bytes:
    image = Image.new("RGB", INVITE_PREVIEW_SIZE, PAPER)
    draw = ImageDraw.Draw(image)

    title_font = _font(62, bold=True)
    label_font = _font(21, bold=True)
    serial_font = _font(72, bold=True)
    body_font = _font(30)
    small_font = _font(20)

    draw.rectangle((62, 54, 1138, 576), outline=INK, width=3)
    draw.rectangle((76, 68, 1124, 562), outline=RULE, width=1)

    draw.text((104, 92), "Dear Editors", fill=INK, font=title_font)
    draw.text((106, 168), "ВНУТРЕННЕЕ ИЗДАНИЕ", fill=INK_SOFT, font=label_font)
    draw.text((778, 110), "ПРИГЛАШЕНИЕ РЕДАКЦИИ", fill=RUBRIC, font=label_font)

    draw.line((104, 226, 1096, 226), fill=RULE, width=2)
    draw.text((106, 267), "ПРИГЛАСИТЕЛЬНЫЙ БИЛЕТ", fill=RUBRIC, font=label_font)
    draw.text((104, 306), invite_reference(invitation), fill=INK, font=serial_font)

    draw.text(
        (106, 414),
        "Редакция приглашает к чтению внутреннего издания.",
        fill=INK,
        font=body_font,
    )
    draw.line((104, 485, 1096, 485), fill=RULE, width=2)
    draw.text((106, 514), "ПО ПРИГЛАШЕНИЯМ РЕДАКЦИИ", fill=INK_SOFT, font=small_font)
    draw.text((767, 514), "Ссылка дает однократный доступ.", fill=INK_SOFT, font=small_font)

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
