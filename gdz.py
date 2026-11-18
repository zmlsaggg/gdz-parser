"""Interactive Google search and local GDZ preview."""
import argparse
import asyncio
import html
import re
import sys
from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import parse_qs, urlencode, urlsplit
import webbrowser

ADS = ('doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
       'adnxs.com', 'adfox.ru', 'an.yandex.ru')
STOP = {'гдз', 'страница', 'страницу', 'стр', 'класс', 'решение', 'решения'}


def tokens(text):
    return set(re.findall(r'[а-яёa-z]+|\d+', text.lower().replace('ё', 'е')))


def search_links(hrefs):
    seen = set()
    for href in hrefs:
        if href.startswith(('/url?', 'https://www.google.com/url?')):
            args = parse_qs(urlsplit(href).query)
            href = (args.get('q') or args.get('url') or [''])[0]
        try:
            link = urlsplit(href)
            host = link.hostname or ''
        except ValueError:
            continue
        if (link.scheme not in ('http', 'https') or not host or link.username
                or re.search(r'(^|\.)(google\.[a-z.]+|youtube\.com|gstatic\.com)$', host)):
            continue
        url = link._replace(fragment='').geturl()
        if url not in seen:
            seen.add(url)
            yield url


def rank(query, title, text, images):
    words = tokens(query) - STOP
    headline = tokens(title)
    body = tokens(text)
    page = re.search(r'(?:страниц[ауые]?|стр\.?)\s*(\d+)|(\d+)\s*(?:страниц[ауые]?|стр\.?)(?!\w)', query.lower())
    if page:
        number = next(n for n in page.groups() if n)
        if number not in headline | body:
            return 0
    if not words or not (words & (headline | body)) or not (images or len(text) > 100):
        return 0
    if re.search(r'оплатите.{0,40}(?:доступ|подписку)|войдите.{0,40}чтобы.{0,30}просмотр', text.lower()):
        return 0
    return 3 * len(words & headline) + len(words & body) + min(images, 3)


KAPPA_UPLOAD = 'https://kappa.lol/api/upload'


async def upload_kappa(request, image):
    response = await request.post(KAPPA_UPLOAD, multipart={
        'file': {'name': 'preview.png', 'mimeType': 'image/png', 'buffer': image},
    }, timeout=15000, max_redirects=0, max_retries=0)
    try:
        if not response.ok:
            raise ValueError(f'HTTP {response.status}')
        data = await response.json()
        link = data.get('link') if isinstance(data, dict) else None
        if not isinstance(link, str) or not re.fullmatch(r'https://kappa\.lol/[A-Za-z0-9_-]+(?:\.png)?', link):
            raise ValueError('неожиданный формат ссылки в ответе сервиса')
        if not link.endswith('.png') and data.get('ext') == '.png':
            link += '.png'
        return link
    finally:
        await response.dispose()


async def run(args, query):
    from playwright.async_api import async_playwright, Error

    async def filter_ads(route):
        host = urlsplit(route.request.url).hostname or ''
        if any(host == d or host.endswith('.' + d) for d in ADS):
            await route.abort()
        else:
            await route.continue_()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(locale='ru-RU', viewport={'width': 1280, 'height': 900}, accept_downloads=False, service_workers='block')
        await context.route('**/*', filter_ads)
        urls = []
        if args.url:
            urls = list(search_links(args.url))
        else:
            search = await context.new_page()
            for start in range(0, args.limit * 2, 10):
                await search.goto('https://www.google.com/search?' + urlencode({'q': 'ГДЗ ' + query, 'start': start, 'hl': 'ru'}), wait_until='domcontentloaded', timeout=15000)
                if '/sorry/' in search.url or 'consent.google.' in search.url:
                    print('Google запросил проверку или согласие. Используйте --url со ссылками из браузера.', file=sys.stderr)
                    break
                links = await search.locator('#search a:has(h3)').evaluate_all('(a) => a.map(x => x.href)')
                new = [u for u in search_links(links) if u not in urls]
                urls.extend(new)
                if not new or len(urls) >= args.limit:
                    break
            await search.close()
        best = None
        semaphore = asyncio.Semaphore(4)

        async def inspect(url):
            nonlocal best, folder
            async with semaphore:
                page = await context.new_page()
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=12000)
                    if not response or not response.ok or 'text/html' not in response.headers.get('content-type', ''):
                        return
                    try:
                        await page.wait_for_load_state('load', timeout=2500)
                    except Error:
                        pass
                    title = await page.title()
                    main = page.locator('main:visible, article:visible, [role=main]:visible').first
                    if not await main.count():
                        main = page.locator('body')
                    headings = await page.locator('h1').all_text_contents()
                    text = (await main.inner_text(timeout=2500)).strip()
                    images = await main.locator('img').evaluate_all('xs => xs.filter(x => x.naturalWidth >= 230 && x.naturalHeight >= 120 && x.getClientRects().length).length')
                    score = rank(query, ' '.join([title, *headings]), text, images)
                    if score and (best is None or score > best[0]):
                        if args.mode in ('html', 'image') and images:
                            await main.locator('img:visible').evaluate_all('''xs => {
                                const image = xs.find(x => x.naturalWidth >= 230 && x.naturalHeight >= 120);
                                image?.scrollIntoView({block: 'start'});
                            }''')
                        shot = await page.screenshot(timeout=5000, animations='disabled', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 900}) if args.mode in ('html', 'image') else None
                        if best is None or score > best[0]:
                            best = score, page.url, title, text, shot
                except Error:
                    pass
                finally:
                    await page.close()

        print(f'Проверяю страниц: {min(len(urls), args.limit)}')
        await asyncio.gather(*(inspect(u) for u in urls[:args.limit]))
        if best is None:
            print('Подходящая открытая страница не найдена. Уточните запрос или передайте ссылки через --url.')
            return 1
        _, url, title, text, shot = best
        print(f'{title}\nИсточник: {url}')
        if args.mode == 'text':
            print(text[:5000])
            return 0
        Path('results').mkdir(exist_ok=True)
        folder = Path(mkdtemp(prefix='gdz-', dir='results')).resolve()
        image = folder / 'preview.png'
        image.write_bytes(shot)
        output = image
        if args.mode == 'html':
            output = folder / 'index.html'
            output.write_text(f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(title)}</title>
<style>body{{font:1rem system-ui;max-width:75rem;margin:2rem auto;padding:0 1rem}}img{{max-width:100%}}pre{{white-space:pre-wrap}}</style>
<h1>{html.escape(title)}</h1><p><a href="{html.escape(url, quote=True)}">Открыть источник</a></p><img src="preview.png" alt="Снимок видимой области"><pre>{html.escape(text[:20000])}</pre></html>''', encoding='utf-8')
        print(f'Сохранено: {output}')
        if args.upload_kappa:
            request = await pw.request.new_context()
            try:
                print(f'Ссылка kappa.lol: {await upload_kappa(request, shot)}')
            except (Error, ValueError) as exc:
                print(f'Не удалось загрузить на kappa.lol: {exc}. Локальные файлы сохранены.', file=sys.stderr)
                return 3
            finally:
                await request.dispose()
        if not args.no_open:
            webbrowser.open(output.as_uri())
        return 0


def main():
    parser = argparse.ArgumentParser(description='Поиск открытых страниц ГДЗ')
    parser.add_argument('query', nargs='?', help='Запрос; если не задан, будет запрошен')
    parser.add_argument('--url', action='append', help='Проверить ссылку вместо поиска Google (можно повторять)')
    parser.add_argument('--limit', type=int, default=20, choices=range(1, 101), metavar='1–100')
    parser.add_argument('--mode', choices=('html', 'image', 'text'), default='html')
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--upload-kappa', action='store_true', help='Опубликовать PNG на kappa.lol (18+; только если у вас есть право делиться снимком)')
    args = parser.parse_args()
    if args.upload_kappa and args.mode == 'text':
        parser.error('--upload-kappa требует --mode image или --mode html.')
    try:
        query = (args.query or input('Введите запрос ГДЗ: ')).strip()
        if not query:
            parser.error('Введите непустой запрос.')
        return asyncio.run(run(args, query))
    except (KeyboardInterrupt, EOFError):
        return 130
    except Exception as exc:
        print(f'Ошибка: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
