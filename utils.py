import re
import logging

logger = logging.getLogger(__name__)

ISO_COUNTRY_CODES = {
    "Afghanistan": "AFG",
    "Albania": "ALB",
    "Algeria": "DZA",
    "Andorra": "AND",
    "Angola": "AGO",
    "Argentina": "ARG",
    "Armenia": "ARM",
    "Australia": "AUS",
    "Austria": "AUT",
    "Azerbaijan": "AZE",
    "Bahamas": "BHS",
    "Bahrain": "BHR",
    "Bangladesh": "BGD",
    "Barbados": "BRB",
    "Belarus": "BLR",
    "Belgium": "BEL",
    "Belize": "BLZ",
    "Benin": "BEN",
    "Bhutan": "BTN",
    "Bolivia": "BOL",
    "Bosnia and Herzegovina": "BIH",
    "Botswana": "BWA",
    "Brazil": "BRA",
    "Brunei": "BRN",
    "Bulgaria": "BGR",
    "Burkina Faso": "BFA",
    "Burundi": "BDI",
    "Cambodia": "KHM",
    "Cameroon": "CMR",
    "Canada": "CAN",
    "Cape Verde": "CPV",
    "Central African Republic": "CAF",
    "Chad": "TCD",
    "Chile": "CHL",
    "China": "CHN",
    "Colombia": "COL",
    "Comoros": "COM",
    "Congo": "COG",
    "Costa Rica": "CRI",
    "Côte d'Ivoire": "CIV",
    "Croatia": "HRV",
    "Cuba": "CUB",
    "Cyprus": "CYP",
    "Czech Republic": "CZE",
    "Czechia": "CZE",
    "Denmark": "DNK",
    "Djibouti": "DJI",
    "Dominica": "DMA",
    "Dominican Republic": "DOM",
    "Ecuador": "ECU",
    "Egypt": "EGY",
    "El Salvador": "SLV",
    "Equatorial Guinea": "GNQ",
    "Eritrea": "ERI",
    "Estonia": "EST",
    "Eswatini": "SWZ",
    "Ethiopia": "ETH",
    "Fiji": "FJI",
    "Finland": "FIN",
    "France": "FRA",
    "Gabon": "GAB",
    "Gambia": "GMB",
    "Georgia": "GEO",
    "Germany": "DEU",
    "Ghana": "GHA",
    "Greece": "GRC",
    "Grenada": "GRD",
    "Guatemala": "GTM",
    "Guinea": "GIN",
    "Guinea-Bissau": "GNB",
    "Guyana": "GUY",
    "Haiti": "HTI",
    "Honduras": "HND",
    "Hungary": "HUN",
    "Iceland": "ISL",
    "India": "IND",
    "Indonesia": "IDN",
    "Iran": "IRN",
    "Iraq": "IRQ",
    "Ireland": "IRL",
    "Israel": "ISR",
    "Italy": "ITA",
    "Jamaica": "JAM",
    "Japan": "JPN",
    "Jordan": "JOR",
    "Kazakhstan": "KAZ",
    "Kenya": "KEN",
    "Kiribati": "KIR",
    "Kosovo": "XKX",
    "Kuwait": "KWT",
    "Kyrgyzstan": "KGZ",
    "Laos": "LAO",
    "Latvia": "LVA",
    "Lebanon": "LBN",
    "Lesotho": "LSO",
    "Liberia": "LBR",
    "Libya": "LBY",
    "Liechtenstein": "LIE",
    "Lithuania": "LTU",
    "Luxembourg": "LUX",
    "Madagascar": "MDG",
    "Malawi": "MWI",
    "Malaysia": "MYS",
    "Maldives": "MDV",
    "Mali": "MLI",
    "Malta": "MLT",
    "Marshall Islands": "MHL",
    "Mauritania": "MRT",
    "Mauritius": "MUS",
    "Mexico": "MEX",
    "Micronesia": "FSM",
    "Moldova": "MDA",
    "Monaco": "MCO",
    "Mongolia": "MNG",
    "Montenegro": "MNE",
    "Morocco": "MAR",
    "Mozambique": "MOZ",
    "Myanmar": "MMR",
    "Namibia": "NAM",
    "Nauru": "NRU",
    "Nepal": "NPL",
    "Netherlands": "NLD",
    "New Zealand": "NZL",
    "Nicaragua": "NIC",
    "Niger": "NER",
    "Nigeria": "NGA",
    "North Korea": "PRK",
    "North Macedonia": "MKD",
    "Norway": "NOR",
    "Oman": "OMN",
    "Pakistan": "PAK",
    "Palau": "PLW",
    "Palestine": "PSE",
    "Panama": "PAN",
    "Papua New Guinea": "PNG",
    "Paraguay": "PRY",
    "Peru": "PER",
    "Philippines": "PHL",
    "Poland": "POL",
    "Portugal": "PRT",
    "Qatar": "QAT",
    "Romania": "ROU",
    "Russia": "RUS",
    "Rwanda": "RWA",
    "Saint Kitts and Nevis": "KNA",
    "Saint Lucia": "LCA",
    "Saint Vincent and the Grenadines": "VCT",
    "Samoa": "WSM",
    "San Marino": "SMR",
    "Sao Tome and Principe": "STP",
    "Saudi Arabia": "SAU",
    "Senegal": "SEN",
    "Serbia": "SRB",
    "Seychelles": "SYC",
    "Sierra Leone": "SLE",
    "Singapore": "SGP",
    "Slovakia": "SVK",
    "Slovenia": "SVN",
    "Solomon Islands": "SLB",
    "Somalia": "SOM",
    "South Africa": "ZAF",
    "South Korea": "KOR",
    "South Sudan": "SSD",
    "Spain": "ESP",
    "Sri Lanka": "LKA",
    "Sudan": "SDN",
    "Suriname": "SUR",
    "Sweden": "SWE",
    "Switzerland": "CHE",
    "Syria": "SYR",
    "Taiwan": "TWN",
    "Tajikistan": "TJK",
    "Tanzania": "TZA",
    "Thailand": "THA",
    "Togo": "TGO",
    "Tonga": "TON",
    "Trinidad and Tobago": "TTO",
    "Tunisia": "TUN",
    "Turkey": "TUR",
    "Türkiye": "TUR",
    "Turkmenistan": "TKM",
    "Tuvalu": "TUV",
    "Uganda": "UGA",
    "Ukraine": "UKR",
    "United Arab Emirates": "ARE",
    "United Kingdom": "GBR",
    "United States": "USA",
    "Uruguay": "URY",
    "Uzbekistan": "UZB",
    "Vanuatu": "VUT",
    "Vatican City": "VAT",
    "Venezuela": "VEN",
    "Vietnam": "VNM",
    "Yemen": "YEM",
    "Zambia": "ZMB",
    "Zimbabwe": "ZWE",
    "UK": "GBR",
    "USA": "USA",
    "Republic of Korea": "KOR",
    "Republic of Côte d'Ivoire": "CIV",
}

MONTH_FR = {
    "janv": "Janvier",
    "févr": "Février",
    "mars": "Mars",
    "avr": "Avril",
    "mai": "Mai",
    "juin": "Juin",
    "juil": "Juillet",
    "août": "Août",
    "sept": "Septembre",
    "oct": "Octobre",
    "nov": "Novembre",
    "déc": "Décembre",
}


def get_country_code(country_name: str) -> str:
    if not country_name:
        return ""
    return ISO_COUNTRY_CODES.get(country_name.strip(), "")


def format_date_display(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        parts = date_str.split("-")
        if len(parts) == 2:
            year, month = int(parts[0]), int(parts[1])
            month_names = {
                1: "Janvier",
                2: "Février",
                3: "Mars",
                4: "Avril",
                5: "Mai",
                6: "Juin",
                7: "Juillet",
                8: "Août",
                9: "Septembre",
                10: "Octobre",
                11: "Novembre",
                12: "Décembre",
            }
            return f"{month_names.get(month, str(month))} {year}"
    except (ValueError, IndexError):
        pass
    return date_str


def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r"\*+$", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def categorize_fraud_issue(issue: str) -> str:
    issue_lower = (issue or "").lower()
    if any(
        kw in issue_lower
        for kw in ["pesticide", "residue", "mrl", "chlorpyrifos", "chemical"]
    ):
        return "Résidus chimiques"
    if any(kw in issue_lower for kw in ["additive", "colorant", "e 1", "e 2", "e 3"]):
        return "Additifs non conformes"
    if any(
        kw in issue_lower
        for kw in ["origin", "document", "certificate", "label", "traceability"]
    ):
        return "Problèmes documentaires"
    if any(kw in issue_lower for kw in ["unauthorized", "not authorized", "illegal"]):
        return "Substances non autorisées"
    if any(kw in issue_lower for kw in ["substitution", "adulteration"]):
        return "Adultération"
    if any(
        kw in issue_lower
        for kw in ["counterfeit", "misdescription", "mislabelling", "misbranding"]
    ):
        return "Falsification / Étiquetage"
    if any(kw in issue_lower for kw in ["grey market", "smuggling", "contraband"]):
        return "Marché gris / Contrebande"
    if any(kw in issue_lower for kw in ["document forgery"]):
        return "Faux documents"
    return "Autres problèmes"
