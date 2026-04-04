"""
Service for generating and refining slide decks using an LLM.
"""

import json
import logging
import random
from typing import List, Dict, Any, Optional
from enum import Enum

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import PromptTemplate
    from pydantic import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseModel = object
    # Create a fallback Field that accepts any arguments but does nothing
    def Field(*args, **kwargs):
        return None
    ChatGoogleGenerativeAI = None
    JsonOutputParser = None
    PromptTemplate = None

from app.core.config import settings
from app.services.chart_generator import chart_generator
from app.services.content_optimizer import content_optimizer
from app.services.graph_validator import graph_validator

logger = logging.getLogger(__name__)


class GraphType(str, Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"


class GraphData(BaseModel):
    type: GraphType
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]


class Slide(BaseModel):
    """Pydantic model for a single slide's structure."""
    title: str = Field(description="The concise title of the slide.")
    content: str = Field(description="The detailed content of the slide in Markdown format. Use headings, lists, and bold text.")
    graph_data: Optional[GraphData] = Field(None, description="Optional graph data for the slide.")
    graph_image: Optional[str] = Field(None, description="Optional base64 Data URI of chart image (PNG).")


class SlideDeck(BaseModel):
    """Pydantic model for the overall slide deck structure."""
    slides: List[Slide] = Field(description="A list of slide objects.")


class SlideDeckPreview(BaseModel):
    """Preview of the slide deck."""
    outline: List[str] = Field(description="Bullet points outlining the slide deck content.")


class SlideDeckService:
    """
    A service to generate and update slide decks using LangChain and Google Gemini.
    """

    def __init__(self):
        """Initializes the Slide Deck Service."""
        self.llm = None
        self.parser = None
        self.preview_parser = None

        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not installed. Slide deck generation will be disabled.")
            return

        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not found. Slide deck generation will be disabled.")
            return

        try:
            self.parser = JsonOutputParser(pydantic_object=SlideDeck)
            self.preview_parser = JsonOutputParser(pydantic_object=SlideDeckPreview)
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7,
            )
            logger.info(f"[OK] SlideDeckService initialized with Gemini model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Gemini LLM for SlideDeckService: {e}")

    async def generate_preview(
        self,
        course_name: str,
        topics: List[str],
        num_slides: int,
        description: str,
        format: str
    ) -> Dict[str, Any]:
        """Generates a preview outline of the slide deck."""
        if not self.llm:
            return {"error": "Slide deck service is not configured."}

        prompt_template = """
        You are an expert instructional designer creating a slide deck outline for the university course "{course_name}".

        **Requirements:**
        - **Topics to cover:** {topics}
        - **Total Number of Slides:** {num_slides}
        - **Description:** {description}
        - **Format:** {format} (presentation: concise, bullet points; document: detailed paragraphs)

        **Instructions:**
        Provide a high-level outline as a list of bullet points describing what each slide will contain.

        **Output Format:**
        You MUST provide the output as a single, valid JSON object with an "outline" array of strings.
        {format_instructions}
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["course_name", "topics", "num_slides", "description", "format"],
            partial_variables={"format_instructions": self.preview_parser.get_format_instructions()}
        )

        chain = prompt | self.llm | self.preview_parser

        try:
            logger.info(f"Generating preview for {num_slides} slides for course: {course_name}")
            preview_data = await chain.ainvoke({
                "course_name": course_name,
                "topics": ", ".join(topics),
                "num_slides": num_slides,
                "description": description,
                "format": format,
            })
            logger.info("Successfully generated slide deck preview.")
            return preview_data
        except Exception as e:
            logger.error("Failed to generate preview", exc_info=True)
            return {"error": "An error occurred while generating the preview. Please try again later."}

    async def generate_slides(
        self,
        course_name: str,
        topics: List[str],
        num_slides: int,
        description: str,
        format: str,
        include_graphs: bool,
        graph_types: Optional[List[GraphType]]
    ) -> Dict[str, Any]:
        """Generates slide deck content based on provided topics."""
        if not self.llm:
            return {"error": "Slide deck service is not configured."}

        # Determine content length based on format and whether graphs are included
        if format == "presentation":
            regular_slide_words = "150-200"
            graph_slide_words = "80-120"
            content_style = "concise bullet points and short paragraphs"
        else:
            regular_slide_words = "300-400"
            graph_slide_words = "200-250"
            content_style = "detailed explanations and longer content"

        graph_instruction = ""
        graph_emphasis = ""
        if include_graphs and graph_types:
            graph_instruction = f"""
        - **Include Graphs:** For approximately 30-40% of content slides (excluding intro and summary), include `graph_data` with one of these types: {', '.join([gt.value for gt in graph_types])}.
        - **Critical:** When a slide has `graph_data`, limit the body content to {graph_slide_words} words MAXIMUM.
          The graph is the focal point - keep explanatory text brief and concise.
          Use bullet points with 1-2 lines per point.
        - Generate appropriate, meaningful data for the graph based on the slide content.
        """
            graph_emphasis = f"""
    **WORD COUNT ENFORCEMENT FOR GRAPH SLIDES:**
    - If you add graph_data to a slide: the body content MUST be {graph_slide_words} words or less
    - Count your words carefully
    - Focus on key insights, let the visualization carry the message
    - If content exceeds {graph_slide_words} words, remove the graph_data instead
    """

        prompt_template = """
        You are an expert instructional designer creating a professional slide deck for the university course "{course_name}".

        **Requirements:**
        - **Topics to cover:** {topics}
        - **Total Number of Slides:** {num_slides}
        - **Description:** {description}
        - **Format:** {format} ({content_style})
        - **Course Level:** University-level, assume intermediate knowledge
        {graph_instruction}

        **CRITICAL: Word Count Limits (strictly enforce these):**
        - Regular content slides: {regular_slide_words} words (excluding title)
        - Graph slides (with graph_data): {graph_slide_words} words MAXIMUM (excluding title)
        {graph_emphasis}

        **Instructions for Slide Creation:**
        1. Create a logical flow starting with an introduction/agenda slide and ending with a summary/conclusion.
        2. For each slide:
           - Provide a clear, concise `title` (3-15 words)
           - Write `content` in Markdown format using **bold**, *italic*, bullet points, and headers
           - Use bullet points when listing concepts (• for bullets, not numbers unless showing sequence)
        
        3. Content Quality:
           - Each bullet point should be 1-2 lines maximum
           - Write for clarity and conciseness
           - Suitable for university-level audience
           - Bold key terms, use *italics* for emphasis
        
        4. Graph Placement Strategy:
           - Identify slides with data, trends, comparisons, or metrics (keywords: data, analysis, performance, growth, distribution, metrics)
           - For these slides, add `graph_data` with the appropriate chart type
           - When adding graph_data: KEEP CONTENT UNDER {graph_slide_words} WORDS
           - Title should clearly indicate what the graph shows
        
        5. Data for Graphs:
           - Ensure data makes sense in context of the slide
           - Use realistic values and ranges appropriate for the topic
           - **IMPORTANT:** Use meaningful category names based on context, NEVER generic "Item 1, Item 2"
           - Examples of meaningful labels:
             • Financial slides: Use regions (North, South, East, West), products (Product A, Product B, Premium, Standard), quarters (Q1, Q2, Q3, Q4), or departments
             • Performance slides: Use team names, categories (Frontend, Backend, DevOps), metrics (CPU, Memory, Disk)
             • Demographic slides: Use age groups (18-25, 26-35, 36-45, 45+), regions, or segments
             • Time series: Use months (Jan, Feb, Mar) or quarters (Q1, Q2, Q3, Q4) based on data span
           - Make the graph tell a meaningful story
        
        6. Formatting:
           - Use Markdown liberally for emphasis (bold key terms, headers for subsections)
           - Use bullet points for lists (cleaner than numbered lists unless showing sequence)
           - Keep paragraphs short (2-3 sentences maximum)
           - Avoid walls of text

        **Validation Before Output:**
        - Word count check: Regular slides {regular_slide_words} words, graph slides {graph_slide_words} words
        - All slides have titles
        - Content is in Markdown format
        - Graph slides have graph_data and brief explanations
        - No slide is empty

        **Output Format:**
        You MUST provide the output as a single, valid JSON object that strictly follows this format. Do not include any other text or markdown.
        {format_instructions}
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["course_name", "topics", "num_slides", "description", "format", "content_style", "regular_slide_words", "graph_slide_words", "graph_instruction", "graph_emphasis"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        chain = prompt | self.llm | self.parser

        try:
            logger.info(f"Generating {num_slides} slides for course: {course_name}, topics: {topics}")
            deck_data = await chain.ainvoke({
                "course_name": course_name,
                "topics": ", ".join(topics),
                "num_slides": num_slides,
                "description": description,
                "format": format,
                "content_style": content_style,
                "regular_slide_words": regular_slide_words,
                "graph_slide_words": graph_slide_words,
                "graph_instruction": graph_instruction,
                "graph_emphasis": graph_emphasis,
            })
            
            # Post-process: Add charts to appropriate slides
            if include_graphs and graph_types and "slides" in deck_data:
                slides = deck_data["slides"]
                deck_data["slides"] = self._add_charts_to_slides(
                    slides, 
                    graph_types, 
                    course_name
                )
            
            # NEW: Enforce content limits and collect metrics
            if "slides" in deck_data:
                logger.info("Applying content optimization and metrics...")
                deck_data["slides"] = content_optimizer.enhance_content_with_metrics(
                    deck_data["slides"],
                    has_graphs=include_graphs
                )
                
                # Log content statistics
                summary = content_optimizer.generate_content_summary(deck_data["slides"])
                logger.info(f"Content Summary: {summary}")
                logger.info(f"Slides within word limits: {summary['slides_within_limit']}/{summary['total_slides']}")
            
            logger.info("Successfully generated slide deck content.")
            return deck_data
        except Exception as e:
            logger.error("Failed to generate or parse slide deck", exc_info=True)
            return {"error": "An error occurred while generating the slides. Please try again later."}
    
    def _add_charts_to_slides(
        self, 
        slides: List[Dict[str, Any]], 
        graph_types: List[GraphType],
        course_name: str
    ) -> List[Dict[str, Any]]:
        """
        Add chart images to slides that would benefit from visualization.
        
        Args:
            slides: List of slide dictionaries
            graph_types: Preferred chart types
            course_name: Course name for context
        
        Returns:
            Updated slides with graph_image and graph_data fields
        """
        # Skip first (intro) and last (summary) slides
        content_slides = slides[1:-1] if len(slides) > 2 else slides
        
        # Determine which slides should get charts (30-50% of content slides)
        num_charts = max(1, min(len(content_slides) // 2, 3))
        
        # Select slides for charts (prefer those with keywords)
        chart_keywords = ['data', 'trend', 'growth', 'comparison', 'analysis', 'performance', 
                         'statistics', 'metrics', 'results', 'distribution']
        
        scored_slides = []
        for idx, slide in enumerate(content_slides):
            title = slide.get('title', '').lower()
            content = slide.get('content', '').lower()
            score = sum(1 for kw in chart_keywords if kw in title or kw in content)
            scored_slides.append((score, idx, slide))
        
        # Sort by score and select top candidates
        scored_slides.sort(reverse=True, key=lambda x: x[0])
        selected_indices = [idx for _, idx, _ in scored_slides[:num_charts]]
        
        # Generate charts for selected slides
        for slide_idx in selected_indices:
            slide = content_slides[slide_idx]
            slide_title = slide.get('title', '')
            
            # Choose chart type (cycle through available types)
            chart_type = graph_types[slide_idx % len(graph_types)].value
            
            try:
                # Generate synthetic data
                labels, values = chart_generator.generate_synthetic_data(
                    slide_title=slide_title,
                    chart_type=chart_type,
                    slide_index=slide_idx
                )
                
                # Generate axis metadata
                axis_metadata = chart_generator.generate_axis_metadata(
                    slide_title=slide_title,
                    chart_type=chart_type,
                    labels=labels,
                    values=values
                )
                
                # Validate graph before rendering
                validation_result = graph_validator.validate_graph(
                    chart_type=chart_type,
                    labels=labels,
                    values=values,
                    axis_metadata=axis_metadata,
                    slide_title=slide_title
                )
                
                # Log validation results
                if not validation_result['is_valid']:
                    logger.warning(f"Graph validation failed for slide {slide_idx} '{slide_title}': {validation_result['errors']}")
                if validation_result['warnings']:
                    logger.info(f"Graph validation warnings for slide {slide_idx} '{slide_title}': {validation_result['warnings']}")
                
                # Generate chart image with axis metadata
                chart_title = f"{slide_title} - Visualization"
                graph_image = chart_generator.generate_chart_image(
                    chart_type=chart_type,
                    title=chart_title,
                    labels=labels,
                    values=values,
                    slide_title=slide_title,
                    slide_index=slide_idx,
                    axis_metadata=axis_metadata
                )
                
                if graph_image:
                    # Add both graph_image (for rendering) and graph_data (for metadata)
                    slide['graph_image'] = graph_image
                    
                    # Format graph_data for compatibility
                    if chart_type == "scatter" and values and isinstance(values[0], (list, tuple)):
                        # For scatter, extract x and y separately
                        x_vals, y_vals = zip(*values)
                        datasets = [
                            {"label": "Data Points", "data": list(y_vals)}
                        ]
                        labels_list = [f"Point {i+1}" for i in range(len(x_vals))]
                    else:
                        datasets = [{"label": "Values", "data": values}]
                        labels_list = labels
                    
                    # Include axis metadata and validation in graph_data
                    slide['graph_data'] = {
                        "type": chart_type,
                        "title": chart_title,
                        "labels": labels_list,
                        "datasets": datasets,
                        "x_axis": axis_metadata.get('x_axis'),
                        "y_axis": axis_metadata.get('y_axis'),
                        "data_description": axis_metadata.get('data_description'),
                        "data_source": axis_metadata.get('data_source'),
                        "validation": {
                            "is_valid": validation_result['is_valid'],
                            "warnings": validation_result['warnings']
                        }
                    }
                    
                    logger.info(f"Successfully added {chart_type} chart to slide {slide_idx}: {slide_title} (validation: {'PASSED' if validation_result['is_valid'] else 'FAILED WITH WARNINGS'})")
                else:
                    logger.warning(f"Chart generation returned None for slide {slide_idx}: {slide_title}. Skipping chart for this slide.")
            
            except Exception as chart_error:
                logger.error(f"Error generating chart for slide {slide_idx} '{slide_title}': {chart_error}. Continuing without chart for this slide.")
                # Continue without adding a chart for this slide
        
        return slides


slide_deck_service = SlideDeckService()
