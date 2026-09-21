# Sources

Personal source tracker: one biblatex-style JSON file per source, edited through a small Flask + Vue app.

## Run

```
uv sync
uv run app.py
```

Opens http://127.0.0.1:8765. On first start, set the directory holding the JSON files (stored in `~/.config/sources/config.json`).

## Data

`<dir>/<key>.json`, with `key` (biblatex key), `entrytype`, `title`, `aliases`, and any biblatex field. Names are `[{family, given, prefix, suffix}]`, lists (publisher, location, …) are string arrays, dates are ISO (`2020-05-17`). BibTeX pasted via the clipboard button is converted to this model (`journal` → `journaltitle`, `year`+`month` → `date`, `phdthesis` → `thesis`, …); unmapped fields land in `extra`.

## Add as desktop app (Ubuntu / Fedora, GNOME)

```
mkdir -p ~/.local/share/icons/hicolor/512x512/apps ~/.local/share/applications
cp static/icons/android-chrome-512x512.png ~/.local/share/icons/hicolor/512x512/apps/sources.png
sed "s|/ABS/PATH/TO/sources|$PWD|g" sources.desktop > ~/.local/share/applications/sources.desktop
update-desktop-database ~/.local/share/applications
```

"Sources" then shows up in application search and can be pinned to the dock. `uv` must be on the desktop session's `PATH` (`~/.local/bin`); otherwise put its absolute path in `Exec`.

## Test

```
uv run pytest
```
