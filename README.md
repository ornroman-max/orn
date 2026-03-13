# Экспорт текста страниц scotlandru.com

Скрипт `scrape_scotlandru.py` теперь использует **браузерные запросы через Playwright**:

1. Загружает карту сайта `https://scotlandru.com/sitemap_index.xml` через `context.request.get(...)`.
2. Собирает URL всех страниц из вложенных sitemap-файлов.
3. Открывает каждую страницу в браузере Chromium (`page.goto(...)`).
4. Забирает видимый текст страницы из `body` (`inner_text`).
5. Сохраняет результат в формате **1 файл = 1 страница** в папку `scotlandru_pages/`.

## Установка

```bash
pip install playwright
playwright install chromium
```

## Запуск

```bash
python3 scrape_scotlandru.py
```

После запуска появятся:

- `scotlandru_pages/urls.txt` — список всех URL;
- `scotlandru_pages/mapping.csv` — соответствие URL и имени файла;
- `scotlandru_pages/*.txt` — текст отдельных страниц.
