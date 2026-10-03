"""specid_ref.py - reference implementation (specification by example) for the SpecID MVP.
Not production code. Python 3.10+. Standard library only, except text_sim() which needs rapidfuzz (baselines, look-alike guard)."""
import copy
import ipaddress
import re
import socket

# ---------- tables ----------
NPS_DN = {"1/2": 15, "3/4": 20, "1": 25, "1-1/4": 32, "1-1/2": 40, "2": 50, "2-1/2": 65, "3": 80, "4": 100,
          "5": 125, "6": 150, "8": 200, "10": 250, "12": 300, "14": 350, "16": 400, "18": 450, "20": 500, "24": 600}
DN_NPS = {v: k for k, v in NPS_DN.items()}
CLASSES = {150, 300, 600, 900, 1500, 2500}
STOP = {"ASTM", "TYPE", "FOR", "OF", "AND", "WITH", "TO", "THE", "A", "ON"}
WATCH = {"NACE", "LTCS", "CRYO", "CRYOGENIC", "BELLOWS", "SOUR", "HIC", "ATEX", "IECEX", "FIRESAFE", "FIREPROOF", "EPOXY", "LINED"}

def take(rx, t):
    m = re.search(rx, t)
    return (m, t[:m.start()] + " " + t[m.end():]) if m else (None, t)

def note(a, key, text):
    """Record a conversion or inference so the evidence card can show it (provenance)."""
    if text: a.setdefault("_notes", {})[key] = text

# ---------- 1. normalise ----------
def normalise(t):
    t = t.upper()
    t = re.sub(r'["\u201c\u201d]', " IN ", t)
    t = re.sub(r"[,;()]", " ", t)
    t = re.sub(r"/(?=[A-Z])", " ", t)                            # SS316/GRAF -> SS316 GRAF (fractions keep their slash)
    t = re.sub(r"(\d)\s*(?:INCHES|INCH|IN)\b", r"\1 IN", t)       # 4IN, 4 INCH -> 4 IN
    t = re.sub(r"\bDN\s*(\d+)\b", r"\1 NB", t)                    # DN100 -> 100 NB
    t = re.sub(r"(\d)\s*NB\b", r"\1 NB", t)
    t = re.sub(r"(\d+)\s*#", r"CL\1", t)                          # 150# -> CL150
    t = re.sub(r"\bCLASS\s*(\d+)", r"CL\1", t)
    t = re.sub(r"\bCL\s+(\d+)", r"CL\1", t)
    t = re.sub(r"\bSCH(?:EDULE)?\.?\s*(\d+S?|STD|XS|XXS)\b", r"SCH\1", t)
    t = re.sub(r"\bGR(?:ADE)?\.?\s*([A-Z0-9][A-Z0-9.]*)", r"GR\1", t)   # GR.B / GRADE B -> GRB
    for a, b in (("SMLS", "SEAMLESS"), ("FLGD", "FLANGED"), ("WND", "WOUND"), ("GRAF", "GRAPHITE"), ("HD", "HEAD"), ("FLG", "FLANGE")):
        t = re.sub(rf"\b{a}\b", b, t)
    return re.sub(r"\s+", " ", t).strip()

# ---------- 2. attribute extractors (Tier 1: rules) ----------
def take_size(t):
    m, t2 = take(r"\b((?:\d+[- ])?\d+/\d+|\d+)\s*IN\b", t)
    if m:
        nps = m.group(1).replace(" ", "-"); dn = NPS_DN.get(nps)
        return dn, t2, (f"{nps} IN = DN{dn}" if dn else f"{nps} IN is not a standard size")
    m, t2 = take(r"\b(\d+)\s*NB\b", t)
    if m:
        dn = int(m.group(1)); ok = dn in DN_NPS
        return (dn if ok else None), t2, (f"{dn} NB = DN{dn}" if ok else f"{dn} NB is not a standard size")
    return None, t, None

def take_class(t):
    m, t2 = take(r"\bCL(\d{3,4})\b", t)
    return ((int(m.group(1)) if int(m.group(1)) in CLASSES else None), t2) if m else (None, t)

MAT = [(r"\bA216\s*(WCB|WCC)\b", "A216-{0}"), (r"\b(WCB|WCC)\b", "A216-{0}"),
       (r"\bA351\s*(CF8M|CF8)\b", "A351-{0}"), (r"\b(CF8M|CF8)\b", "A351-{0}"),
       (r"\bA182\s*F\s*(304L?|316L?|321|347)\b", "A182-F{0}"), (r"\bF(304L?|316L?|321|347)\b", "A182-F{0}"),
       (r"\bA105\b", "A105"), (r"\bA106\s*(?:GR)?\s*([ABC])\b", "A106-{0}"), (r"\bA106\b", "A106-?"),
       (r"\bA53\s*(?:GR)?\s*([AB])\b", "A53-{0}"),
       (r"\bSS\s*(304L?|316L?|321|347)\b", "SS{0}"), (r"\b(304L?|316L?|321|347)\s*SS\b", "SS{0}")]

def take_material(t):
    for rx, fmt in MAT:
        m, t2 = take(rx, t)
        if m:
            code = fmt.format(*m.groups()); written = m.group(0).replace(" ", "")
            return code, t2, (None if written.startswith(code.split("-")[0]) else f"{m.group(0)} -> {code}")
    return None, t, None

def ex_valve(t):
    a = {}
    m, t = take(r"\b(GATE|GLOBE|CHECK|BALL|BUTTERFLY)\b", t)
    if m: a["valve_type"] = m.group(1)
    else:
        m, t = take(r"\b(GV|GLV|CV|BV)\b", t)
        a["valve_type"] = {"GV": "GATE", "GLV": "GLOBE", "CV": "CHECK", "BV": "BALL"}[m.group(1)] if m else None
        if m: note(a, "valve_type", f"{m.group(1)} = {a['valve_type']}")
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n); a["pressure_class"], t = take_class(t)
    a["body_material"], t, n = take_material(t); note(a, "body_material", n)
    fl, t = take(r"\bFLANGED\b", t); face, t = take(r"\b(RF|FF|RTJ)\b", t)
    if fl or face: a["end_connection"] = "FLANGED-" + (face.group(1) if face else "?")
    else:
        m, t = take(r"\b(BW|SW|SCRD|THRD|NPT)\b", t)
        a["end_connection"] = {"BW": "BW", "SW": "SW"}.get(m.group(1), "THRD") if m else None
    m, t = take(r"\bAPI\s*(600|602|603|6D|608|594)\b", t); a["design_standard"] = "API-" + m.group(1) if m else None
    m, t = take(r"\bTRIM\s*([A-Z0-9]+)\b", t); a["trim"] = m.group(1) if m else None
    return a, t

def ex_pipe(t):
    a = {}
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n)
    m, t = take(r"\bSCH(\d+S?|STD|XS|XXS)\b", t)
    if not m: m, t = take(r"\b()(STD|XS|XXS)\b", t); s = m.group(2) if m else None   # bare STD / XS / XXS
    else: s = m.group(1)
    dn = a["size_dn"]
    if s == "STD" and dn and dn <= 250: s = "40"; note(a, "schedule", f"STD = SCH40 (DN{dn} <= 250)")   # SME to verify
    if s == "XS" and dn and dn <= 200: s = "80"; note(a, "schedule", f"XS = SCH80 (DN{dn} <= 200)")     # SME to verify
    a["schedule"] = s
    a["material"], t, n = take_material(t); note(a, "material", n)
    m, t = take(r"\b(SEAMLESS|ERW|WELDED)\b", t)
    p = {"SEAMLESS": "SEAMLESS", "ERW": "WELDED", "WELDED": "WELDED"}[m.group(1)] if m else None
    if p is None and (a["material"] or "").startswith("A106"): p = "SEAMLESS"; note(a, "process", "implied by A106")   # spec-implied
    a["process"] = p
    m, t = take(r"\b(PE|BE|PBE|TBE)\b", t); a["end_finish"] = m.group(1) if m else None
    return a, t

def ex_flange(t):
    a = {}
    typ = None
    for rx, v in ((r"\bWELD\s*NECK\b|\bWN\b", "WN"), (r"\bSLIP\s*-?\s*ON\b|\bSO\b", "SO"), (r"\bBLIND\b|\bBL\b", "BLIND"),
                  (r"\bLAP\s*JOINT\b|\bLJ\b", "LJ"), (r"\bSOCKET\s*WELD\b|\bSW\b", "SW"), (r"\bTHREADED\b|\bTHRD\b|\bSCRD\b", "THRD")):
        m, t = take(rx, t)
        if m: typ = v; break
    a["flange_type"] = typ
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n); a["pressure_class"], t = take_class(t)
    m, t = take(r"\b(RF|FF|RTJ)\b", t); a["face"] = m.group(1) if m else None
    a["material"], t, n = take_material(t); note(a, "material", n)
    return a, t

def ex_fastener(t):
    a = {}
    m, t = take(r"\b(STUD|NUT|BOLT|SCREW)\b", t); a["fastener_type"] = m.group(1) if m else None
    m, t = take(r"\bM(\d{1,2})\s*X\s*(\d{1,3})\b", t)
    if m: a["thread"], a["length_mm"] = "M" + m.group(1), int(m.group(2))
    else:
        m, t = take(r"\bM(\d{1,2})\b", t); a["thread"] = "M" + m.group(1) if m else None; a["length_mm"] = None
    m, t = take(r"\b(?:A19[34]\s*)?(?:GR)?(4\.6|5\.6|8\.8|10\.9|12\.9|B7|2H)\b", t); a["strength"] = m.group(1) if m else None
    m, t = take(r"\b(HEX|SOCKET|CSK)\b", t); a["head"] = m.group(1) if m else None; _, t = take(r"\bHEAD\b", t)
    m, t = take(r"\b(ZN|ZINC|HDG|PTFE|GALV\w*)\b", t)
    a["coating"] = ("ZINC" if m.group(1) in ("ZN", "ZINC") else m.group(1)) if m else None; _, t = take(r"\bPLATED\b", t)
    if m and m.group(1) == "ZN": note(a, "coating", "ZN = ZINC")
    return a, t

def ex_motor(t):
    a = {}
    ind = bool(re.search(r"\b(INDUCTION|IND|SQ|SQUIRREL)\b", t)); ac = bool(re.search(r"\bAC\b", t))
    a["motor_type"] = "AC-IND" if (ind and ac) else ("AC" if ac else None)
    for w in ("AC", "INDUCTION", "IND", "SQ", "SQUIRREL", "CAGE"): _, t = take(rf"\b{w}\b", t)
    m, t = take(r"\b(\d+(?:\.\d+)?)\s*KW\b", t)
    if m: a["power_kw"] = float(m.group(1))
    else:
        m, t = take(r"\b(\d+(?:\.\d+)?)\s*HP\b", t); a["power_kw"] = round(float(m.group(1)) * 0.7457, 1) if m else None
        if m: note(a, "power_kw", f"{m.group(1)} HP = {a['power_kw']} kW")
    m, t = take(r"\b(\d{1,2})\s*(?:P|POLES?)\b", t); a["poles"] = int(m.group(1)) if m else None
    m, t = take(r"\b(\d{3,4})\s*RPM\b", t); a["rpm"] = int(m.group(1)) if m else None
    m, t = take(r"\b(\d{3,4})\s*V\b", t); a["voltage"] = int(m.group(1)) if m else None
    m, t = take(r"\bIP\s*(\d{2})\b", t); a["ip"] = "IP" + m.group(1) if m else None
    m, t = take(r"\b(B3|B5|B35|V1)\b", t); a["mounting"] = m.group(1) if m else None
    a["ex"] = a["frame"] = None
    return a, t

def ex_gasket(t):
    a = {}
    m, t = take(r"\bSPIRAL\s*WOUND\b|\bSPIRAL\b", t); a["gasket_type"] = "SPIRAL-WOUND" if m else None
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n); a["pressure_class"], t = take_class(t)
    a["winding_material"], t, n = take_material(t); note(a, "winding_material", n)
    m, t = take(r"\b(GRAPHITE|PTFE)\b", t); a["filler"] = m.group(1) if m else None
    return a, t

CATS = [("VALVE", r"\bVALVE\b|\bGV\b|\bGLV\b|\bBV\b", ex_valve), ("GASKET", r"\bGASKET\b", ex_gasket), ("FLANGE", r"\bFLANGE\b", ex_flange),
        ("PIPE", r"\bPIPE\b", ex_pipe), ("FASTENER", r"\b(BOLT|STUD|NUT|SCREW)\b", ex_fastener), ("MOTOR", r"\bMOTOR\b", ex_motor)]

def extract(text, mpn=None, maker=None):
    t = normalise(text)
    for cat, rx, fn in CATS:
        if re.search(rx, t):
            if cat != "FASTENER": _, t = take(r"\b(VALVE|GASKET|FLANGE|PIPE|MOTOR)\b", t)
            attrs, t = fn(t)
            notes = attrs.pop("_notes", {})
            toks = [x for x in re.findall(r"[A-Z0-9][A-Z0-9.\-]*", t) if x not in STOP]
            return {"category": cat, "attrs": attrs, "notes": notes, "residual": toks, "mpn": mpn, "maker": maker}
    return {"category": None, "attrs": {}, "notes": {}, "residual": re.findall(r"[A-Z0-9][A-Z0-9.\-]*", t), "mpn": mpn, "maker": maker}

# ---------- 3. templates and decision ----------
TEMPLATES = {
 "VALVE":    dict(core=["valve_type", "size_dn", "pressure_class", "body_material", "end_connection"], ext=["design_standard", "trim"], critical=True),
 "PIPE":     dict(core=["size_dn", "schedule", "material", "process"], ext=["end_finish"], critical=True),
 "FLANGE":   dict(core=["flange_type", "size_dn", "pressure_class", "face", "material"], ext=[], critical=True),
 "FASTENER": dict(core=["fastener_type", "thread", "length_mm", "strength"], ext=["head", "coating"], critical=False),
 "MOTOR":    dict(core=["motor_type", "power_kw", "poles"], ext=["rpm", "voltage", "ip", "mounting"], critical=True),
 "GASKET":   dict(core=["gasket_type", "size_dn", "pressure_class", "winding_material", "filler"], ext=[], critical=True)}

_MAT_TEXT = "Same family and same spec; generic vs specific is PARTIAL"
RULE_TEXT = {"size_dn": "Compared as DN; inch and NB converted by table B.1; non-standard sizes stay unknown",
             "schedule": "STD = SCH40 only for DN <= 250; XS = SCH80 only for DN <= 200",
             "material": _MAT_TEXT, "body_material": _MAT_TEXT, "winding_material": _MAT_TEXT,
             "process": "A106 implies SEAMLESS", "power_kw": "Equal within 1% (HP converted at 0.7457 kW/HP)",
             "rpm": "Equal within 5%", "end_connection": "FLANGED with no face is PARTIAL against a specific face"}

def rule(cat, attr, level):
    """Every comparison cites the rule that produced it (shown on the evidence card)."""
    default = "Must match" if level == "core" else "Conflict vetoes; a value stated on one side only flags the pair"
    return {"id": f"{cat}.{attr}", "text": RULE_TEXT.get(attr, default)}

def family(code):
    if code.startswith("A182-F"): return code[6:]
    if code.startswith("SS"): return code[2:]
    if code == "A351-CF8M": return "316"
    if code == "A351-CF8": return "304"
    if code.startswith(("A216", "A105", "A106", "A53")): return "CS"
    return code

def compare(name, x, y):
    if x is None and y is None: return "MISSING_BOTH"
    if x is None or y is None: return "MISSING_ONE"
    if x == y: return "MATCH"
    if name in ("material", "body_material", "winding_material"):
        if family(x) != family(y): return "CONFLICT"
        gx, gy = x.endswith("?") or x.startswith("SS"), y.endswith("?") or y.startswith("SS")
        return "PARTIAL" if gx != gy else "CONFLICT"            # one generic, one specific, same family
    if name == "end_connection":
        if x.startswith("FLANGED") and y.startswith("FLANGED") and "?" in (x[-1], y[-1]): return "PARTIAL"
        return "CONFLICT"
    if name == "power_kw": return "MATCH" if abs(x - y) <= 0.01 * max(x, y) else "CONFLICT"
    if name == "rpm": return "MATCH" if abs(x - y) <= 0.05 * max(x, y) else "CONFLICT"
    return "CONFLICT"

def decide(A, B, templates=None):
    """Veto -> unknown-state -> verdict. Returns verdict, route, reasons, evidence card.
    `templates` lets a draft rulebook be previewed without activating it."""
    if A["category"] is None or B["category"] is None:
        return dict(verdict="INSUFFICIENT_DATA", route="REVIEW", reasons=["category not recognised"], evidence=[])
    if A["category"] != B["category"]:
        return dict(verdict="NOT_EQUIVALENT", route="NONE", reasons=["category differs"], evidence=[])
    T = (templates or TEMPLATES)[A["category"]]
    core = [c for c in T["core"] if not (A["attrs"].get("fastener_type") == "NUT" and c == "length_mm")]
    ev, conflicts, missing, flags = [], [], [], []
    for level, names in (("core", core), ("ext", T["ext"])):
        for n in names:
            s = compare(n, A["attrs"].get(n), B["attrs"].get(n)); r = rule(A["category"], n, level)
            ev.append(dict(attr=n, level=level, a=A["attrs"].get(n), b=B["attrs"].get(n), status=s,
                           rule=r["id"], rule_text=r["text"], note_a=A.get("notes", {}).get(n), note_b=B.get("notes", {}).get(n)))
            if s == "CONFLICT": conflicts.append(n)
            elif level == "core" and s in ("MISSING_ONE", "MISSING_BOTH", "PARTIAL"): missing.append(n)
            elif level == "ext" and s in ("MISSING_ONE", "PARTIAL"): flags.append(n + " unverified")
    tech = lambda r: {x for x in r if any(c.isdigit() for c in x) or x in WATCH}
    diff = tech(A["residual"]) ^ tech(B["residual"])
    if diff: flags.append("unexplained tokens: " + " ".join(sorted(diff)))
    if conflicts: return dict(verdict="NOT_EQUIVALENT", route="NONE", reasons=["conflict: " + ", ".join(conflicts)], evidence=ev)
    if missing: return dict(verdict="INSUFFICIENT_DATA", route="REVIEW", reasons=["core attribute not verifiable: " + ", ".join(missing)], evidence=ev)
    same_make = A["mpn"] and A["mpn"] == B["mpn"] and (A["maker"] or "").upper() == (B["maker"] or "").upper()
    if T["critical"]: flags.append("critical class: maker-checker")
    return dict(verdict="IDENTICAL" if same_make else "EQUIVALENT", route="REVIEW" if flags else "AUTO_ELIGIBLE", reasons=flags, evidence=ev)

# ---------- 4. constrained clustering (no cluster may contain a conflict) ----------
def constrained_clusters(n, edges, conflict):
    """edges: [(i, j, score)] for EQUIVALENT/IDENTICAL pairs; conflict(i, j) -> True if verdict would be NOT_EQUIVALENT."""
    parent, members = list(range(n)), {i: {i} for i in range(n)}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, j, s in sorted(edges, key=lambda e: -e[2]):
        ri, rj = find(i), find(j)
        if ri != rj and not any(conflict(a, b) for a in members[ri] for b in members[rj]):
            parent[rj] = ri; members[ri] |= members.pop(rj)
    return sorted(map(sorted, members.values()))

# ---------- 5. CNMC id (non-significant, Luhn check digit) and 40-char SAP short text ----------
def luhn_digit(body):
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10

def new_cnmc(seq): body = f"{seq:010d}"; return f"NMC-{body}{luhn_digit(body)}"
def cnmc_valid(c): m = re.fullmatch(r"NMC-(\d{10})(\d)", c); return bool(m) and luhn_digit(m.group(1)) == int(m.group(2))

def short_desc(S, limit=40):
    a, c = S["attrs"], S["category"]; inch = lambda: DN_NPS.get(a.get("size_dn"), "?") + "IN"
    parts = {"VALVE": ["VLV", a.get("valve_type"), inch(), f"CL{a.get('pressure_class')}", a.get("body_material"), (a.get("end_connection") or "").replace("FLANGED-", "FLGD ")],
             "PIPE": ["PIPE", {"SEAMLESS": "SMLS", "WELDED": "ERW"}.get(a.get("process")), inch(), f"SCH{a.get('schedule')}", a.get("material")],
             "FLANGE": ["FLG", a.get("flange_type"), inch(), f"CL{a.get('pressure_class')}", a.get("face"), a.get("material")],
             "FASTENER": [a.get("fastener_type"), a.get("head"), f"{a.get('thread')}X{a.get('length_mm')}" if a.get("length_mm") else a.get("thread"), a.get("strength"), {"ZINC": "ZN"}.get(a.get("coating"), a.get("coating"))],
             "MOTOR": ["MOTOR", a.get("motor_type", "").replace("-", " "), f"{a.get('power_kw'):g}KW" if a.get("power_kw") else None, f"{a.get('poles')}P"],
             "GASKET": ["GASKET", "SPW", inch(), f"CL{a.get('pressure_class')}", a.get("winding_material"), (a.get("filler") or "")[:5]]}[c]
    s = " ".join(p for p in parts if p)
    return s if len(s) <= limit else None          # None -> abbreviate further or route to a human


# ---------- 6. signature features: baselines, look-alike guard, ask-don't-guess, rule-impact preview ----------
def text_sim(x, y):
    """Token-set similarity of the NORMALISED texts: a deliberately fair text-only baseline. Needs rapidfuzz."""
    from rapidfuzz import fuzz
    return fuzz.token_set_ratio(normalise(x), normalise(y)) / 100

def numeric_tokens(t): return sorted(re.findall(r"\d+(?:\.\d+)?", t.upper()))
def baseline_b1(x, y, tau): return text_sim(x, y) >= tau                                   # text only
def baseline_b2(x, y, tau): return text_sim(x, y) >= tau and numeric_tokens(x) == numeric_tokens(y)   # text + numbers must agree

def lookalike_class(sim, verdict, hi=0.85, lo=0.75):
    """Near-Miss Radar: LOOKALIKE_VETOED = text says 'same', SpecID vetoed; HIDDEN_TWIN = text says 'different', SpecID says equivalent."""
    if verdict == "NOT_EQUIVALENT" and sim >= hi: return "LOOKALIKE_VETOED"
    if verdict in ("EQUIVALENT", "IDENTICAL") and sim <= lo: return "HIDDEN_TWIN"
    return None

def supply_attribute(S, attr, value, source):
    """Ask-don't-guess loop: a reviewer supplies a missing attribute; provenance is kept; the pair is then re-decided."""
    return {**S, "attrs": {**S["attrs"], attr: value}, "notes": {**S.get("notes", {}), attr: f"supplied by user: {source}"}}

def impact_preview(pairs, new_templates):
    """Rulebook impact preview: which stored pairs would change verdict or route under a draft template set."""
    out = []
    for i, (a, b) in enumerate(pairs):
        old, new = decide(a, b), decide(a, b, new_templates)
        if (old["verdict"], old["route"]) != (new["verdict"], new["route"]):
            out.append(dict(pair=i, old=old["verdict"], new=new["verdict"], old_route=old["route"], new_route=new["route"]))
    return out


# ---------- 7. air-gap proof: egress guard (defence in depth; the network-level guarantee is the internal Compose network) ----------
class EgressGuard:
    """Refuse every outbound connection and name lookup except loopback and explicitly allowed hosts (for example the database); count the attempts."""
    def __init__(self, allowed=()):
        self.allowed, self.blocked, self._orig = set(allowed) | {"localhost"}, 0, None
    def _check(self, host):
        try: ok = ipaddress.ip_address(host).is_loopback
        except ValueError: ok = False
        if not (ok or host in self.allowed):
            self.blocked += 1
            raise PermissionError(f"egress blocked: {host}")
    def install(self):
        g, self._orig = self, (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)
        def connect(sock, address): g._check(address[0]); return g._orig[0](sock, address)
        def connect_ex(sock, address): g._check(address[0]); return g._orig[1](sock, address)
        def getaddrinfo(host, *a, **k): g._check(host); return g._orig[2](host, *a, **k)
        socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo
    def uninstall(self):
        socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = self._orig
