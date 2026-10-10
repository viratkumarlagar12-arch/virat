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
            tl.fromTo(s, { opacity: 0, scale: 0.45, y: 26 }, { opacity: 1, scale: 1, y: 0, duration: 0.13, ease: "back.out(3)" }, w.t0);
            if (!w.hl) {
              tl.set(s, { color: T.active }, w.t0);
              tl.set(s, { color: T.vars["--cap-color"] }, Math.min(w.t1, ch.t1 - 0.01));
            }
            tl.fromTo(inner, { scale: 1 }, { scale: w.hl ? 1.16 : 1.08, duration: 0.09, ease: "power2.out" }, w.t0);
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
          mk("span", "tx", s, esc(w.w));
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
        const btn = mk("div", "btn", el, `<span>🔔</span><span class="lbl">${esc(o.button || "SUBSCRIBE")}</span>`);
        const lbl = $(".lbl", btn);
        const cur = mk("div", "cursor", el, "👆");
        place(el, o.zone);
        const bx = btn.offsetLeft + btn.offsetWidth * 0.62, by = btn.offsetTop + btn.offsetHeight * 0.55;
        Object.assign(cur.style, { left: bx + "px", top: by + "px" });
        tl.fromTo(el, { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.45, ease: "back.out(2)" }, o.t);
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

      flash(o) {
        const el = mk("div", "flash", fx);
        tl.fromTo(el, { opacity: 0 }, { opacity: o.strength ?? 0.85, duration: 0.05 }, o.t);
        tl.to(el, { opacity: 0, duration: o.dur || 0.3, ease: "power2.out" }, o.t + 0.05);
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
