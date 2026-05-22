import requests
import pdfplumber
import io
from bs4 import BeautifulSoup
from opensearchpy import OpenSearch
from urllib.parse import urljoin, urlparse
from sentence_transformers import SentenceTransformer
import pytesseract
from pdf2image import convert_from_bytes

client = OpenSearch(hosts=["http://localhost:9200"])
model = SentenceTransformer("all-MiniLM-L6-v2")

START_URL = "https://www.ercot.com"
MAX_PAGES = 200

def reset_index():
    if client.indices.exists(index="docs"):
        client.indices.delete(index="docs")
        print("Deleted old index")
    client.indices.create(index="docs", body={
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "title":     { "type": "text" },
                "body":      { "type": "text" },
                "url":       { "type": "keyword" },
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 384
                }
            }
        }
    })
    print("Created fresh index with kNN enabled")

def get_links(url, soup):
    html_links = set()
    pdf_links = set()
    base_domain = urlparse(START_URL).netloc

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(url, href)
        parsed = urlparse(full_url)

        if parsed.netloc != base_domain:
            continue

        clean_url = full_url.split("#")[0]

        if clean_url.endswith(".pdf"):
            pdf_links.add(clean_url)
        elif not any(clean_url.endswith(ext) for ext in [".zip", ".xlsx", ".png", ".jpg"]):
            html_links.add(clean_url)

    return html_links, pdf_links

def fetch_page(url):
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style"]):
        tag.decompose()
    title = soup.title.string if soup.title else url
    body = soup.get_text(separator=" ", strip=True)
    return title, body, soup

def chunk_text(text, size=300, overlap=30):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        chunks.append(chunk)
        i += size - overlap
    return chunks

def index_chunks(title, chunks, url):
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        embedding = model.encode(chunk).tolist()
        doc = {
            "title":     f"{title} (part {i+1})",
            "body":      chunk,
            "url":       url,
            "embedding": embedding
        }
        client.index(index="docs", body=doc)

def ingest_url(url):
    title, body, soup = fetch_page(url)
    chunks = chunk_text(body)
    index_chunks(title, chunks, url)
    return soup

def ingest_pdf(url):
    print(f"  → reading PDF: {url}")
    response = requests.get(url, timeout=30)

    # load the PDF from memory instead of saving to disk
    pdf_file = io.BytesIO(response.content)

    with pdfplumber.open(pdf_file) as pdf:
        title = url.split("/")[-1].replace(".pdf", "")
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + " "

    # if pdfplumber found nothing, fall back to OCR
    if not full_text.strip():
        print(f"  → no text found, trying OCR...")
        images = convert_from_bytes(response.content)
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            if text:
                full_text += text + " "
            print(f"  → OCR processed page {i+1}/{len(images)}")

    if not full_text.strip():
        print(f"  → no text found even after OCR, skipping")
        return

    chunks = chunk_text(full_text)
    index_chunks(title, chunks, url)
    print(f"  → indexed {len(chunks)} chunks from PDF")

def crawl():
    visited = set()
    queue = [START_URL]

    while queue and len(visited) < MAX_PAGES:
        url = queue.pop(0)

        if url in visited:
            continue

        try:
            print(f"[{len(visited)+1}/{MAX_PAGES}] Crawling {url}")

            if url.endswith(".pdf"):
                ingest_pdf(url)
            else:
                soup = ingest_url(url)
                new_links, new_pdfs = get_links(url, soup)

                for link in new_links:
                    if link not in visited and link not in queue:
                        queue.append(link)

                for pdf in new_pdfs:
                    if pdf not in visited and pdf not in queue:
                        queue.append(pdf)

            visited.add(url)

        except Exception as e:
            print(f"  → skipping {url}: {e}")
            continue

    print(f"\nDone! Crawled {len(visited)} pages.")

if __name__ == "__main__":
    reset_index()
    crawl()