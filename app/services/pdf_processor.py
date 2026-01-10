"""PDF Processing Service using PyMuPDF.

Extracts pages and text from PDF documents for the page-first reading platform.
Uses PyMuPDF (fitz) - pure Python, no system dependencies required.

Principle P1: Pages are for rendering (visual browsing).
Principle P2: Chunks are for thinking (AI understanding).
"""

import io
from collections.abc import Iterator
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image

# Resolution configurations for page rendering
RESOLUTIONS = {
    "thumbnail": {"width": 150, "quality": 70},
    "medium": {"width": 800, "quality": 85},
}


@dataclass
class PageDimensions:
    """Original page dimensions from PDF."""

    width: int
    height: int


@dataclass
class ExtractedPage:
    """Extracted page data from PDF."""

    page_number: int  # 1-indexed
    text: str
    dimensions: PageDimensions


class PDFProcessor:
    """Process PDF documents for page rendering and text extraction.

    Usage:
        processor = PDFProcessor(pdf_bytes)
        try:
            # Render a page
            jpeg_bytes = processor.render_page(1, width=800, quality=85)

            # Extract text
            text = processor.extract_text(1)

            # Get all pages with text
            for page in processor.extract_all_pages():
                print(f"Page {page.page_number}: {page.text[:100]}...")
        finally:
            processor.close()
    """

    def __init__(self, pdf_bytes: bytes):
        """Initialize processor with PDF bytes.

        Args:
            pdf_bytes: Raw PDF file bytes.

        Raises:
            ValueError: If the PDF cannot be opened.
        """
        try:
            self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {e}") from e

    @property
    def page_count(self) -> int:
        """Get total number of pages in the PDF."""
        return len(self.doc)

    def get_page_dimensions(self, page_num: int) -> PageDimensions:
        """Get original dimensions of a page.

        Args:
            page_num: Page number (1-indexed).

        Returns:
            PageDimensions with width and height.
        """
        page = self.doc[page_num - 1]  # Convert to 0-indexed
        return PageDimensions(
            width=int(page.rect.width),
            height=int(page.rect.height),
        )

    def render_page(
        self,
        page_num: int,
        width: int,
        quality: int = 85,
    ) -> bytes:
        """Render a single page to JPEG bytes.

        Args:
            page_num: Page number (1-indexed).
            width: Target width in pixels (height maintains aspect ratio).
            quality: JPEG quality (1-100).

        Returns:
            JPEG image bytes.

        Raises:
            IndexError: If page number is out of range.
        """
        if page_num < 1 or page_num > self.page_count:
            raise IndexError(f"Page {page_num} out of range (1-{self.page_count})")

        page = self.doc[page_num - 1]  # Convert to 0-indexed

        # Calculate zoom factor to achieve target width
        zoom = width / page.rect.width
        mat = fitz.Matrix(zoom, zoom)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image and save as JPEG
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)

        return buffer.getvalue()

    def render_page_resolutions(
        self,
        page_num: int,
    ) -> dict[str, bytes]:
        """Render a page at all configured resolutions.

        Args:
            page_num: Page number (1-indexed).

        Returns:
            Dictionary mapping resolution name to JPEG bytes.
        """
        result = {}
        for res_name, config in RESOLUTIONS.items():
            result[res_name] = self.render_page(
                page_num,
                width=config["width"],
                quality=config["quality"],
            )
        return result

    def extract_text(self, page_num: int) -> str:
        """Extract text from a single page.

        Args:
            page_num: Page number (1-indexed).

        Returns:
            Extracted text string.

        Raises:
            IndexError: If page number is out of range.
        """
        if page_num < 1 or page_num > self.page_count:
            raise IndexError(f"Page {page_num} out of range (1-{self.page_count})")

        page = self.doc[page_num - 1]
        return page.get_text()

    def extract_all_pages(self) -> Iterator[ExtractedPage]:
        """Extract text from all pages with metadata.

        Yields:
            ExtractedPage objects for each page.
        """
        for i in range(self.page_count):
            page = self.doc[i]
            page_num = i + 1  # Convert to 1-indexed

            yield ExtractedPage(
                page_number=page_num,
                text=page.get_text(),
                dimensions=PageDimensions(
                    width=int(page.rect.width),
                    height=int(page.rect.height),
                ),
            )

    def close(self) -> None:
        """Close the PDF document and release resources."""
        if self.doc:
            self.doc.close()

    def __enter__(self) -> "PDFProcessor":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


def validate_pdf(pdf_bytes: bytes) -> tuple[bool, str | None]:
    """Validate that bytes represent a valid PDF.

    Args:
        pdf_bytes: Raw bytes to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        with PDFProcessor(pdf_bytes) as processor:
            if processor.page_count == 0:
                return False, "PDF has no pages"
            return True, None
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Invalid PDF: {e}"
