"""Major EU storage facilities. Working gas in TWh, max rates in GWh/d.
Source: GIE AGSI+ public reference, operator factsheets. Approximate.
"""

STORAGE_FACILITIES = [
    # DE
    {"id": "DE-REHDEN",       "country": "DE", "operator": "SEFE",       "name": "Rehden",        "working_gas_twh": 39.0, "max_inj_gwh_d": 200, "max_wdr_gwh_d": 480},
    {"id": "DE-JEMGUM",       "country": "DE", "operator": "VARIOUS",    "name": "Jemgum",        "working_gas_twh": 19.5, "max_inj_gwh_d": 240, "max_wdr_gwh_d": 360},
    {"id": "DE-ETZEL",        "country": "DE", "operator": "VARIOUS",    "name": "Etzel",         "working_gas_twh": 27.0, "max_inj_gwh_d": 220, "max_wdr_gwh_d": 400},
    {"id": "DE-EPE",          "country": "DE", "operator": "VARIOUS",    "name": "Epe",           "working_gas_twh": 21.0, "max_inj_gwh_d": 180, "max_wdr_gwh_d": 350},
    {"id": "DE-HAIDACH",      "country": "DE", "operator": "RAG/ASTORA", "name": "Haidach (DE share)", "working_gas_twh": 17.0, "max_inj_gwh_d": 80, "max_wdr_gwh_d": 130},
    # NL
    {"id": "NL-BERGERMEER",   "country": "NL", "operator": "TAQA",       "name": "Bergermeer",    "working_gas_twh": 48.0, "max_inj_gwh_d": 480, "max_wdr_gwh_d": 660},
    {"id": "NL-NORG",         "country": "NL", "operator": "NAM",        "name": "Norg",          "working_gas_twh": 60.0, "max_inj_gwh_d": 320, "max_wdr_gwh_d": 720},
    {"id": "NL-GRIJPSKERK",   "country": "NL", "operator": "NAM",        "name": "Grijpskerk",    "working_gas_twh": 25.0, "max_inj_gwh_d": 180, "max_wdr_gwh_d": 480},
    # FR
    {"id": "FR-STORENGY",     "country": "FR", "operator": "STORENGY",   "name": "Storengy (agg)","working_gas_twh": 102.0,"max_inj_gwh_d": 850, "max_wdr_gwh_d": 1900},
    {"id": "FR-TEREGA",       "country": "FR", "operator": "TEREGA",     "name": "Teréga (agg)",  "working_gas_twh":  31.0,"max_inj_gwh_d": 230, "max_wdr_gwh_d": 580},
    # IT
    {"id": "IT-STOGIT",       "country": "IT", "operator": "SNAM",       "name": "Stogit (agg)",  "working_gas_twh": 175.0,"max_inj_gwh_d": 1200,"max_wdr_gwh_d": 2400},
    # AT
    {"id": "AT-HAIDACH",      "country": "AT", "operator": "RAG",        "name": "Haidach (AT)",  "working_gas_twh": 28.0, "max_inj_gwh_d": 100, "max_wdr_gwh_d": 130},
    {"id": "AT-7FIELDS",      "country": "AT", "operator": "RAG/UNIPER", "name": "7Fields",       "working_gas_twh": 23.0, "max_inj_gwh_d": 120, "max_wdr_gwh_d": 180},
    # CZ
    {"id": "CZ-RWE-GAS",      "country": "CZ", "operator": "RWE",        "name": "RWE Gas Storage","working_gas_twh": 28.0,"max_inj_gwh_d": 130, "max_wdr_gwh_d": 240},
    # BE
    {"id": "BE-LOENHOUT",     "country": "BE", "operator": "FLUXYS",     "name": "Loenhout",      "working_gas_twh":  8.0, "max_inj_gwh_d":  60, "max_wdr_gwh_d": 130},
    # PL
    {"id": "PL-OSM",          "country": "PL", "operator": "GAS-STORAGE","name": "OSM agg",       "working_gas_twh": 41.0, "max_inj_gwh_d": 200, "max_wdr_gwh_d": 530},
    # ES
    {"id": "ES-ENAGAS",       "country": "ES", "operator": "ENAGAS",     "name": "Enagás (agg)",  "working_gas_twh": 35.0, "max_inj_gwh_d": 180, "max_wdr_gwh_d": 330},
]
