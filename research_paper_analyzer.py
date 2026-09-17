import os
import time
import re
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import pymupdf
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"
NO_AFC = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)


def generate_with_retry(prompt_contents, max_retries=3, base_delay=20):
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_contents,
                config=NO_AFC,
            )
        except Exception as e:
            is_quota_error = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
            if is_quota_error and attempt < max_retries - 1:
                wait = base_delay * (attempt + 1)
                print(f"  rate limited, waiting {wait}s before retrying...")
                time.sleep(wait)
                continue
            raise


def extract_pdf_content(pdf_path, min_width=100, min_height=100):
    doc = pymupdf.open(pdf_path)
    text = ""
    images = []

    for page_num, page in enumerate(doc):
        text += page.get_text()

        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)

            if base_image["width"] < min_width or base_image["height"] < min_height:
                continue

            image_bytes = base_image["image"]
            image_filename = f"image_page{page_num}_{img_index}.png"

            with open(image_filename, "wb") as f:
                f.write(image_bytes)

            images.append(image_filename)

    return text, images


def chunk_text(text, chunk_size=100000, overlap=300):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def summmarize_chunk(chunk_data):
    index, chunk = chunk_data
    print(f"  summarizing chunk {index + 1}...")
    prompt = f"Summarize the research paper into key insights, methods, and conclusions based on this content:\n\n{chunk}"
    response = generate_with_retry(prompt)
    print(f"  done with chunk {index + 1}")
    return index, response.text


def save_report_as_pdf(report_text, extracted_images, output_path="report.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Research Paper Summary Report", styles["Title"]))
    story.append(Spacer(1, 16))

    for line in report_text.split("\n"):
        stripped = line.strip()

        if not stripped:
            story.append(Spacer(1, 8))
            continue

        heading_match = re.match(r"^#+\s*(.*)", stripped)
        bold_heading_match = re.match(r"^\*\*(.+)\*\*$", stripped)

        if heading_match:
            story.append(Paragraph(heading_match.group(1), styles["Heading2"]))
        elif bold_heading_match:
            story.append(Paragraph(bold_heading_match.group(1), styles["Heading2"]))
        else:
            clean_line = stripped.replace("**", "")
            story.append(Paragraph(clean_line, styles["Normal"]))

    if extracted_images:
        story.append(Spacer(1, 20))
        story.append(Paragraph("Extracted Images", styles["Heading2"]))
        for image_path in extracted_images:
            story.append(Paragraph(image_path, styles["Normal"]))

    doc.build(story)
    return output_path


def process_paper(pdf_path, max_workers=5):
    t0 = time.time()
    text, images = extract_pdf_content(pdf_path)
    t1 = time.time()
    print(f"PDF extraction took {t1 - t0:.1f}s")

    print("Splitting into chunks...")
    chunks = chunk_text(text)
    print(f"{len(chunks)} chunk(s) to summarize, {len(images)} image(s) extracted")

    print("Summarizing text...")
    t2 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(summmarize_chunk, enumerate(chunks)))
    results.sort(key=lambda r: r[0])
    summaries = [text for _, text in results]
    t3 = time.time()
    print(f"Text summarization took {t3 - t2:.1f}s")

    final_summary = "\n\n".join(summaries)

    return {
        "text_summary": final_summary,
        "extracted_images": images
    }


def generate_final_report(results):
    prompt = f"""
    Create a structured research report with the following sections: Overview, Methods, and Key Points.

    Text summary:
    {results["text_summary"]}
    """

    response = generate_with_retry(prompt)
    return response.text


if __name__ == "__main__":
    pdf_path = "demo.pdf"
    start_time = time.time()

    results = process_paper(pdf_path)

    t_report_start = time.time()
    report = generate_final_report(results)
    t_report_end = time.time()
    print(f"Final report generation took {t_report_end - t_report_start:.1f}s")

    print("\nFINAL REPORT:\n")
    print(report)

    pdf_output_path = save_report_as_pdf(report, results["extracted_images"])
    print(f"\nSaved report to {pdf_output_path}")

    print(f"\nTotal time: {time.time() - start_time:.1f}s")