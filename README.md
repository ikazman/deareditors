# DearEditors

Небольшое корпоративное медиа с характером.

Каждая хорошая редакция знает две вещи:

> До дорогой редакции дошел слух…

и

> Будем наблюдать.

## Первый релиз

DearEditors пока намеренно маленький: публичная лента, отдельная страница публикации и редактура через Django Admin. Публикации имеют статусы `draft` / `published`; наружу попадают только опубликованные материалы.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate  # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

После запуска:

- `/` — редакционная лента;
- `/admin/` — Django Admin (для входа сначала `python manage.py createsuperuser`).

## Проверка

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Принципы

- сначала законченный вертикальный срез, потом новые фичи;
- обычный Django без SPA и лишней инфраструктуры;
- выразительная типографика и редакционный характер;
- в редакционных и интерфейсных текстах используем только `е`;
- не превращать маленькое корпоративное медиа в инфраструктуру Reuters раньше времени.
