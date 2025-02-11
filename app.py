import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Configurazione della pagina
st.set_page_config(page_title="Price Monitoring App per HDGaming.it", layout="wide")
st.title("Price Monitoring App per HDGaming.it")
st.markdown("Confronta i prezzi dei prodotti di Ready Pro con quelli attuali di Amazon (Keepa)")

st.sidebar.header("Caricamento File")
# Carica il file Ready Pro (CSV)
ready_pro_file = st.sidebar.file_uploader("Carica file CSV Ready Pro", type=["csv"])
# Carica il file Keepa (Excel o CSV)
keepa_file = st.sidebar.file_uploader("Carica file Keepa (Excel o CSV)", type=["xlsx", "csv"])

def parse_price(price_str):
    """
    Converte una stringa di prezzo tipo "33,80 €" in float (es. 33.80).
    Se il valore è NaN o non convertibile, restituisce np.nan.
    """
    try:
        if pd.isna(price_str):
            return np.nan
        price_str = str(price_str)
        price_str = price_str.replace('€', '').strip()
        price_str = price_str.replace(',', '.')
        return float(price_str)
    except Exception as e:
        return np.nan

if ready_pro_file is not None and keepa_file is not None:
    ### Lettura del file Ready Pro
    try:
        # Il file Ready Pro, secondo l'esempio, è separato da tab (\t)
        df_ready = pd.read_csv(ready_pro_file, sep='\t')
    except Exception as e:
        st.error("Errore nella lettura del file Ready Pro: " + str(e))
    
    ### Lettura del file Keepa
    try:
        if keepa_file.name.endswith('.xlsx'):
            df_keepa = pd.read_excel(keepa_file)
        else:
            # Se il file Keepa è CSV, proviamo a usare anche qui il separatore tab
            df_keepa = pd.read_csv(keepa_file, sep='\t')
    except Exception as e:
        st.error("Errore nella lettura del file Keepa: " + str(e))
    
    ### Rinomina delle colonne del file Ready Pro
    # Il file Ready Pro ha le colonne: 
    # "Sito", "Stato", "Codice(ASIN)", "Descrizione sul marketplace", "SKU", "Descrizione", "Quantita'" e "Prezzo"
    df_ready.rename(columns={
        "Codice(ASIN)": "ASIN",
        "Descrizione sul marketplace": "Nome prodotto",
        "Quantita'": "Quantita",
        "Prezzo": "Prezzo di vendita attuale"
    }, inplace=True)
    
    ### Converte i prezzi in Ready Pro in numerico
    try:
        df_ready["Prezzo di vendita attuale"] = df_ready["Prezzo di vendita attuale"].apply(parse_price)
    except Exception as e:
        st.error("Errore nel parsing del prezzo in Ready Pro: " + str(e))
    
    ### Gestione del file Keepa
    # Utilizziamo la colonna "Buy Box: Current" per ottenere il prezzo attuale su Amazon
    if "Buy Box: Current" in df_keepa.columns:
        df_keepa["Prezzo attuale su Amazon"] = df_keepa["Buy Box: Current"].apply(parse_price)
    else:
        st.error("La colonna 'Buy Box: Current' non è presente nel file Keepa. Modifica l'esportazione o aggiorna il mapping.")
    
    # Verifica che Keepa contenga la colonna "ASIN" per il merge
    if "ASIN" not in df_keepa.columns:
        st.error("La colonna 'ASIN' non è presente nel file Keepa.")
    else:
        ### Merge dei DataFrame sulla colonna "ASIN"
        df = pd.merge(df_ready, df_keepa, on="ASIN", how="inner")
        
        ### Calcolo della variazione percentuale
        try:
            df["Differenza %"] = ((df["Prezzo attuale su Amazon"] - df["Prezzo di vendita attuale"]) / df["Prezzo di vendita attuale"]) * 100
        except Exception as e:
            st.error("Errore nel calcolo della differenza percentuale: " + str(e))
        
        ### Definizione dello stato del prodotto
        def calcola_stato(diff):
            if diff < -10:
                return "Fuori Mercato"
            elif diff < 0:
                return "Margine Insufficiente"
            else:
                return "Competitivo"
        
        df["Stato Prodotto"] = df["Differenza %"].apply(calcola_stato)
        
        ### Visualizzazione dei dati analizzati
        st.subheader("Dati Analizzati")
        colonne_visualizzate = [
            "ASIN", "Nome prodotto", "Quantita", "Prezzo di vendita attuale",
            "Prezzo attuale su Amazon", "Differenza %", "Stato Prodotto"
        ]
        st.dataframe(df[colonne_visualizzate])
        
        ### Visualizzazione grafica: Istogramma della differenza percentuale
        st.subheader("Distribuzione della Differenza Percentuale")
        fig, ax = plt.subplots()
        ax.hist(df["Differenza %"].dropna(), bins=20, color="skyblue", edgecolor="black")
        ax.set_xlabel("Differenza %")
        ax.set_ylabel("Numero di prodotti")
        ax.set_title("Istogramma della Differenza Percentuale")
        st.pyplot(fig)
        
        ### Esportazione del report
        st.subheader("Esporta Report")
        # Esportazione in CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(label="Download CSV", data=csv, file_name="report.csv", mime="text/csv")
        
        # Esportazione in Excel
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, index=False, sheet_name="Report")
        writer.save()
        st.download_button(label="Download Excel", data=output.getvalue(),
                           file_name="report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Attendere il caricamento dei file Ready Pro e Keepa.")
