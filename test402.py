import fitz  # PyMuPDF
import re
from pathlib import Path
import textwrap

# === MANUAL HEADINGS ===
WHITELISTED_HEADINGS = {
    "WHAT DEVELOPMENT PROMISES — DIFFERENT PEOPLE, DIFFERENT GOALS",
    "INCOME AND OTHER GOALS",
    "NATIONAL DEVELOPMENT",
    "HOW TO COMPARE DIFFERENT COUNTRIES OR STATES?",
    "INCOME AND OTHER CRITERIA",
    "PUBLIC FACILITIES"

}


JUNK_LINES = {
    "Reprint 2025-26", "India and the Contemporary World", "Nationalism in Europe","Political Parties","UNDERSTANDING ECONOMIC DEVELOPMENT","DEVELOPMENT"
}

SKIP_PHRASES = [
    "Discuss", "Activity", "Write in brief", "Project", "Describe", "What does", "Explain",
    "Summarise", "In what way", "Imagine", "Look at", "Find out", "Compare", "Examine",
    "Comment on", "Suggest", "Create", "Box", "Source", "Map", "Figure", "Fig.",
    "Answer:", "Questions", "New words", "Read the text carefully"
]

def clean_and_format(text_lines):
    paragraphs = []
    buffer = []
    skip_next = False
    first_line = True

    for i in range(len(text_lines)):
        line = text_lines[i].strip()
        if not line:
            continue
        if any(line.lower().startswith(p.lower()) for p in SKIP_PHRASES):
            skip_next = True
            continue
        if skip_next:
            skip_next = False
            continue
        if line.lower() in {j.lower() for j in JUNK_LINES}:
            continue
        if line.isupper() and len(line) < 30:
            continue
        if line.lower().startswith(("fig.", "figure", "map")):
            continue

        line = re.sub(r"\s{2,}", " ", line)

        if first_line:
            paragraphs.append(line)
            paragraphs.append("")  # blank line after section title
            first_line = False
            continue

        if buffer:
            prev_line = buffer[-1]
            if prev_line.endswith('.') and line and line[0].isupper():
                para = " ".join(buffer).strip()
                wrapped = textwrap.fill(para, width=100)
                paragraphs.append(wrapped)
                buffer = [line]
            else:
                buffer.append(line)
        else:
            buffer.append(line)

    if buffer:
        para = " ".join(buffer).strip()
        wrapped = textwrap.fill(para, width=100)
        paragraphs.append(wrapped)

    return "\n\n".join(paragraphs)


def extract_pdf_structure(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    lines = "\n".join(page.get_text() for page in doc).split("\n")

    base_path = Path(output_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    current_section = "Chapter_1_Power_Sharing"
    current_subsection = "Introduction"
    structure = {}
    buffer = []

    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        if clean in JUNK_LINES or clean.isdigit():
            continue
        if any(skip in clean.lower() for skip in SKIP_PHRASES):
            continue
        if clean in WHITELISTED_HEADINGS:
            if buffer:
                key = f"{current_section}/{current_subsection}"
                structure.setdefault(key, []).append(buffer.copy())
                buffer.clear()
            current_subsection = clean
            buffer.append(clean)
            print(f"📘 Subsection: {current_subsection}")
            continue
        buffer.append(clean)

    if buffer:
        key = f"{current_section}/{current_subsection}"
        structure.setdefault(key, []).append(buffer.copy())

    for key, blocks in structure.items():
        path = base_path
        for part in key.split("/"):
            safe = re.sub(r"[^\w\s-]", "", part).strip().replace(" ", "_")
            path = path / safe
        path.mkdir(parents=True, exist_ok=True)
        all_lines = []
        for block in blocks:
            all_lines.extend(block)
        with open(path / "text.txt", "w", encoding="utf-8") as f:
            f.write(clean_and_format(all_lines))

    print(f"\n✅ Extraction complete! Check the '{output_dir}' folder.")

# === Run It ===
if __name__ == "__main__":
    extract_pdf_structure("/Users/aasthasisodia/Downloads/pdfextraction/jess201.pdf", "CHAPTER I_DEVELOPMENT")