"""
Doubt Summarizer Export Service

Handles PDF, CSV, and Email export of doubt summaries.
"""

import logging
from typing import Dict, Any
from io import BytesIO, StringIO
import csv
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import PDF generation library
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available - PDF export disabled")


class DoubtExportService:
    """Service for exporting doubt summaries in various formats"""

    def generate_pdf(self, summary_data: Dict[str, Any], course_code: str, period: str) -> BytesIO:
        """
        Generate PDF report from summary data.
        
        Args:
            summary_data: Complete summary response from doubt summarizer
            course_code: Course identifier
            period: Time period (daily/weekly/monthly)
            
        Returns:
            BytesIO buffer containing PDF data
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
        )
        story.append(Paragraph(f"Doubt Summary Report - {course_code}", title_style))
        story.append(Paragraph(f"Period: {period.capitalize()} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # Overall Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        story.append(Paragraph(summary_data.get('overall_summary', 'No summary available'), styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        # Statistics
        if 'stats' in summary_data:
            stats = summary_data['stats']
            story.append(Paragraph("Key Metrics", styles['Heading2']))
            
            stats_data = [
                ['Metric', 'Value'],
                ['Total Messages', str(stats.get('total_messages', 0))],
                ['Topic Clusters', str(stats.get('topic_clusters', 0))],
                ['Recurring Issues', str(stats.get('recurring_issues', 0))],
                ['Learning Gaps', str(stats.get('learning_gaps', 0))],
            ]
            
            stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 0.3*inch))

        # Topic Clusters
        topics = summary_data.get('topics', [])
        if topics:
            story.append(Paragraph("Topic Clusters", styles['Heading2']))
            for i, topic in enumerate(topics, 1):
                story.append(Paragraph(f"{i}. <b>{topic.get('label', 'Unknown')}</b> ({topic.get('count', 0)} queries)", styles['Normal']))
                story.append(Paragraph(f"   Trend: {topic.get('trend', 'N/A')}", styles['Normal']))
                
                samples = topic.get('sample_questions', [])
                if samples:
                    story.append(Paragraph("   Sample Questions:", styles['Normal']))
                    for sample in samples[:3]:  # Limit to 3 samples
                        story.append(Paragraph(f"   • {sample}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))

        # Learning Gaps
        gaps = summary_data.get('learning_gaps', [])
        if gaps:
            story.append(Paragraph("Learning Gaps", styles['Heading2']))
            for i, gap in enumerate(gaps, 1):
                story.append(Paragraph(
                    f"{i}. <b>{gap.get('issue_title', 'Unknown')}</b> - {gap.get('student_count', 0)} students affected",
                    styles['Normal']
                ))
                story.append(Paragraph(f"   Category: {gap.get('category', 'N/A')}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))

        # Insights
        insights = summary_data.get('insights', [])
        if insights:
            story.append(Paragraph("AI Insights", styles['Heading2']))
            for insight in insights:
                story.append(Paragraph(f"• {insight}", styles['Normal']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_csv(self, summary_data: Dict[str, Any], course_code: str, period: str) -> StringIO:
        """
        Generate CSV export from summary data.
        
        Args:
            summary_data: Complete summary response from doubt summarizer
            course_code: Course identifier
            period: Time period (daily/weekly/monthly)
            
        Returns:
            StringIO buffer containing CSV data
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Doubt Summary Report'])
        writer.writerow(['Course Code', course_code])
        writer.writerow(['Period', period])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])

        # Statistics
        if 'stats' in summary_data:
            writer.writerow(['STATISTICS'])
            writer.writerow(['Metric', 'Value'])
            stats = summary_data['stats']
            writer.writerow(['Total Messages', stats.get('total_messages', 0)])
            writer.writerow(['Topic Clusters', stats.get('topic_clusters', 0)])
            writer.writerow(['Recurring Issues', stats.get('recurring_issues', 0)])
            writer.writerow(['Learning Gaps', stats.get('learning_gaps', 0)])
            writer.writerow([])

        # Topic Clusters
        topics = summary_data.get('topics', [])
        if topics:
            writer.writerow(['TOPIC CLUSTERS'])
            writer.writerow(['#', 'Topic', 'Count', 'Trend', 'Sample Questions'])
            for i, topic in enumerate(topics, 1):
                samples = '; '.join(topic.get('sample_questions', [])[:3])
                writer.writerow([
                    i,
                    topic.get('label', 'Unknown'),
                    topic.get('count', 0),
                    topic.get('trend', 'N/A'),
                    samples
                ])
            writer.writerow([])

        # Learning Gaps
        gaps = summary_data.get('learning_gaps', [])
        if gaps:
            writer.writerow(['LEARNING GAPS'])
            writer.writerow(['#', 'Issue', 'Category', 'Students Affected'])
            for i, gap in enumerate(gaps, 1):
                writer.writerow([
                    i,
                    gap.get('issue_title', 'Unknown'),
                    gap.get('category', 'N/A'),
                    gap.get('student_count', 0)
                ])
            writer.writerow([])

        # Insights
        insights = summary_data.get('insights', [])
        if insights:
            writer.writerow(['AI INSIGHTS'])
            for insight in insights:
                writer.writerow([insight])

        output.seek(0)
        return output


# Global instance
doubt_export_service = DoubtExportService()
