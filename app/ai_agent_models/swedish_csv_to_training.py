from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


TARGET_LABELS: tuple[str, ...] = (
    "Dagligvaror",
    "Restaurang",
    "Fika & Kafé",
    "Godis & Snacks",
    "Alkohol",
    "Boende: Hyra & avgifter",
    "Hem & inredning",
    "Bygg & verktyg",
    "Lokaltrafik",
    "Taxi & samåkning",
    "Bil: bränsle & laddning",
    "Bil: parkering & vägavgifter",
    "Resor: transport & boende",
    "Resor: mat & nöjen på resa",
    "Apotek & medicin",
    "Vård & tandvård",
    "Kroppsvård & hygien",
    "Optik",
    "Kläder & skor",
    "Elektronik",
    "Övriga prylar",
    "Nöjen & kultur",
    "Sport & träning",
    "Sportutrustning",
    "Hobby & skapande",
    "Böcker & media",
    "Barn",
    "Husdjur",
    "Finans & avgifter",
    "Övrigt/Okänt",
)


# 1) Legacy-category -> target (coarse; merchant/keywords may override)
LEGACY_TO_TARGET: dict[str, str] = {
    "Alkohol": "Alkohol",
    "Mat": "Restaurang",
    "Livsmedel": "Dagligvaror",
    "Godis": "Godis & Snacks",
    "Hyra": "Boende: Hyra & avgifter",
    "Avgift": "Boende: Hyra & avgifter",
    "Hem": "Hem & inredning",
    "Kök": "Hem & inredning",
    "Prylar": "Övriga prylar",
    "Kläder": "Kläder & skor",
    "Kroppsvård": "Kroppsvård & hygien",
    "Hygien": "Kroppsvård & hygien",
    "Kosmetika": "Kroppsvård & hygien",
    "Hälsovård": "Vård & tandvård",
    "Medicin": "Apotek & medicin",
    "Optik": "Optik",
    "Resor": "Resor: transport & boende",
    "Nöjen": "Nöjen & kultur",
    "Sport/Fritid": "Sport & träning",
    "Sport": "Sport & träning",
    "Golf": "Sport & träning",
    "Dykning": "Sport & träning",
    "Böcker": "Böcker & media",
    "Foto": "Böcker & media",
    "Video": "Böcker & media",  # includes film, DVD, etc.
    "Lek": "Barn",             # coarse; keyword rules will refine sometimes
    "Spel": "Böcker & media",  # per your choice
    "Barn": "Barn",
    "Husdjur": "Husdjur",
    "Finans": "Finans & avgifter",
    "Lån": "Finans & avgifter",
    "Ränta": "Finans & avgifter",
    "Bank": "Finans & avgifter",
    "Avgifter": "Finans & avgifter",
    "Överföring": "Finans & avgifter",
    "Utlägg": "Finans & avgifter",
    "Present": "Övrigt/Okänt",  # optional: split later if you add a Gifts category
    "Post": "Övrigt/Okänt",     # per your choice
}


# 2) Merchant overrides (high confidence)
MERCHANT_TO_TARGET: dict[str, str] = {
    "systembolaget": "Alkohol",

    #---Transport ---
    "sl": "Lokaltrafik",
    "arlandabuss": "Resor: transport & boende",
    "sas": "Resor: transport & boende",
    "sj": "Resor: transport & boende",
    "taxi": "Taxi & samåkning",
    "taxi stockholm": "Taxi & samåkning",
    "taxi kurir": "Taxi & samåkning",
    "uber": "Taxi & samåkning",
    "lyft": "Taxi & samåkning",

    #--- Vård och syn ---
    "apoteket": "Apotek & medicin",
    "folktandvården": "Vård & tandvård",
    "tandläkare": "Vård & tandvård",
    "synsam": "Optik",
    "synoptik": "Optik",
    "öga": "Optik",
    "ögat": "Optik",

    #--- Böcker och media ---
    "akademibokhandeln": "Böcker & media",
    "bokskotten": "Böcker & media",
    "bok-skotten": "Böcker & media",
    "webhallen": "Elektronik",
    "elgiganten": "Elektronik",
    "onoff": "Elektronik",
    "spotify": "Böcker & media",
    "netflix": "Böcker & media",
    "steam": "Böcker & media",
    "nintendo": "Böcker & media",

    #--- Hus och hem ---
    "ikea": "Hem & inredning",
    "hemtex": "Hem & inredning",
    "cervera": "Hem & inredning",
    "bauhaus": "Bygg & verktyg",
    "k-rauta": "Bygg & verktyg",
    "byggmax": "Bygg & verktyg",
    "clas ohlson": "Bygg & verktyg",

    #--- Sport och utrustning ---
    "intersport": "Sportutrustning",
    "stadium": "Sportutrustning",
    "xxl": "Sportutrustning",
    "sats": "Sport & träning",
    "nautilus": "Sport & träning",

    #--- Husdjur ---
    "zoo kompaniet": "Husdjur",
    "arken zoo": "Husdjur",

    # --- Groceries / supermarkets ---
    "ica": "Dagligvaror",
    "hemköp": "Dagligvaror",
    "hemkop": "Dagligvaror",
    "coop": "Dagligvaror",
    "konsum": "Dagligvaror",

    # --- Finans & avgifter ---
    "överföring": "Finans & avgifter",
    "swish": "Finans & avgifter",
}


# 3) Keyword helpers for ambiguous merchants
_RE_NUMBER_RUN = re.compile(r"\b\d{3,}\b")


def _norm(s: object) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _scrub_text(s: str) -> str:
    """
    Keep semantics but reduce overfitting to IDs/phone-like runs.
    """
    s = _RE_NUMBER_RUN.sub("<NUM>", s)
    return s


def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
    return any(n in haystack for n in needles)


def _keyword_based_target(spec: str) -> Optional[str]:
    """
    Keyword-only signal for cases like Pressbyrån / NK / Åhléns etc.
    """
    t = spec.lower()

    # transport / vehicle
    if _contains_any(t, ("parkering", "p-bot", "pbot", "vägavgift", "broavgift", "trängsel")):
        return "Bil: parkering & vägavgifter"
    if _contains_any(t, ("bensin", "diesel", "tank", "tanka", "ladd", "el-ladd", "el.")):
        return "Bil: bränsle & laddning"

    # food/drink
    if _contains_any(t, ("fika", "kaffe", "latte", "cappuccino", "semla", "konditori")):
        return "Fika & Kafé"
    if _contains_any(t, ("pizza", "lunch", "middag", "sushi", "hamburg", "restaurang", "korv")):
        return "Restaurang"
    if _contains_any(t, ("tuggummi", "läkerol", "godis", "choklad", "chips", "glass", "snacks", "halstabletter")):
        return "Godis & Snacks"

    # health/body
    if _contains_any(t, ("tabletter", "medicin", "penicillin", "recept", "salva")):
        return "Apotek & medicin"
    if _contains_any(t, ("tandläk", "tandvård", "undersökning", "hygienist")):
        return "Vård & tandvård"
    if _contains_any(t, ("schampo", "balsam", "deo", "nagellack", "smink", "parfym", "dusch")):
        return "Kroppsvård & hygien"

    # books/media/electronics
    if _contains_any(t, ("dvd", "bluray", "bok", "kindle", "ljudbok", "spel", "xbox", "switch", "ps3", "ps4", "steam")):
        return "Böcker & media"
    if _contains_any(t, ("router", "ssd", "hårddisk", "hdmi", "telefon", "ipad", "iphone", "laptop", "usb")):
        return "Elektronik"

    # clothing
    if _contains_any(t, ("byxor", "tröja", "skor", "jacka", "strump", "underkläder", "klänning")):
        return "Kläder & skor"

    # home
    if _contains_any(t, ("gardin", "lakan", "kudde", "duk", "glas", "bestick", "stekpanna", "kruka", "vas")):
        return "Hem & inredning"

    # sport
    if _contains_any(t, ("medlemskap", "gymkort", "träning", "entré", "bad", "sim", "greenfee", "golf", "dyk")):
        return "Sport & träning"
    if _contains_any(t, ("handske", "hjälm", "skidor", "stavar", "pjäxor", "cykel", "löparskor", "underställ")):
        return "Sportutrustning"

    # pets / kids
    if _contains_any(t, ("papego", "katt", "hund", "pellets", "fågel", "bur", "kattsand")):
        return "Husdjur"
    if _contains_any(t, ("barn", "elsa", "lovisa", "leksak", "dagis", "skola")):
        return "Barn"

    return None


def map_to_target(stalle: str, legacy_cat: str, spec: str) -> str:
    st = stalle.lower().strip()
    sp = spec.lower().strip()
    lc = legacy_cat.strip()

    # merchant rules (exact)
    if st in MERCHANT_TO_TARGET:
        return MERCHANT_TO_TARGET[st]

    # merchant rules (prefixes for chains / store variants)
    grocery_prefixes = (
        "ica",
        "hemköp", "hemkop",
        "coop",
        "konsum",
    )
    if any(st.startswith(p) for p in grocery_prefixes):
        return "Dagligvaror"

    # keyword rules (help disambiguate)
    kw = _keyword_based_target(spec=sp)
    if kw is not None:
        return kw

    # legacy fallback
    if lc in LEGACY_TO_TARGET:
        return LEGACY_TO_TARGET[lc]

    return "Övrigt/Okänt"


@dataclass(frozen=True)
class ConvertConfig:
    csv_path: Path
    out_jsonl: Path = Path(__file__).with_name("purchase_training.jsonl")
    delimiter: str = ";"
    encoding: str = "utf-8"
    text_template: str = "{ställe} | {specifikation}"


def convert_csv_to_jsonl(cfg: ConvertConfig) -> None:
    df = pd.read_csv(cfg.csv_path, sep=cfg.delimiter, encoding=cfg.encoding, dtype=str)

    # Accept either Swedish headers or variants
    cols = {c.lower().strip(): c for c in df.columns}
    col_stalle = cols.get("ställe") or cols.get("stalle")
    col_kategori = cols.get("kategori")
    col_spec = cols.get("specifikation") or cols.get("spec")

    if not (col_stalle and col_kategori and col_spec):
        raise ValueError(
            "CSV must contain columns: Ställe;Kategori;Specifikation "
            f"(found: {list(df.columns)})"
        )

    examples = []
    allowed = set(TARGET_LABELS)

    for _, row in df.iterrows():
        stalle = _norm(row.get(col_stalle))
        legacy_cat = _norm(row.get(col_kategori))
        spec = _norm(row.get(col_spec))

        # Skip totally empty rows
        if not (stalle or legacy_cat or spec):
            continue

        label = map_to_target(stalle=stalle, legacy_cat=legacy_cat, spec=spec)
        if label not in allowed:
            label = "Övrigt/Okänt"

        text = cfg.text_template.format(
            ställe=_scrub_text(stalle),
            specifikation=_scrub_text(spec),
        ).strip()

        if not text:
            continue

        examples.append({"text": text, "label": label})

    cfg.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with cfg.out_jsonl.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    counts = pd.Series([ex["label"] for ex in examples]).value_counts()
    print(f"Wrote {len(examples)} rows to: {cfg.out_jsonl.resolve()}")
    print("\nLabel distribution (top 20):")
    print(counts.head(20).to_string())

def _project_root() -> Path:
    """
    Best-effort project root resolver.
    Assumes this file lives at: <root>/app/ai_agent_models/swedish_csv_to_training.py
    """
    return Path(__file__).resolve().parents[2]

def _test_data_csv(filename: str) -> str:
    """
    Returns an absolute path to a CSV inside <project_root>/test_data/.

    Raises FileNotFoundError with a helpful message if it doesn't exist.
    """
    root = _project_root()
    candidate = root / "test_data" / filename

    if not candidate.exists():
        raise FileNotFoundError(
            "Test CSV not found.\n"
            f"Looked for: {candidate}\n"
            "Make sure the file exists under <project_root>/test_data/ "
            "or change the filename to an existing test file."
        )
    return str(candidate)

# ... existing code ...
if __name__ == "__main__":
    # If you run this as a module, prefer:
    #   python -m app.ai_agent_models.swedish_csv_to_training
    csv_path = _test_data_csv("Ekonomi_copyfor_testingaa.csv")

convert_csv_to_jsonl(
    ConvertConfig(
        csv_path=csv_path,
    )
)