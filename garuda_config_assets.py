"""
garuda_config_assets.py
=======================
Static configuration registry for the Garuda-Ops institutional terminal.

Now ships a 370+ ticker Nifty-broad universe (large-cap, mid-cap, small-cap,
PSU, new-age, defence, chemicals, sugar, paper, textiles, ...) so that the
random scan engine can keep yfinance below its IP rate-limit while still
covering the full Indian equity opportunity set across many runs.

Exports:
    * NSE_UNIVERSE          - ticker -> sector dictionary (~375 names)
    * SECTOR_INDEX_MAP      - sector -> NSE sector index symbol
    * LOTTIE_ASSETS         - public Lottie JSON URLs
    * INDIAN_MARKET_FEES    - statutory fee config
    * THEME                 - Cybernetic Indigo palette tokens
    * RISK_PROFILES         - sidebar dropdown configs (sector caps, ATR mults)
"""

from __future__ import annotations


# =========================================================================
# 1.  NIFTY-BROAD UNIVERSE  (built from per-sector lists for compactness)
# =========================================================================
_SECTOR_GROUPS: dict[str, list[str]] = {

    # ---------- Banking ----------
    "Banking": [
        "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
        "INDUSINDBK", "BANKBARODA", "PNB", "FEDERALBNK", "IDFCFIRSTB",
        "AUBANK", "BANKINDIA", "CANBK", "UNIONBANK", "RBLBANK",
        "YESBANK", "IOB", "CENTRALBK", "MAHABANK", "SOUTHBANK",
        "KARURVYSYA", "DCBBANK", "CSBBANK", "KTKBANK", "UCOBANK",
    ],

    # ---------- Financial Services (NBFC, AMC, Insurance, Exchanges) ----
    "Financial Services": [
        "BAJFINANCE", "BAJAJFINSV", "BAJAJHLDNG", "HDFCLIFE", "SBILIFE",
        "ICICIPRULI", "ICICIGI", "CHOLAFIN", "MUTHOOTFIN", "SHRIRAMFIN",
        "PFC", "RECLTD", "M&MFIN", "MANAPPURAM", "LICHSGFIN",
        "IIFLFIN", "HDFCAMC", "NAM-INDIA", "360ONE", "ABCAPITAL",
        "CDSL", "BSE", "MCX", "MFSL", "IRFC",
        "PEL", "SBICARD", "POONAWALLA", "AAVAS", "ANGELONE",
        "MOTILALOFS", "PRUDENT", "CAMS", "KFINTECH", "FIVESTAR",
    ],

    # ---------- Information Technology ----------
    "IT": [
        "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM",
        "LTIM", "PERSISTENT", "MPHASIS", "COFORGE", "OFSS",
        "KPITTECH", "BSOFT", "CYIENT", "ZENSARTECH", "TATAELXSI",
        "FIRSTSOURCE", "RATEGAIN", "INTELLECT", "NEWGEN", "HAPPSTMNDS",
        "MASTEK", "NIITLTD", "ROUTE", "SONATSOFTW", "LATENTVIEW",
        "BIRLASOFT", "TANLA", "ECLERX", "RSYSTEMS",
    ],

    # ---------- Pharma & Healthcare ----------
    "Pharma": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN",
        "AUROPHARMA", "BIOCON", "TORNTPHARM", "ALKEM", "ZYDUSLIFE",
        "GLAND", "IPCALAB", "GLENMARK", "AJANTPHARM", "ABBOTINDIA",
        "PFIZER", "GLAXO", "SANOFI", "SYNGENE", "NATCOPHARM",
        "GRANULES", "JBCHEPHARM", "LAURUSLABS", "MANKIND", "ERIS",
        "APOLLOHOSP", "MAXHEALTH", "FORTIS", "METROPOLIS", "LALPATHLAB",
        "POLYMED", "CAPLIPOINT", "FDC",
    ],

    # ---------- Energy / Oil & Gas / Power ----------
    "Energy": [
        "RELIANCE", "ONGC", "IOC", "BPCL", "HINDPETRO",
        "GAIL", "OIL", "MGL", "IGL", "GUJGASLTD",
        "PETRONET", "AEGISLOG", "CASTROLIND", "GULFOILLUB",
        "NTPC", "POWERGRID", "ADANIPOWER", "TATAPOWER", "JSWENERGY",
        "ADANIGREEN", "NHPC", "SJVN", "TORNTPOWER", "CESC", "NLCINDIA",
    ],

    # ---------- FMCG ----------
    "FMCG": [
        "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR",
        "MARICO", "GODREJCP", "COLPAL", "TATACONSUM", "VBL",
        "EMAMILTD", "JYOTHYLAB", "RADICO", "UNITDSPR", "UBL",
        "KRBL", "BIKAJI", "GILLETTE", "PGHH", "HATSUN",
    ],

    # ---------- Automotive ----------
    "Auto": [
        "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO",
        "EICHERMOT", "TVSMOTOR", "ASHOKLEY", "BOSCHLTD", "MRF",
        "APOLLOTYRE", "BALKRISIND", "CEATLTD", "EXIDEIND", "ENDURANCE",
        "MOTHERSON", "BHARATFORG", "SUNDARMFIN", "ESCORTS", "SCHAEFFLER",
        "FORCEMOT", "OLECTRA", "LUMAXIND", "GABRIEL", "MINDAIND",
    ],

    # ---------- Metals & Mining ----------
    "Metals": [
        "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "COALINDIA",
        "NMDC", "SAIL", "JINDALSTEL", "HINDZINC", "NATIONALUM",
        "HINDCOPPER", "MOIL", "RATNAMANI", "APLAPOLLO", "JSL",
        "WELCORP", "GRAVITA", "MAITHANALL",
    ],

    # ---------- Cement ----------
    "Cement": [
        "ULTRACEMCO", "GRASIM", "SHREECEM", "AMBUJACEM", "ACC",
        "DALBHARAT", "JKCEMENT", "RAMCOCEM", "BIRLACORPN", "INDIACEM",
        "JKLAKSHMI", "ORIENTCEM",
    ],

    # ---------- Infrastructure & Construction ----------
    "Infrastructure": [
        "LT", "ADANIENT", "ADANIPORTS", "GMRINFRA", "IRB",
        "NCC", "KEC", "KALPATPOWR", "RVNL", "PNCINFRA",
        "KNRCON", "HGINFRA", "NBCC", "HUDCO", "IRCON",
        "ENGINERSIN", "JKIL", "ASHOKA",
    ],

    # ---------- Telecom & Media ----------
    "Telecom": [
        "BHARTIARTL", "IDEA", "TATACOMM", "RAILTEL", "HFCL",
        "TEJASNET", "STLTECH",
    ],
    "Media": [
        "ZEEL", "SUNTV", "PVRINOX", "SAREGAMA", "TIPSINDLTD",
        "NETWORK18", "NAZARA", "ONMOBILE",
    ],

    # ---------- Consumer Discretionary ----------
    "Consumer Discretionary": [
        "TITAN", "ASIANPAINT", "BERGEPAINT", "PIDILITIND", "DMART",
        "TRENT", "NYKAA", "ZOMATO", "JUBLFOOD", "DEVYANI",
        "WESTLIFE", "BATAINDIA", "RELAXO", "METROBRAND", "PAGEIND",
        "VEDANTFASH", "RAYMOND", "ARVIND", "ABFRL", "V2RETAIL",
        "SHOPERSTOP", "KALYANKJIL", "SENCO", "RTNINDIA", "CAMPUS",
        "MIRZAINT", "VMART",
    ],

    # ---------- Chemicals & Specialty ----------
    "Chemicals": [
        "UPL", "PIIND", "SRF", "DEEPAKNTR", "TATACHEM",
        "AARTIIND", "ATUL", "CLEAN", "CHEMPLASTS", "GHCL",
        "NAVINFLUOR", "NOCIL", "ROSSARI", "VINATIORGA", "BALAMINES",
        "ALKYLAMINE", "FINEORG", "GALAXYSURF", "JUBLINGREA", "SUMICHEM",
        "LXCHEM", "AMIORG", "ANURAS",
    ],

    # ---------- Realty ----------
    "Realty": [
        "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "BRIGADE",
        "PHOENIXLTD", "SOBHA", "MAHLIFE", "SUNTECK", "KOLTEPATIL",
        "LODHA", "SIGNATURE",
    ],

    # ---------- Capital Goods / Engineering ----------
    "Capital Goods": [
        "SIEMENS", "ABB", "BHEL", "BEL", "HAL",
        "BEML", "CUMMINSIND", "THERMAX", "ELGIEQUIP", "GREAVESCOT",
        "ISGEC", "AIAENG", "GRINDWELL", "CARBORUNIV", "TIMKEN",
        "SKFINDIA", "CGPOWER", "HAPPYFORGE", "TRIVENI", "KIRLOSENG",
        "AZAD", "DATAPATTNS",
    ],

    # ---------- Textiles ----------
    "Textiles": [
        "TRIDENT", "WELSPUNLIV", "VARDHMAN", "KPRMILL", "GRWRHITECH",
        "INDORAMA", "NITINSPIN", "GOKEX",
    ],

    # ---------- Hospitality & Travel ----------
    "Hospitality": [
        "INDIGO", "SPICEJET", "EIHOTEL", "INDHOTEL", "IRCTC",
        "EASEMYTRIP", "IXIGO", "LEMONTREE", "CHALET", "TBOTEK",
    ],

    # ---------- Logistics ----------
    "Logistics": [
        "BLUEDART", "ALLCARGO", "CONCOR", "TCI", "VRLLOG",
        "DELHIVERY", "SNOWMAN", "MAHLOG", "GATI",
    ],

    # ---------- Defence / Shipbuilding ----------
    "Defence": [
        "MAZDOCK", "COCHINSHIP", "GRSE", "BDL", "MIDHANI",
    ],

    # ---------- Agri & Fertilizers ----------
    "Agri": [
        "COROMANDEL", "CHAMBLFERT", "GNFC", "GSFC", "RCF",
        "NFL", "ZUARIIND", "KSCL", "DCMSHRIRAM", "FACT",
        "GODREJAGRO", "BAYERCROP",
    ],

    # ---------- Sugar & Distilleries ----------
    "Sugar": [
        "BALRAMCHIN", "BAJAJHIND", "BANNARI", "DHAMPURSUG", "RENUKA",
        "EIDPARRY",
    ],

    # ---------- Paper ----------
    "Paper": [
        "WSTCSTPAPR", "JKPAPER", "TNPL", "SESHAPAPER",
    ],

    # ---------- Glass / Ceramics / Tiles ----------
    "Ceramics": [
        "ASAHIINDIA", "CERA", "KAJARIACER", "ORIENTBELL", "SOMANYCERA",
    ],

    # ---------- Electronics Manufacturing ----------
    "Electronics": [
        "DIXON", "AMBER", "KAYNES", "SYRMA", "AVALON",
        "ELECON", "VOLTAS", "WHIRLPOOL", "BLUESTARCO", "CROMPTON",
        "HAVELLS", "POLYCAB", "VGUARD", "BAJAJELEC", "SUPREMEIND",
    ],

    # ---------- New-Age / FinTech ----------
    "New-Age": [
        "PAYTM", "POLICYBZR", "FSL", "MAPMYINDIA", "IEX",
        "TATATECH", "HONASA",
    ],
}


# Build the public mapping ticker -> sector with the .NS suffix
NSE_UNIVERSE: dict[str, str] = {
    f"{ticker}.NS": sector
    for sector, tickers in _SECTOR_GROUPS.items()
    for ticker in tickers
}


# =========================================================================
# 2.  SECTOR -> INDEX MAP  (used by CrossSectorVelocity)
# =========================================================================
SECTOR_INDEX_MAP: dict[str, str] = {
    "Banking":                "^NSEBANK",
    "Financial Services":     "NIFTY_FIN_SERVICE.NS",
    "IT":                     "^CNXIT",
    "Energy":                 "^CNXENERGY",
    "FMCG":                   "^CNXFMCG",
    "Auto":                   "^CNXAUTO",
    "Pharma":                 "^CNXPHARMA",
    "Metals":                 "^CNXMETAL",
    "Cement":                 "^NSEI",
    "Infrastructure":         "^CNXINFRA",
    "Telecom":                "^NSEI",
    "Media":                  "^CNXMEDIA",
    "Consumer Discretionary": "^CNXCONSUM",
    "Chemicals":              "^NSEI",
    "Realty":                 "^CNXREALTY",
    "Capital Goods":          "^NSEI",
    "Textiles":               "^NSEI",
    "Hospitality":            "^NSEI",
    "Logistics":              "^NSEI",
    "Defence":                "^NSEI",
    "Agri":                   "^NSEI",
    "Sugar":                  "^NSEI",
    "Paper":                  "^NSEI",
    "Ceramics":               "^NSEI",
    "Electronics":            "^NSEI",
    "New-Age":                "^NSEI",
}

LOTTIE_ASSETS: dict[str, str] = {
    "loading":  "https://assets10.lottiefiles.com/packages/lf20_p8bfn5to.json",
    "success":  "https://assets2.lottiefiles.com/packages/lf20_jbrw3hcz.json",
    "scanning": "https://assets5.lottiefiles.com/packages/lf20_kxsd2ytq.json",
    "alert":    "https://assets1.lottiefiles.com/packages/lf20_qpwbqki6.json",
}

INDIAN_MARKET_FEES: dict[str, float] = {
    "BROKERAGE_FLAT_INR":  20.0,
    "STT_PCT":             0.001,
    "GST_PCT":             0.18,
    "SEBI_PCT":            0.000001,
    "STAMP_DUTY_PCT":      0.00015,
    "EXCHANGE_TXN_PCT":    0.0000345,
    "DP_CHARGES_INR":      15.93,
}

THEME: dict[str, str] = {
    "BG_DEEP":        "#0B0F19",
    "BG_PANEL":       "#111827",
    "BG_CARD":        "#161E2E",
    "ACCENT_MINT":    "#10B981",
    "ACCENT_CRIMSON": "#EF4444",
    "ACCENT_INDIGO":  "#6366F1",
    "ACCENT_AMBER":   "#F59E0B",
    "TEXT_PRIMARY":   "#E5E7EB",
    "TEXT_MUTED":     "#9CA3AF",
    "BORDER":         "#1F2937",
}

RISK_PROFILES: dict[str, dict] = {
    "Conservative": {
        "min_hurst":          0.62,
        "atr_target_mult":    1.5,
        "atr_stop_mult":      1.0,
        "max_positions":      8,
        "max_sector_weight":  0.30,
    },
    "Balanced": {
        "min_hurst":          0.58,
        "atr_target_mult":    2.5,
        "atr_stop_mult":      1.2,
        "max_positions":      10,
        "max_sector_weight":  0.35,
    },
    "Aggressive": {
        "min_hurst":          0.55,
        "atr_target_mult":    3.5,
        "atr_stop_mult":      1.5,
        "max_positions":      14,
        "max_sector_weight":  0.45,
    },
}
