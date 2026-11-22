// madebyscu — petit script sans dependance : en-tete, menu mobile, tiroir panier, photos des cartes, galerie produit,
// choix des tailles, lookbook, apparitions au defilement, bandeau, transitions de page.
(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const root = document.documentElement;
  const calm = matchMedia("(prefers-reduced-motion: reduce)");

  const head = $("[data-head]");
  const burger = $(".burger");
  const menu = $("#menu");
  const drawer = $("#cart-drawer");
  // le defilement de la page est bloque tant que le menu ou le tiroir est ouvert
  const syncLock = () => document.body.classList.toggle("is-locked", menu.classList.contains("is-open") || drawer.open);

  // ---------- en-tete : se cache en descendant, revient en remontant ----------
  let lastY = scrollY;
  let ticking = false;
  const onScroll = () => {
    ticking = false;
    const y = Math.max(0, scrollY);
    root.classList.toggle("is-scrolled", y > 4);
    if (y < 150 || menu.classList.contains("is-open") || head.contains(document.activeElement)) {
      head.classList.remove("is-hidden");
      lastY = y;
      return;
    }
    if (Math.abs(y - lastY) < 12) return; // petits mouvements ignores
    head.classList.toggle("is-hidden", y > lastY);
    lastY = y;
  };
  addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  head.addEventListener("focusin", () => head.classList.remove("is-hidden"));
  onScroll();

  // ---------- menu mobile ----------
  const behindMenu = () => [$("main"), $("footer"), $(".announcement"), $(".skip-link"), $(".header__right")];
  const setMenu = (open) => {
    burger.setAttribute("aria-expanded", open);
    burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    $(".burger__text", burger).textContent = open ? "Close" : "Menu";
    menu.classList.toggle("is-open", open);
    root.classList.toggle("menu-open", open);
    behindMenu().forEach((el) => el && (el.inert = open)); // le clavier reste dans le menu ouvert
    syncLock();
  };
  burger.addEventListener("click", () => setMenu(burger.getAttribute("aria-expanded") !== "true"));
  matchMedia("(min-width: 900px)").addEventListener("change", (e) => e.matches && menu.classList.contains("is-open") && setMenu(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && menu.classList.contains("is-open")) { setMenu(false); burger.focus(); }
  });

  // ---------- tiroir panier (vide tant que l'achat n'est pas branche) ----------
  $$("[data-cart-open]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    if (menu.classList.contains("is-open")) setMenu(false);
    drawer.showModal(); // <dialog> : focus garde dedans, Echap ferme, focus rendu a la fermeture
    syncLock();
  }));
  // la sortie animee est en CSS (transition de display/overlay) : on ferme simplement ; Echap ferme tout seul
  const closeDrawer = () => drawer.close();
  $$("[data-cart-close]").forEach((el) => el.addEventListener("click", closeDrawer));
  drawer.addEventListener("click", (e) => { if (e.target === drawer) closeDrawer(); }); // clic sur le fond
  drawer.addEventListener("close", syncLock);

  // ---------- message bref ----------
  const toastEl = $(".toast");
  let toastTimer;
  const toast = (msg) => {
    toastEl.textContent = msg;
    toastEl.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 2500);
  };

  // fin d'un defilement horizontal (glisser au doigt ou defilement doux) : plus d'evenement scroll depuis 120 ms
  const onSettle = (el, fn) => {
    let t;
    el.addEventListener("scroll", () => { clearTimeout(t); t = setTimeout(fn, 120); }, { passive: true });
  };

  // ---------- photos des cartes produit ----------
  const canHover = matchMedia("(hover: hover) and (pointer: fine)").matches;
  $$(".card__media").forEach((media) => {
    const track = $("[data-card-track]", media);
    const n = track.children.length;
    if (n < 2) return;
    const dots = $$(".card__dots i", media);
    // photo visee, gardee en memoire : un clic pendant un defilement doux part d'elle (pas de la position a mi-chemin)
    let i = 0;
    const mark = () => dots.forEach((d, k) => d.classList.toggle("is-on", k === i));
    const to = (k) => {
      i = (k + n) % n;
      mark();
      track.scrollTo({ left: i * track.clientWidth, behavior: calm.matches ? "auto" : "smooth" });
    };
    onSettle(track, () => { i = Math.round(track.scrollLeft / (track.clientWidth || 1)); mark(); }); // apres un glisser au doigt
    mark();
    $("[data-card-prev]", media)?.addEventListener("click", () => to(i - 1));
    $("[data-card-next]", media)?.addEventListener("click", () => to(i + 1));
    if (canHover) { // comme l'original : la 2e photo au survol, retour a la 1re en sortant
      media.addEventListener("mouseenter", () => to(1));
      media.addEventListener("mouseleave", () => to(0));
    }
  });

  // ---------- galerie produit (telephone : piste qui glisse + compteur ; ordinateur : photos empilees) ----------
  $$("[data-gallery]").forEach((g) => {
    const track = $("[data-gallery-track]", g);
    const items = [...track.children];
    const count = $("[data-gallery-index]", g);
    if (items.length < 2) return;
    // telephone : la 2e et la derniere photo (fleche precedente) sont pretes avant le premier geste
    if (matchMedia("(max-width: 899px)").matches) [items[1], items.at(-1)].forEach((li) => { $("img", li).loading = "eager"; });
    let i = 0; // photo visee, comme pour les cartes
    const show = (k) => {
      i = (k + items.length) % items.length;
      count.textContent = i + 1;
      track.scrollTo({ left: i * track.clientWidth, behavior: calm.matches ? "auto" : "smooth" });
    };
    onSettle(track, () => { i = Math.round(track.scrollLeft / (track.clientWidth || 1)); count.textContent = i + 1; });
    $("[data-prev]", g).addEventListener("click", () => show(i - 1));
    $("[data-next]", g).addEventListener("click", () => show(i + 1));
    g.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") show(i - 1);
      if (e.key === "ArrowRight") show(i + 1);
    });
  });

  // colonne d'achat collante : si elle depasse la fenetre, elle colle par le bas (on voit tout en descendant)
  $$(".product__sticky").forEach((col) => {
    const place = () => {
      const top = parseFloat(getComputedStyle(root).getPropertyValue("--ann-h")) + parseFloat(getComputedStyle(root).getPropertyValue("--head-h")) + 16;
      col.style.top = `${Math.min(top, innerHeight - col.offsetHeight - 24)}px`;
    };
    $$("details", col).forEach((d) => d.addEventListener("toggle", place));
    addEventListener("resize", place);
    place();
  });

  // lien « Size guide » : ouvre l'accordeon du guide
  $$("[data-open-guide]").forEach((a) => a.addEventListener("click", () => {
    const d = $(a.getAttribute("href"));
    if (d) d.open = true;
  }));

  // ---------- choix des tailles ----------
  $$("[data-buy]").forEach((form) => {
    const variants = JSON.parse($("[data-variants]", form).textContent);
    const btn = $("[data-add-to-cart]", form);
    const groups = $$(".options", form);
    const anyLeft = variants.some((v) => v.available); // produit entierement epuise : tailles laissees visibles, bouton « Sold out »
    const selected = () => groups.map((fs) => $("input:checked", fs)?.value ?? null);
    const update = () => {
      const sel = selected();
      // une valeur est barree si aucune variante disponible ne la propose avec les autres choix
      groups.forEach((fs, k) => $$(".option", fs).forEach((label) => {
        const input = $("input", label);
        const ok = variants.some((v) => v.available && v.options[k] === input.value && v.options.every((o, j) => j === k || o === sel[j]));
        label.classList.toggle("is-unavailable", !ok);
        input.disabled = !ok && anyLeft;
        input.setAttribute("aria-label", ok ? input.value : `${input.value} – sold out`);
      }));
      const v = variants.find((v) => v.options.every((o, j) => o === sel[j]));
      btn.disabled = !v || !v.available;
      btn.textContent = !v ? "Unavailable" : v.available ? `Add to cart — ${v.price}` : "Sold out";
      if (v) btn.dataset.variantId = v.id;
    };
    form.addEventListener("change", update);
    update();
    // ACHAT : a brancher plus tard (panier / paiement). La variante choisie est dans btn.dataset.variantId.
    btn.addEventListener("click", () => {
      if (!calm.matches) btn.animate([{ transform: "none" }, { transform: "scale(.98)" }, { transform: "none" }], { duration: 250, easing: "ease-out" });
      toast("Checkout coming soon");
    });
  });

  // ---------- lookbook ----------
  // ordinateur + navigateur qui sait lier une animation au defilement : bande horizontale epinglee ;
  // sinon (telephone, mouvement reduit, vieux navigateur) : carrousel natif + barre + glisser a la souris
  const pinQuery = matchMedia("(min-width: 900px) and (prefers-reduced-motion: no-preference)");
  const canPin = () => pinQuery.matches && CSS.supports("animation-timeline: view()");
  $$("[data-lookbook-section]").forEach((section) => {
    const rail = $("[data-lookbook-rail]", section);
    const pin = $(".lookbook__pin", section);
    const track = $("[data-lookbook]", section);
    const thumb = $("[data-lookbook-thumb]", section);
    let speed = 1; // px de bande par px de defilement
    const layout = () => {
      section.classList.toggle("is-pinned", canPin());
      if (section.classList.contains("is-pinned")) {
        // epinglage plafonne a 1,25 hauteur d'ecran : au-dela, la bande avance plus vite que la page
        const dist = Math.max(0, rail.scrollWidth - pin.clientWidth);
        const run = Math.min(dist, Math.round(innerHeight * 1.25));
        speed = run ? dist / run : 1;
        section.style.setProperty("--dist", `${dist}px`);
        section.style.setProperty("--pin", `${run}px`);
        thumb.style.cssText = "";
      } else {
        section.style.removeProperty("--dist");
        section.style.removeProperty("--pin");
        sync();
      }
    };
    const sync = () => {
      if (section.classList.contains("is-pinned")) return;
      const max = track.scrollWidth - track.clientWidth;
      const ratio = track.clientWidth / track.scrollWidth;
      thumb.style.width = `${Math.min(100, ratio * 100)}%`;
      thumb.style.left = `${max > 0 ? (track.scrollLeft / max) * (100 - ratio * 100) : 0}%`;
    };
    track.addEventListener("scroll", sync, { passive: true });
    addEventListener("resize", layout);
    pinQuery.addEventListener("change", layout);
    $$("img", track).forEach((im) => im.addEventListener("load", layout));
    layout();
    // clavier : « Shop the look » est loin a droite dans la bande epinglee ; on amene la fin de l'epinglage a l'ecran
    $(".lookbook__end", section).addEventListener("focus", () => {
      if (section.classList.contains("is-pinned")) scrollTo({ top: section.getBoundingClientRect().bottom + scrollY - innerHeight, behavior: "auto" });
    });

    let start = null;
    track.addEventListener("pointerdown", (e) => {
      if (e.pointerType !== "mouse" || section.classList.contains("is-pinned")) return;
      start = { x: e.clientX, left: track.scrollLeft };
      track.classList.add("is-dragging");
      track.setPointerCapture(e.pointerId);
    });
    track.addEventListener("pointermove", (e) => { if (start) track.scrollLeft = start.left - (e.clientX - start.x); });
    const end = () => { start = null; track.classList.remove("is-dragging"); };
    track.addEventListener("pointerup", end);
    track.addEventListener("pointercancel", end);
    track.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault(); // sinon le navigateur fait aussi defiler la piste (anime) : deux photos par appui
      const dir = e.key === "ArrowRight" ? 1 : -1;
      const behavior = calm.matches ? "auto" : "smooth";
      if (section.classList.contains("is-pinned")) scrollBy({ top: dir * ((track.firstElementChild?.offsetWidth || 300) + 40) / speed, behavior }); // bande epinglee : les fleches font defiler la page
      else track.scrollBy({ left: dir * ((track.firstElementChild?.offsetWidth || 280) + 10), behavior });
    });
  });

  // ---------- bandeau qui defile : bouton pause (WCAG 2.2.2) ----------
  $$("[data-ticker]").forEach((t) => {
    const b = $("[data-ticker-toggle]", t);
    if (calm.matches) { b.hidden = true; return; }
    b.addEventListener("click", () => {
      const paused = t.classList.toggle("is-paused");
      b.setAttribute("aria-pressed", paused);
      b.textContent = paused ? "Play" : "Pause";
    });
  });

  // ---------- apparitions au defilement (une seule fois) ----------
  // ce qui est deja a l'ecran au chargement n'est jamais cache (animation CSS directe) ;
  // le reste est « arme » puis revele quand il entre dans la fenetre
  $$(".lookbook__track").forEach((g) => [...g.children].forEach((c, k) => c.style.setProperty("--i", k % 4)));
  // grilles : rang = colonne reelle, la cascade suit l'ordre de lecture quel que soit le nombre de colonnes
  $$(".grid, .closeups__grid").forEach((g) => [...g.children].forEach((c) => c.style.setProperty("--i", Math.round((c.offsetLeft - g.firstElementChild.offsetLeft) / c.offsetWidth))));
  if ("IntersectionObserver" in window && !calm.matches) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("is-in");
      io.unobserve(e.target);
    }), { rootMargin: "0px 0px -8% 0px" });
    $$("[data-reveal], [data-split]").forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.top < innerHeight && r.bottom > 0 && r.left < innerWidth && r.right > 0) return;
      if (el.matches(".is-pinned .lookbook__item") && r.left >= innerWidth) return; // arrivent de droite trop vite pour un rideau
      el.dataset.armed = "";
      io.observe(el);
    });
  }

  // ---------- transition de page : la photo de la carte devient la 1re photo de la fiche ----------
  // photo affichee dans la piste de la carte (la 2e au survol, ou apres un glisser)
  const shownImg = (card) => {
    const track = $("[data-card-track]", card);
    return track.children[Math.round(track.scrollLeft / (track.clientWidth || 1))] || track.children[0];
  };
  document.addEventListener("click", (e) => {
    const a = e.target.closest(".card a");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    $$("[data-vt]").forEach((el) => { el.style.viewTransitionName = "none"; });
    shownImg(a.closest(".card")).style.viewTransitionName = "product";
  });
  // retour arriere restaure depuis le cache : on retire le nom pose au clic
  addEventListener("pageshow", (e) => {
    if (e.persisted) $$(".card__track img").forEach((im) => { im.style.viewTransitionName = ""; });
  });
  // retour depuis une fiche : sa photo revient dans sa carte (morph inverse)
  addEventListener("pagereveal", (e) => {
    const act = window.navigation?.activation;
    // Retour / Avance seulement : en navigation normale (produit lie, logo) la carte est hors de l'ecran
    const from = e.viewTransition && act?.navigationType === "traverse" && act.from?.url;
    if (!from) return;
    const file = new URL(from).pathname.split("/").pop();
    const link = $$(".card__name a").find((a) => a.pathname.endsWith(`/products/${file}`));
    if (!link) return;
    const img = shownImg(link.closest(".card"));
    const named = $$("[data-vt]"); // un seul element par nom, sinon le navigateur annule la transition
    named.forEach((el) => { el.style.viewTransitionName = "none"; });
    img.style.viewTransitionName = "product";
    e.viewTransition.finished.finally(() => {
      img.style.viewTransitionName = "";
      named.forEach((el) => { el.style.viewTransitionName = ""; });
    });
  });
})();
