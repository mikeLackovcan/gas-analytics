"""EU LNG regas terminals (operational as of mid-2026). Capacity in GWh/d sendout,
storage in GWh. Source: GIE ALSI public reference + operator factsheets.
"""

LNG_TERMINALS = [
    # DE (all FSRUs commissioned 2022-2024)
    {"id": "DE-WILHELMSHAVEN-1",  "country": "DE", "name": "Wilhelmshaven FSRU I",   "capacity_gwh_d": 200, "storage_gwh": 1000, "owner": "UNIPER"},
    {"id": "DE-WILHELMSHAVEN-2",  "country": "DE", "name": "Wilhelmshaven FSRU II",  "capacity_gwh_d": 150, "storage_gwh":  900, "owner": "TES/ENGIE"},
    {"id": "DE-BRUNSBUTTEL",      "country": "DE", "name": "Brunsbüttel FSRU",       "capacity_gwh_d": 110, "storage_gwh":  900, "owner": "RWE"},
    {"id": "DE-MUKRAN",           "country": "DE", "name": "Mukran (Lubmin)",        "capacity_gwh_d": 150, "storage_gwh": 1700, "owner": "DET"},
    {"id": "DE-STADE",            "country": "DE", "name": "Stade onshore",          "capacity_gwh_d": 150, "storage_gwh": 2400, "owner": "HEH"},
    # NL
    {"id": "NL-GATE",             "country": "NL", "name": "Gate terminal",          "capacity_gwh_d": 530, "storage_gwh": 5400, "owner": "GASUNIE/VOPAK"},
    {"id": "NL-EEMSHAVEN",        "country": "NL", "name": "Eemshaven FSRU",         "capacity_gwh_d": 220, "storage_gwh": 1700, "owner": "GASUNIE"},
    # BE
    {"id": "BE-ZEEBRUGGE",        "country": "BE", "name": "Zeebrugge LNG",          "capacity_gwh_d": 460, "storage_gwh": 3800, "owner": "FLUXYS"},
    # FR
    {"id": "FR-MONTOIR",          "country": "FR", "name": "Montoir-de-Bretagne",    "capacity_gwh_d": 340, "storage_gwh": 4100, "owner": "ELENGY"},
    {"id": "FR-FOS-TONKIN",       "country": "FR", "name": "Fos Tonkin",             "capacity_gwh_d":  70, "storage_gwh":  800, "owner": "ELENGY"},
    {"id": "FR-FOS-CAVAOU",       "country": "FR", "name": "Fos Cavaou",             "capacity_gwh_d": 270, "storage_gwh": 2200, "owner": "FOSMAX"},
    {"id": "FR-DUNKERQUE",        "country": "FR", "name": "Dunkerque LNG",          "capacity_gwh_d": 410, "storage_gwh": 2400, "owner": "DUNKERQUE LNG"},
    {"id": "FR-LEHAVRE",          "country": "FR", "name": "Le Havre FSRU",          "capacity_gwh_d": 150, "storage_gwh": 1700, "owner": "TOTALENERGIES"},
    # IT
    {"id": "IT-PANIGAGLIA",       "country": "IT", "name": "Panigaglia",             "capacity_gwh_d":  45, "storage_gwh":  600, "owner": "GNL ITALIA"},
    {"id": "IT-ROVIGO",           "country": "IT", "name": "Rovigo (Adriatic)",      "capacity_gwh_d": 260, "storage_gwh": 2300, "owner": "TERMINALE GNL ADRIATICO"},
    {"id": "IT-LIVORNO",          "country": "IT", "name": "OLT Livorno",            "capacity_gwh_d": 130, "storage_gwh":  900, "owner": "OLT OFFSHORE"},
    {"id": "IT-PIOMBINO",         "country": "IT", "name": "Piombino FSRU",          "capacity_gwh_d": 150, "storage_gwh": 1700, "owner": "SNAM"},
    {"id": "IT-RAVENNA",          "country": "IT", "name": "Ravenna FSRU",           "capacity_gwh_d": 150, "storage_gwh": 1700, "owner": "SNAM"},
    # ES
    {"id": "ES-BARCELONA",        "country": "ES", "name": "Barcelona",              "capacity_gwh_d": 580, "storage_gwh": 9300, "owner": "ENAGAS"},
    {"id": "ES-CARTAGENA",        "country": "ES", "name": "Cartagena",              "capacity_gwh_d": 510, "storage_gwh": 7000, "owner": "ENAGAS"},
    {"id": "ES-HUELVA",           "country": "ES", "name": "Huelva",                 "capacity_gwh_d": 510, "storage_gwh": 6500, "owner": "ENAGAS"},
    {"id": "ES-BILBAO",           "country": "ES", "name": "Bilbao",                 "capacity_gwh_d": 270, "storage_gwh": 3000, "owner": "BBG"},
    {"id": "ES-SAGUNTO",          "country": "ES", "name": "Sagunto",                "capacity_gwh_d": 290, "storage_gwh": 4100, "owner": "SAGGAS"},
    {"id": "ES-MUGARDOS",         "country": "ES", "name": "Mugardos",               "capacity_gwh_d": 130, "storage_gwh": 2000, "owner": "REGANOSA"},
    # PT
    {"id": "PT-SINES",            "country": "PT", "name": "Sines",                  "capacity_gwh_d": 180, "storage_gwh": 2100, "owner": "REN"},
    # PL
    {"id": "PL-SWINOUJSCIE",      "country": "PL", "name": "Świnoujście",            "capacity_gwh_d": 220, "storage_gwh": 3000, "owner": "GAZ-SYSTEM"},
    # LT
    {"id": "LT-KLAIPEDA",         "country": "LT", "name": "Klaipėda FSRU",          "capacity_gwh_d":  90, "storage_gwh": 1100, "owner": "KN"},
    # FI/EE
    {"id": "FI-INKOO",            "country": "FI", "name": "Inkoo FSRU",             "capacity_gwh_d": 150, "storage_gwh": 1100, "owner": "GASGRID"},
    # GR
    {"id": "GR-REVITHOUSSA",      "country": "GR", "name": "Revithoussa",            "capacity_gwh_d":  90, "storage_gwh":  1100,"owner": "DESFA"},
    {"id": "GR-ALEXANDROUPOLIS",  "country": "GR", "name": "Alexandroupolis FSRU",   "capacity_gwh_d": 150, "storage_gwh": 1700, "owner": "GASTRADE"},
    # HR
    {"id": "HR-KRK",              "country": "HR", "name": "Krk FSRU",               "capacity_gwh_d":  90, "storage_gwh": 1100, "owner": "LNG HRVATSKA"},
    # UK
    {"id": "UK-ISLE-OF-GRAIN",    "country": "UK", "name": "Isle of Grain",          "capacity_gwh_d": 670, "storage_gwh": 7000, "owner": "NATIONAL GRID"},
    {"id": "UK-SOUTHHOOK",        "country": "UK", "name": "South Hook",             "capacity_gwh_d": 600, "storage_gwh": 5600, "owner": "QATAR PETROLEUM"},
    {"id": "UK-DRAGON",           "country": "UK", "name": "Dragon",                 "capacity_gwh_d": 220, "storage_gwh": 1700, "owner": "DRAGON LNG"},
]
