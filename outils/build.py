"""Fabrique toutes les pages HTML du site a partir de data/.

Usage : python outils/build.py
Les pages sont ecrites a la racine du depot (index.html, products/, collections/, pages/, policies/).
Aucune dependance : Python 3.9+ suffit.
"""
import datetime, hashlib, html, json, re, sys, textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync import local_file, cdn, PRODUCT_W, LOOKBOOK_W, SMALL_W, SMALL  # meme nommage des images que le telechargement

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
PRODUCTS = {}
for _p in json.loads((DATA / "products.json").read_text(encoding="utf-8"))["products"]:
    if _p["images"] and _p["variants"]:
        _p["title"] = _p["title"].title() if _p["title"].isupper() else _p["title"]  # « PANEL DENIM » -> « Panel Denim », comme les autres fiches
        PRODUCTS[_p["handle"]] = _p
    else:
        print(f"ATTENTION produit ignore (sans photo ou sans variante) : {_p['handle']}")
SHOP = "https://" + site["shopify_domain"]
YEAR = datetime.date.today().year
# ?v=empreinte : le navigateur recharge le CSS/JS des qu'ils changent (sinon GitHub Pages les garde 10 min en cache)
VER = {f: hashlib.md5((ROOT / "assets" / f).read_bytes()).hexdigest()[:8] for f in ("css/style.css", "js/site.js")}
CARD_IMAGES = 6  # photos qui defilent dans une carte produit, comme l'original
LOGO_SVG = (ROOT / "assets" / "img" / "logo.svg").read_text(encoding="utf-8").strip()  # logo vectorise (suit la couleur du texte)
esc = html.escape
# attributs repetes (pas de barre oblique inversee dans les f-strings avant Python 3.12)
LAZY, HIGH, CURRENT = ' loading="lazy"', ' fetchpriority="high"', ' aria-current="page"'
FIRST = ' class="gallery__img--first" data-vt'


# ---------- petits outils ----------

def img_path(url, suffix=""):
    """Chemin (depuis la racine) de l'image telechargee par sync.py pour cette URL Shopify."""
    found = local_file(url, suffix)
    if not found:
        raise SystemExit(f"Image manquante : {url}\n-> lance d'abord : python outils/sync.py --images")
    return "assets/img/" + found.name


def srcset(url, big_w, sizes):
    """srcset : version 600 px + grande version (toutes deux telechargees par sync.py), avec sizes."""
    if big_w <= SMALL_W or not local_file(url, SMALL):
        return ""
    return f' srcset="@/{img_path(url, SMALL)} {SMALL_W}w, @/{img_path(url)} {big_w}w" sizes="{sizes}"'


def img_dims(url):
    """' width=".." height=".."' lus dans l'en-tete du WebP telecharge (sans dimensions, l'image fait sauter la page) ; '' si inconnu."""
    b = (ROOT / img_path(url)).read_bytes()[:30]
    if b[:4] != b"RIFF" or b[8:12] != b"WEBP":
        return ""
    kind = b[12:16]
    if kind == b"VP8X":  # largeur-1 et hauteur-1 sur 24 bits
        w, h = 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
    elif kind == b"VP8L":  # 14 bits chacune, moins 1
        bits = int.from_bytes(b[21:25], "little")
        w, h = (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    elif kind == b"VP8 ":
        w, h = int.from_bytes(b[26:28], "little") & 0x3FFF, int.from_bytes(b[28:30], "little") & 0x3FFF
    else:
        return ""
    return f' width="{w}" height="{h}"'


def og_image(url):
    """Adresse absolue de l'image de partage : celle du site s'il a une adresse (version 900 si elle existe), sinon le CDN Shopify."""
    base = site["site_url"].rstrip("/")
    if not base:
        return cdn(url) + ("&" if "?" in cdn(url) else "?") + "width=1200"
    return f"{base}/{img_path(url, '-900') if local_file(url, '-900') else img_path(url)}"


def accent(collection):
    """Couleur d'accent de la collection (data/site.json > collection_accents), sinon rien (noir)."""
    a = site.get("collection_accents", {}).get(collection)
    return f"--accent:{esc(a)}" if a else ""


def money(price):
    c = site["currency"]
    euros, cents = f"{float(price):.2f}".split(".")
    return f"{c['symbol']}{euros}{c['decimal']}{cents}"


def js(obj):
    """JSON sur pour une balise <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def text_of(html_):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_ or ""))).strip()


def available(p):
    return any(v["available"] for v in p["variants"])


def stock_note(p):
    """Etat du stock dit franchement, calcule depuis les variantes ('' = tout est en stock)."""
    left = [v for v in p["variants"] if v["available"]]
    if not left:
        return "Sold out"
    if len(left) == 1 and len(p["variants"]) > 1:
        return f"Only {left[0]['option1']} left"
    return ""


def card_price(p):
    return money(min(float(v["price"]) for v in p["variants"]))


def url_product(h):
    return f"products/{h}.html"


def logo(cls):
    return LOGO_SVG.replace("<svg ", f'<svg class="{cls}" aria-hidden="true" focusable="false" ', 1)


def words(text, start=0):
    """Chaque mot dans un masque : le titre monte mot par mot (--wi = rang du mot)."""
    return " ".join(f'<span class="w"><span style="--wi:{start + i}">{esc(w)}</span></span>' for i, w in enumerate(text.split()))


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def short_name(ch):
    """'CHERRY COLLECTION' -> 'Cherry' ; la collection 'all' -> 'All'."""
    if ch == "all":
        return "All"
    return re.sub(r"\s*collection\s*$", "", content["collections"][ch]["title"], flags=re.I).title()


def collection_of(h):
    for ch, c in content["collections"].items():
        if ch != "all" and h in c["products"]:
            return ch
    return "all"


ARROW_L = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M20 12H4m0 0 6-6m-6 6 6 6" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
ARROW_R = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M4 12h16m0 0-6-6m6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
ARROW = '<svg class="arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16m0 0-6-6m6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'
STAR = '<svg class="star" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2v20M3.3 7l17.4 10M3.3 17 20.7 7" stroke="currentColor" stroke-width="2.6"/></svg>'


# ---------- gabarit commun ----------

def layout(path, title, body, description=None, image=None, head_extra="", body_class="", collection=None):
    """Page complete. `path` = chemin du fichier depuis la racine (ex. 'products/x.html').
    `image` = URL Shopify de l'image de partage (sinon la photo d'ouverture) ; `collection` = sa couleur d'accent."""
    is404 = path == "404.html"
    # liens relatifs (marchent en local et sur GitHub Pages) ; la 404 est servie a n'importe quelle profondeur
    R = site["base_path"] if is404 else "../" * path.count("/")
    full_title = esc(site["name"] if title is None else f"{title} – {site['name']}")
    desc = esc(description or site["description"])
    abs_url = site["site_url"].rstrip("/")
    og_img = (f'\n<meta property="og:image" content="{esc(og_image(image or site["home"]["hero"]["image"]))}">'
              '\n<meta name="twitter:card" content="summary_large_image">')
    style = accent(collection)
    body_attrs = (f' class="{body_class}"' if body_class else "") + (f' style="{style}"' if style else "")
    canon = f'\n<link rel="canonical" href="{abs_url}/{"" if path == "index.html" else path}">' if abs_url and not is404 else ""
    current = lambda href: ' aria-current="page"' if href == path else ""
    menu = "".join(f'<li><a class="menu__link" href="{R}{m["href"]}"{current(m["href"])}><span class="menu__num" aria-hidden="true">{i:02d}</span><span class="menu__label">{esc(m["label"])}</span></a></li>'
                   for i, m in enumerate(site["menu"], start=1))
    foot = "".join(f'<li><a class="link" href="{R}{f["href"]}"{current(f["href"])}>{esc(f["label"])}</a></li>' for f in site["footer"])
    foot_menu = "".join(f'<li><a class="link" href="{R}{m["href"]}"{current(m["href"])}>{esc(m["label"])}</a></li>' for m in site["menu"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">{og_img}{canon}
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="{R}{img_path(site['favicon'])}">
<link rel="preload" href="{R}assets/fonts/archivo-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{R}assets/fonts/geist-mono-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{R}assets/css/style.css?v={VER['css/style.css']}">
<script>document.documentElement.classList.add("js")</script>
<script src="{R}assets/js/site.js?v={VER['js/site.js']}" defer blocking="render"></script>{head_extra}
</head>
<body{body_attrs}>
<a class="skip-link" href="#main">Skip to content</a>
<div class="site-head" data-head>
  <div class="announcement"><p>{esc(site['announcement'])}</p></div>
  <header class="header">
    <div class="header__inner">
      <button class="burger" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="menu"><span class="burger__text">Menu</span></button>
      <nav class="menu" id="menu" aria-label="Main menu">
        <ul class="menu__list">{menu}</ul>
        <div class="menu__foot"><a class="menu__account" href="{SHOP}/account">Account</a><a href="mailto:{esc(site['email'])}">{esc(site['email'])}</a></div>
      </nav>
      <a class="header__logo" href="{R}index.html" aria-label="{esc(site['name'])} – home">{logo("logo")}</a>
      <div class="header__right">
        <a class="header__account link" href="{SHOP}/account">Account</a>
        <a class="header__cart link" href="{R}cart.html" data-cart-open>Cart (<span data-cart-count>0</span>)</a>
      </div>
    </div>
  </header>
</div>
<main id="main">
{body}
</main>
<footer class="footer">
  <div class="footer__grid">
    <nav class="footer__col" aria-label="Shop"><p class="footer__label">Shop</p><ul>{foot_menu}</ul></nav>
    <nav class="footer__col" aria-label="Policies"><p class="footer__label">Legal</p><ul>{foot}</ul></nav>
    <div class="footer__col"><p class="footer__label">Contact</p><ul><li><a class="link" href="mailto:{esc(site['email'])}">{esc(site['email'])}</a></li><li>{esc(site['based'])}</li></ul></div>
    <p class="footer__col footer__note">{esc(site['announcement'])}</p>
  </div>
  <div class="footer__mark" aria-hidden="true"><div class="footer__mark-inner">{logo("logo")}</div></div>
  <p class="footer__copy">&copy; {YEAR}, <a class="link" href="{R}index.html">{esc(site['name'])}</a></p>
</footer>
<dialog class="drawer" id="cart-drawer" aria-labelledby="cart-drawer-title">
  <div class="drawer__head"><h2 id="cart-drawer-title">Cart (0)</h2><button class="drawer__close" type="button" data-cart-close aria-label="Close cart"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M5 5l14 14M19 5 5 19" stroke="currentColor" stroke-width="1.5"/></svg></button></div>
  <div class="drawer__body"><p>Your cart is empty.</p><a class="btn" href="{R}collections/all.html"><span>Shop all</span>{ARROW}</a></div>
</dialog>
<div class="toast" role="status" aria-live="polite"></div>
</body>
</html>
"""


# ---------- morceaux ----------

def card(h, heading="h3", num=None, sizes="(max-width: 899px) 50vw, 25vw"):
    """Carte produit : jusqu'a 6 photos qui defilent (fleches au survol sur ordinateur, glisser au doigt sur mobile)."""
    p = PRODUCTS[h]
    name = esc(p["title"])
    ims = p["images"][:CARD_IMAGES]
    # 1re photo chargee tout de suite (dans une piste horizontale, le chargement differe ne part qu'a l'ecran)
    imgs = "".join(
        f'<img src="@/{img_path(im["src"])}"{srcset(im["src"], min(PRODUCT_W, im["width"]), sizes)} alt="" width="{im["width"]}" height="{im["height"]}"'
        f'{LAZY if i else ""} decoding="async" draggable="false">'
        for i, im in enumerate(ims))
    arrows = (f'<button type="button" class="card__arrow card__arrow--prev" data-card-prev aria-label="Previous photo of {name}">{ARROW_L}</button>'
              f'<button type="button" class="card__arrow card__arrow--next" data-card-next aria-label="Next photo of {name}">{ARROW_R}</button>'
              f'<span class="card__dots" aria-hidden="true">{"<i></i>" * len(ims)}</span>') if len(ims) > 1 else ""
    note = stock_note(p)
    tag = f'<span class="card__tag">{esc(note)}</span>' if note else ""
    number = f'<span class="card__num" aria-hidden="true">{num:02d}</span>' if num else ""
    return f"""<article class="card{' is-sold-out' if not available(p) else ''}" data-reveal>
  <div class="card__media">{number}{tag}<a class="card__track" href="@/{url_product(h)}" tabindex="-1" aria-hidden="true" data-card-track>{imgs}</a>{arrows}</div>
  <div class="card__info">
    <{heading} class="card__name"><a href="@/{url_product(h)}">{name}</a></{heading}>
    <p class="card__price">{card_price(p)}</p>
  </div>
</article>"""


def card_sizes(kind, n, i):
    """Largeur affichee d'une carte (attribut sizes), selon la grille ; doit suivre les regles .grid* de style.css."""
    if kind == "featured":
        return "(max-width: 899px) 50vw, 36vw"
    if kind == "page" and n == 1:
        return "(max-width: 899px) 100vw, 32vw"
    if kind == "page" and n == 2:
        return "(max-width: 899px) 50vw, 32vw"
    if kind == "page" and n == 5:
        return ("(max-width: 899px) 100vw" if i == 1 else "(max-width: 899px) 50vw") + ", (max-width: 1199px) 31vw, 19vw"
    return "(max-width: 899px) 50vw, 25vw"


def grid(handles, extra_class="", heading="h3"):
    hs = [h for h in handles if h in PRODUCTS]
    kind = extra_class.rsplit("--", 1)[-1]
    cards = [card(h, heading, i, card_sizes(kind, len(hs), i)) for i, h in enumerate(hs, start=1)]
    return f'<div class="grid {extra_class}" data-count="{len(hs)}">\n' + "\n".join(cards) + "\n</div>"


def collection_nav(current):
    links = []
    for ch, c in content["collections"].items():
        n = len([h for h in c["products"] if h in PRODUCTS])
        href = f"collections/{ch}.html"
        on = ' aria-current="page"' if href == current else (' class="is-active"' if current == "pages/catalog.html" and ch == "all" else "")
        links.append(f'<li><a href="@/{href}"{on}>{esc(short_name(ch))}<span class="filters__n">{n}</span></a></li>')
    return f'<nav class="filters" aria-label="Collections"><ul>{"".join(links)}</ul></nav>'


def page_head(title, crumbs, count=None, tag="h1", big=True):
    """En-tete de page ; big=False : titre sobre (pages utilitaires), sans le condense en capitales."""
    meta = f'<p class="page-head__count">{plural(count, "product")}</p>' if count is not None else ""
    cls = "page-head__title display" if big else "page-head__title title"
    return f"""<header class="page-head">
  <p class="page-head__crumbs">{crumbs}</p>
  <{tag} class="{cls}" data-split>{words(title)}</{tag}>
  {meta}
</header>"""


# ---------- pages ----------

def page_home():
    hm = site["home"]
    hero, col, sa, lb, nl = hm["hero"], content["collections"][hm["featured_collection"]], hm["shop_all"], hm["lookbook"], hm["newsletter"]
    feat = [h for h in col["products"] if h in PRODUCTS]
    k, lines = 0, []
    for line in hero.get("lines") or [hero["title"]]:
        lines.append(f'<span class="line">{words(line, k)}</span>')
        k += len(line.split())
    # index numerote des pieces de la collection : chaque ligne mene a sa fiche
    index = "".join(
        f'<li><a href="@/{url_product(h)}"><span class="hero__num">{i:02d}</span><span class="hero__name">{esc(PRODUCTS[h]["title"])}</span>'
        f'<span class="hero__price">{card_price(PRODUCTS[h])}</span></a></li>'
        for i, h in enumerate(feat, start=1))
    # petite version pour les telephones (+ prechargement : c'est l'image la plus grande de l'ouverture)
    big = f'@/{img_path(hero["image"])}'
    small = local_file(hero["image"], "-900")
    sizes = "(max-width: 899px) 100vw, 42vw"
    set_ = f'@/{img_path(hero["image"], "-900")} 900w, @/{img_path(hero["image"], "-1400")} 1400w, {big} 2400w' if small else ""
    srcset_attr = f' srcset="{set_}" sizes="{sizes}"' if small else ""
    preload = f'\n<link rel="preload" as="image" href="{big}"' + (f' imagesrcset="{set_}" imagesizes="{sizes}"' if small else "") + ' fetchpriority="high">'
    n_lb = len(lb["images"])
    slides = "".join(
        f'<li class="lookbook__item" data-reveal="curtain"><figure><div class="lookbook__frame"><img src="@/{img_path(u)}"{srcset(u, LOOKBOOK_W, "(max-width: 899px) 74vw, 30vw")} alt="{esc(lb["title"])} – photo {i + 1}" width="900" height="1350" loading="lazy" decoding="async" draggable="false"></div>'
        f'<figcaption>{i + 1:02d} / {n_lb:02d}</figcaption></figure></li>'
        for i, u in enumerate(lb["images"]))
    ticker = "".join(f"<li>{esc(t)}{STAR}</li>" for t in site["ticker"])
    n_all = len([h for h in content["collections"]["all"]["products"] if h in PRODUCTS])
    body = f"""<section class="hero" aria-labelledby="hero-title">
  <div class="hero__text">
    <p class="hero__kicker"><span>{esc(hero['kicker'])}</span></p>
    <h1 class="hero__title display" id="hero-title" data-split>{''.join(lines)}</h1>
    <div class="hero__foot">
      <ol class="hero__index" aria-label="{esc(col['title'].title())}">{index}</ol>
      <a class="btn" href="@/{hero['link']}"><span>{esc(hero['button'])}</span>{ARROW}</a>
    </div>
  </div>
  <div class="hero__media">
    <a class="hero__frame" href="@/{hero['link']}" tabindex="-1" aria-hidden="true"><div class="hero__zoom"><img class="hero__img" src="{big}"{srcset_attr} alt="{esc(hero.get('alt', ''))}" width="2400" height="3600" fetchpriority="high"></div></a>
  </div>
</section>
<section class="ticker" aria-label="About the clothes" data-ticker>
  <div class="ticker__track"><ul class="ticker__group">{ticker}</ul><ul class="ticker__group" aria-hidden="true">{ticker}</ul></div>
  <button class="ticker__toggle" type="button" aria-pressed="false" data-ticker-toggle>Pause</button>
</section>
<section class="section featured" aria-labelledby="featured-title">
  <div class="section__head">
    <p class="section__num" aria-hidden="true">(01)</p>
    <h2 class="section__title display" id="featured-title" data-split>{words(col['title'].title())}</h2>
    <p class="section__meta">{plural(len(feat), "piece")}</p>
  </div>
  <div class="featured__body">
    <div class="featured__aside" data-reveal>
      <p class="featured__text">{esc(hm['featured_text'])}</p>
      <a class="link link--arrow" href="@/collections/{hm['featured_collection']}.html">View collection {ARROW}</a>
    </div>
    {grid(feat, "grid--featured")}
  </div>
</section>
{closeups(hm.get("details"))}
<section class="section shop-all" aria-label="{esc(sa['title'])}">
  <a class="shop-all__link" href="@/{sa['link']}">
    <span class="section__num" aria-hidden="true">(03)</span>
    <span class="shop-all__title display"><span class="roll" data-text="{esc(sa['button'])}"><span>{esc(sa['button'])}</span></span></span>
    <span class="shop-all__meta"><span>{esc(sa['title'])}</span><span>{n_all}</span></span>
    <span class="shop-all__arrow">{ARROW}</span>
  </a>
</section>
<section class="lookbook" aria-labelledby="lookbook-title" data-lookbook-section>
  <a class="skip-inline" href="#newsletter">Skip lookbook</a>
  <div class="lookbook__pin">
    <div class="lookbook__rail" data-lookbook-rail>
      <div class="lookbook__head">
        <p class="section__num" aria-hidden="true">(04)</p>
        <h2 class="lookbook__title display" id="lookbook-title" data-split>{words(lb['heading'])}</h2>
        <p class="lookbook__sub">{esc(lb['title'])}<br>{n_lb} photos</p>
      </div>
      <ul class="lookbook__track" data-lookbook tabindex="0" aria-label="Lookbook photos, scroll sideways">{slides}</ul>
      <a class="lookbook__end" href="@/{hero['link']}"><span class="display">{esc(lb['end'])}</span>{ARROW}</a>
    </div>
    <div class="lookbook__bar" aria-hidden="true"><span data-lookbook-thumb></span></div>
  </div>
</section>
{newsletter(nl)}"""
    return layout("index.html", None, body, image=hero["image"], head_extra=preload, body_class="is-home", collection=hm["featured_collection"])


def closeups(dt):
    """Section « The details » : gros plans tires des photos produits, legendes = details reels (data/content.json)."""
    if not dt:
        return ""
    items = []
    for it in dt["items"]:
        p = PRODUCTS.get(it["product"])
        im = next((x for x in p["images"] if x["src"] == it["image"]), None) if p else None
        if not im or it["detail"] not in content["products"].get(it["product"], {}).get("details", []):
            print(f"ATTENTION site.json home.details : photo ou detail introuvable pour {it['product']} ({it['detail']}) -> gros plan ignore")
            continue
        k = len(items) + 1
        sizes = f"(max-width: 899px) {'100vw' if k == 1 else '50vw'}, 31vw"
        items.append(
            f'<li class="closeups__item" data-reveal="curtain"><a href="@/{url_product(it["product"])}"><figure>'
            f'<div class="closeups__frame"><img src="@/{img_path(im["src"])}"{srcset(im["src"], min(PRODUCT_W, im["width"]), sizes)} alt="{esc(p["title"])} – {esc(it["detail"].lower())}" width="{im["width"]}" height="{im["height"]}" loading="lazy" decoding="async"></div>'
            f'<figcaption><span class="closeups__num">{k:02d}</span><span class="closeups__detail">{esc(it["detail"])}</span><span class="closeups__product">{esc(p["title"])}</span></figcaption>'
            f'</figure></a></li>')
    if not items:
        return ""
    return f"""<section class="section closeups" aria-labelledby="closeups-title">
  <div class="section__head">
    <p class="section__num" aria-hidden="true">(02)</p>
    <h2 class="section__title display" id="closeups-title" data-split>{words(dt['title'])}</h2>
    <p class="section__meta">{plural(len(items), "detail")}</p>
  </div>
  <ul class="closeups__grid">{"".join(items)}</ul>
</section>"""


def newsletter(nl):
    # Inscription envoyee a la liste clients de la boutique Shopify (meme formulaire que l'original).
    return f"""<section class="section newsletter" id="newsletter" aria-labelledby="newsletter-title">
  <p class="section__num" aria-hidden="true">(05)</p>
  <h2 class="newsletter__title display" id="newsletter-title" data-split>{words(nl['title'])}</h2>
  <div class="newsletter__side" data-reveal>
    <p class="newsletter__text">{esc(nl['text'])}</p>
    <form class="newsletter__form" method="post" action="{SHOP}/contact#contact_form" accept-charset="UTF-8">
      <input type="hidden" name="form_type" value="customer">
      <input type="hidden" name="utf8" value="✓">
      <input type="hidden" name="contact[tags]" value="newsletter">
      <label class="visually-hidden" for="newsletter-email">Your email</label>
      <input id="newsletter-email" type="email" name="contact[email]" placeholder="Your email" autocomplete="email" required>
      <button type="submit"><span>Subscribe</span>{ARROW}</button>
    </form>
  </div>
</section>"""


def page_listing(path, title, handles, label, collection=None):
    hs = [h for h in handles if h in PRODUCTS]
    crumbs = f'<a class="link" href="@/pages/catalog.html">Shop</a><span aria-hidden="true">/</span><span>{esc(label)}</span>'
    # data-count : 2 produits = titre collant a gauche + 2 grandes tuiles a droite (voir .listing[data-count="2"])
    body = f"""<div class="listing" data-count="{len(hs)}">
<div class="listing__head">
{page_head(title, crumbs, len(hs))}
{collection_nav(path)}
</div>
{grid(hs, "grid--page", heading="h2")}
</div>"""
    image = PRODUCTS[hs[0]]["images"][0]["src"] if hs else None
    return layout(path, title, body, image=image, collection=collection)


def page_collection(h):
    c = content["collections"][h]
    return page_listing(f"collections/{h}.html", c["title"].title() if c["title"].isupper() else c["title"], c["products"], short_name(h), collection=h)


def page_catalog():
    return page_listing("pages/catalog.html", "Catalog", content["collections"]["all"]["products"], "All")


def page_product(h):
    p = PRODUCTS[h]
    extra = content["products"].get(h, {})
    title = esc(p["title"])
    n = len(p["images"])
    # ordinateur : 2 photos 3:4 par rangee, comme les cartes ; telephone : une photo par ecran
    imgs = "".join(
        f'<li class="gallery__item"><img{FIRST if i == 0 else ""} src="@/{img_path(im["src"])}"{srcset(im["src"], min(PRODUCT_W, im["width"]), "(max-width: 899px) 100vw, 31vw")}'
        f' alt="{title} – image {i + 1} of {n}" width="{im["width"]}" height="{im["height"]}"'
        f'{HIGH if i == 0 else LAZY} decoding="async" draggable="false"></li>'
        for i, im in enumerate(p["images"]))
    nav = f"""<div class="gallery__nav">
      <button type="button" class="gallery__arrow" data-prev aria-label="Previous image">{ARROW_L}</button>
      <p class="gallery__count"><span data-gallery-index>1</span> / {n}</p>
      <button type="button" class="gallery__arrow" data-next aria-label="Next image">{ARROW_R}</button>
    </div>""" if n > 1 else ""

    # options (taille, couleur...) : un groupe de boutons radio par option
    first = next((v for v in p["variants"] if v["available"]), p["variants"][0])
    guide_link = '<a class="link" href="#size-guide" data-open-guide>Size guide</a>' if extra.get("size_guide") else ""
    groups = []
    for k, opt in enumerate(p["options"], start=1):
        radios = "".join(
            f'<label class="option"><input type="radio" name="option{k}" value="{esc(val)}"{" checked" if first[f"option{k}"] == val else ""}><span>{esc(val)}</span></label>'
            for val in opt["values"])
        hide = " hidden" if opt["values"] == ["Default Title"] else ""  # produit sans taille
        name = opt["name"].title()
        side = guide_link if k == 1 else ""
        groups.append(f'<fieldset class="options"{hide}><legend class="options__legend"><span>{esc(name)}</span></legend>{side}<div class="options__list">{radios}</div></fieldset>')
    variants = [{"id": v["id"], "options": [v.get(f"option{k}") for k in range(1, len(p["options"]) + 1)],
                 "available": v["available"], "price": money(v["price"])} for v in p["variants"]]
    label = f"Add to cart — {money(first['price'])}" if first["available"] else "Sold out"
    note = stock_note(p) or "In stock"

    acc = []
    if extra.get("details"):
        acc.append(("Product Details", "", '<ul class="details">' + "".join(f"<li>{esc(d)}</li>" for d in extra["details"]) + "</ul>"))
    if extra.get("size_guide"):
        acc.append(("Size Guide", ' id="size-guide"', f'<img src="@/{img_path(extra["size_guide"])}"{img_dims(extra["size_guide"])} alt="{title} size chart (measurements per size)" loading="lazy">'))
    acc.append(("Shipping", "", site["shipping_html"]))
    accordion = "".join(f'<details class="accordion__item"{i}><summary>{t}</summary><div class="accordion__content rte">{c}</div></details>' for t, i, c in acc)

    related_html = related_section("Related", [r for r in extra.get("related", []) if r != h])

    ch = collection_of(h)
    crumbs = (f'<a class="link" href="@/pages/catalog.html">Shop</a><span aria-hidden="true">/</span>'
              f'<a class="link" href="@/collections/{ch}.html">{esc(short_name(ch))}</a>')

    desc_text = text_of(p["body_html"])
    ld = {"@context": "https://schema.org", "@type": "Product", "name": p["title"], "description": desc_text,
          "brand": {"@type": "Brand", "name": site["name"]}, "sku": first.get("sku") or None,
          "offers": [{"@type": "Offer", "price": v["price"], "priceCurrency": site["currency"]["code"],
                      "availability": "https://schema.org/" + ("InStock" if v["available"] else "OutOfStock"), "sku": v.get("sku")} for v in p["variants"]]}
    if site["site_url"]:
        ld["image"] = [f'{site["site_url"].rstrip("/")}/{img_path(im["src"])}' for im in p["images"]]
    head = f'\n<script type="application/ld+json">{js(ld)}</script>'

    # ordre du code = ordre de lecture mobile (photos, titre, achat, infos) ; la grille CSS place les photos a gauche sur ordinateur
    body = f"""<div class="product">
  <div class="product__gallery gallery" data-gallery role="region" aria-roledescription="carousel" aria-label="{title} photos">
    <ul class="gallery__track" data-gallery-track>{imgs}</ul>
    {nav}
  </div>
  <div class="product__panel">
    <div class="product__sticky">
      <p class="product__crumbs">{crumbs}</p>
      <h1 class="product__title" data-split>{words(p['title'])}</h1>
      <p class="product__price"><span>{money(first['price'])}</span><span class="product__stock{' is-out' if not available(p) else ''}">{esc(note)}</span></p>
      <div class="product__desc rte">{p['body_html']}</div>
      <form class="buy" data-buy onsubmit="return false">
        {''.join(groups)}
        <button type="button" class="btn btn--block buy__button" data-add-to-cart data-variant-id="{first['id']}"{"" if first["available"] else " disabled"}>{label}</button>
        <script type="application/json" data-variants>{js(variants)}</script>
      </form>
      <div class="accordion">{accordion}</div>
    </div>
  </div>
</div>
{related_html}"""
    return layout(url_product(h), p["title"], body, description=textwrap.shorten(desc_text, 160, placeholder="…") or None,
                  image=p["images"][0]["src"], head_extra=head, body_class="is-product", collection=ch)


def related_section(title, handles, kind="grid--related"):
    """Bandeau titre + nombre, puis grille de cartes (produits lies d'une fiche, produits du guide des tailles)."""
    hs = [h for h in handles if h in PRODUCTS]
    return f"""<section class="section related" aria-labelledby="related-title">
  <div class="related__head">
    <h2 class="related__title" id="related-title">{esc(title)}</h2>
    <p class="section__meta">{plural(len(hs), "piece")}</p>
  </div>
  {grid(hs, kind)}
</section>""" if hs else ""


def page_contact():
    # meme gabarit que les pages de texte ; la ligne d'envoi = 1er paragraphe de data/site.json > shipping_html
    inner = f"""<div class="contact-page__info" data-reveal>
    <p class="field-label">Email</p>
    <p><a class="link" href="mailto:{esc(site['email'])}">{esc(site['email'])}</a></p>
    <p class="field-label">Shipping</p>
    <p>{esc(text_of(site['shipping_html'].split('</p>')[0]))}</p>
  </div>
  <form class="contact" method="post" action="{SHOP}/contact#contact_form" accept-charset="UTF-8" data-reveal>
    <input type="hidden" name="form_type" value="contact">
    <input type="hidden" name="utf8" value="✓">
    <div class="field"><label class="field-label" for="c-name">Name</label><input id="c-name" type="text" name="contact[name]" autocomplete="name" required></div>
    <div class="field"><label class="field-label" for="c-phone">Phone number</label><input id="c-phone" type="tel" name="contact[phone]" autocomplete="tel"></div>
    <div class="field"><label class="field-label" for="c-email">Email</label><input id="c-email" type="email" name="contact[email]" autocomplete="email" required></div>
    <div class="field"><label class="field-label" for="c-message">Message</label><textarea id="c-message" name="contact[body]" rows="6" required></textarea></div>
    <button class="btn btn--block" type="submit"><span>Send</span>{ARROW}</button>
  </form>"""
    return page_simple("pages/contact.html", "Contact", inner, cls="contact-page__body", kicker="Get in touch", description=f"Contact {site['name']}: {site['email']}")


def page_simple(path, title, inner, cls="rte page-content", after="", kicker="Info", description=None, aside=""):
    body = f"""<div class="text-page">
  <header class="text-page__head">
    <div class="text-page__sticky">
      <p class="text-page__kicker">{esc(kicker)}</p>
      <h1 class="text-page__title title" data-split>{words(title)}</h1>
      {aside}
    </div>
  </header>
  <div class="text-page__body {cls}">{inner}</div>
</div>
{after}"""
    return layout(path, title, body, description=description)


def policy_index(path):
    items = "".join(f'<li><a class="link" href="@/{f["href"]}"{CURRENT if f["href"] == path else ""}>{esc(f["label"])}</a></li>' for f in site["footer"])
    return f'<nav class="text-page__index" aria-label="All policies"><ul>{items}</ul></nav>'


def page_cart():
    body = f"""<div class="cart-page">
  <h1 class="cart-page__title title" data-split>{words("Your cart")}</h1>
  <p>Your cart is empty.</p>
  <a class="btn" href="@/collections/all.html"><span>Shop all</span>{ARROW}</a>
</div>"""
    return layout("cart.html", "Your Shopping Cart", body)


def page_404():
    body = f"""<div class="not-found">
  <h1><span class="not-found__code display">404</span><span class="not-found__text">Page no longer exists</span></h1>
  <a class="btn" href="@/collections/all.html"><span>Shop all</span>{ARROW}</a>
</div>"""
    return layout("404.html", "404 Not Found", body)


# ---------- controles ----------

def check_content():
    """Previent quand data/content.json n'est plus a jour apres un sync (rien n'est ajoute tout seul)."""
    listed = set(content["collections"]["all"]["products"])
    for h in PRODUCTS:
        if h not in listed:
            print(f"ATTENTION nouveau produit absent du catalogue : {h} -> l'ajouter dans data/content.json (collections > all)")
        if h not in content["products"]:
            print(f"ATTENTION pas de details pour {h} -> ajouter une entree dans data/content.json (products)")
    for ch, c in content["collections"].items():
        for h in c["products"]:
            if h not in PRODUCTS:
                print(f"ATTENTION collection {ch} : produit inconnu ou ignore '{h}'")
    for h, extra in content["products"].items():
        for r in extra.get("related", []):
            if r not in PRODUCTS:
                print(f"ATTENTION produits lies de {h} : produit inconnu '{r}'")


# ---------- ecriture ----------

def build():
    check_content()
    pages = {"index.html": page_home(), "pages/catalog.html": page_catalog(), "pages/contact.html": page_contact(),
             "cart.html": page_cart(), "404.html": page_404()}
    for h in content["collections"]:
        pages[f"collections/{h}.html"] = page_collection(h)
    for h in PRODUCTS:
        pages[url_product(h)] = page_product(h)
    for h, pg in content["pages"].items():
        html_ = re.sub(r'src="([^"]+)"', lambda m: f'src="@/{img_path(m.group(1))}"{img_dims(m.group(1))} loading="lazy"', pg["html"])
        col = content["collections"].get(pg.get("products"))
        after = related_section(col["title"], col["products"], "grid--page") if col else ""
        pages[f"pages/{h}.html"] = page_simple(f"pages/{h}.html", pg["title"], html_, after=after, kicker="Guide", description=pg.get("description"))
    for f in sorted((DATA / "policies").glob("*.html")):
        raw = f.read_text(encoding="utf-8")
        title = re.match(r"<!--\s*(.*?)\s*-->", raw).group(1)
        body = re.sub(r"^<!--.*?-->\s*", "", raw)
        body = re.sub(r"(?:<br\s*/?>\s*){2,}", "</p><p>", body)  # double saut de ligne = nouveau paragraphe : un seul rythme (toujours dans un <p> ici)
        path = f"policies/{f.stem}.html"
        pages[path] = page_simple(path, title, body, "rte policy", kicker="Legal", aside=policy_index(path),
                                  description=textwrap.shorten(text_of(body), 160, placeholder="…"))

    # products/ et collections/ sont 100 % fabriques : on retire les pages d'un produit ou d'une collection disparus
    for folder in ("products", "collections"):
        for old in (ROOT / folder).glob("*.html"):
            if f"{folder}/{old.name}" not in pages:
                old.unlink()
                print(f"page retiree : {folder}/{old.name}")

    for path, text in pages.items():
        out = ROOT / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(layout_fix(path, text), encoding="utf-8", newline="\n")

    if site["site_url"]:
        base = site["site_url"].rstrip("/")
        urls = "".join(f"<url><loc>{base}/{'' if p == 'index.html' else p}</loc></url>\n" for p in pages if p not in ("404.html", "cart.html"))
        (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n', encoding="utf-8")
        (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(pages)} pages ecrites")


def layout_fix(path, text):
    """Les liens '@/...' deviennent relatifs a la page (la 404 utilise base_path)."""
    R = site["base_path"] if path == "404.html" else "../" * path.count("/")
    return text.replace('"@/', f'"{R}').replace(' @/', f' {R}')


if __name__ == "__main__":
    build()
