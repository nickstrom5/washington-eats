"""One-time port of wi-eats/site/index.html (read-only reference) to Washington -> site/index.html. Re-run from a fresh copy."""
import re, sys
p = "site/index.html"
s = open(p).read()
R = []
def rep(a, b, count=1):
    global s
    n = s.count(a)
    if n < 1:
        sys.exit(f"MISSING: {a[:100]!r}")
    if count == 1 and n > 1:
        sys.exit(f"AMBIGUOUS ({n}): {a[:100]!r}")
    s = s.replace(a, b)

# ---- head, palette
rep('<title>Wisconsin Restaurant Leaderboard</title>', '<title>Washington Restaurant Leaderboard</title>')
rep('content="Every restaurant in Wisconsin, ranked on ratings, popularity, fish fry, supper clubs, custard, value and estimated sales."',
    'content="Every restaurant in Washington State, ranked on ratings, popularity, teriyaki, phở, King County food safety ratings, value and estimated sales."')
rep('/* Packers: green #203731, gold #FFB612, white. Light-only by design; gold is a fill with green text on it, never text on white. */',
    '/* Provisional Washington landscape palette (the app palette is Nick\'s call): evergreen #1F4D3A (9.6:1 on white), Puget Sound blue #1B5E7A,\n     apple red #B3262E (6.5:1, white text on it). Variable names kept from the Wisconsin page: --green is evergreen, --gold is the red accent. */')
rep('--ink:#14241D; --ink-2:#2E4238; --muted:#53665B; --rule:#DAE3DD; --rule-2:#B6C6BC;', '--ink:#13231C; --ink-2:#2B4038; --muted:#4F635A; --rule:#D8E2DD; --rule-2:#B3C4BC;')
rep('--green:#203731; --green-2:#2D5242; --gold:#FFB612; --gold-soft:#FFE7A8; --on-gold:#203731;',
    '--green:#1F4D3A; --green-2:#1B5E7A; --gold:#B3262E; --gold-soft:#F7DEE0; --on-gold:#FFFFFF; --sound:#1B5E7A;')
rep('.tab.wi{border-color:#D9A21A;background:#FFF9EA}', '.tab.wi{border-color:#1B5E7A;background:#EAF3F7}')
rep('.chips.wi .chip[aria-pressed="false"]{background:#FFF9EA;border-color:#D9A21A}', '.chips.wi .chip[aria-pressed="false"]{background:#EAF3F7;border-color:#1B5E7A}')
rep('.badge.sc{background:var(--gold-soft);color:var(--on-gold)}', '.badge.sc{background:#EAF3F7;color:#123F52;border:1px solid #9CC3D3}')
rep('.g-A{background:#12733A} .g-B{background:#4B7A1B} .g-C{background:#F2B01E;color:#2B1D00} .g-D{background:#E8804F;color:#2B1000} .g-F{background:#C1302F}',
    '.g-A{background:#12733A} .g-B{background:#4B7A1B} .g-C{background:#F2B01E;color:#2B1D00} .g-D{background:#E8804F;color:#2B1000} .g-F{background:#C1302F}\n'
    '.kcr{display:inline-block;padding:2px 8px;border-radius:999px;font:700 13px/1.4 var(--body);white-space:nowrap}\n'
    '.r-4{background:#12733A;color:#fff} .r-3{background:#4B7A1B;color:#fff} .r-2{background:#F2B01E;color:#2B1D00} .r-1{background:#C1302F;color:#fff}\n'
    '.ridge{display:block;width:100%;height:34px;margin:-6px 0 -4px;color:var(--green)}')
rep('.head{margin:0 -16px;border-top:10px solid var(--green)}', '.head{margin:0 -16px;border-top:10px solid var(--green)}\n.hmid{background:linear-gradient(#fff,#fff) padding-box}')
# ---- header copy (one Washington element: a Rainier ridgeline over the evergreen band)
rep('<p class="kicker" id="kicker">Wisconsin · map listings as of Sep 2026</p>', '<p class="kicker" id="kicker">Washington State · map listings as of Sep 2026</p>')
rep('<h1 id="h1">Every Wisconsin restaurant, <span class="count">ranked</span></h1>', '<h1 id="h1">Every Washington restaurant, <span class="count">ranked</span></h1>')
rep('<p class="lede" id="lede">Supper clubs, taverns, custard stands, Friday fish fries and the places in between, from Superior to Kenosha. Each one is ranked on ratings, popularity, value and estimated sales, with Wisconsin\'s own boards for fish fry, supper clubs, custard and cheese curds. Flip any leaderboard to see the bottom.</p>',
    '<p class="lede" id="lede">Teriyaki counters, phở shops, drive-ins, espresso stands and the places in between, from Bellingham to Walla Walla. Each one is ranked on ratings, popularity, value and estimated sales, with Washington boards for teriyaki and phở and King County\'s official food safety ratings. Flip any leaderboard to see the bottom.</p>')
rep('<header class="head">\n  <div class="hmid"><div class="inner">', '<header class="head">\n  <svg class="ridge" viewBox="0 0 1200 34" preserveAspectRatio="none" aria-hidden="true"><path d="M0 34 L0 26 L120 22 L210 25 L300 18 L380 21 L470 14 L520 16 L585 6 L612 2 L640 5 L700 13 L760 11 L850 19 L930 16 L1010 22 L1100 19 L1200 24 L1200 34 Z" fill="currentColor"/><path d="M585 6 L612 2 L640 5 L622 9 L612 7 L600 10 Z" fill="#fff" opacity=".9"/></svg>\n  <div class="hmid"><div class="inner">')
# ---- filters
rep('<select id="city"><option value="">All of Wisconsin</option></select>', '<select id="city"><option value="">All of Washington</option></select>')
rep('<span class="flabel" id="l-tags">Wisconsin classics</span>', '<span class="flabel" id="l-tags">Washington classics</span>')
rep('Only confirmed places (on a Milwaukee or Dane County license list, or in two sources)', 'Only confirmed places (inspected by King County, or in two sources)')
rep('<summary>WI Score recipe:', '<summary>WA Score recipe:')
rep('Each ingredient is a 0–100 percentile across Wisconsin.', 'Each ingredient is a 0–100 percentile across Washington.')
rep('placeholder="Search name, town, street, zip, “fish fry”…"', 'placeholder="Search name, town, street, zip, “teriyaki”…"')
rep('"Search name, town, street, zip, “fish fry”…"', '"Search name, town, street, zip, “teriyaki”…"')
# ---- JS constants
rep('const TAGS = [["supper","Supper clubs",1],["fishfry","Fish fry",2],["custard","Frozen custard",8],["curds","Cheese curds",4]];',
    'const TAGS = [["teriyaki","Teriyaki",1],["pho","Phở",2],["oysters","Oysters & seafood",4],["drivein","Drive-ins",8],["espresso","Espresso stands",16]];\n'
    'const KCR = {4:"Excellent", 3:"Good", 2:"Okay", 1:"Needs to Improve"};')
rep('const JUR = ["", "City of Milwaukee", "Public Health Madison & Dane County"];\n', '')
rep('const SRCNAME = {meta:"Meta (Facebook)", AllThePlaces:"the chain\'s own store list (AllThePlaces)", DAC:"a chain store feed (DAC)", official:"the license list",\n  research:"our verified list, placed with its Google listing",',
    'const SRCNAME = {meta:"Meta (Facebook)", AllThePlaces:"the chain\'s own store list (AllThePlaces)", DAC:"a chain store feed (DAC)", official:"King County\'s inspection records",\n  research:"our hand-checked list, placed on its street address",')
s = s.replace("WI_BOUNDS", "WA_BOUNDS")
rep('WA_BOUNDS = a[0] < a[1] ? a : [-92.9, -86.8, 42.49, 47.08];', 'WA_BOUNDS = a[0] < a[1] ? a : [-124.8, -116.9, 45.54, 49.0];')
rep('const w = c.clientWidth || 600, h = Math.round(w / 0.95);', 'const w = c.clientWidth || 600, h = Math.round(w / 1.45);')
rep('fetchJSON("wi_shapes.json")', 'fetchJSON("wa_shapes.json")')
rep('fetchJSON("wi_detail.json")', 'fetchJSON("wa_detail.json")')
rep('fetchJSON("wisconsin.json")', 'fetchJSON("washington.json")')
s = s.replace('localStorage.getItem("wi-eats")', 'localStorage.getItem("wa-eats")').replace('localStorage.setItem("wi-eats"', 'localStorage.setItem("wa-eats"')
# ---- boards
a = s.index('const B = [')
b = s.index('];\nconst board = () =>')
boards = r'''const B = [
  {id:"overall", tab:"WA Score", top:"Top WA Score", bottom:"Lowest WA Score", metric:"WA Score", val:r=>r.score,
   sub:()=>"A blend of rating, popularity, value and estimated profit, weighted by the WA Score recipe in the filters. Places missing some data are pulled toward 40, a little below the middle.",
   show:r=>[Math.round(r.score), "WA Score"]},
  {id:"rating", tab:"Rating", top:"Highest rated", bottom:"Lowest rated", metric:"rating", val:r=>r.bayes, need:(r,d)=>r.reviews >= (d==="top"?15:40),
   sub:"Google star rating as of the Sep 2021 snapshot, adjusted for review count so a 5.0 from three friends doesn't beat a 4.8 from 3,000 strangers.",
   show:r=>[stars(r.rating), revs(r)+(r.reviews === 1 ? " review" : " reviews")+" ('21)"], dup:"rating"},
  {id:"popular", tab:"Popularity", top:"Most popular", bottom:"Least popular", metric:"reviews", val:r=>r.reviews, need:r=>r.reviews!=null,
   sub:"Total Google reviews as of Sep 2021: the best public stand-in for how many people walk through the door. Places opened since aren't in the snapshot, and the snapshot caps counts at 9,998 (shown as 9,998+).",
   show:r=>[revs(r), (r.reviews === 1 ? "review" : "reviews")+" ('21) · "+stars(r.rating)], dup:"rating"},
  {id:"gems", tab:"Hidden gems", top:"Hidden gems", bottom:"Popular but panned", metric:"rating", val:r=>r.gem, need:(r,d)=> d==="top" ? (r.reviews>=20 && r.reviews<=250 && r.chain_n<5) : r.reviews>=600,
   sub:"Top: independents with 20–250 reviews and great ratings. Bottom: places with 600+ reviews and the lowest ratings. Both from the Sep 2021 snapshot.",
   show:r=>[stars(r.rating), revs(r)+(r.reviews === 1 ? " review" : " reviews")+" ('21)"], dup:"rating"},
  {id:"teriyaki", wi:true, tab:"Teriyaki", top:"Top teriyaki", bottom:"Lowest-rated teriyaki", metric:"rating", val:r=>r.bayes, need:(r,d)=>(r.tags & 1) && r.reviews >= (d==="top"?10:30),
   sub:"Teriyaki shops statewide: places named teriyaki, plus the ones on our hand-checked guide (marked Teriyaki ✓, each confirmed open and serving teriyaki with a 2025–26 source). Ranked by Google rating (Sep 2021), adjusted for review count.",
   show:r=>[stars(r.rating), revs(r)+(r.reviews === 1 ? " review" : " reviews")+" ('21)"], dup:"rating"},
  {id:"pho", wi:true, tab:"Phở", top:"Top phở", bottom:"Lowest-rated phở", metric:"rating", val:r=>r.bayes, need:(r,d)=>(r.tags & 2) && r.reviews >= (d==="top"?10:30),
   sub:"Places with phở in the name, statewide. Ranked by Google rating (Sep 2021), adjusted for review count.",
   show:r=>[stars(r.rating), revs(r)+(r.reviews === 1 ? " review" : " reviews")+" ('21)"], dup:"rating"},
  {id:"iconic", tab:"Iconic", top:"Most iconic", bottom:"Least iconic", metric:"iconic points", val:r=>r.s_icon, need:r=>r.s_icon!=null,
   sub:"Only places on our hand-verified list: James Beard finalists and semifinalists (named as such, never as winners) and Washington's oldest restaurants and bars still open. Points for honors, years open (verified year at this address) and how many people know it. There is no MICHELIN Guide for Washington State.",
   show:r=>[Math.round(r.s_icon), "iconic pts" + (r.founded ? " · since " + r.founded : "")]},
  {id:"value", tab:"Value", top:"Best bang for buck", bottom:"Worst value", metric:"value score", val:r=>r.value_raw, need:r=>r.rating!=null,
   sub:"Rating (2021) relative to price level: a 4.7 at $ beats a 4.7 at $$$.",
   show:r=>[stars(r.rating)+" "+dollars(r.price)+(r.price_est?ESTTAG:""), "value "+Math.round(r.i_value)+" · rating '21"], dup:"rating"},
  {id:"price", tab:"Price", top:"Priciest", bottom:"Cheapest", metric:"price", val:r=>r.spend,
   sub:"Google price level (filled in from the chain or cuisine when missing, and marked est.) with typical spend per person. Within a price level, ties are ordered by WA Score.",
   show:r=>[dollars(r.price)+(r.price_est?ESTTAG:""), "~$"+r.spend+"/person "+ESTTAG]},
  {id:"sales", tab:"Sales", top:"Highest sales", bottom:"Lowest sales", metric:"sales", val:r=>r.rev, need:(r,d)=>r.rev!=null && (d==="top" || r.rev_src!=="model-low"), est:true,
   sub:d=>`Estimated yearly sales. Locations of chains with a published average (${META.model?.n_chains ?? "40+"} brands) use that average scaled by how busy the location is; independents use a model.` + (d==="bottom" ? " This end leaves out places with no review data (their figures are rough placeholders). The model never goes below $100K a year, so the very bottom is a tie, ordered by WA Score." : ""),
   show:r=>[money(r.rev), "sales/yr · " + src(r)], dup:"sales"},
  {id:"profit", tab:"Profit", top:"Most profitable", bottom:"Least profitable", metric:"profit", val:r=>r.profit, need:(r,d)=>r.profit!=null && (d==="top" || r.rev_src!=="model-low"), est:true,
   sub:d=>"Estimated yearly pre-tax profit: estimated sales × a typical margin for the segment, nudged by how well-loved the place is." + (d==="bottom" ? " This end leaves out places with no review data (their figures are rough placeholders). The sales model never goes below $100K a year, so the very bottom is mostly places at that floor, ordered by margin and then WA Score." : ""),
   show:r=>[money(r.profit), "profit/yr "+ESTTAG]},
  {id:"food", tab:"Food cost", top:"Biggest food bill", bottom:"Smallest food bill", metric:"food bill", val:r=>r.rev*r.food_cost/100, need:(r,d)=>r.rev!=null && (d==="top" || r.rev_src!=="model-low"), est:true,
   sub:d=>"Estimated yearly food purchases: estimated sales × the typical food-cost share for the cuisine (steak ~38%, seafood ~36%, pizza ~26%)." + (d==="bottom" ? " This end leaves out places with no review data. The sales model never goes below $100K a year, so the very bottom is mostly places at that floor." : ""),
   show:r=>[money(r.rev*r.food_cost/100), r.food_cost+"% food cost "+ESTTAG]},
  {id:"safety", tab:"Food safety", top:"Excellent first (King County)", bottom:"Needs to Improve first (King County)", metric:"official rating", val:r=>r.kc_r, need:r=>r.kc_r!=null,
   tie:(a,b,d)=> d==="top" ? ((a.kc_avg ?? 99) - (b.kc_avg ?? 99)) : ((b.kc_avg ?? -1) - (a.kc_avg ?? -1)),
   sub:()=>`King County only: Public Health – Seattle & King County's official food safety rating, shown as published (Excellent, Good, Okay, Needs to Improve). It averages the red-critical points of a place's last four routine inspections (two for lower-risk places). Needs to Improve means closed by Public Health in the last 90 days or needing several return inspections. Within a rating, places are ordered by their average red points per routine inspection since 2023 (our ordering, from the same records). Inspections through ${esc(META.records_through || "")}.`,
   show:r=>[`<span class="kcr r-${r.kc_r}">${KCR[r.kc_r]}</span>`, `official rating · ${r.kc_avg == null ? "—" : r.kc_avg} red pts/inspection avg`], dup:"kc"},
'''
s = s[:a] + boards + s[b:]
# ---- badges and rows
rep('  if ((r.tags & 1) && !/supper ?club/i.test(r.name)) h += `<span class="badge sc">Supper club</span>`;',
    '  if (r.hc & 1) h += `<span class="badge sc" title="On our hand-checked teriyaki guide (2025–26 source)">Teriyaki ✓</span>`;\n'
    '  else if (r.hc & 128) h += `<span class="badge sc" title="On our hand-checked list (2025–26 source)">Checked ✓</span>`;')
rep('  if (r.ff_n >= 3 && b.id !== "fishfry") bits.push(`<span>${r.ff_n} <i>fish fry mentions</i></span>`);\n', '')
rep('  if (r.grade) bits.push(`<span class="${dup("grade")}" title="Our grade from Dane County inspection results, not an official grade"><span class="grade sm g-${r.grade}">${r.grade}</span> <i>our inspection grade</i></span>`);',
    '  if (r.kc_r) bits.push(`<span class="${dup("kc")}" title="King County\'s official food safety rating"><span class="kcr r-${r.kc_r}" style="font-size:11.5px;padding:1px 6px">${KCR[r.kc_r]}</span> <i>KC official</i></span>`);')
rep('  if (S.board !== "overall" && r.score != null) bits.push(`<span>${Math.round(r.score)} <i>WI Score</i></span>`);',
    '  if (S.board !== "overall" && r.score != null) bits.push(`<span>${Math.round(r.score)} <i>WA Score</i></span>`);')
# ---- search phrases
rep('''const TAG_PH = [["friday fish fry","fishfry"],["fish fries","fishfry"],["fish fry","fishfry"],["fishfry","fishfry"],["supper clubs","supper"],["supper club","supper"],
  ["supperclub","supper"],["frozen custard","custard"],["custard","custard"],["cheese curds","curds"],["cheese curd","curds"],["curds","curds"]].map(([p, t]) => [norm(p), t]);''',
    '''const TAG_PH = [["teriyaki","teriyaki"],["teriyakis","teriyaki"],["pho","pho"],["oysters","oysters"],["oyster","oysters"],["drive ins","drivein"],["drive in","drivein"],
  ["drivein","drivein"],["espresso stands","espresso"],["espresso stand","espresso"],["coffee stands","espresso"],["coffee stand","espresso"]].map(([p, t]) => [norm(p), t]);''')
rep('  // "fish fry", "supper club", "custard", "cheese curds" mean the Wisconsin tags, not words in a name', '  // "teriyaki", "pho", "oysters", "drive in", "espresso stand" mean the Washington tags, not words in a name')
rep('No places match “${esc(S.q.trim())}” in Wisconsin.', 'No places match “${esc(S.q.trim())}” in Washington.')
rep('The WI Score recipe is empty.', 'The WA Score recipe is empty.')
rep('if (pool.length && board().id === "clean") return `${plural(pool.length, "place matches", "places match")} ${what}, but inspection results are only published for Dane County (Madison and its suburbs). ${f.length ? undo + " to see them." : ""}`;',
    'if (pool.length && board().id === "safety") return `${plural(pool.length, "place matches", "places match")} ${what}, but official food safety ratings are only published in bulk for King County (Seattle and its suburbs). ${f.length ? undo + " to see them." : ""}`;')
rep(': "All of Wisconsin"}</option>`', ': "All of Washington"}</option>`')
rep('["score","Avg WI Score","r"]', '["score","Avg WA Score","r"]')
rep('`Random pick: ${r.name}, ${r.city || "Wisconsin"}.`', '`Random pick: ${r.name}, ${r.city || "Washington"}.`')
# ---- calibration note per place
a = s.index('function calibNote(r) {')
b = s.index('function sigCard(')
s = s[:a] + r'''function calibNote(r) {
  const c = META.calibration || {}, g = k => [c.king?.artifact?.[k]].filter(Boolean);
  const range = k => { const v = g(k).map(x => x.official); if (!v.length) return null; return pctTxt(v[0]); };
  const feed = r.src === "AllThePlaces" || r.src === "DAC", checked = r.hc ? " It's also on our hand-checked list, confirmed open with a 2025–26 source." : "";
  if (r.src === "research") return "This place isn't in the map listings as a place to eat. It's on our hand-checked list, confirmed open with a 2025–26 source, and placed on its street address.";
  if (r.tier === 2) return (r.src === "official" ? "This place comes straight from King County's food establishment inspection records. The map listings we use didn't have it, so its location comes from its street address." : "Matched to a business King County inspected in the last 18 months, so it's confirmed as operating.") + checked;
  const via = feed ? (r.tier === 1 ? "brand feed + Google 2021" : "brand feed only") : r.src === "meta" ? (r.tier === 1 ? "Meta + open in Google 2021" : "Meta only") : null;
  const rate = via ? range(via) : null, kind = feed ? "chain store-list listings" : "listings";
  if (!via) return "Kept because it's on our hand-checked list (2025–26 source), even though its only map listing comes from a source that's usually unreliable.";
  if (r.tier === 1) return `Found in two independent sources: a map listing and Google's 2021 data. Checked against King County's inspection records, ${kind} like this matched an inspected business ${rate || "most"} of the time.` + checked;
  return `Found in one map source only. Checked against King County's inspection records, single-source ${kind} like this matched an inspected business ${rate || "less than half"} of the time, so this one may be closed or misfiled.` + checked;
}
''' + s[b:]
# ---- drawer
rep('const gq = encodeURIComponent(`${r.name} ${r.addr || ""} ${r.city || ""} WI`);', 'const gq = encodeURIComponent(`${r.name} ${r.addr || ""} ${r.city || ""} WA`);')
rep('const heroLbl = r.score == null ? (weightTotal ? "No WI Score: not enough data" : "WI Score recipe is empty")', 'const heroLbl = r.score == null ? (weightTotal ? "No WA Score: not enough data" : "WA Score recipe is empty")')
rep('`WI Score · #${fmtN(ri+1)} of ${fmtN(L.length)} with your filters (ignoring search)` : "WI Score · outside your current filters";',
    '`WA Score · #${fmtN(ri+1)} of ${fmtN(L.length)} with your filters (ignoring search)` : "WA Score · outside your current filters";')
rep('<h3>Category scores (percentile vs. all Wisconsin places)</h3>', '<h3>Category scores (percentile vs. all Washington places)</h3>')
rep('''  const sig = [sigCard(r.ff_n, r.ff_r, "the fish fry"), sigCard(r.cs_n, r.cs_r, "custard"), sigCard(r.cc_n, r.cc_r, "cheese curds"),
    r.sc_n ? `<div><b>${fmtN(r.sc_n)}</b><span>${r.sc_n === 1 ? "review calls" : "reviews call"} it a supper club</span></div>` : ""].join("");''',
    '''  const hcSec = (r.hc || x.dishes || x.note) ? `<div class="dsec"><h3>Hand-checked${r.hc & 1 ? " · teriyaki guide" : ""}</h3>${x.note ? `<p style="margin:0 0 8px;color:var(--ink-2);font-size:14px">${esc(x.note)}</p>` : ""}${kv([
      x.dishes ? ["Serves", esc(x.dishes)] : null, x.kasahara ? ["History", "Connected to Toshi Kasahara, per the source"] : null,
      x.brand_founded ? ["Brand founded", esc(x.brand_founded)] : null, x.src ? ["Source", `<a href="${esc(x.src)}" target="_blank" rel="noopener">${esc(x.src.replace(/^https?:\\/\\/(www\\.)?/, "").slice(0, 48))} ↗</a>`] : null])}${DETAIL ? "" : `<p class="note">${detailFailed ? "Couldn't load the details." : "Loading…"}</p>`}</div>` : "";''')
rep('similar Wisconsin places (the same model as the Chicago leaderboard', 'similar Washington places (the same model as the Chicago leaderboard')
rep("compared with the chain's other Wisconsin locations.", "compared with the chain's other Washington locations.")
rep('''  const tagsTxt = TAGS.filter(([, , bit]) => r.tags & bit).map(([, l]) => l.replace(/s$/, "")).concat(r.tags & 16 ? ["Fish boil"] : []);''',
    '''  const tagsTxt = TAGS.filter(([, , bit]) => r.tags & bit).map(([, l]) => l.replace(/s$/, ""));''')
a = s.index('  const insp = r.grade ?')
b = s.index('  $("#drawer").innerHTML = `${dhead(')
s = s[:a] + r'''  const RES = {Satisfactory: "Satisfactory (no red critical violations)", Unsatisfactory: "Unsatisfactory (at least one red critical violation found)", Complete: "Complete"};
  const insp = (r.kc_r || x.kc_date) ? `<div class="dsec"><h3>Food safety · King County (official)</h3>
      ${r.kc_r ? `<div class="hero" style="margin:0 0 10px"><span class="kcr r-${r.kc_r}" style="font-size:18px;padding:6px 14px">${KCR[r.kc_r]}</span><span class="lbl">Public Health – Seattle &amp; King County's official food safety rating, as published. Records through ${esc(META.records_through || "")}.</span></div>` : ""}
      ${kv([x.kc_date ? ["Latest routine inspection", `${esc(x.kc_date)} · ${esc(RES[x.kc_result] || x.kc_result || "—")}`] : null, x.kc_red != null ? ["Red points at that inspection", fmtN(x.kc_red)] : null,
        ["Routine inspections since 2023", wait ?? fmtN(x.kc_n ?? r.kc_n)], ["With a red critical violation", wait ?? fmtN(x.kc_unsat ?? r.kc_u)],
        x.kc_return ? ["Return inspections since 2023", fmtN(x.kc_return)] : null, x.kc_closure ? ["Closed by Public Health (latest)", esc(x.kc_closure)] : null,
        r.kc_avg != null ? ["Average red points per routine inspection (since 2023)", String(r.kc_avg)] : null])}
      <p class="note">“Unsatisfactory” means the inspector found at least one red (critical) violation; it isn't a closure. The rating is King County's; the averages are counted from the same public records.</p>
      ${DETAIL ? "" : `<p class="note">${detailFailed ? "Couldn't load the inspection breakdown. Check your connection and reopen this place." : "Loading the inspection breakdown…"}</p>`}</div>` : "";
''' + s[b:]
rep('$("#drawer").innerHTML = `${dhead(esc(r.city || "Wisconsin"), random)}', '$("#drawer").innerHTML = `${dhead(esc(r.city || "Washington"), random)}')
rep('<div class="addr">${r.addr ? esc(r.addr) + ", " : ""}${esc(r.city || "Wisconsin")}', '<div class="addr">${r.addr ? esc(r.addr) + ", " : ""}${esc(r.city || "Washington")}')
rep('''    ${sig ? `<div class="dsec"><h3>Wisconsin classics · from Google reviews through Sep 2021</h3><div class="wisig">${sig}</div><p class="note">Average star rating of just the reviews that mention it. Reviews rate the whole visit, so read these as a lean, not a verdict.</p></div>` : ""}''',
    '    ${hcSec}')
rep('${x.founded ? `<p class="note">Open since ${esc(x.founded)} (verified).</p>` : ""}', '${x.founded ? `<p class="note">Open at this address since ${esc(x.founded)} (verified).</p>` : ""}')
rep('''      ["Confirmed by", r.tier === 2 ? esc(JUR[r.jur]) + " license list" : r.tier === 1 ? "Map listing (2026) and Google (2021)" : "One map listing (2026) only"],''',
    '''      ["Confirmed by", r.tier === 2 ? "King County inspection records" : r.tier === 1 ? "Map listing (2026) and Google (2021)" : "One map listing (2026) only"],
      r.county ? ["County", esc(r.county)] : null,''')
rep('''      x.lic ? ["License number", esc(x.lic.replace(/^(MKE|PHMDC)-/, ""))] : null,
      tagsTxt.length ? ["Wisconsin tags", esc(tagsTxt.join(", "))] : null,
      ["Listed as a bar or tavern", r.bar ? "Yes" : "No"], ["Locations in Wisconsin", r.chain_n >= 2 ? fmtN(r.chain_n) : "This one only"],''',
    '''      x.lic ? ["King County business ID", esc(x.lic.replace(/^KC-/, ""))] : null,
      tagsTxt.length ? ["Washington tags", esc(tagsTxt.join(", "))] : null,
      ["Listed as a bar or tavern", r.bar ? "Yes" : "No"], ["Locations in Washington", r.chain_n >= 2 ? fmtN(r.chain_n) : "This one only"],''')
rep('`confirmed by a license list or two sources · ${plural(nc, "town", "towns")}`', '`confirmed by King County records or two sources · ${plural(nc, "town", "towns")}`')
# ---- sources & calibration
a = s.index('function methodCards() {')
b = s.index('// ---------------- boot ----------------')
s = s[:a] + r'''function methodCards() {
  const m = META, c = m.calibration || {}, k = c.king?.artifact || {};
  const dv = ["Foursquare only", "BrightQuery only", "Foursquare/BrightQuery/Microsoft + Google 2021"].map(x => k[x]).filter(Boolean).map(g => g.official);
  const dropRange = dv.length ? `${Math.round(Math.min(...dv) * 100)}–${Math.round(Math.max(...dv) * 100)}%` : "a small share";
  const cols = [
    ["m", "Official records", [
      ["King County inspections", `Public Health – Seattle & King County's food establishment inspection data (data.kingcounty.gov, public domain), 2021 to the present, through ${esc(m.records_through || "")} (fetched ${esc(m.king_fetched || "")}). A listing that matches a business inspected in the last 18 months is marked confirmed, and inspected restaurants the map data doesn't have are added from the records. The Food safety board shows King County's own rating (Excellent, Good, Okay, Needs to Improve), never one of ours.`],
      ["The rest of the state", "Washington has no statewide restaurant or inspection list. Local health jurisdictions inspect, and outside King County their results are one-at-a-time searches or PDFs (Pierce, Snohomish, Clark, Spokane, Whatcom and others), which we don't scrape. So outside King County, every place comes from map listings."]]],
    ["s", "Map listings & 2021 snapshot", [
      ["Places statewide", `Overture Maps' open map listings (${esc(m.overture_release || "Sep 2026")} release, which merges Meta, Foursquare, chain store lists and other sources). We keep listings from Meta and from chains' own store lists, and drop Foursquare, BrightQuery and Microsoft listings: in King County only ${dropRange} of those matched an inspected business. Anything Google already showed as closed in 2021 is dropped, unless it's on our hand-checked list. Out-of-state rows (Portland, Idaho, B.C.) are cut at the state line.`],
      ["Ratings, reviews & price level", "Google Maps ratings from the UCSD Google Local research dataset, frozen in September 2021 (Washington State only; D.C. is a different file). Each Google listing is matched to one place at most, on a shared distinctive name word nearby. Places that opened later aren't in it, and the rating boards leave them out rather than guess."],
      ["Teriyaki, phở & other tags", "Teriyaki and phở come from the business name (or cuisine). Places on our hand-checked teriyaki guide carry Teriyaki ✓: each one was confirmed open and serving teriyaki with a 2025–26 source (its own menu or ordering page, or dated local news). A place merely named teriyaki stays on the board without the check."],
      ["Honors & history", `Hand-verified in Oct 2026 with closures checked: James Beard finalists and semifinalists (Washington had no Restaurant & Chef winner 2023–2026), and Washington's oldest restaurants and bars still open, each with a source. There is no MICHELIN Guide for Washington State.`]]],
    ["e", "Estimated", [
      ["Sales & profit", `Chains use their published U.S. average sales per store (QSR 50, Technomic, company filings; ${m.model?.n_chains ?? "40+"} brands found here), scaled by how busy the location is. Independents start from a typical figure for their price level ($600K for $ up to $3.5M for $$$$) and scale with 2021 review volume relative to similar Washington places, with an exponent of ${m.model?.b ?? 0.76} fit on published Chicago sales. Places without reviews get a rough placeholder. Profit = sales × a typical segment margin.`],
      ["Price, cuisine & food cost", "Missing price levels are filled in from the chain's or cuisine's usual Washington level and marked est. Cuisine comes from the business name, the listing's category and Google categories, so a few will be off. Food cost is the typical share for that cuisine × estimated sales, a benchmark rather than the restaurant's own invoices."]]],
  ];
  $("#srcgrid").innerHTML = cols.map(([t, h, cards]) => `<div class="srccol"><span class="tag ${t}">${h}</span>${cards.map(([h,p]) => `<div class="src"><h3>${h}</h3><p>${p}</p></div>`).join("")}</div>`).join("");
  const G = [["Meta + open in Google 2021","Meta listing, open in Google's 2021 data","kept · two sources"],["Meta only","Meta listing only","kept · listing only"],
    ["brand feed + Google 2021","Chain store list + Google 2021","kept · two sources"],["brand feed only","Chain store list only","kept · listing only"],
    ["Foursquare/BrightQuery/Microsoft + Google 2021","Foursquare / BrightQuery / Microsoft + Google 2021","dropped"],["Foursquare only","Foursquare only","dropped"],
    ["BrightQuery only","BrightQuery only","dropped"],["Microsoft only","Microsoft only","dropped"],["Google 2021 says closed","Google showed it closed in 2021","dropped"]];
  const cell = (j, key) => { const g = c[j]?.artifact?.[key]; return g ? `${Math.round(g.official * 100)}% <span style="color:var(--muted)">of ${fmtN(g.n)}</span>` : "—"; };
  const cov = (m.coverage_county || []).filter(x => x.lcb_on_premise >= 30);
  $("#calib").innerHTML = c.king ? `<div class="src" style="display:grid;gap:10px"><h3>How the map listings were checked</h3>
    <p>Inside King County, every map listing was checked against King County's inspection records (businesses inspected in the last 18 months): same business name nearby, or the same street address with a distinctive name word in common. Inside Seattle, the same check ran against the city's active business licenses for restaurants and bars. The share that matched decides what's kept (the same checks gave 74% for Meta + Google in Chicago and 76–81% in Wisconsin). The map listings held ${Math.round((c.king.coverage_all_listings||0)*100)}% of King County's inspected restaurants; the rest were added from the records.</p>
    <div class="calib"><table><thead><tr><th scope="col">Kind of listing</th><th scope="col" class="r">King County</th><th scope="col" class="r">Seattle licenses</th><th scope="col">Here</th></tr></thead><tbody>
    ${G.map(([key, l, what]) => `<tr><td>${esc(l)}</td><td class="r num">${cell("king", key)}</td><td class="r num">${cell("seattle", key)}</td><td>${what}</td></tr>`).join("")}</tbody></table></div>
    <p class="note">Matched = on King County's list of inspected food businesses (or Seattle's restaurant and bar licenses). These are lower bounds: a real place under a different name on its permit counts as a miss. Hand-checked places are kept whatever their source.</p>
    ${cov.length ? `<h3 style="margin-top:8px">Coverage by county</h3><p>Share of each county's liquor-licensed restaurants and taverns (state Liquor and Cannabis Board on-premise list, Sep 29, 2026) found among the kept map listings. A lower bound and a check only; the list itself isn't shown.</p>
    <div class="calib"><table><thead><tr><th scope="col">County</th><th scope="col" class="r">Kept listings</th><th scope="col" class="r">Liquor-licensed found</th></tr></thead><tbody>
    ${cov.map(x => `<tr><td>${esc(x.county)}</td><td class="r num">${fmtN(x.listings_kept)}</td><td class="r num">${Math.round(x.lcb_found*100)}% <span style="color:var(--muted)">of ${fmtN(x.lcb_on_premise)}</span></td></tr>`).join("")}</tbody></table></div>` : ""}</div>` : "";
}

''' + s[b:]
# ---- build()
rep('o.value_raw = col("value_raw", i); o.tier = C.tier[i]; o.both = o.tier >= 1 ? 1 : 0; o.jur = C.jur[i]; o.bar = C.bar[i]; o.venue = C.venue[i]; o.tags = C.tags[i] || 0;',
    'o.value_raw = col("value_raw", i); o.tier = C.tier[i]; o.both = o.tier >= 1 ? 1 : 0; o.bar = C.bar[i]; o.venue = C.venue[i]; o.tags = C.tags[i] || 0; o.hc = C.hc[i] || 0;\n'
    '    o.county = C.county[i] == null ? null : (m.counties || [])[C.county[i]];')
rep('o._s = " " + normRaw([o.name, o.city, o.zip, o.cuisine, o.brand].join(" ")) + " " + norm(o.addr) + " ";', 'o._s = " " + normRaw([o.name, o.city, o.zip, o.cuisine, o.brand, o.county ? o.county + " county" : ""].join(" ")) + " " + norm(o.addr) + " ";')
a = s.index('  // Wisconsin signals: Bayes-shrink')
b = s.index('  for (const [i, s, f] of sp.hon || [])')
s = s[:a] + s[b:]
rep('  for (const [i, cl, g, ni, nr] of sp.insp || []) if (rows[i]) Object.assign(rows[i], {clean: cl, grade: g, n_insp: ni, n_reinsp: nr});',
    '  for (const [i, rc, avg, ni, nu] of sp.insp || []) if (rows[i]) Object.assign(rows[i], {kc_r: rc, kc_avg: avg, kc_n: ni, kc_u: nu});')
rep('"fish", "fry", "custard", "curds", "cheese", "supper", "club", "brats", "tavern", "tap", "brewery", "kringle"]));',
    '"teriyaki", "pho", "espresso", "oysters", "oyster", "chowder", "drive", "tavern", "tap", "brewery", "seafood", "poke", "dumplings"]));')
rep('$("#h1").innerHTML = `<span class="count num">${fmtN(n)}</span> Wisconsin restaurants, ranked`;', '$("#h1").innerHTML = `<span class="count num">${fmtN(n)}</span> Washington restaurants, ranked`;')
rep('`${fmtN(CITIES.filter(([, c]) => c > 0).length)} cities and towns · map listings as of Sep 2026 · ratings as of Sep 2021`',
    '`Washington State · ${fmtN(CITIES.filter(([, c]) => c > 0).length)} cities and towns · map listings as of Sep 2026 · ratings as of Sep 2021 · King County inspections through ${META.records_through || ""}`')
rep('else { $("#cityhint").textContent = `No Wisconsin town matches', 'else { $("#cityhint").textContent = `No Washington town matches')
s = s if s.startswith("<meta charset") else "<meta charset=\"utf-8\">\n" + s
open(p, "w").write(s)
left = [(i + 1, l.strip()[:140]) for i, l in enumerate(s.splitlines()) if re.search(r"Wisconsin|\bWI\b|Dane|Milwaukee|supper|fish fry|custard|curds|ff_n|\.jur\b|JUR\[|n_insp|\.grade\b", l)]
print("remaining Wisconsin-specific lines:", len(left))
for x in left: print(x)
