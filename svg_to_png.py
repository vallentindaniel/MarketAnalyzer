"""
Convert SVG to PNG
"""
import cairosvg

# Convert SVG to PNG
cairosvg.svg2png(
    url='static/img/market_analyzer_screenshot.svg', 
    write_to='static/img/market_analyzer_screenshot.png',
    output_width=800,
    output_height=400
)

print("Conversion completed: SVG image converted to PNG successfully.")