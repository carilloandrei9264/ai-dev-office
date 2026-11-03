#!/usr/bin/env python3
"""WCAG contrast checker.   Usage: python contrast.py "#111827" "#ffffff"   (foreground, then background)."""
import sys


def luminance(hex_color: str) -> float:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"'{hex_color}' is not a valid hex color")
    try:
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError:
        raise ValueError(f"'{hex_color}' is not a valid hex color") from None
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(foreground_hex: str, background_hex: str) -> float:
    l1, l2 = luminance(foreground_hex), luminance(background_hex)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def check(foreground_hex: str, background_hex: str) -> str:
    """Human-readable verdict. Returns an error message (not an exception) for bad input."""
    try:
        r = ratio(foreground_hex, background_hex)
    except ValueError as e:
        return str(e)
    return (
        f"Contrast ratio {r:.2f}:1. "
        f"AA normal text (>=4.5): {'PASS' if r >= 4.5 else 'FAIL'}. "
        f"AA large text (>=3): {'PASS' if r >= 3 else 'FAIL'}. "
        f"AAA normal text (>=7): {'PASS' if r >= 7 else 'FAIL'}."
    )


def main(argv) -> int:
    if len(argv) != 3:
        print(__doc__.strip())
        return 2
    try:
        ratio(argv[1], argv[2])
    except ValueError as e:
        print(e)
        return 2
    print(check(argv[1], argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
