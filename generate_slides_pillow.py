import os
import sys
import shutil
from PIL import Image, ImageDraw, ImageFont

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Brand Color Palette (matching refrence1.jpg)
BG_COLOR = (250, 246, 240)       # Warm light cream (#FAF6F0)
GRID_COLOR = (235, 230, 220)     # Muted grid lines (#EBE6DC)
TEXT_COLOR = (17, 17, 17)        # Dark carbon/black (#111111)
HIGHLIGHT_BG = (17, 17, 17)      # Dark box background
HIGHLIGHT_TEXT = (245, 166, 35)  # Orange accent text (#F5A623)
MUTED_TEXT = (80, 80, 80)        # Dark grey for body text
ACCENT_ORANGE = (245, 166, 35)   # Orange dots and accents

def draw_diamond(draw, cx, cy, size=8, color=(245, 166, 35)):
    """Draw a rotated square (diamond) for bullet points."""
    points = [
        (cx, cy - size),
        (cx + size, cy),
        (cx, cy + size),
        (cx - size, cy)
    ]
    draw.polygon(points, fill=color)

def draw_line_arrow(draw, x_start=800, y_center=1225, length=80, head_size=15, width=3, color=(17, 17, 17)):
    """Draw an elegant custom line-art navigation arrow."""
    x_end = x_start + length
    # Draw horizontal shaft
    draw.line([(x_start, y_center), (x_end, y_center)], fill=color, width=width)
    # Draw arrowhead wings
    draw.line([(x_end - head_size, y_center - head_size), (x_end, y_center)], fill=color, width=width)
    draw.line([(x_end - head_size, y_center + head_size), (x_end, y_center)], fill=color, width=width)

def draw_chevron_dots(draw, cx=850, cy=108, spacing=16):
    """Draw three right-pointing chevrons made of fading orange dots."""
    num_chevrons = 3
    for c in range(num_chevrons):
        # Scale size: rightmost chevron c=0 is largest, leftmost c=2 is smallest
        scale = 1.0 - (c * 0.3)
        radius = int(5.5 * scale)
        if radius < 2:
            radius = 2
            
        # Opacity simulation (blend with background cream color)
        alpha = 1.0 - (c * 0.35)
        r = int(245 * alpha + 250 * (1 - alpha))
        g = int(166 * alpha + 246 * (1 - alpha))
        b = int(35 * alpha + 240 * (1 - alpha))
        dot_color = (r, g, b)
        
        # Horizontal spacing offset (rightmost is shifted furthest right)
        chevron_base_x = cx + (num_chevrons - 1 - c) * spacing
        
        # Draw 5 rows forming the '>' chevron shape
        for row in range(5):
            if row == 0 or row == 4:
                x_offset = 0
            elif row == 1 or row == 3:
                x_offset = 1
            else:
                x_offset = 2
                
            x = chevron_base_x + x_offset * spacing
            y = cy + row * spacing
            
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=dot_color)

def draw_rotated_text_line(img, text, font, fill_color, bg_color, angle, x, y, pad_x=22, pad_y=12):
    """Render a text line (with optional background) rotated on a transparent sheet, then composite it."""
    # Measure text dimensions
    dummy = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy)
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    box_w = tw + pad_x * 2
    box_h = th + pad_y * 2
    
    # Ample margins on temporary canvas to prevent rotation clipping
    canvas_w = int(box_w * 1.5) + 100
    canvas_h = int(box_h * 2.0) + 100
    
    line_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    line_draw = ImageDraw.Draw(line_img)
    
    cx = canvas_w / 2
    cy = canvas_h / 2
    
    bx0 = cx - box_w / 2
    by0 = cy - box_h / 2
    bx1 = bx0 + box_w
    by1 = by0 + box_h
    
    if bg_color:
        line_draw.rectangle([bx0, by0, bx1, by1], fill=bg_color)
        
    tx = bx0 + pad_x - bbox[0]
    ty = by0 + pad_y - bbox[1]
    line_draw.text((tx, ty), text, font=font, fill=fill_color)
    
    # Rotate with smooth BICUBIC resampling
    rotated = line_img.rotate(angle, resample=Image.BICUBIC, expand=True)
    rot_w, rot_h = rotated.size
    
    target_cx = x + box_w / 2
    target_cy = y + box_h / 2
    
    px = int(target_cx - rot_w / 2)
    py = int(target_cy - rot_h / 2)
    
    img.paste(rotated, (px, py), rotated)

def create_base_canvas():
    """Create a 1080x1350 canvas with the warm cream color, grid lines, and chevron dot pattern."""
    img = Image.new("RGBA", (1080, 1350), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 1. Thin grid lines (54px spacing)
    spacing = 54
    for x in range(0, 1080, spacing):
        draw.line([(x, 0), (x, 1350)], fill=GRID_COLOR, width=1)
    for y in range(0, 1350, spacing):
        draw.line([(0, y), (1080, y)], fill=GRID_COLOR, width=1)
        
    # 2. Chevron dots pattern at top-right
    draw_chevron_dots(draw, cx=860, cy=108, spacing=16)
            
    return img

def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width."""
    words = text.split(' ')
    lines = []
    current_line = []
    
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
        
    return lines

def draw_header_quotes(draw, font_quotes):
    """Draw double quote outlines at top-left, masking grid lines behind them."""
    # 1. Mask background grid line with background color solid quote
    draw.text((108, 140), "“", font=font_quotes, fill=BG_COLOR)
    # 2. Draw outline quotes
    draw.text((108, 140), "“", font=font_quotes, fill=None, stroke_width=3, stroke_fill=TEXT_COLOR)

def draw_footer_elements(draw, font_small, font_arrow, page_num):
    """Draw footer social handle, custom navigation arrow, and rotated page indicator."""
    # Bottom Left Social Handle
    draw.text((108, 1220), "@goran.dotin", font=font_small, fill=TEXT_COLOR)
    
    # Bottom Right Navigation Arrow
    draw_line_arrow(draw, x_start=800, y_center=1230, length=70, head_size=12, width=3, color=TEXT_COLOR)
    
    # Bottom Right Page Number (rotated 90 degrees counter-clockwise)
    txt_img = Image.new("RGBA", (200, 50), (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    txt_draw.text((0, 10), f"page {page_num:02d}", font=font_small, fill=TEXT_COLOR)
    
    rotated = txt_img.rotate(90, expand=True)
    return rotated

def draw_bullet_line(draw, line, font_bold, text_y, card_x_start=138):
    """Draw bullet point lines using clean vector diamonds and colored text labels."""
    accent_orange = (245, 166, 35)
    red_color = (239, 68, 68)
    text_color = (17, 17, 17)
    
    # Clean symbol prefixes
    clean_line = line
    if clean_line.startswith("✦"):
        clean_line = clean_line[1:].strip()
    elif clean_line.startswith("*"):
        clean_line = clean_line[1:].strip()
        
    # Check highlight tags
    if clean_line.startswith("THE AI CURE:"):
        draw_diamond(draw, card_x_start + 8, text_y + 18, size=8, color=accent_orange)
        draw.text((card_x_start + 28, text_y), "THE AI CURE:", font=font_bold, fill=accent_orange)
        rem = clean_line.replace("THE AI CURE:", "").strip()
        bbox = draw.textbbox((card_x_start + 28, text_y), "THE AI CURE: ", font=font_bold)
        draw.text((bbox[2], text_y), rem, font=font_bold, fill=text_color)
        
    elif clean_line.startswith("THE BOTTLENECK:"):
        draw_diamond(draw, card_x_start + 8, text_y + 18, size=8, color=red_color)
        draw.text((card_x_start + 28, text_y), "THE BOTTLENECK:", font=font_bold, fill=red_color)
        rem = clean_line.replace("THE BOTTLENECK:", "").strip()
        bbox = draw.textbbox((card_x_start + 28, text_y), "THE BOTTLENECK: ", font=font_bold)
        draw.text((bbox[2], text_y), rem, font=font_bold, fill=text_color)
        
    elif clean_line.startswith("THE ADVANTAGE:"):
        draw_diamond(draw, card_x_start + 8, text_y + 18, size=8, color=accent_orange)
        draw.text((card_x_start + 28, text_y), "THE ADVANTAGE:", font=font_bold, fill=accent_orange)
        rem = clean_line.replace("THE ADVANTAGE:", "").strip()
        bbox = draw.textbbox((card_x_start + 28, text_y), "THE ADVANTAGE: ", font=font_bold)
        draw.text((bbox[2], text_y), rem, font=font_bold, fill=text_color)
        
    else:
        # Standard line
        draw_diamond(draw, card_x_start + 8, text_y + 18, size=6, color=accent_orange)
        draw.text((card_x_start + 28, text_y), clean_line, font=font_bold, fill=text_color)

def generate_slide(data, out_path):
    """Generate a single slide using configuration options and save it to disk."""
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    font_title = ImageFont.truetype("arialbd.ttf", 64)
    font_body = ImageFont.truetype("arial.ttf", 34)
    font_bold = ImageFont.truetype("arialbd.ttf", 34)
    font_small = ImageFont.truetype("arialbd.ttf", 22)
    font_quotes = ImageFont.truetype("georgia.ttf", 160)
    
    # Draw outline quotes at top-left
    draw_header_quotes(draw, font_quotes)
    
    # Top Left Label
    draw.text((108, 108), data["top_label"], font=font_small, fill=TEXT_COLOR)
    
    slide_type = data.get("type", "body")
    
    if slide_type == "cover":
        current_y = 320
        title_lines = data["title_lines"]
        for line, is_highlight in title_lines:
            if is_highlight:
                draw_rotated_text_line(img, line, font_title, HIGHLIGHT_TEXT, HIGHLIGHT_BG, -2, 108, current_y)
            else:
                draw.text((108, current_y), line, font=font_title, fill=TEXT_COLOR)
            current_y += 85
            
    elif slide_type == "body":
        current_y = 320
        title_lines = data["title_lines"]
        for line, is_highlight in title_lines:
            if is_highlight:
                draw_rotated_text_line(img, line, font_title, HIGHLIGHT_TEXT, HIGHLIGHT_BG, -2, 108, current_y)
            else:
                draw.text((108, current_y), line, font=font_title, fill=TEXT_COLOR)
            current_y += 85
            
        current_y += 30
        body_lines = wrap_text(data["body_text"], font_body, 864)
        for line in body_lines:
            draw.text((108, current_y), line, font=font_body, fill=MUTED_TEXT)
            current_y += 50
            
        # Composite glassmorphic translucent orange card at bottom
        if data.get("cure_text"):
            card_y = 860
            card_width = 864
            card_height = 220
            
            # Create overlay for proper alpha blending
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rounded_rectangle(
                [108, card_y, 108 + card_width, card_y + card_height],
                radius=14,
                fill=(245, 166, 35, 15),     # 6% opacity fill
                outline=(245, 166, 35, 180), # ~70% opacity border
                width=2
            )
            
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)
            
            # Draw text inside card
            cure_lines = wrap_text(data["cure_text"], font_bold, card_width - 60)
            text_y = card_y + 35
            for line in cure_lines:
                draw_bullet_line(draw, line, font_bold, text_y)
                text_y += 50
                
    elif slide_type == "stats":
        current_y = 320
        title_lines = data["title_lines"]
        for line, is_highlight in title_lines:
            if is_highlight:
                draw_rotated_text_line(img, line, font_title, HIGHLIGHT_TEXT, HIGHLIGHT_BG, -2, 108, current_y)
            else:
                draw.text((108, current_y), line, font=font_title, fill=TEXT_COLOR)
            current_y += 85
            
        current_y += 50
        font_stat_num = ImageFont.truetype("arialbd.ttf", 64)
        for num, label in data["stats"]:
            draw.text((108, current_y), num, font=font_stat_num, fill=ACCENT_ORANGE)
            bbox = draw.textbbox((108, current_y), num, font=font_stat_num)
            draw.text((bbox[2] + 30, current_y + 15), label, font=font_bold, fill=TEXT_COLOR)
            current_y += 110
            
    elif slide_type == "cta":
        current_y = 320
        title_lines = data["title_lines"]
        for line, is_highlight in title_lines:
            if is_highlight:
                draw_rotated_text_line(img, line, font_title, HIGHLIGHT_TEXT, HIGHLIGHT_BG, -2, 108, current_y)
            else:
                draw.text((108, current_y), line, font=font_title, fill=TEXT_COLOR)
            current_y += 85
            
        current_y += 40
        body_lines = wrap_text(data["body_text"], font_body, 864)
        for line in body_lines:
            draw.text((108, current_y), line, font=font_body, fill=MUTED_TEXT)
            current_y += 50
            
        card_y = 860
        card_width = 864
        card_height = 180
        
        # Draw CTA solid box (opaque black is fine directly on img)
        draw.rounded_rectangle(
            [108, card_y, 108 + card_width, card_y + card_height],
            radius=14,
            fill=HIGHLIGHT_BG,
            outline=ACCENT_ORANGE,
            width=2
        )
        
        trigger_lines = wrap_text(data["trigger_text"], font_bold, card_width - 60)
        text_y = card_y + 40
        for line in trigger_lines:
            words = line.split(" ")
            current_x = 138
            for w in words:
                word_font = font_bold
                if w.startswith("'") or w.endswith("'") or "DAY" in w:
                    word_fill = ACCENT_ORANGE
                else:
                    word_fill = (255, 255, 255)
                draw.text((current_x, text_y), w + " ", font=word_font, fill=word_fill)
                bbox = draw.textbbox((current_x, text_y), w + " ", font=word_font)
                current_x = bbox[2]
            text_y += 50
            
    # Draw footer page count and return rotated page label
    rotated = draw_footer_elements(draw, font_small, None, data["page_num"])
    img.paste(rotated, (965, 1140), rotated)
    
    # Save image
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.convert("RGB").save(out_path, "PNG")
    print(f"Saved: {out_path}")

def build_preview_page(post_id, caption, title, slide_count):
    """Generate HTML preview page with Instagram filmstrip preview for scheduler dashboard."""
    template_path = "c:\\Users\\ranja\\.gemini\\config\\plugins\\carousel-generator\\resources\\preview_template.html"
    if not os.path.exists(template_path):
        print(f"Warning: HTML template not found at {template_path}")
        return
        
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    slides_html = ""
    dots_html = ""
    for i in range(1, slide_count + 1):
        slides_html += f'<div class="ig-slide"><img src="slide_{i:02d}.png"></div>\n'
        dots_html += f'<span class="dot { "active" if i == 1 else "" }" onclick="currentSlide({i})"></span>\n'
        
    html = html.replace("{{POST_TITLE}}", title)
    html = html.replace("{{CAPTION_TEXT_PLACEHOLDER}}", caption)
    html = html.replace("{{TOTAL_SLIDES_COUNT}}", str(slide_count))
    html = html.replace("{{SLIDE_IMAGES_PLACEHOLDER}}", slides_html)
    html = html.replace("{{SLIDE_DOTS_PLACEHOLDER}}", dots_html)
    
    out_dir = f"d:\\InstagramPost\\post\\{post_id}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "preview.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved preview HTML: {out_path}")

def main():
    # Day 1: day_01_cart_recovery
    day1_slides = [
        {
            "type": "cover",
            "top_label": "D2C AUTOMATION: DAY 01/50",
            "page_num": 1,
            "title_lines": [
                ("Abandoned", False),
                ("cart recovery", False),
                ("Nahi Toh...", False),
                ("D2C Brand", True),
                ("Ka Kya Future?", False)
            ]
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 01/50",
            "page_num": 2,
            "title_lines": [
                ("The 70% Leak", False)
            ],
            "body_text": "D2C stores lose 70% of potential buyers at checkout. Sending standard automated email reminders gets ignored, ends up in spam folders, or gets buried. The ad spend is already wasted.",
            "cure_text": "✦ THE BOTTLENECK: Delayed answers to sizing, delivery times, or payment trust signals cause buyers to walk away."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 01/50",
            "page_num": 3,
            "title_lines": [
                ("Conversational", False),
                ("Cart Rescue", True)
            ],
            "body_text": "An autonomous AI WhatsApp agent triggers 15 minutes after a cart is abandoned. It answers shipping/product queries, handles sizing objections, and completes checkouts directly inside the chat.",
            "cure_text": "✦ THE AI CURE: Dynamically injects customer records and custom checkout link nodes for friction-free purchasing."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 01/50",
            "page_num": 4,
            "title_lines": [
                ("Instant", False),
                ("Conversion Lift", True)
            ],
            "body_text": "By addressing buyer questions and friction points inside WhatsApp in real-time, brands recover up to 45% of abandoned checkouts, directly boosting bottom-line profits.",
            "cure_text": "✦ THE ADVANTAGE: Scale order volume and customer lifetime value on complete autopilot."
        },
        {
            "type": "stats",
            "top_label": "D2C AUTOMATION: DAY 01/50",
            "page_num": 5,
            "title_lines": [
                ("Our Execution", False),
                ("Metrics", True)
            ],
            "stats": [
                ("99.9%", "System Uptime Guarantee"),
                ("500k+", "Daily Agent Actions Orchestrated"),
                ("<5 Hours", "Average Technical Response Time")
            ]
        },
        {
            "type": "cta",
            "top_label": "D2C AUTOMATION: DAY 01/50",
            "page_num": 6,
            "title_lines": [
                ("Stop letting", False),
                ("traffic leak.", True)
            ],
            "body_text": "Get a free 30-minute operational workflow audit. We will map your inventory bottlenecks and outline 3 custom AI agent deployments.",
            "trigger_text": "Comment 'DAY1' below and our AI agent will DM you your direct scoping invite instantly."
        }
    ]
    
    # Day 2: day_02_cod_confirmation_call
    day2_slides = [
        {
            "type": "cover",
            "top_label": "D2C AUTOMATION: DAY 02/50",
            "page_num": 1,
            "title_lines": [
                ("Confirming", False),
                ("COD orders", False),
                ("manually?", False),
                ("80% RTO", True),
                ("REDUCTION", True)
            ]
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 02/50",
            "page_num": 2,
            "title_lines": [
                ("The COD Killer", False)
            ],
            "body_text": "Every refused cash-on-delivery (COD) parcel is money burned on shipping and logistics. High RTO rates wipe out profitability for scaling D2C brands in India.",
            "cure_text": "✦ THE BOTTLENECK: Customers forget they ordered, double-order by mistake, or change their minds during delivery delay."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 02/50",
            "page_num": 3,
            "title_lines": [
                ("Autonomous", False),
                ("Verification", True)
            ],
            "body_text": "An AI voice agent calls each COD customer automatically before dispatch. It speaks in English or Hindi, confirms their purchase intent, verifies the delivery address, and logs confirmation in your CRM.",
            "cure_text": "✦ THE AI CURE: Automatically cancels unconfirmed or fake orders, reducing RTO shipments by up to 80%."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 02/50",
            "page_num": 4,
            "title_lines": [
                ("Drastic Cost", False),
                ("Savings", True)
            ],
            "body_text": "By filtering out bogus or accidental orders before they ever leave the warehouse, you save massive shipping overhead and keep your inventory active for real buyers.",
            "cure_text": "✦ THE ADVANTAGE: Improve warehouse operations and protect D2C margins automatically."
        },
        {
            "type": "stats",
            "top_label": "D2C AUTOMATION: DAY 02/50",
            "page_num": 5,
            "title_lines": [
                ("AI Agent", False),
                ("Performance", True)
            ],
            "stats": [
                ("80%", "Average RTO Reduction"),
                ("30 Sec", "Average Call Verification Time"),
                ("100%", "Automatic CRM/Logistics Sync")
            ]
        },
        {
            "type": "cta",
            "top_label": "D2C AUTOMATION: DAY 02/50",
            "page_num": 6,
            "title_lines": [
                ("Stop wasting", False),
                ("shipping cash.", True)
            ],
            "body_text": "Get a free 30-minute operational workflow audit. We will map your logistics bottlenecks and outline custom voice agent configurations.",
            "trigger_text": "Comment 'DAY2' below and our AI agent will DM you your direct scoping invite instantly."
        }
    ]

    # Day 3: day_03_dm_to_order
    day3_slides = [
        {
            "type": "cover",
            "top_label": "D2C AUTOMATION: DAY 03/50",
            "page_num": 1,
            "title_lines": [
                ("Converting DMs", False),
                ("to orders", False),
                ("manually?", False),
                ("10X FASTER", True),
                ("CHECKOUTS", True)
            ]
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 03/50",
            "page_num": 2,
            "title_lines": [
                ("The DM Drop-off", False)
            ],
            "body_text": "Customers DM you to buy, but manual copy-pasting of delivery details, sending bank transfer links, and creating Shopify draft orders manually takes minutes. By then, the customer has changed their mind.",
            "cure_text": "✦ THE BOTTLENECK: Delayed manual checkout links and address collections cause 70% of high-intent DM leads to drop off before buying."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 03/50",
            "page_num": 3,
            "title_lines": [
                ("Zero-Friction", False),
                ("DM Commerce", True)
            ],
            "body_text": "An AI agent automatically detects intent to buy, extracts delivery addresses and contact details from chat, and creates a Shopify order immediately. It sends a pre-filled direct checkout link in 5 seconds.",
            "cure_text": "✦ THE AI CURE: Turn conversations into sales instantly, processing orders 24/7 directly inside Instagram and WhatsApp."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 03/50",
            "page_num": 4,
            "title_lines": [
                ("Unlocking", False),
                ("Social Revenue", True)
            ],
            "body_text": "No more waking up to hundred unread buying DMs. The AI agent guides them from first inquiry to order placement, acting as a tireless 24/7 retail salesperson.",
            "cure_text": "✦ THE ADVANTAGE: Handle infinite buying conversations simultaneously without adding support staff."
        },
        {
            "type": "stats",
            "top_label": "D2C AUTOMATION: DAY 03/50",
            "page_num": 5,
            "title_lines": [
                ("Agent", False),
                ("Performance", True)
            ],
            "stats": [
                ("5 Sec", "Average Checkout Link Delivery"),
                ("10X", "Increase in Checkout Speed"),
                ("0%", "Manual Data Entry Mistakes")
            ]
        },
        {
            "type": "cta",
            "top_label": "D2C AUTOMATION: DAY 03/50",
            "page_num": 6,
            "title_lines": [
                ("Stop losing", False),
                ("social sales.", True)
            ],
            "body_text": "Get a free 30-minute operational workflow audit. We will map your DM sales funnel and outline custom checkout agent deployments.",
            "trigger_text": "Comment 'DAY3' below and our AI agent will DM you your direct scoping invite instantly."
        }
    ]

    # Day 4: day_04_return_exchange_agent
    day4_slides = [
        {
            "type": "cover",
            "top_label": "D2C AUTOMATION: DAY 04/50",
            "page_num": 1,
            "title_lines": [
                ("Manual returns", False),
                ("killing your", False),
                ("profits?", False),
                ("AUTOMATED", True),
                ("REVERSE LOGISTICS", True)
            ]
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 04/50",
            "page_num": 2,
            "title_lines": [
                ("The Return Nightmare", False)
            ],
            "body_text": "Processing returns manually eats up hours of customer support time. Verifying order details, checking return windows, booking reverse pickups, and sending labels drains resources.",
            "cure_text": "✦ THE BOTTLENECK: Back-and-forth messages for size returns frustrate buyers and increase your operational overhead."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 04/50",
            "page_num": 3,
            "title_lines": [
                ("Self-Serve", False),
                ("WhatsApp Returns", True)
            ],
            "body_text": "An AI WhatsApp agent verifies return eligibility using courier APIs, asks for product photos to verify condition, books reverse pickup via Delhivery/Shiprocket, and issues exchange orders.",
            "cure_text": "✦ THE AI CURE: Turn refund requests into size exchange orders automatically, saving product sales in the process."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 04/50",
            "page_num": 4,
            "title_lines": [
                ("Instant Support", False),
                ("Loves Exchanges", True)
            ],
            "body_text": "Customers request exchanges in their own time, and get confirmation labels in seconds. No waiting for support agents, no frustrating email threads. It builds massive customer trust.",
            "cure_text": "✦ THE ADVANTAGE: Scale your post-purchase experience while cutting operational return costs in half."
        },
        {
            "type": "stats",
            "top_label": "D2C AUTOMATION: DAY 04/50",
            "page_num": 5,
            "title_lines": [
                ("System", False),
                ("Efficiency", True)
            ],
            "stats": [
                ("90%", "Reduction in Return Support DMs"),
                ("<2 Mins", "Average Return Booking Time"),
                ("35%", "Refund Requests Saved into Exchanges")
            ]
        },
        {
            "type": "cta",
            "top_label": "D2C AUTOMATION: DAY 04/50",
            "page_num": 6,
            "title_lines": [
                ("Automate your", False),
                ("reverse logistics.", True)
            ],
            "body_text": "Get a free 30-minute operational workflow audit. We will analyze your return policies and map out self-serve exchange agents.",
            "trigger_text": "Comment 'DAY4' below and our AI agent will DM you your direct scoping invite instantly."
        }
    ]

    # Day 5: day_05_centralized_order_dashboard
    day5_slides = [
        {
            "type": "cover",
            "top_label": "D2C AUTOMATION: DAY 05/50",
            "page_num": 1,
            "title_lines": [
                ("Too many tabs", False),
                ("open to manage", False),
                ("your orders?", False),
                ("CENTRALIZED", True),
                ("AI DASHBOARD", True)
            ]
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 05/50",
            "page_num": 2,
            "title_lines": [
                ("Operational Chaos", False)
            ],
            "body_text": "Fulfilling orders from Shopify, manual Instagram orders, WhatsApp catalogs, and marketplace listings across multiple tabs leads to stock mismatches, missed shipments, and customer complaints.",
            "cure_text": "✦ THE BOTTLENECK: Scattered order records make it impossible to track accurate stock counts or shipping status."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 05/50",
            "page_num": 3,
            "title_lines": [
                ("One Unified", False),
                ("Control Center", True)
            ],
            "body_text": "An AI-powered dashboard pulls orders and inventory from Shopify, Instagram, WhatsApp, and courier accounts into a single dashboard. It auto-updates inventory levels across all stores instantly.",
            "cure_text": "✦ THE AI CURE: Sync operations in real time and eliminate stock-outs or double-sells across all channels."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 05/50",
            "page_num": 4,
            "title_lines": [
                ("Error-Free", False),
                ("Order Flows", True)
            ],
            "body_text": "The system auto-formats and pushes order details into Shiprocket or Delhivery, printing labels and triggering tracking emails without a single manual click.",
            "cure_text": "✦ THE ADVANTAGE: Process thousands of daily orders from one dashboard with zero human errors."
        },
        {
            "type": "stats",
            "top_label": "D2C AUTOMATION: DAY 05/50",
            "page_num": 5,
            "title_lines": [
                ("Operational", False),
                ("Results", True)
            ],
            "stats": [
                ("100%", "Real-time Multi-channel Inventory Sync"),
                ("Zero", "Manual Order Form Entry Mismatches"),
                ("4x Faster", "Order Manifest to Dispatch Time")
            ]
        },
        {
            "type": "cta",
            "top_label": "D2C AUTOMATION: DAY 05/50",
            "page_num": 6,
            "title_lines": [
                ("Streamline your", False),
                ("order dispatch.", True)
            ],
            "body_text": "Get a free 30-minute operational workflow audit. We will map your multi-channel stores and design a unified order control center.",
            "trigger_text": "Comment 'DAY5' below and our AI agent will DM you your direct scoping invite instantly."
        }
    ]

    # Day 6: day_06_whatsapp_fit_faq
    day6_slides = [
        {
            "type": "cover",
            "top_label": "D2C AUTOMATION: DAY 06/50",
            "page_num": 1,
            "title_lines": [
                ("Lose buyers over", False),
                ("sizing or fit?", False),
                ("INSTANT AI", True),
                ("FIT ADVISOR", True)
            ]
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 06/50",
            "page_num": 2,
            "title_lines": [
                ("Will this fit me?", False)
            ],
            "body_text": "Sizing is the #1 reason why cart-adders don't check out. If customers have to wait hours for a support team to reply with size charts, they abandon the cart and buy elsewhere.",
            "cure_text": "✦ THE BOTTLENECK: Sizing doubts cause 40% of checkout drop-offs and lead to expensive sizing return requests."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 06/50",
            "page_num": 3,
            "title_lines": [
                ("Interactive", False),
                ("Fit Recommendation", True)
            ],
            "body_text": "A trained AI WhatsApp agent asks for height, weight, and fit preferences. It cross-references your product sizing chart and recommends the perfect size (M, L, XL) instantly.",
            "cure_text": "✦ THE AI CURE: Answer sizing questions 24/7 in English, Hindi, and regional languages to capture buying intent."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 06/50",
            "page_num": 4,
            "title_lines": [
                ("First-Time-Right", False),
                ("Orders", True)
            ],
            "body_text": "By giving accurate, custom recommendations before they buy, you boost checkout conversion rates and dramatically reduce size-related exchanges.",
            "cure_text": "✦ THE ADVANTAGE: Improve buyer confidence, scale sales, and save massive return shipping costs."
        },
        {
            "type": "stats",
            "top_label": "D2C AUTOMATION: DAY 06/50",
            "page_num": 5,
            "title_lines": [
                ("Campaign", False),
                ("Metrics", True)
            ],
            "stats": [
                ("35%", "Increase in Checkout Conversions"),
                ("40%", "Decrease in Sizing Return Rates"),
                ("Instant", "Fitting Recommendations Under 3 Seconds")
            ]
        },
        {
            "type": "cta",
            "top_label": "D2C AUTOMATION: DAY 06/50",
            "page_num": 6,
            "title_lines": [
                ("Solve D2C sizing", False),
                ("drop-offs now.", True)
            ],
            "body_text": "Get a free 30-minute operational workflow audit. We will analyze your product catalog and outline custom sizing agent deployments.",
            "trigger_text": "Comment 'DAY6' below and our AI agent will DM you your direct scoping invite instantly."
        }
    ]

    # Day 7: day_07_order_status_bot
    day7_slides = [
        {
            "type": "cover",
            "top_label": "D2C AUTOMATION: DAY 07/50",
            "page_num": 1,
            "title_lines": [
                ("Where is my order?", False),
                ("spamming your DMs?", False),
                ("AUTOMATED", True),
                ("WISMO RESOLUTIONS", True)
            ]
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 07/50",
            "page_num": 2,
            "title_lines": [
                ("The WISMO Flood", False)
            ],
            "body_text": "\"Where is my order?\" (WISMO) queries flood support channels daily. Your team waste hours copying tracking numbers, opening courier portals, and copying status updates back to clients.",
            "cure_text": "✦ THE BOTTLENECK: Repetitive shipping questions block support queues, causing high-priority sales inquiries to be missed."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 07/50",
            "page_num": 3,
            "title_lines": [
                ("Live Courier", False),
                ("API Sync", True)
            ],
            "body_text": "An automated chatbot connects directly to Delhivery, Shiprocket, and Bluedart. When customers input their order number or phone, it pulls live transit details and updates them in seconds.",
            "cure_text": "✦ THE AI CURE: Instantly resolve shipping status queries, providing real-time tracking links and transit details."
        },
        {
            "type": "body",
            "top_label": "D2C AUTOMATION: DAY 07/50",
            "page_num": 4,
            "title_lines": [
                ("Proactive", False),
                ("Shipping Alerts", True)
            ],
            "body_text": "The system triggers proactive WhatsApp alerts for key milestones (shipped, out for delivery, delayed), keeping buyers informed before they ever need to ask support.",
            "cure_text": "✦ THE ADVANTAGE: Drastically reduce support volume, improve shipping transparently, and build post-purchase loyalty."
        },
        {
            "type": "stats",
            "top_label": "D2C AUTOMATION: DAY 07/50",
            "page_num": 5,
            "title_lines": [
                ("Operational", False),
                ("Impact", True)
            ],
            "stats": [
                ("85%", "Reduction in Order Status Support DMs"),
                ("100%", "Automated Live Courier API Lookup Sync"),
                ("<2 Sec", "Average Status Query Resolution Time")
            ]
        },
        {
            "type": "cta",
            "top_label": "D2C AUTOMATION: DAY 07/50",
            "page_num": 6,
            "title_lines": [
                ("Stop manually", False),
                ("tracking shipments.", True)
            ],
            "body_text": "Get a free 30-minute operational workflow audit. We will integrate your courier APIs and set up automated tracking bots.",
            "trigger_text": "Comment 'DAY7' below and our AI agent will DM you your direct scoping invite instantly."
        }
    ]

    # Render Days 1 to 7
    campaigns = [
        ("day_01_cart_recovery", day1_slides),
        ("day_02_cod_confirmation_call", day2_slides),
        ("day_03_dm_to_order", day3_slides),
        ("day_04_return_exchange_agent", day4_slides),
        ("day_05_centralized_order_dashboard", day5_slides),
        ("day_06_whatsapp_fit_faq", day6_slides),
        ("day_07_order_status_bot", day7_slides)
    ]
    
    for post_id, slides in campaigns:
        print(f"\n--- Generating {post_id} Slides ---")
        for idx, slide_data in enumerate(slides, start=1):
            out_path = f"d:\\InstagramPost\\post\\{post_id}\\slide_{idx:02d}.png"
            generate_slide(slide_data, out_path)
            
    # Copy Day 1 slides to post_temp for immediate publishing test staging
    print("\nCopying Day 1 slides to post_temp...")
    os.makedirs("d:\\InstagramPost\\post\\post_temp", exist_ok=True)
    for idx in range(1, 7):
        src = f"d:\\InstagramPost\\post\\day_01_cart_recovery\\slide_{idx:02d}.png"
        dst = f"d:\\InstagramPost\\post\\post_temp\\slide_{idx:02d}.png"
        shutil.copy(src, dst)
        print(f"Copied {src} -> {dst}")
        
    # Build HTML preview pages for dashboard
    captions = {
        "day_01_cart_recovery": "Day 1 of 50 Days AI Automation for D2C Brands 🚀\n\nPersonalized abandoned-cart recovery. Recover 45% of lost sales on complete autopilot.",
        "day_02_cod_confirmation_call": "Day 2 of 50 Days AI Automation for D2C Brands 🚀\n\nAI voice agent confirming COD orders before dispatch. Reduce RTO by 80% automatically.",
        "day_03_dm_to_order": "Day 3 of 50 Days AI Automation for D2C Brands 🚀\n\nInstagram/WhatsApp DM orders auto-converted to Shopify. 10x faster checkouts without manual copying.",
        "day_04_return_exchange_agent": "Day 4 of 50 Days AI Automation for D2C Brands 🚀\n\nSelf-serve return & exchange agent on WhatsApp. Reduce refund support inquiries by 90% automatically.",
        "day_05_centralized_order_dashboard": "Day 5 of 50 Days AI Automation for D2C Brands 🚀\n\nSync Shopify, WhatsApp, and courier channels into a single control center. Zero inventory mismatches.",
        "day_06_whatsapp_fit_faq": "Day 6 of 50 Days AI Automation for D2C Brands 🚀\n\nAutomated sizing and fit advisor on WhatsApp. Boost checkout conversions by 35% and reduce size returns.",
        "day_07_order_status_bot": "Day 7 of 50 Days AI Automation for D2C Brands 🚀\n\nSelf-serve transit lookup bot integrated with Delhivery & Shiprocket. Slash WISMO queries by 85%."
    }
    
    titles = {
        "day_01_cart_recovery": "Personalized abandoned-cart recovery",
        "day_02_cod_confirmation_call": "AI voice agent confirming COD orders",
        "day_03_dm_to_order": "DM-to-order conversion agent",
        "day_04_return_exchange_agent": "End-to-end WhatsApp return/exchange agent",
        "day_05_centralized_order_dashboard": "Centralized AI order dashboard",
        "day_06_whatsapp_fit_faq": "WhatsApp AI agent for sizing & fit FAQs",
        "day_07_order_status_bot": "Order-status lookup bot via courier APIs"
    }
    
    for post_id, slides in campaigns:
        caption = captions[post_id]
        title = titles[post_id]
        build_preview_page(post_id, caption, title, 6)

if __name__ == "__main__":
    main()
