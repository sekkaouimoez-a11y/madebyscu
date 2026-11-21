"""Fabrique toutes les pages HTML du site a partir de data/.

Usage : python outils/build.py
Les pages sont ecrites a la racine du depot (index.html, products/, collections/, pages/, policies/).
Aucune dependance : Python 3.9+ suffit.
"""
import datetime, hashlib, html, json, re, sys, textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync import IMG, local_file  # meme nommage des images que le telechargement

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
PRODUCTS = {}
for _p in json.loads((DATA / "products.json").read_text(encoding="utf-8"))["products"]:
    if _p["images"] and _p["variants"]:
        PRODUCTS[_p["handle"]] = _p
    else:
        print(f"ATTENTION produit ignore (sans photo ou sans variante) : {_p['handle']}")
SHOP = "https://" + site["shopify_domain"]
YEAR = datetime.date.today().year
# ?v=empreinte : le navigateur recharge le CSS/JS des qu'ils changent (sinon GitHub Pages les garde 10 min en cache)
VER = {f: hashlib.md5((ROOT / "assets" / f).read_bytes()).hexdigest()[:8] for f in ("css/style.css", "js/site.js")}
CARD_IMAGES = 6  # photos qui defilent dans une carte produit, comme l'original
esc = html.escape


# ---------- petits outils ----------

def img_path(url, suffix=""):
    """Chemin (depuis la racine) de l'image telechargee par sync.py pour cette URL Shopify."""
    found = local_file(url, suffix)
    if not found:
        raise SystemExit(f"Image manquante : {url}\n-> lance d'abord : python outils/sync.py --images")
    return "assets/img/" + found.name


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


def card_price(p):
    price = min(float(v["price"]) for v in p["variants"])
    text = f"{money(price)} {site['currency']['code']}"
    return text if available(p) else text + " — Sold out"


def url_product(h):
    return f"products/{h}.html"


ARROW_L = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M20 12H4m0 0 6-6m-6 6 6 6" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
ARROW_R = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M4 12h16m0 0-6-6m6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'


# ---------- gabarit commun ----------

def layout(path, title, body, description=None, image=None, head_extra=""):
    """Page complete. `path` = chemin du fichier depuis la racine (ex. 'products/x.html')."""
    is404 = path == "404.html"
    # liens relatifs (marchent en local et sur GitHub Pages) ; la 404 est servie a n'importe quelle profondeur
    R = site["base_path"] if is404 else "../" * path.count("/")
    full_title = esc(site["name"] if title is None else f"{title} – {site['name']}")
    desc = esc(description or site["description"])
    abs_url = site["site_url"].rstrip("/")
    og_img = f'\n<meta property="og:image" content="{abs_url}/{image}">' if abs_url and image else ""
    canon = f'\n<link rel="canonical" href="{abs_url}/{"" if path == "index.html" else path}">' if abs_url and not is404 else ""
    current = lambda href: ' aria-current="page"' if href == path else ""
    menu = "".join(f'<a class="menu__link" href="{R}{m["href"]}"{current(m["href"])}>{esc(m["label"])}</a>' for m in site["menu"])
    foot = "".join(f'<a href="{R}{f["href"]}"{current(f["href"])}>{esc(f["label"])}</a>' for f in site["footer"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">{og_img}{canon}
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="{R}{img_path(site['favicon'])}">
<link rel="preload" href="{R}assets/fonts/archivo-narrow-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{R}assets/css/style.css?v={VER['css/style.css']}">
<script src="{R}assets/js/site.js?v={VER['js/site.js']}" defer></script>{head_extra}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div class="announcement"><p>{esc(site['announcement'])}</p></div>
<header class="header">
  <div class="header__inner page-width">
    <button class="burger" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="menu"><span></span><span></span></button>
    <nav class="menu" id="menu" aria-label="Main menu">
      {menu}
      <a class="menu__link menu__account" href="{SHOP}/account">Account</a>
    </nav>
    <a class="header__logo" href="{R}index.html"><img src="{R}{img_path(site['logo'])}" alt="{esc(site['name'])}" width="105" height="105"></a>
    <div class="header__right">
      <a class="header__account" href="{SHOP}/account">Account</a>
      <a class="header__cart" href="{R}cart.html" data-cart-open>Cart (<span data-cart-count>0</span>)</a>
    </div>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="footer">
  <nav class="footer__nav page-width" aria-label="Policies">{foot}</nav>
  <p class="footer__copy">&copy; {YEAR}, <a href="{R}index.html">{esc(site['name'])}</a></p>
</footer>
<dialog class="drawer" id="cart-drawer" aria-labelledby="cart-drawer-title">
  <div class="drawer__head"><h2 id="cart-drawer-title">Your Cart</h2><button class="drawer__close" type="button" data-cart-close aria-label="Close cart">&times;</button></div>
  <div class="drawer__body"><p>Your cart is empty.</p></div>
</dialog>
<div class="toast" role="status" aria-live="polite"></div>
</body>
</html>
"""


# ---------- morceaux ----------

def card(h, heading="h3"):
    """Carte produit : jusqu'a 6 photos qui defilent (fleches au survol sur ordinateur, glisser au doigt sur mobile)."""
    p = PRODUCTS[h]
    name = esc(p["title"])
    # 1re photo chargee tout de suite (dans une piste horizontale, le chargement differe ne part qu'a l'ecran)
    lazy_attr = ' loading="lazy"'
    imgs = "".join(
        f'<img src="@/{img_path(im["src"])}" alt="" width="{im["width"]}" height="{im["height"]}"'
        f'{lazy_attr if i else ""} decoding="async" draggable="false">'
        for i, im in enumerate(p["images"][:CARD_IMAGES]))
    arrows = (f'<button type="button" class="card__arrow card__arrow--prev" data-card-prev aria-label="Previous photo of {name}">{ARROW_L}</button>'
              f'<button type="button" class="card__arrow card__arrow--next" data-card-next aria-label="Next photo of {name}">{ARROW_R}</button>'
              ) if len(p["images"]) > 1 else ""
    return f"""<article class="card">
  <div class="card__media"><a class="card__track" href="@/{url_product(h)}" tabindex="-1" aria-hidden="true" data-card-track>{imgs}</a>{arrows}</div>
  <{heading} class="card__name"><a href="@/{url_product(h)}">{name}</a></{heading}>
  <p class="card__price">{card_price(p)}</p>
</article>"""


def grid(handles, extra_class="", heading="h3"):
    cards = [card(h, heading) for h in handles if h in PRODUCTS]
    return f'<div class="grid {extra_class}">\n' + "\n".join(cards) + "\n</div>"


# ---------- pages ----------

def page_home():
    hm = site["home"]
    hero, col, sa, lb, nl = hm["hero"], content["collections"][hm["featured_collection"]], hm["shop_all"], hm["lookbook"], hm["newsletter"]
    slides = "".join(f'<li class="lookbook__item"><img src="@/{img_path(u)}" alt="{esc(lb["title"])} – photo {i + 1}" loading="lazy" decoding="async" draggable="false"></li>' for i, u in enumerate(lb["images"]))
    # petite version pour les telephones (l'image remplit 75 % de la hauteur, recadree)
    small = local_file(hero["image"], "-900")
    srcset = f' srcset="@/{img_path(hero["image"], "-900")} 900w, @/{img_path(hero["image"])} 2400w" sizes="(max-width: 749px) 422px, 100vw"' if small else ""
    body = f"""<section class="hero">
  <img class="hero__img" src="@/{img_path(hero['image'])}"{srcset} alt="" fetchpriority="high">
  <div class="hero__content">
    <h1 class="hero__title">{esc(hero['title'])}</h1>
    <a class="btn" href="@/{hero['link']}">{esc(hero['button'])}</a>
  </div>
</section>
<section class="featured page-width" aria-labelledby="featured-title">
  <h2 class="section-title" id="featured-title">{esc(col['title'])}</h2>
  {grid(col['products'])}
</section>
<section class="shop-all page-width">
  <h2 class="shop-all__title">{esc(sa['title'])}</h2>
  <a class="btn" href="@/{sa['link']}">{esc(sa['button'])}</a>
</section>
<section class="lookbook" aria-labelledby="lookbook-title">
  <h2 class="lookbook__title page-width" id="lookbook-title">{esc(lb['title'])}</h2>
  <ul class="lookbook__track" data-lookbook tabindex="0" aria-label="Lookbook photos, scroll sideways">{slides}</ul>
  <div class="lookbook__bar" aria-hidden="true"><span data-lookbook-thumb></span></div>
</section>
{newsletter(nl)}"""
    return layout("index.html", None, body, image=img_path(hero["image"]))


def newsletter(nl):
    # Inscription envoyee a la liste clients de la boutique Shopify (meme formulaire que l'original).
    return f"""<section class="newsletter page-width" aria-labelledby="newsletter-title">
  <h2 class="newsletter__title" id="newsletter-title">{esc(nl['title'])}</h2>
  <p class="newsletter__text">{esc(nl['text'])}</p>
  <form class="newsletter__form" method="post" action="{SHOP}/contact#contact_form" accept-charset="UTF-8">
    <input type="hidden" name="form_type" value="customer">
    <input type="hidden" name="utf8" value="✓">
    <input type="hidden" name="contact[tags]" value="newsletter">
    <label class="visually-hidden" for="newsletter-email">Your email</label>
    <input id="newsletter-email" type="email" name="contact[email]" placeholder="Your Email" autocomplete="email" required>
    <button type="submit">Subscribe</button>
  </form>
</section>"""


def page_collection(h):
    c = content["collections"][h]
    body = f'<div class="page-width collection">\n<h1 class="visually-hidden">{esc(c["title"])}</h1>\n{grid(c["products"], heading="h2")}\n</div>'
    return layout(f"collections/{h}.html", c["title"], body)


def page_catalog():
    body = f'<div class="page-width catalog">\n<h1 class="page-title">Catalog</h1>\n{grid(content["collections"]["all"]["products"], heading="h2")}\n</div>'
    return layout("pages/catalog.html", "Catalog", body)


def page_product(h):
    p = PRODUCTS[h]
    extra = content["products"].get(h, {})
    title = esc(p["title"])
    n = len(p["images"])
    imgs = "".join(
        f'<img class="{"is-active" if i == 0 else ""}" {"src" if i == 0 else "data-src"}="@/{img_path(im["src"])}" alt="{title} – image {i + 1} of {n}" width="{im["width"]}" height="{im["height"]}" draggable="false"{"" if i == 0 else " hidden"}>'
        for i, im in enumerate(p["images"]))
    # cadre mobile a la proportion de la photo la plus haute (sur ordinateur : 3:4)
    tallest = min(p["images"], key=lambda im: im["width"] / im["height"])
    cur = ' aria-current="true"'
    dots = "".join(f'<button type="button" class="gallery__dot" aria-label="Show image {i + 1}"{cur if i == 0 else ""}></button>' for i in range(n))
    nav = f"""<div class="gallery__nav">
      <button type="button" class="gallery__arrow" data-prev aria-label="Previous image">{ARROW_L}</button>
      <div class="gallery__dots">{dots}</div>
      <button type="button" class="gallery__arrow" data-next aria-label="Next image">{ARROW_R}</button>
    </div>""" if n > 1 else ""

    # options (taille, couleur...) : un groupe de boutons radio par option
    first = next((v for v in p["variants"] if v["available"]), p["variants"][0])
    groups = []
    for k, opt in enumerate(p["options"], start=1):
        radios = "".join(
            f'<label class="option"><input type="radio" name="option{k}" value="{esc(val)}"{" checked" if first[f"option{k}"] == val else ""}><span>{esc(val)}</span></label>'
            for val in opt["values"])
        hide = " hidden" if opt["values"] == ["Default Title"] else ""  # produit sans taille
        groups.append(f'<fieldset class="options"{hide}><legend class="visually-hidden">{esc(opt["name"].title())}</legend>{radios}</fieldset>')
    variants = [{"id": v["id"], "options": [v.get(f"option{k}") for k in range(1, len(p["options"]) + 1)],
                 "available": v["available"], "price": money(v["price"])} for v in p["variants"]]
    label = f"Add to cart — {money(first['price'])}" if first["available"] else "Sold out"

    acc = []
    if extra.get("details"):
        acc.append(("Product Details", '<ul class="details">' + "".join(f"<li>{esc(d)}</li>" for d in extra["details"]) + "</ul>"))
    if extra.get("size_guide"):
        acc.append(("Size Guide", f'<img src="@/{img_path(extra["size_guide"])}" alt="{title} size chart (measurements per size)" loading="lazy">'))
    acc.append(("Shipping", site["shipping_html"]))
    accordion = "".join(f'<details class="accordion__item"><summary>{t}</summary><div class="accordion__content rte">{c}</div></details>' for t, c in acc)

    related = [r for r in extra.get("related", []) if r in PRODUCTS and r != h]
    related_html = f"""<section class="related page-width" aria-labelledby="related-title">
  <h2 class="related__title" id="related-title">Related</h2>
  {grid(related, "grid--related")}
</section>""" if related else ""

    desc_text = text_of(p["body_html"])
    ld = {"@context": "https://schema.org", "@type": "Product", "name": p["title"], "description": desc_text,
          "brand": {"@type": "Brand", "name": site["name"]}, "sku": first.get("sku") or None,
          "offers": [{"@type": "Offer", "price": v["price"], "priceCurrency": site["currency"]["code"],
                      "availability": "https://schema.org/" + ("InStock" if v["available"] else "OutOfStock"), "sku": v.get("sku")} for v in p["variants"]]}
    if site["site_url"]:
        ld["image"] = [f'{site["site_url"].rstrip("/")}/{img_path(im["src"])}' for im in p["images"]]
    head = f'\n<script type="application/ld+json">{js(ld)}</script>'

    # ordre du code = ordre de lecture mobile (photos, titre, achat, infos) ; la grille CSS replace tout sur ordinateur
    body = f"""<div class="page-width">
<div class="product">
  <div class="product__gallery gallery" data-gallery role="region" aria-roledescription="carousel" aria-label="{title} photos">
    <div class="gallery__stage" style="--ratio: {tallest['width']} / {tallest['height']}">{imgs}</div>
    {nav}
  </div>
  <h1 class="product__title">{title}</h1>
  <div class="product__buy">
    <form class="buy" data-buy onsubmit="return false">
      {''.join(groups)}
      <button type="button" class="btn btn--block buy__button" data-add-to-cart data-variant-id="{first['id']}"{"" if first["available"] else " disabled"}>{label}</button>
      <script type="application/json" data-variants>{js(variants)}</script>
    </form>
  </div>
  <div class="product__info">
    <div class="product__desc rte">{p['body_html']}</div>
    <div class="accordion">{accordion}</div>
  </div>
</div>
</div>
{related_html}"""
    return layout(url_product(h), p["title"], body, description=textwrap.shorten(desc_text, 160, placeholder="…") or None,
                  image=img_path(p["images"][0]["src"]), head_extra=head)


def page_contact():
    body = f"""<div class="page-width">
<h1 class="page-title">Contact</h1>
<form class="contact" method="post" action="{SHOP}/contact#contact_form" accept-charset="UTF-8">
  <input type="hidden" name="form_type" value="contact">
  <input type="hidden" name="utf8" value="✓">
  <label class="visually-hidden" for="c-name">Name</label>
  <input id="c-name" type="text" name="contact[name]" placeholder="Name" autocomplete="name" required>
  <label class="visually-hidden" for="c-phone">Phone Number</label>
  <input id="c-phone" type="tel" name="contact[phone]" placeholder="Phone Number" autocomplete="tel">
  <label class="visually-hidden" for="c-email">Email</label>
  <input id="c-email" type="email" name="contact[email]" placeholder="Email" autocomplete="email" required>
  <label class="visually-hidden" for="c-message">Message</label>
  <textarea id="c-message" name="contact[body]" placeholder="Message" rows="10" required></textarea>
  <button class="btn btn--block" type="submit">Send</button>
</form>
</div>"""
    return layout("pages/contact.html", "Contact", body, description=f"Contact {site['name']}: {site['email']}")


def page_simple(path, title, inner, cls="rte page-content", after="", title_cls="page-title", description=None):
    body = f'<div class="page-width">\n<h1 class="{title_cls}">{esc(title)}</h1>\n<div class="{cls}">{inner}</div>\n{after}</div>'
    return layout(path, title, body, description=description)


def page_cart():
    body = '<div class="page-width cart"><h1 class="visually-hidden">Your cart</h1><p>Your cart is empty.</p></div>'
    return layout("cart.html", "Your Shopping Cart", body)


def page_404():
    body = '<div class="page-width not-found"><h1>404 - Page no longer exists</h1><a class="btn" href="@/collections/all.html">Shop all</a></div>'
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
        html_ = re.sub(r'src="([^"]+)"', lambda m: f'src="@/{img_path(m.group(1))}" loading="lazy"', pg["html"])
        after = grid(content["collections"][pg["products"]]["products"], heading="h2") if pg.get("products") else ""
        pages[f"pages/{h}.html"] = page_simple(f"pages/{h}.html", pg["title"], html_, after=after, description=pg.get("description"))
    for f in sorted((DATA / "policies").glob("*.html")):
        raw = f.read_text(encoding="utf-8")
        title = re.match(r"<!--\s*(.*?)\s*-->", raw).group(1)
        body = re.sub(r"^<!--.*?-->\s*", "", raw)
        pages[f"policies/{f.stem}.html"] = page_simple(f"policies/{f.stem}.html", title, body, "rte policy", title_cls="page-title page-title--policy",
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
