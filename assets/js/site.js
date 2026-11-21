// madebyscu — petit script sans dependance : menu mobile, tiroir panier, photos des cartes, galerie produit,
// choix des tailles, lookbook.
(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];

  const burger = $(".burger");
  const menu = $("#menu");
  const drawer = $("#cart-drawer");
  // le defilement de la page est bloque tant que le menu ou le tiroir est ouvert
  const syncLock = () => document.body.classList.toggle("is-locked", menu.classList.contains("is-open") || drawer.open);

  // ---------- menu mobile ----------
  const behindMenu = () => [$("main"), $("footer"), $(".announcement"), $(".skip-link"), $(".header__logo"), $(".header__right")];
  const setMenu = (open) => {
    burger.setAttribute("aria-expanded", open);
    burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    menu.classList.toggle("is-open", open);
    behindMenu().forEach((el) => el && (el.inert = open)); // le clavier reste dans le menu ouvert
    syncLock();
  };
  burger.addEventListener("click", () => setMenu(burger.getAttribute("aria-expanded") !== "true"));
  matchMedia("(min-width: 750px)").addEventListener("change", (e) => e.matches && menu.classList.contains("is-open") && setMenu(false));
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
  $$("[data-cart-close]").forEach((el) => el.addEventListener("click", () => drawer.close()));
  drawer.addEventListener("click", (e) => { if (e.target === drawer) drawer.close(); }); // clic sur le fond
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
  const canHover = matchMedia("(hover: hover)").matches;
  $$(".card__media").forEach((media) => {
    const track = $("[data-card-track]", media);
    const n = track.children.length;
    if (n < 2) return;
    const index = () => Math.round(track.scrollLeft / track.clientWidth);
    const to = (k) => track.scrollTo({ left: ((k + n) % n) * track.clientWidth, behavior: "smooth" });
    $("[data-card-prev]", media)?.addEventListener("click", () => to(index() - 1));
    $("[data-card-next]", media)?.addEventListener("click", () => to(index() + 1));
    if (canHover) { // comme l'original : la 2e photo au survol, retour a la 1re en sortant
      media.addEventListener("mouseenter", () => to(1));
      media.addEventListener("mouseleave", () => to(0));
    }
  });

  // ---------- galerie produit ----------
  $$("[data-gallery]").forEach((g) => {
    const imgs = $$(".gallery__stage img", g);
    const dots = $$(".gallery__dot", g);
    if (imgs.length < 2) return;
    let i = 0;
    const load = (im) => { if (im.dataset.src) { im.src = im.dataset.src; delete im.dataset.src; } };
    const show = (n) => {
      i = (n + imgs.length) % imgs.length;
      imgs.forEach((im, k) => { im.hidden = false; im.classList.toggle("is-active", k === i); });
      load(imgs[i]);
      load(imgs[(i + 1) % imgs.length]); // precharge la suivante
      dots.forEach((d, k) => d.setAttribute("aria-current", k === i ? "true" : "false"));
    };
    $("[data-prev]", g).addEventListener("click", () => show(i - 1));
    $("[data-next]", g).addEventListener("click", () => show(i + 1));
    dots.forEach((d, k) => d.addEventListener("click", () => show(k)));
    const stage = $(".gallery__stage", g);
    // glisser (doigt ou souris) : change de photo ; le clic qui suit un glisser est ignore
    let x0 = null, swiped = false;
    stage.addEventListener("pointerdown", (e) => { x0 = e.clientX; swiped = false; });
    stage.addEventListener("pointerup", (e) => {
      if (x0 === null) return;
      const dx = e.clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 40) { swiped = true; show(dx < 0 ? i + 1 : i - 1); }
    });
    stage.addEventListener("pointercancel", () => { x0 = null; });
    // clic sur la photo : moitie gauche = precedente, moitie droite = suivante
    stage.addEventListener("click", (e) => {
      if (swiped) { swiped = false; return; }
      const r = stage.getBoundingClientRect();
      show(e.clientX - r.left < r.width / 2 ? i - 1 : i + 1);
    });
    g.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") show(i - 1);
      if (e.key === "ArrowRight") show(i + 1);
    });
  });

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
    btn.addEventListener("click", () => toast("Checkout coming soon"));
  });

  // ---------- lookbook : barre de progression + glisser a la souris ----------
  $$("[data-lookbook]").forEach((track) => {
    const thumb = $("[data-lookbook-thumb]", track.parentElement);
    const sync = () => {
      const max = track.scrollWidth - track.clientWidth;
      const ratio = track.clientWidth / track.scrollWidth;
      thumb.style.width = `${Math.min(100, ratio * 100)}%`;
      thumb.style.left = `${max > 0 ? (track.scrollLeft / max) * (100 - ratio * 100) : 0}%`;
    };
    track.addEventListener("scroll", sync, { passive: true });
    addEventListener("resize", sync);
    $$("img", track).forEach((im) => im.addEventListener("load", sync));
    sync();

    let start = null;
    track.addEventListener("pointerdown", (e) => {
      if (e.pointerType !== "mouse") return;
      start = { x: e.clientX, left: track.scrollLeft };
      track.classList.add("is-dragging");
      track.setPointerCapture(e.pointerId);
    });
    track.addEventListener("pointermove", (e) => { if (start) track.scrollLeft = start.left - (e.clientX - start.x); });
    const end = () => { start = null; track.classList.remove("is-dragging"); };
    track.addEventListener("pointerup", end);
    track.addEventListener("pointercancel", end);
    track.addEventListener("keydown", (e) => {
      const step = (track.firstElementChild?.offsetWidth || 280) + 10;
      if (e.key === "ArrowRight") track.scrollBy({ left: step, behavior: "smooth" });
      if (e.key === "ArrowLeft") track.scrollBy({ left: -step, behavior: "smooth" });
    });
  });
})();
