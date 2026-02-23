from __future__ import annotations

from pathlib import Path

PAGE_WIDTH = 612
PAGE_HEIGHT = 792


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(path: Path, title: str, boxes: list[dict], lines: list[tuple]) -> None:
    content = []
    content.append("0.8 w")
    content.append("0 0 0 RG")
    content.append(f"BT /F1 18 Tf 50 750 Td ({_escape(title)}) Tj ET")

    for box in boxes:
        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        text = _escape(box["text"])
        content.append(f"{x} {y} {w} {h} re S")
        content.append(f"BT /F1 12 Tf {x + 8} {y + h - 18} Td ({text}) Tj ET")

    for x1, y1, x2, y2 in lines:
        content.append(f"{x1} {y1} m {x2} {y2} l S")

    stream = "\n".join(content)
    stream_bytes = stream.encode("utf-8")

    objects = []
    objects.append("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    )
    objects.append(
        f"4 0 obj << /Length {len(stream_bytes)} >> stream\n{stream}\nendstream\nendobj\n"
    )
    objects.append("5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj.encode("utf-8")

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("utf-8")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("utf-8")

    pdf += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("utf-8")

    path.write_bytes(pdf)


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "docs"
    root.mkdir(parents=True, exist_ok=True)

    architecture_boxes = [
        {"x": 60, "y": 640, "w": 220, "h": 60, "text": "React Frontend (Vite + Tailwind)"},
        {"x": 330, "y": 640, "w": 220, "h": 60, "text": "FastAPI Backend"},
        {"x": 60, "y": 540, "w": 220, "h": 60, "text": "Firebase Auth"},
        {"x": 330, "y": 540, "w": 220, "h": 60, "text": "ML Pipeline"},
        {"x": 60, "y": 440, "w": 220, "h": 60, "text": "Local Storage"},
        {"x": 330, "y": 440, "w": 220, "h": 60, "text": "Graph Engine"},
    ]

    architecture_lines = [
        (280, 670, 330, 670),
        (170, 640, 170, 600),
        (440, 640, 440, 600),
        (170, 540, 170, 500),
        (440, 540, 440, 500),
        (280, 470, 330, 470),
    ]

    flow_boxes = [
        {"x": 70, "y": 650, "w": 460, "h": 50, "text": "1. Capture Transaction + Profile"},
        {"x": 70, "y": 570, "w": 460, "h": 50, "text": "2. Feature Engineering"},
        {"x": 70, "y": 490, "w": 460, "h": 50, "text": "3. Anomaly + Supervised + Graph Risk"},
        {"x": 70, "y": 410, "w": 460, "h": 50, "text": "4. Weighted Risk Score"},
        {"x": 70, "y": 330, "w": 460, "h": 50, "text": "5. Explainable Output + Alerts"},
    ]

    flow_lines = [
        (300, 650, 300, 620),
        (300, 570, 300, 540),
        (300, 490, 300, 460),
        (300, 410, 300, 380),
    ]

    _build_pdf(root / "securepay-architecture.pdf", "SecurePay AI Architecture", architecture_boxes, architecture_lines)
    _build_pdf(root / "ai-flowchart.pdf", "SecurePay AI Flowchart", flow_boxes, flow_lines)


if __name__ == "__main__":
    main()
