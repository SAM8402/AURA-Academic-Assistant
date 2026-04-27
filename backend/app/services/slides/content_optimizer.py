"""
Utility functions for optimizing slide content length and quality.
Provides word counting, content truncation, and validation functions.
"""

import re
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class ContentOptimizer:
    """Optimizes slide content for length, readability, and quality."""

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text, ignoring Markdown syntax.
        
        Args:
            text: Text to count
        
        Returns:
            Word count
        """
        # Remove Markdown syntax
        text = re.sub(r'[#*_\[\]()]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Count words
        return len(text.split())

    @staticmethod
    def truncate_to_word_limit(text: str, max_words: int, preserve_sentences: bool = True) -> str:
        """
        Truncate text to a maximum word count, optionally preserving complete sentences.
        
        Args:
            text: Text to truncate
            max_words: Maximum number of words
            preserve_sentences: If True, truncates at sentence boundaries
        
        Returns:
            Truncated text with ellipsis if needed
        """
        word_count = ContentOptimizer.count_words(text)
        
        if word_count <= max_words:
            return text
        
        if preserve_sentences:
            # Split by sentences (roughly)
            sentences = re.split(r'(?<=[.!?])\s+', text)
            current_words = 0
            result_sentences = []
            
            for sentence in sentences:
                sentence_words = ContentOptimizer.count_words(sentence)
                if current_words + sentence_words <= max_words:
                    result_sentences.append(sentence)
                    current_words += sentence_words
                else:
                    break
            
            result = ' '.join(result_sentences)
            if len(result) < len(text):
                result += '...'
            return result
        else:
            # Just truncate at word boundary
            words = text.split()[:max_words]
            return ' '.join(words) + '...'

    @staticmethod
    def validate_content_length(slide: Dict[str, Any], has_graph: bool = False) -> Tuple[bool, str, int]:
        """
        Validate slide content length is within acceptable ranges.
        
        Args:
            slide: Slide dictionary with 'title' and 'content'
            has_graph: Whether the slide has a graph
        
        Returns:
            Tuple of (is_valid, message, word_count)
        """
        content = slide.get('content', '')
        word_count = ContentOptimizer.count_words(content)
        
        if has_graph:
            max_words = 80
            ideal_range = (40, 80)
            too_long_msg = f"Graph slide content is {word_count} words (ideal: {ideal_range[0]}-{ideal_range[1]}). Consider shortening."
            too_short_msg = f"Graph slide content is only {word_count} words. Add a bit more context if possible."
        else:
            max_words = 200
            ideal_range = (120, 180)
            too_long_msg = f"Content is {word_count} words (ideal: {ideal_range[0]}-{ideal_range[1]}). Consider shortening."
            too_short_msg = f"Content is only {word_count} words. Add more detail if possible."
        
        if word_count > max_words:
            return False, too_long_msg, word_count
        elif word_count < ideal_range[0]:
            return True, too_short_msg, word_count  # Still valid, just notify
        else:
            return True, f"Content is {word_count} words - good length.", word_count

    @staticmethod
    def enhance_content_with_metrics(slides: List[Dict[str, Any]], has_graphs: bool = False) -> List[Dict[str, Any]]:
        """
        Enhance slides with content metrics and optionally truncate content.
        
        Args:
            slides: List of slide dictionaries
            has_graphs: Whether slides have graphs
        
        Returns:
            Enhanced slides with metrics
        """
        enhanced_slides = []
        graph_slide_indices = []
        
        # Identify which slides likely have graphs based on keywords
        if has_graphs:
            chart_keywords = ['data', 'trend', 'growth', 'comparison', 'analysis', 'performance',
                            'statistics', 'metrics', 'results', 'distribution', 'visualization']
            for idx, slide in enumerate(slides):
                title = slide.get('title', '').lower()
                content = slide.get('content', '').lower()
                has_keywords = any(kw in title or kw in content for kw in chart_keywords)
                if has_keywords and idx not in [0, len(slides)-1]:  # Skip intro and conclusion
                    graph_slide_indices.append(idx)
        
        for idx, slide in enumerate(slides):
            slide_copy = slide.copy()
            has_graph = idx in graph_slide_indices
            max_words = 120 if has_graph else 200
            
            # Add metrics
            word_count = ContentOptimizer.count_words(slide_copy.get('content', ''))
            slide_copy['_content_metrics'] = {
                'word_count': word_count,
                'has_graph': has_graph,
                'within_limit': word_count <= max_words,
                'recommended_max': max_words
            }
            
            # Optionally truncate if too long
            if word_count > max_words:
                slide_copy['content'] = ContentOptimizer.truncate_to_word_limit(
                    slide_copy['content'],
                    max_words,
                    preserve_sentences=True
                )
                logger.info(f"Truncated slide {idx} from {word_count} to {ContentOptimizer.count_words(slide_copy['content'])} words")
            
            enhanced_slides.append(slide_copy)
        
        return enhanced_slides

    @staticmethod
    def generate_content_summary(slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics about slide content.
        
        Args:
            slides: List of slide dictionaries
        
        Returns:
            Dictionary with summary statistics
        """
        total_words = sum(ContentOptimizer.count_words(s.get('content', '')) for s in slides)
        avg_words = total_words // len(slides) if slides else 0
        
        word_counts = [ContentOptimizer.count_words(s.get('content', '')) for s in slides]
        max_words = max(word_counts) if word_counts else 0
        min_words = min(word_counts) if word_counts else 0
        
        slides_with_metrics = [s for s in slides if '_content_metrics' in s]
        within_limit = sum(1 for s in slides_with_metrics if s['_content_metrics']['within_limit'])
        
        return {
            'total_slides': len(slides),
            'total_words': total_words,
            'average_words_per_slide': avg_words,
            'max_words': max_words,
            'min_words': min_words,
            'slides_within_limit': within_limit,
            'slides_exceeding_limit': len(slides_with_metrics) - within_limit
        }


# Global instance
content_optimizer = ContentOptimizer()
