"""Preserve the editorially maintained result post during report rebuilds.

POST.md is now the canonical text. Quantitative inputs are generated separately
by post_metrics.py; rebuilding the numerical report must not rewrite the post.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    post = ROOT / 'POST.md'
    if not post.exists() or not post.read_text().strip():
        raise FileNotFoundError('The editorially maintained POST.md is missing or empty')
    print('Kept editorial POST.md unchanged')


if __name__ == '__main__':
    main()
