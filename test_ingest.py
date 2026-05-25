from unittest.mock import patch

with patch("opensearchpy.OpenSearch"), patch("sentence_transformers.SentenceTransformer"):
    from ingest import chunk_text, get_links
    from bs4 import BeautifulSoup


def test_chunk_text_small():
    chunks = chunk_text("hello world", size=300, overlap=30)
    assert len(chunks) == 1
    assert chunks[0] == "hello world"


def test_chunk_text_boundary():
    words = " ".join(["word"] * 300)
    chunks = chunk_text(words, size=300, overlap=30)
    assert len(chunks) == 2
    assert len(chunks[0].split()) == 300
    assert len(chunks[1].split()) <= 300


def test_chunk_text_overlap():
    words = " ".join(["word"] * 450)
    chunks = chunk_text(words, size=300, overlap=30)
    assert len(chunks) == 2
    first = chunks[0].split()
    second = chunks[1].split()
    assert len(first) == 300
    assert len(second) <= 300


def test_chunk_text_empty():
    chunks = chunk_text("", size=300, overlap=30)
    assert chunks == []


def test_get_links_filters_external():
    html = """
    <a href="https://other.com/page">external</a>
    <a href="https://www.ercot.com/page">internal</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    links, pdfs, docx, xlsx = get_links("https://www.ercot.com", soup)
    assert "https://other.com/page" not in links
    assert "https://www.ercot.com/page" in links


def test_get_links_routes_file_types():
    html = """
    <a href="/doc.pdf">pdf</a>
    <a href="/sheet.xlsx">xlsx</a>
    <a href="/report.docx">docx</a>
    <a href="/page">html</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    links, pdfs, docx, xlsx = get_links("https://www.ercot.com", soup)
    assert "https://www.ercot.com/doc.pdf" in pdfs
    assert "https://www.ercot.com/sheet.xlsx" in xlsx
    assert "https://www.ercot.com/report.docx" in docx
    assert "https://www.ercot.com/page" in links


def test_get_links_strips_fragment():
    html = '<a href="/page#section">link</a>'
    soup = BeautifulSoup(html, "html.parser")
    links, pdfs, docx, xlsx = get_links("https://www.ercot.com", soup)
    assert "https://www.ercot.com/page#section" not in links
    assert "https://www.ercot.com/page" in links


def test_get_links_skips_media_extensions():
    html = """
    <a href="/image.png">png</a>
    <a href="/archive.zip">zip</a>
    <a href="/photo.jpg">jpg</a>
    <a href="/video.mp4">mp4</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    links, pdfs, docx, xlsx = get_links("https://www.ercot.com", soup)
    assert len(links) == 0
