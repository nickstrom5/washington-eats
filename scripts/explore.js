// Washington Eats web app: the iPhone app's guides, search, filters, map and place details, in the browser.
// Same data file as the app (split into core + detail by scripts/make-site.py). No cookies, no trackers;
// saved places and the last guide live in this browser's localStorage only. Adapted from wi-eats/scripts/explore.js.
(() => {
  "use strict";
  const BASE = document.documentElement.dataset.base || "";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem("wae-" + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("wae-" + k, JSON.stringify(v)); } catch { /* private mode */ } },
  };

  // ---------------------------------------------------------------- search (a port of WashingtonEats/Models/Search.swift)
  const typeSyn = { avenue: "ave", av: "ave", street: "st", boulevard: "blvd", road: "rd", drive: "dr", place: "pl", court: "ct",
    parkway: "pkwy", highway: "hwy", lane: "ln", trail: "trl", circle: "cir", terrace: "ter" };
  const syn = { ...typeSyn, north: "n", south: "s", east: "e", west: "w", northeast: "ne", northwest: "nw", southeast: "se", southwest: "sw",
    saint: "st", mount: "mt", fort: "ft" };
  const abbrs = new Set(Object.values(syn)), typeAbbrs = new Set(Object.values(typeSyn));
  const TERIYAKI = 1, PHO = 2, SEAFOOD = 4, DRIVEIN = 8, ESPRESSO = 16;
  const tagPhrases = [["teriyaki", TERIYAKI], ["pho", PHO], ["oysters", SEAFOOD], ["oyster", SEAFOOD], ["drive ins", DRIVEIN], ["drive in", DRIVEIN],
    ["drivein", DRIVEIN], ["espresso stands", ESPRESSO], ["espresso stand", ESPRESSO], ["coffee stand", ESPRESSO]];
  function normalize(s) {
    let t = String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/đ/g, "d");
    t = t.replace(/\b([a-z0-9])\s*&\s*([a-z0-9])\b/g, "$1$2").replace(/&/g, " and ").replace(/['’`]/g, "");
    return t.replace(/[^\p{L}\p{N}]+/gu, " ").trim();
  }
  const normAddr = (s) => normalize(s).split(" ").map((w) => syn[w] || w).join(" ");

  function parse(text) {
    const q = { tokens: [], town: null, townPhrase: null, tag: 0, tagPhrase: null };
    let raw = normalize(text).split(" ").filter(Boolean);
    if (!raw.length) return q;
    let mapped = raw.map((w) => syn[w] || w);
    const find = (phrase) => {
      const p = phrase.split(" ");
      for (let i = 0; i + p.length <= mapped.length; i++) if (p.every((w, k) => mapped[i + k] === w)) return [i, i + p.length];
      return null;
    };
    const cut = ([a, b]) => { const words = raw.slice(a, b).join(" "); raw.splice(a, b - a); mapped.splice(a, b - a); return words; };
    for (const [phrase, tag] of tagPhrases) { const r = find(normalize(phrase)); if (r) { q.tag = tag; q.tagPhrase = cut(r); break; } }
    for (const key of TOWN_KEYS_BY_LENGTH) {
      const r = find(key);
      if (r && !(r[1] < mapped.length && typeAbbrs.has(mapped[r[1]]))) { q.town = TOWN_KEYS[key]; q.townPhrase = cut(r); break; }
    }
    const stop = new Set(["the", "and", "of", "a", "in", "near"]);
    let idx = raw.map((_, i) => i);
    if (idx.some((i) => !stop.has(mapped[i]))) idx = idx.filter((i) => !stop.has(mapped[i]));
    idx.forEach((i, n) => {
      const token = raw[i], isLast = n === idx.length - 1;
      if (syn[token]) { q.tokens.push([` ${syn[token]} `, ` ${token}`]); return; }
      const whole = (abbrs.has(token) && (!isLast || token.length > 1)) || (token.length <= 2 && !isLast);
      const needles = [" " + token + (whole ? " " : "")];
      if (isLast && token.length >= 3) for (const [word, abbr] of Object.entries(typeSyn)) if (word !== token && word.startsWith(token)) needles.push(` ${abbr} `);
      q.tokens.push(needles);
    });
    if (q.tokens.length >= 2 && idx.length && typeAbbrs.has(mapped[idx[idx.length - 1]])) {
      const last = idx[idx.length - 1], prev = idx[idx.length - 2];
      q.tokens.splice(-2, 2, [` ${mapped[prev]} ${mapped[last]} `, ` ${raw[prev]} ${raw[last]}`]);
    }
    return q;
  }
  const qEmpty = (q) => !q.tokens.length && !q.town && !q.tag;
  function matches(p, q) {
    if (q.tag && !(p.g & q.tag)) {
      const stem = normalize(q.tagPhrase || "").replace(/s$/, "");
      if (!stem || !p.nameText.includes(" " + stem)) return false;
    }
    if (q.town && p.c !== q.town && !p.nameText.includes(" " + normalize(q.townPhrase || ""))) return false;
    return q.tokens.every((needles) => needles.some((n) => p.search.includes(n)));
  }
  const nameMatches = (p, q) => q.tokens.length && q.tokens.every((needles) => needles.some((n) => p.nameText.includes(n)));

  // ---------------------------------------------------------------- guides (WashingtonEats/Models/Guide.swift)
  const KCR = { 4: "Excellent", 3: "Good", 2: "Okay", 1: "Needs to Improve" };
  const GUIDES = {
    teriyaki: { title: "Seattle Teriyaki", sub: "Hand-checked teriyaki counters statewide, with what they serve. Seattle-style teriyaki is traced to Toshi Kasahara's 1976 shop; many shops share the name Toshi's, and only one is his.",
      inc: (p) => p.hc & TERIYAKI, sorts: ["nearest", "oldest", "name"] },
    pho: { title: "Phở", sub: "Hand-checked phở shops, from Little Saigon to Spokane", inc: (p) => p.hc & PHO, sorts: ["nearest", "oldest", "name"] },
    drivein: { title: "Drive-In Burgers", sub: "Hand-checked burger stands and drive-ins, Dick's to Zip's", inc: (p) => p.hc & DRIVEIN, sorts: ["nearest", "oldest", "name"] },
    seafood: { title: "Oysters & Seafood", sub: "Hand-checked oyster bars, chowder and fish and chips", inc: (p) => p.hc & SEAFOOD, sorts: ["nearest", "oldest", "name"] },
    honors: { title: "Honors & History", sub: "James Beard finalists and long-running institutions", inc: (p) => p.ip != null, sorts: ["iconic", "oldest", "nearest"], ranked: true },
    oldest: { title: "Oldest Places", sub: "Opening years we could verify, oldest first", inc: (p) => p.f != null, sorts: ["oldest"], ranked: true },
    safety: { title: "Food Safety", sub: "King County only: Public Health – Seattle & King County's official food safety rating, as published. Other counties don't publish ratings in bulk.",
      inc: (p) => p.kr != null, sorts: ["best", "lowest", "nearest"] },
    all: { title: "All Restaurants", sub: "Restaurants, cafés, espresso stands and bars statewide", inc: () => true, sorts: ["name", "nearest"] },
    saved: { title: "Saved", sub: "Places you saved in this browser", inc: (p) => saved.has(p.id), sorts: ["name", "nearest"] },
  };
  const SORT_LABEL = { nearest: "Nearest", oldest: "Oldest first", name: "A to Z", iconic: "Most iconic", best: "Best rating first", lowest: "Lowest rating first" };

  // ---------------------------------------------------------------- state
  let P = [], D = null, CAL = {}, TOWN_KEYS = {}, TOWN_KEYS_BY_LENGTH = [], GENERATED = "", THROUGH = "";
  let here = null, shown = 100, current = [], view = "list";
  const saved = new Set(store.get("saved", []));
  const st = { g: "teriyaki", q: "", sort: "", town: "", cuisine: "", chains: false, p: "" };

  const miles = (a, b) => {
    const r = Math.PI / 180, dLa = (b.la - a.la) * r, dLo = (b.lo - a.lo) * r;
    const h = Math.sin(dLa / 2) ** 2 + Math.cos(a.la * r) * Math.cos(b.la * r) * Math.sin(dLo / 2) ** 2;
    return 3958.8 * 2 * Math.asin(Math.sqrt(h));
  };
  const milesText = (m) => (m < 10 ? m.toFixed(1) : Math.round(m)) + " mi";

  function order() {
    const g = GUIDES[st.g];
    if (st.sort && g.sorts.includes(st.sort)) return st.sort;
    return g.sorts[0];
  }

  function allows(p) {
    if (p.v && st.g !== "saved") return false;            // gas-station counters, stadium stands and the like
    if (st.town && p.c !== st.town) return false;
    if (st.cuisine && p.cu !== st.cuisine) return false;
    if (st.chains && p.ch >= 5) return false;
    return true;
  }

  function list() {
    const g = GUIDES[st.g], q = parse(st.q), o = order();
    if (qEmpty(q) && st.q.trim()) return [];   // typed something, but nothing searchable ("🍜", "!!!")
    let out = P.filter((p) => g.inc(p) && allows(p) && (qEmpty(q) || matches(p, q)));
    const byName = (a, b) => a.n.localeCompare(b.n, "en", { sensitivity: "base" });
    const dist = (p) => (here && p.la != null ? miles(here, p) : Infinity);
    if (o === "nearest" && here) out.sort((a, b) => dist(a) - dist(b) || byName(a, b));
    else if (o === "nearest") out.sort((a, b) => (b.ip ?? -1) - (a.ip ?? -1) || (a.f ?? 9999) - (b.f ?? 9999) || byName(a, b));
    else if (o === "oldest") out.sort((a, b) => (a.f ?? 9999) - (b.f ?? 9999) || byName(a, b));
    else if (o === "iconic") out.sort((a, b) => (b.ip ?? -1) - (a.ip ?? -1) || byName(a, b));
    else if (o === "best" || o === "lowest") {
      const s = o === "best" ? -1 : 1;   // King County's own rating; ties by the latest routine inspection
      const bad = (p) => (p.kq === 1 ? 0 : 1);   // within a rating: satisfactory latest result first when best-first
      out.sort((a, b) => s * ((a.kr ?? 0) - (b.kr ?? 0)) || -s * (bad(a) - bad(b)) || String(b.kd || "").localeCompare(String(a.kd || "")) || byName(a, b));
    } else out.sort(byName);
    if (q.tokens.length && !g.ranked && o !== "best" && o !== "lowest") {       // name matches first when searching
      const named = out.filter((p) => nameMatches(p, q));
      if (named.length && named.length < out.length) { const ids = new Set(named); out = named.concat(out.filter((p) => !ids.has(p))); }
    }
    return out;
  }

  // ---------------------------------------------------------------- rendering
  function chips(p, max) {
    const c = [];
    const jb = p.h & 1 ? "America's Classic" : p.h & 2 ? "James Beard winner" : p.h & 4 ? "James Beard finalist" : p.h & 8 ? "James Beard semifinalist" : null;
    if (jb) c.push(`<span class="tag tag-jb">${jb}</span>`);
    if (p.hc & TERIYAKI) c.push('<span class="tag">Teriyaki</span>');
    if (p.hc & PHO) c.push('<span class="tag tag-sound">Phở</span>');
    if (p.hc & DRIVEIN) c.push('<span class="tag tag-sound">Drive-in</span>');
    if (p.hc & SEAFOOD) c.push('<span class="tag tag-sound">Seafood</span>');
    if (p.ks) c.push('<span class="tag tag-jb">Toshi Kasahara\'s shop</span>');
    if (p.h & 16 && !jb) c.push('<span class="tag tag-plain">Icon</span>');
    if (p.ch >= 5) c.push(`<span class="tag tag-plain">Chain · ${p.ch}</span>`);
    if (p.t === 0 && !p.h && !p.hc) c.push('<span class="tag tag-dash">Listing only</span>');
    return (max ? c.slice(0, max) : c).join("");
  }

  function metric(p, o) {
    if (o === "nearest" && here && p.la != null) return [milesText(miles(here, p)), "away"];
    if ((o === "best" || o === "lowest") && p.kr) return [KCR[p.kr], "King County"];
    if (o === "iconic" && p.ip != null) return [String(Math.round(p.ip)), "iconic pts"];
    if (p.f && st.g !== "all") return [String(p.f), "since"];
    return null;
  }

  function render() {
    const g = GUIDES[st.g], o = order();
    current = list();
    document.querySelectorAll(".ex-guides button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.g === st.g)));
    $("#ex-sub").textContent = g.sub + (st.g === "safety" && THROUGH ? ` Inspections through ${THROUGH}.` : "");
    const sortSel = $("#ex-sort");
    sortSel.innerHTML = g.sorts.map((s) => `<option value="${s}"${s === o ? " selected" : ""}>${SORT_LABEL[s]}</option>`).join("");
    sortSel.disabled = g.sorts.length < 2;
    const filters = [st.town && `in ${st.town}`, st.cuisine && st.cuisine, st.chains && "no chains"].filter(Boolean);
    $("#ex-count").textContent = `${current.length.toLocaleString()} ${current.length === 1 ? "place" : "places"} · ${SORT_LABEL[o]}` + (filters.length ? ` · ${filters.join(", ")}` : "");
    $("#ex-clear").hidden = !filters.length;
    $("#ex-locate").hidden = Boolean(here);
    if (view === "list") renderList(o); else drawMap();
    saveHash();
  }

  function renderList(o) {
    const ol = $("#ex-list");
    const g = GUIDES[st.g];
    if (!current.length) {
      ol.innerHTML = `<li class="ex-empty">${st.g === "saved" ? "Nothing saved yet. Open a place and tap Save to keep it here, in this browser." : "No places match. Try fewer words or clear the filters."}</li>`;
      $("#ex-more").hidden = true;
      return;
    }
    ol.innerHTML = current.slice(0, shown).map((p, i) => {
      const m = metric(p, o);
      const rank = g.ranked ? `<span class="ex-rank${i < 3 ? " top" : ""}" aria-label="Rank ${i + 1}">${i + 1}</span>` : "";
      const second = st.g === "safety" ? [p.a, p.kd && "inspected " + p.kd].filter(Boolean).join(" · ") : (["teriyaki", "pho", "drivein", "seafood"].includes(st.g) ? p.di : "");
      const metricHtml = m ? (m[1] === "King County" ? `<span class="ex-metric"><span class="ex-kc ex-kc-${p.kr}">${esc(m[0])}</span><small>official</small></span>`
        : `<span class="ex-metric"><b>${esc(m[0])}</b><small>${m[1]}</small></span>`) : "";
      return `<li><button class="ex-row" data-i="${p.i}">${rank}<span class="ex-main"><b>${esc(p.n)}</b><span class="ex-town">${esc([p.c, p.cu].filter(Boolean).join(" · "))}</span>${second ? `<span class="ex-town">${esc(second)}</span>` : ""}<span class="ex-chips">${chips(p, 4)}</span></span>${metricHtml}</button></li>`;
    }).join("");
    const left = current.length - shown;
    $("#ex-more").hidden = left <= 0;
    $("#ex-more").textContent = `Show more (${left.toLocaleString()} left)`;
  }

  // ---------------------------------------------------------------- place panel
  const TIER = { 2: "Inspected by King County", 1: "Confirmed listing", 0: "Listing only" };
  const RES = { 1: "Satisfactory: no red critical violations", 2: "Unsatisfactory: at least one red critical violation", 3: "Complete" };

  function rate(p) {
    if (p.t === 2) return null;
    const src = SOURCES[p.s] || "meta";
    const group = src === "meta" ? (p.t === 1 ? "meta_high" : "meta_mid") : (src === "AllThePlaces" || src === "DAC") ? "brand_feed" : null;
    const v = group && CAL.king?.app?.[group]?.official;
    return v == null ? null : `${Math.round(v * 100)}%`;
  }

  function howWeKnow(p) {
    const src = SOURCES[p.s] || "meta";
    if (src === "research") return "On our hand-checked list (checked in Oct 2026 against a 2025 or 2026 source). The open map data didn't list it as a place to eat, so it's placed from its own map listing or street address.";
    if (p.t === 2) return src === "official"
      ? "From King County's food establishment inspection records. The open map data didn't have it, so its location comes from its street address."
      : "Matched to a business King County inspected in the last 18 months.";
    const r = rate(p);
    return (p.t === 1 ? "A high-confidence listing in Overture's open map data." : "A single listing in Overture's open map data, so it may be closed or misfiled.")
      + (r ? ` Checked against King County's inspection records, listings like this matched an inspected business ${r} of the time.` : "")
      + (p.hc ? " It's also on our hand-checked list, checked in Oct 2026 against a 2025 or 2026 source." : "");
  }

  const kv = (k, v) => (v == null || v === "" ? "" : `<div class="ex-kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`);
  const section = (t, body) => `<section class="ex-sec"><h3>${esc(t)}</h3>${body}</section>`;

  function openPlace(p, push = true) {
    st.p = p.id;
    const d = (D && D[p.i]) || {};
    const addr = [p.a, [p.c, p.z].filter(Boolean).join(" ")].filter(Boolean).join(", ");
    const apple = p.la != null
      ? `https://maps.apple.com/?q=${encodeURIComponent(p.n)}&ll=${p.la},${p.lo}`
      : `https://maps.apple.com/?q=${encodeURIComponent(p.n + ", " + addr)}`;
    const dirs = p.la != null ? `https://maps.apple.com/?daddr=${p.la},${p.lo}&dirflg=d` : apple;
    const site = d.w ? (/^https?:/.test(d.w) ? d.w : "https://" + d.w) : null;
    let html = `<button class="ex-close" id="ex-close" aria-label="Close">×</button>
      <p class="ex-kicker">${esc((p.c || "Washington").toUpperCase())}</p>
      <h2 id="ex-pname">${esc(p.n)}</h2>
      <p class="ex-addr">${esc([addr, p.cu].filter(Boolean).join(" · "))}</p>
      ${here && p.la != null ? `<p class="ex-dist">${milesText(miles(here, p))} away</p>` : ""}
      <p class="ex-chips">${chips(p)}</p>
      <div class="ex-actions">
        <a class="btn ex-apple" href="${esc(apple)}" rel="noopener" target="_blank">Ratings, hours &amp; photos · Apple Maps</a>
        <div class="ex-act-row">
          <a href="${esc(dirs)}" rel="noopener" target="_blank">Directions</a>
          ${d.ph ? `<a href="tel:${esc(d.ph.replace(/[^\d+]/g, ""))}">Call</a>` : ""}
          ${site ? `<a href="${esc(site)}" rel="noopener nofollow" target="_blank">Website</a>` : ""}
          <button id="ex-save" aria-pressed="${saved.has(p.id)}">${saved.has(p.id) ? "Saved" : "Save"}</button>
        </div>
      </div>`;
    if (p.hc || d.note || p.di) {
      const kinds = [p.hc & TERIYAKI && "teriyaki", p.hc & PHO && "phở", p.hc & DRIVEIN && "drive-in burgers", p.hc & SEAFOOD && "oysters & seafood"].filter(Boolean);
      html += section("Hand-checked", (d.note ? `<p>${esc(d.note)}</p>` : "") + (p.di ? `<p><b>Serves</b><br>${esc(p.di)}</p>` : "")
        + (p.ks ? `<p><b>History</b><br>Toshi Kasahara opened Toshi's Teriyaki on Roy Street in Seattle in 1976, the shop Seattle-style teriyaki is traced to. This Mill Creek shop is his; the many other shops named Toshi's are not.</p>` : "")
        + (d.src ? `<p><a href="${esc(d.src)}" rel="noopener nofollow" target="_blank">Source: ${esc(d.src.replace(/^https?:\/\/(www\.)?/, "").split("/")[0])}</a></p>` : "")
        + `<p class="ex-fine">${kinds.length ? `Hand-checked for our ${kinds.join(", ")} guide in Oct 2026 against a 2025 or 2026 source: the place's own site, menu or ordering page, or dated local news.` : "Checked in Oct 2026 against a 2025 or 2026 source."} Menus and hours change, so check before you go.</p>`);
    }
    if (p.h || p.f || d.bf) {
      const lines = [...(d.jbf ? d.jbf.split("; ").map((x) => "James Beard: " + x) : []), ...(d.hon ? d.hon.split("; ") : [])];
      html += section("Honors & history", (d.icon ? `<p>${esc(d.icon)}</p>` : "") + (lines.length ? `<ul>${lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : "")
        + (p.f ? kv("Open at this address since", `${p.f} (verified)`) : "") + (d.bf && d.bf !== p.f ? kv("Business founded", `${d.bf} (verified)`) : ""));
    }
    if (d.kc) {
      const k = d.kc;
      html += section("Food safety · King County (official)",
        (k.r ? `<p class="ex-grade"><span class="ex-kc ex-kc-${k.r}">${KCR[k.r]}</span> Public Health – Seattle &amp; King County's rating, as published</p>` : "")
        + kv("Latest routine inspection", k.d) + kv("Result", RES[k.res]) + kv("Red (critical) points", k.red)
        + kv("Routine inspections since 2023", k.n) + (k.n ? kv("With a red critical violation", k.u) : "") + (k.rt ? kv("Return inspections since 2023", k.rt) : "")
        + (k.cl ? kv("Closed by Public Health", k.cl) : "")
        + `<p class="ex-fine">The rating averages a place's last four routine inspections (two for lower-risk places). “Needs to Improve” means closed by Public Health in the last 90 days or several return inspections. An unsatisfactory inspection is not a closure. Inspections through ${esc(THROUGH)}.</p>`);
    }
    html += section("How we know it's here", kv("Listed as", TIER[p.t]) + kv("County", p.co)
      + (p.ch >= 2 ? kv("Locations in Washington", p.ch.toLocaleString()) : "") + `<p class="ex-fine">${esc(howWeKnow(p))}</p>`);
    html += `<p class="ex-app">Save it on your phone: <a class="store-btn" href="${BASE}/#download"><span class="store-label">Get the free iPhone app</span></a></p>`;
    const panel = $("#ex-panel");
    panel.innerHTML = html;
    panel.hidden = false;
    document.body.classList.add("ex-open");
    $("#ex-close").onclick = closePlace;
    $("#ex-save").onclick = (e) => {
      if (saved.has(p.id)) saved.delete(p.id); else saved.add(p.id);
      store.set("saved", [...saved]);
      e.target.textContent = saved.has(p.id) ? "Saved" : "Save";
      e.target.setAttribute("aria-pressed", String(saved.has(p.id)));
      if (st.g === "saved") render();
    };
    panel.scrollTop = 0;
    $("#ex-close").focus();
    if (push) saveHash();
    if (!D) loadDetail().then(() => { if (st.p === p.id) openPlace(p, false); });
  }

  function closePlace() {
    const was = st.p;
    st.p = "";
    $("#ex-panel").hidden = true;
    document.body.classList.remove("ex-open");
    saveHash();
    const row = was && document.querySelector(`.ex-row[data-i="${P.findIndex((p) => p.id === was)}"]`);
    if (row) row.focus();
  }

  // ---------------------------------------------------------------- map (canvas: county outlines + a dot per place)
  let SHAPES = null, cam = null;
  const LAT0 = 47.3, KX = Math.cos(LAT0 * Math.PI / 180);
  const proj = (lo, la) => [(lo + 120) * KX, -(la - LAT0)];

  function fitCam(w, h) {
    const [x0, y0] = proj(-124.8, 49.05), [x1, y1] = proj(-116.9, 45.5);
    const k = Math.min(w / (x1 - x0), h / (y1 - y0)) * 0.95;
    return { k, x: (w - (x1 - x0) * k) / 2 - x0 * k, y: (h - (y1 - y0) * k) / 2 - y0 * k };
  }

  async function drawMap() {
    const cv = $("#ex-map"), wrap = $("#ex-mapwrap");
    const w = wrap.clientWidth, h = wrap.clientHeight, dpr = window.devicePixelRatio || 1;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    if (!cam) cam = fitCam(w, h);
    if (!SHAPES) SHAPES = await fetchJSON(`${BASE}/data/wa_shapes.json`).catch(() => ({ state: [], counties: [] }));
    const c = cv.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h);
    const X = (lo, la) => { const [x, y] = proj(lo, la); return [x * cam.k + cam.x, y * cam.k + cam.y]; };
    const ring = (r) => { r.forEach(([lo, la], i) => { const [x, y] = X(lo, la); i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.closePath(); };
    c.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--surface").trim() || "#fff";
    c.beginPath(); (SHAPES.state || []).forEach((poly) => poly.forEach(ring)); c.fill("evenodd");
    c.strokeStyle = "rgba(79,99,90,.35)"; c.lineWidth = 0.8;
    for (const co of SHAPES.counties || []) { c.beginPath(); co.c.forEach(ring); c.stroke(); }
    const pts = current.filter((p) => p.la != null);
    const r = Math.max(2.2, Math.min(5, 1.6 + cam.k / 120));
    for (const checked of [false, true]) {
      c.fillStyle = checked ? "#f7c948" : "#1f4d3a";
      c.strokeStyle = "#1f4d3a"; c.lineWidth = 1;
      for (const p of pts) {
        if (Boolean(p.hc & 15) !== checked) continue;
        const [x, y] = X(p.lo, p.la);
        if (x < -5 || y < -5 || x > w + 5 || y > h + 5) continue;
        c.beginPath(); c.arc(x, y, checked ? r + 1 : r, 0, 6.2832); c.fill(); if (checked) c.stroke();
      }
    }
    $("#ex-maphint").textContent = pts.length ? `${pts.length.toLocaleString()} places · tap a dot` : "No places to show";
  }

  function nearestDot(px, py) {
    let best = null, bd = 14 * 14;
    for (const p of current) {
      if (p.la == null) continue;
      const [x0, y0] = proj(p.lo, p.la), x = x0 * cam.k + cam.x, y = y0 * cam.k + cam.y;
      const d = (x - px) ** 2 + (y - py) ** 2;
      if (d < bd) { bd = d; best = p; }
    }
    return best;
  }

  function zoomAt(f, px, py) {
    const k = Math.min(Math.max(cam.k * f, 40), 60000);
    const s = k / cam.k;
    cam = { k, x: px - (px - cam.x) * s, y: py - (py - cam.y) * s };
    drawMap();
  }

  function mapEvents() {
    const cv = $("#ex-map");
    const ptrs = new Map();
    let moved = false, pinch0 = null;
    cv.addEventListener("wheel", (e) => { e.preventDefault(); const b = cv.getBoundingClientRect(); zoomAt(e.deltaY < 0 ? 1.25 : 0.8, e.clientX - b.left, e.clientY - b.top); }, { passive: false });
    cv.addEventListener("pointerdown", (e) => { cv.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); moved = false; pinch0 = null; });
    cv.addEventListener("pointermove", (e) => {
      if (!ptrs.has(e.pointerId)) return;
      const prev = ptrs.get(e.pointerId);
      ptrs.set(e.pointerId, [e.clientX, e.clientY]);
      if (ptrs.size === 2) {
        const [a, b] = [...ptrs.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        const r = cv.getBoundingClientRect();
        if (pinch0) zoomAt(d / pinch0, (a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top);
        pinch0 = d; moved = true; return;
      }
      const dx = e.clientX - prev[0], dy = e.clientY - prev[1];
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      cam.x += dx; cam.y += dy; drawMap();
    });
    const up = (e) => {
      ptrs.delete(e.pointerId);
      if (!moved && ptrs.size === 0) {
        const b = cv.getBoundingClientRect(), p = nearestDot(e.clientX - b.left, e.clientY - b.top);
        if (p) openPlace(p);
      }
      if (ptrs.size < 2) pinch0 = null;
    };
    cv.addEventListener("pointerup", up);
    cv.addEventListener("pointercancel", (e) => ptrs.delete(e.pointerId));
    $("#ex-zin").onclick = () => zoomAt(1.6, cv.clientWidth / 2, cv.clientHeight / 2);
    $("#ex-zout").onclick = () => zoomAt(0.625, cv.clientWidth / 2, cv.clientHeight / 2);
    window.addEventListener("resize", () => { if (view === "map") drawMap(); });
  }

  function centerOn(pt) {
    const cv = $("#ex-map"), w = cv.clientWidth, h = cv.clientHeight;
    const k = 4000, [x, y] = proj(pt.lo, pt.la);
    cam = { k, x: w / 2 - x * k, y: h / 2 - y * k };
  }

  // ---------------------------------------------------------------- data, URL state, controls
  let SOURCES = [];
  async function fetchJSON(url) { const r = await fetch(url); if (!r.ok) throw new Error(r.status + " " + url); return r.json(); }
  let detailPromise = null;
  function loadDetail() {
    detailPromise ||= fetchJSON(`${BASE}/data/detail.json`).then((d) => { D = d; }).catch(() => { D = {}; });
    return detailPromise;
  }

  async function load() {
    const d = await fetchJSON(`${BASE}/data/core.json`);
    GENERATED = d.generated; THROUGH = d.records_through || ""; CAL = d.calibration || {}; SOURCES = d.sources || [];
    const C = d.cols, n = C.id.length, towns = new Map();
    P = new Array(n);
    for (let i = 0; i < n; i++) {
      const city = C.c[i] == null ? null : d.cities[C.c[i]], cu = d.cuisines[C.cu[i]], brand = C.b[i] == null ? null : d.brands[C.b[i]];
      const co = C.co[i] == null ? null : d.counties[C.co[i]];
      const p = { i, id: C.id[i], n: C.n[i], c: city, co, cu, t: C.t[i], s: C.s[i], a: C.a[i], z: C.z[i], la: C.la[i], lo: C.lo[i],
        ch: C.ch[i] || 1, v: C.v[i] === 1, g: C.g[i] || 0, hc: C.hc[i] || 0, ip: C.ip[i], f: C.f[i], h: C.h[i] || 0, ks: C.ks[i] === 1,
        di: C.di[i], kr: C.kr[i], kd: C.kd[i], kq: C.kq[i] };
      p.search = " " + normalize([p.n, city, co, p.z, cu, brand, p.di].filter(Boolean).join(" ")) + " " + normAddr(p.a || "") + " ";
      p.nameText = " " + normalize([p.n, brand].filter(Boolean).join(" ")) + " ";
      P[i] = p;
      if (city && !p.v) towns.set(city, (towns.get(city) || 0) + 1);
    }
    const byCount = [...towns.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    for (const [name] of byCount) { const k = normAddr(name); if (!(k in TOWN_KEYS)) TOWN_KEYS[k] = name; }
    TOWN_KEYS_BY_LENGTH = Object.keys(TOWN_KEYS).sort((a, b) => b.length - a.length);
    $("#ex-town").innerHTML = '<option value="">All towns</option>' + [...towns.keys()].sort((a, b) => a.localeCompare(b)).map((t) => `<option>${esc(t)}</option>`).join("");
    const cuis = new Map();
    for (const p of P) if (!p.v) cuis.set(p.cu, (cuis.get(p.cu) || 0) + 1);
    $("#ex-cuisine").innerHTML = '<option value="">All kinds</option>' + [...cuis.entries()].sort((a, b) => b[1] - a[1]).map(([c, k]) => `<option value="${esc(c)}">${esc(c)} (${k.toLocaleString()})</option>`).join("");
  }

  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    st.g = GUIDES[h.get("g")] ? h.get("g") : store.get("guide", "teriyaki");
    if (!GUIDES[st.g]) st.g = "teriyaki";
    st.q = h.get("q") || ""; st.town = h.get("town") || ""; st.cuisine = h.get("kind") || ""; st.chains = h.get("chains") === "1";
    st.sort = h.get("sort") || ""; st.p = h.get("p") || "";
  }
  function saveHash() {
    const h = new URLSearchParams();
    h.set("g", st.g);
    if (st.q) h.set("q", st.q); if (st.town) h.set("town", st.town); if (st.cuisine) h.set("kind", st.cuisine);
    if (st.chains) h.set("chains", "1"); if (st.sort) h.set("sort", st.sort); if (st.p) h.set("p", st.p);
    history.replaceState(null, "", "#" + h.toString());
    store.set("guide", st.g);
  }

  function locate() {
    if (!navigator.geolocation) { $("#ex-locmsg").textContent = "This browser can't share its location."; return; }
    $("#ex-locmsg").textContent = "Finding you…";
    navigator.geolocation.getCurrentPosition((pos) => {
      here = { la: pos.coords.latitude, lo: pos.coords.longitude };
      const outside = here.la < 45.5 || here.la > 49.05 || here.lo < -124.9 || here.lo > -116.9;
      $("#ex-locmsg").textContent = outside ? "You're outside Washington, so distances are from where you are now. Your location stays in this browser."
        : "Sorted by distance from you. Your location stays in this browser.";
      st.sort = GUIDES[st.g].sorts.includes("nearest") ? "nearest" : st.sort;
      if (view === "map" && !outside) centerOn(here);
      shown = 100; render();
    }, () => { $("#ex-locmsg").textContent = "Location is off for this site. Allow it in your browser settings to sort by distance."; },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  }

  function setView(v) {
    view = v;
    document.querySelectorAll(".ex-view button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === v)));
    $("#ex-listwrap").hidden = v !== "list";
    $("#ex-mapwrap").hidden = v !== "map";
    render();
  }

  function controls() {
    document.querySelectorAll(".ex-guides button").forEach((b) => b.onclick = () => { st.g = b.dataset.g; st.sort = ""; shown = 100; render(); });
    let t = null;
    $("#ex-q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { st.q = e.target.value; shown = 100; render(); }, 120); });
    $("#ex-sort").onchange = (e) => { st.sort = e.target.value; if (st.sort === "nearest" && !here) locate(); shown = 100; render(); };
    $("#ex-town").onchange = (e) => { st.town = e.target.value; shown = 100; render(); };
    $("#ex-cuisine").onchange = (e) => { st.cuisine = e.target.value; shown = 100; render(); };
    $("#ex-chains").onchange = (e) => { st.chains = e.target.checked; shown = 100; render(); };
    $("#ex-clear").onclick = () => { st.town = st.cuisine = ""; st.chains = false; syncInputs(); shown = 100; render(); };
    $("#ex-locate").onclick = locate;
    $("#ex-more").onclick = () => { shown += 200; renderList(order()); };
    document.querySelectorAll(".ex-view button").forEach((b) => b.onclick = () => setView(b.dataset.v));
    $("#ex-list").addEventListener("click", (e) => { const b = e.target.closest(".ex-row"); if (b) openPlace(P[+b.dataset.i]); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && st.p) closePlace(); });
    // a link or an edited address bar changing the hash (our own updates use replaceState, which doesn't fire this)
    window.addEventListener("hashchange", () => {
      readHash(); syncInputs(); shown = 100; render();
      const p = st.p && P.find((x) => x.id === st.p);
      if (p) openPlace(p, false); else if (!$("#ex-panel").hidden) closePlace();
    });
    mapEvents();
  }
  function syncInputs() {
    $("#ex-q").value = st.q; $("#ex-town").value = st.town; $("#ex-cuisine").value = st.cuisine; $("#ex-chains").checked = st.chains;
  }

  (async () => {
    readHash();
    try { await load(); } catch (e) { $("#ex-count").textContent = "The restaurant list couldn't load. Refresh to try again."; return; }
    syncInputs(); controls();
    $("#ex-app").hidden = false;
    $("#ex-loading").hidden = true;
    render();
    const open = st.p && P.find((p) => p.id === st.p);
    if (open) { await loadDetail(); openPlace(open, false); }
    ("requestIdleCallback" in window ? requestIdleCallback : setTimeout)(() => loadDetail());
  })();
})();
