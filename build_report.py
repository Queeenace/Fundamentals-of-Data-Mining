"""Build vector charts and a Russian PDF report from saved experiment results."""
import argparse
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Line, String, Rect, Circle
from reportlab.graphics import renderPDF, renderSVG

ROOT = Path(__file__).resolve().parent
BLUE = colors.HexColor('#2266A8')
INK = colors.HexColor('#172D43')
TEAL = colors.HexColor('#20958F')
ORANGE = colors.HexColor('#E49739')


def fonts(directory=None):
    candidates = [Path(directory)] if directory else [
        ROOT / 'fonts', Path('/usr/share/fonts/truetype/dejavu'),
        Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype']
    for folder in candidates:
        if (folder / 'DejaVuSans.ttf').exists():
            pdfmetrics.registerFont(TTFont('DV', str(folder / 'DejaVuSans.ttf')))
            pdfmetrics.registerFont(TTFont('DV-Bold', str(folder / 'DejaVuSans-Bold.ttf')))
            pdfmetrics.registerFontFamily('DV', normal='DV', bold='DV-Bold', italic='DV', boldItalic='DV-Bold')
            return
    raise RuntimeError('Install DejaVu Sans or pass --font-dir.')


def chart(rows, mode):
    d = Drawing(490, 280)
    x0, y0, w, h = 45, 47, 425, 190
    maximum = 10 if mode == 'time' else 200
    def label(x, y, text, size=9, anchor='start', color=INK):
        d.add(String(x, y, text, fontName='DV', fontSize=size, textAnchor=anchor, fillColor=color))
    label(x0, 261, 'Время, мс' if mode == 'time' else 'Количество частых наборов', 11)
    for value in range(0, maximum + 1, 2 if mode == 'time' else 40):
        y = y0 + h * value / maximum
        d.add(Line(x0, y, x0 + w, y, strokeColor=colors.HexColor('#DFE6EE'), strokeWidth=.5))
        label(x0 - 7, y - 3, str(value), anchor='end')
    d.add(Line(x0, y0, x0, y0 + h, strokeColor=INK))
    d.add(Line(x0, y0, x0 + w, y0, strokeColor=INK))
    if mode == 'time':
        points = []
        for row in rows:
            x = x0 + (row['threshold_percent'] - 1) / 14 * w
            y = y0 + row['median_ms'] / maximum * h
            lo, hi = [y0 + row[key] / maximum * h for key in ['min_ms', 'max_ms']]
            d.add(Line(x, lo, x, hi, strokeColor=BLUE, strokeWidth=1.2))
            for yy in [lo, hi]:
                d.add(Line(x-4, yy, x+4, yy, strokeColor=BLUE))
            points.append((x, y))
            label(x, hi + 8, f"{row['median_ms']:.2f}", anchor='middle')
            label(x, y0 - 17, str(row['threshold_percent']), anchor='middle')
        for a, b in zip(points, points[1:]):
            d.add(Line(*a, *b, strokeColor=BLUE, strokeWidth=2))
        for x, y in points:
            d.add(Circle(x, y, 3, fillColor=BLUE, strokeColor=BLUE))
    else:
        for index, row in enumerate(rows):
            center = x0 + (index + .5) * w / len(rows)
            for length, color in [(1, BLUE), (2, TEAL), (3, ORANGE)]:
                x = center + (length - 2) * 20 - 8
                value = row['by_length'].get(str(length), 0)
                height = value / maximum * h
                d.add(Rect(x, y0, 16, height, fillColor=color, strokeColor=None))
                label(x + 8, y0 + height + 5, str(value), size=8, anchor='middle')
            label(center, y0 - 17, str(row['threshold_percent']), anchor='middle')
        for index, (name, color) in enumerate([('1 товар', BLUE), ('2 товара', TEAL), ('3 товара', ORANGE)]):
            x = 210 + index * 92
            d.add(Rect(x, 254, 9, 9, fillColor=color, strokeColor=None))
            label(x + 14, 255, name, size=8)
    label(265, 7, 'Порог поддержки, %', anchor='middle')
    return d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-url')
    parser.add_argument('--font-dir')
    args = parser.parse_args()
    fonts(args.font_dir)
    # Берём сохранённые измерения, не повторяя эксперимент при сборке PDF.
    data = json.loads((ROOT / 'results/experiments.json').read_text())
    rows = data['summary']
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyRU', fontName='DV', fontSize=10, leading=15, spaceAfter=9, textColor=INK))
    styles.add(ParagraphStyle(name='TitleRU', fontName='DV-Bold', fontSize=25, leading=31, spaceAfter=20, textColor=INK))
    styles.add(ParagraphStyle(name='HeadRU', fontName='DV-Bold', fontSize=15, leading=20, spaceAfter=13, textColor=BLUE))
    styles.add(ParagraphStyle(name='SmallRU', fontName='DV', fontSize=8, leading=12, spaceAfter=8, textColor=INK))
    story = []
    def p(text, style='BodyRU'):
        return Paragraph(text, styles[style])
    def add(text, style='BodyRU'):
        story.append(p(text, style))
    def table(values, widths):
        t = Table([[p(str(v), 'SmallRU') for v in row] for row in values], colWidths=widths, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E8F0F7')),
                               ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                               ('TOPPADDING', (0,0), (-1,-1), 7), ('LINEBELOW', (0,0), (-1,-1), .4, colors.HexColor('#D5E0EA'))]))
        story.append(t)
    add('АНАЛИЗ ПОКУПАТЕЛЬСКИХ КОРЗИН', 'SmallRU')
    add('Поиск частых наборов<br/>алгоритмом Apriori', 'TitleRU')
    add('Экспериментальное исследование baskets.csv<br/>11 сентября 2026 г.')
    story.append(Spacer(1, 16))
    add('1. Формулировка задания', 'HeadRU')
    add('Разработать программу поиска всех непустых частых наборов объектов с помощью Apriori или его модификации. Входные параметры: файл транзакций, порог поддержки и порядок результатов: по убыванию поддержки либо лексикографически. Для каждого набора вывести состав и поддержку.')
    add('На фиксированном наборе baskets.csv провести эксперименты с порогами 1%, 3%, 5%, 10% и 15%. Визуализировать время поиска и количество частых наборов каждой длины. Подготовить PDF с исходной постановкой, ссылкой на материалы и интерпретацией результатов.')
    add('2. Репозиторий и материалы', 'HeadRU')
    if args.repo_url:
        url = escape(args.repo_url)
        add(f'Каталог репозитория: <link href="{url}" color="#2266A8">{url}</link>.')
    else:
        uri = ROOT.as_uri()
        add(f'<link href="{uri}" color="#2266A8">Открыть локальный каталог Git-репозитория AD</link>.')
        add('Онлайн-публикация ожидает входа в GitHub. Эта локальная ссылка работает только на исходном компьютере; перед сдачей отчёта её следует заменить адресом опубликованного репозитория.', 'SmallRU')
    add('В каталоге находятся apriori.py, experiments.py, build_report.py, tests/, исходный data/baskets.csv, полные списки наборов и измерения в results/, рисунки в figures/ и этот отчёт в output/pdf/. Команды запуска приведены в README.md.')
    story.append(PageBreak())
    add('3. Данные и алгоритм', 'HeadRU')
    add(f"В файле {data['transactions']:,} транзакция и {data['unique_items']} разных товаров. Каждая строка - отдельная корзина; первая строка также является транзакцией. Разделитель - запятая, кодировка исходного файла - Windows-1251. Пустых корзин нет. Средняя длина после удаления повторов составляет {data['mean_length']:.2f} товара, максимальная - {data['max_length']}.")
    add('Пробелы по краям названий удаляются, пустые поля игнорируются. 39 лишних повторных вхождений товаров внутри корзин удалены: поддержка отражает присутствие товара, а не число купленных единиц. Одинаковые корзины в разных строках сохраняются. Названия товаров не объединяются по смыслу.')
    add('Для набора X абсолютная поддержка count(X) равна числу корзин, содержащих все товары X. Относительная поддержка support(X) = count(X) / N. Набор частый, если count(X) ≥ ceil(s × N), где s - заданный порог. Для точного округления используется Decimal; например, 1% от 7 501 требует не менее 76 корзин.')
    add('Используется свойство Apriori: все подмножества частого набора тоже частые [1]. Сначала отбираются одиночные товары. Затем частые наборы длины k−1 с общим префиксом объединяются в кандидаты длины k; кандидаты с нечастым подмножеством длины k−1 отбрасываются. После подсчёта поддержки остаются частые кандидаты. Поиск прекращается при пустом очередном уровне.')
    add('Модификация подсчёта: каждому товару сопоставляется целое число с битом для каждой содержащей его транзакции. Маска кандидата получается пересечением масок двух родительских наборов (побитовое AND), а поддержка - методом int.bit_count(). Сохраняется поуровневая генерация Apriori; готовые библиотеки поиска частых наборов не используются.')
    add('Число кандидатов в худшем случае экспоненциально по числу товаров. Битовые пересечения обрабатывают маски из N бит; память зависит от числа масок текущего и следующего уровней. Поэтому быстрый результат на этом файле не гарантирует такую же скорость на плотных данных.')
    add('Выход и проверка корректности', 'HeadRU')
    add('JSON содержит items, length, count и support для каждого набора. При сортировке support сначала идут большие count, при равенстве - лексикографический порядок. Режим lex сравнивает отсортированные кортежи названий по Unicode, без языковой локали.')
    add('Пройдены 4 теста, включая 60 сравнений со всеми подмножествами на случайных малых данных, точную границу порога, обработку CSV и сортировки. На baskets.csv результаты всех пяти порогов независимо сверены горизонтальным перебором комбинаций длины 1–3; Apriori также проверил кандидатов длины 4 и не нашёл частых наборов.')
    story.append(PageBreak())
    add('4. Постановка экспериментов', 'HeadRU')
    add(f"Среда измерений: Python {data['python']}, {data['platform']}. Для каждого порога выполнен один прогрев и {data['repeats']} измерений. Порядок 75 запусков перемешан с seed=42. Время измерено time.perf_counter_ns(); показаны медиана и диапазон минимум–максимум.")
    add('CSV читается один раз до измерений. Каждый запуск заново строит битовые маски и выполняет полный поиск. Чтение файла, сортировка, экспорт и построение графиков не входят в измеренное время. Это время ядра поиска, а не полное время команды. Фоновые процессы не изолировались; диапазон не является доверительным интервалом.')
    table([['Порог', 'Мин. count', 'Медиана, мс', 'Мин.–макс., мс', 'Наборов']] +
          [[f"{r['threshold_percent']}%", r['minimum_count'], f"{r['median_ms']:.3f}", f"{r['min_ms']:.3f}–{r['max_ms']:.3f}", r['total']] for r in rows], [58,82,100,148,102])
    story.append(Spacer(1, 20))
    story.append(chart(rows, 'time'))
    add('Рисунок 1. Зависимость времени поиска от порога поддержки. Точки - медианы 15 запусков; вертикальные отрезки - минимум и максимум.', 'SmallRU')
    add(f"При повышении порога с 1% до 15% медиана снизилась с {rows[0]['median_ms']:.2f} до {rows[-1]['median_ms']:.2f} мс (примерно в {rows[0]['median_ms']/rows[-1]['median_ms']:.2f} раза). Сокращается число кандидатов, но построение исходных масок выполняется при каждом пороге. При 10% и 15% время почти одинаково; небольшое обратное изменение медианы укладывается в наблюдаемый разброс.")
    story.append(PageBreak())
    add('5. Количество и длина частых наборов', 'HeadRU')
    story.append(chart(rows, 'count'))
    add('Рисунок 2. Количество частых наборов длины 1, 2 и 3 при каждом пороге. Подписи 0 обозначают отсутствие наборов соответствующей длины. Для длин 4 и более значения равны нулю при всех порогах.', 'SmallRU')
    table([['Порог', '1 товар', '2 товара', '3 товара', 'Всего']] +
          [[f"{r['threshold_percent']}%", *[r['by_length'].get(str(k), 0) for k in (1,2,3)], r['total']] for r in rows], [70,105,105,105,105])
    story.append(Spacer(1, 15))
    add('При 1% преобладают пары: 170 из 261 набора. Также найдены 17 троек. При 3% тройки исчезают, при 5% остаются лишь три пары. При 10% и 15% встречаются только одиночные товары. Чем больше товаров требуется одновременно, тем меньше или равно число подходящих корзин, поэтому длинные наборы быстрее перестают проходить порог.')
    add('Для одного и того же файла множество результатов при большем пороге вложено в множество результатов при меньшем. Количество результатов каждой длины поэтому не может увеличиваться. В отличие от числа наборов, измеренное время не обязано строго убывать из-за накладных расходов и шума измерения.')
    add('При 1% после отсечения проверяются 2 701 пара, 507 троек и 2 четвёрки. При 15% проверяется только 10 пар, ни одна не проходит порог. Это объясняет снижение вычислительной нагрузки. Наборы большей длины отсутствуют уже при минимальном исследованном пороге.')
    story.append(PageBreak())
    add('6. Интерпретация и выводы', 'HeadRU')
    examples = json.loads((ROOT / 'results/itemsets_01_support.json').read_text())
    selected = examples[:1] + [r for r in examples if r['length'] == 2][:3] + [r for r in examples if r['length'] == 3][:1]
    table([['Набор товаров', 'Корзин', 'Поддержка']] +
          [[', '.join(r['items']), r['count'], f"{100*r['support']:.3f}%"] for r in selected], [340,65,85])
    story.append(Spacer(1, 15))
    add('Минеральная вода встречается в 1 788 корзинах (23,837%). Самая частая пара - макароны и минеральная вода: 459 корзин (6,119%). Поэтому она сохраняется при 5%, но не при 10%. Самая частая тройка - говяжий фарш, макароны и минеральная вода: 129 корзин (1,720%); она проходит порог 1%, но не 3%.')
    add('Порог 1% даёт подробное описание совместных покупок ценой более длинного списка результатов и большего времени. Порог 5% выделяет наиболее распространённые пары, а 10–15% оставляет только массовые одиночные товары. Для изучения сочетаний товаров на этом файле пороги 1–5% информативнее; окончательный выбор зависит от цели анализа.')
    add('Поддержка характеризует распространённость сочетания, но сама по себе не доказывает зависимость товаров или причинное влияние. В работе не вычислялись правила ассоциации, confidence и lift. Нет сведений о периоде наблюдения и составе покупателей, поэтому результаты описывают только предоставленные 7 501 корзину.')
    add('Реализован параметризуемый поиск со всеми требуемыми вариантами сортировки. Эксперимент показал сокращение числа частых наборов с 261 до 5 при повышении порога с 1% до 15%. Воспроизводимость обеспечивают исходный файл, код, тесты, полные результаты и все 75 измерений времени.')
    add('Источники и контроль данных', 'HeadRU')
    add('[1] Agrawal R., Srikant R. Fast Algorithms for Mining Association Rules in Large Databases. VLDB, 1994, pp. 487–499. <link href="https://rsrikant.com/papers/vldb94.pdf" color="#2266A8">Текст статьи</link>.', 'SmallRU')
    add('Источник данных: baskets.csv, предоставленный пользователем; исходный файл сохранён без изменения байтов. SHA-256:<br/>' + data['sha256'], 'SmallRU')
    add('Все числовые результаты и рисунки построены по локальным экспериментам этой работы. Измерения времени зависят от машины и текущей нагрузки.', 'SmallRU')
    def page(canvas, doc):
        canvas.setFont('DV', 8)
        canvas.setFillColor(INK)
        canvas.drawString(52, 29, 'Apriori / baskets.csv')
        canvas.drawRightString(543, 29, str(doc.page))
    (ROOT / 'output/pdf').mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(ROOT / 'output/pdf/apriori_report.pdf'), rightMargin=52, leftMargin=52,
                      topMargin=45, bottomMargin=48, title='Поиск частых наборов алгоритмом Apriori', author='Vladislav').build(story, onFirstPage=page, onLaterPages=page)
    # Экспортируем те же диаграммы отдельно в векторных форматах.
    for mode, name in [('time', 'runtime'), ('count', 'itemset_lengths')]:
        drawing = chart(rows, mode)
        renderSVG.drawToFile(drawing, str(ROOT / f'figures/{name}.svg'))
        renderPDF.drawToFile(drawing, str(ROOT / f'figures/{name}.pdf'))


if __name__ == '__main__':
    main()
