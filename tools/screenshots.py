"""Dizayn tekshiruvi: sahifalarni 1440px va 375px da suratga oladi va to'liq oqimni sinaydi.

Ishlatish (server ishlab turgan bo'lishi kerak):
    python tools/screenshots.py [--base http://127.0.0.1:8765] [--only shots|flow]

Lokal Chrome ishlatiladi (channel="chrome"), Playwright brauzer yuklab olinmaydi.
Demo foydalanuvchi: seed_data yaratgan demo/demo12345.
"""

import argparse
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"
WIDTHS = {"desktop": (1440, 900), "mobile": (375, 812)}
CHECK_ONLY = {"small": (360, 740)}  # qabul mezoni: 360px, faqat tekshiruv (surat saqlanmaydi)

problems = []


def check_page(page, name):
    """Gorizontal scroll va konsol xatolarini tekshiradi."""
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    if overflow > 0:
        problems.append(f"{name}: gorizontal scroll {overflow}px")


def shot(page, name, full_page=True):
    page.wait_for_timeout(350)  # shriftlar va animatsiyalar
    check_page(page, name)
    if name.endswith("-small"):
        print("  ok", name)
        return
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    print("  +", path.relative_to(ROOT))


def login(page, base, username="demo", password="demo12345"):
    page.goto(f"{base}/accounts/login/")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", password)
    page.click("form[method=post] button[type=submit]")
    page.wait_for_load_state("networkidle")


def visible_card(page):
    return page.locator(".question-card:not(.d-none)").first


def new_context(browser, viewport):
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]}, device_scale_factor=1)
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and problems.append(f"console: {m.text}"))
    page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
    # Imtihondan chiqishdagi beforeunload ogohlantirishini qabul qilamiz
    page.on("dialog", lambda d: d.accept() if d.type == "beforeunload" else d.dismiss())
    return ctx, page


def run_shots(browser, base, widths=WIDTHS):
    for label, viewport in widths.items():
        print(f"[{label} {viewport[0]}px]")
        ctx, page = new_context(browser, viewport)

        for path, name in [("/", "01-home"), ("/accounts/login/", "02-login"), ("/accounts/register/", "03-register")]:
            page.goto(base + path)
            shot(page, f"{name}-{label}")

        # Xato holati: noto'g'ri parol
        page.goto(f"{base}/accounts/login/")
        page.fill("input[name=username]", "demo")
        page.fill("input[name=password]", "notogri-parol")
        page.click("form[method=post] button[type=submit]")
        page.wait_for_load_state("networkidle")
        shot(page, f"02b-login-error-{label}", full_page=False)

        login(page, base)
        page.goto(f"{base}/mavzular/")
        shot(page, f"04-topics-{label}")

        # Mashq: birinchi mavzu, bitta javob
        page.locator("form[action*='/mashq/'] button[type=submit]").first.click()
        page.wait_for_load_state("networkidle")
        shot(page, f"05-practice-{label}", full_page=False)
        visible_card(page).locator(".answer-option").first.click()
        page.wait_for_timeout(600)
        shot(page, f"06-practice-answered-{label}")

        page.goto(f"{base}/imtihon/")
        shot(page, f"07-exam-start-{label}")
        start = page.locator("form[method=post] button[type=submit]:has-text('Imtihonni boshlash'), a:has-text('Davom ettirish')").first
        start.click()
        page.wait_for_load_state("networkidle")
        for i in range(3):
            visible_card(page).locator(".answer-option").nth(i % 4).click()
            page.wait_for_timeout(250)
            page.click("#next-btn")
        shot(page, f"08-exam-{label}", full_page=False)
        page.locator("[data-bs-target='#finishModal']").first.click()
        page.wait_for_selector("#finishModal.show")
        page.wait_for_timeout(300)
        shot(page, f"09-exam-finish-modal-{label}", full_page=False)
        page.keyboard.press("Escape")

        page.goto(f"{base}/accounts/profile/")
        page.wait_for_timeout(500)  # Chart.js
        shot(page, f"10-profile-{label}")
        result_link = page.locator("a[href*='/natija/']").first
        if result_link.count():
            result_link.click()
            page.wait_for_load_state("networkidle")
            shot(page, f"11-result-{label}")
        else:
            problems.append("profilda natija havolasi topilmadi")
        ctx.close()


def run_flow(browser, base):
    """Yangi foydalanuvchi: ro'yxatdan o'tish -> mashq -> imtihon -> natija -> profil."""
    print("[flow 375px]")
    ctx, page = new_context(browser, WIDTHS["mobile"])
    username = f"sinov{int(time.time())}"
    page.goto(f"{base}/accounts/register/")
    page.fill("input[name=first_name]", "Sinov")
    page.fill("input[name=username]", username)
    page.fill("input[name=email]", f"{username}@example.com")
    page.fill("input[name=password1]", "Sinov-parol-2026")
    page.fill("input[name=password2]", "Sinov-parol-2026")
    page.click("form[method=post] button[type=submit]")
    page.wait_for_url("**/mavzular/")
    print("  ok: ro'yxatdan o'tish -> mavzular")

    page.locator("form[action*='/mashq/'] button[type=submit]").first.click()
    page.wait_for_url("**/mashq/sessiya/**")
    total = page.locator(".question-card").count()
    for _ in range(total):
        card = visible_card(page)
        card.locator(".answer-option").first.click()
        card.locator(".explanation:not(.d-none)").wait_for()
        page.click("#next-btn")
    page.locator("#practice-summary:not(.d-none)").wait_for()
    page.locator("#practice-summary button[type=submit]").click()
    page.wait_for_url("**/natija/**")
    print(f"  ok: mashq ({total} savol) -> natija")

    page.goto(f"{base}/imtihon/")
    page.locator("button:has-text('Imtihonni boshlash')").click()
    page.wait_for_url("**/imtihon/*/")
    page.reload()  # sahifa yangilansa ham davom etadi
    timer_text = page.inner_text("#timer")
    count = page.locator(".question-card").count()
    for i in range(count):
        card = visible_card(page)
        with page.expect_response("**/javob/") as resp:
            card.locator(".answer-option").nth(i % 4).click()
        assert resp.value.ok, "javob saqlanmadi"
        if i < count - 1:
            page.click("#next-btn")
    answered = page.locator(".nav-num.answered").count()
    page.locator("[data-bs-target='#finishModal']").first.click()
    page.wait_for_selector("#finishModal.show")
    page.locator("#finishModal button[form=finish-form]").first.click()
    page.wait_for_url("**/natija/**")
    shot(page, "12-flow-result-mobile")
    print(f"  ok: imtihon ({answered}/{count} javob, taymer {timer_text}) -> natija")

    page.goto(f"{base}/accounts/profile/")
    assert page.locator("a[href*='/natija/']").count() >= 2, "profilda imtihonlar yo'q"
    print("  ok: profil")
    ctx.close()


def run_roles(browser, base):
    """Yagona login: admin -> dashboard (13–15), mehmon /admin/ -> login (16), o'quvchi /admin/ -> profil (17)."""
    for label, viewport in WIDTHS.items():
        print(f"[rollar {label} {viewport[0]}px]")
        ctx, page = new_context(browser, viewport)

        page.goto(f"{base}/admin/")
        page.wait_for_load_state("networkidle")
        if "/accounts/login/?next=%2Fadmin%2F" not in page.url:
            problems.append(f"mehmon /admin/ -> {page.url}")
        shot(page, f"16-login-redirect-{label}", full_page=False)
        page.fill("input[name=username]", "admin")
        page.fill("input[name=password]", "admin12345")
        page.click("form[method=post] button[type=submit]")
        page.wait_for_load_state("networkidle")
        if not page.url.rstrip("/").endswith("/admin"):
            problems.append(f"admin login -> {page.url}")
        print("  ok: admin -> boshqaruv paneli")
        shot(page, f"13-admin-dashboard-{label}")

        page.goto(f"{base}/admin/quiz/question/")
        shot(page, f"14-admin-questions-{label}")
        page.goto(f"{base}/admin/quiz/question/?rasm=bor")
        page.locator("#result_list a[href*='/change/']").first.click()
        page.wait_for_load_state("networkidle")
        shot(page, f"15-admin-question-form-{label}")
        ctx.close()

        ctx, page = new_context(browser, viewport)
        page.goto(f"{base}/accounts/login/")
        page.fill("input[name=username]", "demo")
        page.fill("input[name=password]", "demo12345")
        page.click("form[method=post] button[type=submit]")
        page.wait_for_load_state("networkidle")
        if not page.url.endswith("/accounts/profile/"):
            problems.append(f"demo login -> {page.url}")
        page.goto(f"{base}/admin/")
        page.wait_for_load_state("networkidle")
        if not page.url.endswith("/accounts/profile/") or "faqat administratorlar" not in page.content():
            problems.append(f"o'quvchi /admin/ -> {page.url}")
        print("  ok: demo -> profil; /admin/ -> profil + ogohlantirish")
        shot(page, f"17-student-admin-denied-{label}", full_page=False)
        ctx.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    parser.add_argument("--only", choices=["shots", "flow", "roles"])
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        if args.only in (None, "shots"):
            run_shots(browser, args.base)
            run_shots(browser, args.base, CHECK_ONLY)
        if args.only in (None, "roles"):
            run_roles(browser, args.base)
        if args.only in (None, "flow"):
            run_flow(browser, args.base)
        browser.close()
    if problems:
        print("\nMUAMMOLAR:")
        for item in problems:
            print("  -", item)
        sys.exit(1)
    print("\nMuammo topilmadi.")


if __name__ == "__main__":
    main()
