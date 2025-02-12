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
# Carica il file Ready Pro (Excel: .xls o .xlsx)
ready_pro_file = st.sidebar.file_uploader("Carica file Ready Pro (XLS o XLSX)", type=["xls", "xlsx"])
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
    except Exception:
        return np.nan

if ready_pro_file is not None and keepa_file is not None:
    ### Lettura del file Ready Pro
    try:
        if ready_pro_file.name.endswith('.xls'):
            # Usa xlrd per file .xls (assicurarsi di avere xlrd in requirements.txt)
            df_ready = pd.read_excel(ready_pro_file, engine="xlrd")
        elif ready_pro_file.name.endswith('.xlsx'):
            # Usa openpyxl per file .xlsx
            df_ready = pd.read_excel(ready_pro_file, engine="openpyxl")
        else:
            df_ready = pd.read_csv(ready_pro_file, sep=None, engine="python")
        df_ready.columns = df_ready.columns.str.strip()  # Rimuove spazi indesiderati nei nomi delle colonne
        st.write("Colonne Ready Pro:", df_ready.columns.tolist())
    except Exception as e:
        st.error("Errore nella lettura del file Ready Pro: " + str(e))
    
    ### Lettura del file Keepa
    try:
        if keepa_file.name.endswith('.xlsx'):
            df_keepa = pd.read_excel(keepa_file, engine="openpyxl")
        else:
            df_keepa = pd.read_csv(keepa_file, sep=None, engine="python")
        df_keepa.columns = df_keepa.columns.str.strip()
        st.write("Colonne Keepa:", df_keepa.columns.tolist())
    except Exception as e:
        st.error("Errore nella lettura del file Keepa: " + str(e))
    
    ### Mapping delle colonne per Ready Pro
    # Le colonne attese in Ready Pro sono: "Sito", "Stato", "Codice(ASIN)", "Descrizione sul marketplace", "SKU", "Descrizione", "Quantita'" e "Prezzo"
    if "Codice(ASIN)" in df_ready.columns:
        df_ready.rename(columns={"Codice(ASIN)": "ASIN"}, inplace=True)
    else:
        st.error("Il file Ready Pro non contiene la colonna 'Codice(ASIN)' necessaria per l'ASIN.")
    
    if "Descrizione sul marketplace" in df_ready.columns:
        df_ready.rename(columns={"Descrizione sul marketplace": "Nome prodotto"}, inplace=True)
    else:
        st.error("Il file Ready Pro non contiene la colonna 'Descrizione sul marketplace' per il nome prodotto.")
    
    if "Quantita'" in df_ready.columns:
        df_ready.rename(columns={"Quantita'": "Quantita"}, inplace=True)
    else:
        df_ready["Quantita"] = np.nan
    
    if "Prezzo" in df_ready.columns:
        df_ready.rename(columns={"Prezzo": "Prezzo di vendita attuale"}, inplace=True)
    else:
        st.error("Il file Ready Pro non contiene la colonna 'Prezzo' necessaria per il prezzo di vendita attuale.")
    
    ### Parsing del prezzo in Ready Pro
    try:
        df_ready["Prezzo di vendita attuale"] = df_ready["Prezzo di vendita attuale"].apply(parse_price)
    except Exception as e:
        st.error("Errore nel parsing del prezzo in Ready Pro: " + str(e))
    
    ### Gestione del file Keepa
    # Utilizziamo la colonna "Buy Box: Current" come riferimento principale (prezzo + spedizione)
    if "Buy Box: Current" in df_keepa.columns:
        df_keepa["Prezzo di riferimento"] = df_keepa["Buy Box: Current"].apply(parse_price)
    else:
        st.error("La colonna 'Buy Box: Current' non è presente nel file Keepa.")
    
    if "ASIN" not in df_keepa.columns:
        st.error("Il file Keepa non contiene la colonna 'ASIN'.")
    else:
        ### Merge dei DataFrame sulla colonna "ASIN"
        try:
            df = pd.merge(df_ready, df_keepa, on="ASIN", how="inner")
        except Exception as e:
            st.error("Errore durante il merge dei dati: " + str(e))
        
        ### Calcolo della differenza percentuale
        try:
            df["Differenza %"] = ((df["Prezzo di riferimento"] - df["Prezzo di vendita attuale"]) /
                                  df["Prezzo di vendita attuale"]) * 100
        except Exception as e:
            st.error("Errore nel calcolo della differenza percentuale: " + str(e))
        
        def calcola_stato(diff):
            if diff < -10:
                return "Fuori Mercato"
            elif diff < 0:
                return "Margine Insufficiente"
            else:
                return "Competitivo"
        
        try:
            df["Stato Prodotto"] = df["Differenza %"].apply(calcola_stato)
        except Exception as e:
            st.error("Errore nel calcolo dello stato del prodotto: " + str(e))
        
        colonne_visualizzate = [
            "ASIN", "Nome prodotto", "Quantita", "Prezzo di vendita attuale",
            "Prezzo di riferimento", "Differenza %", "Stato Prodotto"
        ]
        
        ### Filtri interattivi (sidebar)
        st.sidebar.subheader("Filtra Risultati")
        stati = df["Stato Prodotto"].unique().tolist()
        selected_stati = st.sidebar.multiselect("Seleziona Stato Prodotto", options=stati, default=stati)
        min_diff, max_diff = st.sidebar.slider("Intervallo Differenza %", min_value=-100.0, max_value=100.0, value=(-100.0, 100.0), step=1.0)
        filtered_df = df[(df["Stato Prodotto"].isin(selected_stati)) & (df["Differenza %"] >= min_diff) & (df["Differenza %"] <= max_diff)]
        
        st.subheader("Dati Analizzati")
        st.dataframe(filtered_df[colonne_visualizzate])
        
        ### Sezione per modificare i prezzi
        st.subheader("Modifica Prezzi")
        # Data editor per modificare individualmente i prezzi (ed altri campi se necessario)
        edited_df = st.data_editor(filtered_df, key="editor", num_rows="dynamic")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Allinea a Prezzo di Mercato"):
                # Imposta il prezzo di vendita uguale al prezzo di riferimento per le righe modificate
                edited_df["Prezzo di vendita attuale"] = edited_df["Prezzo di riferimento"]
                st.success("Prezzi allineati al prezzo di riferimento!")
        with col2:
            new_price = st.number_input("Imposta Nuovo Prezzo per tutte le righe filtrate", min_value=0.0, step=0.1)
            if st.button("Applica Modifica di Massa"):
                edited_df["Prezzo di vendita attuale"] = new_price
                st.success("Modifica di massa applicata!")
        with col3:
            if st.button("Aggiorna Calcoli"):
                try:
                    edited_df["Differenza %"] = ((edited_df["Prezzo di riferimento"] - edited_df["Prezzo di vendita attuale"]) /
                                                  edited_df["Prezzo di vendita attuale"]) * 100
                    edited_df["Stato Prodotto"] = edited_df["Differenza %"].apply(calcola_stato)
                    # Aggiorna il DataFrame globale (usando ASIN come chiave)
                    df.update(edited_df)
                    st.success("Calcoli aggiornati!")
                except Exception as e:
                    st.error("Errore nell'aggiornamento dei calcoli: " + str(e))
        
        st.subheader("Dati Aggiornati")
        st.dataframe(df[colonne_visualizzate])
        
        ### Istogramma della differenza percentuale
        st.subheader("Distribuzione della Differenza Percentuale")
        fig, ax = plt.subplots()
        ax.hist(df["Differenza %"].dropna(), bins=20, color="skyblue", edgecolor="black")
        ax.set_xlabel("Differenza %")
        ax.set_ylabel("Numero di prodotti")
        ax.set_title("Istogramma della Differenza Percentuale")
        st.pyplot(fig)
        
        ### Esportazione del report
        st.subheader("Esporta Report")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(label="Download CSV", data=csv, file_name="report.csv", mime="text/csv")
        
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, index=False, sheet_name="Report")
        writer.close()  # Utilizza writer.close() invece di writer.save()
        st.download_button(label="Download Excel", data=output.getvalue(),
                           file_name="report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Attendere il caricamento dei file Ready Pro e Keepa.")
