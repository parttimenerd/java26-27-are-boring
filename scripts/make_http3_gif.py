from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 430
FRAMES = 64
OUT = '/Users/i560383_1/code/experiments/java26-is-boring/img/http-protocol-comparison.gif'


def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return None


font_title = (
    get_font('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 34)
    or ImageFont.load_default()
)
font_row = (
    get_font('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 28)
    or ImageFont.load_default()
)
font_sub = (
    get_font('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
    or ImageFont.load_default()
)


def draw_car(draw, x, y, color):
    draw.rounded_rectangle((x, y, x + 30, y + 12), radius=3, fill=color)
    draw.polygon([(x + 6, y), (x + 12, y - 7), (x + 24, y - 7), (x + 27, y)], fill=color)
    draw.ellipse((x + 5, y + 10, x + 11, y + 16), fill='#0f172a')
    draw.ellipse((x + 19, y + 10, x + 25, y + 16), fill='#0f172a')


def draw_plane(draw, x, y, color):
    draw.polygon([(x, y + 6), (x + 28, y), (x + 20, y + 7), (x + 28, y + 14)], fill=color)
    draw.polygon([(x + 11, y + 6), (x + 6, y + 16), (x + 13, y + 9)], fill=color)


frames = []
for t in range(FRAMES):
    image = Image.new('RGB', (W, H), '#0f172a')
    draw = ImageDraw.Draw(image)

    draw.text((40, 22), 'HTTP/1.1 vs HTTP/2 vs HTTP/3', fill='#e2e8f0', font=font_title)

    draw.text((40, 92), 'HTTP/1.1', fill='#f59e0b', font=font_row)
    draw.text((210, 100), 'One lane road. One request at a time.', fill='#94a3b8', font=font_sub)
    draw.rounded_rectangle((40, 122, 1160, 186), radius=10, fill='#1e293b', outline='#334155', width=2)
    draw.line((52, 154, 1148, 154), fill='#475569', width=2)

    cycle = t % FRAMES
    if cycle < 20:
        x_single = 55 + cycle * 20
    elif cycle < 38:
        x_single = 55 + 20 * 20
    else:
        x_single = 55 + 20 * 20 + (cycle - 38) * 20
    draw_car(draw, min(x_single, 1110), 147, '#f8fafc')

    draw.text((40, 240), 'HTTP/2', fill='#60a5fa', font=font_row)
    draw.text((155, 248), 'Multi-lane highway. Multiplexed streams.', fill='#94a3b8', font=font_sub)
    draw.rounded_rectangle((40, 270, 1160, 354), radius=10, fill='#1e293b', outline='#334155', width=2)
    for lane_y in [288, 306, 324, 342]:
        draw.line((52, lane_y, 1148, lane_y), fill='#475569', width=2)

    offsets = [0, 18, 36, 54]
    colors = ['#93c5fd', '#bfdbfe', '#dbeafe', '#e0f2fe']
    for index, (offset, color) in enumerate(zip(offsets, colors)):
        x_multi = 52 + ((t * 22 + offset * 13) % 1120)
        y_multi = 279 + index * 18
        draw_car(draw, x_multi, y_multi, color)

    draw.text((40, 386), 'HTTP/3', fill='#34d399', font=font_row)
    draw.text((155, 394), 'No road. QUIC over UDP, independent streams.', fill='#94a3b8', font=font_sub)

    draw.rounded_rectangle((430, 372, 1160, 416), radius=10, fill='#082f49', outline='#0c4a6e', width=2)
    draw.line((440, 394, 1150, 394), fill='#155e75', width=2)

    for i in range(6):
        x_plane = 440 + ((t * 18 + i * 130) % 700)
        y_plane = 378 + (i % 3) * 11
        draw_plane(draw, x_plane, y_plane, '#6ee7b7')

    frames.append(image)

frames[0].save(
    OUT,
    save_all=True,
    append_images=frames[1:],
    duration=70,
    loop=0,
    optimize=False,
)

print(OUT)
