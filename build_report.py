"""Сборка отчёта: Times New Roman, 14 пунктов, чёрно-белое оформление."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-url', default='https://github.com/Queeenace/Fundamentals-of-Data-Mining')
    parser.add_argument('--font-dir')
    args = parser.parse_args()
    fonts(args.font_dir)
    # Используем прежние измерения, поскольку алгоритм не изменился.
    data = json.loads((ROOT / 'results/experiments.json').read_text())
    rows = data['summary']
    body = ParagraphStyle('Body', fontName='TNR', fontSize=14, leading=17,
                          textColor=BLACK, alignment=TA_JUSTIFY,
                          firstLineIndent=28, spaceAfter=6)
    plain = ParagraphStyle('Plain', parent=body, alignment=0, firstLineIndent=0)
    title = ParagraphStyle('Title', parent=plain, fontName='TNR-Bold',
                           alignment=TA_CENTER, spaceAfter=18)
    cell = ParagraphStyle('Cell', parent=plain, leading=16, spaceAfter=0)
    story = []

    def add(text, style=body):
        story.append(Paragraph(text, style))

    def table(values, widths):
        # Размер текста в таблицах также равен 14 пунктам.
        grid = [[Paragraph(str(value), cell) for value in row] for row in values]
        t = Table(grid, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), .6, BLACK),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

    add('Поиск частых наборов объектов алгоритмом Apriori', title)
    add('Цель работы состоит в разработке программы, которая находит часто встречающиеся сочетания товаров в покупательских корзинах. Программа должна принимать файл с данными, порог поддержки и способ сортировки результатов. Для каждого найденного набора необходимо вывести его состав и поддержку.')
    add('По условию задания нужно провести эксперименты на файле baskets.csv при порогах 1%, 3%, 5%, 10% и 15%. Затем следует сравнить время поиска и количество частых наборов разной длины, построить диаграммы и объяснить полученные результаты.')
    url = escape(args.repo_url)
    add(f'Материалы работы размещены в репозитории:<br/><link href="{url}" color="black">{url}</link>.', plain)
    add('Архив apriori_project.zip содержит исходный код, данные, тесты, полные результаты и программу для создания отчёта. PDF, файл baskets.csv и программа apriori.py также опубликованы отдельно. Команды запуска приведены в README.md.')
    add('В исходном файле 7 501 корзина и 115 разных товаров. Каждая строка описывает одну покупку. Заголовка нет, поэтому первая строка тоже участвует в расчётах. Для чтения используется кодировка Windows-1251, а названия товаров разделены запятыми.')
    add('При подготовке данных удаляются пробелы по краям названий и повторы товаров внутри одной корзины. Всего обнаружено 39 повторных вхождений. Такой подход позволяет учитывать факт покупки товара, а не число его единиц. Одинаковые корзины в разных строках сохраняются. Средняя длина корзины после обработки составляет 3,91 товара, максимальная достигает 20 товаров.')
    add('Поддержка набора равна доле корзин, в которых присутствуют все входящие в него товары. Например, поддержка 5% означает, что сочетание встретилось как минимум в пяти корзинах из ста. При расчётах используется точная граница: число корзин должно быть не меньше произведения порога на общее число корзин, округлённого вверх. Поэтому для порога 1% в этом файле требуется не менее 76 корзин.')

    story.append(PageBreak())
    add('В программе реализована модификация алгоритма Apriori. Сначала находятся частые одиночные товары, затем из них формируются пары, тройки и более длинные наборы. Если хотя бы одно подмножество кандидата оказалось нечастым, такой кандидат исключается. Это следует из свойства Apriori: каждое подмножество частого набора тоже является частым [1].')
    add('Для ускорения подсчёта каждому товару сопоставляется битовая маска. В ней отмечены номера корзин, содержащих этот товар. Пересечение масок показывает корзины с нужным сочетанием, а подсчёт установленных битов даёт его абсолютную поддержку. Поиск заканчивается, когда очередной уровень не содержит частых наборов.')
    add('Результат сохраняется в формате JSON. Для каждого набора указаны товары, длина, число подходящих корзин и относительная поддержка. Доступна сортировка по убыванию поддержки и лексикографическая сортировка названий. При равной поддержке также применяется лексикографический порядок.')
    add('Корректность проверена четырьмя тестами. В их числе 60 сравнений с полным перебором на небольших случайных данных, проверка граничного порога, чтения файла и сортировки. На baskets.csv результаты всех пяти порогов дополнительно сверены прямым подсчётом сочетаний длиной от одного до трёх товаров. Расхождений не обнаружено.')
    add(f"Эксперименты выполнены в Python {data['python']} на macOS 26.6.2, ARM64. Для каждого порога проведён один предварительный запуск, затем {data['repeats']} измерений. Порядок всех 75 измеряемых запусков перемешан с фиксированным значением seed=42. Время измерялось с помощью time.perf_counter_ns().")
    add('В измерение входят построение битовых масок и поиск наборов. Чтение файла, сортировка, сохранение результатов и построение диаграмм выполняются отдельно. Для сравнения используется медиана 15 запусков. Минимальное и максимальное время показывают наблюдаемый разброс, но не являются доверительным интервалом.')
    table([['Порог', 'Минимум корзин', 'Медиана, мс', 'Минимум, мс', 'Максимум, мс']] +
          [[f"{r['threshold_percent']}%", r['minimum_count'], number(r['median_ms']),
            number(r['min_ms']), number(r['max_ms'])] for r in rows], [57,103,107,107,107])

    story.append(PageBreak())
    story.extend([chart(rows, 'time'), Spacer(1, 12)])
    add('Рисунок 1. Время поиска при разных порогах поддержки. Точки показывают медианы, вертикальные отрезки обозначают минимальное и максимальное время.', plain)
    add(f"При повышении порога с 1% до 15% медианное время уменьшилось с {number(rows[0]['median_ms'], 2)} до {number(rows[-1]['median_ms'], 2)} мс. Поиск стал быстрее примерно в {number(rows[0]['median_ms'] / rows[-1]['median_ms'], 2)} раза. При более высоком пороге алгоритм раньше исключает редкие товары и их сочетания, поэтому проверяет меньше кандидатов.")
    add('При пороге 1% после предварительного отсечения проверяются 2 701 пара, 507 троек и 2 четвёрки. При пороге 15% остаётся только 10 пар, и ни одна из них не становится частой. Это объясняет сокращение объёма вычислений.')
    add('Время при порогах 10% и 15% почти одинаково. Построение исходных масок требуется в обоих случаях, даже если дальнейший поиск короткий. Небольшое увеличение медианы при 15% укладывается в разброс измерений. Поэтому по этому отличию нельзя сделать вывод, что повышение порога замедляет алгоритм.')
    add('Полученные значения характеризуют эту реализацию на данном компьютере. Фоновые процессы во время экспериментов не отключались. На другом устройстве время может отличаться, а для больших и плотных корзин число возможных сочетаний может существенно возрасти.')

    story.append(PageBreak())
    story.extend([chart(rows, 'count'), Spacer(1, 12)])
    add('Рисунок 2. Количество частых наборов разной длины при изменении порога поддержки.', plain)
    table([['Порог', 'Один товар', 'Два товара', 'Три товара', 'Всего']] +
          [[f"{r['threshold_percent']}%", *[r['by_length'].get(str(k), 0) for k in (1, 2, 3)],
            r['total']] for r in rows], [65,104,104,104,104])
    add('При пороге 1% найден 261 набор. Большую часть составляют пары, которых насчитывается 170. Кроме того, найдены 74 одиночных товара и 17 троек. При повышении порога до 3% тройки исчезают. При 5% остаются только три пары, а при 10% и 15% встречаются лишь одиночные товары.')
    add('Наборы из четырёх и более товаров не найдены ни при одном исследованном пороге. Чем больше товаров должно присутствовать одновременно, тем меньше корзин обычно подходит под это условие. Поэтому длинные сочетания быстрее перестают удовлетворять требованию к поддержке.')
    add('При повышении порога число частых наборов каждой длины не может увеличиться. Новый порог только исключает часть прежних результатов. В отличие от количества наборов, измеренное время может немного колебаться из-за текущей нагрузки компьютера.')

    story.append(PageBreak())
    add('Чтобы пояснить смысл результатов, рассмотрим несколько наиболее частых сочетаний. В таблице указаны число корзин и относительная поддержка каждого набора.')
    examples = json.loads((ROOT / 'results/itemsets_01_support.json').read_text())
    selected = examples[:1] + [r for r in examples if r['length'] == 2][:3] + [r for r in examples if r['length'] == 3][:1]
    table([['Набор товаров', 'Корзин', 'Поддержка']] +
          [[', '.join(r['items']), r['count'], number(r['support'] * 100) + '%']
           for r in selected], [305,70,106])
    add('Минеральная вода встречается в 1 788 корзинах, что составляет 23,837% покупок. Самая частая пара состоит из макарон и минеральной воды. Она встречается в 459 корзинах и имеет поддержку 6,119%. Поэтому эта пара остаётся в результатах при пороге 5%, но исчезает при 10%.')
    add('Самая частая тройка включает говяжий фарш, макароны и минеральную воду. Она встречается в 129 корзинах с поддержкой 1,720%. Такое сочетание проходит порог 1%, но уже не проходит порог 3%.')
    add('Для подробного изучения совместных покупок на этом файле подходит порог 1%. Порог 5% позволяет выделить самые распространённые пары. При порогах 10% и 15% результат описывает только популярность отдельных товаров. Выбор порога зависит от того, насколько подробные сочетания нужны для анализа.')
    add('Поддержка показывает распространённость сочетания, но сама по себе не доказывает зависимость между товарами. Для такой оценки потребовались бы дополнительные показатели, например confidence и lift. В данной работе они не рассчитывались.')
    add('В результате создана программа с необходимыми параметрами и двумя способами сортировки. Проведённые эксперименты показали, что повышение порога с 1% до 15% сокращает число частых наборов с 261 до 5 и уменьшает время поиска. Исходный файл, код и сохранённые измерения позволяют повторить расчёты.')
    add('[1] Agrawal R., Srikant R. Fast Algorithms for Mining Association Rules in Large Databases. VLDB, 1994, страницы с 487 по 499. <link href="https://rsrikant.com/papers/vldb94.pdf" color="black">Текст статьи</link>.', plain)
    add('Источник данных: файл baskets.csv, предоставленный для выполнения задания. Все таблицы и рисунки получены в ходе описанных экспериментов.', plain)

    def page_number(canvas, doc):
        # Внизу страницы остаётся только номер без дополнительного заголовка.
        canvas.setFont('TNR', 14)
        canvas.setFillColor(BLACK)
        canvas.drawCentredString(A4[0] / 2, 26, str(doc.page))

    (ROOT / 'output/pdf').mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(ROOT / 'output/pdf/apriori_report.pdf'), pagesize=A4,
                      leftMargin=57, rightMargin=57, topMargin=45, bottomMargin=48,
                      title='Поиск частых наборов объектов алгоритмом Apriori',
                      author='Vladislav').build(story, onFirstPage=page_number, onLaterPages=page_number)
    # Отдельные рисунки совпадают с диаграммами в отчёте.
    for mode, name in [('time', 'runtime'), ('count', 'itemset_lengths')]:
        drawing = chart(rows, mode)
        renderSVG.drawToFile(drawing, str(ROOT / f'figures/{name}.svg'))
        renderPDF.drawToFile(drawing, str(ROOT / f'figures/{name}.pdf'))


if __name__ == '__main__':
    main()
