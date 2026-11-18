# ГДЗ-парсер

<p align="center">
  Найди подходящую открытую страницу с решением и сохрани удобный локальный просмотр — HTML, изображение или текст.
</p>

<p align="center">
  <a href="https://pypi.org/project/gdz-parser/"><img src="https://img.shields.io/pypi/v/gdz-parser?style=flat-square&logo=pypi&logoColor=white&label=PyPI&color=8B5CF6" alt="PyPI version"></a>
  <a href="https://github.com/zmlsaggg/gdz-parser/releases/latest"><img src="https://img.shields.io/github/v/release/zmlsaggg/gdz-parser?style=flat-square&logo=github&label=release&color=7C3AED" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+">
  <a href="https://github.com/zmlsaggg/gdz-parser/releases/latest"><img src="https://img.shields.io/badge/Windows-EXE-0078D4?style=flat-square&logo=windows&logoColor=white" alt="Windows executable"></a>
</p>

## Установка через pip

Нужен Python 3.9 или новее. Пакет называется `gdz-parser`. После установки самого пакета скачай браузер Chromium, который использует Playwright.

### Windows (PowerShell)

```powershell
py -m pip install --upgrade gdz-parser
py -m playwright install chromium
gdz-parser "Математика 10 класс Максимов 215 страница"
```

### Linux и macOS

```sh
python3 -m pip install --upgrade gdz-parser
python3 -m playwright install chromium
gdz-parser "Математика 10 класс Максимов 215 страница"
```

Если Linux сообщает о недостающих системных библиотеках Chromium, установи их командой `python3 -m playwright install --with-deps chromium` (для установки системных пакетов могут понадобиться права администратора).

Если система запрещает установку в системный Python, сначала создай виртуальное окружение:

```powershell
# Windows
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```sh
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

Затем в активированном окружении выполни:

```sh
python -m pip install --upgrade gdz-parser
python -m playwright install chromium
```

Обновить пакет: `python -m pip install --upgrade gdz-parser`. Удалить: `python -m pip uninstall gdz-parser`.
После установки Chromium команду `gdz-parser` можно запускать из любого каталога. Флаг `--upload-kappa` необязателен и по умолчанию ничего не публикует.

## Запуск из исходников


Скачайте репозиторий и откройте терминал в его папке. Нужен Python 3.9+.

```sh
python -m pip install -r requirements.txt
python -m playwright install chromium
python gdz.py
```

Если команда `python` недоступна, используйте `python3` или `py` в Windows. На Linux при ошибке о недостающих системных библиотеках используйте `python -m playwright install --with-deps chromium`.

После запуска введите, например, `Математика 10 класс Максимов 215 страница`. Программа проверит до 20 результатов Google параллельно (до четырёх одновременно) и выберет наиболее подходящую открытую страницу по заголовку, тексту, номеру страницы и наличию крупных изображений. Блокировка известных рекламных доменов работает на уровне запросов Chromium; она не убирает всю рекламу.

```sh
python gdz.py "Математика 10 класс Максимов 215 страница" --limit 40 --mode image
python gdz.py --mode text
python gdz.py --url "https://example.org/solution" --no-open
```

- `html` (по умолчанию): локальная HTML-карточка с текстом, снимком видимой области и ссылкой на оригинал. Это не полная копия сайта; храните `index.html` и `preview.png` рядом.
- `image`: локальный PNG. `text`: печать извлечённого текста в терминал.
- Файлы сохраняются в `results/` и открываются в браузере по умолчанию. `--no-open` отключает открытие.
- `--url` можно повторять, чтобы проверить несколько ссылок без Google. При CAPTCHA, запросе согласия или пустой выдаче найдите ссылки в обычном браузере и передайте их этим параметром.

Лимит — верхняя граница, а не обещание, что Google выдаст столько ссылок. Проверка эвристическая: совпадение номера и наличие картинки не гарантируют нужное решение. Снимок не охватывает всю страницу; изображения, которые ещё не загрузились, могут не попасть в него. Программа не обходит платный доступ и CAPTCHA.

### Публикация скриншота на kappa.lol

```sh
python gdz.py --mode image --upload-kappa
```

По умолчанию ничего не публикуется. Флаг отправляет только PNG и выводит ссылку. Используйте его только если вам есть 18 лет, вы согласны с [условиями сервиса](https://kappa.lol/terms) и вправе публично делиться снимком. Локальный файл сохраняется до отправки; при ошибке загрузки программа возвращает код 3. Используется multipart API [из документации Chatterino](https://wiki.chatterino.com/Image%20Uploader/). Живая загрузка из среды разработки не проверена.
