import sys
import urllib.request
import urllib.error

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
BASE_URL = BASE_URL.rstrip("/")

ENDPOINTS = [
    "/",
    "/feed",
    "/account",
    "/upload",
    "/settings",
    "/search",
    "/messenger",
    "/live",
    "/create",
    "/create/reel",
    "/create/post",
    "/create/story",
    "/create/live",
]


def check(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.geturl()
    except urllib.error.HTTPError as err:
        return err.code, err.geturl()
    except Exception as err:
        return None, str(err)


def main():
    print("Base:", BASE_URL)
    ok = True
    for path in ENDPOINTS:
        status, final_url = check(BASE_URL + path)
        if status is None:
            ok = False
            print("FAIL", path, "->", final_url)
            continue
        if status >= 500:
            ok = False
            print("FAIL", path, "->", status, final_url)
            continue
        print("OK  ", path, "->", status, final_url)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
