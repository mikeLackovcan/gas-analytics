"""IP master table.

Seeded with the major active EU interconnection points (post-Nord Stream era,
post-Russia–Ukraine transit shutdown 2025-01-01). Country pairs are oriented
country_from → country_to as the *positive* (nominal export) direction; ENTSOG
reports per-direction so we ingest both signs.

reporting_side picks which adjacent operator's print we ingest to avoid double
counting. Default "operator", flip per-IP when the adjacent print is cleaner.

This list is intentionally not exhaustive — extend as new IPs are observed in
ENTSOG operational data.
"""

IPS = [
    # Norway → EU
    {"id": "ITP-00064", "name": "Emden (NCS → DE)",        "country_from": "NO", "country_to": "DE", "tso_from": "GASSCO",  "tso_to": "GUD",      "vip_id": None, "reporting_side": "operator"},
    {"id": "ITP-00080", "name": "Dornum (NCS → DE)",       "country_from": "NO", "country_to": "DE", "tso_from": "GASSCO",  "tso_to": "GUD",      "vip_id": None, "reporting_side": "operator"},
    {"id": "ITP-00114", "name": "Zeebrugge (NCS → BE)",    "country_from": "NO", "country_to": "BE", "tso_from": "GASSCO",  "tso_to": "FLUXYS",   "vip_id": None, "reporting_side": "operator"},
    {"id": "ITP-00138", "name": "Dunkerque (NCS → FR)",    "country_from": "NO", "country_to": "FR", "tso_from": "GASSCO",  "tso_to": "GRTGAZ",   "vip_id": None, "reporting_side": "operator"},
    {"id": "ITP-00065", "name": "Easington (NCS → UK)",    "country_from": "NO", "country_to": "UK", "tso_from": "GASSCO",  "tso_to": "NGT",      "vip_id": None, "reporting_side": "operator"},

    # DE ↔ NL
    {"id": "ITP-00094", "name": "Oude Statenzijl H",       "country_from": "NL", "country_to": "DE", "tso_from": "GTS",     "tso_to": "GUD",      "vip_id": "VIP-TTF-THE", "reporting_side": "operator"},
    {"id": "ITP-00095", "name": "Oude Statenzijl L",       "country_from": "NL", "country_to": "DE", "tso_from": "GTS",     "tso_to": "GUD",      "vip_id": "VIP-TTF-THE", "reporting_side": "operator"},
    {"id": "ITP-00112", "name": "Bocholtz / Vreden",       "country_from": "NL", "country_to": "DE", "tso_from": "GTS",     "tso_to": "THYSSEN",  "vip_id": "VIP-TTF-THE", "reporting_side": "operator"},
    {"id": "ITP-00113", "name": "Zelzate / Eynatten",      "country_from": "BE", "country_to": "DE", "tso_from": "FLUXYS",  "tso_to": "THYSSEN",  "vip_id": "VIP-ZTP-THE", "reporting_side": "operator"},

    # DE ↔ CZ
    {"id": "ITP-00076", "name": "Brandov / OPAL",          "country_from": "DE", "country_to": "CZ", "tso_from": "GASCADE", "tso_to": "NET4GAS",  "vip_id": "VIP-THE-CZ",  "reporting_side": "operator"},
    {"id": "ITP-00077", "name": "Waidhaus",                "country_from": "CZ", "country_to": "DE", "tso_from": "NET4GAS", "tso_to": "OGE",      "vip_id": "VIP-THE-CZ",  "reporting_side": "operator"},

    # DE ↔ AT
    {"id": "ITP-00081", "name": "Oberkappel",              "country_from": "DE", "country_to": "AT", "tso_from": "BAYERNETS","tso_to": "GCA",     "vip_id": "VIP-THE-CEGH","reporting_side": "operator"},
    {"id": "ITP-00082", "name": "Überackern (SUDAL)",      "country_from": "DE", "country_to": "AT", "tso_from": "BAYERNETS","tso_to": "GCA",     "vip_id": "VIP-THE-CEGH","reporting_side": "operator"},

    # DE ↔ PL
    {"id": "ITP-00091", "name": "Mallnow (Yamal reverse)", "country_from": "DE", "country_to": "PL", "tso_from": "GASCADE", "tso_to": "GAZ-SYSTEM","vip_id": None, "reporting_side": "operator"},
    {"id": "ITP-00092", "name": "Lasów",                   "country_from": "DE", "country_to": "PL", "tso_from": "ONTRAS",  "tso_to": "GAZ-SYSTEM","vip_id": None, "reporting_side": "operator"},

    # NL ↔ BE
    {"id": "ITP-00101", "name": "Zelzate / 's Gravenvoeren","country_from": "NL", "country_to": "BE", "tso_from": "GTS",    "tso_to": "FLUXYS",   "vip_id": "VIP-TTF-ZTP", "reporting_side": "operator"},

    # BE ↔ FR
    {"id": "ITP-00121", "name": "Taisnières H / Blaregnies","country_from": "BE", "country_to": "FR","tso_from": "FLUXYS",  "tso_to": "GRTGAZ",   "vip_id": "VIP-ZTP-PEG", "reporting_side": "operator"},

    # DE ↔ FR
    {"id": "ITP-00141", "name": "Obergailbach / Medelsheim","country_from": "DE", "country_to": "FR","tso_from": "OGE",     "tso_to": "GRTGAZ",   "vip_id": "VIP-THE-PEG", "reporting_side": "operator"},

    # FR ↔ ES
    {"id": "ITP-00151", "name": "Pirineos (Larrau)",       "country_from": "FR", "country_to": "ES", "tso_from": "TEREGA",  "tso_to": "ENAGAS",   "vip_id": "VIP-PEG-PVB", "reporting_side": "operator"},
    {"id": "ITP-00152", "name": "Pirineos (Biriatou)",     "country_from": "FR", "country_to": "ES", "tso_from": "TEREGA",  "tso_to": "ENAGAS",   "vip_id": "VIP-PEG-PVB", "reporting_side": "operator"},

    # AT ↔ IT
    {"id": "ITP-00161", "name": "Tarvisio / Arnoldstein",  "country_from": "AT", "country_to": "IT", "tso_from": "TAG",     "tso_to": "SNAM",     "vip_id": "VIP-CEGH-PSV", "reporting_side": "operator"},

    # CH ↔ IT
    {"id": "ITP-00162", "name": "Passo Gries",             "country_from": "CH", "country_to": "IT", "tso_from": "FLUXSWISS","tso_to": "SNAM",    "vip_id": None, "reporting_side": "operator"},

    # SK ↔ AT
    {"id": "ITP-00171", "name": "Baumgarten",              "country_from": "SK", "country_to": "AT", "tso_from": "EUSTREAM", "tso_to": "GCA",     "vip_id": None, "reporting_side": "operator"},

    # CZ ↔ SK
    {"id": "ITP-00172", "name": "Lanžhot",                 "country_from": "SK", "country_to": "CZ", "tso_from": "EUSTREAM", "tso_to": "NET4GAS", "vip_id": None, "reporting_side": "operator"},

    # SK ↔ HU
    {"id": "ITP-00181", "name": "Veľké Zlievce",           "country_from": "SK", "country_to": "HU", "tso_from": "EUSTREAM", "tso_to": "FGSZ",    "vip_id": None, "reporting_side": "operator"},

    # AT ↔ HU
    {"id": "ITP-00182", "name": "Mosonmagyaróvár",         "country_from": "AT", "country_to": "HU", "tso_from": "GCA",      "tso_to": "FGSZ",    "vip_id": None, "reporting_side": "operator"},

    # HU ↔ RO
    {"id": "ITP-00191", "name": "Csanádpalota",            "country_from": "HU", "country_to": "RO", "tso_from": "FGSZ",     "tso_to": "TRANSGAZ","vip_id": None, "reporting_side": "operator"},

    # RO ↔ BG (post Trans-Balkan)
    {"id": "ITP-00201", "name": "Negru Vodă / Kardam",     "country_from": "RO", "country_to": "BG", "tso_from": "TRANSGAZ", "tso_to": "BULGARTRANSGAZ","vip_id": None, "reporting_side": "operator"},

    # BG ↔ GR (IGB)
    {"id": "ITP-00211", "name": "Komotini (IGB)",          "country_from": "BG", "country_to": "GR", "tso_from": "ICGB",     "tso_to": "DESFA",   "vip_id": None, "reporting_side": "operator"},

    # GR ↔ BG (Sidirokastro)
    {"id": "ITP-00212", "name": "Sidirokastro / Kulata",   "country_from": "GR", "country_to": "BG", "tso_from": "DESFA",    "tso_to": "BULGARTRANSGAZ","vip_id": None, "reporting_side": "operator"},

    # DK ↔ DE
    {"id": "ITP-00221", "name": "Ellund",                  "country_from": "DK", "country_to": "DE", "tso_from": "ENERGINET","tso_to": "GUD",     "vip_id": None, "reporting_side": "operator"},

    # DK ↔ PL (Baltic Pipe)
    {"id": "ITP-00222", "name": "Faxe (Baltic Pipe)",      "country_from": "DK", "country_to": "PL", "tso_from": "ENERGINET","tso_to": "GAZ-SYSTEM","vip_id": None, "reporting_side": "operator"},

    # NO → DK (Baltic Pipe upstream)
    {"id": "ITP-00223", "name": "Nybro (NO → DK)",         "country_from": "NO", "country_to": "DK", "tso_from": "GASSCO",   "tso_to": "ENERGINET","vip_id": None, "reporting_side": "operator"},

    # UK ↔ BE (Interconnector)
    {"id": "ITP-00231", "name": "IUK Bacton-Zeebrugge",    "country_from": "UK", "country_to": "BE", "tso_from": "IUK",      "tso_to": "FLUXYS",  "vip_id": None, "reporting_side": "operator"},

    # UK ↔ NL (BBL)
    {"id": "ITP-00232", "name": "BBL Bacton-Balgzand",     "country_from": "UK", "country_to": "NL", "tso_from": "BBL",      "tso_to": "GTS",     "vip_id": None, "reporting_side": "operator"},

    # UK ↔ IE
    {"id": "ITP-00241", "name": "Moffat",                  "country_from": "UK", "country_to": "IE", "tso_from": "NGT",      "tso_to": "GNI",     "vip_id": None, "reporting_side": "operator"},

    # PL ↔ LT (GIPL)
    {"id": "ITP-00251", "name": "Santaka (GIPL)",          "country_from": "PL", "country_to": "LT", "tso_from": "GAZ-SYSTEM","tso_to": "AB AMBER","vip_id": None, "reporting_side": "operator"},

    # FI ↔ EE (Balticconnector)
    {"id": "ITP-00261", "name": "Balticconnector",         "country_from": "FI", "country_to": "EE", "tso_from": "GASGRID",  "tso_to": "ELERING", "vip_id": None, "reporting_side": "operator"},
]
