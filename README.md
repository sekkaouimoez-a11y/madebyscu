# madebyscu — site statique

Réécriture complète du site [madebyscu.com](https://madebyscu.com) (boutique Shopify) en HTML / CSS / JS simples, hébergeable gratuitement sur **GitHub Pages**. Aucune dépendance : Python 3.9+ suffit pour régénérer les pages.

> **Achat pas encore branché.** Le bouton « Add to cart » affiche seulement « Checkout coming soon », le panier est toujours vide et « Account » renvoie vers le compte Shopify. Le point d'accroche est dans `assets/js/site.js` (commentaire `ACHAT`) : la variante choisie y est disponible (`data-variant-id`).

## Ce qu'il y a dedans

| Page | Fichier |
|---|---|
| Accueil (bandeau, collection Cherry, lookbook, newsletter) | `index.html` |
| Shop (tout le catalogue) | `pages/catalog.html` |
| Collections | `collections/all.html`, `cherry.html`, `denim.html`, `ljwrld-og-drop.html` |
| Fiches produits (galerie, tailles, détails, guide des tailles, livraison, produits liés) | `products/*.html` |
| Contact | `pages/contact.html` |
| Guide des tailles denim | `pages/denim-size-guide.html` |
| Pages légales | `policies/*.html` |
| Panier (vide) et page 404 | `cart.html`, `404.html` |

Les formulaires **Contact** et **Newsletter** envoient vers la boutique Shopify (`/contact`), comme sur le site d'origine : les messages et les inscrits arrivent toujours dans Shopify.

## Modifier le site

Les pages HTML sont **fabriquées** à partir des fichiers de `data/`. On ne retouche pas les `.html` à la main : on modifie les données puis on relance la fabrication.

| Je veux changer… | Fichier |
|---|---|
| bandeau du haut, menu, textes de l'accueil, photo principale, lookbook, texte de livraison | `data/site.json` |
| détails produit (puces), guide des tailles, produits liés, contenu des collections | `data/content.json` |
| produits (noms, prix, stock, photos, descriptions) | dans l'admin Shopify, puis synchro (plus bas). Ne pas modifier `data/products.json` à la main : il est remplacé à chaque synchro |
| pages légales | `data/policies/*.html` |
| apparence | `assets/css/style.css` |
| comportements (menu, galerie, tailles…) | `assets/js/site.js` |

Puis :

```powershell
python outils/build.py
```

## Apparence et mouvement

- **Jetons** (couleurs, polices, tailles, espaces, courbes et durées) : en tête de `assets/css/style.css`, dans `:root`. Changer une valeur là change tout le site.
- **Couleur d'accent** : noire par défaut. Une collection peut avoir la sienne dans `data/site.json` → `collection_accents` (ex. `"cherry": "#7a0a22"`). `build.py` la pose sur les pages de cette collection, sur ses fiches produits et sur l'accueil si elle est mise en avant (`home.featured_collection`). Elle ne sert qu'à « OUT NOW » et à quelques détails (fil d'Ariane, sélection de texte). Pour un nouveau drop : ajouter sa couleur, changer `featured_collection`, puis `python outils/build.py`.
- **Gros plans de l'accueil** (« The details ») : `data/site.json` → `home.details`. Chaque gros plan = une photo d'un produit + un de ses détails de `data/content.json` (`build.py` vérifie que les deux existent).
- **Mouvement** : tout est dans `assets/css/style.css`, bloc `MOUVEMENT` (sous `prefers-reduced-motion: no-preference`). Avec « réduire les animations » dans le système, tout est visible tout de suite et immobile ; sans JavaScript, rien ne reste caché.
- **Couper un effet** : supprimer (ou commenter) sa ligne dans ce bloc, par exemple `.shop-all__title` (glissement de « Shop all »), `.hero__zoom` (zoom de la photo d'ouverture), `.footer__mark-inner` (logo du pied qui monte), `.ticker__track` (bandeau qui défile), `[data-reveal="curtain"]` (rideaux des photos). Le lookbook épinglé se coupe dans `assets/js/site.js` (`canPin`) : il redevient un carrousel, comme sur téléphone.

## Rester synchronisé avec Shopify

Pour récupérer les derniers produits, prix et stocks de la boutique et télécharger les nouvelles photos :

```powershell
python outils/sync.py
```

```powershell
python outils/build.py
```

Chaque photo produit et du lookbook est aussi téléchargée en 600 px (suffixe `-600`) : `build.py` s'en sert pour les `srcset` (téléphones, vignettes).  
(`python outils/sync.py --images` ne télécharge que les images manquantes, sans toucher aux produits ; `--force` retélécharge aussi les photos remplacées sous le même nom. La synchro refuse d'écrire si la boutique ne répond pas en euros.)  
Un nouveau produit doit aussi être ajouté à sa collection dans `data/content.json` (et, si besoin, ses puces « Product Details » et son guide des tailles).

## Voir le site en local

```powershell
python -m http.server 8000
```

Puis ouvrir http://localhost:8000

## Mise en ligne (GitHub Pages)

1. Dans `data/site.json`, mettre `"base_path": "/NOM-DU-DEPOT/"` et `"site_url": "https://UTILISATEUR.github.io/NOM-DU-DEPOT"`, puis `python outils/build.py`.
2. Pousser sur GitHub (dépôt **public** : obligatoire pour Pages sur un compte gratuit), puis *Settings → Pages → Deploy from a branch → main / (root)*.
3. **Attention : tant que l'achat n'est pas branché, ne pas déplacer madebyscu.com**, sinon les clients ne peuvent plus commander. Plus tard, avec un nom de domaine à soi (ex. madebyscu.com) : `"base_path": "/"`, `"site_url": "https://madebyscu.com"`, et ajouter le domaine dans *Settings → Pages*. Si le domaine quitte Shopify, mettre l'adresse `xxxx.myshopify.com` de la boutique dans `"shopify_domain"` pour que formulaires et compte continuent de marcher.

## Mettre à jour le site en ligne

Après chaque modification (ou synchro) :

```powershell
python outils/build.py
```

```powershell
git add -A
```

```powershell
git commit -m "Ce qui a changé"
```

```powershell
git push
```

GitHub Pages republie le site en quelques minutes.

## Crédits

Polices, toutes deux sous licence SIL Open Font License 1.1 et hébergées sur le site :
- **Archivo** (variable, largeur 62–125 %, graisse 100–900), © The Archivo Project Authors (Omnibus-Type) : `assets/fonts/archivo-var.woff2`, licence `assets/fonts/OFL-Archivo.txt` ;
- **Geist Mono** (variable), © The Geist Project Authors (Vercel) : `assets/fonts/geist-mono-var.woff2`, licence `assets/fonts/OFL-GeistMono.txt`.

Logo vectorisé depuis le PNG d'origine : `assets/img/logo.svg` (pour un pied de page encore plus grand, il faudrait le fichier vectoriel original de la marque).
