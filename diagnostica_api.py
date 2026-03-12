from google import genai
from google.genai import errors

# INIETTA QUI IL TUO TOKEN CRITTOGRAFICO REALE
CHIAVE_API_REALE = "AIzaSyAko7SK0QvAAH02P-P2x6eszhAgoA1_oY0"

def test_connessione_nuovo_sdk():
    print("--- Inizializzazione Client Google GenAI (Nuovo SDK) ---")
    
    try:
        # Istanziazione del Client con il token
        client = genai.Client(api_key=CHIAVE_API_REALE)
        
        print("Richiesta di handshake inviata. Attesa risposta dal server...")
        
        # Effettuiamo una chiamata generativa di base per testare il modello e la chiave
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Rispondi esclusivamente con la parola: AUTENTICAZIONE_AVVENUTA'
        )
        
        print(f"\n[SUCCESSO] Risposta del Server: {response.text.strip()}")
        print("Il tunnel crittografico è aperto e il modello è operativo.")
        
    except errors.APIError as e:
        print(f"\n[FALLIMENTO] Errore API: {e}")
    except Exception as e:
        print(f"\n[ERRORE DI SISTEMA]: {e}")

test_connessione_nuovo_sdk()