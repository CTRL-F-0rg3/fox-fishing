#!/usr/bin/env bash
set -euo pipefail
VERSION="${1:-v1.0.0}"
cd "$(dirname "$0")/.."
source venv/bin/activate

echo "==> Generating PNG icon"
python -c "import cairosvg; cairosvg.svg2png(url='assets/fox-fishing.svg', write_to='assets/fox-fishing.png', output_width=256, output_height=256)"

echo "==> Building binary with PyInstaller"
pyinstaller --clean --onefile --windowed --name fox-fishing \
  --add-data "assets:assets" \
  --collect-all cairosvg \
  --collect-all pygame \
  --icon assets/fox-fishing.png \
  main.py

echo "==> Packaging tarball"
PKG="fox-fishing-linux-${VERSION}"
rm -rf "dist/${PKG}" "dist/${PKG}.tar.gz"
mkdir -p "dist/${PKG}/bin" \
         "dist/${PKG}/share/applications" \
         "dist/${PKG}/share/icons/hicolor/scalable/apps"
cp dist/fox-fishing "dist/${PKG}/bin/"
cp assets/fox-fishing.desktop "dist/${PKG}/share/applications/"
cp assets/fox-fishing.svg "dist/${PKG}/share/icons/hicolor/scalable/apps/"
tar -czf "dist/${PKG}.tar.gz" -C dist "${PKG}"

echo "==> Uploading to GitHub"
gh release create "${VERSION}" "dist/${PKG}.tar.gz" \
  --repo CTRL-F-0rg3/fox-fishing \
  --title "Fox Fishing ${VERSION}" \
  --notes "Release ${VERSION}" 2>/dev/null || \
gh release upload "${VERSION}" "dist/${PKG}.tar.gz" \
  --repo CTRL-F-0rg3/fox-fishing --clobber

echo "Done: dist/${PKG}.tar.gz"
