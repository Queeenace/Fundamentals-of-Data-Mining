"""Создание отчёта об ассоциативных правилах в формате PDF."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from plots import fonts, number, rule_chart, save_rule_charts

ROOT = Path(__file__).resolve().parent
BLACK = colors.black


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--repo-url',
        default='https://github.com/Queeenace/Fundamentals-of-Data-Mining/tree/main/2',
    )
    parser.add_argument('--font-dir')
    args = parser.parse_args()
    fonts(args.font_dir)
    data = json.loads((ROOT / 'results/rule_experiments.json').read_text())
    rows = data['summary']
    rules = json.loads((ROOT / 'results/rules_analysis_40_support.json').read_text())

    body = ParagraphStyle('Body', fontName='TNR', fontSize=14, leading=17,
                          alignment=TA_JUSTIFY, firstLineIndent=28,
                          textColor=BLACK, spaceAfter=6)
    plain = ParagraphStyle('Plain', parent=body, alignment=0, firstLineIndent=0)
    title = ParagraphStyle('Title', parent=plain, fontName='TNR-Bold',
                           alignment=TA_CENTER, spaceAfter=16)
    heading = ParagraphStyle('Heading', parent=plain, fontName='TNR-Bold',
                             spaceBefore=8, spaceAfter=8)
    cell = ParagraphStyle('Cell', parent=plain, leading=16, spaceAfter=0)
    story = []

    def add(text, style=body):
        story.append(Paragraph(text, style))

    def table(values, widths, repeat=1):
        grid = [[Paragraph(str(value), cell) for value in row] for row in values]
        item = Table(grid, colWidths=widths, repeatRows=repeat, hAlign='LEFT')
        item.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), .6, BLACK),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.extend([item, Spacer(1, 10)])

    add('Поиск ассоциативных правил алгоритмом Apriori', title)
    add('1. Формулировка задания', heading)
    add('Требуется дополнить программу поиска частых наборов генерацией ассоциативных правил. Каждое правило должно выводиться в виде «антецедент → консеквент» вместе с поддержкой и достоверностью. Пользователь задаёт пороги поддержки и достоверности, а также выбирает сортировку по убыванию поддержки или лексикографически.')
    add('На исходном наборе baskets.csv нужно зафиксировать поддержку, изменить порог достоверности, измерить время поиска и число правил. Результаты необходимо показать на двух диаграммах. Также требуется подготовить список правил, содержащих суммарно не более семи объектов, и объяснить их практический смысл.')

    add('2. Репозиторий и материалы', heading)
    url = escape(args.repo_url)
    add(f'Исходный код, набор данных, полные результаты, рисунки и отчёт размещены в репозитории:<br/><link href="{url}" color="black">{url}</link>.', plain)
    add('Основная программа находится в файле apriori.py. Эксперименты выполняет rule_experiments.py, а диаграммы строятся функцией save_rule_charts из plots.py. Полные списки правил сохранены в каталоге results в двух вариантах сортировки.')

    add('3. Метод поиска правил', heading)
    add('Сначала алгоритм Apriori находит частые наборы. Для каждого частого набора L длиной не менее двух программа перебирает все непустые собственные подмножества A. Подмножество A становится антецедентом, а оставшиеся товары образуют консеквент B. Так получается правило A → B.')
    add('Поддержка правила равна доле корзин, которые содержат все товары из A и B. Достоверность показывает, в какой доле корзин с антецедентом A также встречается консеквент B. Она вычисляется как отношение поддержки совместного набора A и B к поддержке A. Правило сохраняется, если его достоверность не меньше заданного порога.')
    add('В текстовом режиме программа печатает правило, поддержку и достоверность. Формат JSON дополнительно содержит обе части правила как списки, абсолютное число корзин и суммарную длину. Параметр max-rule-length позволяет ограничить число объектов. Сортировка support сначала учитывает поддержку, затем достоверность. Сортировка lex сравнивает антецедент и консеквент по названиям товаров.')

    story.append(PageBreak())
    add('4. Постановка экспериментов', heading)
    add(f"В файле {data['transactions']} корзина. Поддержка зафиксирована на уровне {data['support_percent']}%. При этом найдено {data['frequent_itemsets']} частый набор, а максимальная длина набора равна {data['maximum_itemset_length']}. Порог достоверности изменялся от 20% до 50% с шагом 5%.")
    add('Пример из задания с диапазоном от 70% до 95% для этих данных не подходит. Максимальная достоверность среди правил с поддержкой 1% составляет 50,67%, поэтому при каждом пороге от 70% получился бы нулевой результат. Диапазон от 20% до 50% показывает реальное изменение числа правил.')
    add(f"Для каждого порога выполнен один прогрев и {data['repeats']} измерений. Порядок 700 запусков перемешан с seed=42. В измеряемый участок входят генерация, фильтрация и сортировка правил. Поиск частых наборов выполняется один раз до измерений, потому что при фиксированной поддержке он не зависит от порога достоверности.")
    table([['Порог, %', 'Медиана, мс', 'Минимум, мс', 'Максимум, мс', 'Правил']] +
          [[f"{row['confidence_percent']}%", number(row['median_ms']),
            number(row['min_ms']), number(row['max_ms']), row['rules']]
           for row in rows], [78, 100, 100, 105, 75])

    story.append(PageBreak())
    story.extend([rule_chart(rows, 'time'), Spacer(1, 10)])
    add('Рисунок 1. Время генерации, фильтрации и сортировки правил при изменении порога достоверности.', plain)
    add(f"Медианное время уменьшается с {number(rows[0]['median_ms'], 3)} мс при пороге 20% до {number(rows[-1]['median_ms'], 3)} мс при пороге 50%. Разница небольшая, потому что программа в любом случае рассматривает одни и те же разбиения частых наборов. Более высокий порог сокращает число объектов, которые нужно добавить в результат и отсортировать.")
    add('Измеренные значения меньше одной миллисекунды и зависят от компьютера и фоновой нагрузки. Они показывают тенденцию для этой реализации, но не являются универсальной оценкой скорости Apriori.')

    story.append(PageBreak())
    story.extend([rule_chart(rows, 'count'), Spacer(1, 10)])
    add('Рисунок 2. Количество правил при изменении порога достоверности.', plain)
    add('Количество правил последовательно сокращается: 164, 99, 65, 34, 19, 6 и 2. Это ожидаемый результат. Любое правило, которое проходит высокий порог, проходит и все более низкие пороги. Поэтому множество правил при увеличении confidence может только уменьшаться.')
    add('Порог 20% даёт большой список, в котором сложнее выделить главное. Порог 50% оставляет только два правила. Для содержательного анализа выбран промежуточный порог 40%. Он даёт 19 правил, поэтому список остаётся обозримым и сохраняет несколько разных типов покупательского поведения.')

    story.append(PageBreak())
    add('5. Список правил и содержательный анализ', heading)
    add('Ниже приведены все правила при поддержке 1% и достоверности 40%. Антецедент и консеквент суммарно содержат не более семи объектов. Фактически максимальная длина равна трём, потому что при поддержке 1% частые наборы большей длины в baskets.csv отсутствуют.')
    table([['Правило', 'Поддержка', 'Достоверность']] +
          [[row['rule'], number(row['support'] * 100) + '%',
            number(row['confidence'] * 100) + '%'] for row in rules],
          [285, 80, 116])

    add('Большинство правил указывает на минеральную воду в консеквенте. Например, правило «суп → минеральная вода» имеет поддержку 2,306% и достоверность 45,646%. Это означает, что оба товара встречаются вместе примерно в 2,3% всех корзин, а среди корзин с супом минеральная вода присутствует примерно в 45,6% случаев.')
    add('Самые достоверные правила связаны с сочетаниями из двух товаров. Для «говяжий фарш, яйца → минеральная вода» достоверность равна 50,667%, а для «говяжий фарш, молоко → минеральная вода» она равна 50,303%. Такие правила могут использоваться для совместного размещения товаров или рекомендаций, однако их поддержка составляет около 1%, поэтому они описывают сравнительно небольшую часть покупок.')
    add('Правило «говяжий фарш → макароны» выделяется тем, что его консеквентом является не минеральная вода. Поддержка равна 4,026%, достоверность 40,977%. Это одно из наиболее распространённых правил в списке и оно отражает понятное сочетание продуктов для приготовления основного блюда.')
    add('Высокая доля правил с минеральной водой частично объясняется её общей популярностью: она встречается в 23,837% всех корзин. Поэтому confidence нельзя понимать как доказательство причинной связи. Для оценки силы связи полезно дополнительно вычислять lift и сравнивать достоверность с базовой частотой консеквента, хотя это не входило в задание.')
    add('6. Вывод', heading)
    add('Программа дополнена поиском ассоциативных правил, порогом достоверности, ограничением длины и двумя способами сортировки. Правильность поддержки и достоверности 19 анализируемых правил независимо проверена прямым просмотром корзин. Эксперимент показал, что повышение порога достоверности с 20% до 50% сокращает число правил со 164 до 2 и немного уменьшает время формирования результата.')
    add('[1] Agrawal R., Srikant R. Fast Algorithms for Mining Association Rules in Large Databases. VLDB, 1994, страницы с 487 по 499. <link href="https://rsrikant.com/papers/vldb94.pdf" color="black">Текст статьи</link>.', plain)

    def page_number(canvas, document):
        canvas.setFont('TNR', 14)
        canvas.setFillColor(BLACK)
        canvas.drawCentredString(A4[0] / 2, 26, str(document.page))

    output = ROOT / 'output/pdf/association_rules_report.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(output), pagesize=A4, leftMargin=57, rightMargin=57,
                      topMargin=45, bottomMargin=48,
                      title='Поиск ассоциативных правил алгоритмом Apriori',
                      author='Vladislav').build(
        story, onFirstPage=page_number, onLaterPages=page_number)
    save_rule_charts(rows, font_dir=args.font_dir)


if __name__ == '__main__':
    main()
