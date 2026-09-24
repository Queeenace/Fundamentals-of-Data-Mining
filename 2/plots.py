"""Построение чёрно-белых диаграмм экспериментов Apriori."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line, String, Rect, Circle
from reportlab.graphics import renderPDF, renderSVG

ROOT = Path(__file__).resolve().parent
BLACK = colors.black


def fonts(directory=None):
    # Используем настоящий Times New Roman с поддержкой кириллицы.
    folders = [Path(directory)] if directory else [
        ROOT / 'fonts', Path('/System/Library/Fonts/Supplemental'),
        Path('C:/Windows/Fonts'),
        Path('/usr/share/fonts/truetype/msttcorefonts'),
    ]
    for folder in folders:
        for regular, bold in [('Times New Roman.ttf', 'Times New Roman Bold.ttf'),
                              ('times.ttf', 'timesbd.ttf'),
                              ('Times_New_Roman.ttf', 'Times_New_Roman_Bold.ttf')]:
            if (folder / regular).exists() and (folder / bold).exists():
                pdfmetrics.registerFont(TTFont('TNR', str(folder / regular)))
                pdfmetrics.registerFont(TTFont('TNR-Bold', str(folder / bold)))
                pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-Bold',
                                             italic='TNR', boldItalic='TNR-Bold')
                return
    raise RuntimeError('Укажите --font-dir с файлами Times New Roman.')


def number(value, digits=3):
    return f'{value:.{digits}f}'.replace('.', ',')


def chart(rows, mode):
    # Линии и штриховка различают серии без использования цвета.
    d = Drawing(481, 280)
    x0, y0, width, height = 38, 42, 419, 178
    maximum = 10 if mode == 'time' else 200

    def label(x, y, text, anchor='start'):
        d.add(String(x, y, text, fontName='TNR', fontSize=14,
                     textAnchor=anchor, fillColor=BLACK))

    def pattern(x, y, w, h, kind):
        d.add(Rect(x, y, w, h, fillColor=BLACK if kind == 1 else colors.white,
                   strokeColor=BLACK, strokeWidth=.7))
        if kind == 2:
            # Горизонтальная штриховка обозначает пары товаров.
            for offset in range(4, int(h), 5):
                d.add(Line(x, y + offset, x + w, y + offset,
                           strokeColor=BLACK, strokeWidth=.6))

    label(x0, 260, 'Время поиска, мс' if mode == 'time' else 'Количество наборов')
    for value in range(0, maximum + 1, 2 if mode == 'time' else 40):
        y = y0 + height * value / maximum
        d.add(Line(x0 - 3, y, x0, y, strokeColor=BLACK, strokeWidth=.7))
        label(x0 - 7, y - 4, str(value), 'end')
    d.add(Line(x0, y0, x0, y0 + height, strokeColor=BLACK))
    d.add(Line(x0, y0, x0 + width, y0, strokeColor=BLACK))
    if mode == 'time':
        points = []
        for row in rows:
            x = x0 + (row['threshold_percent'] - 1) / 14 * width
            y = y0 + row['median_ms'] / maximum * height
            low, high = [y0 + row[key] / maximum * height for key in ['min_ms', 'max_ms']]
            d.add(Line(x, low, x, high, strokeColor=BLACK))
            for end in [low, high]:
                d.add(Line(x - 4, end, x + 4, end, strokeColor=BLACK))
            points.append((x, y))
            label(x + 17 if row['threshold_percent'] == 1 else x,
                  high + 9, number(row['median_ms'], 2), 'middle')
            label(x, y0 - 19, str(row['threshold_percent']), 'middle')
        for first, second in zip(points, points[1:]):
            d.add(Line(*first, *second, strokeColor=BLACK, strokeWidth=1.3))
        for x, y in points:
            d.add(Circle(x, y, 2.8, fillColor=BLACK, strokeColor=BLACK))
    else:
        for i, row in enumerate(rows):
            center = x0 + (i + .5) * width / len(rows)
            for length in (1, 2, 3):
                x = center + (length - 2) * 23 - 8
                value = row['by_length'].get(str(length), 0)
                bar_height = value / maximum * height
                if value:
                    pattern(x, y0, 16, bar_height, length)
                label(x + 8, y0 + bar_height + 5, str(value), 'middle')
            label(center, y0 - 19, str(row['threshold_percent']), 'middle')
        for i, name in enumerate(['1 товар', '2 товара', '3 товара']):
            x = 105 + i * 120
            pattern(x, 235, 15, 12, i + 1)
            label(x + 22, 235, name)
    label(250, 1, 'Порог поддержки, %', 'middle')
    return d


def save_charts(rows, directory=ROOT / 'figures', font_dir=None):
    """Сохраняем графики времени и количества наборов в SVG и PDF."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fonts(font_dir)
    for mode, name in [("time", "runtime"), ("count", "itemset_lengths")]:
        drawing = chart(rows, mode)
        renderSVG.drawToFile(drawing, str(directory / f"{name}.svg"))
        renderPDF.drawToFile(drawing, str(directory / f"{name}.pdf"))


def rule_chart(rows, mode):
    """Строим график времени или количества правил по порогу confidence."""
    d = Drawing(481, 300)
    x0, y0, width, height = 55, 65, 390, 175
    values = ([row['median_ms'] for row in rows] if mode == 'time'
              else [row['rules'] for row in rows])
    maximum = max(values) * 1.25 if values and max(values) else 1

    def label(x, y, text, anchor='start'):
        d.add(String(x, y, text, fontName='TNR', fontSize=14,
                     textAnchor=anchor, fillColor=BLACK))

    label(x0, 278, 'Время поиска правил, мс' if mode == 'time'
          else 'Количество найденных правил')
    d.add(Line(x0, y0, x0, y0 + height, strokeColor=BLACK))
    d.add(Line(x0, y0, x0 + width, y0, strokeColor=BLACK))
    points = []
    for index, row in enumerate(rows):
        x = x0 + index * width / (len(rows) - 1)
        value = row['median_ms'] if mode == 'time' else row['rules']
        y = y0 + value / maximum * height
        points.append((x, y))
        label(x, y + 10, number(value, 3) if mode == 'time' else str(value), 'middle')
        label(x, y0 - 22, str(row['confidence_percent']), 'middle')
    for first, second in zip(points, points[1:]):
        d.add(Line(*first, *second, strokeColor=BLACK, strokeWidth=1.3))
    for x, y in points:
        d.add(Circle(x, y, 3, fillColor=BLACK, strokeColor=BLACK))
    label(250, 10, 'Порог достоверности, %', 'middle')
    return d


def save_rule_charts(rows, directory=ROOT / 'figures', font_dir=None):
    """Сохраняем две диаграммы экспериментов с ассоциативными правилами."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fonts(font_dir)
    for mode, name in [('time', 'rule_runtime'), ('count', 'rule_count')]:
        drawing = rule_chart(rows, mode)
        renderSVG.drawToFile(drawing, str(directory / f'{name}.svg'))
        renderPDF.drawToFile(drawing, str(directory / f'{name}.pdf'))
