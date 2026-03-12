import streamlit as st
import json
import os
from datetime import datetime, timedelta

# --- LIBRERIE GOOGLE CLOUD & GENAI ---
from google import genai
from google.genai import types
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- CONFIGURAZIONE AMBIENTE ---
st.set_page_config(page_title="TurniScanner: Pure PDF", layout="wide", page_icon="📑")

try:
    CHIAVE_API = st.secrets["GEMINI_API_KEY"]
    ai_client = genai.Client(api_key=CHIAVE_API)
except KeyError:
    st.error("ERRORE ARCHITETTURALE: API Key Gemini mancante nel file .streamlit/secrets.toml")
    st.stop()

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


# --- CORE BUSINESS LOGIC ---

def estrazione_pdf_cloud(file_pdf, target_name):
    """
    Ingestione esclusiva di file PDF.
    Sfrutta il Geometric Anchor Prompting per evitare il collasso delle celle vuote.
    """
    byte_stream = file_pdf.read()
    mime_type = "application/pdf"
    
    documento_strutturato = types.Part.from_bytes(data=byte_stream, mime_type=mime_type)
    
    prompt_ingegnerizzato = f"""
    Sei un Architetto dei Dati. Devi estrarre i turni di '{target_name}' da questo PDF.
    
    VINCOLO GEOMETRICO ASSOLUTO (ANTI-COLLASSO):
    Nel PDF, gli spazi vuoti non generano testo. NON LEGGERE LA RIGA DA SINISTRA A DESTRA.
    Guarda l'intestazione della colonna (es. 'Martedì') e scendi verticalmente. Gli orari appartengono ESCLUSIVAMENTE al giorno sotto il quale si trovano incolonnati fisicamente.
    
    COMPILA QUESTO JSON:
    {{
      "_mappatura_cartesiana": {{
         "Lunedì": "Quali orari si trovano FISICAMENTE sotto Lunedì?",
         "Martedì": "Quali orari si trovano FISICAMENTE sotto Martedì?",
         "Mercoledì": "Quali orari si trovano FISICAMENTE sotto Mercoledì?",
         "Giovedì": "Quali orari si trovano FISICAMENTE sotto Giovedì?",
         "Venerdì": "Quali orari si trovano FISICAMENTE sotto Venerdì?",
         "Sabato": "Quali orari si trovano FISICAMENTE sotto Sabato?",
         "Domenica": "Quali orari si trovano FISICAMENTE sotto Domenica?"
      }},
      "turni": {{
         "Lunedì": {{"entrata1": "HH:MM", "uscita1": "HH:MM", "entrata2": null, "uscita2": null}},
         "Martedì": {{"entrata1": "HH:MM", "uscita1": "HH:MM", "entrata2": null, "uscita2": null}},
         "Mercoledì": {{"entrata1": "HH:MM", "uscita1": "HH:MM", "entrata2": null, "uscita2": null}},
         "Giovedì": {{"entrata1": "HH:MM", "uscita1": "HH:MM", "entrata2": null, "uscita2": null}},
         "Venerdì": {{"entrata1": "HH:MM", "uscita1": "HH:MM", "entrata2": null, "uscita2": null}},
         "Sabato": {{"entrata1": "HH:MM", "uscita1": "HH:MM", "entrata2": null, "uscita2": null}},
         "Domenica": {{"entrata1": "HH:MM", "uscita1": "HH:MM", "entrata2": null, "uscita2": null}}
      }}
    }}

    REGOLE TASSATIVE:
    1. Trascrivi gli orari nei 'turni' leggendoli SOLO dall'oggetto '_mappatura_cartesiana'.
    2. Se un giorno ha 4 orari, compilali in ordine. Se ne ha 2, mettili in entrata1/uscita1 e usa null per gli altri.
    3. Se un giorno è vuoto, usa null per tutti e 4 i campi. NON traslare gli orari da altri giorni.
    4. Formato 24h rigoroso (es. 18:30).
    
    RESTITUISCI SOLO IL CODICE JSON.
    """
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt_ingegnerizzato, documento_strutturato]
    )
    
    payload = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(payload)["turni"]


def inietta_su_calendar_sicuro(turni_target, data_lunedi_base):
    """
    Gestione OAuth 2.0 e iniezione RFC 3339 con matematica dello scavalco notturno.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("Certificato 'credentials.json' mancante nell'infrastruttura.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    contatore = 0

    for i, giorno in enumerate(giorni):
        turno = turni_target.get(giorno)
        
        if turno and isinstance(turno, dict):
            data_corrente = data_lunedi_base + timedelta(days=i)
            data_str = data_corrente.strftime('%Y-%m-%d')
            
            def crea_evento(entrata, uscita):
                if not entrata or not uscita or str(entrata).lower() == "null" or str(uscita).lower() == "null": 
                    return 0
                
                entrata = str(entrata).replace(".", ":").strip()
                uscita = str(uscita).replace(".", ":").strip()
                
                # Calcolo vettoriale dello scavalco della mezzanotte
                data_fine_str = data_str
                if uscita < entrata: 
                    data_fine_str = (data_corrente + timedelta(days=1)).strftime('%Y-%m-%d')

                evento = {
                    'summary': 'Lavoro 💼',
                    'start': {'dateTime': f'{data_str}T{entrata}:00', 'timeZone': 'Europe/Rome'},
                    'end': {'dateTime': f'{data_fine_str}T{uscita}:00', 'timeZone': 'Europe/Rome'},
                }
                service.events().insert(calendarId='primary', body=evento).execute()
                return 1

            contatore += crea_evento(turno.get("entrata1"), turno.get("uscita1"))
            contatore += crea_evento(turno.get("entrata2"), turno.get("uscita2"))

    return contatore


# --- PRESENTATION LAYER ---

st.title("📑 Sincronizzazione Turni: Architettura Pure-PDF")
st.markdown("Estrazione semantica deterministica basata su file PDF vettoriali. Zero entropia visiva.")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("Parametri di Ingestione")
    # Limitazione ferrea: si accettano solo PDF
    file_upload = st.file_uploader("1. Carica il documento originale (Solo PDF)", type=['pdf'])
    nome_dipendente = st.text_input("2. Target Operativo", value="Mici Rei")
    data_lunedi = st.date_input("3. Coordinata Temporale", value=datetime(2026, 3, 23))

with col2:
    if file_upload:
        st.info(f"File acquisito nel buffer in modo sicuro: `{file_upload.name}`")
        
        if st.button("Avvia Pipeline Deterministica", type="primary"):
            try:
                with st.spinner("Decodifica PDF e Allineamento Cartesiano in corso..."):
                    turni_estratti = estrazione_pdf_cloud(file_upload, nome_dipendente)
                    st.success("Struttura Dati estratta con successo!")
                    
                with st.spinner("Negoziazione TLS e Iniezione su Google Calendar..."):
                    tot_eventi = inietta_su_calendar_sicuro(turni_estratti, data_lunedi)
                    
                st.balloons()
                st.success(f"🏆 Iniezione Perfetta! {tot_eventi} blocchi orari registrati sul Calendario.")
                
                with st.expander("Ispeziona la Matrice Dati Generata (JSON)"):
                    st.json(turni_estratti)
                    
            except FileNotFoundError as fnf:
                st.error(f"Errore di Sistema: {fnf}")
            except Exception as e:
                st.error(f"Collasso Architetturale: {e}")