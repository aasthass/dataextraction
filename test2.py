import fitz  # PyMuPDF
import re
from pathlib import Path

# === Patterns ===
SECTION_RE = re.compile(r"^(\d+)\s+([A-Z][^\n]+)$")
SUBSECTION_RE = re.compile(r"^(\d+\.\d+)\s+([A-Z][^\n]+)$")

# === Filters ===
JUNK_LINES = {"Reprint 2025-26", "India and the Contemporary World", "Nationalism in Europe"}
SKIP_PHRASES = [
    "Discuss", "Activity", "Write in brief", "Project", "Describe", "What does", "Explain",
    "Summarise", "In what way", "Imagine", "Look at", "Find out", "Compare", "Examine",
    "Comment on", "Suggest", "Create", "Box", "Source", "Map", "Figure", "Fig.",
    "Answer:", "Questions", "New words", "Read the text carefully"
]

# === Smart Paragraph Merge Function ===
def smart_merge_lines(text):
    lines = text.splitlines()
    merged = []
    buffer = ""
    for line in lines:
        if not line.strip():
            continue
        if buffer and not buffer.endswith(('.', '!', '?', '.”', '?”', '!”')):
            buffer += ' ' + line.strip()
        else:
            if buffer:
                merged.append(buffer.strip())
            buffer = line.strip()
    if buffer:
        merged.append(buffer.strip())
    return "\n\n".join(merged)

import textwrap

import textwrap

def clean_and_format(text_lines):
    paragraphs = []
    buffer = []
    skip_next = False
    first_line = True

    for i in range(len(text_lines)):
        line = text_lines[i].strip()

        # Skip empty and junk
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

        # Title line logic
        if first_line:
            paragraphs.append(line)
            paragraphs.append("")  # blank line after section title
            first_line = False
            continue

        # Smart paragraph detection
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

    # Final flush
    if buffer:
        para = " ".join(buffer).strip()
        wrapped = textwrap.fill(para, width=100)
        paragraphs.append(wrapped)

    return "\n\n".join(paragraphs)


# === Main Extraction Function ===
def extract_pdf_structure(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    lines = "\n".join(page.get_text() for page in doc).split("\n")

    current_section = None
    current_subsection = None
    structure = {}
    intro_buffer = []
    section_buffer = []
    subsection_buffer = []
    pending_subsections = []

    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        lc = clean.lower()
        if clean in JUNK_LINES or clean.isdigit():
            continue
        if any(skip in lc for skip in SKIP_PHRASES):
            continue
        if clean.isupper() and len(clean) < 30:
            continue

        # Subsection
        subsection_match = SUBSECTION_RE.match(clean)
        if subsection_match:
            subsection_id = subsection_match.group(1)
            subsection_title = subsection_match.group(2)
            subsection_parent = subsection_id.split(".")[0]

            if current_section is None or not current_section.startswith(subsection_parent + " "):
                pending_subsections.append((subsection_id, subsection_title, subsection_buffer.copy()))
                subsection_buffer.clear()
                current_subsection = None
                continue

            if current_subsection and subsection_buffer:
                key = f"{current_section}/{current_subsection}"
                structure.setdefault(key, []).append(subsection_buffer.copy())
                subsection_buffer.clear()

            if section_buffer:
                key = f"{current_section}"
                structure.setdefault(key, []).append(section_buffer.copy())
                section_buffer.clear()

            current_subsection = f"{subsection_id} {subsection_title}"
            subsection_buffer.append(current_subsection)
            print(f"  🔹 Subsection: {current_subsection}")
            continue

        # Section
        section_match = SECTION_RE.match(clean)
        if section_match:
            if current_subsection and subsection_buffer:
                key = f"{current_section}/{current_subsection}"
                structure.setdefault(key, []).append(subsection_buffer.copy())
                subsection_buffer.clear()

            if current_section and section_buffer:
                key = f"{current_section}"
                structure.setdefault(key, []).append(section_buffer.copy())
                section_buffer.clear()

            current_section = f"{section_match.group(1)} {section_match.group(2)}"
            current_subsection = None
            section_buffer.append(current_section)
            print(f"\n📘 Section: {current_section}")

            parent = section_match.group(1)
            to_restore = [ps for ps in pending_subsections if ps[0].split('.')[0] == parent]
            for sid, stitle, sbuf in to_restore:
                key = f"{current_section}/{sid} {stitle}"
                structure.setdefault(key, []).append(sbuf)
                print(f"  🔹 (Restored) Subsection: {sid} {stitle}")
            pending_subsections = [ps for ps in pending_subsections if ps[0].split('.')[0] != parent]
            continue

        # Route content
        if current_section is None:
            intro_buffer.append(clean)
        elif current_subsection:
            subsection_buffer.append(clean)
        else:
            section_buffer.append(clean)

    # Final flush
    if current_subsection and subsection_buffer:
        key = f"{current_section}/{current_subsection}"
        structure.setdefault(key, []).append(subsection_buffer.copy())
    elif current_section and section_buffer:
        key = f"{current_section}"
        structure.setdefault(key, []).append(section_buffer.copy())

    # Write to disk
    base_path = Path(output_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    if intro_buffer:
        intro_dir = base_path / "Introduction"
        intro_dir.mkdir(parents=True, exist_ok=True)
        with open(intro_dir / "text.txt", "w", encoding="utf-8") as f:
            f.write(clean_and_format(intro_buffer))

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

    print("\n✅ Extraction complete! Check the 'result' folder.\n")

# === Run It ===
if __name__ == "__main__":
    extract_pdf_structure("/Users/aasthasisodia/Downloads/pdfextraction/jess302.pdf", "result")
