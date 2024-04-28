from lxml import html
from lxml.cssselect import CSSSelector
import requests

def fetch_text_with_css_selector(url, css_selector):
    try:
        # HTTP-Anfrage senden, um den HTML-Inhalt der Seite abzurufen
        response = requests.get(url)
        # Überprüfen, ob die Anfrage erfolgreich war (Status-Code 200)
        if response.status_code == 200:
            # HTML-Inhalt in ein lxml-Element parsen
            tree = html.fromstring(response.content)
            # CSS-Selektor auf das lxml-Element anwenden, um den Text zu finden
            selector = CSSSelector(css_selector)
            selected_elements = selector(tree)
            # Den Text aus den ausgewählten Elementen extrahieren
            text_content = [element.text_content().strip() for element in selected_elements]
            return text_content
        else:
            print("Fehler beim Abrufen der Seite. Statuscode:", response.status_code)
            return None
    except Exception as e:
        print("Fehler beim Abrufen der Seite:", str(e))
        return None

# Beispiel URL und CSS-Selektor
url = "https://www.abendblatt.de/region/niedersachsen/article242193940/Bei-Suche-nach-Arian-sollen-Aufnahmen-der-Mutter-helfen.html"
css_selector = "div > div > div > div > div > p"

# Text von der URL mit dem CSS-Selektor abrufen
text_content = fetch_text_with_css_selector(url, css_selector)

if text_content:
    print("Text gefunden:")
    for text in text_content:
        print(text)
else:
    print("Fehler beim Abrufen des Textes von der URL.")
