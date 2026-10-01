"""Собирает PDF-отчёт о случайном лесе и сравнении с деревом."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent
URL = "https://github.com/Queeenace/Fundamentals-of-Data-Mining/tree/main/4"
FONT = Path("/System/Library/Fonts/Supplemental")


def main():
    pdfmetrics.registerFont(TTFont("TNR", str(FONT / "Times New Roman.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-Bold", str(FONT / "Times New Roman Bold.ttf")))
    data = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
    body = ParagraphStyle("body", fontName="TNR", fontSize=14, leading=18,
                          textColor=colors.black, alignment=TA_JUSTIFY,
                          firstLineIndent=25, spaceAfter=8)
    plain = ParagraphStyle("plain", parent=body, firstLineIndent=0, alignment=0)
    title = ParagraphStyle("title", parent=plain, fontName="TNR-Bold",
                           alignment=TA_CENTER, spaceAfter=15)
    heading = ParagraphStyle("heading", parent=plain, fontName="TNR-Bold",
                             spaceBefore=8, spaceAfter=8)
    cell = ParagraphStyle("cell", parent=plain, leading=16, spaceAfter=0)
    story = []

    def add(value, style=body):
        story.append(Paragraph(value, style))

    def percent(value):
        return f"{value * 100:.2f}".replace(".", ",")

    def table(values, widths):
        item = Table([[Paragraph(str(value), cell) for value in row] for row in values],
                     colWidths=widths, repeatRows=1)
        item.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .6, colors.black),
                                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                  ("TOPPADDING", (0, 0), (-1, -1), 5),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        story.extend([item, Spacer(1, 10)])

    add("Лабораторная работа 4. Ансамблевая классификация", title)
    add("1. Формулировка задания", heading)
    add("Требуется классифицировать данные Census Income ансамблем, меняя число участников от 50 до 100 с шагом 10. Программа принимает набор данных, технику, число участников и её параметры. На диаграмме нужно сравнить качество ансамбля с одиночным деревом из третьей работы.")
    add("2. Репозиторий и материалы", heading)
    add(f'Программа, результаты, диаграмма и PDF-отчёт размещены в каталоге <link href="{URL}" color="black">{escape(URL)}</link>.', plain)
    add('Использован файл <link href="https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data" color="black">adult.data из UCI</link>. Он и код подготовки данных находятся в каталоге третьей работы. Команды повторения приведены в README.md.')
    add("3. Метод и условия сравнения", heading)
    add("Выбран случайный лес. Каждое дерево обучается на случайной выборке с возвращением. При разбиении рассматривается случайное подмножество признаков размера sqrt от их общего числа. Настраиваются число деревьев, глубина, минимальный размер листа и способ выбора признаков.")
    add("Для всех шести опытов разбиение одинаково: 80% данных для обучения и 20% для проверки. Фиксируются seed=42, глубина 12, минимум 10 записей в листе и критерий Джини. Положительный класс - доход выше 50 000 долларов.")
    add("Одиночное дерево взято из опыта 80% / 20% третьей работы. Тестовые записи совпадают. Его глубина равна 6, минимум в листе - 120 записей; поэтому сравниваются выбранные настройки моделей.")
    add("4. Результаты", heading)
    rows = [["Модель", "Аккуратность, %", "Точность, %", "Полнота, %", "F-мера, %"]]
    rows.append(["Одно дерево"] + [percent(data["tree_baseline"][key]) for key in ("accuracy", "precision", "recall", "f1")])
    for item in data["forests"]:
        rows.append([f"Лес, {item['n_estimators']} деревьев"] +
                    [percent(item["quality"][key]) for key in ("accuracy", "precision", "recall", "f1")])
    table(rows, [175, 140, 120, 120, 100])

    story.append(PageBreak())
    add("5. Диаграмма и объяснение результатов", heading)
    story.append(Image(str(ROOT / "figures/forest_quality.png"), width=460, height=322))
    add("Рисунок 1. Четыре показателя качества случайного леса при разном числе деревьев. Пунктир показывает одиночное дерево на той же тестовой части.", plain)
    add("Показатели леса почти не меняются от 50 до 100 деревьев. При 100 деревьях аккуратность равна 85,81%, F-мера - 65,34%, тогда как у одиночного дерева они равны 85,05% и 62,01%. Полнота выросла с 50,70% до 55,55%, а точность немного снизилась с 79,82% до 79,33%.")
    add("Вывод: лес лучше выявляет высокий доход при выбранных настройках, но около 44% положительного класса остаётся пропущенным. Оценка получена на одном фиксированном разбиении.")

    def page(canvas, document):
        canvas.setFont("TNR", 14)
        canvas.drawCentredString(landscape(A4)[0] / 2, 25, str(document.page))

    output = ROOT / "output/pdf/random_forest_report.pdf"
    SimpleDocTemplate(str(output), pagesize=landscape(A4), leftMargin=45,
                      rightMargin=45, topMargin=38, bottomMargin=45,
                      title="Лабораторная работа 4. Ансамблевая классификация").build(
        story, onFirstPage=page, onLaterPages=page)


if __name__ == "__main__":
    main()
