# portfolio

## How RenderCV works (quick explanation)

Yes — your understanding is mostly correct.

RenderCV typically follows this flow:

1. **Load CV input data** from a YAML file.
2. **Parse and validate** that YAML into Python data models/objects.
3. **Render templates** (usually LaTeX/Jinja-based) using those objects.
4. **Generate output files** such as a CV document (e.g., `.tex`) and then a **PDF**.

## How to combine it with other projects

The easiest integration pattern is:

- Keep your source data in your main app (DB/API/JSON).
- Convert/export that data into RenderCV’s expected YAML schema.
- Run RenderCV as a generation step to produce the final CV/PDF.

So in short: **YAML -> Python objects -> rendered document -> PDF** is the right mental model.
