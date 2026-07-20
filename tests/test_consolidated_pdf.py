import tempfile
import unittest
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from generator import merge_pdf_files


class ConsolidatedPdfTest(unittest.TestCase):
    def test_merge_pdf_files_creates_pdf_with_all_pages(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_one = tmp_path / "one.pdf"
            pdf_two = tmp_path / "two.pdf"
            merged_pdf = tmp_path / "merged.pdf"

            for path in [pdf_one, pdf_two]:
                c = canvas.Canvas(str(path), pagesize=A4)
                c.drawString(100, 750, "sample")
                c.showPage()
                c.save()

            merge_pdf_files([str(pdf_one), str(pdf_two)], str(merged_pdf))

            self.assertTrue(merged_pdf.exists())
            from pypdf import PdfReader

            reader = PdfReader(str(merged_pdf))
            self.assertEqual(len(reader.pages), 2)


if __name__ == "__main__":
    unittest.main()
