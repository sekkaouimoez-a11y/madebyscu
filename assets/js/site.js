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
  const closeDrawer = () => {
    if (!drawer.open || drawer.classList.contains("is-closing")) return;
    if (calm.matches || !drawer.getAnimations) return drawer.close();
    drawer.classList.add("is-closing"); // le tiroir ressort par la droite avant de se fermer
    setTimeout(() => { drawer.classList.remove("is-closing"); drawer.close(); }, 340);
  };
  $$("[data-cart-close]").forEach((el) => el.addEventListener("click", closeDrawer));
  drawer.addEventListener("click", (e) => { if (e.target === drawer) closeDrawer(); }); // clic sur le fond
  drawer.addEventListener("cancel", (e) => { e.preventDefault(); closeDrawer(); }); // Echap
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

  // ---------- photos des cartes produit ----------
  const canHover = matchMedia("(hover: hover) and (pointer: fine)").matches;
  $$(".card__media").forEach((media) => {
    const track = $("[data-card-track]", media);
    const n = track.children.length;
    if (n < 2) return;
    const dots = $$(".card__dots i", media);
    const index = () => Math.round(track.scrollLeft / track.clientWidth);
    const to = (k) => track.scrollTo({ left: ((k + n) % n) * track.clientWidth, behavior: calm.matches ? "auto" : "smooth" });
    const mark = () => { const i = index(); dots.forEach((d, k) => d.classList.toggle("is-on", k === i)); };
    track.addEventListener("scroll", mark, { passive: true });
    mark();
    $("[data-card-prev]", media)?.addEventListener("click", () => to(index() - 1));
    $("[data-card-next]", media)?.addEventListener("click", () => to(index() + 1));
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
    const index = () => Math.round(track.scrollLeft / (track.clientWidth || 1));
    const show = (k) => {
      const i = (k + items.length) % items.length;
      track.scrollTo({ left: i * track.clientWidth, behavior: calm.matches ? "auto" : "smooth" });
    };
    track.addEventListener("scroll", () => { count.textContent = index() + 1; }, { passive: true });
    $("[data-prev]", g).addEventListener("click", () => show(index() - 1));
    $("[data-next]", g).addEventListener("click", () => show(index() + 1));
    g.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") show(index() - 1);
      if (e.key === "ArrowRight") show(index() + 1);
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
    const selected = () => groups.map((fs) => $("input:checked", fs)?.value ?? null);
    const update = () => {
      const sel = selected();
      // une valeur est barree si aucune variante disponible ne la propose avec les autres choix
      groups.forEach((fs, k) => $$(".option", fs).forEach((label) => {
        const input = $("input", label);
        const ok = variants.some((v) => v.available && v.options[k] === input.value && v.options.every((o, j) => j === k || o === sel[j]));
        label.classList.toggle("is-unavailable", !ok);
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
    const layout = () => {
      section.classList.toggle("is-pinned", canPin());
      if (section.classList.contains("is-pinned")) {
        section.style.setProperty("--dist", `${Math.max(0, rail.scrollWidth - pin.clientWidth)}px`);
        thumb.style.cssText = "";
      } else {
        section.style.removeProperty("--dist");
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
      if (section.classList.contains("is-pinned")) { // bande epinglee : les fleches font defiler la page
        const step = (track.firstElementChild?.offsetWidth || 300) + 40;
        if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); scrollBy({ top: e.key === "ArrowRight" ? step : -step, behavior: calm.matches ? "auto" : "smooth" }); }
        return;
      }
      const step = (track.firstElementChild?.offsetWidth || 280) + 10;
      if (e.key === "ArrowRight") track.scrollBy({ left: step, behavior: "smooth" });
      if (e.key === "ArrowLeft") track.scrollBy({ left: -step, behavior: "smooth" });
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
  $$(".grid, .lookbook__track").forEach((g) => [...g.children].forEach((c, k) => c.style.setProperty("--i", k % 4)));
  if ("IntersectionObserver" in window && !calm.matches) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("is-in");
      io.unobserve(e.target);
    }), { rootMargin: "0px 0px -8% 0px" });
    $$("[data-reveal], [data-split]").forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.top < innerHeight && r.bottom > 0 && r.left < innerWidth && r.right > 0) return;
      el.dataset.armed = "";
      io.observe(el);
    });
  }

  // ---------- transition de page : la photo de la carte devient la 1re photo de la fiche ----------
  document.addEventListener("click", (e) => {
    const a = e.target.closest(".card a");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    $$("[data-vt]").forEach((el) => { el.style.viewTransitionName = "none"; });
    const track = $("[data-card-track]", a.closest(".card"));
    const img = track.children[Math.round(track.scrollLeft / (track.clientWidth || 1))] || track.children[0];
    img.style.viewTransitionName = "product";
  });
  // retour arriere restaure depuis le cache : on retire le nom pose au clic
  addEventListener("pageshow", (e) => {
    if (e.persisted) $$(".card__track img").forEach((im) => { im.style.viewTransitionName = ""; });
  });
})();
