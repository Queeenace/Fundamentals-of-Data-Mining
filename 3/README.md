# Лабораторная работа 3. Классификация деревом решений

Программа классифицирует годовой доход по данным Census Income. Поддерживаются
три критерия разбиения: `information_gain`, `gain_ratio`, `gini`. Результат
содержит полное дерево, четыре показателя качества и размеры выборок.

## Данные

Файлы [adult.data](https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data),
[adult.test](https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.test)
и [adult.names](https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.names)
получены из архива UCI и сохранены в `data/`. В исходной обучающей части 32 561
запись, в независимой тестовой 16 281. Доход `>50K` считается положительным
классом. Метки из `adult.test` нормализуются: конечная точка удаляется.

## Запуск

Из корня репозитория:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r 3/requirements.txt
.venv/bin/python 3/decision_tree.py --criterion gain_ratio --output 3/results/example.json
.venv/bin/python 3/decision_tree.py --criterion gini --train-share 0.8 --output 3/results/example_split.json
.venv/bin/python -m unittest discover -s 3/tests -v
.venv/bin/python 3/experiments.py
.venv/bin/python 3/build_report.py
```

Без `--train-share` дерево обучается на всех 32 561 строках `adult.data` и
проверяется на `adult.test`. С этим параметром исходная обучающая часть делится
на две части. Путь к произвольному набору такого же формата можно задать через
`--train` и `--test`; для разделения достаточно `--train` и `--train-share`.
Дополнительные параметры: `--max-depth` и `--min-leaf`.

Числовые признаки разделяются по 32 квантильным порогам, категориальные
кодируются индикаторами. Значение `?` сохраняется как отдельная категория.
Кодировщик обучается только на обучающей части. Максимальная глубина равна 6,
минимальный размер листа равен 120. Эти параметры и случайный seed=42
зафиксированы во всех опытах.

## Эксперименты и материалы

`experiments.py` строит три дерева на полном исходном обучении и оценивает их на
независимом тестовом файле. Затем при критерии Джини сравнивает доли обучения
60%, 70%, 80%, 90%, каждый раз деля `adult.data` со стратификацией.

Сводка находится в `results/summary.json`, полные деревья в
`results/tree_*.json`. Схемы первых трёх уровней находятся в
`figures/tree_*.png`, диаграмма качества в `figures/quality_by_share.png`.
Ветви глубже третьего уровня доступны в полном JSON.

Готовый [PDF-отчёт](output/pdf/decision_tree_report.pdf) содержит задание,
ссылку на репозиторий, рисунки и объяснение результатов. Для его пересборки
нужен установленный Times New Roman. Основной текст набран размером 14 пунктов.

Исходный набор: [UCI Adult](https://archive.ics.uci.edu/dataset/2/adult).
