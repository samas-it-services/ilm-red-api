"""Text Chunking Service for AI/RAG processing.

Splits book text into AI-friendly chunks with token counting and page mapping.
Each chunk maps to a page range for citations.

Principle P2: Chunks are for thinking (AI understanding).
"""

from dataclasses import dataclass

import tiktoken


@dataclass
class TextChunkData:
    """Data for a single text chunk."""

    text: str
    token_count: int
    page_start: int
    page_end: int


class ChunkingService:
    """Split book text into AI-friendly chunks with page mapping.

    Chunks are sized for efficient AI context windows:
    - Max tokens: 500 (good balance for context retrieval)
    - Overlap: 50 tokens (maintains context continuity)

    Each chunk tracks which pages it came from, enabling citations
    in AI responses like "According to pages 15-17..."

    Usage:
        service = ChunkingService()
        pages = [(1, "First page text..."), (2, "Second page text...")]
        chunks = service.chunk_book(pages)
        for chunk in chunks:
            print(f"[Pages {chunk.page_start}-{chunk.page_end}] {chunk.text[:50]}...")
    """

    def __init__(
        self,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
        encoding_name: str = "cl100k_base",
    ):
        """Initialize chunking service.

        Args:
            max_tokens: Maximum tokens per chunk (default 500).
            overlap_tokens: Token overlap between chunks (default 50).
            encoding_name: tiktoken encoding name (default cl100k_base for GPT-4).
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoder = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count.

        Returns:
            Number of tokens.
        """
        return len(self.encoder.encode(text))

    def chunk_book(
        self,
        pages: list[tuple[int, str]],
    ) -> list[TextChunkData]:
        """Chunk book text into AI-friendly segments.

        Each chunk maps to a page range for citations. Chunks never exceed
        max_tokens and include overlap with previous chunk for context.

        Args:
            pages: List of (page_number, text) tuples, 1-indexed.

        Returns:
            List of TextChunkData with text, token count, and page range.
        """
        if not pages:
            return []

        chunks: list[TextChunkData] = []
        current_tokens: list[int] = []  # Token IDs
        chunk_start_page = pages[0][0]
        current_page = pages[0][0]

        for page_num, page_text in pages:
            current_page = page_num

            # Encode page text to tokens
            page_tokens = self.encoder.encode(page_text)

            for token in page_tokens:
                # Check if we need to create a new chunk
                if len(current_tokens) >= self.max_tokens:
                    # Decode current tokens to text
                    chunk_text = self.encoder.decode(current_tokens)

                    # Save chunk
                    chunks.append(
                        TextChunkData(
                            text=chunk_text.strip(),
                            token_count=len(current_tokens),
                            page_start=chunk_start_page,
                            page_end=current_page,
                        )
                    )

                    # Start new chunk with overlap
                    # Keep the last overlap_tokens from current chunk
                    overlap_start = max(0, len(current_tokens) - self.overlap_tokens)
                    current_tokens = current_tokens[overlap_start:]
                    chunk_start_page = current_page

                # Add token to current chunk
                current_tokens.append(token)

        # Don't forget the last chunk
        if current_tokens:
            chunk_text = self.encoder.decode(current_tokens)
            if chunk_text.strip():
                chunks.append(
                    TextChunkData(
                        text=chunk_text.strip(),
                        token_count=len(current_tokens),
                        page_start=chunk_start_page,
                        page_end=current_page,
                    )
                )

        return chunks

    def chunk_text_simple(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[TextChunkData]:
        """Chunk a single text block (convenience method).

        Args:
            text: Text to chunk.
            page_number: Page number to assign to all chunks.

        Returns:
            List of TextChunkData.
        """
        return self.chunk_book([(page_number, text)])


def create_chunking_service(
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> ChunkingService:
    """Factory function to create a chunking service.

    Args:
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Token overlap between chunks.

    Returns:
        Configured ChunkingService instance.
    """
    return ChunkingService(
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )
