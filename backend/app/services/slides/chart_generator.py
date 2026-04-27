"""
Chart generation utility using matplotlib.
Generates deterministic, context-aware chart images for slide decks.
"""

import io
import base64
import logging
from typing import List, Tuple, Optional, Dict, Any
import re

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    np = None

from app.services.slides.chart_data_service import chart_data_service

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generates chart images as base64 Data URIs."""
    
    def __init__(self):
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available. Chart generation disabled.")
    
    def generate_axis_metadata(self, slide_title: str, chart_type: str, labels: List[str], values: List) -> Dict[str, Any]:
        """
        Generate meaningful axis metadata based on slide context.
        
        Args:
            slide_title: Title of the slide for context detection
            chart_type: Type of chart (bar, line, pie, scatter)
            labels: Data labels
            values: Data values
        
        Returns:
            Dictionary with x_axis, y_axis, data_description, and data_source metadata
        """
        title_lower = slide_title.lower()
        
        # Detect context keywords
        is_financial = any(kw in title_lower for kw in ['revenue', 'profit', 'cost', 'price', 'sales', 'financial', 'budget', 'income'])
        is_performance = any(kw in title_lower for kw in ['performance', 'efficiency', 'productivity', 'score', 'rating', 'kpi'])
        is_growth = any(kw in title_lower for kw in ['growth', 'increase', 'trend', 'progress'])
        is_time_series = any(kw in title_lower for kw in ['quarter', 'month', 'year', 'week', 'time', 'timeline'])
        is_demographic = any(kw in title_lower for kw in ['age', 'population', 'demographic', 'people', 'users', 'customers'])
        is_geographic = any(kw in title_lower for kw in ['region', 'location', 'country', 'city', 'area', 'zone'])
        is_percentage = any(kw in title_lower for kw in ['percentage', 'rate', 'ratio', 'share', 'proportion'])
        
        # Initialize metadata
        x_axis = {"label": "Categories", "unit": None}
        y_axis = {"label": "Values", "unit": None}
        data_description = "Synthetic data generated for visualization"
        
        # Determine X-axis metadata
        if chart_type == "pie":
            x_axis = None  # Pie charts don't have traditional axes
            y_axis = None
            data_description = f"Distribution breakdown showing relative proportions"
        elif is_time_series or any(label in ['Q1', 'Q2', 'Q3', 'Q4'] for label in labels[:4]):
            if 'quarter' in title_lower or any(label.startswith('Q') for label in labels[:4]):
                x_axis = {"label": "Quarter", "unit": None}
            elif any(month in labels[0] if labels else '' for month in ['Jan', 'Feb', 'Mar']):
                x_axis = {"label": "Month", "unit": None}
            elif 'week' in str(labels[0]).lower() if labels else False:
                x_axis = {"label": "Week", "unit": None}
            else:
                x_axis = {"label": "Time Period", "unit": None}
        elif is_geographic:
            x_axis = {"label": "Region", "unit": None}
        elif 'product' in title_lower:
            x_axis = {"label": "Product", "unit": None}
        elif 'category' in title_lower or 'segment' in title_lower:
            x_axis = {"label": "Category", "unit": None}
        
        # Determine Y-axis metadata and data range
        if chart_type != "pie":
            if is_financial:
                y_axis = {"label": "Amount", "unit": "$"}
                data_description = "Financial metrics showing monetary values"
            elif is_percentage:
                y_axis = {"label": "Percentage", "unit": "%"}
                data_description = "Percentage distribution or rates"
            elif is_performance:
                y_axis = {"label": "Score", "unit": "points"}
                data_description = "Performance metrics or ratings"
            elif is_demographic:
                y_axis = {"label": "Count", "unit": "people"}
                data_description = "Demographic data showing population counts"
            elif is_growth:
                y_axis = {"label": "Growth Rate", "unit": "%"}
                data_description = "Growth trends over time"
            else:
                y_axis = {"label": "Value", "unit": None}
            
            # Calculate min/max from values
            if chart_type == "scatter" and values and isinstance(values[0], (list, tuple)):
                x_vals, y_vals = zip(*values)
                x_axis["min_value"] = float(min(x_vals))
                x_axis["max_value"] = float(max(x_vals))
                y_axis["min_value"] = float(min(y_vals))
                y_axis["max_value"] = float(max(y_vals))
            elif values and all(isinstance(v, (int, float)) for v in values):
                y_axis["min_value"] = float(min(values))
                y_axis["max_value"] = float(max(values))
        
        return {
            "x_axis": x_axis,
            "y_axis": y_axis,
            "data_description": data_description,
            "data_source": "Context-aware synthetic data generation"
        }
    
    def generate_synthetic_data(
        self, 
        slide_title: str, 
        chart_type: str, 
        slide_index: int,
        num_points: Optional[int] = None
    ) -> Tuple[List[str], List[float]]:
        """
        Generate contextual synthetic data based on slide title and chart type.
        Tries to use realistic sample data from chart_data_service first.
        Falls back to generated data if not available.
        
        Args:
            slide_title: Title of the slide (used for context)
            chart_type: Type of chart (bar, line, pie, scatter)
            slide_index: Index of slide (for deterministic randomness)
            num_points: Optional number of data points
        
        Returns:
            Tuple of (labels, values)
        """
        try:
            # Try to get sample data based on context
            labels, values, metadata = chart_data_service.get_chart_data_for_context(
                slide_title=slide_title,
                chart_type=chart_type,
                slide_index=slide_index
            )
            
            # If sample data has fewer points than requested, use it as-is
            # Otherwise generate synthetic if more points needed
            if num_points and len(labels) < num_points:
                # Generate additional data matching the pattern
                logger.info(f"Sample data has {len(labels)} points, but {num_points} requested. Augmenting...")
                # For now, just return what we have
                pass
            
            logger.info(f"Using sample data for '{slide_title}': {len(labels)} points, type={chart_type}")
            return labels, values
        
        except Exception as e:
            logger.warning(f"Could not load sample data for '{slide_title}': {e}. Generating synthetic data...")
            # Fall back to generated data
            return self._generate_synthetic_data_fallback(slide_title, chart_type, slide_index, num_points)
    
    def _generate_synthetic_data_fallback(
        self,
        slide_title: str,
        chart_type: str,
        slide_index: int,
        num_points: Optional[int] = None
    ) -> Tuple[List[str], List[float]]:
        """Fallback method for generating synthetic data when sample data unavailable."""
        # Create deterministic seed from title and index
        seed = abs(hash(slide_title)) % 10000 + slide_index * 100
        np.random.seed(seed)
        
        title_lower = slide_title.lower()
        
        # Detect context from keywords
        is_growth = any(kw in title_lower for kw in ['growth', 'increase', 'rising', 'trend'])
        is_decline = any(kw in title_lower for kw in ['decline', 'decrease', 'falling', 'drop'])
        is_comparison = any(kw in title_lower for kw in ['compare', 'comparison', 'versus', 'vs'])
        is_distribution = any(kw in title_lower for kw in ['distribution', 'breakdown', 'share', 'composition'])
        is_performance = any(kw in title_lower for kw in ['performance', 'metrics', 'kpi', 'score'])
        
        if chart_type == "bar":
            n = num_points or np.random.randint(5, 9)
            labels = self._generate_category_labels(n, title_lower)
            
            if is_comparison:
                # Varied values for comparison
                values = np.random.uniform(40, 95, n).tolist()
            elif is_performance:
                # Performance scores (higher better)
                values = np.random.uniform(60, 98, n).tolist()
            else:
                # General data
                values = np.random.uniform(30, 100, n).tolist()
        
        elif chart_type == "line":
            n = num_points or np.random.randint(6, 11)
            labels = self._generate_time_labels(n)
            
            base = np.random.uniform(40, 60)
            if is_growth:
                # Increasing trend with noise
                values = [base + i * np.random.uniform(3, 8) + np.random.uniform(-5, 5) for i in range(n)]
            elif is_decline:
                # Decreasing trend with noise
                values = [base + 50 - i * np.random.uniform(3, 8) + np.random.uniform(-5, 5) for i in range(n)]
            else:
                # Stable with fluctuation
                values = [base + np.random.uniform(-10, 10) for _ in range(n)]
            
            # Ensure positive values
            values = [max(10, v) for v in values]
        
        elif chart_type == "pie":
            n = num_points or np.random.randint(4, 7)
            labels = self._generate_category_labels(n, title_lower)
            
            if is_distribution:
                # More varied distribution
                values = np.random.dirichlet(np.ones(n)) * 100
            else:
                # Somewhat balanced distribution
                values = np.random.dirichlet(np.ones(n) * 2) * 100
            
            values = values.tolist()
        
        elif chart_type == "scatter":
            n = num_points or np.random.randint(15, 25)
            # For scatter, labels are just point indices
            labels = [str(i) for i in range(n)]
            
            # Generate correlated data (x and y values)
            x_vals = np.random.uniform(10, 100, n)
            
            if 'correlation' in title_lower or 'relationship' in title_lower:
                # Positive correlation with noise
                y_vals = x_vals * np.random.uniform(0.7, 1.2) + np.random.normal(0, 10, n)
            else:
                # Random scatter
                y_vals = np.random.uniform(10, 100, n)
            
            # For scatter, return as list of tuples (x, y)
            values = list(zip(x_vals.tolist(), y_vals.tolist()))
            return labels, values
        
        else:
            # Default bar chart
            n = 6
            labels = [f"Item {i+1}" for i in range(n)]
            values = np.random.uniform(30, 90, n).tolist()
        
        return labels, values
    
    def _generate_category_labels(self, n: int, context: str = "") -> List[str]:
        """Generate contextual category labels based on context."""
        context_lower = context.lower()
        
        # Financial context
        if any(kw in context_lower for kw in ['revenue', 'profit', 'cost', 'sales', 'financial', 'budget']):
            if 'quarter' in context_lower:
                return [f"Q{i+1}" for i in range(min(n, 4))]
            elif 'product' in context_lower:
                return ["Premium", "Standard", "Basic", "Enterprise", "Professional", "Starter"][:n]
            elif 'region' in context_lower:
                return ["North", "South", "East", "West", "Central", "Northeast"][:n]
            elif 'department' in context_lower:
                return ["Sales", "Marketing", "Engineering", "Operations", "Support", "HR"][:n]
            else:
                return ["Product A", "Product B", "Product C", "Product D", "Product E", "Product F"][:n]
        
        # Performance context
        elif any(kw in context_lower for kw in ['performance', 'efficiency', 'productivity', 'score', 'rating', 'kpi']):
            if 'team' in context_lower:
                return ["Team A", "Team B", "Team C", "Team D", "Team E", "Team F"][:n]
            elif 'component' in context_lower or 'service' in context_lower:
                return ["API", "Frontend", "Backend", "Database", "Cache", "Queue"][:n]
            elif 'metric' in context_lower:
                return ["CPU", "Memory", "Disk", "Network", "Latency", "Throughput"][:n]
            else:
                return ["Category A", "Category B", "Category C", "Category D", "Category E", "Category F"][:n]
        
        # Demographic context
        elif any(kw in context_lower for kw in ['age', 'population', 'demographic', 'people', 'users', 'customers']):
            if 'age' in context_lower:
                return ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"][:n]
            elif 'segment' in context_lower:
                return ["Premium", "Standard", "Basic", "Free", "Enterprise", "SMB"][:n]
            elif 'region' in context_lower:
                return ["North", "South", "East", "West", "Central", "Coastal"][:n]
            else:
                return ["Segment A", "Segment B", "Segment C", "Segment D", "Segment E", "Segment F"][:n]
        
        # Time/Quarter context
        elif 'quarter' in context_lower or 'q1' in context_lower:
            return [f"Q{i+1}" for i in range(min(n, 4))]
        
        # Month context
        elif 'month' in context_lower:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return months[:n]
        
        # Product context
        elif 'product' in context_lower or 'item' in context_lower:
            return [f"Product {chr(65+i)}" for i in range(n)]
        
        # Category context
        elif 'category' in context_lower or 'segment' in context_lower:
            return [f"Category {chr(65+i)}" for i in range(n)]
        
        # Region context
        elif 'region' in context_lower or 'location' in context_lower:
            regions = ["North", "South", "East", "West", "Central", "Northeast", "Southeast", "Northwest"]
            return regions[:n]
        
        # Default: Use generic but numbered labels (fallback)
        else:
            return [f"Item {i+1}" for i in range(n)]
    
    def _generate_time_labels(self, n: int) -> List[str]:
        """Generate time-series labels."""
        if n <= 4:
            return [f"Q{i+1}" for i in range(n)]
        elif n <= 12:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return months[:n]
        else:
            return [f"Week {i+1}" for i in range(n)]
    
    def _truncate_label(self, label: str, max_len: int = 18) -> str:
        """Truncate label if too long."""
        if len(label) > max_len:
            return label[:max_len-2] + ".."
        return label
    
    def generate_chart_image(
        self,
        chart_type: str,
        title: str,
        labels: List[str],
        values: List,
        slide_title: str = "",
        slide_index: int = 0,
        axis_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generate a chart image and return as base64 Data URI.
        
        Args:
            chart_type: Type of chart (bar, line, pie, scatter)
            title: Chart title
            labels: Data labels
            values: Data values
            slide_title: Slide title for context
            slide_index: Slide index
            axis_metadata: Optional axis metadata with x_axis, y_axis information
        
        Returns:
            Base64 Data URI string or None if generation fails
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available. Cannot generate chart.")
            return None
        
        try:
            # Generate axis metadata if not provided
            if not axis_metadata:
                axis_metadata = self.generate_axis_metadata(slide_title, chart_type, labels, values)
            
            # Create figure with appropriate size
            fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
            
            # Truncate labels
            truncated_labels = [self._truncate_label(str(l)) for l in labels]
            
            # Extract axis info
            x_axis = axis_metadata.get('x_axis', {})
            y_axis = axis_metadata.get('y_axis', {})
            
            if chart_type == "bar":
                bars = ax.bar(truncated_labels, values, color='#4F46E5', alpha=0.8, edgecolor='white', linewidth=1.5)
                
                # Set Y-axis label with unit
                y_label = y_axis.get('label', 'Values') if y_axis else 'Values'
                y_unit = y_axis.get('unit') if y_axis else None
                if y_unit:
                    ax.set_ylabel(f'{y_label} ({y_unit})', fontsize=11, fontweight='bold')
                else:
                    ax.set_ylabel(y_label, fontsize=11, fontweight='bold')
                
                # Set X-axis label
                x_label = x_axis.get('label', '') if x_axis else ''
                if x_label:
                    ax.set_xlabel(x_label, fontsize=11, fontweight='bold')
                
                # Rotate x-labels if many categories
                if len(labels) > 6:
                    plt.xticks(rotation=30, ha='right', fontsize=9)
                else:
                    plt.xticks(fontsize=9)
                ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.7)
            
            elif chart_type == "line":
                ax.plot(truncated_labels, values, marker='o', linewidth=2.5, 
                       color='#4F46E5', markersize=7, markerfacecolor='white', 
                       markeredgewidth=2.5, markeredgecolor='#4F46E5')
                
                # Set Y-axis label with unit
                y_label = y_axis.get('label', 'Values') if y_axis else 'Values'
                y_unit = y_axis.get('unit') if y_axis else None
                if y_unit:
                    ax.set_ylabel(f'{y_label} ({y_unit})', fontsize=11, fontweight='bold')
                else:
                    ax.set_ylabel(y_label, fontsize=11, fontweight='bold')
                
                # Set X-axis label
                x_label = x_axis.get('label', '') if x_axis else ''
                if x_label:
                    ax.set_xlabel(x_label, fontsize=11, fontweight='bold')
                
                if len(labels) > 8:
                    plt.xticks(rotation=30, ha='right', fontsize=9)
                else:
                    plt.xticks(fontsize=9)
                ax.grid(alpha=0.3, linestyle='--', linewidth=0.7)
            
            elif chart_type == "pie":
                colors = plt.cm.Set3(np.linspace(0, 1, len(values)))
                wedges, texts, autotexts = ax.pie(
                    values, 
                    labels=truncated_labels, 
                    autopct='%1.1f%%',
                    colors=colors,
                    startangle=90,
                    textprops={'fontsize': 9}
                )
                # Make percentage text more visible
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_weight('bold')
                    autotext.set_fontsize(8)
            
            elif chart_type == "scatter":
                # Values are list of (x, y) tuples
                if values and isinstance(values[0], (list, tuple)):
                    x_vals, y_vals = zip(*values)
                    ax.scatter(x_vals, y_vals, s=60, alpha=0.6, color='#4F46E5', edgecolors='white', linewidth=1.5)
                    
                    # Set X-axis label with unit
                    x_label = x_axis.get('label', 'X Values') if x_axis else 'X Values'
                    x_unit = x_axis.get('unit') if x_axis else None
                    if x_unit:
                        ax.set_xlabel(f'{x_label} ({x_unit})', fontsize=11, fontweight='bold')
                    else:
                        ax.set_xlabel(x_label, fontsize=11, fontweight='bold')
                    
                    # Set Y-axis label with unit
                    y_label = y_axis.get('label', 'Y Values') if y_axis else 'Y Values'
                    y_unit = y_axis.get('unit') if y_axis else None
                    if y_unit:
                        ax.set_ylabel(f'{y_label} ({y_unit})', fontsize=11, fontweight='bold')
                    else:
                        ax.set_ylabel(y_label, fontsize=11, fontweight='bold')
                    
                    ax.grid(alpha=0.3, linestyle='--', linewidth=0.7)
            
            # Set title
            ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
            
            # Tight layout to prevent clipping
            plt.tight_layout()
            
            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            
            # Encode as base64
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            data_uri = f"data:image/png;base64,{image_base64}"
            
            # Clean up
            plt.close(fig)
            buf.close()
            
            logger.info(f"Successfully generated {chart_type} chart: {title}")
            return data_uri
        
        except Exception as e:
            logger.error(f"Failed to generate chart: {e}")
            plt.close('all')  # Clean up any open figures
            return None


# Global instance
chart_generator = ChartGenerator()
