"""Synchronise le site avec la boutique Shopify (madebyscu.com).

1. Recupere data/products.json depuis la boutique (prix en EUR, stock, photos, descriptions).
2. Telecharge en WebP toutes les images manquantes dans assets/img/.

Usage :  python outils/sync.py            (produits + images)
         python outils/sync.py --images   (images seulement, sans toucher aux produits)
         python outils/sync.py --force    (retelecharge aussi les images deja presentes, si une photo a ete remplacee)
Puis :   python outils/build.py
"""
import json, re, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
IMG = ROOT / "assets" / "img"
COOKIE = "localization=FR; cart_currency=EUR"  # cookies de pays : memes prix en euros que la page ?country=FR
# largeurs de telechargement (build.py s'en sert pour les srcset) ; "-600" = petite version pour telephones et vignettes
PRODUCT_W, LOOKBOOK_W, SMALL_W, SMALL = 1200, 900, 600, "-600"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def get(url, accept="*/*", cookie=""):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, "Cookie": cookie})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))  # Shopify limite le debit : on patiente


def local_stem(url):
    """Nom local stable d'une image Shopify : 'IMG_2594.jpg?v=1' -> 'img_2594-jpg' (extension gardee : pas de doublon)."""
    name = url.split("?")[0].rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9_-]+", "-", name.lower())


def local_file(url, suffix=""):
    """Fichier deja telecharge pour cette image (.webp, .jpg ou .png), sinon None."""
    return next(IMG.glob(local_stem(url) + suffix + ".*"), None)


def cdn(url):
    """Ramene toute URL d'image de la boutique sur le CDN Shopify (pas limite en debit), sans parametre width."""
    url = url if not url.startswith("//") else "https:" + url
    m = re.search(r"/cdn/shop/files/(.+)$", url)
    if m:
        url = "https://cdn.shopify.com/s/files/1/0778/5303/2797/files/" + m.group(1)
    base, _, query = url.partition("?")
    query = "&".join(q for q in query.split("&") if q and not q.startswith("width="))
    return base + ("?" + query if query else "")


def download(url, width, suffix="", force=False):
    old = local_file(url, suffix)
    if old and not force:
        return False
    src = cdn(url)
    src += ("&" if "?" in src else "?") + f"width={width}"
    data = get(src, accept="image/webp,*/*")  # le CDN donne du WebP quand c'est plus leger
    ext = ".webp" if data[8:12] == b"WEBP" else ".png" if data[1:4] == b"PNG" else ".jpg" if data[:3] == bytes([255, 216, 255]) else None
    if not ext:
        raise RuntimeError(f"format d'image inconnu : {src}")
    if old:
        old.unlink()
    (IMG / (local_stem(url) + suffix + ext)).write_bytes(data)
    return True


def images_wanted():
    """Toutes les images du site : (url, largeur de telechargement[, suffixe du fichier])."""
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
    products = json.loads((DATA / "products.json").read_text(encoding="utf-8"))["products"]
    yield site["favicon"], 192
    yield site["home"]["hero"]["image"], 2400
    yield site["home"]["hero"]["image"], 900, "-900"  # version telephone
    yield site["home"]["hero"]["image"], 1400, "-1400"  # telephones DPR 3 et ecrans Retina
    for u in site["home"]["lookbook"]["images"]:
        yield u, LOOKBOOK_W
        yield u, SMALL_W, SMALL
    for p in products:
        for i in p["images"]:
            yield i["src"], PRODUCT_W
            yield i["src"], SMALL_W, SMALL
    for extra in content["products"].values():
        if extra.get("size_guide"):
            yield extra["size_guide"], 1400
    for page in content["pages"].values():
        for u in re.findall(r'src="([^"]+)"', page.get("html", "")):
            yield u, 1400


def sync_products():
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    url = f"https://{site['shopify_domain']}/products.json?limit=250"
    data = json.loads(get(url, accept="application/json", cookie=COOKIE))
    if not data.get("products"):
        raise RuntimeError("reponse vide, products.json garde tel quel")
    # sans le bon pays, Shopify repond en livres : on refuse plutot que d'afficher de faux prix
    cur = json.loads(get(f"https://{site['shopify_domain']}/cart.js", accept="application/json", cookie=COOKIE)).get("currency")
    if cur != site["currency"]["code"]:
        raise RuntimeError(f"boutique en {cur}, pas en {site['currency']['code']} : products.json garde tel quel")
    (DATA / "products.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"products.json : {len(data['products'])} produits")


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    if "--images" not in sys.argv:
        try:
            sync_products()
        except Exception as e:  # la boutique peut refuser (429) : on garde les donnees actuelles
            print(f"ATTENTION produits non mis a jour : {e}")
    n = 0
    for url, width, *suffix in images_wanted():
        if download(url, width, *suffix, force="--force" in sys.argv):
            n += 1
            print("  +", local_file(url, *suffix).name)
    print(f"{n} image(s) telechargee(s)")
