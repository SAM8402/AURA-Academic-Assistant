"""
Simple test script to verify chart generation functionality.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.slides.chart_generator import chart_generator

def test_chart_generation():
    print("Testing chart generation...")
    
    # Test bar chart
    print("\n1. Testing bar chart generation...")
    labels, values = chart_generator.generate_synthetic_data(
        slide_title="Sales Growth Analysis",
        chart_type="bar",
        slide_index=1
    )
    print(f"   Generated {len(labels)} labels: {labels[:3]}...")
    print(f"   Generated {len(values)} values: {values[:3]}...")
    
    image_uri = chart_generator.generate_chart_image(
        chart_type="bar",
        title="Sales Growth",
        labels=labels,
        values=values,
        slide_title="Sales Growth Analysis",
        slide_index=1
    )
    
    if image_uri:
        print(f"   ✓ Bar chart generated successfully ({len(image_uri)} chars)")
    else:
        print("   ✗ Bar chart generation failed")
    
    # Test line chart
    print("\n2. Testing line chart generation...")
    labels, values = chart_generator.generate_synthetic_data(
        slide_title="Performance Trend Over Time",
        chart_type="line",
        slide_index=2
    )
    print(f"   Generated {len(labels)} labels: {labels[:3]}...")
    print(f"   Generated {len(values)} values: {[round(v, 1) for v in values[:3]]}...")
    
    image_uri = chart_generator.generate_chart_image(
        chart_type="line",
        title="Performance Trend",
        labels=labels,
        values=values,
        slide_title="Performance Trend Over Time",
        slide_index=2
    )
    
    if image_uri:
        print(f"   ✓ Line chart generated successfully ({len(image_uri)} chars)")
    else:
        print("   ✗ Line chart generation failed")
    
    # Test pie chart
    print("\n3. Testing pie chart generation...")
    labels, values = chart_generator.generate_synthetic_data(
        slide_title="Market Share Distribution",
        chart_type="pie",
        slide_index=3
    )
    print(f"   Generated {len(labels)} labels: {labels}")
    print(f"   Generated {len(values)} values: {[round(v, 1) for v in values]}...")
    print(f"   Sum: {sum(values):.1f}%")
    
    image_uri = chart_generator.generate_chart_image(
        chart_type="pie",
        title="Market Share",
        labels=labels,
        values=values,
        slide_title="Market Share Distribution",
        slide_index=3
    )
    
    if image_uri:
        print(f"   ✓ Pie chart generated successfully ({len(image_uri)} chars)")
    else:
        print("   ✗ Pie chart generation failed")
    
    print("\n✓ All chart generation tests completed!")

if __name__ == "__main__":
    test_chart_generation()
