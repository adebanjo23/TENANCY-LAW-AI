import io
import os
import tempfile
import shutil
from datetime import datetime, timedelta
import nest_asyncio
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv
from langchain.schema import Document as LangchainDocument
from pypdf import PdfReader, PdfWriter
from llama_parse import LlamaParse

# Enable nested async support
nest_asyncio.apply()

# Load environment variables
load_dotenv()


class DocumentType(Enum):
    PDF = "pdf"
    WORD = "docx"


@dataclass
class DocumentFile:
    """Data class to represent a document"""
    data_bytes: bytes
    name: str
    doc_type: DocumentType
    title: Optional[str] = None


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors"""
    pass


class DocumentProcessor:
    """Utility class for processing PDF and Word documents"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the document processor.

        Args:
            api_key: Llama Cloud API key. If not provided, will attempt to get from environment.
        """

        self.api_key = api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            raise DocumentProcessingError(
                "LLAMA CLOUD API key not found. Please set LLAMA_CLOUD_API_KEY environment variable")

        # Initialize LlamaParse
        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",
            verbose=True,
            language="en"
        )

        # Set up temp directory in project folder
        today = datetime.now().strftime("%Y-%m-%d")
        self.temp_base_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "temp_files",
            today
        )
        os.makedirs(self.temp_base_dir, exist_ok=True)

        # Check available disk space
        self._check_disk_space()

        # Load configuration from environment
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))

    def _check_disk_space(self, min_gb: int = 10):
        """Check available disk space in temp directory"""
        total, used, free = shutil.disk_usage(self.temp_base_dir)
        free_gb = free // (2 ** 30)  # Convert to GB

    def cleanup_old_files(self, days_to_keep: int = 7):
        """Clean up temporary files older than specified days"""
        temp_root = os.path.join(os.path.dirname(__file__), "..", "..", "temp_files")
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        cleaned_dirs = 0
        for item in os.listdir(temp_root):
            item_path = os.path.join(temp_root, item)
            if os.path.isdir(item_path) and item != ".gitkeep":
                try:
                    dir_date = datetime.strptime(item, "%Y-%m-%d")
                    if dir_date < cutoff_date:
                        shutil.rmtree(item_path)
                        cleaned_dirs += 1
                except ValueError:
                    continue

    async def parse_document(self, file_paths: List[str]) -> List[LangchainDocument]:
        """
        Parse PDF and Word documents using Llama Parse.

        Args:
            file_paths: List of paths to PDF or Word files

        Returns:
            List of parsed documents

        Raises:
            DocumentProcessingError: If parsing fails
        """
        if not file_paths:
            raise DocumentProcessingError("File paths are required")

        try:
            documents = []
            for file_path in file_paths:
                try:
                    parsed_docs = await self.parser.aload_data(file_path)
                    if parsed_docs:
                        documents.extend(parsed_docs)
                except Exception as e:
                    continue

            if not documents:
                return []

            return documents

        except Exception as e:
            raise DocumentProcessingError(f"Document parsing failed: {str(e)}")

    async def split_document_pages(self, document: DocumentFile) -> Tuple[List[str], tempfile.TemporaryDirectory]:
        """
        Split a document into individual pages.

        Args:
            document: DocumentFile instance

        Returns:
            Tuple of (list of page file paths, temporary directory)

        Raises:
            DocumentProcessingError: If splitting fails
        """
        try:
            temp_dir = tempfile.TemporaryDirectory(dir=self.temp_base_dir)

            if document.doc_type == DocumentType.PDF:
                return await self._split_pdf_pages(document, temp_dir)
            elif document.doc_type == DocumentType.WORD:
                return await self._split_word_pages(document, temp_dir)
            else:
                raise DocumentProcessingError(f"Unsupported document type: {document.doc_type}")

        except Exception as e:
            raise DocumentProcessingError(f"Document splitting failed: {str(e)}")

    async def _split_pdf_pages(
            self,
            document: DocumentFile,
            temp_dir: tempfile.TemporaryDirectory
    ) -> Tuple[List[str], tempfile.TemporaryDirectory]:
        """Split PDF document into pages"""
        reader = PdfReader(io.BytesIO(document.data_bytes))

        if not document.title:
            document.title = self._extract_pdf_title(reader) or document.name

        page_files = []
        total_pages = len(reader.pages)

        for i, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)

            output_stream = io.BytesIO()
            writer.write(output_stream)

            output_filename = os.path.join(temp_dir.name, f"page_{i}.pdf")
            with open(output_filename, "wb") as f:
                f.write(output_stream.getvalue())

            page_files.append(output_filename)

        return page_files, temp_dir

    async def _split_word_pages(
            self,
            document: DocumentFile,
            temp_dir: tempfile.TemporaryDirectory
    ) -> Tuple[List[str], tempfile.TemporaryDirectory]:
        """Split Word document into pages using Llama Parse"""
        temp_path = os.path.join(temp_dir.name, "complete.docx")
        with open(temp_path, "wb") as f:
            f.write(document.data_bytes)


        parsed_docs = await self.parser.aload_data(temp_path)
        page_files = []

        for i, section in enumerate(parsed_docs, start=1):
            output_filename = os.path.join(temp_dir.name, f"page_{i}.docx")

            if hasattr(section, 'text'):
                content = section.text
            elif isinstance(section, dict):
                content = section.get('text', '')
            else:
                content = str(section)

            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(content)

            page_files.append(output_filename)

        return page_files, temp_dir

    def _extract_pdf_title(self, reader: PdfReader) -> Optional[str]:
        """Extract title from PDF metadata"""
        try:
            metadata = reader.metadata
            title = metadata.get("/Title", None)
            return title.strip() if title else None
        except Exception as e:
            return None

    @staticmethod
    def read_document_bytes(file_path: str) -> Tuple[bytes, DocumentType]:
        """Read document file into bytes and determine its type"""

        try:
            with open(file_path, "rb") as file:
                data = file.read()

            if file_path.lower().endswith('.pdf'):
                doc_type = DocumentType.PDF
            elif file_path.lower().endswith(('.docx', '.doc')):
                doc_type = DocumentType.WORD
            else:
                raise DocumentProcessingError(f"Unsupported file type: {file_path}")
            return data, doc_type

        except Exception as e:
            raise DocumentProcessingError(f"Failed to read document file: {str(e)}")
