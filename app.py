import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Configurazione della pagina
st.set_page_config(page_title="Price Monitoring App per HDGaming.it", layout="wide")

# Titolo dell'applicazione
st.title("Price Monitoring App per HDGaming.it")
st.markdown("Confronta i prezzi dei prodotti presenti su Ready Pro con quelli attuali di Amazon (Keepa)")

# Sidebar: caricamento dei file CSV
st.sidebar.header("Caricamento File CSV")
ready_pro_file = st.sidebar.file_uploader("Carica file CSV Ready Pro", type=["csv"])
keepa_file = st.sidebar.file_uploader("Carica file CSV Keepa", type=["csv"])

if ready_pro_file is not None and keepa_file is not None:
    try:
        # Lettura dei CSV
        df_ready = pd.read_csv(ready_pro_file)
        df_keepa = pd.read_csv(keepa_file)
    except Exception as e:
        st.error("Errore nella lettura dei file CSV: " + str(e))
    
    # Controlla che la colonna per il merge sia presente
    if "Codice(ASIN)" not in df_ready.columns:
        st.error("Il file Ready Pro deve contenere la colonna 'Codice(ASIN)'.")
    elif "ASIN" not in df_keepa.columns:
        st.error("Il file Keepa deve contenere la colonna 'ASIN'.")
    else:
        # Rinominiamo le colonne di Ready Pro per uniformarle
        df_ready.rename(columns={
            "Codice(ASIN)": "ASIN",
            "Quantita'": "Quantita",
            "Prezzo": "Prezzo di vendita attuale",
            "Descrizione sul marketplace": "Nome prodotto"
        }, inplace=True)
        
        # Esempio: visualizziamo le colonne disponibili (puoi aggiungere altre colonne se necessario)
        # Le colonne principali in Ready Pro ora sono: Sito, Stato, ASIN, Nome prodotto, SKU, Descrizione, Quantita, Prezzo di vendita attuale
        
        # Merge dei DataFrame utilizzando la colonna "ASIN"
        df = pd.merge(df_ready, df_keepa, on="ASIN", how="inner")
        
        # Calcolo della variazione percentuale:
        # Formula: ((Prezzo attuale su Amazon - Prezzo di vendita attuale) / Prezzo di vendita attuale) * 100
        try:
            df["Differenza %"] = ((df["Prezzo attuale su Amazon"] - df["Prezzo di vendita attuale"]) / df["Prezzo di vendita attuale"]) * 100
        except Exception as e:
            st.error("Errore nel calcolo della differenza percentuale: " + str(e))
        
        # Definizione dello "Stato" del prodotto in base alla differenza percentuale
        # Logica di esempio (modifica le soglie se necessario):
        #   - Se la differenza % è inferiore a -10: "Fuori Mercato"
        #   - Se la differenza % è compresa tra -10 e 0: "Margine Insufficiente"
        #   - Altrimenti: "Competitivo"
        def calcola_stato(diff):
            if diff < -10:
                return "Fuori Mercato"
            elif diff < 0:
                return "Margine Insufficiente"
            else:
                return "Competitivo"
        
        df["Stato Prodotto"] = df["Differenza %"].apply(calcola_stato)
        
        st.subheader("Dati Analizzati")
        
        ### Filtri interattivi nella sidebar ###
        
        # Filtro per Sito (marketplace)
        siti = df["Sito"].unique().tolist()
        sito_selezionato = st.sidebar.multiselect("Filtra per Sito", options=siti, default=siti)
        df_filtrato = df[df["Sito"].isin(sito_selezionato)]
        
        # Filtro per Stato (ad es. "Attivo")
        stati = df["Stato"].unique().tolist()
        stato_selezionato = st.sidebar.multiselect("Filtra per Stato", options=stati, default=stati)
        df_filtrato = df_filtrato[df_filtrato["Stato"].isin(stato_selezionato)]
        
        # Filtro per Quantità (utilizzo di uno slider)
        try:
            quantita_min = int(df["Quantita"].min())
            quantita_max = int(df["Quantita"].max())
        except Exception:
            quantita_min, quantita_max = 0, 100  # default in caso di errore
        quantita_range = st.sidebar.slider("Quantità in magazzino", min_value=quantita_min, max_value=quantita_max, value=(quantita_min, quantita_max))
        df_filtrato = df_filtrato[(df_filtrato["Quantita"] >= quantita_range[0]) &
                                  (df_filtrato["Quantita"] <= quantita_range[1])]
        
        # Filtro testuale per Nome prodotto (ricerca nel campo "Nome prodotto")
        nome_input = st.sidebar.text_input("Cerca per Nome prodotto", "")
        if nome_input:
            df_filtrato = df_filtrato[df_filtrato["Nome prodotto"].str.contains(nome_input, case=False, na=False)]
        
        # Ordinamento per differenza percentuale
        ordinamento = st.sidebar.selectbox("Ordina per Differenza %", options=["Decrescente", "Crescente"])
        ascending = True if ordinamento == "Crescente" else False
        df_filtrato = df_filtrato.sort_values("Differenza %", ascending=ascending)
        
        # Visualizzazione del DataFrame filtrato
        st.dataframe(df_filtrato[["ASIN", "Nome prodotto", "SKU", "Sito", "Stato", "Quantita", 
                                  "Prezzo di vendita attuale", "Prezzo attuale su Amazon", "Differenza %", "Stato Prodotto"]])
        
        ### Visualizzazione grafica ###
        st.subheader("Distribuzione della Differenza Percentuale")
        fig, ax = plt.subplots()
        ax.hist(df_filtrato["Differenza %"].dropna(), bins=20, color="skyblue", edgecolor="black")
        ax.set_xlabel("Differenza %")
        ax.set_ylabel("Numero di prodotti")
        ax.set_title("Istogramma della Differenza Percentuale")
        st.pyplot(fig)
        
        ### Esportazione del report ###
        st.subheader("Esporta Report")
        
        # Esportazione in CSV
        csv = df_filtrato.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download CSV", data=csv, file_name="report.csv", mime="text/csv")
        
        # Esportazione in Excel
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df_filtrato.to_excel(writer, index=False, sheet_name="Report")
        writer.save()
        processed_data = output.getvalue()
        st.download_button(label="Download Excel", data=processed_data, file_name="report.xlsx", 
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        ### Storico delle variazioni di prezzo (se disponibili) ###
        st.subheader("Storico Prezzi")
        st.markdown("Visualizzazione dei dati storici: Prezzo minimo storico, Prezzo medio ultimi 90 giorni e Prezzo massimo storico")
        storico_cols = ["ASIN", "Nome prodotto", "Prezzo minimo storico", "Prezzo medio ultimi 90 giorni", "Prezzo massimo storico"]
        if set(storico_cols).issubset(df.columns):
            st.dataframe(df[storico_cols])
        else:
            st.info("I dati storici non sono disponibili nel file Keepa.")

else:
    st.info("Attendere il caricamento dei file CSV di Ready Pro e Keepa.")
