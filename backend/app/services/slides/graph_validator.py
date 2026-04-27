"""
Graph validation service for slide deck charts.
Validates axis metadata, units, data ranges, and chart type appropriateness.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class GraphValidator:
    """Validates graph metadata and ensures data quality."""
    
    # Valid units for different contexts
    VALID_UNITS = {
        'financial': ['$', 'USD', '€', 'EUR', '£', 'GBP', '¥', 'JPY'],
        'percentage': ['%', 'percent'],
        'performance': ['points', 'score', 'rating'],
        'demographic': ['people', 'users', 'customers', 'persons'],
        'time': ['years', 'months', 'days', 'hours', 'minutes', 'seconds'],
        'quantity': ['units', 'items', 'count', 'number'],
        'none': [None, '', 'N/A']
    }
    
    # Expected chart types for different data patterns
    CHART_TYPE_RECOMMENDATIONS = {
        'time_series': ['line', 'bar'],
        'comparison': ['bar', 'scatter'],
        'distribution': ['pie', 'bar'],
        'correlation': ['scatter'],
        'trend': ['line']
    }
    
    def __init__(self):
        """Initialize the graph validator."""
        pass
    
    def validate_axis_labels(self, axis_metadata: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Validate that axis has proper labels.
        
        Args:
            axis_metadata: Dictionary with 'label' and 'unit' keys
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not axis_metadata:
            return True, "No axis metadata (acceptable for pie charts)"
        
        label = axis_metadata.get('label')
        if not label or not isinstance(label, str):
            return False, "Axis label is missing or invalid"
        
        if len(label.strip()) < 2:
            return False, f"Axis label too short: '{label}'"
        
        # Check for generic/unhelpful labels
        generic_labels = ['value', 'data', 'number', 'x', 'y']
        if label.lower() in generic_labels:
            return False, f"Axis label too generic: '{label}'. Should be more descriptive"
        
        return True, "Axis label is valid"
    
    def validate_axis_units(self, axis_metadata: Optional[Dict[str, Any]], context: str = "") -> Tuple[bool, str]:
        """
        Validate that axis units make sense for the context.
        
        Args:
            axis_metadata: Dictionary with 'label' and 'unit' keys
            context: Context string (e.g., slide title) to check unit appropriateness
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not axis_metadata:
            return True, "No axis metadata to validate"
        
        unit = axis_metadata.get('unit')
        label = axis_metadata.get('label', '').lower()
        context_lower = context.lower()
        
        # Unit can be None for categorical data
        if unit is None:
            # Check if unit SHOULD exist based on label
            if any(kw in label for kw in ['amount', 'revenue', 'profit', 'cost', 'price', 'sales']):
                return False, f"Financial label '{label}' should have a currency unit like '$'"
            if any(kw in label for kw in ['percentage', 'rate', 'growth']):
                return False, f"Percentage label '{label}' should have '%' unit"
            return True, "Unit is None (acceptable for categorical data)"
        
        # Validate unit format
        if not isinstance(unit, str):
            return False, f"Unit must be a string, got {type(unit)}"
        
        # Check if unit matches context
        if any(kw in context_lower for kw in ['revenue', 'profit', 'cost', 'price', 'financial']):
            if unit not in self.VALID_UNITS['financial']:
                return False, f"Financial context should use currency unit, got '{unit}'"
        
        if any(kw in context_lower for kw in ['percentage', 'rate', 'growth', 'share']):
            if unit not in self.VALID_UNITS['percentage']:
                return False, f"Percentage context should use '%' unit, got '{unit}'"
        
        if any(kw in label for kw in ['people', 'users', 'customers', 'population']):
            if unit not in self.VALID_UNITS['demographic']:
                return False, f"Demographic label should use people/users unit, got '{unit}'"
        
        return True, f"Unit '{unit}' is valid"
    
    def validate_data_range(self, axis_metadata: Optional[Dict[str, Any]], values: List[float]) -> Tuple[bool, str]:
        """
        Validate that data ranges are reasonable.
        
        Args:
            axis_metadata: Dictionary with min_value and max_value
            values: List of actual data values
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not axis_metadata:
            return True, "No axis metadata to validate"
        
        if not values:
            return False, "No data values provided"
        
        # Extract numeric values (handle tuples for scatter plots)
        numeric_values = []
        for v in values:
            if isinstance(v, (list, tuple)):
                numeric_values.extend([x for x in v if isinstance(x, (int, float))])
            elif isinstance(v, (int, float)):
                numeric_values.append(v)
        
        if not numeric_values:
            return False, "No numeric values found in data"
        
        actual_min = min(numeric_values)
        actual_max = max(numeric_values)
        
        # Check if metadata min/max are set
        meta_min = axis_metadata.get('min_value')
        meta_max = axis_metadata.get('max_value')
        
        if meta_min is not None and meta_max is not None:
            # Validate metadata matches actual data
            if abs(meta_min - actual_min) > 0.1:
                return False, f"Metadata min ({meta_min}) doesn't match actual min ({actual_min})"
            if abs(meta_max - actual_max) > 0.1:
                return False, f"Metadata max ({meta_max}) doesn't match actual max ({actual_max})"
        
        # Check for reasonable ranges
        data_range = actual_max - actual_min
        if data_range <= 0:
            return False, f"Data has no variation: all values ~{actual_min}"
        
        # Check for extreme outliers (values 10x outside normal range)
        mean_val = sum(numeric_values) / len(numeric_values)
        outliers = [v for v in numeric_values if abs(v - mean_val) > data_range * 5]
        if outliers:
            return False, f"Found {len(outliers)} extreme outliers in data"
        
        # Validate percentage data
        unit = axis_metadata.get('unit')
        if unit in self.VALID_UNITS['percentage']:
            if actual_min < 0 or actual_max > 100:
                return False, f"Percentage data should be 0-100, got range [{actual_min}, {actual_max}]"
        
        return True, f"Data range [{actual_min:.2f}, {actual_max:.2f}] is valid"
    
    def validate_chart_type_fit(self, chart_type: str, labels: List[str], values: List, slide_title: str = "") -> Tuple[bool, str]:
        """
        Validate that the chart type is appropriate for the data.
        
        Args:
            chart_type: Type of chart (bar, line, pie, scatter)
            labels: Data labels
            values: Data values
            slide_title: Slide title for context
        
        Returns:
            Tuple of (is_valid, message)
        """
        title_lower = slide_title.lower()
        
        # Detect data pattern
        is_time_series = any(kw in title_lower for kw in ['trend', 'over time', 'timeline', 'quarter', 'month', 'year'])
        is_comparison = any(kw in title_lower for kw in ['compare', 'comparison', 'versus', 'vs'])
        is_distribution = any(kw in title_lower for kw in ['distribution', 'breakdown', 'share', 'composition'])
        is_correlation = any(kw in title_lower for kw in ['correlation', 'relationship', 'vs'])
        
        # Check time-series labels
        has_time_labels = any(label in str(labels[0]) if labels else '' for label in ['Q1', 'Q2', 'Jan', 'Week', 'Month'])
        
        # Validate chart type appropriateness
        if chart_type == "line":
            if not (is_time_series or has_time_labels):
                return False, f"Line chart used for '{slide_title}' but no time-series context detected. Consider bar chart."
            if len(labels) < 3:
                return False, f"Line chart needs at least 3 data points, got {len(labels)}"
        
        elif chart_type == "pie":
            if not is_distribution:
                return False, f"Pie chart used for '{slide_title}' but no distribution context detected"
            if len(labels) < 2 or len(labels) > 8:
                return False, f"Pie chart should have 2-8 slices, got {len(labels)}"
            # Check if values sum to reasonable total
            if values and all(isinstance(v, (int, float)) for v in values):
                total = sum(values)
                if total < 50 or total > 150:  # Should be ~100 for percentages
                    return False, f"Pie chart values should sum to ~100, got {total:.2f}"
        
        elif chart_type == "scatter":
            if not is_correlation:
                return False, f"Scatter chart used for '{slide_title}' but no correlation context detected"
            if len(values) < 10:
                return False, f"Scatter chart needs at least 10 points, got {len(values)}"
        
        elif chart_type == "bar":
            if len(labels) > 15:
                return False, f"Bar chart has too many categories ({len(labels)}), consider grouping or using different visualization"
        
        return True, f"{chart_type.capitalize()} chart is appropriate for this data"
    
    def validate_graph(
        self,
        chart_type: str,
        labels: List[str],
        values: List,
        axis_metadata: Dict[str, Any],
        slide_title: str = ""
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of a graph.
        
        Args:
            chart_type: Type of chart
            labels: Data labels
            values: Data values
            axis_metadata: Dictionary with x_axis, y_axis metadata
            slide_title: Slide title for context
        
        Returns:
            Dictionary with validation results: {
                'is_valid': bool,
                'warnings': List[str],
                'errors': List[str],
                'validation_details': Dict
            }
        """
        warnings = []
        errors = []
        validation_details = {}
        
        # Extract x and y axis metadata
        x_axis = axis_metadata.get('x_axis')
        y_axis = axis_metadata.get('y_axis')
        
        # Validate X-axis
        x_label_valid, x_label_msg = self.validate_axis_labels(x_axis)
        validation_details['x_axis_label'] = {'valid': x_label_valid, 'message': x_label_msg}
        if not x_label_valid and chart_type != "pie":
            warnings.append(f"X-axis: {x_label_msg}")
        
        # Validate Y-axis
        y_label_valid, y_label_msg = self.validate_axis_labels(y_axis)
        validation_details['y_axis_label'] = {'valid': y_label_valid, 'message': y_label_msg}
        if not y_label_valid and chart_type != "pie":
            warnings.append(f"Y-axis: {y_label_msg}")
        
        # Validate X-axis units
        x_unit_valid, x_unit_msg = self.validate_axis_units(x_axis, slide_title)
        validation_details['x_axis_unit'] = {'valid': x_unit_valid, 'message': x_unit_msg}
        if not x_unit_valid:
            warnings.append(f"X-axis unit: {x_unit_msg}")
        
        # Validate Y-axis units
        y_unit_valid, y_unit_msg = self.validate_axis_units(y_axis, slide_title)
        validation_details['y_axis_unit'] = {'valid': y_unit_valid, 'message': y_unit_msg}
        if not y_unit_valid:
            errors.append(f"Y-axis unit: {y_unit_msg}")
        
        # Validate data range for Y-axis
        if chart_type != "pie" and y_axis:
            range_valid, range_msg = self.validate_data_range(y_axis, values)
            validation_details['data_range'] = {'valid': range_valid, 'message': range_msg}
            if not range_valid:
                errors.append(f"Data range: {range_msg}")
        
        # Validate chart type appropriateness
        chart_type_valid, chart_type_msg = self.validate_chart_type_fit(chart_type, labels, values, slide_title)
        validation_details['chart_type'] = {'valid': chart_type_valid, 'message': chart_type_msg}
        if not chart_type_valid:
            warnings.append(f"Chart type: {chart_type_msg}")
        
        # Overall validation status
        is_valid = len(errors) == 0
        
        result = {
            'is_valid': is_valid,
            'warnings': warnings,
            'errors': errors,
            'validation_details': validation_details,
            'summary': f"Graph validation: {'PASSED' if is_valid else 'FAILED'} with {len(warnings)} warnings and {len(errors)} errors"
        }
        
        # Log validation results
        if errors:
            logger.warning(f"Graph validation failed for '{slide_title}': {errors}")
        elif warnings:
            logger.info(f"Graph validation passed with warnings for '{slide_title}': {warnings}")
        else:
            logger.info(f"Graph validation passed for '{slide_title}'")
        
        return result


# Global instance
graph_validator = GraphValidator()
