#!/usr/bin/env python3
"""生成 MacCleaner 应用图标"""
from PIL import Image, ImageDraw, ImageFont
import math
import os

SIZE = 1024
PADDING = 80
CORNER_RADIUS = 220

def create_icon():
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 背景 - 圆角矩形，蓝绿渐变模拟
    for y in range(SIZE):
        ratio = y / SIZE
        r = int(30 + ratio * 20)
        g = int(180 + ratio * 40)
        b = int(220 + ratio * 20)
        for x in range(SIZE):
            # 圆角矩形裁剪
            in_rect = True
            # 左上角
            if x < CORNER_RADIUS and y < CORNER_RADIUS:
                dist = math.sqrt((x - CORNER_RADIUS) ** 2 + (y - CORNER_RADIUS) ** 2)
                if dist > CORNER_RADIUS:
                    in_rect = False
            # 右上角
            if x > SIZE - CORNER_RADIUS and y < CORNER_RADIUS:
                dist = math.sqrt((x - (SIZE - CORNER_RADIUS)) ** 2 + (y - CORNER_RADIUS) ** 2)
                if dist > CORNER_RADIUS:
                    in_rect = False
            # 左下角
            if x < CORNER_RADIUS and y > SIZE - CORNER_RADIUS:
                dist = math.sqrt((x - CORNER_RADIUS) ** 2 + (y - (SIZE - CORNER_RADIUS)) ** 2)
                if dist > CORNER_RADIUS:
                    in_rect = False
            # 右下角
            if x > SIZE - CORNER_RADIUS and y > SIZE - CORNER_RADIUS:
                dist = math.sqrt((x - (SIZE - CORNER_RADIUS)) ** 2 + (y - (SIZE - CORNER_RADIUS)) ** 2)
                if dist > CORNER_RADIUS:
                    in_rect = False

            if in_rect:
                img.putpixel((x, y), (r, g, b, 255))

    # 画一个大的圆形盾牌/扫描区域
    cx, cy = SIZE // 2, SIZE // 2 - 40
    radius = 320

    # 外圈光环
    for angle in range(360):
        rad = math.radians(angle)
        for r_offset in range(-4, 5):
            x = int(cx + (radius + 60 + r_offset) * math.cos(rad))
            y = int(cy + (radius + 60 + r_offset) * math.sin(rad))
            if 0 <= x < SIZE and 0 <= y < SIZE:
                alpha = 180 - abs(r_offset) * 20
                orig = img.getpixel((x, y))
                img.putpixel((x, y), (255, 255, 255, min(255, orig[3] + alpha)))

    # 内部圆 - 扫描区域
    for x in range(cx - radius, cx + radius + 1):
        for y in range(cy - radius, cy + radius + 1):
            if 0 <= x < SIZE and 0 <= y < SIZE:
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist <= radius:
                    orig = img.getpixel((x, y))
                    # 混合白色，半透明
                    blend = 0.15
                    nr = int(orig[0] * (1 - blend) + 255 * blend)
                    ng = int(orig[1] * (1 - blend) + 255 * blend)
                    nb = int(orig[2] * (1 - blend) + 255 * blend)
                    img.putpixel((x, y), (nr, ng, nb, orig[3]))

    # 扫描线 - 从左下到右上的弧线
    draw2 = ImageDraw.Draw(img)
    for offset in range(-3, 4):
        points = []
        for t in range(0, 180, 2):
            rad = math.radians(t - 45)
            x = int(cx + (radius - 40) * math.cos(rad)) + offset
            y = int(cy + (radius - 40) * math.sin(rad)) + offset
            points.append((x, y))
        if len(points) > 1:
            draw2.line(points, fill=(255, 255, 255, 220), width=8)

    # 中心 - 小扫帚/清理图标简化：画一个勾号 ✓
    check_cx, check_cy = cx - 60, cy + 20
    # 勾号第一笔（短斜线）
    for w in range(-12, 13):
        for t in range(100):
            x = int(check_cx + t * 0.8) + w
            y = int(check_cy + t * 1.2)
            if 0 <= x < SIZE and 0 <= y < SIZE:
                orig = img.getpixel((x, y))
                blend = 0.9
                nr = int(orig[0] * (1 - blend) + 255 * blend)
                ng = int(orig[1] * (1 - blend) + 255 * blend)
                nb = int(orig[2] * (1 - blend) + 255 * blend)
                img.putpixel((x, y), (nr, ng, nb, 255))

    # 勾号第二笔（长斜线）
    for w in range(-14, 15):
        for t in range(200):
            x = int(check_cx + 80 + t * 1.0) + w
            y = int(check_cy + 120 - t * 1.8)
            if 0 <= x < SIZE and 0 <= y < SIZE:
                orig = img.getpixel((x, y))
                blend = 0.9
                nr = int(orig[0] * (1 - blend) + 255 * blend)
                ng = int(orig[1] * (1 - blend) + 255 * blend)
                nb = int(orig[2] * (1 - blend) + 255 * blend)
                img.putpixel((x, y), (nr, ng, nb, 255))

    # 底部文字区域 - 添加一个小的 Mac 显示器轮廓
    mon_cx, mon_cy = cx, cy + radius + 100
    mon_w, mon_h = 160, 100
    # 显示器外框
    draw2.rounded_rectangle(
        [mon_cx - mon_w, mon_cy - mon_h, mon_cx + mon_w, mon_cy + mon_h],
        radius=15,
        fill=(255, 255, 255, 200),
        outline=(255, 255, 255, 240),
        width=4
    )
    # 显示器底座
    draw2.rectangle(
        [mon_cx - 40, mon_cy + mon_h, mon_cx + 40, mon_cy + mon_h + 30],
        fill=(255, 255, 255, 200)
    )
    draw2.rectangle(
        [mon_cx - 80, mon_cy + mon_h + 25, mon_cx + 80, mon_cy + mon_h + 40],
        fill=(255, 255, 255, 200)
    )
    # 屏幕内部 - 深色
    draw2.rounded_rectangle(
        [mon_cx - mon_w + 15, mon_cy - mon_h + 15, mon_cx + mon_w - 15, mon_cy + mon_h - 15],
        radius=8,
        fill=(20, 60, 80, 200)
    )

    # 在屏幕里画一个小勾号
    sc_cx, sc_cy = mon_cx - 10, mon_cy - 10
    for w in range(-4, 5):
        for t in range(30):
            x = int(sc_cx + t * 0.6) + w
            y = int(sc_cy + t * 0.8)
            if 0 <= x < SIZE and 0 <= y < SIZE:
                img.putpixel((x, y), (100, 255, 180, 255))
    for w in range(-5, 6):
        for t in range(50):
            x = int(sc_cx + 18 + t * 0.7) + w
            y = int(sc_cy + 24 - t * 1.0)
            if 0 <= x < SIZE and 0 <= y < SIZE:
                img.putpixel((x, y), (100, 255, 180, 255))

    return img


def create_icns(img, output_path):
    """生成 .icns 文件（macOS 图标格式）"""
    # 先保存 PNG，然后用 macOS 的 iconutil 生成 icns
    iconset_dir = output_path.replace('.icns', '.iconset')
    os.makedirs(iconset_dir, exist_ok=True)

    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(os.path.join(iconset_dir, f'icon_{s}x{s}.png'))
        if s <= 512:
            resized2x = img.resize((s * 2, s * 2), Image.Resampling.LANCZOS)
            resized2x.save(os.path.join(iconset_dir, f'icon_{s}x{s}@2x.png'))

    # 使用 iconutil 生成 icns
    import subprocess
    result = subprocess.run(
        ['iconutil', '-c', 'icns', iconset_dir, '-o', output_path],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✅ ICNS: {output_path}")
        import shutil
        shutil.rmtree(iconset_dir)
    else:
        print(f"  ⚠️ iconutil 失败，保留 PNG iconset: {iconset_dir}")


if __name__ == '__main__':
    print("生成 MacCleaner 图标...")
    icon = create_icon()

    png_path = 'resources/icon.png'
    icon.save(png_path)
    print(f"  ✅ PNG: {png_path}")

    icns_path = 'resources/icon.icns'
    create_icns(icon, icns_path)

    print("完成！")
