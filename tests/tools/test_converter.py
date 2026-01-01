"""
Tests for the DocumentConverter tool.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from edmcp.tools.converter import DocumentConverter


class TestDocumentConverter:
    """Test suite for DocumentConverter."""

    def test_init_checks_dependencies(self):
        """Test that initialization checks for required tools."""
        converter = DocumentConverter()
        # Should have checked for tools
        assert hasattr(converter, "has_libreoffice")
        assert hasattr(converter, "has_pdftotext")

    def test_get_conversion_info(self):
        """Test that conversion info returns expected structure."""
        converter = DocumentConverter()
        info = converter.get_conversion_info()

        assert "word_to_pdf" in info
        assert "pdf_to_text" in info
        assert "available" in info["word_to_pdf"]
        assert "tool" in info["word_to_pdf"]
        assert "install_instructions" in info["word_to_pdf"]

    @patch("subprocess.run")
    def test_convert_word_to_pdf_no_libreoffice(self, mock_run):
        """Test that convert_word_to_pdf fails gracefully without LibreOffice."""
        # Mock which command to return failure
        mock_run.return_value = MagicMock(returncode=1)

        converter = DocumentConverter()
        converter.has_libreoffice = False

        with pytest.raises(RuntimeError, match="LibreOffice is not installed"):
            converter.convert_word_to_pdf("test.docx")

    def test_convert_word_to_pdf_file_not_found(self):
        """Test that convert_word_to_pdf fails if file doesn't exist."""
        converter = DocumentConverter()
        converter.has_libreoffice = True

        with pytest.raises(FileNotFoundError):
            converter.convert_word_to_pdf("/nonexistent/file.docx")

    @patch("subprocess.run")
    def test_convert_pdf_to_text_no_pdftotext(self, mock_run):
        """Test that convert_pdf_to_text fails gracefully without pdftotext."""
        # Mock which command to return failure
        mock_run.return_value = MagicMock(returncode=1)

        converter = DocumentConverter()
        converter.has_pdftotext = False

        with pytest.raises(RuntimeError, match="pdftotext is not installed"):
            converter.convert_pdf_to_text("test.pdf")

    def test_convert_pdf_to_text_file_not_found(self):
        """Test that convert_pdf_to_text fails if file doesn't exist."""
        converter = DocumentConverter()
        converter.has_pdftotext = True

        with pytest.raises(FileNotFoundError):
            converter.convert_pdf_to_text("/nonexistent/file.pdf")

    @patch("edmcp.tools.converter.DocumentConverter.convert_word_to_pdf")
    def test_batch_convert_to_pdf(self, mock_convert, tmp_path):
        """Test batch conversion of Word documents."""
        # Create fake input directory with mock files
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create fake .docx files
        (input_dir / "test1.docx").touch()
        (input_dir / "test2.DOCX").touch()

        output_dir = tmp_path / "output"

        # Mock successful conversions
        mock_convert.side_effect = [output_dir / "test1.pdf", output_dir / "test2.pdf"]

        converter = DocumentConverter()
        converter.has_libreoffice = True

        results = converter.batch_convert_to_pdf(str(input_dir), str(output_dir))

        assert len(results) == 2
        assert mock_convert.call_count == 2

    @patch("edmcp.tools.ocr.OCRTool")
    def test_convert_pdf_to_text_with_ocr(self, mock_ocr_class, tmp_path):
        """Test PDF to text conversion using OCR."""
        # Create a fake PDF file
        input_pdf = tmp_path / "test.pdf"
        input_pdf.write_text("fake pdf content")

        output_txt = tmp_path / "test.txt"

        # Mock OCRTool
        mock_ocr_instance = MagicMock()
        mock_ocr_instance.extract_text_from_pdf.return_value = "Extracted text via OCR"
        mock_ocr_class.return_value = mock_ocr_instance

        converter = DocumentConverter()
        result = converter.convert_pdf_to_text(
            str(input_pdf), str(output_txt), use_ocr=True
        )

        assert result == output_txt
        assert output_txt.read_text() == "Extracted text via OCR"
        mock_ocr_instance.extract_text_from_pdf.assert_called_once()
