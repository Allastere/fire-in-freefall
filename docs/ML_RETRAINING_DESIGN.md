# Combustion Prediction Engine: расширение датасета и переобучение

Статус: проект целевой архитектуры. Основание: [аудит данных](ML_DATA_AUDIT.md).
Исследовательский этап для одной CO₂-задачи теперь реализован и обучен:
см. [фактические результаты и ограничения реализации](ML_TRAINING_RESULTS.md).
Ниже описана целевая архитектура; не все будущие targets и UI-инструменты уже реализованы.

## 1. Граница ML-модуля

```text
SQLite + исходные файлы + reviewed protocol metadata
    → согласованный read-only snapshot
    → проверка совместимости и качества по каждой задаче
    → canonical dataset + fingerprint + exclusion report
    → постоянное разделение независимых групп
    → train-only preprocessing + grouped model selection
    → calibration + независимая оценка + проверка области применимости
    → неизменяемый кандидат
    → quality/scientific promotion gates
    → атомарное обновление approved.json
    → Streamlit: загрузка одобренной версии, inference без обучения
```

Число исследований, материалов, прогонов и замеров не зашивается в код. SQL извлекает
все доступные записи. Количество объектов — результат запроса, а не условие работоспособности.
Наличие новых данных запускает аудит при очередном training command; обучение не выполняется
в Streamlit rerun или автоматически при пользовательской загрузке файла.

## 2. Контракты научной совместимости

`tasks.json` определяет не список текущих исследований, а версии задач:

- physical phenomenon: solid flame spread / droplet combustion / smoke formation и т. п.;
- target: каноническое имя, единицы, момент измерения, допустимые типы значений;
- feature definitions: только известные на момент прогноза признаки, единицы и происхождение;
- material formulation / цвет / покрытие, fuel phase, geometry, relevant dimensions;
- flow arrangement, ignition protocol, exposure duration, instrument/calibration protocol,
  hardware scale и другие обязательные именно для этой цели условия;
- группировка зависимых наблюдений, правила дубликатов, censoring и quality exclusions;
- разрешённый scientific-review status и версия критериев допуска.

Разные units конвертируются только при совпадении физической размерности **и смысла**.
Одинаковое название параметра или DOI не доказывает сопоставимость. Масштаб Saffire,
тонкая плёнка BASS и капля FLEX не объединяются автоматически в одну задачу.

Совместимые вновь импортированные строки включаются при полном переобучении без изменения
кода/UI. Новый неизвестный протокол попадает в карантин с причиной. После научного review
его metadata может соответствовать существующей задаче либо породить отдельную task version.
Проверенные mappings не требуют ручного перечисления каждого нового экспериментального ID.

ML review metadata хранится рядом с ML-кодом/артефактами; она может ссылаться на исходный
record ID и content fingerprint. Изменение исходной строки делает старое одобрение
невалидным. Общая БД и оригинальные NASA-файлы не переписываются ради очистки ML-данных.

## 3. Единица наблюдения и отсутствие утечек

Один пример = один физический прогон для выбранного target и протокола, а не EAV-строка.
Повторные measurements не превращаются в независимые примеры; правило агрегации, если
оно допустимо научно, фиксируется в task contract. Конфликтующие результаты сохраняются
для аудита, а не усредняются незаметно.

Использовать стабильный identity `(investigation, run, target, measurement phase, source identity)`.
Автоинкремент SQLite не годится как единственная воспроизводимая идентичность.

Связи образец → повторный поджиг → исходная серия → общий calibration/session cohort
формируют leakage groups. Записи, связанные хотя бы одной подтверждённой зависимостью,
попадают в один связный компонент. Непроверенные cross-investigation дубликаты помещаются
в карантин. Investigation ID сам по себе не достаточная группа и не физический feature.

Роли групп: development train/CV, uncertainty calibration и независимый benchmark.
Сохранять их manifest с версиями, не пересоздавать случайный test split при каждом запуске.
Новые записи известной группы наследуют её роль; группа benchmark никогда не попадает
в training. Новая связь, объединяющая разные роли, блокирует релиз до разрешения конфликта.

Импутация, кодирование, масштабирование, отбор признаков и подбор гиперпараметров
выполняются внутри `sklearn.Pipeline` только на training folds. Не заполнять неизвестные
давление, материал или критическую геометрию «удобными» средними значениями. Структурные
размеры обрабатываются по геометрии; статистическая импутация допустима лишь для
некритических пропусков по заранее согласованному контракту.

`GroupKFold`/grouped nested CV применяется по достаточным независимым группам.
Число folds ограничивается реальным количеством пригодных групп, а не количеством
измерений. Для внешней переносимости отдельно нужен holdout независимой кампании или
исследования; текущий CSV не подтверждает такую переносимость.

## 4. Переиспользуемый запуск

Предлагаемые команды:

```powershell
python -m ml.train --audit-only
python -m ml.train --task solid_co_final --config ml/tasks.json
python -m ml.train --all-compatible --config ml/tasks.json
```

Первый запуск должен работать без ML-библиотек и сообщать причины исключения данных.
Training-запуск выполняет полный fit на объединении старых и новых **пригодных development
данных**, не включая benchmark/calibration. Старые версии моделей не перезаписываются.
Недостаток данных, незаданные научные пороги или отсутствие независимой оценки дают
машиночитаемый отказ и ненулевой exit status; approved pointer остаётся прежним.

Сначала audit → split verification → baselines → кандидаты → calibration → оценка →
сохранение candidate → promotion evaluation. Новые источники не могут обойти этап eligibility.
Повтор с тем же data/config/code fingerprint обнаруживается как воспроизводимый повтор;
не нужно создавать релиз только из-за новой даты запуска.

При малом объёме — полное переобучение, CPU, ограниченная сетка гиперпараметров,
фиксированные seeds и ограниченный параллелизм под 16 GB RAM. Incremental learning
по умолчанию выключен. Он требует отдельного решения о стационарности процесса,
неизменности preprocessing, поддержке `partial_fit` выбранной моделью и протокола оценки;
теплый запуск RF/MLP не считать автоматически корректным online learning.

## 5. Модели и честное сравнение

| Метод | Роль в первом исследовании |
| --- | --- |
| Dummy / среднее training target | Обязательный baseline |
| Линейная интерполяция | Только одинаковый материал/геометрия/протокол и локальное покрытие; вне оболочки отказ |
| Linear Regression / Ridge | Проверяемый простой baseline с масштабированием |
| Random Forest | Нелинейный кандидат; разброс деревьев не объявлять готовой неопределённостью |
| Gaussian Process Regression | Приоритетный кандидат для маленьких однородных серий; дисперсию калибровать/проверять |
| Небольшой MLP | Сравнительный кандидат только при достаточных данных; без предпочтения сложности |

Выбрать победителя до экспериментов нельзя. Предварительная рекомендация — GPR или Ridge
для узкой однородной серии; наиболее точный метод определяется одинаковой grouped CV.
Нейросеть на нынешних небольших strata не обоснована как основной метод.

В регрессии сохранять MAE/RMSE/R², ошибки по группам, материалам и режимам, baseline metrics,
coverage и ширину интервалов. R² не определён на единичной/константной цели — хранить
`null` и причину. В классификации после независимой проверки меток — precision/recall/F1,
confusion matrix, counts по классам и проверка редких опасных исходов.

Разбиения и budgets для сравниваемых моделей одинаковы. Сначала selection на development,
затем calibration на отдельной группе, затем фиксированная независимая оценка.

## 6. Dataset fingerprints и воспроизводимость

В согласованной SQLite read transaction извлечь научные таблицы. Отдельно проверить hashes
исходных файлов. Стабильно отсортировать canonical observations, нормализовать единицы,
типы, missing values и JSON. Запретить NaN/Infinity и определить стабильное представление чисел.

`dataset_sha256 = SHA256(canonical scientific observations + source hashes + review metadata)`.
В него не входят `llm_cache`, время запуска, абсолютные пути и незначимые технические timestamps.
Изменение добавленного/исправленного/удалённого научного значения меняет fingerprint.

Отдельно хранить hashes feature contract, task config, split manifest, benchmark snapshot,
preprocessing code и promotion policy. Конкретный training run включает эти hashes,
Python/library versions, platform, seed, git HEAD и hash фактического diff: один git commit
не описывает текущую рабочую копию с незакоммиченными изменениями.

Хранить неизменяемые canonical dataset snapshots или доступные по hash исходные файлы
вместе с review manifest. Один fingerprint без данных не позволяет воспроизвести обучение.
Проверять fingerprint после извлечения, чтобы не смешать SQL snapshot с изменившимся источником.

## 7. Хранение версий

```text
ml/
  dataset.py          # Dynamic SQLite extraction, provenance, canonicalization
  preprocessing.py    # Task-specific eligibility and train-only feature pipeline
  train.py            # CLI orchestration and full retraining
  evaluate.py         # Grouped CV, benchmark metrics, promotion decision
  uncertainty.py      # Calibration and supported-domain checks
  predict.py          # Stable inference contract used by Streamlit
  registry.py         # Immutable versions and atomic approved pointer
  tasks.json          # Versioned tasks and scientific compatibility policy
models/
  <phenomenon>/<target>/
    approved.json
    versions/<version_id>/
      pipeline.joblib
      metadata.json
      evaluation_results.json
      domain.json
      split_manifest.json
      promotion_decision.json
datasets/
  <dataset_sha256>/
    observations.jsonl
    provenance.json
    exclusions.json
```

Version ID связывает dataset, task/config и code fingerprints. Metadata содержит:
UTC training date, model class/hyperparameters, all fingerprints, feature order/units,
target definition/units, sample **и group** counts по каждой роли, investigation/material
coverage, ranges/constant features, metrics per cohort, uncertainty method/thresholds,
scientific-review decision, supported domain, known limitations, dependency versions,
artifact SHA-256 и predecessor version. Предыдущие кандидаты, отклонения и одобрения сохраняются.

Загружать joblib только из собственного доверенного registry, проверяя artifact hash и
совместимость окружения. Не загружать модель из пользовательского file upload.

## 8. Допуск новой версии

Quality policy фиксируется **до** финальной оценки и версионируется отдельно для target:

- достаточность независимых групп и полнота provenance;
- нулевая пересечённость leakage groups между ролями;
- target-specific предельные MAE/RMSE и допустимая ширина интервала в физических единицах;
- преимущество перед baseline и отсутствие недопустимой деградации относительно champion;
- требования к interval coverage и минимальной доле запросов, на которые модель отвечает;
- отсутствие провалов по заявленным материалам/режимам;
- отсутствие неподтверждённого расширения scientific domain;
- подтверждённый review протокола и smoke tests загрузки/inference.

Нельзя сейчас выдумать допустимую ошибку в ppm или мм/с: она зависит от датчика и задачи.
Пока policy thresholds или scientific review не заданы, статус только research candidate,
автоматическое одобрение запрещено. Число строк само по себе не является критерием качества.

Champion и challenger оцениваются на одном неизменяемом benchmark с одним fingerprint.
При новой области (например, новом материале) нужен самостоятельный независимый benchmark
для этой области; сравнение с отказом старой модели не доказывает качество новой.
Неподдерживаемые champion запросы не исключаются незаметно из отчёта.

Benchmark не используется для настройки гиперпараметров/порогов. Повторное принятие
решений на одном holdout постепенно создаёт selection bias: вести журнал оценок,
ограничивать циклы и вводить новую независимую benchmark version при расширении домена.
При обновлении benchmark обе модели повторно проверяются на одной версии; метрики
разных test snapshots напрямую не сравниваются.

Только прошедший все gates кандидат обновляет `approved.json` через временный файл и
атомарный replace, с проверкой ожидаемой предыдущей версии. Неудача training/promotion
не меняет pointer. Для MVP один training/promotion process одновременно; параллельный
publisher отклоняется блокировкой. Rollback меняет pointer на прежнюю одобренную версию.

## 9. Domain, uncertainty и отказы

Пересчитывать на каждом fit, но только по training/calibration и с последующей независимой
проверкой. Сохранять отдельные области по материалу/геометрии/протоколу, а не один общий
прямоугольник min/max на все исследования. Проверять совместные сочетания признаков,
локальную плотность и расстояние до сопоставимых наблюдений. Одних min/max недостаточно.

Константный training pressure/gravity не даёт права предсказывать при другом значении.
Неизвестный материал, состав/покрытие, partial-g без измерений, отсутствующие критические
условия, высокий локальный разброс, недостаточная calibration и слишком широкий интервал
дают отказ. Повторные измерения одного образца не увеличивают независимую локальную плотность.

GPR std — модельная неопределённость, не автоматически проверенная вероятность покрытия.
При достаточных независимых calibration groups можно исследовать group-aware conformal
intervals, проверив предпосылки обменности и фактическое покрытие. Если для выбранного
уровня покрытия недостаточно групп для конечного квантили — честный отказ, без фиктивного
«95% confidence». Финальный test set не используется для калибровки.

Результат inference — стабильный JSON-контракт:

```json
{
  "status": "INSUFFICIENT_DATA",
  "target": "solid_flame_spread",
  "value": null,
  "unit": "mm/s",
  "interval": null,
  "model_version": null,
  "dataset_sha256": null,
  "reasons": ["No approved model supports this experimental domain."],
  "sources": []
}
```

`OBSERVED` — реальное измерение при совпадающих условиях и протоколе, с исходной
точностью и censoring flags; это не предсказание и не доказательство безопасности.
`INTERPOLATED` — оценка между проверенными сопоставимыми точками внутри локального
покрытия, не просто между глобальными минимумом и максимумом O₂.
`PREDICTED` — результат одобренной модели внутри независимо проверенного домена.
`INSUFFICIENT_DATA` — число и интервал отсутствуют, причины перечислены явно.

## 10. Streamlit и Gemini

SI Insights обращается только к `ml.predict.assess(request)`. Discovery доступных targets,
materials и features идёт из approved metadata. `st.cache_resource` ключуется version ID /
artifact hash, а маленький approved pointer перечитывается до выбора cache key. Новое
одобрение не требует изменения UI; отсутствие модели не мешает остальному приложению.

На Cloud Run контейнер может использовать immutable bundled registry: новая версия
появляется после нового deployment с артефактами, без изменений архитектуры. Для живого
обновления между deployments нужен отдельно настроенный внешний registry, а не запись
в эфемерную файловую систему контейнера. Локально pointer можно обновлять на диске.

Gemini получает вычисленный result как read-only evidence с model/dataset version,
метриками, ограничениями и NASA references. Числовые значения и интервалы UI показывает
из ML-result, никогда из текста Gemini. Generated interpretations отдельно помечаются;
при отказе числовой прогноз не восстанавливается языковой моделью. Новая численная
интерпретация не меняет исходный prediction object.

## 11. Согласования backend перед расширением

В `database/repository.py` self-check требует ровно 5 исследований и 6 findings. После
расширения он будет падать при корректной БД. Следует согласовать проверку схемы,
ссылочной целостности и ожидаемых fixtures вместо текущего общего размера каталога.

`experiments.test_id` сейчас глобальный PRIMARY KEY, а `parse_and_store_csv` использует
`INSERT OR REPLACE`. Повтор Test # в новом исследовании может затронуть старую запись.
До новых импортов нужен согласованный namespace/stable experiment UID или миграция
составной идентичности `(psi_id, test_id)` и всех внешних ключей. ML-loader не может
восстановить данные, уже потерянные при конфликтующем импорте.

Нельзя автоматически применять PSI-25-специфические предположения о PMMA, N₂, давлении,
gravity и диапазонах датчиков к новым исследованиям. Нужен provenance-aware импорт
или reviewed sidecar metadata. Эти изменения принадлежат backend коллеги и не внесены
без отдельного согласования. Новая ML-реализация не должна обходить эти ограничения.

## 12. Поэтапная реализация после согласования

1. Read-only dataset audit, immutable snapshots, task/review contracts и fingerprint tests.
2. Проверки новых импортов и совместимости; отклонение неизвестных протоколов/конфликтов.
3. Stable group manifests и тесты отсутствия leakage на повторах образцов и expansion.
4. CLI `python -m ml.train`, full retraining, baselines и небольшие кандидаты; отказ при
   недостаточных данных без публикации непроверенной модели.
5. Evaluation, calibration, домены, registry и quality/scientific gates; version rollback.
6. Combustion Predictor в SI Insights, загрузка approved model, наблюдения/график/отказы,
   затем отдельная Gemini interpretation без изменения рассчитанных чисел.

Обязательные регрессии: добавление совместимого исследования меняет fingerprint и
development sample count; несовместимое не попадает в training; `llm_cache` не меняет
fingerprint; порядок SQL-строк не влияет на версию; образец не пересекает роли; плохой
challenger не меняет approved pointer; старые версии остаются доступны; UI получает
новую approved version без правки кода; отсутствие модели возвращает отказ без падения app.

Не устанавливать PyTorch/TensorFlow. Лёгкие ML-зависимости вынести в отдельный pinned
training requirements-файл; существующий стек приложения не обновлять без необходимости.

## Документация, проверенная через Context7

- [Scikit-learn: leakage и train-only preprocessing](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage)
- [Scikit-learn: grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data)
- [Scikit-learn: GaussianProcessRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.gaussian_process.GaussianProcessRegressor.html)
- [Scikit-learn: persistence и совместимость версий](https://scikit-learn.org/stable/model_persistence.html)
