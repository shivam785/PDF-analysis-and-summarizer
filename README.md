# Research Paper Analyzer

A Python script that takes a research paper PDF, summarizes it using Google's Gemini API, and outputs a clean, structured PDF report.

## What It Does

1. Extracts all text and meaningful embedded images from a PDF research paper.
2. Splits the text into manageable chunks and sends them to Gemini for summarization.
3. Combines the summaries and asks Gemini to generate a structured report (Overview, Methods, Key Points).
4. Saves that report as a formatted PDF file (`report.pdf`), alongside the extracted images.

## How It Works — Step by Step

### 1. PDF Text & Image Extraction (`extract_pdf_content`)
Uses **PyMuPDF** (`pymupdf`) to open the PDF and pull out:
- All page text, concatenated into one string.
- Embedded images, saved as `.png` files. Small images (under 100x100 pixels by default) are skipped, since these are usually logos or decorative graphics rather than meaningful figures.

### 2. Chunking (`chunk_text`)
Large language models can only process a limited amount of text per request. This function splits the extracted text into overlapping chunks (default: 100,000 characters, with a 300-character overlap between chunks so context isn't lost at the boundaries). For most academic papers, this means the entire paper fits in a single chunk, minimizing the number of API calls needed.

### 3. Summarizing Each Chunk (`summmarize_chunk`)
Each chunk is sent to Gemini with a prompt asking it to summarize key insights, methods, and conclusions. Multiple chunks (when there are more than one) are summarized **in parallel** using Python's `ThreadPoolExecutor`, rather than one after another, which significantly speeds up processing for longer papers.

### 4. Retry Logic (`generate_with_retry`)
Google's Gemini API enforces rate limits (a set number of requests per minute/day, especially on the free tier). This function wraps every API call so that if a `429 RESOURCE_EXHAUSTED` (rate limit) error occurs, the script automatically waits and retries a few times with increasing delays, instead of crashing outright.

### 5. Final Report Generation (`generate_final_report`)
Once all chunk summaries are combined, one more Gemini call turns them into a polished, structured report with clear sections.

### 6. PDF Report Writing (`save_report_as_pdf`)
Uses **ReportLab** to convert the plain-text report into a properly formatted PDF: a title page, styled headings for each section, normal paragraphs for body text, and a list of extracted image filenames at the end.

## Key Terms & Libraries Used

| Term / Library | What It Is |
|---|---|
| **PyMuPDF (`pymupdf`)** | A Python library for reading, parsing, and extracting content (text, images) from PDF files. |
| **Gemini API (`google-genai`)** | Google's official SDK for calling their Gemini large language models to generate text from prompts. Replaces the now-deprecated `google-generativeai` package. |
| **`gemini-2.5-flash`** | The specific Gemini model used — a fast, lower-cost model well suited for summarization tasks. |
| **Chunking** | Splitting a large body of text into smaller pieces so it fits within a model's input limits. |
| **`ThreadPoolExecutor`** | A Python tool (from the built-in `concurrent.futures` module) that runs multiple functions concurrently using threads, instead of one at a time — used here to summarize several chunks simultaneously. |
| **Rate Limiting / 429 Errors** | APIs cap how many requests you can make in a given time window (or day, on free tiers). A `429` HTTP status code means that limit has been hit. |
| **Automatic Function Calling (AFC)** | A Gemini SDK feature that lets the model call external functions/tools automatically. It's explicitly disabled here (`NO_AFC`) since this project doesn't use tool-calling, only plain text generation. |
| **ReportLab** | A Python library for programmatically generating PDF documents, including styled text, headings, and layouts. |
| **`python-dotenv`** | Loads environment variables (like API keys) from a `.env` file, keeping secrets out of the source code. |

## Setup

1. Install dependencies:
   ```
   pip install google-genai pymupdf reportlab python-dotenv
   ```
2. Create a `.env` file in the project folder with your Gemini API key:
   ```
   GEMINI_API_KEY=your_key_here
   ```
3. Place your research paper PDF in the project folder and name it `demo.pdf` (or update the `pdf_path` variable in the script).

## Usage

```
python research_paper_analyzer.py
```

The script will print progress as it extracts, chunks, and summarizes the paper, then save the final report as `report.pdf` in the same folder.

## Notes

- Gemini's free tier has daily and per-minute request quotas. If you hit a `429` error repeatedly, check your usage at [ai.dev/rate-limit](https://ai.dev/rate-limit) or consider enabling billing for higher limits.
- Extracted images are saved to disk but are **not** sent to Gemini for analysis — they're just extracted and listed in the final report, to keep API usage and processing time low.

## License

This project is provided as-is for personal or educational use.
