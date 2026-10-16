"""Theme browser smoke test. Requires playwright and a Chromium installation.
uv run --with playwright python scripts/test_theme.py --browser PATH_TO_CHROME --artifacts OUTPUT_DIR
External requests are blocked so legacy CDN availability cannot affect the checks.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from threading import Thread
from urllib.parse import quote
from playwright.sync_api import sync_playwright


def assert_tag_contrast(tags):
    """Require opaque tag backgrounds and WCAG AA normal-text contrast."""
    assert tags.count() > 0
    ratios = []
    for style in tags.evaluate_all('''elements => elements.map(el => {
        const css = getComputedStyle(el);
        return {text: el.textContent, color: css.color, background: css.backgroundColor};
    })'''):
        foreground = [float(x) for x in re.findall(r'[\d.]+', style['color'])]
        background = [float(x) for x in re.findall(r'[\d.]+', style['background'])]
        assert len(background) == 3 or background[3] == 1, style
        luminances = []
        for rgb in [foreground, background]:
            linear = [c / 255 / 12.92 if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb[:3]]
            luminances.append(sum(c * weight for c, weight in zip(linear, [0.2126, 0.7152, 0.0722])))
        ratio = (max(luminances) + 0.05) / (min(luminances) + 0.05)
        assert ratio >= 4.5, (style, ratio)
        ratios.append(ratio)
    return min(ratios)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser')
    parser.add_argument('--artifacts', required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    artifacts = Path(args.artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    pages = sorted(repo.rglob('*.html'))
    assert pages
    for file in pages:
        html = file.read_text(encoding='utf-8')
        assert html.count('src="/js/theme.js"') == 1, file
        assert html.count('href="/css/theme.css"') == 1, file
        assert html.index('src="/js/theme.js"') < html.index('</head>'), file
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(repo)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    checks = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=args.browser, headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, color_scheme='light')
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base, wait_until='load')
            assert page.locator('html').get_attribute('data-theme') == 'light'
            toggle = page.locator('#theme-toggle')
            assert toggle.count() == 1
            page.screenshot(path=str(artifacts / 'desktop-light.png'))
            toggle.click()
            assert toggle.get_attribute('aria-pressed') == 'true'
            assert page.evaluate('localStorage.getItem("blog-theme")') == 'dark'
            assert page.locator('body').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(23, 26, 32)'
            page.screenshot(path=str(artifacts / 'desktop-dark.png'))
            page.reload(wait_until='load')
            assert page.locator('html').get_attribute('data-theme') == 'dark'
            checks.append('desktop click + persistence + reload')
            tag_ratios = []
            for path, selector, name in [('/tags/', '#tag_cloud a', 'cloud'), ('/', '.sidebar-container .tags a', 'sidebar'), ('/2024/05/08/record-opencv/', '.intro-header .tags a', 'header')]:
                page.goto(base + path, wait_until='load')
                tags = page.locator(selector)
                page.screenshot(path=str(artifacts / (name + '-tags-dark.png')))
                tag_ratios.append(assert_tag_contrast(tags))
                # Reproduce the existing plugin's inline backgrounds without a CDN.
                if name == 'cloud':
                    page.add_script_tag(url=base + '/js/jquery.tagcloud.js')
                    page.evaluate("$('#tag_cloud a').tagcloud({color: {start: '#bbbbee', end: '#0085a1'}})")
                    tag_ratios.append(assert_tag_contrast(tags))
                tags.first.hover()
                tag_ratios.append(assert_tag_contrast(tags))
                page.mouse.move(0, 0)
                tags.first.focus()
                tag_ratios.append(assert_tag_contrast(tags))
            checks.append(f'dark cloud/sidebar/header tags, inline plugin, hover/focus: minimum contrast {min(tag_ratios):.2f}:1')
            for file in pages:
                response = page.goto(base + '/' + quote(file.relative_to(repo).as_posix()), wait_until='domcontentloaded')
                assert response.status == 200, file
                assert page.locator('#theme-toggle').count() == 1, file
                assert page.locator('html').get_attribute('data-theme') == 'dark', file
                assert page.locator('body').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(23, 26, 32)', file
            checks.append(f'all {len(pages)} HTML pages: assets + button + dark background')
            page.goto(base + '/2024/05/08/record-opencv/', wait_until='load')
            assert page.locator('.highlight').first.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(34, 40, 50)'
            page.screenshot(path=str(artifacts / 'article-dark.png'))
            checks.append('article code block dark styling')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(base, wait_until='load')
            box = page.locator('#theme-toggle').bounding_box()
            assert box and box['width'] >= 44 and box['height'] >= 44
            assert box['x'] >= 0 and box['x'] + box['width'] <= 390
            page.screenshot(path=str(artifacts / 'mobile-layout.png'))
            width = page.evaluate('document.documentElement.scrollWidth')
            baseline_width = page.evaluate('''() => {
                const sheet = document.querySelector('link[href="/css/theme.css"]');
                sheet.disabled = true;
                const width = document.documentElement.scrollWidth;
                sheet.disabled = false;
                return width;
            }''')
            assert width <= max(390, baseline_width), (width, baseline_width)
            page.locator('.navbar-toggle').click()
            page.wait_for_timeout(600)
            assert page.locator('#huxblog_navbar').evaluate('(el) => getComputedStyle(el).opacity') == '1'
            page.screenshot(path=str(artifacts / 'mobile-dark.png'))
            page.locator('#theme-toggle').click()
            assert page.locator('html').get_attribute('data-theme') == 'light'
            checks.append('mobile navigation + button bounds + light/dark switch')
            page.locator('#theme-toggle').focus()
            page.keyboard.press('Space')
            assert page.locator('html').get_attribute('data-theme') == 'dark'
            checks.append('keyboard Space toggles theme')
            page.evaluate('localStorage.removeItem("blog-theme")')
            page.reload(wait_until='load')
            page.emulate_media(color_scheme='dark')
            page.wait_for_function('document.documentElement.dataset.theme === "dark"')
            page.emulate_media(color_scheme='light')
            page.wait_for_function('document.documentElement.dataset.theme === "light"')
            checks.append('follows OS changes without a saved preference')
            page.locator('#theme-toggle').click()
            page.emulate_media(color_scheme='dark')
            page.emulate_media(color_scheme='light')
            assert page.locator('html').get_attribute('data-theme') == 'dark'
            second = context.new_page()
            second.goto(base, wait_until='load')
            second.locator('#theme-toggle').click()
            page.wait_for_function('document.documentElement.dataset.theme === "light"')
            checks.append('manual preference overrides OS + synchronizes across tabs')
            page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('storage blocked');}})")
            page.reload(wait_until='load')
            page.locator('#theme-toggle').click()
            assert page.locator('html').get_attribute('data-theme') == 'dark'
            checks.append('storage unavailable: switch still works')
            assert not errors, errors
            checks.append('no uncaught JavaScript errors')
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    report = '\n'.join('PASS ' + check for check in checks) + '\nPASS temporary browser and HTTP server closed\n'
    (artifacts / 'verification.txt').write_text(report, encoding='utf-8')
    print(report)


if __name__ == '__main__':
    main()
