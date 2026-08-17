"""从 Shopify 店铺抓取全部商品/系列的图片与视频，按用途组织好目录。

为 jetset.ch（Shopify）写的，换任何 Shopify 店铺都能用。

用法：
    python3 tools/fetch_shopify_assets.py https://jetset.ch --out assets
    python3 tools/fetch_shopify_assets.py https://jetset.ch --out assets --limit 3   # 先试跑 3 个商品

依赖：只用标准库，不需要 pip install。

两条取数路径，各管一半：
  A. 商品与系列走公开 JSON 接口，比爬页面干净：
       /products.json?limit=250&page=N    全部商品（含图片）
       /products/<handle>.js              单商品完整媒体，**视频只能从这里拿**
       /collections.json?limit=250&page=N 全部系列（含封面图）
  B. 首页横幅 / 宣传海报 / 内容页与博客的配图视频没有 JSON 接口，
     从 HTML 源码里正则捞 cdn.shopify.com 地址——比逐个解析
     <img src>/srcset/data-src/CSS 背景图更全，懒加载和内联 JSON 里的都能捞到。

两个关键处理：
  · 抓原图：Shopify CDN 会在文件名后加 _1024x1024 之类的尺寸后缀，抓之前剥掉
  · 去重：同一张图常以多个 URL/尺寸出现，按内容 sha256 判重，重复的只记账不落盘

对站点友好：全程串行 + 固定间隔，遇 429 按 Retry-After 退避。别改小 --delay。
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Shopify CDN 的尺寸后缀：foo_1024x1024.jpg / foo_grande.jpg / foo_800x_crop_center.jpg
SIZE_SUFFIX = re.compile(
    r"_(?:\d+x\d*|\d*x\d+|pico|icon|thumb|small|compact|medium|large|grande|master)"
    r"(?:_crop_\w+)?(?=\.[a-zA-Z0-9]+(?:\?|$))"
)
UNSAFE = re.compile(r"[^\w.\-]+")


def original_url(url: str) -> str:
    """剥掉尺寸后缀换原图；协议归一，否则 http/https 同图会算成两条。"""
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("http://"):
        url = "https://" + url[7:]
    return SIZE_SUFFIX.sub("", url)


def safe(name: str, fallback: str = "x") -> str:
    s = UNSAFE.sub("-", (name or "").strip()).strip("-.")
    return (s or fallback)[:80]


class Fetcher:
    def __init__(self, delay: float):
        self.delay = delay
        self.last = 0.0

    def _wait(self):
        gap = time.time() - self.last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self.last = time.time()

    def get(self, url: str, tries: int = 5) -> bytes | None:
        for i in range(tries):
            self._wait()
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code in (429, 430, 503):
                    wait = int(e.headers.get("Retry-After") or 0) or (5 * (i + 1))
                    print(f"    限流，等 {wait}s 后重试（{i + 1}/{tries}）", flush=True)
                    time.sleep(wait)
                    continue
                print(f"    HTTP {e.code}: {url}", flush=True)
                return None
            except Exception as e:
                print(f"    请求失败（{i + 1}/{tries}）：{type(e).__name__} {e}", flush=True)
                time.sleep(3 * (i + 1))
        return None

    def get_json(self, url: str):
        raw = self.get(url)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"    不是 JSON：{url}", flush=True)
            return None


class Store:
    """下载 + 去重 + 记账。"""

    def __init__(self, out: Path, fetcher: Fetcher):
        self.out = out
        self.f = fetcher
        self.by_hash: dict[str, str] = {}
        self.rows: list[dict] = []
        self.dup = 0

    def save(self, url: str, rel: Path, kind: str, owner: str, title: str) -> None:
        dest = self.out / rel
        if dest.exists():                      # 断点续传：已下过的跳过
            self._record(url, rel, kind, owner, title, dest.stat().st_size,
                         self._hash_file(dest), "已存在")
            return
        data = self.f.get(url)
        if data is None:
            print(f"    ✗ 下载失败 {url}", flush=True)
            return
        h = hashlib.sha256(data).hexdigest()
        if h in self.by_hash:                  # 同一张图的另一个 URL，不重复落盘
            self.dup += 1
            self._record(url, Path(self.by_hash[h]), kind, owner, title, len(data), h, "内容重复")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        self.by_hash[h] = str(rel)
        self._record(url, rel, kind, owner, title, len(data), h, "已下载")
        print(f"    ✓ {rel}  ({len(data) // 1024} KB)", flush=True)

    def note_video(self, url: str, owner: str, title: str, note: str) -> None:
        """只登记视频地址，不下载。"""
        if any(r["source_url"] == url and r["kind"] == "video_url" for r in self.rows):
            return
        self._record(url, Path("-"), "video_url", owner, title, 0, "", note)
        print(f"    ▶ 视频地址：{url}", flush=True)

    @staticmethod
    def _hash_file(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def _record(self, url, rel, kind, owner, title, size, h, status):
        self.rows.append({"kind": kind, "owner": owner, "title": title,
                          "local_path": str(rel), "bytes": size,
                          "sha256": h, "status": status, "source_url": url})

    def write_manifest(self) -> None:
        p = self.out / "manifest.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8-sig") as fp:
            w = csv.DictWriter(fp, fieldnames=["kind", "owner", "title", "local_path",
                                               "bytes", "sha256", "status", "source_url"])
            w.writeheader()
            w.writerows(self.rows)
        print(f"\n清单已写入 {p}")


def fetch_products(base: str, f: Fetcher, limit: int | None) -> list[dict]:
    out, page = [], 1
    while True:
        data = f.get_json(f"{base}/products.json?limit=250&page={page}")
        items = (data or {}).get("products") or []
        if not items:
            break
        out.extend(items)
        print(f"  商品列表第 {page} 页：{len(items)} 个（累计 {len(out)}）", flush=True)
        if limit and len(out) >= limit:
            return out[:limit]
        page += 1
    return out


# 页面上的素材（首页横幅、宣传海报、内容页配图/视频）没有 JSON 接口。
# 但 Shopify 把所有上传素材都放在 cdn.shopify.com 下，所以直接从 HTML 源码里
# 正则捞 CDN 地址，比逐个解析 <img src>/srcset/data-src/CSS 背景图更全：
# 懒加载的、藏在内联 JSON 里的、写在 style 里的，一次都跑不掉。
# 页面里的素材地址三种写法都得认，少一种就整批漏：
#   //cdn.shopify.com/s/files/…      协议相对 —— 主题渲染出来的绝大多数是这种
#   https://cdn.shopify.com/s/files/… 显式协议 —— products.json 接口返回这种
#   /cdn/shop/…                      站内绝对路径 —— 新版 Shopify 主题在用
# 路径不再限定 /s/files|/videos：cdn.shopify.com 下还有 /products、/collections、
# /articles 等目录，是否为素材交给扩展名判断，js/css 自然被滤掉。
CDN_ASSET = re.compile(
    r"(?:https?:)?//cdn\.shopify\.com/[^\s\"'\\)<>]+"
    r"|(?:(?:https?:)?//[\w.\-]+)?/cdn/shop/[^\s\"'\\)<>]+",
    re.I,
)

# 第三方托管视频（YouTube/Vimeo 嵌入）页面里只有 iframe，源文件本就下不到；
# 自托管 mp4 也一律只登记地址不下载——视频体积大，交给人自己按需取。
EXTERNAL_VIDEO = re.compile(
    r"youtube(?:-nocookie)?\.com/(?:embed|v|shorts)/([\w\-]{11})"
    r"|youtu\.be/([\w\-]{11})"
    r"|youtube\.com/watch\?v=([\w\-]{11})"
    # 主题常把 ID 放在属性/字段里而非完整链接：data-video-id="…"、"videoId":"…"、
    # video_id: '…'。延迟加载（deferred-media）的主题初始 HTML 里根本没有 iframe，
    # 只有这个属性，不认就整个漏掉。
    r"|video[-_]?id[\"']?\s*[:=]\s*[\"']([\w\-]{11})[\"']"
    r"|vimeo\.com/(?:video/)?(\d{6,})",
    re.I,
)


def external_videos(text: str) -> list[str]:
    """从 HTML 里提取第三方视频地址（去重保序）。"""
    out = []
    for g in EXTERNAL_VIDEO.findall(text):
        yt = next((x for x in g[:4] if x), "")
        url = f"https://www.youtube.com/watch?v={yt}" if yt else (
            f"https://vimeo.com/{g[4]}" if g[4] else "")
        if url and url not in out:
            out.append(url)
    return out


VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".m3u8"}
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"} | VIDEO_EXT


# 会改变输出尺寸/格式的参数，去掉才能拿到原图；v= 是缓存版本号，留着无害
TRANSFORM_PARAMS = ("width=", "height=", "crop=", "format=", "quality=", "pad_color=")


def _clean_asset_url(u: str, base: str = "") -> str | None:
    """补全为绝对地址、剥尺寸后缀与变换参数拿原图；非媒体文件返回 None。"""
    u = u.replace("&amp;", "&").rstrip(".,;)'\"")
    if u.startswith("/") and not u.startswith("//"):
        u = base.rstrip("/") + u          # 站内绝对路径 /cdn/shop/...
    path, _, query = u.partition("?")
    if Path(path).suffix.lower() not in MEDIA_EXT:
        return None
    # 必须整体重建查询串。早先用正则逐个删参数，把第一个参数连同 "?" 一起删掉时，
    # 剩下的 "&v=…" 就没了问号，变成畸形地址、同一张图还会重复下载一次。
    kept = [kv for kv in query.split("&")
            if kv and not kv.lower().startswith(TRANSFORM_PARAMS)]
    return original_url(path + ("?" + "&".join(kept) if kept else ""))


def sitemap_urls(base: str, f: Fetcher) -> list[tuple[str, str]]:
    """从 sitemap 索引里取出「页面」和「博客文章」的地址。返回 [(用途, url)]。

    多语言站会有 /de/ /fr/ 等重复项，媒体是同一份，只取主语言。
    """
    import xml.etree.ElementTree as ET

    NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    raw = f.get(f"{base}/sitemap.xml")
    if raw is None:
        return []
    children = [e.text for e in ET.fromstring(raw).iter(f"{NS}loc") if e.text]

    host = base.split("//", 1)[-1]
    wanted, out = ("sitemap_pages", "sitemap_blogs"), []
    for sm in children:
        # 跳过语言副本：https://jetset.ch/de/sitemap_pages_1.xml
        after_host = sm.split(host, 1)[-1].lstrip("/")
        if not after_host.startswith("sitemap_"):
            continue
        kind = next((k for k in wanted if k in sm), None)
        if kind is None:
            continue
        sub = f.get(sm)
        if sub is None:
            continue
        for e in ET.fromstring(sub).iter(f"{NS}loc"):
            if e.text:
                out.append(("page" if "pages" in kind else "blog", e.text))
    return out


def harvest_html_assets(base: str, f: Fetcher, store: "Store") -> None:
    """抓首页 + 所有内容页/博客文章里的图片与视频。"""
    targets = [("home", base + "/")] + sitemap_urls(base, f)
    print(f"  待扫描页面 {len(targets)} 个（首页 + 内容页 + 博客）")

    for i, (kind, url) in enumerate(targets, 1):
        html = f.get(url)
        if html is None:
            continue
        # 主题的 section 配置常以 JSON 内嵌在 <script> 里，地址被转义成 https:\/\/...
        # 先还原斜杠，否则这部分素材（海报图往往就在这儿）会整批漏掉
        text = html.decode("utf-8", "ignore").replace("\\/", "/")
        # 根地址取不出页面名，会拿成域名（home-jetset.ch），单独判掉
        path = url.split("//", 1)[-1].partition("/")[2].rstrip("/")
        slug = safe(path.rsplit("/", 1)[-1]) if path else "index"
        for ev in external_videos(text):
            store.note_video(ev, slug, url, "页面中的第三方视频")
        seen, found = set(), 0
        for m in CDN_ASSET.findall(text):
            clean = _clean_asset_url(m, base)
            if not clean or clean in seen:
                continue
            seen.add(clean)
            found += 1
            ext = Path(clean.split("?")[0]).suffix.lower() or ".jpg"
            if ext in VIDEO_EXT:          # 视频只登记地址
                store.note_video(clean, slug, url, "页面中的自托管视频")
                continue
            store.save(clean, Path("pages") / f"{kind}-{slug}" / f"{found:02d}{ext}",
                       "image", slug, url)
        print(f"  [{i}/{len(targets)}] {kind}/{slug}：{found} 个素材", flush=True)


def fetch_collections(base: str, f: Fetcher) -> list[dict]:
    out, page = [], 1
    while True:
        data = f.get_json(f"{base}/collections.json?limit=250&page={page}")
        items = (data or {}).get("collections") or []
        if not items:
            break
        out.extend(items)
        page += 1
    return out


stats: dict = {}


def diagnose(url: str, f: Fetcher) -> None:
    """诊断单个页面：HTML 里到底有哪些 CDN 资源。不下载，只打印。

    用途：某个页面抓到的素材少得可疑时，判断是「页面本来就没有」
    还是「内容由 JS 动态渲染、不在初始 HTML 里」。
    """
    raw = f.get(url)
    if raw is None:
        sys.exit(f"✗ 取不到 {url}")
    text = raw.decode("utf-8", "ignore")
    print(f"页面：{url}\nHTML 大小：{len(raw) // 1024} KB")

    unescaped = text.replace("\\/", "/")
    hits = list(dict.fromkeys(CDN_ASSET.findall(unescaped)))
    print(f"\ncdn.shopify.com 资源共 {len(hits)} 条：")
    kept, dropped = [], []
    for u in hits:
        c = _clean_asset_url(u)
        (kept if c else dropped).append(c or u)
    for u in dict.fromkeys(kept):
        tag = "视频" if Path(u.split("?")[0]).suffix.lower() in VIDEO_EXT else "图片"
        print(f"  [{tag}] {u}")
    print(f"\n非媒体（js/css/字体，已忽略）{len(dropped)} 条")

    # 不限域名扫一遍「像素材的地址」，按 host 分组。
    # 素材换了域名时，这里会直接暴露出来——比逐条猜快得多。
    ANY = re.compile(r"(?:https?:)?//[\w.\-]+/[^\s\"'\\)<>]+\.(?:jpg|jpeg|png|webp|gif|avif|mp4|mov|webm|m3u8)", re.I)
    hosts: dict[str, int] = {}
    for u in ANY.findall(unescaped):
        h = u.split("//", 1)[-1].split("/", 1)[0].lower()
        hosts[h] = hosts.get(h, 0) + 1
    print("\n=== 页面里所有素材地址按域名分布 ===")
    for h, n in sorted(hosts.items(), key=lambda x: -x[1]):
        print(f"  {n:5} 条  {h}")
    rel = len(re.findall(r"[\"'(]/cdn/shop/[^\s\"'\\)<>]+", unescaped))
    print(f"  {rel:5} 条  （站内相对路径 /cdn/shop/…）")

    # 这些迹象说明主体内容是 JS 渲染的，正则抓不到
    evs = external_videos(unescaped)
    selfhosted = [c for c in (_clean_asset_url(u) for u in CDN_ASSET.findall(unescaped))
                  if c and Path(c.split("?")[0]).suffix.lower() in VIDEO_EXT]
    allv = list(dict.fromkeys(evs + selfhosted))
    print(f"\n=== 视频地址 {len(allv)} 条 ===")
    for u in allv:
        print(f"  {u}")
    if not allv:
        print("  （无）")

    print("\n=== 动态渲染迹象 ===")
    for name, needle in (
        ("懒加载属性 data-src", "data-src"),
        ("srcset 多分辨率", "srcset"),
        ("section 渲染接口", "sections?section_id"),
        ("<video> 标签", "<video"),
        ("视频托管 Vimeo", "vimeo"),
        ("视频托管 YouTube", "youtube"),
        ("Shopify 视频 CDN", "cdn.shopify.com/videos"),
    ):
        n = unescaped.lower().count(needle.lower())
        print(f"  {name:22} 出现 {n} 次")
    # 关键词命中但提取不到视频时，把原文摘出来看——是嵌入视频还是频道链接，
    # 光看计数分不清，猜十次不如摘一次。
    print("\n=== youtube / vimeo / <video> 出现在什么上下文 ===")
    for kw in ("youtube", "vimeo", "<video"):
        for mm in list(re.finditer(re.escape(kw), unescaped, re.I))[:6]:
            a, b = max(0, mm.start() - 70), min(len(unescaped), mm.end() + 90)
            frag = re.sub(r"\s+", " ", unescaped[a:b]).strip()
            print(f"  [{kw}] …{frag}…")
    # 不限形式地列出所有第三方视频平台地址（频道页/播放页都会露出来）
    plat = sorted(set(re.findall(
        r"https?://[^\s\"'\\)<>]*(?:youtube\.com|youtu\.be|vimeo\.com)[^\s\"'\\)<>]*",
        unescaped, re.I)))
    print(f"\n=== 页面里所有 youtube/vimeo 地址（{len(plat)} 条，含频道页）===")
    for u in plat[:20]:
        print(f"  {u}")

    print("\n若图片数远少于页面实际所见，说明内容由 JS 动态加载，")
    print("需要用无头浏览器（Playwright）渲染后再抓，或在浏览器里手动存。")


def main() -> None:
    ap = argparse.ArgumentParser(description="抓取 Shopify 店铺的图片与视频")
    ap.add_argument("base", help="店铺地址，如 https://jetset.ch")
    ap.add_argument("--out", default="assets", help="输出目录（默认 assets）")
    ap.add_argument("--delay", type=float, default=0.8, help="请求间隔秒数，默认 0.8")
    ap.add_argument("--limit", type=int, help="只处理前 N 个商品（试跑用）")
    ap.add_argument("--skip-products", action="store_true",
                    help="跳过商品，只抓页面素材（宣传海报/视频）")
    ap.add_argument("--skip-pages", action="store_true",
                    help="跳过页面，只抓商品与系列")
    ap.add_argument("--debug", metavar="URL",
                    help="只诊断一个页面：打印抓到的全部 CDN 地址，不下载任何文件")
    args = ap.parse_args()

    if args.debug:
        diagnose(args.debug, Fetcher(args.delay))
        sys.exit(0)

    base = args.base.rstrip("/")
    out = Path(args.out)
    f = Fetcher(args.delay)
    store = Store(out, f)
    stats.update(js_failed=0, with_media=0, external_video=0, video_from_html=0)

    print(f"店铺：{base}\n输出：{out.resolve()}\n间隔：{args.delay}s\n")

    if not args.skip_products:
        print("【1/4】拉取商品列表")
        products = fetch_products(base, f, args.limit)
        if not products:
            sys.exit("✗ 拿不到 /products.json。可能是被限流、或店铺关闭了该接口。")
        print(f"共 {len(products)} 个商品\n")
    else:
        products = []

    print("【2/4】逐个商品抓图片与视频")
    for i, p in enumerate(products, 1):
        handle = p.get("handle") or f"product-{p.get('id')}"
        title = p.get("title") or handle
        d = Path("products") / safe(handle)
        print(f"  [{i}/{len(products)}] {title}", flush=True)

        for n, img in enumerate(p.get("images") or [], 1):
            src = original_url(img.get("src") or "")
            if not src:
                continue
            ext = Path(src.split("?")[0]).suffix or ".jpg"
            store.save(src, d / f"{n:02d}{ext}", "image", handle, title)

        # 视频只存在于 AJAX 接口的 media 里，products.json 不含
        js = f.get_json(f"{base}/products/{handle}.js")
        if js is None:
            stats["js_failed"] += 1
            print("    △ /products/{}.js 取不到，视频可能因此漏掉".format(handle), flush=True)
        media = (js or {}).get("media") or []
        if media:
            stats["with_media"] += 1
        vn = 0
        for m in media:
            if m.get("media_type") == "video":
                srcs = [x for x in (m.get("sources") or []) if x.get("url")]
                best = max(srcs, key=lambda x: x.get("height") or 0, default=None)
                if best:
                    vn += 1
                    store.note_video(best["url"], handle, title,
                                     f"商品自托管视频 {best.get('height') or '?'}p")
            elif m.get("media_type") == "external_video":
                stats["external_video"] += 1
                store._record(m.get("external_id") or "", Path("-"), "external_video",
                              handle, title, 0, "", f"外部视频（{m.get('host')}），需手动处理")
                print(f"    △ 外部视频（{m.get('host')}），无法直接下载", flush=True)
        # .js 一无所获时回退解析商品页 HTML —— 视频可能只以 <video> 出现在页面里
        if not media:
            html = f.get(f"{base}/products/{handle}")
            if html:
                text = html.decode("utf-8", "ignore").replace("\\/", "/")
                for u in dict.fromkeys(CDN_ASSET.findall(text)):
                    c = _clean_asset_url(u, base)
                    if c and Path(c.split("?")[0]).suffix.lower() in VIDEO_EXT:
                        stats["video_from_html"] += 1
                        store.note_video(c, handle, title, "商品页 HTML 中的自托管视频")
                for ev in external_videos(text):
                    store.note_video(ev, handle, title, "商品页中的第三方视频")

    print("\n【3/4】拉取系列封面")
    for c in ([] if args.skip_products else fetch_collections(base, f)):
        img = (c.get("image") or {}).get("src")
        if not img:
            continue
        src = original_url(img)
        ext = Path(src.split("?")[0]).suffix or ".jpg"
        store.save(src, Path("collections") / f"{safe(c.get('handle'))}{ext}",
                   "collection", c.get("handle") or "", c.get("title") or "")

    print("\n【4/4】抓页面素材（首页横幅 / 宣传海报 / 内容页配图与视频）")
    if args.skip_pages:
        print("  已跳过")
    else:
        harvest_html_assets(base, f, store)

    store.write_manifest()
    downloaded = sum(1 for r in store.rows if r["status"] == "已下载")
    print(f"新下载 {downloaded} 个文件，跳过重复 {store.dup} 个，记录 {len(store.rows)} 条")
    vurls = list(dict.fromkeys(r["source_url"] for r in store.rows
                               if r["kind"] == "video_url" and r["source_url"]))
    if vurls:
        vf = out / "video_urls.txt"
        vf.write_text("\n".join(vurls) + "\n", encoding="utf-8")
        print(f"\n=== 视频地址 {len(vurls)} 条（脚本不下载，已写入 {vf}）===")
        for u in vurls:
            print(f"  {u}")

    print(f"\n=== 视频诊断 ===")
    print(f"  /products/<handle>.js 取数失败：{stats['js_failed']} 个商品"
          + ("  ← 视频漏抓的头号嫌疑" if stats["js_failed"] else ""))
    print(f"  含 media 字段的商品：{stats['with_media']} 个")
    print(f"  外部视频（YouTube/Vimeo，下不到）：{stats['external_video']} 个")
    print(f"  从商品页 HTML 回退抓到的视频：{stats['video_from_html']} 个")
    print(f"  收集到的视频地址：{len(vurls)} 条（视频一律不下载，见 video_urls.txt）")


if __name__ == "__main__":
    main()
