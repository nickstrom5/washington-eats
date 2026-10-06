"""Shared helpers: name keys, casing, name matching, town and street keys, cuisine rules and money benchmarks.

Adapted from wi-eats/pipeline/common.py (itself from chi-eats/pipeline/build.py: the same rules, learned on Chicago and Wisconsin),
with Wisconsin-only words taken out and Washington ones added. Washington addresses keep their quadrant directions in the street key:
in Seattle "4th Ave N" and "4th Ave S" are different streets, and so are "NE 45th St" and "NW 45th St".
"""
import os, re
from rapidfuzz import fuzz

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
WA = os.path.join(DATA, "wa")

STOP = {"THE", "INC", "LLC", "CO", "CORP", "RESTAURANT", "RESTAURANTS", "AND", "OF", "LTD", "CAFE", "#"}


def norm_name(s):
    s = (s or "").upper().replace("&", " AND ").replace("'S", "S").replace("’S", "S")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b\d{2,}\b", " ", s)  # store numbers like "#1234"
    return " ".join(w for w in s.split() if w not in STOP)


SMALL = {"of", "and", "the", "on", "at", "in", "de", "la", "el", "y", "du"}
NOT_ACRONYM = {"mr", "mrs", "ms", "st", "dr", "jr", "sr", "pl", "ct", "rd", "ln", "blvd", "pkwy", "hwy", "sq", "cr", "th", "nd", "mc",
               "cty", "hwy", "trl", "cir", "ste", "fl", "wy", "pkwy", "rr", "rt", "ne", "nw", "se", "sw"}
UNIT_TAIL = re.compile(r"(\s+(BLDG|BLD|STE|SUITE|FL|FLR|FLOOR|UNIT|RM|LOWER LEVEL|LL|APT|SPACE)\b.*$)|(\s+\d+\s*$)", re.I)


def _case(w, first, addr):
    lw = w.lower()
    if not lw:
        return w
    if first is False and lw in SMALL and not addr:
        return lw
    if lw == "bj's":
        return "BJ's"
    core = re.sub(r"[^a-z']", "", lw)
    if re.fullmatch(r"(bbq|ii|iii|iv|usa|jj|kfc|ihop|tgi|atm|llc|bp|dj|pb|vfw|amvets|ymca|uw|[a-z])", core):
        return w.upper()
    if addr and re.fullmatch(r"(ne|nw|se|sw|us|wa|sr|i|n|s|e|w)", core):
        return w.upper()
    if re.fullmatch(r"(dj|bj|jj)'s", core):
        return core[:2].upper() + core[2:] + w[len(core):]
    if not addr and core not in NOT_ACRONYM and re.fullmatch(r"[b-df-hj-np-tv-xz]{2,4}", core) and not re.search(r"(.)\1\1", core):
        return w.upper()
    if re.match(r"^mc[a-z]{3}", lw):
        return "Mc" + lw[2].upper() + lw[3:]
    if re.match(r"^o'[a-z]{2}", lw):
        return "O'" + lw[2].upper() + lw[3:]
    t = lw[:1].upper() + lw[1:]
    return re.sub(r"([-(.&])([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)


def nice(s, addr=False):
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r"(?i)\b(\w+)IES'S\b", r"\1IE'S", s)
    s = re.sub(r"(?i)'S\s+'S\b", "'S", s)
    s = re.sub(r"(?i)\bMC\s+([A-Z]{2,})", r"MC\1", s)
    if addr:   # "55 E MAIN ST STE 4" -> drop the dangling unit / stray number
        m = re.match(r"^(\d+[A-Z]?(?:\s*-\s*\d+)?\s+.+?\b(?:ST|AVE|BLVD|DR|RD|PL|CT|PKWY|TER|WAY|LN|HWY|PLZ|SQ|CIR|TRL|MARKET)\b)", s, re.I)
        if m and UNIT_TAIL.search(s[m.end():]):
            s = m.group(1)
    if not s:
        return s
    out = []
    words = s.split(" ")
    for i, w in enumerate(words):
        parts = re.split(r"([/@&])", w)
        cased = "".join(p if p in "/@&" else _case(p, None if i == 0 and j == 0 else False, addr) for j, p in enumerate(parts))
        if i and re.fullmatch(r"\(?wa\)?[\d,]*", w.lower()) and (i == len(words) - 1 or "(" in w):   # the state code
            cased = w.upper()
        out.append(cased)
    return " ".join(out).replace("Chick-Fil-A", "Chick-fil-A")


# Seattle neighborhoods and military-base spellings that map listings use as a town
TOWN_ALIAS = {"westseattle": "Seattle", "fremont": "Seattle", "ballard": "Seattle", "capitolhill": "Seattle", "queenanne": "Seattle",
              "southlakeunion": "Seattle", "georgetown": "Seattle", "beaconhill": "Seattle", "wallingford": "Seattle", "greenlake": "Seattle",
              "universitydistrict": "Seattle", "udistrict": "Seattle", "columbiacity": "Seattle", "northgate": "Seattle", "magnolia": "Seattle",
              "seattlewa": "Seattle", "seatac": "SeaTac", "seatacwa": "SeaTac", "dupont": "DuPont", "battleground": "Battle Ground",
              "jblm": "Joint Base Lewis-McChord", "jblewismcchord": "Joint Base Lewis-McChord", "jointbaselewismcchord": "Joint Base Lewis-McChord",
              "mcchordafb": "Joint Base Lewis-McChord", "fortlewis": "Joint Base Lewis-McChord", "sedrowoolley": "Sedro-Woolley",
              "spokanevalley": "Spokane Valley", "miltonfreewater": "Milton-Freewater", "mossyrock": "Mossyrock", "lacrosse": "LaCrosse",
              "mountvernon": "Mount Vernon", "mtvernon": "Mount Vernon", "mountlaketerrace": "Mountlake Terrace", "lakeforestpark": "Lake Forest Park",
              "universityplace": "University Place", "eastwenatchee": "East Wenatchee", "coeurdalene": "Coeur d'Alene", "walla walla": "Walla Walla",
              "wallawalla": "Walla Walla", "portorchard": "Port Orchard", "porttownsend": "Port Townsend", "portangeles": "Port Angeles",
              "normandypark": "Normandy Park", "bainbridgeisland": "Bainbridge Island", "vashonisland": "Vashon", "vashon": "Vashon",
              "fridayharbor": "Friday Harbor", "oceanshores": "Ocean Shores", "moseslake": "Moses Lake", "colvillewa": "Colville",
              "medicallake": "Medical Lake", "liberty lake": "Liberty Lake", "libertylake": "Liberty Lake", "gigharbor": "Gig Harbor",
              "fedway": "Federal Way", "federalway": "Federal Way", "millcreek": "Mill Creek", "lakestevens": "Lake Stevens",
              "mapleValley".lower(): "Maple Valley", "blackdiamond": "Black Diamond", "northbend": "North Bend", "snoqualmiepass": "Snoqualmie Pass",
              "steilacoom": "Steilacoom", "bonneylake": "Bonney Lake", "fircrest": "Fircrest", "whitecenter": "White Center",
              "deerpark": "Deer Park", "cheney": "Cheney", "kenmore": "Kenmore", "ridgefield": "Ridgefield", "lacenter": "La Center",
              "washougal": "Washougal", "camas": "Camas", "longbeach": "Long Beach", "westport": "Westport", "elma": "Elma"}


def canon_city(c):
    """One spelling per town: St/Saint -> St., Mt/Mount -> Mount, Ft -> Fort, "City of X" -> X, case fixes, Seattle neighborhoods -> Seattle."""
    if not isinstance(c, str) or not c.strip():
        return None
    c = re.sub(r",?\s*(?:WA|Wash\.?|Washington)\.?$", "", c.strip().strip(","), flags=re.I).strip(" ,")
    c = re.sub(r"^(?:City|Town)\s+of\s+", "", c, flags=re.I)
    if not c:
        return None
    c = nice(c) if c.isupper() or c.islower() else c
    c = re.sub(r"\b(?:Saint|St)\b\.?\s*", "St. ", c)
    c = re.sub(r"\bMt\b\.?\s*", "Mount ", c)
    c = re.sub(r"\bFt\b\.?\s*", "Fort ", c)
    c = re.sub(r"\s+", " ", c).strip()
    key = re.sub(r"[^a-z]", "", c.lower())
    return TOWN_ALIAS.get(key, c)


def town_key(c):
    k = c.lower().replace(".", " ")
    k = re.sub(r"^(e|n|s|w)\s+", lambda m: {"e": "east ", "n": "north ", "s": "south ", "w": "west "}[m.group(1)], k)
    k = re.sub(r"\bmt\b", "mount", k); k = re.sub(r"\bhts\b", "heights", k); k = re.sub(r"\bft\b", "fort", k)
    return re.sub(r"[^a-z]", "", k)


# ---------------------------------------------------------------- street keys (Washington grids keep their directions)
_DIR = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
        "N": "N", "S": "S", "E": "E", "W": "W", "NE": "NE", "NW": "NW", "SE": "SE", "SW": "SW"}
_TYPE = {"STREET": "ST", "ST": "ST", "AVENUE": "AVE", "AVE": "AVE", "AV": "AVE", "BOULEVARD": "BLVD", "BLVD": "BLVD", "ROAD": "RD", "RD": "RD",
         "DRIVE": "DR", "DR": "DR", "PLACE": "PL", "PL": "PL", "COURT": "CT", "CT": "CT", "LANE": "LN", "LN": "LN", "HIGHWAY": "HWY", "HWY": "HWY",
         "PARKWAY": "PKWY", "PKWY": "PKWY", "WAY": "WAY", "WY": "WAY", "TERRACE": "TER", "TER": "TER", "CIRCLE": "CIR", "CIR": "CIR", "LOOP": "LOOP",
         "PLAZA": "PLZ", "PLZ": "PLZ", "SQUARE": "SQ", "SQ": "SQ", "TRAIL": "TRL", "TRL": "TRL", "MALL": "MALL", "CRESCENT": "CRES", "ALLEY": "ALY",
         "EXPRESSWAY": "EXPY", "EXPY": "EXPY", "FREEWAY": "FWY", "FWY": "FWY", "ROW": "ROW", "WALK": "WALK", "PIKE": "PIKE", "BYPASS": "BYP",
         "CROSSING": "XING", "XING": "XING", "RUN": "RUN", "PASS": "PASS", "PT": "PT", "POINT": "PT", "LOOP RD": "LOOP"}
_ORD = {"FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH", "FIFTH": "5TH", "SIXTH": "6TH", "SEVENTH": "7TH", "EIGHTH": "8TH",
        "NINTH": "9TH", "TENTH": "10TH", "ELEVENTH": "11TH", "TWELFTH": "12TH"}


def road(a):
    """One spelling for numbered roads: 'State Route 99' = 'SR-99' = 'Hwy 99' = 'WA-99'; 'US Highway 2' = 'US-2'; 'Interstate 5' = 'I 5'."""
    a = a.upper()
    a = re.sub(r"\b(?:STATE\s+(?:ROUTE|HIGHWAY|HWY|RTE|RD|ROAD)|STATE\s+RT|SR|WA|WASHINGTON\s+(?:HIGHWAY|HWY|STATE\s+ROUTE))\s*-?\s*(\d+)\b", r"SR \1", a)
    a = re.sub(r"\b(?:US|U\s+S)\s*(?:HIGHWAY|HWY|ROUTE|RTE)?\s*-?\s*(\d+)\b", r"US \1", a)
    a = re.sub(r"\b(?:INTERSTATE|I)\s*-?\s*(\d+)\b", r"I \1", a)
    a = re.sub(r"\b(?:HIGHWAY|HWY)\s+(\d+)\b", r"SR \1", a)      # a bare "Highway 99" in Washington is a state route
    return a


def street_key(a):
    """'2746 NE 45th St' -> ('2746', 'NE 45TH'); '2746 Northeast 45TH Street' -> the same; '100 4th Ave N' -> ('100', '4TH N');
    '14200 1ST AVE S, F' -> ('14200', '1ST S'); '20829 Hwy 99' -> ('20829', 'SR 99')."""
    if not isinstance(a, str):
        return None, None
    a = road(a.split(",")[0])
    a = re.sub(r"[.#]", " ", a).replace("-", " ") if not re.match(r"^\s*\d+\s*-\s*\d+\s", a) else re.sub(r"[.#]", " ", a)
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*\d+[A-Z]?)?\s+(.*)$", a)
    if not m:
        return None, None
    words = [w for w in m.group(2).replace("-", " ").split() if w]
    out, pre, post, seen_type = [], None, None, False
    if words and words[0] in _DIR and len(words) > 1:
        pre = _DIR[words[0]]; words = words[1:]
    for j, w in enumerate(words):
        if w in ("STE", "SUITE", "UNIT", "APT", "SPC", "SPACE", "BLDG", "FL", "RM", "#", "LOWER", "UPPER") or re.fullmatch(r"[A-Z]?\d+[A-Z]?", w) and seen_type:
            break
        if w in _DIR and out:
            post = _DIR[w]; break
        if w in _TYPE and out and not (w == "WAY" and j == 0):
            seen_type = True
            continue
        if seen_type:
            break
        out.append(_ORD.get(w, w))
    core = " ".join(out[:3])
    if not core:
        return None, None
    return m.group(1), " ".join(x for x in (pre, core, post) if x)


_DIRS = r"(?:N|S|E|W|NE|NW|SE|SW)"


def undir(k):
    """'NE NORTHUP' -> 'NORTHUP'; '4TH N' -> '4TH'. For matching when one source leaves the direction out."""
    return re.sub(rf"^{_DIRS} | {_DIRS}$", "", k) if isinstance(k, str) else k


def street_eq(a, b):
    """Same street: equal keys, or equal once directions are dropped when one side has none ('NORTHUP' = 'NE NORTHUP',
    but '4TH N' != '4TH S')."""
    if not a or not b:
        return False
    return a == b or (undir(a) == undir(b) and (a == undir(a) or b == undir(b)))


def street_nums(a):
    """'157-159 Main St' -> {'157', '159'}; '2505 Pacific Ave' -> {'2505'}."""
    if not isinstance(a, str):
        return set()
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*(\d+)[A-Z]?)?\s", a.upper() + " ")
    if not m:
        return set()
    lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else lo
    if hi < lo:   # "1500-02"
        hi = int(str(lo)[: len(str(lo)) - len(m.group(2))] + m.group(2)) if m.group(2) else lo
    return {str(x) for x in range(lo, hi + 1, 2 if (hi - lo) % 2 == 0 else 1)} if 0 <= hi - lo <= 12 else {str(lo)}


# words that don't identify a business on their own: a name match needs a shared word outside this list
GENERIC = set("""PIZZA PIZZERIA PHO TACO TACOS TAQUERIA GRILL GRILLE KITCHEN EXPRESS HOUSE COFFEE BAR PUB TAVERN FOOD FOODS STORE SHOP MARKET
DELI BAKERY CHICKEN FISH BBQ SUSHI THAI CHINESE MEXICAN INDIAN ITALIAN GYROS BURGER BURGERS WINGS DONUTS DONUT BEEF TEA JUICE
NORTH SOUTH EAST WEST PARK SQUARE STATION UNION TOWN VILLAGE STREET AVE AVENUE CENTER PLAZA LAKE LAKES RIVER BAY
NEW OLD BEST GOLDEN LITTLE BIG KING STAR ORIGINAL FAMOUS FRESH HOT GRAND LA EL LOS LAS DE DEL ON THE Y AT OF LOUNGE SNACK SNACKS
NOODLE NOODLES ASIAN SHRIMP PATIO CLUB SUPPER INN LODGE SALOON RESORT BREWING BREWERY COMPANY BREW HALL CUSTARD FROZEN CHEESE CURDS
FRY BRATS BRAT WISCONSIN BAKE CAFETERIA CORNER SPOT STOP PLACE ROOM SPORTS FAMILY STEAKHOUSE STEAK DINER CREAMERY ICE CREAM
MKE MILW HUT WOK MEAL FUSION BUFFET CUISINE EATS EATERY
SEATTLE TACOMA SPOKANE WASHINGTON WA NW PNW NORTHWEST PACIFIC PUGET SOUND TERIYAKI TERIYAKE ESPRESSO BURRITO BURRITOS
HARBOR VALLEY ISLAND DRIVE THRU IN DOGS POKE BOWL BOWLS ROLL ROLLS HAWAIIAN FILIPINO JAPANESE KOREAN""".split())


def _stems(s):
    return {w if w in GENERIC else (w[:-1] if len(w) > 3 and w.endswith("S") else w) for w in s.split()} - GENERIC


def name_sim(a, b):
    ours, theirs = set(a.split()), set(b.split())
    distinct = (_stems(a) - GENERIC) & (_stems(b) - GENERIC)
    joined = a.replace(" ", "") == b.replace(" ", "") or fuzz.ratio(a.replace(" ", ""), b.replace(" ", "")) >= 92
    if joined:
        return 96
    if not distinct and fuzz.ratio(a, b) < 95:   # nothing but generic words in common: not the same business
        return 60
    s_set = fuzz.token_set_ratio(a, b)
    # token_set_ratio is 100 whenever one name's words are a subset of the other's: cap it unless the overlap is a real share of both
    if len(ours & theirs) < 0.5 * min(len(ours), len(theirs)) + 0.5 or len(ours & theirs) < 0.4 * max(len(ours), len(theirs)):
        s_set = min(s_set, 72)
    return max(s_set, fuzz.ratio(a, b), fuzz.token_sort_ratio(a, b))


FOODCAT = re.compile(r"\b(restaurant|cafe|coffee|bakery|pizza|bar|pub|diner|deli|taco|ice cream|donut|dessert|sandwich|food court|caterer|tea house|bistro|brewpub|brewery|juice|grill|takeout|buffet|bagel|chicken|seafood|steak|hot dog|tavern|lounge|gastropub|snack|yogurt|creperie|patisserie|chocolate|confectionery|bubble tea|night club|beer|wine|bbq|barbecue|pie|pastry|popcorn|tamale|churro|takeaway|tortilleria|supper club|custard|fish & chips|cheesesteak)\b", re.I)
NOTFOOD = re.compile(r"^(?:Tower|Museum|Stadium|Convention|Hotel|Performing|Theater|Hospital|University|Corporate|Observation|Tourist|Airport|Casino|Gas station|Grocery|Supermarket|Convenience|Liquor store|Event|Banquet|Park|Arena)\b")

# Name keywords -> cuisine. Whole words only, so HOSPITAL isn't "PITA", BREWING isn't "WING", BOWLING isn't "BOWL".
# Order matters: specific before general.
_W = lambda words: re.compile(r"\b(?:" + words + r")\b")
CUISINE_RULES = [
    ("Teriyaki", _W(r"TERIYAKI|TERIYAKE|TERIYAKIS|TERIYAKI MADNESS|SARKU")),
    ("Hot Dogs", _W(r"HOT ?DOGS?|DOGS|WIENERS?|BRATS?|BRATWURST|SAUSAGES?|FRANKS?")),
    ("Pizza", _W(r"PIZZA|PIZZAS|PIZZERIA|PIZZERIAS|DOMINOS|PAPA JOHNS|LITTLE CAESARS?|PAGLIACCI|ZEEKS|ROUND TABLE|ABBYS|GARLIC JIMS|PIZZA HUT|PIZZA RANCH|MOD PIZZA|BLAZE")),
    ("Hawaiian", _W(r"HAWAIIAN|HAWAII|ALOHA|LOCO MOCO|MUSUBI|KONA|L AND L|ONO|MAHALO|LUAU|KAU KAU|PLATE LUNCH")),
    ("Filipino", _W(r"FILIPINO|PINOY|LUMPIA|ADOBO|SISIG|MANILA|JOLLIBEE|SILOG|TAPSILOG|LECHON|CHIBOG|KAMAYAN|INASAL")),
    ("Korean", _W(r"KOREAN?|KOREA|KIMCHI|BIBIMBAP|SEOUL|GOGI|BULGOGI|KBBQ|CUPBOP")),
    ("Thai", _W(r"THAI|SIAM|BANGKOK|ISAAN|ISAN")),
    ("Vietnamese", _W(r"PHO|VIETNAMESE|VIETNAM|SAIGON|BANH MI|BANH|HANOI")),
    ("Coffee & Café", _W(r"COFFEE|ESPRESSO|STARBUCKS|DUNKIN|CAFFE|TEA|TEAS|TEAHOUSE|BOBA|LATTE|ROASTERS?|ROASTING|KAFFE|KAFFEE|DUTCH BROS|BLACK ROCK|ZIGGIS|TULLYS|LADRO|VIVACE|BARISTAS?|JAVA|BREW HUT|MOCHA|CAFFEINE|AMERICANO")),
    ("Bakery & Sweets", _W(r"BAKERY|BAKERIES|BAKESHOP|BAKE SHOP|BAKEHOUSE|PASTRY|PASTRIES|PATISSERIE|DONUTS?|DOUGHNUTS?|PANADERIA|CAKES?|CUPCAKES?|COOKIES?|DESSERTS?|ICE CREAM|GELATO|GELATERIA|PALETERIA|PALETAS|YOGURT|FROYO|CREPES?|CREPERIE|SWEETS|CHOCOLATE|CHOCOLATIER|CINNABON|BAGELS?|CREAMERY|CHURROS?|PIES|KRINGLE|CONFECTIONS?|MICHOACANA|DAIRY QUEEN|BASKIN")),
    ("Mexican", _W(r"TACO TIME|TACO DEL MAR|TAQUERIA|TAQUERIAS|TACOS?|MEXICAN[AO]?|MEXICO|BURRITOS?|BIRRIA|BIRRIERIA|CARNITAS|TAMALES?|TORTAS?|ELOTES?|MARISCOS|CHIPOTLE|QDOBA|AZTECA|JALISCO|MICHOACAN|GUADALAJARA|OAXACA|GUERRERO|PUEBLA|CANTINA|TORTILLERIA|ANTOJITOS?|QUESADILLAS?|NACHOS?|HUARACHES?|FONDA|EL TORO|TAQUERIA")),
    ("Latin & Caribbean", _W(r"CUBAN[AO]?|CUBA|PUERTO RICAN|BORINQUEN|CARIBBEAN|JAMAICAN?|JERK|HAITIAN?|PERUVIAN|PERU|COLOMBIAN[AO]?|COLOMBIA|SALVADOREN[AO]|PUPUSAS?|PUPUSERIA|ARGENTIN[AE]|ARGENTINIAN|VENEZUELAN?|AREPAS?|BRAZILIAN?|EMPANADAS?|DOMINICAN|GUATEMALTEC[AO]|HONDUREN[AO]|ECUADORIAN|LATIN[AO]?|CEVICHE")),
    ("Japanese & Sushi", _W(r"SUSHI|RAMEN|JAPANESE|JAPAN|IZAKAYA|HIBACHI|OMAKASE|TOKYO|BENTO|UDON|YAKITORI|KATSU|SAKE|TEMPURA|SASHIMI|TEPPANYAKI|KYOTO|OSAKA|BENIHANA|MANEKI|ONIGIRI|DONBURI|OKONOMIYAKI|TAKOYAKI")),
    ("German & European", _W(r"PELMENI|PIEROGI|PIEROGIES|HOLLANDER|BENELUX|CENTRAAL|BELGIAN|DUTCH|MELTING POT|FONDUE|SCHNITZEL|BIERGARTEN|BIERHALLE|RATSKELLER|RATHSKELLER|SERBIAN|POLISH|GERMAN|BAVARIAN")),
    ("Chinese", _W(r"CHINA|CHINESE|EGG ROLLS?|WOK|DUMPLINGS?|DIM SUM|PANDA EXPRESS|HUNAN|SZECHUAN|SICHUAN|MANDARIN|CANTONESE|KUNG PAO|HONG KONG|BEIJING|SHANGHAI|HOT ?POT|CHOP SUEY|BAO|LO MEIN|WONTON|PEKING|YUNNAN")),
    ("South Asian", _W(r"INDIA|INDIAN|TANDOOR|TANDOORI|CURRY|CURRIES|MASALA|BIRYANI|NEPAL|NEPALI|NEPALESE|HIMALAYAN?|PAKISTANI?|BOMBAY|MUMBAI|DELHI|PUNJAB|PUNJABI|KATHMANDU|MOMOS?|CHAAT|SAMOSAS?|BENGALI|SRI LANKAN?|DOSA|TIKKA")),
    ("Mediterranean & Middle Eastern", _W(r"GREEK|GYROS?|MEDITERRANEAN|MEDITERANNEAN|FALAFEL|SHAWARMA|MIDDLE EASTERN|LEBANESE|HALAL|KABOBS?|KEBABS?|KABABS?|PERSIAN|TURKISH|ISRAELI|HUMMUS|PITA|PITAS|ZAATAR|SYRIAN|AFGHAN|ARABIC|ARABIAN|ATHENS|OLYMPIA|PARTHENON|AEGEAN|NAF NAF|MEZZE|ASSYRIAN|YEMENI|ZAROB")),
    ("African", _W(r"AFRICAN?|AFRICA|ETHIOPIAN?|NIGERIAN?|ERITREAN?|GHANAIAN|SENEGALESE|SOMALI|MOROCCAN|EGYPTIAN|KENYAN|CAMEROONIAN|JOLLOF|SUYA")),
    ("Italian", _W(r"ITALIAN[AO]?|ITALIA|TRATTORIA|OSTERIA|PASTA|RISTORANTE|VINO|NONNA|CUCINA|ENOTECA|SPAGHETTI|NAPOLI|NAPOLETANA|SICILIAN|TUSCANY|TUSCAN|FORNO|MAGGIANOS|OLIVE GARDEN|BARTOLOTTA")),
    ("Burgers", _W(r"BURGERS?|HAMBURGERS?|CHEESEBURGERS?|BUTTERBURGERS?|MCDONALDS|MC DONALDS|WENDYS|WHITE CASTLE|FIVE GUYS|SHAKE SHACK|SMASHBURGER|PATTY|PATTIES|STEAK N SHAKE|SONIC|ARBYS|CHECKERS|JACK IN THE BOX|CARLS JR|IN N OUT|HABIT|RED ROBIN|DICKS DRIVE IN|DICKS|BURGERMASTER|KIDD VALLEY|ZIPS|FRISKO FREEZE|BURGERVILLE|DRIVE IN|TRIPLE XXX|HAMBURGER")),
    ("Seafood", _W(r"SEAFOOD|FISH|FISHERIES|FISHERY|SHRIMP|OYSTERS?|CRABS?|CRAB|LOBSTER|CATFISH|CAJUN|BOIL|POKE|CHOWDER|CLAMS?|SALMON|HALIBUT|IVARS|ANTHONYS|DUKES|LONG JOHN SILVERS|FISH AND CHIPS|SPUD")),
    ("Chicken & Wings", _W(r"CHICKEN|WINGS|POPEYES|KFC|CHURCHS|RAISING CANES?|CHICK FIL A|BROASTED|WINGSTOP|NASHVILLE HOT|KRISPY KRUNCHY")),
    ("BBQ", _W(r"BBQ|BAR B Q|BAR BQ|BAR B QUE|BAR BE CUE|BAR B CUE|BARBECUE|BARBEQUE|RIBS|SMOKEHOUSE|SMOKED|BRISKET|FAMOUS DAVES")),
    ("Sandwiches & Deli", _W(r"SANDWICH|SANDWICHES|DELI|DELICATESSEN|SUBWAY|JIMMY JOHNS|POTBELLY|JERSEY MIKES|FIREHOUSE SUBS|SUBS|HOAGIES?|PANERA|CORNER BAKERY|CHEESE ?STEAKS?|PHILLY|CAPRIOTTIS|COUSINS SUBS|ERBERT|GERBERTS|SUB SHOP")),
    ("Steakhouse", _W(r"STEAK|STEAKS|STEAKHOUSE|STEAK HOUSE|CHOPHOUSE|CHOP HOUSE|RUTHS CHRIS|CAPITAL GRILLE|MORTONS|TEXAS ROADHOUSE|LONGHORN|OUTBACK|PRIME RIB")),
    ("Soul & Southern", _W(r"SOUL|SOUTHERN|CREOLE|GUMBO|BISCUITS?|GRITS|CHICKEN WAFFLES")),
    ("Healthy & Vegan", _W(r"VEGAN|VEGETARIAN|SALADS?|JUICE|JUICERY|SMOOTHIES?|SWEETGREEN|PLANT BASED|ACAI|HEALTHY|ORGANIC|JAMBA|NOODLES AND COMPANY")),
    ("Breakfast & Diner", _W(r"BREAKFAST|PANCAKES?|DINER|BRUNCH|EGGS?|IHOP|DENNYS|PERKINS|YOLK|OMELETTES?|OMELETS?|SUNRISE|MORNING|WAFFLES?|GRIDDLE|SKILLETS?|MAMA DS|MY FAVORITE MUFFIN|BAGEL")),
    ("German & European", _W(r"POLISH|POLSKA|UKRAINIAN|GERMAN|BAVARIAN|SERBIAN|BOSNIAN|CROATIAN|RUSSIAN|FRENCH|BISTRO|BRASSERIE|IRISH|BRITISH|SWEDISH|NORWEGIAN|NORSKE|DANISH|SPANISH|TAPAS|PORTUGUESE|EUROPEAN|LITHUANIAN|CZECH|HUNGARIAN|ROMANIAN|GEORGIAN|PIEROGI|PIEROGIES|HAUS|BIERGARTEN|BEER GARDEN|BIERHALLE|RATHSKELLER|STUBE|SCHNITZEL|MADERS|KEGELS|SWISS|SLOVENIAN|FONDUE")),
    ("Bar & Pub", _W(r"PUB|TAVERN|BAR|SALOON|LOUNGE|TAP|TAPS|TAPROOM|TAPHOUSE|BREWING|BREWERY|BREWPUB|BEER|ALE HOUSE|GASTROPUB|COCKTAILS?|WINE|WINERY|DISTILLERY|DISTILLING|INN|PADDY|BARS")),
]
GCAT = [(c, re.compile(p)) for c, p in [
    ("Teriyaki", r"Teriyaki"), ("Pizza", r"Pizza"), ("Hawaiian", r"Hawaiian"), ("Filipino", r"Filipino"), ("Coffee & Café", r"Coffee|Cafe|Espresso|Tea house|Bubble tea"),
    ("Bakery & Sweets", r"Bakery|Donut|Dessert|Ice cream|Pastry|Cake|Frozen yogurt|Chocolate|Bagel|Pie shop|Candy"),
    ("Mexican", r"Mexican|Taco|Burrito|Tex-Mex|Taqueria"), ("Latin & Caribbean", r"Latin|Caribbean|Cuban|Puerto Rican|Jamaican|Peruvian|Colombian|Salvadoran|Brazilian|Venezuelan|Argentin|Haitian"),
    ("Japanese & Sushi", r"Japanese|Sushi|Ramen"), ("Chinese", r"Chinese|Cantonese|Dim sum|Szechuan|Dumpling|Hot pot"),
    ("Korean", r"Korean"), ("Thai", r"Thai"), ("Vietnamese", r"Vietnamese|Pho"), ("South Asian", r"Indian|Pakistani|Nepal|Bangladeshi|Sri Lankan"),
    ("Mediterranean & Middle Eastern", r"Mediterranean|Middle Eastern|Greek|Lebanese|Falafel|Halal|Turkish|Persian|Israeli|Afghan|Shawarma"),
    ("African", r"African|Ethiopian|Nigerian|Moroccan|Eritrean|Somali"), ("Italian", r"Italian"),
    ("Hot Dogs", r"Hot dog"), ("Burgers", r"Hamburger|Burger"), ("Seafood", r"Seafood|Fish|Oyster|Poke|Cajun"),
    ("Chicken & Wings", r"Chicken"), ("BBQ", r"Barbecue"), ("Steakhouse", r"Steak"),
    ("Soul & Southern", r"Soul food|Southern"), ("Sandwiches & Deli", r"Sandwich|Deli|Cheesesteak"),
    ("Healthy & Vegan", r"Vegan|Vegetarian|Health food|Salad|Juice"), ("Breakfast & Diner", r"Breakfast|Brunch|Diner|Pancake"),
    ("German & European", r"French|German|Polish|Ukrainian|Spanish|Tapas|Irish|European|Eastern European|Serbian|Russian|Bistro|Scandinavian|Swiss|Belgian|Dutch|Fondue"),
    ("Bar & Pub", r"Bar\b|Pub|Brewpub|Brewery|Tavern|Gastropub|Wine bar|Cocktail|Beer"),
    # a primary "American" category is an answer too, so a later "Bar" tag doesn't turn a family restaurant into a pub
    ("American & Other", r"American restaurant|Eclectic restaurant|Fine dining restaurant|Family restaurant|Southwestern"),
]]


def cuisine(name_key, gcats, raw=""):
    for c, pat in CUISINE_RULES:
        if pat.search(name_key or ""):
            return c
    cats = [x for x in (gcats or "").split("|") if x]
    for cat in cats:
        for c, pat in GCAT:
            if pat.search(cat):
                return c
    if re.search(r"\bCAF[EÉ]\b", (raw or "").upper()) and not cats:
        return "Coffee & Café"
    return "American & Other"


# Typical food-cost % by cuisine (industry rule-of-thumb ranges, midpoint)
FOOD_COST = {"Pizza": 26, "Coffee & Café": 24, "Bakery & Sweets": 25, "Frozen Custard": 24, "Mexican": 28, "Latin & Caribbean": 30,
             "Japanese & Sushi": 34, "Chinese": 30, "Korean": 32, "Thai": 30, "Vietnamese": 30, "South Asian": 28,
             "Mediterranean & Middle Eastern": 30, "African": 30, "Italian": 29, "Hot Dogs": 31, "Teriyaki": 30, "Hawaiian": 31, "Filipino": 30, "Burgers": 31,
             "Chicken & Wings": 33, "Seafood": 36, "BBQ": 34, "Steakhouse": 38, "Supper Club": 35, "Soul & Southern": 32,
             "Sandwiches & Deli": 30, "Healthy & Vegan": 32, "Breakfast & Diner": 27, "German & European": 30, "Bar & Pub": 27,
             "American & Other": 30}
# Pre-tax net margin benchmarks by segment
MARGIN = {1: 0.075, 2: 0.05, 3: 0.055, 4: 0.045}
MARGIN_CUISINE = {"Bar & Pub": 0.10, "Steakhouse": 0.09, "Pizza": 0.07, "Coffee & Café": 0.08, "Teriyaki": 0.07}
SPEND = {1: 13, 2: 28, 3: 62, 4: 165}   # typical per-person spend by price tier
