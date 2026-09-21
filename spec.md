Completely empty folder, just uv scaffold.

Install:
- flask via uv
- niceties for web, via cdn in html template:
    - vue
    - lucide, tailwind, daisy (use this for style and icons, avoid manual styles unless unavoidable)
    - use jsdoc for typing js code w/o a build step

## Point of this App

- track sources (e.g. academic literature, web links, book) based on plaintext json on disk
- add affordances to quickly add, find and edit sources

## Data Model

one source=one json file. each file:

`key`: str, required, the slug (=valid bibtex key) the source is uniquely referred by
`title`: str, canonical human-readable titles
`aliases`: str[], alternative ways to refer to the source
- *full valid set of biblatex properties*, well-typed

## Pages

### Settings

set the path on disk where the json files live.
we go here automatically if path is not set

### Form to edit/add sources

Form with nice UX to edit all the props. 
Entails things like 
- automatically adding a new empty field when alias fields are all filled
- correct input fields for e.g. numeric inputs or dropdowns

### List

main/start view.

First, list of icon-only button with core functions, for now:
- new source
- add from bibtex (reads the clipboard, if valid bibtex, create accordingly)

tight list (I think daisy dense table is appropriate) of sources

## Misc

- Add brief/tight README.
- Add a section on how to add this as "app" to Ubuntu/Fedora (such as that it can be opened via application search/pinned to dock)
- move/utilize icons from icons/ for stuff like favicon and desktop icon
- Utilize libraries when possible, especially bibtex stuff
- I'd like to oriented around the biblatex style, since it's superior, but I think we need to support bibtex also. Deal with it as well as you csan.