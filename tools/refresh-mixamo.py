#!/usr/bin/env python3
"""Mint a fresh Mixamo bearer from a signed-in session, and write it to ~/.aaabench.env.

    ~/imagegen/bin/python tools/refresh-mixamo.py --login    # once: a window opens, you sign in
    ~/imagegen/bin/python tools/refresh-mixamo.py            # every time after: headless, silent

Why this exists: Mixamo authenticates with an Adobe IMS **access token that expires after 24
hours**, not an API key. A static token in an env file is dead by the second session, and the
failure is quiet — the API answers 401 and an agent reasonably concludes the source is closed.

The Adobe *session cookie* behind it lasts far longer. So the sustainable arrangement is to keep
that session in a browser profile this harness owns, and re-derive a token from it on demand:
loading mixamo.com with a live session silently mints a new access token into local storage, which
is exactly what happens when a human returns the next morning without logging in again.

The profile lives at ~/.aaabench-browser and belongs to this harness. It is deliberately NOT the
operator's own Chrome profile: nothing here reads, copies or unlocks a browser they are using.

Exit codes: 0 fresh token written · 2 not signed in (run with --login) · 3 signed in but no token.
"""
import argparse, base64, json, os, pathlib, re, sys, time

PROFILE = pathlib.Path.home() / ".aaabench-browser"
ENV_FILE = pathlib.Path.home() / ".aaabench.env"
GPU_ARGS = ["--enable-unsafe-webgpu", "--use-angle=metal"]


def token_life_hours(tok):
    """Hours remaining on an Adobe IMS JWT, or None if it will not parse."""
    try:
        p = tok.split(".")[1]
        p += "=" * (-len(p) % 4)
        d = json.loads(base64.urlsafe_b64decode(p))
        return round(((int(d["created_at"]) + int(d["expires_in"])) / 1000 - time.time()) / 3600, 1)
    except Exception:
        return None


def write_env(key, value):
    ENV_FILE.touch(mode=0o600, exist_ok=True)
    os.chmod(ENV_FILE, 0o600)
    text = ENV_FILE.read_text()
    line = f"export {key}='{value}'"
    if re.search(rf"^export {key}=", text, re.M):
        text = re.sub(rf"^export {key}=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + ("\n" if text.strip() else "") + line + "\n"
    ENV_FILE.write_text(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true",
                    help="open a window so you can sign in; the session is then kept for later runs")
    ap.add_argument("--print", dest="show", action="store_true", help="print the token instead of storing it")
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is not importable by this interpreter. Try: ~/imagegen/bin/python " + " ".join(sys.argv))

    PROFILE.mkdir(mode=0o700, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=not a.login, args=GPU_ARGS,
            viewport={"width": 1400, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.mixamo.com/", wait_until="load", timeout=60000)

        if a.login:
            print("Sign in to Mixamo in the window that opened. Waiting up to 5 minutes…")
            deadline = time.time() + 300
            while time.time() < deadline:
                if page.evaluate("() => !!localStorage.getItem('access_token')"):
                    break
                page.wait_for_timeout(2000)

        # Give IMS a moment to complete silent auth on a returning session.
        tok = None
        for _ in range(12):
            tok = page.evaluate("() => localStorage.getItem('access_token')")
            if tok:
                break
            page.wait_for_timeout(1500)

        if not tok:
            signed_out = page.evaluate(
                "() => /log ?in|sign ?up/i.test(document.body.innerText.slice(0, 400))")
            ctx.close()
            if signed_out or a.login:
                print("not signed in — run once with --login", file=sys.stderr)
                sys.exit(2)
            print("signed in but no token appeared", file=sys.stderr)
            sys.exit(3)

        ok = page.evaluate(
            """async (t) => {
                 const r = await fetch('https://www.mixamo.com/api/v1/products?page=1&limit=1&type=Motion',
                   { headers: { Authorization: 'Bearer ' + t, 'X-Api-Key': 'mixamo2' } });
                 return r.status;
               }""", tok)
        ctx.close()

    hours = token_life_hours(tok)
    if a.show:
        print(tok)
    else:
        write_env("MIXAMO_BEARER", tok)
        print(f"wrote MIXAMO_BEARER to {ENV_FILE}")
    print(f"api check: {ok}   valid for: {hours}h")
    if ok != 200:
        sys.exit(3)


if __name__ == "__main__":
    main()
