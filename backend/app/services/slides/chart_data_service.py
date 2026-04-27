"""
Chart data service providing realistic sample data for chart generation.
Matches context keywords to appropriate chart data templates.
"""

import json
import logging
import os
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)


class ChartDataService:
    """Service for retrieving context-aware chart data."""
    
    def __init__(self):
        """Initialize the chart data service by loading sample data."""
        self.chart_data = {}
        self._load_sample_data()
    
    def _load_sample_data(self):
        """Load sample chart data from JSON configuration."""
        try:
            # Try to load from backend/config/sample_chart_data.json
            config_path = os.path.join(
                os.path.dirname(__file__),
                "..",   # → services/
                "..",   # → app/
                "..",   # → backend/
                "config",
                "sample_chart_data.json"
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.chart_data = json.load(f)
                logger.info(f"Loaded sample chart data from {config_path}")
            else:
                logger.warning(f"Chart data file not found at {config_path}")
                # Use inline fallback data if file not found
                self.chart_data = self._get_fallback_data()
        except Exception as e:
            logger.error(f"Error loading chart data: {e}")
            self.chart_data = self._get_fallback_data()
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """Provide fallback chart data if config file is not available."""
        return {
            "financial_data": {
                "revenue_by_region": {
                    "type": "bar",
                    "labels": ["North", "South", "East", "West"],
                    "values": [85000, 92000, 78000, 88000]
                }
            },
            "performance_data": {
                "team_scores": {
                    "type": "bar",
                    "labels": ["Team A", "Team B", "Team C", "Team D"],
                    "values": [92, 88, 85, 91]
                }
            }
        }
    
    def get_context_category(self, text: str) -> str:
        """
        Detect the context category from text.
        
        Args:
            text: Text to analyze (slide title or content)
        
        Returns:
            Category name (financial_data, performance_data, etc.)
        """
        text_lower = text.lower()
        
        # Financial keywords
        if any(kw in text_lower for kw in ['revenue', 'profit', 'cost', 'sales', 'financial', 'budget', 'product', 'quarter', 'region']):
            return "financial_data"
        
        # Performance keywords
        elif any(kw in text_lower for kw in ['performance', 'team', 'efficiency', 'score', 'metric', 'uptime', 'resource', 'cpu', 'memory']):
            return "performance_data"
        
        # Demographic keywords
        elif any(kw in text_lower for kw in ['demographic', 'user', 'age', 'segment', 'subscription', 'customer', 'population']):
            return "demographic_data"
        
        # Sales keywords
        elif any(kw in text_lower for kw in ['sales', 'monthly', 'regional', 'tier', 'market', 'america', 'europe', 'asia']):
            return "sales_data"
        
        # Education keywords
        elif any(kw in text_lower for kw in ['education', 'student', 'course', 'enrollment', 'department', 'learning']):
            return "education_data"
        
        # Operations keywords
        elif any(kw in text_lower for kw in ['production', 'operational', 'facility', 'plant', 'error', 'output']):
            return "operational_data"
        
        # Default
        return "financial_data"
    
    def get_chart_data_for_context(
        self,
        slide_title: str,
        chart_type: str,
        slide_index: int
    ) -> Tuple[List[str], List[float], Dict[str, Any]]:
        """
        Get realistic chart data based on slide context and chart type.
        
        Args:
            slide_title: Title of the slide
            chart_type: Desired chart type (bar, line, pie)
            slide_index: Index of slide (for selection)
        
        Returns:
            Tuple of (labels, values, metadata)
        """
        category = self.get_context_category(slide_title)
        
        if category not in self.chart_data:
            logger.warning(f"Category {category} not found in chart data")
            return self._generate_default_data(chart_type)
        
        # Get all data samples in this category
        samples = self.chart_data[category]
        
        # Filter by chart type
        matching_samples = [
            (key, data) for key, data in samples.items()
            if data.get("type") == chart_type
        ]
        
        if not matching_samples:
            # If no matching type, return first available sample
            matching_samples = list(samples.items())
        
        if not matching_samples:
            return self._generate_default_data(chart_type)
        
        # Select sample deterministically based on slide index
        selected_key, selected_data = matching_samples[slide_index % len(matching_samples)]
        
        labels = selected_data.get("labels", [])
        values = selected_data.get("values", [])
        metadata = {
            "source": "Sample Data",
            "category": category,
            "data_key": selected_key,
            "context": selected_data.get("context", "")
        }
        
        logger.info(f"Selected chart data for '{slide_title}': {selected_key} ({chart_type})")
        
        return labels, values, metadata
    
    def _generate_default_data(self, chart_type: str) -> Tuple[List[str], List[float], Dict[str, Any]]:
        """Generate default data if no context-specific data available."""
        if chart_type == "bar":
            return (
                ["Category A", "Category B", "Category C", "Category D"],
                [75, 82, 68, 90],
                {"source": "Generated Default", "category": "unknown"}
            )
        elif chart_type == "line":
            return (
                ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
                [40, 45, 50, 55, 60, 68],
                {"source": "Generated Default", "category": "unknown"}
            )
        elif chart_type == "pie":
            return (
                ["Segment A", "Segment B", "Segment C", "Segment D"],
                [35, 25, 25, 15],
                {"source": "Generated Default", "category": "unknown"}
            )
        else:
            return (
                ["Item 1", "Item 2", "Item 3"],
                [50, 60, 70],
                {"source": "Generated Default", "category": "unknown"}
            )


# Initialize service
chart_data_service = ChartDataService()
