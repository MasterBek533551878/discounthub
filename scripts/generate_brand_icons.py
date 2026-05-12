#!/usr/bin/env python3
"""Generate DiscountHub platform icons from one source PNG.

Expected source: square PNG, ideally 1024x1024 or larger, with the final app icon
artwork already centered and with enough safe padding.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image


ANDROID_LEGACY_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

ANDROID_FOREGROUND_SIZES = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}

IOS_ICON_FILES = {
    "Icon-App-20x20@1x.png": 20,
    "Icon-App-20x20@2x.png": 40,
    "Icon-App-20x20@3x.png": 60,
    "Icon-App-29x29@1x.png": 29,
    "Icon-App-29x29@2x.png": 58,
    "Icon-App-29x29@3x.png": 87,
    "Icon-App-40x40@1x.png": 40,
    "Icon-App-40x40@2x.png": 80,
    "Icon-App-40x40@3x.png": 120,
    "Icon-App-60x60@2x.png": 120,
    "Icon-App-60x60@3x.png": 180,
    "Icon-App-76x76@1x.png": 76,
    "Icon-App-76x76@2x.png": 152,
    "Icon-App-83.5x83.5@2x.png": 167,
    "Icon-App-1024x1024@1x.png": 1024,
}

WEB_ICON_FILES = {
    "Icon-192.png": 192,
    "Icon-512.png": 512,
    "Icon-maskable-192.png": 192,
    "Icon-maskable-512.png": 512,
}

LAUNCH_IMAGE_FILES = {
    "LaunchImage.png": 168,
    "LaunchImage@2x.png": 336,
    "LaunchImage@3x.png": 504,
}


def parse_hex_color(value: str) -> Tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError("Background color must be in #RRGGBB format.")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        255,
    )


def crop_square(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size
    size = min(width, height)
    left = (width - size) // 2
    top = (height - size) // 2
    return image.crop((left, top, left + size, top + size))


def flatten(image: Image.Image, background: Tuple[int, int, int, int]) -> Image.Image:
    image = image.convert("RGBA")
    base = Image.new("RGBA", image.size, background)
    base.alpha_composite(image)
    return base.convert("RGB")


def resize_cover(image: Image.Image, size: int, background: Tuple[int, int, int, int], *, flatten_alpha: bool = True) -> Image.Image:
    square = crop_square(image)
    resized = square.resize((size, size), Image.Resampling.LANCZOS)
    if flatten_alpha:
        return flatten(resized, background)
    return resized


def resize_with_padding(
    image: Image.Image,
    canvas_size: int,
    art_ratio: float,
    background: Tuple[int, int, int, int],
) -> Image.Image:
    square = crop_square(image)
    art_size = max(1, round(canvas_size * art_ratio))
    art = square.resize((art_size, art_size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    offset = ((canvas_size - art_size) // 2, (canvas_size - art_size) // 2)
    canvas.alpha_composite(art, offset)
    return canvas


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def update_colors_xml(path: Path, background_hex: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    color_value = background_hex.upper()
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">{color_value}</color>
    <color name="splash_background">#07153B</color>
</resources>
'''
    path.write_text(xml, encoding="utf-8")


def update_android_launch_background(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    xml = '''<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:drawable="@color/splash_background" />
</layer-list>
'''
    path.write_text(xml, encoding="utf-8")


def update_web_manifest(path: Path) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["background_color"] = "#07153B"
    data["theme_color"] = "#0B63FF"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def update_ios_launch_storyboard(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    # Deep DiscountHub blue: #07153B in sRGB decimal components.
    text = re.sub(
        r'<color key="backgroundColor"[^>]*/>',
        '<color key="backgroundColor" red="0.027" green="0.082" blue="0.231" alpha="1" colorSpace="custom" customColorSpace="sRGB"/>',
        text,
    )
    path.write_text(text, encoding="utf-8")


def copy_brand_assets(
    project_root: Path,
    app_icon: Image.Image,
    app_icon_source: Path,
    logo_full_source: Path | None,
    background: Tuple[int, int, int, int],
) -> None:
    brand_dir = project_root / "assets" / "brand"
    brand_dir.mkdir(parents=True, exist_ok=True)

    save_png(resize_cover(app_icon, 1024, background), brand_dir / "logo.png")
    save_png(resize_cover(app_icon, 1024, background), brand_dir / "app_icon_source.png")

    if logo_full_source and logo_full_source.exists():
        logo_full = Image.open(logo_full_source)
        # Keep the wordmark version mostly as-is but normalize it to PNG.
        save_png(logo_full.convert("RGBA"), brand_dir / "logo_full.png")


def generate_icons(project_root: Path, source_path: Path, logo_full_source: Path | None, background_hex: str) -> None:
    background = parse_hex_color(background_hex)
    source = Image.open(source_path)

    copy_brand_assets(project_root, source, source_path, logo_full_source, background)

    android_res = project_root / "android" / "app" / "src" / "main" / "res"
    update_colors_xml(android_res / "values" / "colors.xml", background_hex)
    update_android_launch_background(android_res / "drawable" / "launch_background.xml")
    update_android_launch_background(android_res / "drawable-v21" / "launch_background.xml")

    for folder, size in ANDROID_LEGACY_SIZES.items():
        out_dir = android_res / folder
        icon = resize_cover(source, size, background)
        save_png(icon, out_dir / "ic_launcher.png")
        save_png(icon, out_dir / "ic_launcher_round.png")

    for folder, size in ANDROID_FOREGROUND_SIZES.items():
        out_dir = android_res / folder
        foreground = resize_with_padding(source, size, 0.76, background)
        save_png(foreground, out_dir / "ic_launcher_foreground.png")

    ios_icon_dir = project_root / "ios" / "Runner" / "Assets.xcassets" / "AppIcon.appiconset"
    for filename, size in IOS_ICON_FILES.items():
        icon = resize_cover(source, size, background)
        save_png(icon, ios_icon_dir / filename)

    ios_launch_dir = project_root / "ios" / "Runner" / "Assets.xcassets" / "LaunchImage.imageset"
    for filename, size in LAUNCH_IMAGE_FILES.items():
        launch_icon = resize_with_padding(source, size, 0.62, background)
        save_png(launch_icon, ios_launch_dir / filename)
    update_ios_launch_storyboard(project_root / "ios" / "Runner" / "Base.lproj" / "LaunchScreen.storyboard")

    web_icon_dir = project_root / "web" / "icons"
    for filename, size in WEB_ICON_FILES.items():
        icon = resize_cover(source, size, background)
        save_png(icon, web_icon_dir / filename)
    save_png(resize_cover(source, 32, background), project_root / "web" / "favicon.png")
    update_web_manifest(project_root / "web" / "manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DiscountHub brand icons.")
    parser.add_argument("--project-root", required=True, help="Path to Flutter project root.")
    parser.add_argument("--app-icon-source", required=True, help="Square source PNG for app icon/mark.")
    parser.add_argument("--logo-full-source", default=None, help="Optional full wordmark logo PNG.")
    parser.add_argument("--background-color", default="#0B63FF", help="Icon background color in #RRGGBB.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    source_path = Path(args.app_icon_source).resolve()
    logo_full_source = Path(args.logo_full_source).resolve() if args.logo_full_source else None

    if not source_path.exists():
        raise FileNotFoundError(f"App icon source not found: {source_path}")

    generate_icons(project_root, source_path, logo_full_source, args.background_color)
    print("DiscountHub brand icons generated successfully.")


if __name__ == "__main__":
    main()
