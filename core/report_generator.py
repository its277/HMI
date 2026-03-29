"""
report_generator.py — PDF report generation with QR code.

Produces a professional PDF summarising the semen analysis using
ReportLab, and generates a QR code linking to a hosted copy or
containing sample metadata.
"""

from __future__ import annotations

import io
import logging
import os
import time
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ReportGenerator(QThread):
    """
    Generates a PDF report from AnalysisResult data.

    Signals
    -------
    progress_updated(int)
        Progress 0-100.
    report_ready(str)
        Absolute path to the generated PDF.
    error_occurred(str)
        Error message.
    """

    progress_updated = pyqtSignal(int)
    report_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        result: Any,  # AnalysisResult
        config: dict[str, Any],
        sample_id: str = "",
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._result = result
        self._config = config
        self._sample_id = sample_id or f"YAK-{int(time.time())}"

    def run(self) -> None:
        try:
            self.progress_updated.emit(10)
            output_dir = self._config.get("output_dir", "reports/")
            os.makedirs(output_dir, exist_ok=True)

            filename = f"{self._sample_id}_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(output_dir, filename)

            self.progress_updated.emit(20)
            self._generate_pdf(filepath)
            self.progress_updated.emit(100)
            self.report_ready.emit(os.path.abspath(filepath))
            logger.info("Report saved: %s", filepath)

        except Exception as exc:
            logger.exception("Report generation failed")
            self.error_occurred.emit(str(exc))

    def _generate_pdf(self, filepath: str) -> None:
        """Build the PDF using ReportLab."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            # Fallback: generate a simple text file
            logger.warning("reportlab not installed — generating text report")
            self._generate_text_report(filepath.replace(".pdf", ".txt"))
            return

        self.progress_updated.emit(40)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements: list[Any] = []

        # Title
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor("#1a73e8"),
        )
        elements.append(Paragraph("Yak Semen Analysis Report", title_style))
        elements.append(Spacer(1, 8 * mm))

        # Lab info
        lab_name = self._config.get("lab_name", "Laboratory")
        lab_id = self._config.get("lab_id", "N/A")
        info_data = [
            ["Laboratory:", lab_name],
            ["Lab ID:", lab_id],
            ["Sample ID:", self._sample_id],
            ["Date/Time:", self._result.timestamp],
            ["Analysis Duration:", f"{self._result.analysis_duration_s} s"],
        ]
        info_table = Table(info_data, colWidths=[4 * cm, 10 * cm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8 * mm))

        self.progress_updated.emit(60)

        # Results summary
        elements.append(Paragraph("Analysis Results", styles["Heading2"]))
        r = self._result
        results_data = [
            ["Parameter", "Value", "Reference"],
            ["Total Cells Detected", str(r.total_cells), "—"],
            ["Total Motility", f"{r.total_motility_pct}%", "≥ 40%"],
            ["Progressive Motility", f"{r.progressive_motility_pct}%", "≥ 32%"],
            ["VCL (avg)", f"{r.avg_vcl} µm/s", "—"],
            ["VSL (avg)", f"{r.avg_vsl} µm/s", "—"],
            ["VAP (avg)", f"{r.avg_vap} µm/s", "—"],
            ["Linearity (avg)", f"{r.avg_lin}", "—"],
            ["Normal Morphology", f"{r.normal_morphology_pct}%", "≥ 70%"],
            ["Concentration (est.)", f"{r.concentration} M/mL", "≥ 15 M/mL"],
        ]
        res_table = Table(results_data, colWidths=[5 * cm, 4 * cm, 4 * cm])
        res_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(res_table)
        elements.append(Spacer(1, 10 * mm))

        self.progress_updated.emit(80)

        # QR Code
        try:
            import qrcode

            qr_data = f"SampleID:{self._sample_id}|Motility:{r.total_motility_pct}%|Morphology:{r.normal_morphology_pct}%"
            qr = qrcode.make(qr_data)
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)

            from reportlab.platypus import Image as RLImage

            qr_image = RLImage(buf, width=3 * cm, height=3 * cm)
            elements.append(Paragraph("QR Code — Sample Data", styles["Heading3"]))
            elements.append(qr_image)
        except ImportError:
            logger.warning("qrcode library not installed — skipping QR")
            elements.append(Paragraph("[QR Code — install 'qrcode' package]", styles["Normal"]))

        self.progress_updated.emit(90)

        # Build
        doc.build(elements)

    def _generate_text_report(self, filepath: str) -> None:
        """Fallback text report when reportlab is unavailable."""
        r = self._result
        lines = [
            "=" * 60,
            "        YAK SEMEN ANALYSIS REPORT",
            "=" * 60,
            f"Sample ID       : {self._sample_id}",
            f"Date/Time       : {r.timestamp}",
            f"Duration        : {r.analysis_duration_s} s",
            "-" * 60,
            f"Total Cells     : {r.total_cells}",
            f"Total Motility  : {r.total_motility_pct}%",
            f"Progressive     : {r.progressive_motility_pct}%",
            f"Avg VCL         : {r.avg_vcl} µm/s",
            f"Avg VSL         : {r.avg_vsl} µm/s",
            f"Normal Morpho.  : {r.normal_morphology_pct}%",
            f"Concentration   : {r.concentration} M/mL",
            "=" * 60,
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Text report saved: %s", filepath)
