import cv2
import pytesseract
from pytesseract import Output
import difflib

def similarita_fuzzy(stringa_target, stringa_ocr):
    # Calcola una percentuale di similarità tra due parole (da 0.0 a 1.0)
    return difflib.SequenceMatcher(None, stringa_target, stringa_ocr).ratio()

def estrai_riga_resiliente(image_path):
    print(f"--- Inizializzazione Motore Fuzzy su: {image_path} ---")
    
    target_name = input("Inserisci il Cognome da cercare (es. 'Mici'): ").strip().lower()
    
    # 1. Acquisizione e Pre-processing Avanzato (Ottimizzato per righe grigie)
    img = cv2.imread(image_path)
    if img is None:
        print("Errore: Immagine non trovata.")
        return

    # Ingrandimento massiccio (3x) per separare i pixel fusi
    img_scaled = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img_scaled, cv2.COLOR_BGR2GRAY)
    
    # Thresholding Adattivo (Gestisce le righe grigie annullando le ombre locali)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 21, 4)

    print("Scansione topologica in corso...")
    dati = pytesseract.image_to_data(thresh, config='--psm 6', output_type=Output.DICT)
    
    n_elementi = len(dati['text'])
    y_target = None
    parola_trovata = ""
    
    # 2. Ricerca Fuzzy (Tolleranza all'errore OCR)
    for i in range(n_elementi):
        testo_corrente = dati['text'][i].strip().lower()
        
        # Ignoriamo la spazzatura di 1 o 2 caratteri
        if len(testo_corrente) > 2:
            score = similarita_fuzzy(target_name, testo_corrente)
            
            # Se la similarità supera il 65%, consideriamo il match valido!
            if score > 0.65:
                y_target = dati['top'][i]
                parola_trovata = dati['text'][i]
                print(f"\n[SUCCESS] Ancoraggio stabilito!")
                print(f"-> Nome inserito: '{target_name}'")
                print(f"-> Letto dall'OCR come: '{parola_trovata}' (Similarità: {score*100:.1f}%)")
                print(f"-> Coordinata Asse Y identificata: {y_target}")
                break

    if y_target is None:
        print(f"\n[FALLIMENTO] Nemmeno la logica Fuzzy ha trovato tracce di '{target_name}'. L'area è totalmente illeggibile.")
        return

    # 3. Estrazione Vettoriale sulla Coordinata Y Trovata
    elementi_riga = []
    tolleranza_y = 30 # Aumentiamo la tolleranza per compensare l'ingrandimento 3x
    
    for i in range(n_elementi):
        testo = dati['text'][i].strip()
        if len(testo) > 1: # Filtra i caratteri singoli come '|' o '_'
            y_corrente = dati['top'][i]
            x_corrente = dati['left'][i]
            
            # Condizione spaziale
            if abs(y_corrente - y_target) <= tolleranza_y:
                elementi_riga.append((x_corrente, testo))
                
    # 4. Ordinamento Spaziale e Stampa
    elementi_riga.sort(key=lambda val: val[0])
    
    print("\n--- VETTORE ESTRATTO (Sequenza Cronologica) ---")
    risultato_finale = [elemento[1] for elemento in elementi_riga]
    print(" | ".join(risultato_finale))
    print("------------------------------------------------")

# Avvio
estrai_riga_resiliente('image.jpeg')