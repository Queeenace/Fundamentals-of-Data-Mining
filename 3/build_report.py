"""Собирает PDF-отчёт о классификации деревом решений."""

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
URL = "https://github.com/Queeenace/Fundamentals-of-Data-Mining/tree/main/3"
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

    def table(values, widths):
        item = Table([[Paragraph(str(value), cell) for value in row] for row in values],
                     colWidths=widths, repeatRows=1)
        item.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .6, colors.black),
                                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                  ("TOPPADDING", (0, 0), (-1, -1), 5),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        story.extend([item, Spacer(1, 10)])

    def percent(value):
        return f"{value * 100:.2f}".replace(".", ",")

    add("Лабораторная работа 3. Классификация деревом решений", title)
    add("1. Формулировка задания", heading)
    add("Требуется построить классификатор годового дохода на данных Census Income. Пользователь выбирает критерий разбиения: информационный выигрыш, отношение выигрыша или индекс Джини. Нужно обучить деревья на 100% исходной обучающей выборки, проверить их на отдельной тестовой выборке и показать структуру деревьев.")
    add("Затем программа должна принимать долю обучающей выборки и рассчитывать аккуратность, точность, полноту и F-меру. Для одного критерия необходимо сравнить доли обучения 60%, 70%, 80% и 90% и построить диаграмму качества.")
    add("2. Репозиторий и данные", heading)
    add(f'Исходный код, файлы UCI, рисунки, подробные результаты и отчёт находятся в каталоге <link href="{URL}" color="black">{escape(URL)}</link>.', plain)
    add('Использованы файлы adult.data (32 561 запись), adult.test (16 281 запись) и adult.names из <link href="https://archive.ics.uci.edu/ml/machine-learning-databases/adult/" color="black">архива UCI</link>. Метка «&gt;50K» считается положительным классом. Точка в конце метки в adult.test удаляется при чтении. Значение «?» остаётся отдельной категорией.')
    add("3. Метод и постановка опыта", heading)
    add("Числовые признаки сравниваются с порогами, категориальные кодируются отдельными двоичными признаками. Кодировщик обучается только на обучающей части. Для числового признака проверяются 32 квантильных порога. Дерево ограничено глубиной 6 и содержит не менее 120 наблюдений в каждом листе. Эти ограничения уменьшают переобучение и делают схему обозримой.")
    add("Информационный выигрыш оценивает снижение энтропии. Gain ratio делит выигрыш на энтропию самого разбиения и тем самым меняет оценку кандидатов. Критерий Джини оценивает уменьшение неоднородности классов. Все три критерия реализованы в одном алгоритме дерева.")
    add("Для первого опыта использованы все 32 561 строки исходного файла обучения; качество измерено на отдельном файле adult.test. Для второго опыта только adult.data делится на обучающую и тестовую части с сохранением доли классов и фиксированным seed=42. Критерий второго опыта - индекс Джини. Положительный класс во всех расчётах один и тот же: доход выше 50 000 долларов.")
    add("4. Качество при полном исходном обучении", heading)
    rows = [["Критерий", "Аккуратность, %", "Точность, %", "Полнота, %", "F-мера, %"]]
    titles = {"information_gain": "Information gain", "gain_ratio": "Gain ratio", "gini": "Gini index"}
    for item in data["full_training"]:
        q = item["quality"]
        rows.append([titles[item["criterion"]]] + [percent(q[key]) for key in ("accuracy", "precision", "recall", "f1")])
    table(rows, [150, 140, 125, 125, 115])
    add("На отдельном тестовом файле аккуратность всех трёх деревьев составляет около 84,4–84,5%. Различия лучше видны в структуре разбиений и балансе точности и полноты.")

    for index, criterion in enumerate(("information_gain", "gain_ratio", "gini"), start=1):
        story.append(PageBreak())
        add(f"Рисунок {index}. Верхние уровни дерева по критерию {titles[criterion]}.", heading)
        picture = Image(str(ROOT / "figures" / f"tree_{criterion}.png"), width=700, height=340)
        story.append(picture)
        story.append(Spacer(1, 9))
        add("На схеме показаны первые три уровня. Надпись «ветвь продолжается» означает, что в полном дереве есть следующие разбиения. Число n обозначает количество записей в узле, а &gt;50K - количество представителей положительного класса. Полная структура дерева с порогами сохранена в каталоге results в формате JSON.")
        if criterion == "gain_ratio":
            add("Gain ratio сначала отделяет записи с большим приростом капитала. В этой группе доля доходов выше 50 000 долларов особенно высока. При небольшом приросте капитала дерево далее учитывает семейное положение и образование. Это описание статистических связей, а не причин дохода.")
        else:
            add("У разных критериев могут отличаться первые выбранные признаки и следующие пороги. Поэтому близкие итоговые оценки качества не означают, что построенные деревья одинаковы.")

    story.append(PageBreak())
    add("5. Влияние доли обучающей выборки", heading)
    story.append(Image(str(ROOT / "figures/quality_by_share.png"), width=560, height=323))
    add("Рисунок 4. Показатели качества дерева при разных долях обучающей выборки.", plain)
    add("Аккуратность увеличилась с 84,50% при доле обучения 60% до 85,48% при 90%. F-мера выросла с 60,91% до 62,67%. Полнота остаётся около 50%, поэтому примерно половина людей с высоким доходом не определяется как положительный класс.")
    add("При увеличении доли обучения тестовая часть становится меньше. По четырём точкам нельзя утверждать, что рост продолжится. Для сравнения с ансамблем используется разбиение 80% / 20% и те же исходные строки.")

    def page(canvas, document):
        canvas.setFont("TNR", 14)
        canvas.drawCentredString(landscape(A4)[0] / 2, 25, str(document.page))

    output = ROOT / "output/pdf/decision_tree_report.pdf"
    SimpleDocTemplate(str(output), pagesize=landscape(A4), leftMargin=45,
                      rightMargin=45, topMargin=38, bottomMargin=45,
                      title="Лабораторная работа 3. Классификация деревом решений").build(
        story, onFirstPage=page, onLaterPages=page)


if __name__ == "__main__":
    main()
