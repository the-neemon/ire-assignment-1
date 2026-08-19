#!/usr/bin/env bash
# Renders DESIGN_NOTE.md -> design_note_c1.pdf (the Moodle deliverable, <=4 pages).
# 1.5cm/10pt is what fits the content at 4 pages; check the page count after editing.
set -euo pipefail
# Run from the repo root: the venv lives there, the note lives here.
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import pypandoc
pypandoc.convert_file('deliverable/DESIGN_NOTE.md', 'pdf',
    outputfile='deliverable/design_note_c1.pdf',
    extra_args=['--pdf-engine=xelatex', '-V', 'geometry:margin=1.5cm',
                '-V', 'fontsize=10pt', '-V', 'colorlinks=true'])
PY
pdfinfo deliverable/design_note_c1.pdf | awk '/^Pages/{print "design_note_c1.pdf:", $2, "pages"; if ($2>4) print "  WARNING: over the 4-page limit"}'
