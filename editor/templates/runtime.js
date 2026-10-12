/* Shorts editor runtime: turns the compiled edit (window.EDIT, written by build.py) into DOM + one
   paused, seekable GSAP timeline registered for HyperFrames. All timing decisions are made in Python;
   this file only draws and animates. Deterministic: no clocks, no randomness, no network. */
(function () {
  const E = window.EDIT;
  const root = document.getElementById("root");
  const $ = (sel, el = document) => el.querySelector(sel);
  const mk = (tag, cls, parent, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    if (parent) parent.appendChild(n);
    return n;
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  // *word* => accent span
  const markup = (s) => esc(s).replace(/\*([^*]+)\*/g, '<span class="acc">$1</span>');
  const seeded = (seed) => () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

  // ---------------------------------------------------------------- theme
  const T = E.theme;
  for (const [k, v] of Object.entries(T.vars)) root.style.setProperty(k, v);

  const cam = $("#cam");
  const overlays = $("#overlays");
  const brollLayer = $("#broll");
  const capLayer = $("#captions");
  const fx = $("#fx");

  // fit an element vertically into [top, bottom] (px) — CSS zoom keeps GSAP transforms free
  function place(el, zone, align = "center") {
    const [top, bottom] = zone;
    const avail = bottom - top;
    let h = el.offsetHeight;
    if (h > avail) {
      el.style.zoom = (avail / h).toFixed(3);
      h = avail;
      el.style.top = top / el.style.zoom + "px";
      return;
    }
    const y = align === "top" ? top : align === "bottom" ? bottom - h : top + (avail - h) / 2;
    el.style.top = Math.round(y) + "px";
  }

  function build() {
    const tl = gsap.timeline({ paused: true });

    // ---------------------------------------------------------------- camera
    gsap.set(cam, { transformOrigin: `${E.camera.origin[0]}px ${E.camera.origin[1]}px`, scale: E.camera.start_scale || 1 });
    for (const ev of E.camera.events) {
      if (ev.type === "shake") {
        const r = seeded(Math.round(ev.t * 1000) + 7);
        const n = Math.max(4, Math.round(ev.dur / 0.045));
        for (let i = 0; i < n; i++) {
          const k = 1 - i / n;
          tl.to(cam, { x: (r() - 0.5) * 2 * ev.amp * k, y: (r() - 0.5) * 2 * ev.amp * k, rotation: (r() - 0.5) * 1.2 * k,
            duration: ev.dur / n, ease: "none" }, ev.t + (i * ev.dur) / n);
        }
        tl.to(cam, { x: ev.x || 0, y: ev.y || 0, rotation: 0, duration: 0.05, ease: "none" }, ev.t + ev.dur);
        continue;
      }
      if (ev.origin) tl.set(cam, { transformOrigin: `${ev.origin[0]}px ${ev.origin[1]}px` }, ev.t);
      const props = { scale: ev.scale };
      if (ev.x != null) props.x = ev.x;
      if (ev.y != null) props.y = ev.y;
      if (!ev.dur) tl.set(cam, props, ev.t);
      else tl.to(cam, { ...props, duration: ev.dur, ease: ev.ease || "power3.out" }, ev.t);
    }
    if (E.vignette != null) root.style.setProperty("--vignette", E.vignette);

    // ---------------------------------------------------------------- captions
    const C = E.captions;
    if (C && C.chunks.length) {
      capLayer.classList.add("cap-" + C.style);
      if (C.uppercase) capLayer.classList.add("cap-upper");
      for (const ch of C.chunks) {
        const box = mk("div", "cap-chunk", capLayer);
        box.style.fontSize = C.size + "px";
        const pill = C.style === "karaoke" ? mk("div", "cap-pill", box) : null;
        const spans = ch.words.map((w) => {
          const s = mk("span", "cap-word" + (w.hl ? " hl" : ""), box);
          const inner = mk("span", null, s, esc(w.text));
          inner.style.display = "inline-block";
          return { s, inner, w };
        });
        // shrink long chunks to the max width
        box.style.visibility = "hidden";
        box.style.opacity = 1;
        const maxW = 1080 - 140;
        let fs = C.size;
        while (box.scrollWidth > maxW + 2 && fs > 40) {
          fs -= 4;
          box.style.fontSize = fs + "px";
        }
        const h = box.offsetHeight;
        box.style.top = Math.round(ch.y - h / 2) + "px";
        const rects = spans.map(({ s }) => ({ x: s.offsetLeft, y: s.offsetTop, w: s.offsetWidth, h: s.offsetHeight }));
        box.style.visibility = "";
        box.style.opacity = 0;

        tl.set(box, { opacity: 1 }, ch.t0);
        tl.set(box, { opacity: 0 }, ch.t1);
        if (C.style === "pop") {
          spans.forEach(({ s, inner, w }) => {
            // gentle overshoot + small bump: bigger values make wide uppercase words collide with their neighbours
            tl.fromTo(s, { opacity: 0, scale: 0.55, y: 22 }, { opacity: 1, scale: 1, y: 0, duration: 0.13, ease: "back.out(1.7)" }, w.t0);
            if (!w.hl) {
              tl.set(s, { color: T.active }, w.t0);
              tl.set(s, { color: T.vars["--cap-color"] }, Math.min(w.t1, ch.t1 - 0.01));
            }
            tl.fromTo(inner, { scale: 1 }, { scale: w.hl ? 1.07 : 1.04, duration: 0.09, ease: "power2.out" }, w.t0);
            tl.to(inner, { scale: 1, duration: 0.16, ease: "power2.inOut" }, w.t0 + 0.09);
          });
        } else if (C.style === "karaoke") {
          tl.fromTo(box, { scale: 0.86, y: 20 }, { scale: 1, y: 0, duration: 0.14, ease: "back.out(2.4)" }, ch.t0);
          spans.forEach(({ s, w }, i) => {
            const r = rects[i];
            const pad = 0.12 * fs;
            const geo = { left: r.x - pad, top: r.y + 0.06 * fs, width: r.w + 2 * pad, height: r.h - 0.06 * fs };
            if (i === 0) tl.set(pill, { ...geo, opacity: 1 }, w.t0);
            else tl.to(pill, { ...geo, opacity: 1, duration: 0.09, ease: "power2.out" }, w.t0);
            tl.set(s, { className: "cap-word on" + (w.hl ? " hl" : "") }, w.t0);
            tl.set(s, { className: "cap-word" + (w.hl ? " hl" : "") }, Math.min(w.t1, ch.t1 - 0.01));
          });
        } else {
          tl.fromTo(box, { y: 18 }, { y: 0, duration: 0.16, ease: "power3.out" }, ch.t0);
        }
      }
    }

    // ---------------------------------------------------------------- overlays
    const enterX = (side) => (side === "left" ? -1150 : side === "right" ? 1150 : 0);
    const R = {
      hook(o) {
        const el = mk("div", "hook" + (o.boxed ? " boxed" : ""), overlays);
        const words = o.words.map((w) => {
          const s = mk("span", "w" + (w.acc ? " acc" : ""), el);
          if (w.acc && o.boxed) mk("span", "hlbox", s); // first child, so the text paints above it
          // the theme fonts have no "≠": draw it as "=" with a slash so it stays as heavy as the words
          mk("span", "tx", s, w.w === "≠" ? '<span class="neq">=</span>' : esc(w.w));
          return s;
        });
        if (o.size) el.style.fontSize = o.size + "px";
        place(el, o.zone);
        tl.set(el, { opacity: 1 }, o.t);
        words.forEach((s, i) => {
          const at = o.t + i * (o.stagger ?? 0.07);
          tl.fromTo(s, { opacity: 0, scale: 1.9, y: -10 }, { opacity: 1, scale: 1, y: 0, duration: 0.22, ease: "power4.out" }, at);
          const hb = $(".hlbox", s);
          if (hb) tl.fromTo(hb, { scaleX: 0, transformOrigin: "0% 50%" }, { scaleX: 1, duration: 0.25, ease: "power3.out" }, at + 0.12);
        });
        if (o.sub) {
          const sub = mk("div", "hook-sub", overlays, markup(o.sub));
          const top = parseFloat(el.style.top) + el.offsetHeight * (parseFloat(el.style.zoom) || 1) + 14;
          sub.style.top = top + "px";
          tl.fromTo(sub, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }, o.t + words.length * 0.07 + 0.15);
          tl.to(sub, { opacity: 0, duration: 0.2 }, o.t + o.dur - 0.2);
        }
        tl.to(el, { opacity: 0, y: -30, duration: 0.22, ease: "power2.in" }, o.t + o.dur - 0.22);
      },

      card(o) {
        const el = mk("div", "card", overlays);
        if (o.accent_bar !== false) mk("div", "bar", el);
        if (o.icon) mk("div", "icon", el, esc(o.icon));
        const txt = mk("div", "txt", el);
        if (o.label) mk("div", "label", txt, markup(o.label));
        if (o.value) mk("div", "value", txt, markup(o.value));
        if (o.sub) mk("div", "sub", txt, markup(o.sub));
        if (o.value_size) $(".value", el).style.fontSize = o.value_size + "px";
        place(el, o.zone);
        const x0 = enterX(o.side || "left");
        tl.fromTo(el, { opacity: 0, x: x0, scale: 0.96 }, { opacity: 1, x: 0, scale: 1, duration: 0.5, ease: "expo.out" }, o.t);
        const ic = $(".icon", el);
        if (ic) tl.fromTo(ic, { scale: 0, rotation: -25 }, { scale: 1, rotation: 0, duration: 0.45, ease: "back.out(2.6)" }, o.t + 0.15);
        tl.to(el, { opacity: 0, x: -x0 * 0.6, duration: 0.32, ease: "power2.in" }, o.t + o.dur - 0.32);
      },

      stat(o) {
        const el = mk("div", "stat", overlays);
        const num = mk("div", "num", el);
        const v = mk("span", null, num);
        if (o.suffix) mk("span", "unit", num, esc(o.suffix));
        if (o.label) mk("div", "lbl", el, markup(o.label));
        const fmt = (x) => (o.prefix || "") + Number(x).toLocaleString("en-IN", { minimumFractionDigits: o.decimals || 0, maximumFractionDigits: o.decimals || 0 });
        v.textContent = fmt(o.to);
        place(el, o.zone);
        v.textContent = fmt(o.from || 0);
        const p = { v: o.from || 0 };
        tl.fromTo(el, { opacity: 0, scale: 0.6, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: 0.35, ease: "back.out(2)" }, o.t);
        tl.to(p, { v: o.to, duration: o.count_dur || 1.0, ease: "power2.out", onUpdate: () => (v.textContent = fmt(p.v)) }, o.t + 0.1);
        tl.fromTo(num, { scale: 1 }, { scale: 1.08, duration: 0.1, yoyo: true, repeat: 1, ease: "power1.inOut" }, o.t + 0.1 + (o.count_dur || 1.0));
        tl.to(el, { opacity: 0, scale: 0.9, duration: 0.25, ease: "power2.in" }, o.t + o.dur - 0.25);
      },

      bars(o) {
        const el = mk("div", "chart", overlays);
        if (o.title) mk("h3", null, el, markup(o.title));
        const max = o.max || Math.max(...o.items.map((i) => i.value));
        const rows = o.items.map((it) => {
          const row = mk("div", "row" + (it.hot ? " hot" : ""), el);
          mk("div", "l", row, esc(it.label));
          const tr = mk("div", "track", row);
          const fill = mk("div", "fill", tr);
          const val = mk("div", "v", tr, esc(it.display ?? it.value));
          const w = Math.max(0.06, it.value / max);
          fill.style.width = (w * 100).toFixed(1) + "%";
          return { fill, val, w, it };
        });
        place(el, o.zone);
        tl.fromTo(el, { opacity: 0, y: 40, scale: 0.97 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "expo.out" }, o.t);
        for (const r of rows) {
          const tw = r.fill.parentNode.offsetWidth;
          const end = r.w * tw;
          const inside = end > tw * 0.62;
          if (inside) { r.val.style.color = "#111"; }
          tl.fromTo(r.fill, { scaleX: 0, transformOrigin: "0% 50%" }, { scaleX: 1, duration: 0.55, ease: "power3.out" }, r.it.t);
          tl.fromTo(r.val, { opacity: 0, x: 0 }, { opacity: 1, x: inside ? end - r.val.offsetWidth - 18 : end, duration: 0.55, ease: "power3.out" }, r.it.t);
        }
        tl.to(el, { opacity: 0, y: -30, duration: 0.3, ease: "power2.in" }, o.t + o.dur - 0.3);
      },

      list(o) {
        const el = mk("div", "list", overlays);
        if (o.title) mk("h3", null, el, markup(o.title));
        const items = o.items.map((it) => {
          const row = mk("div", "it", el);
          mk("div", "ck" + (it.bad ? " bad" : ""), row, it.bad ? "✕" : "✓");
          mk("div", null, row, markup(it.text));
          return { row, it };
        });
        place(el, o.zone);
        tl.fromTo(el, { opacity: 0, x: enterX(o.side || "left") }, { opacity: 1, x: 0, duration: 0.45, ease: "expo.out" }, o.t);
        for (const { row, it } of items) {
          tl.fromTo(row, { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.3, ease: "back.out(2)" }, it.t);
          tl.fromTo($(".ck", row), { scale: 0 }, { scale: 1, duration: 0.3, ease: "back.out(3)" }, it.t + 0.05);
        }
        tl.to(el, { opacity: 0, duration: 0.25 }, o.t + o.dur - 0.25);
      },

      compare(o) {
        const el = mk("div", "compare", overlays);
        const side = (s, cls) => {
          const d = mk("div", "side " + cls + (s.win ? " win" : s.lose ? " lose" : ""), el);
          mk("div", "t", d, markup(s.title));
          mk("div", "v", d, markup(s.value));
          return d;
        };
        const a = side(o.a, "a"), b = side(o.b, "b");
        const vs = mk("div", "vs", el, "VS");
        place(el, o.zone);
        tl.fromTo(a, { opacity: 0, x: -600 }, { opacity: 1, x: 0, duration: 0.5, ease: "expo.out" }, o.t);
        tl.fromTo(b, { opacity: 0, x: 600 }, { opacity: 1, x: 0, duration: 0.5, ease: "expo.out" }, o.t_b ?? o.t + 0.25);
        tl.fromTo(vs, { opacity: 0, scale: 0, rotation: -90 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.4, ease: "back.out(3)" }, (o.t_b ?? o.t + 0.25) + 0.25);
        tl.to([a, b, vs], { opacity: 0, duration: 0.25 }, o.t + o.dur - 0.25);
      },

      emoji(o) {
        const el = mk("div", "emoji", overlays, esc(o.emoji));
        const size = o.size || 220;
        Object.assign(el.style, { width: size + "px", height: size + "px", fontSize: size * 0.86 + "px", left: o.x - size / 2 + "px", top: o.y - size / 2 + "px" });
        tl.fromTo(el, { opacity: 0, scale: 0, rotation: -30 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.42, ease: "back.out(3)" }, o.t);
        tl.to(el, { rotation: 8, duration: 0.5, ease: "sine.inOut", yoyo: true, repeat: Math.max(0, Math.floor((o.dur - 0.9) / 0.5)) }, o.t + 0.42);
        tl.to(el, { opacity: 0, scale: 0, duration: 0.2, ease: "back.in(2)" }, o.t + o.dur - 0.2);
      },

      media(o) {
        // media elements are written into index.html by build.py (the renderer pre-extracts video frames)
        const el = document.getElementById(o.el_id);
        const kb = $(".kb", el);
        if (o.mode === "full") {
          tl.set(el, { opacity: 1 }, o.t);
          tl.fromTo(kb, { scale: 1.12 }, { scale: o.kb === false ? 1.12 : 1.0, duration: o.dur, ease: "none" }, o.t);
          tl.fromTo(el, { clipPath: "inset(0% 0% 100% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 0.28, ease: "power3.out" }, o.t);
          tl.to(el, { clipPath: "inset(100% 0% 0% 0%)", duration: 0.25, ease: "power3.in" }, o.t + o.dur - 0.25);
          tl.set(el, { opacity: 0 }, o.t + o.dur);
          return;
        }
        el.style.height = (o.height || Math.min(640, o.zone[1] - o.zone[0])) + "px";
        if (o.width) Object.assign(el.style, { left: (1080 - o.width) / 2 + "px", right: "auto", width: o.width + "px" });  // small badge, centred
        place(el, o.zone);
        const x0 = enterX(o.side || "right");
        tl.fromTo(el, { opacity: 0, x: x0, rotation: x0 > 0 ? 4 : -4 }, { opacity: 1, x: 0, rotation: 0, duration: 0.55, ease: "expo.out" }, o.t);
        tl.fromTo(kb, { scale: 1.0 }, { scale: 1.1, duration: o.dur, ease: "none" }, o.t);
        tl.to(el, { opacity: 0, x: -x0 * 0.5, duration: 0.3, ease: "power2.in" }, o.t + o.dur - 0.3);
      },

      lower_third(o) {
        const el = mk("div", "l3", overlays);
        mk("div", "bar", el);
        mk("div", "n", el, markup(o.name));
        if (o.role) mk("div", "r", el, markup(o.role));
        place(el, o.zone, o.align || "bottom");
        tl.fromTo(el, { opacity: 0, x: -500 }, { opacity: 1, x: 0, duration: 0.5, ease: "expo.out" }, o.t);
        tl.to(el, { opacity: 0, x: -500, duration: 0.35, ease: "power2.in" }, o.t + o.dur - 0.35);
      },

      countdown(o) {
        const el = mk("div", "countdown", overlays);
        const ring = mk("div", "ring", el);
        const C = 2 * Math.PI * 130;
        ring.innerHTML = `<svg viewBox="0 0 300 300"><circle cx="150" cy="150" r="130" fill="rgba(0,0,0,.55)" stroke="rgba(255,255,255,.25)" stroke-width="18"/>
          <circle class="arc" cx="150" cy="150" r="130" fill="none" stroke="${T.vars["--accent"]}" stroke-width="18" stroke-linecap="round"
          stroke-dasharray="${C}" stroke-dashoffset="0" transform="rotate(-90 150 150)"/></svg>`;
        const nums = [];
        for (let k = o.n; k >= 1; k--) nums.push(mk("div", "n", ring, String(k)));
        if (o.tag) mk("div", "tag", ring, markup(o.tag));
        place(el, o.zone);
        tl.fromTo(el, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.5)" }, o.t);
        tl.fromTo($(".arc", ring), { attr: { "stroke-dashoffset": 0 } }, { attr: { "stroke-dashoffset": C }, duration: o.n, ease: "none" }, o.t);
        nums.forEach((n, i) => {
          tl.fromTo(n, { opacity: 0, scale: 1.8 }, { opacity: 1, scale: 1, duration: 0.25, ease: "power4.out" }, o.t + i);
          tl.to(n, { opacity: 0, scale: 0.6, duration: 0.15 }, o.t + i + 0.85);
        });
        tl.to(el, { opacity: 0, scale: 1.3, duration: 0.2 }, o.t + o.n);
      },

      cta(o) {
        const el = mk("div", "cta", overlays);
        if (o.text) mk("div", "line", el, markup(o.text));
        const btn = mk("div", "btn", el, `<span>${esc(o.icon || "🔔")}</span><span class="lbl">${esc(o.button || "SUBSCRIBE")}</span>`);
        if (o.color) btn.style.background = o.color;
        const lbl = $(".lbl", btn);
        place(el, o.zone);
        tl.fromTo(el, { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.45, ease: "back.out(2)" }, o.t);
        if (o.click === false) {  // no cursor/click: the button just pulses (e.g. "COMMENT KARO")
          tl.to(btn, { scale: 1.07, duration: 0.35, yoyo: true, repeat: Math.max(1, Math.floor((o.dur - 0.9) / 0.35)), ease: "sine.inOut" }, o.t + 0.45);
          tl.to(el, { opacity: 0, duration: 0.3 }, o.t + o.dur - 0.3);
          return;
        }
        const cur = mk("div", "cursor", el, "👆");
        const bx = btn.offsetLeft + btn.offsetWidth * 0.62, by = btn.offsetTop + btn.offsetHeight * 0.55;
        Object.assign(cur.style, { left: bx + "px", top: by + "px" });
        tl.fromTo(cur, { opacity: 0, x: 160, y: 180 }, { opacity: 1, x: 0, y: 0, duration: 0.45, ease: "power3.out" }, o.t + 0.5);
        tl.to(btn, { scale: 0.9, duration: 0.08 }, o.t + 1.0);
        tl.set(btn, { className: "btn done" }, o.t + 1.08);
        tl.set(lbl, { textContent: o.done || "SUBSCRIBED" }, o.t + 1.08);
        tl.to(btn, { scale: 1, duration: 0.25, ease: "back.out(3)" }, o.t + 1.08);
        tl.to(cur, { opacity: 0, duration: 0.2 }, o.t + 1.5);
        tl.to(el, { opacity: 0, duration: 0.3 }, o.t + o.dur - 0.3);
      },

      text_slam(o) {
        if (o.dim !== false) {
          const d = mk("div", "dim", overlays);
          tl.to(d, { opacity: 1, duration: 0.15 }, o.t);
          tl.to(d, { opacity: 0, duration: 0.2 }, o.t + o.dur - 0.2);
        }
        const el = mk("div", "text-slam", overlays, markup(o.text));
        if (o.size) el.style.fontSize = o.size + "px";
        place(el, o.zone);
        tl.fromTo(el, { opacity: 0, scale: 2.2 }, { opacity: 1, scale: 1, duration: 0.25, ease: "power4.out" }, o.t);
        tl.to(el, { scale: 1.06, duration: o.dur - 0.45, ease: "none" }, o.t + 0.25);
        tl.to(el, { opacity: 0, scale: 0.9, duration: 0.2 }, o.t + o.dur - 0.2);
      },

      // animated explainer: a chariot wheel used as a sundial — the sun moves across the sky and the
      // hub's shadow swings the opposite way. times: t_shadow (shadow appears), t_move0..t_move1 (sun moves)
      sundial(o) {
        const el = mk("div", "sundial", overlays);
        if (o.title) mk("h3", null, el, markup(o.title));
        const cx = 320, cy = 300, R = 250, a0 = o.from ?? -68, a1 = o.to ?? 68;
        const pt = (a, r) => [cx + r * Math.sin((a * Math.PI) / 180), cy - r * Math.cos((a * Math.PI) / 180)];
        const spokes = (n, off, r0, r1, w, c) => Array.from({ length: n }, (_, k) => {
          const a = off + (360 / n) * k, [x0, y0] = pt(a, r0), [x1, y1] = pt(a, r1);
          return `<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="${c}" stroke-width="${w}" stroke-linecap="round"/>`;
        }).join("");
        const beads = Array.from({ length: 48 }, (_, k) => {
          const [x, y] = pt(k * 7.5, 110);
          return `<circle cx="${x}" cy="${y}" r="3.4" fill="#7A5634"/>`;
        }).join("");
        const [sx0, sy0] = pt(a0, R), [sx1, sy1] = pt(a1, R);
        const svg = mk("div", "sd-art", el);
        svg.innerHTML = `<svg viewBox="0 0 640 420" width="640" height="420">
          <path d="M ${sx0} ${sy0} A ${R} ${R} 0 0 1 ${sx1} ${sy1}" fill="none" stroke="rgba(255,214,10,.45)" stroke-width="4" stroke-dasharray="10 12"/>
          <text x="${sx0 - 4}" y="${sy0 + 86}" class="sd-lbl" text-anchor="middle">Subah</text>
          <text x="${sx1 + 4}" y="${sy1 + 86}" class="sd-lbl" text-anchor="middle">Shaam</text>
          <g class="sd-wheel">
            <circle cx="${cx}" cy="${cy}" r="110" fill="#E6CBA4" stroke="#C69A6B" stroke-width="16"/>
            <circle cx="${cx}" cy="${cy}" r="92" fill="none" stroke="#B0855A" stroke-width="4"/>
            ${spokes(8, 22.5, 26, 92, 4, "#B98E61")}${spokes(8, 0, 26, 92, 11, "#C69A6B")}${beads}
          </g>
          <g class="sd-shadow"><polygon points="${cx - 15},${cy} ${cx + 15},${cy} ${cx + 5},${cy + 96} ${cx - 5},${cy + 96}" fill="rgba(35,20,8,.78)"/></g>
          <circle cx="${cx}" cy="${cy}" r="26" fill="#8B6A4A" stroke="#F3DDBB" stroke-width="5"/>
          <g class="sd-sun">
            <line x1="${cx}" y1="${cy - R + 34}" x2="${cx}" y2="${cy - 34}" stroke="rgba(255,214,10,.55)" stroke-width="5" stroke-dasharray="4 14" stroke-linecap="round"/>
            <circle cx="${cx}" cy="${cy - R}" r="44" fill="rgba(255,190,0,.22)"/>
            <circle cx="${cx}" cy="${cy - R}" r="27" fill="#FFD60A" stroke="#FFF3B0" stroke-width="4"/>
          </g>
        </svg>`;
        place(el, o.zone);
        const wheel = $(".sd-wheel", el), shadow = $(".sd-shadow", el), sun = $(".sd-sun", el);
        const org = `${cx} ${cy}`;
        tl.fromTo(el, { opacity: 0, y: 40, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "expo.out" }, o.t);
        tl.fromTo(wheel, { rotation: -120, svgOrigin: org, opacity: 0 }, { rotation: 0, svgOrigin: org, opacity: 1, duration: 0.9, ease: "power3.out" }, o.t + 0.1);
        tl.fromTo(sun, { opacity: 0 }, { opacity: 1, duration: 0.35 }, o.t + 0.35);
        tl.fromTo(shadow, { opacity: 0 }, { opacity: 1, duration: 0.4 }, o.t_shadow ?? o.t + 0.6);
        const m0 = o.t_move0 ?? o.t + 1, m1 = Math.max(m0 + 0.5, o.t_move1 ?? o.t + o.dur - 0.6);
        tl.fromTo([sun, shadow], { rotation: a0, svgOrigin: org }, { rotation: a1, svgOrigin: org, duration: m1 - m0, ease: "sine.inOut" }, m0);
        tl.to(el, { opacity: 0, y: -30, duration: 0.3, ease: "power2.in" }, o.t + o.dur - 0.3);
      },

      // golden clock hand (or a hub shadow) pinned to a point on the footage, e.g. the wheel's hub.
      // o.x, o.y px; o.len; o.from/o.to degrees (0 = 12 o'clock, clockwise); o.style "glow" | "shadow"; o.ticks
      hand(o) {
        const el = mk("div", "ov-full", overlays);
        const steps = o.steps ?? Math.max(1, Math.round(o.dur / 0.5));
        const ticks = o.ticks ? Array.from({ length: 12 }, (_, k) => {
          const a = (k * 30 * Math.PI) / 180, r0 = o.len * 1.12, r1 = o.len * (k % 3 ? 1.2 : 1.27);
          return `<line class="tk" x1="${o.x + r0 * Math.sin(a)}" y1="${o.y - r0 * Math.cos(a)}" x2="${o.x + r1 * Math.sin(a)}" y2="${o.y - r1 * Math.cos(a)}" stroke="#FFD60A" stroke-width="${k % 3 ? 6 : 11}" stroke-linecap="round"/>`;
        }).join("") : "";
        const handSvg = o.style === "shadow"
          ? `<polygon points="${o.x - 26},${o.y} ${o.x + 26},${o.y} ${o.x + 9},${o.y - o.len} ${o.x - 9},${o.y - o.len}" fill="rgba(25,12,2,.62)"/>`
          : `<line x1="${o.x}" y1="${o.y + o.len * 0.18}" x2="${o.x}" y2="${o.y - o.len}" stroke="#FFD60A" stroke-width="16" stroke-linecap="round"/>
             <circle cx="${o.x}" cy="${o.y - o.len}" r="15" fill="#FFF3B0"/>`;
        el.innerHTML = `<svg viewBox="0 0 1080 1920" width="1080" height="1920">
          <g class="tks">${ticks}</g>
          <g class="hd" style="filter: drop-shadow(0 0 14px rgba(255,214,10,.85))">${handSvg}</g>
          ${o.style === "shadow" ? "" : `<circle cx="${o.x}" cy="${o.y}" r="22" fill="#FFD60A" stroke="#3A2A10" stroke-width="5"/>`}
        </svg>`;
        const hd = $(".hd", el), org = `${o.x} ${o.y}`;
        tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.18 }, o.t);
        if (o.ticks) tl.fromTo(el.querySelectorAll(".tk"), { opacity: 0 }, { opacity: 1, duration: 0.05, stagger: 0.03 }, o.t);
        tl.fromTo(hd, { rotation: o.from ?? 0, svgOrigin: org }, { rotation: o.to ?? 120, svgOrigin: org, duration: o.dur - 0.2,
          ease: o.style === "shadow" ? "power2.out" : `steps(${steps})` }, o.t);
        tl.to(el, { opacity: 0, duration: 0.2 }, o.t + o.dur - 0.2);
      },

      // circle drawn around something on the footage + a label pill
      ring(o) {
        const el = mk("div", "ov-full", overlays);
        const C = 2 * Math.PI * o.r;
        el.innerHTML = `<svg viewBox="0 0 1080 1920" width="1080" height="1920" style="filter: drop-shadow(0 0 12px rgba(255,214,10,.8))">
          <circle class="rg" cx="${o.x}" cy="${o.y}" r="${o.r}" fill="none" stroke="#FFD60A" stroke-width="11"
            stroke-dasharray="${C}" stroke-dashoffset="${C}" transform="rotate(-90 ${o.x} ${o.y})"/></svg>`;
        const lab = mk("div", "ring-label", el, markup(o.label || ""));
        const lx = Math.min(1080 - 360, Math.max(60, o.x + (o.label_dx ?? o.r * 0.55)));
        Object.assign(lab.style, { left: lx + "px", top: o.y - o.r - 120 + (o.label_dy ?? 0) + "px" });
        tl.set(el, { opacity: 1 }, o.t);
        tl.to($(".rg", el), { attr: { "stroke-dashoffset": 0 }, duration: 0.45, ease: "power2.out" }, o.t);
        tl.fromTo(lab, { opacity: 0, scale: 0.5, y: 20 }, { opacity: 1, scale: 1, y: 0, duration: 0.3, ease: "back.out(2.5)" }, o.t + 0.2);
        tl.to(el, { opacity: 0, duration: 0.2 }, o.t + o.dur - 0.2);
        gsap.set(el, { opacity: 0 });
      },

      // red rubber stamp slammed on screen ("NAHI!")
      stamp(o) {
        const el = mk("div", "stamp", overlays, markup(o.text));
        if (o.size) el.style.fontSize = o.size + "px";
        place(el, o.zone);
        el.style.left = Math.round((1080 - el.offsetWidth) / 2) + "px";
        tl.fromTo(el, { opacity: 0, scale: 2.6, rotation: (o.rot ?? -10) - 8 }, { opacity: 1, scale: 1, rotation: o.rot ?? -10, duration: 0.16, ease: "power4.in" }, o.t);
        tl.to(el, { scale: 1.06, duration: 0.08, yoyo: true, repeat: 1 }, o.t + 0.16);
        tl.to(el, { opacity: 0, scale: 0.9, duration: 0.2 }, o.t + o.dur - 0.2);
      },

      // warm sunlight glow sweeping in (screen blend)
      flare(o) {
        const el = mk("div", "flare", fx);
        tl.fromTo(el, { opacity: 0, x: -420, y: -380, scale: 0.7 }, { opacity: o.strength ?? 0.85, x: 0, y: 0, scale: 1.15, duration: o.dur * 0.55, ease: "sine.out" }, o.t);
        tl.to(el, { opacity: 0, x: 160, duration: o.dur * 0.45, ease: "sine.in" }, o.t + o.dur * 0.55);
      },

      // ending: Konark wheel -> stylised (not a replica) Rs 10 note that flips to show the wheel on its back,
      // then a push into the wheel that loops back to the opening shot.
      // times: t_wheel, t_card, t_label, t_flip, t_zoom
      note10(o) {
        const el = mk("div", "n10", overlays);
        const wheelSvg = (r, stroke) => {
          const pt = (a, rr) => [r + rr * Math.sin((a * Math.PI) / 180), r - rr * Math.cos((a * Math.PI) / 180)];
          const sp = (n, off, w) => Array.from({ length: n }, (_, k) => {
            const [x0, y0] = pt(off + (360 / n) * k, r * 0.2), [x1, y1] = pt(off + (360 / n) * k, r * 0.84);
            return `<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="${stroke}" stroke-width="${w}" stroke-linecap="round"/>`;
          }).join("");
          const beads = Array.from({ length: 40 }, (_, k) => { const [x, y] = pt(k * 9, r * 0.93); return `<circle cx="${x}" cy="${y}" r="${r * 0.025}" fill="${stroke}"/>`; }).join("");
          return `<svg viewBox="0 0 ${2 * r} ${2 * r}" width="${2 * r}" height="${2 * r}">
            <circle cx="${r}" cy="${r}" r="${r * 0.86}" fill="none" stroke="${stroke}" stroke-width="${r * 0.07}"/>${beads}
            ${sp(8, 22.5, r * 0.025)}${sp(8, 0, r * 0.06)}
            <circle cx="${r}" cy="${r}" r="${r * 0.2}" fill="none" stroke="${stroke}" stroke-width="${r * 0.05}"/>
            <circle cx="${r}" cy="${r}" r="${r * 0.08}" fill="${stroke}"/></svg>`;
        };
        const label = mk("div", "n10-label", el, markup(o.label || "₹10 ke *NAYE* note ke *PEECHE*"));
        const card = mk("div", "n10-card", el);
        const front = mk("div", "n10-face n10-front", card,
          `<div class="n10-amt">₹10</div><div class="n10-chip">NAYA NOTE</div><div class="n10-guil"></div>`);
        const back = mk("div", "n10-face n10-back", card, `<div class="n10-guil"></div><div class="n10-motif">${wheelSvg(150, "#F3D9A4")}</div>`);
        const big = mk("div", "n10-big", el, wheelSvg(260, "#FFD60A"));
        gsap.set(card, { transformPerspective: 1600 });
        gsap.set(back, { rotationY: 180 });
        tl.set(el, { opacity: 1 }, o.t);
        // the wheel spins in
        tl.fromTo(big, { opacity: 0, scale: 0.2, rotation: -200 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.6, ease: "back.out(1.6)" }, o.t_wheel ?? o.t);
        tl.to(big, { rotation: 30, duration: (o.t_card ?? o.t + 1) - (o.t_wheel ?? o.t) - 0.6 + 0.01, ease: "none" }, (o.t_wheel ?? o.t) + 0.6);
        // "aapki jeb mein": the note slides up, the big wheel shrinks out of the way
        tl.fromTo(card, { opacity: 0, y: 700, rotation: 8 }, { opacity: 1, y: 0, rotation: -3, duration: 0.55, ease: "expo.out" }, o.t_card);
        tl.to(big, { scale: 0.42, x: 225, opacity: 0.95, duration: 0.5, ease: "power3.inOut" }, o.t_card);  // onto the note's right side
        tl.fromTo(label, { opacity: 0, y: -30, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2)" }, o.t_label);
        if (o.t_label_out) tl.to(label, { opacity: 0, y: -20, duration: 0.2 }, o.t_label_out);
        // "peeche": flip to the back; the floating wheel drops into the motif
        tl.to(card, { rotationY: 180, rotation: 0, duration: 0.6, ease: "power3.inOut" }, o.t_flip);
        tl.to(front, { opacity: 0, duration: 0.01 }, o.t_flip + 0.3);
        tl.to(big, { x: 0, scale: 0.58, opacity: 0, duration: 0.45, ease: "power2.in" }, o.t_flip + 0.05);
        tl.fromTo($(".n10-motif", back), { rotation: 0 }, { rotation: 360, transformOrigin: "50% 50%", duration: (o.t_zoom ?? o.t + o.dur - 0.7) - o.t_flip, ease: "none" }, o.t_flip);
        // "yaad rakhna...": dive into the wheel (loops into the opening wheel shot)
        const tz = o.t_zoom ?? o.t + o.dur - 0.7;
        tl.to(label, { opacity: 0, duration: 0.2 }, tz);
        tl.to(card, { scale: 6.5, duration: o.t + o.dur - tz, ease: "power3.in" }, tz);
        tl.to(el, { opacity: 0, duration: 0.15 }, o.t + o.dur - 0.15);
        gsap.set(el, { opacity: 0 });
      },

      // A/B/C quiz. o.options[k] = {key, text, t}: each pops in at its own time. Optional answer reveal at o.t_answer
      // (o.answer turns green with a tick, the others dim with a cross), o.label after it (o.t_label), o.footer pill
      // at o.t_footer. o.style "stack" (one big card per option) | "row" (letter tiles side by side)
      quiz(o) {
        const row = o.style === "row";
        const el = mk("div", "quiz" + (row ? " row" : ""), overlays);
        if (o.title) mk("div", "qz-title", el, markup(o.title));
        const wrap = mk("div", "qz-opts", el);
        const opts = o.options.map((op) => {
          const c = mk("div", "qz-opt", wrap);
          mk("div", "qz-key", c, esc(op.key));
          if (!row && op.text) mk("div", "qz-txt", c, markup(op.text));
          const win = o.answer != null && op.key === o.answer;
          const mark = o.t_answer != null ? mk("div", "qz-mark " + (win ? "ok" : "no"), c, win ? "✓" : "✕") : null;
          return { c, mark, win, op };
        });
        const lab = o.label ? mk("div", "qz-label", el, markup(o.label)) : null;
        const foot = o.footer ? mk("div", "qz-foot", el, markup(o.footer)) : null;
        place(el, o.zone);
        tl.set(el, { opacity: 1 }, o.t);
        for (const { c, op } of opts) {
          if (row) tl.fromTo(c, { opacity: 0, y: 50, scale: 0.5 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(2.6)" }, op.t);
          else tl.fromTo(c, { opacity: 0, x: 320, scale: 0.92 }, { opacity: 1, x: 0, scale: 1, duration: 0.34, ease: "back.out(1.8)" }, op.t);
        }
        if (o.t_answer != null) {
          for (const { c, mark, win } of opts) {
            if (win) {
              tl.set(c, { className: "qz-opt win" }, o.t_answer);
              tl.fromTo(c, { scale: 1 }, { scale: 1.1, duration: 0.14, yoyo: true, repeat: 1, ease: "power2.out" }, o.t_answer);
            } else {
              tl.to(c, { opacity: 0.38, duration: 0.2 }, o.t_answer);
            }
            tl.fromTo(mark, { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, o.t_answer + (win ? 0.05 : 0.12));
          }
        }
        if (lab) tl.fromTo(lab, { opacity: 0, y: 24, scale: 0.85 }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2)" },
          o.t_label ?? (o.t_answer ?? o.t) + 0.35);
        if (foot) tl.fromTo(foot, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, o.t_footer ?? o.t + 1);
        tl.to(el, { opacity: 0, y: -24, duration: 0.25, ease: "power2.in" }, o.t + o.dur - 0.25);
        gsap.set(el, { opacity: 0 });
      },

      // thermometer card: the column sits at o.from (°C), the reading o.from is crossed out at o.t_cross, the column
      // drops to o.to at o.t_drop while the readout counts down. From o.t_steady a flame under the bulb grows
      // ("more heat") but the column only trembles, and o.steady_text shows.
      thermo(o) {
        const el = mk("div", "thermo", overlays);
        const lo = o.min ?? 60, hi = o.max ?? 110, top = 34, len = 400, base = top + len + 26;
        const y = (v) => top + len * (1 - (v - lo) / (hi - lo));
        let ticks = "";
        for (let v = lo; v <= hi; v += 10) {
          const yy = y(v), mark = v === o.from;
          ticks += `<line x1="150" y1="${yy}" x2="${mark ? 182 : 172}" y2="${yy}" stroke="rgba(255,255,255,.75)" stroke-width="5" stroke-linecap="round"/>
            <text x="194" y="${yy + 11}" class="th-tk">${v}°</text>`;
        }
        const art = mk("div", "th-art", el);
        art.innerHTML = `<svg viewBox="0 0 270 560" width="270" height="560">
          <rect x="88" y="${top - 22}" width="60" height="${len + 70}" rx="30" fill="rgba(255,255,255,.12)" stroke="#fff" stroke-width="6"/>
          <rect class="th-hg" x="104" y="${y(o.from)}" width="28" height="${base - y(o.from)}" rx="14" fill="#FF3B30"/>
          <circle cx="118" cy="${base + 40}" r="54" fill="#FF3B30" stroke="#fff" stroke-width="6"/>
          <circle cx="102" cy="${base + 26}" r="14" fill="rgba(255,255,255,.45)"/>
          ${ticks}
        </svg>`;
        const heat = mk("div", "th-heat", el, "🔥");
        const side = mk("div", "th-side", el);
        if (o.tag) mk("div", "th-tag", side, markup(o.tag));
        const old = mk("div", "th-old", side, `${esc(o.from)}°C<span class="th-strike"></span>`);
        const cur = mk("div", "th-new", side);
        const fmt = (v) => `${o.prefix ?? "~"}${Math.round(v)}°C`;
        cur.textContent = fmt(o.to);
        const steady = o.steady_text ? mk("div", "th-steady", side, markup(o.steady_text)) : null;
        place(el, o.zone);
        cur.textContent = fmt(o.from);
        const hg = $(".th-hg", el), strike = $(".th-strike", old);
        tl.fromTo(el, { opacity: 0, y: 40, scale: 0.95 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "expo.out" }, o.t);
        gsap.set(cur, { opacity: 0 });
        const tc = o.t_cross ?? o.t_drop - 0.4;
        tl.fromTo(strike, { scaleX: 0, transformOrigin: "0% 50%" }, { scaleX: 1, duration: 0.22, ease: "power3.out" }, tc);
        tl.to(old, { opacity: 0.55, scale: 0.72, transformOrigin: "0% 50%", duration: 0.3, ease: "power2.out" }, tc + 0.15);
        const p = { v: o.from };
        tl.fromTo(cur, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.25, ease: "power3.out" }, o.t_drop);
        tl.to(p, { v: o.to, duration: 0.9, ease: "power2.inOut", onUpdate: () => (cur.textContent = fmt(p.v)) }, o.t_drop);
        tl.to(hg, { attr: { y: y(o.to), height: base - y(o.to) }, duration: 0.9, ease: "power2.inOut" }, o.t_drop);
        tl.fromTo(cur, { scale: 1 }, { scale: 1.12, duration: 0.12, yoyo: true, repeat: 1, ease: "power1.inOut" }, o.t_drop + 0.9);
        gsap.set(heat, { opacity: 0 });
        if (o.t_steady != null) {
          const end = o.t + o.dur - 0.3, n = Math.max(1, Math.floor((end - o.t_steady) / 0.16));
          tl.fromTo(heat, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1.7, duration: 0.6, ease: "back.out(2)" }, o.t_steady);
          tl.to(hg, { attr: { y: y(o.to) - 5, height: base - y(o.to) + 5 }, duration: 0.08, yoyo: true, repeat: n * 2 - 1, ease: "sine.inOut" }, o.t_steady + 0.2);
          if (steady) tl.fromTo(steady, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.5)" }, o.t_steady_text ?? o.t_steady + 0.5);
        }
        if (steady) gsap.set(steady, { opacity: 0 });
        tl.to(el, { opacity: 0, y: -24, duration: 0.25, ease: "power2.in" }, o.t + o.dur - 0.25);
      },

      // pressure dial: the needle swings in to o.from, then down to o.to at o.t_drop; the readout counts along and
      // the caption under it switches from o.from_label to o.to_label
      gauge(o) {
        const el = mk("div", "gauge", overlays);
        if (o.title) mk("div", "gg-title", el, markup(o.title));
        const lo = o.min ?? 40, hi = o.max ?? 110, cx = 300, cy = 290, r = 230;
        const ang = (v) => -120 + (240 * (v - lo)) / (hi - lo);
        const pt = (a, rr) => [cx + rr * Math.sin((a * Math.PI) / 180), cy - rr * Math.cos((a * Math.PI) / 180)];
        const arc = (v0, v1, col) => {
          const [x0, y0] = pt(ang(v0), r), [x1, y1] = pt(ang(v1), r), big = ang(v1) - ang(v0) > 180 ? 1 : 0;
          return `<path d="M ${x0} ${y0} A ${r} ${r} 0 ${big} 1 ${x1} ${y1}" fill="none" stroke="${col}" stroke-width="34"/>`;
        };
        let ticks = "";
        for (let v = lo; v <= hi; v += 10) {
          const [x0, y0] = pt(ang(v), r - 30), [x1, y1] = pt(ang(v), r - 56), [tx, ty] = pt(ang(v), r - 92);
          ticks += `<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="#fff" stroke-width="6" stroke-linecap="round"/>
            <text x="${tx}" y="${ty + 12}" text-anchor="middle" class="gg-tk">${v}</text>`;
        }
        const art = mk("div", "gg-art", el);
        art.innerHTML = `<svg viewBox="0 0 600 420" width="600" height="420">
          ${arc(lo, 70, "#FF453A")}${arc(70, 90, "#FFD60A")}${arc(90, hi, "#30D158")}
          ${ticks}
          <g class="gg-needle"><polygon points="${cx - 13},${cy} ${cx + 13},${cy} ${cx},${cy - r + 22}" fill="#fff"/></g>
          <circle cx="${cx}" cy="${cy}" r="26" fill="#111" stroke="#fff" stroke-width="7"/>
        </svg>`;
        const read = mk("div", "gg-read", el);
        const val = mk("div", "gg-val", read);
        const sub = mk("div", "gg-sub", read, markup(o.from_label || ""));
        const fmt = (v, pre) => `${pre}${Math.round(v)}${o.unit ?? "%"}`;
        val.textContent = fmt(o.to, o.prefix ?? "~");
        place(el, o.zone);
        val.textContent = fmt(o.from, "");
        const nd = $(".gg-needle", el), org = `${cx} ${cy}`;
        tl.fromTo(el, { opacity: 0, y: 40, scale: 0.95 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "expo.out" }, o.t);
        tl.fromTo(nd, { rotation: ang(lo), svgOrigin: org }, { rotation: ang(o.from), svgOrigin: org, duration: 0.7, ease: "back.out(1.6)" }, o.t + 0.1);
        const p = { v: o.from };
        tl.to(nd, { rotation: ang(o.to), svgOrigin: org, duration: 0.9, ease: "back.out(1.3)" }, o.t_drop);
        tl.to(p, { v: o.to, duration: 0.9, ease: "power2.out", onUpdate: () => (val.textContent = fmt(p.v, o.prefix ?? "~")) }, o.t_drop);
        tl.set(sub, { innerHTML: markup(o.to_label || "") }, o.t_drop);
        tl.set(val, { className: "gg-val low" }, o.t_drop);
        tl.fromTo(read, { scale: 1 }, { scale: 1.1, duration: 0.12, yoyo: true, repeat: 1 }, o.t_drop + 0.9);
        tl.to(el, { opacity: 0, y: -24, duration: 0.25, ease: "power2.in" }, o.t + o.dur - 0.25);
      },

      // altitude meter: a marker climbs a 0..o.max ruler while the number counts to o.to (o.t .. o.t_end)
      altimeter(o) {
        const el = mk("div", "altimeter", overlays);
        const mx = o.max ?? 4000, top = 30, len = o.len ?? 440, step = o.step ?? 1000;
        const y = (v) => top + len * (1 - v / mx);
        let ticks = "";
        for (let v = 0; v <= mx; v += step / 2) {
          const major = v % step === 0;
          ticks += `<line x1="70" y1="${y(v)}" x2="${major ? 110 : 94}" y2="${y(v)}" stroke="rgba(255,255,255,.8)" stroke-width="${major ? 6 : 4}" stroke-linecap="round"/>`;
          if (major) ticks += `<text x="122" y="${y(v) + 11}" class="al-tk">${v.toLocaleString("en-IN")}</text>`;
        }
        const art = mk("div", "al-art", el);
        art.style.height = len + 60 + "px";
        art.innerHTML = `<svg viewBox="0 0 260 ${len + 60}" width="260" height="${len + 60}">
          <line x1="70" y1="${top - 10}" x2="70" y2="${top + len + 6}" stroke="rgba(255,255,255,.35)" stroke-width="8" stroke-linecap="round"/>
          <line class="al-fill" x1="70" y1="${y(0)}" x2="70" y2="${y(0)}" stroke="#FFD60A" stroke-width="8" stroke-linecap="round"/>
          ${ticks}
          <g class="al-mark"><polygon points="20,${y(0) - 22} 20,${y(0) + 22} 58,${y(0)}" fill="#FFD60A"/></g>
        </svg>`;
        const side = mk("div", "al-side", el);
        if (o.tag) mk("div", "al-tag", side, markup(o.tag));
        const num = mk("div", "al-num", side);
        const v = mk("span", null, num);
        mk("span", "unit", num, esc(o.suffix ?? " m"));
        if (o.label) mk("div", "al-lbl", side, markup(o.label));
        const fmt = (x) => (o.prefix ?? "~") + Math.round(x).toLocaleString("en-IN");
        v.textContent = fmt(o.to);
        place(el, o.zone);
        v.textContent = fmt(0);
        const t1 = o.t_end ?? o.t + 1.2, p = { v: 0 };
        tl.fromTo(el, { opacity: 0, x: -200 }, { opacity: 1, x: 0, duration: 0.45, ease: "expo.out" }, o.t);
        tl.to(p, { v: o.to, duration: t1 - o.t - 0.2, ease: "power2.out", onUpdate: () => (v.textContent = fmt(p.v)) }, o.t + 0.2);
        tl.to($(".al-mark", el), { y: y(o.to) - y(0), duration: t1 - o.t - 0.2, ease: "power2.out" }, o.t + 0.2);
        tl.to($(".al-fill", el), { attr: { y2: y(o.to) }, duration: t1 - o.t - 0.2, ease: "power2.out" }, o.t + 0.2);
        tl.fromTo(num, { scale: 1 }, { scale: 1.1, duration: 0.12, yoyo: true, repeat: 1 }, t1);
        tl.to(el, { opacity: 0, x: -120, duration: 0.3, ease: "power2.in" }, o.t + o.dur - 0.3);
      },

      // pills with a bouncing arrow, e.g. "PRESSURE ↑": o.items[k] = {text, dir: "up"|"down", t}
      chips(o) {
        const el = mk("div", "chips", overlays);
        const rows = o.items.map((it) => {
          const c = mk("div", "chip", el);
          mk("span", "ct", c, markup(it.text));
          const a = mk("span", "ca" + (it.dir === "down" ? " down" : ""), c, it.dir === "down" ? "↓" : "↑");
          return { c, a, it };
        });
        place(el, o.zone);
        tl.set(el, { opacity: 1 }, o.t);
        for (const { c, a, it } of rows) {
          tl.fromTo(c, { opacity: 0, scale: 0.4, y: 40 }, { opacity: 1, scale: 1, y: 0, duration: 0.35, ease: "back.out(2.6)" }, it.t);
          const n = Math.max(1, Math.floor((o.t + o.dur - it.t - 0.7) / 0.3));
          const d = it.dir === "down" ? 10 : -10;
          tl.fromTo(a, { y: 0 }, { y: d, duration: 0.15, yoyo: true, repeat: n * 2 - 1, ease: "sine.inOut" }, it.t + 0.35);
        }
        tl.to(el, { opacity: 0, y: -24, duration: 0.25, ease: "power2.in" }, o.t + o.dur - 0.25);
        gsap.set(el, { opacity: 0 });
      },

      // pressure-cooker cut-away (drawn, not footage): sealed lid + gasket, whistle, water with dal inside. Pressure
      // arrows build from the first item's time, the whistle blows at o.t_whistle; o.items = chips under the drawing
      cooker(o) {
        const el = mk("div", "cooker", overlays);
        if (o.title) mk("div", "ck-title", el, markup(o.title));
        const petals = Array.from({ length: 9 }, (_, k) => {
          const x = 200 + k * 30;
          return `<path d="M ${x - 11} 540 Q ${x} 496 ${x + 11} 540 Z" fill="#3D8BFF" opacity=".9"/><path d="M ${x - 5} 540 Q ${x} 516 ${x + 5} 540 Z" fill="#BFE0FF"/>`;
        }).join("");
        const dal = Array.from({ length: 26 }, (_, k) => {
          const x = 168 + ((k * 53) % 300), y = 392 + ((k * 37) % 70);
          return `<circle cx="${x}" cy="${y}" r="${7 + (k % 3)}" fill="#F2B632" stroke="#C98A12" stroke-width="2"/>`;
        }).join("");
        const arrow = (x, y, rot) => `<g transform="translate(${x} ${y}) rotate(${rot})"><rect x="-7" y="-34" width="14" height="40" rx="5" fill="#FF9F0A"/>
          <polygon points="-20,4 20,4 0,30" fill="#FF9F0A"/></g>`;
        const arrows = [arrow(210, 280, 0), arrow(275, 270, 0), arrow(340, 266, 0), arrow(405, 270, 0), arrow(470, 280, 0),
          arrow(182, 340, 90), arrow(498, 340, -90)].join("");
        const steam = [200, 300, 400].map((x) => `<path d="M ${x} 330 q -12 -18 0 -34 q 12 -18 0 -34" fill="none" stroke="rgba(255,255,255,.7)" stroke-width="7" stroke-linecap="round"/>`).join("");
        const art = mk("div", "ck-art", el);
        art.innerHTML = `<svg viewBox="0 0 640 560" width="800" height="700">
          <defs>
            <linearGradient id="ckMetal" x1="0" x2="1"><stop offset="0" stop-color="#7C838C"/><stop offset=".3" stop-color="#E9EDF1"/>
              <stop offset=".65" stop-color="#B9C0C8"/><stop offset="1" stop-color="#6E757E"/></linearGradient>
            <clipPath id="ckIn"><rect x="150" y="222" width="340" height="248" rx="24"/></clipPath>
          </defs>
          <g class="ck-flame">${petals}</g>
          <rect x="130" y="200" width="380" height="296" rx="42" fill="url(#ckMetal)" stroke="#4B535C" stroke-width="5"/>
          <rect x="150" y="222" width="340" height="248" rx="24" fill="#16202B"/>
          <g clip-path="url(#ckIn)">
            <rect x="150" y="372" width="340" height="110" fill="#2E8FD6"/>
            <rect x="150" y="372" width="340" height="8" fill="#7CC4F5"/>
            ${dal}
            <g class="ck-steam">${steam}</g>
            <g class="ck-arrows">${arrows}</g>
          </g>
          <rect x="520" y="300" width="96" height="30" rx="15" fill="#3A3F47" stroke="#8A929C" stroke-width="4"/>
          <rect x="112" y="176" width="416" height="30" rx="13" fill="#D3D9DF" stroke="#4B535C" stroke-width="5"/>
          <rect x="132" y="204" width="376" height="8" rx="4" fill="#E0463A"/>
          <rect x="520" y="182" width="104" height="24" rx="12" fill="#3A3F47" stroke="#8A929C" stroke-width="4"/>
          <rect x="307" y="146" width="26" height="34" fill="#4B535C"/>
          <g class="ck-whistle"><rect x="290" y="104" width="60" height="48" rx="14" fill="#2B2F36" stroke="#111" stroke-width="3"/>
            <rect x="302" y="88" width="36" height="20" rx="8" fill="#3A3F47"/></g>
          <g class="ck-puff"><circle cx="300" cy="70" r="22" fill="#fff"/><circle cx="330" cy="54" r="28" fill="#fff"/><circle cx="362" cy="70" r="20" fill="#fff"/>
            <circle cx="335" cy="22" r="18" fill="rgba(255,255,255,.8)"/></g>
        </svg>`;
        const chips = mk("div", "ck-chips", el);
        const rows = (o.items || []).map((it) => {
          const c = mk("div", "chip", chips);
          mk("span", "ct", c, markup(it.text));
          const a = mk("span", "ca", c, "↑");
          return { c, a, it };
        });
        place(el, o.zone);
        const arrowsG = $(".ck-arrows", el), puff = $(".ck-puff", el), wh = $(".ck-whistle", el);
        tl.fromTo(el, { opacity: 0, y: 50, scale: 0.95 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "expo.out" }, o.t);
        const end = o.t + o.dur - 0.3;
        tl.fromTo($(".ck-flame", el), { opacity: 0.75 }, { opacity: 1, duration: 0.12, yoyo: true, repeat: 2 * Math.max(1, Math.floor((end - o.t) / 0.24)) - 1, ease: "sine.inOut" }, o.t);
        tl.fromTo($(".ck-steam", el), { y: 0, opacity: 0.3 }, { y: -14, opacity: 0.9, duration: 0.3, yoyo: true, repeat: 2 * Math.max(1, Math.floor((end - o.t) / 0.6)) - 1, ease: "sine.inOut" }, o.t);
        const tp = rows.length ? rows[0].it.t : o.t + 0.6;
        gsap.set(arrowsG, { opacity: 0 });
        tl.to(arrowsG, { opacity: 1, duration: 0.3 }, tp);
        tl.fromTo(arrowsG, { scale: 0.75, svgOrigin: "340 330" }, { scale: 1.12, svgOrigin: "340 330", duration: Math.max(0.6, end - tp - 0.2), ease: "power1.in" }, tp);
        for (const { c, a, it } of rows) {
          tl.fromTo(c, { opacity: 0, scale: 0.4, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: 0.35, ease: "back.out(2.6)" }, it.t);
          const n = Math.max(1, Math.floor((end - it.t - 0.4) / 0.3));
          tl.fromTo(a, { y: 0 }, { y: -10, duration: 0.15, yoyo: true, repeat: n * 2 - 1, ease: "sine.inOut" }, it.t + 0.35);
        }
        gsap.set(puff, { opacity: 0 });
        if (o.t_whistle != null) {
          tl.to(wh, { y: -7, duration: 0.06, yoyo: true, repeat: 7, ease: "sine.inOut" }, o.t_whistle);
          tl.fromTo(puff, { opacity: 0, y: 20, scale: 0.6, svgOrigin: "330 60" }, { opacity: 1, y: -10, scale: 1.2, svgOrigin: "330 60", duration: 0.45, ease: "power2.out" }, o.t_whistle);
          tl.to(puff, { opacity: 0, y: -40, duration: 0.4, ease: "power1.in" }, o.t_whistle + 0.45);
        }
        tl.to(el, { opacity: 0, y: -24, duration: 0.25, ease: "power2.in" }, o.t + o.dur - 0.25);
      },

      flash(o) {
        const el = mk("div", "flash", fx);
        const rise = o.in ?? 0.05;  // 0 = full white on the first frame (flash on a hard cut)
        if (rise > 0) tl.fromTo(el, { opacity: 0 }, { opacity: o.strength ?? 0.85, duration: rise }, o.t);
        tl.fromTo(el, { opacity: o.strength ?? 0.85 }, { opacity: 0, duration: o.dur || 0.3, ease: "power2.out",
                                                         immediateRender: false }, o.t + rise);
      },

      // fade to / from a colour over everything (black by default): "in" s to full, "hold" s, "out" s back to clear.
      // Dip to black between shots, or "out": 0 at the very end to finish on black.
      fade(o) {
        const el = mk("div", "fade", fx);
        if (o.color) el.style.background = o.color;
        const a = o.in ?? 0.3, h = o.hold ?? 0, b = o.out ?? 0.3, peak = o.strength ?? 1;
        if (a > 0) tl.fromTo(el, { opacity: 0 }, { opacity: peak, duration: a, ease: "power1.inOut" }, o.t);
        else tl.set(el, { opacity: peak }, o.t);
        if (b > 0) tl.fromTo(el, { opacity: peak }, { opacity: 0, duration: b, ease: "power1.inOut",
                                                      immediateRender: false }, o.t + a + h);
      },
    };
    R.image = R.media;
    R.video = R.media;

    for (const o of E.overlays) {
      if (!R[o.type]) { console.warn("unknown overlay", o.type); continue; }
      R[o.type](o);
    }

    // ---------------------------------------------------------------- progress bar
    if (E.progress) {
      const p = mk("div", null, fx);
      p.id = "progress";
      tl.fromTo(p, { scaleX: 0 }, { scaleX: 1, duration: E.duration, ease: "none" }, 0);
    }

    tl.set({}, {}, E.duration);
    return tl;
  }

  // index.html registers the timeline (after fonts load, so text is measured correctly)
  window.__buildEdit = build;
})();
