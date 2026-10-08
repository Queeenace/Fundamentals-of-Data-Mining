# Лабораторная работа 6. Иерархическая кластеризация

Программа строит иерархию клиентов из [набора лабораторной работы 5](../5/data/customers.csv). Доступны четыре способа связи кластеров: `single`, `complete`, `average`, `ward`. Расстояние между клиентами евклидово; признаки стандартизируются точно так же, как в лабораторной работе 5.

```bash
python 6/hierarchical.py --data 5/data/customers.csv --method ward --k 5 --output 6/results/example.csv --dendrogram 6/figures/example.png
python 6/experiments.py
```

Дендрограммы для [single](figures/dendrogram_single.png), [complete](figures/dendrogram_complete.png), [average](figures/dendrogram_average.png) и [ward](figures/dendrogram_ward.png) показывают последние 35 слияний, иначе подписи 850 объектов были бы нечитаемыми. [Таблица результатов](results/experiments.csv) содержит среднее расстояние до центроида, коэффициент силуэта при k=5 и индекс Рэнда с поправкой при сравнении с двумя разделительными алгоритмами. Также доступны [расположение кластеров](figures/clusters_by_linkage.png), [сравнение ошибок](figures/comparison_with_partitioning.png) и [отчёт PDF](output/pdf/hierarchical_clustering_report.pdf).
