import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Configurazione della pagina
st.set_page_config(page_title="Price Monitoring App per HDGaming.it", layout="wide")
st.title("Price Monitoring App per HDGaming.it")
st.markdown("Confronta i prezzi dei prodotti di ReadyPro con i prezzi aggiornati di Amazon per ogni paese")

st.sidebar.header("Caricamento File")
# Carica il file ReadyPro (TXT, delimitato da ';')
ready_pro_file = st.sidebar.file_uploader("Carica file ReadyPro (TXT, delimitato da ';')", type=["txt"])
# Carica i file Keepa (Excel) per ogni paese
keepa_files = st.sidebar.file_uploader("Carica file Keepa (Excel) per ogni paese", type=["xlsx"], accept_multiple_files=True)

def parse_price(price_str):
    """
    Converte una stringa di prezzo tipo "33,80 €" in float (es. 33.80).
    Gestisce la presenza di virgola, simboli di euro e spazi.
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

# Se il file ReadyPro è caricato, leggi e mostra la lista completa degli ASIN
if ready_pro_file is not None:
    try:
        # Usa on_bad_lines='skip' per saltare le righe mal formattate
        df_ready = pd.read_csv(ready_pro_file, delimiter=";", encoding="latin1", on_bad_lines="skip")
        df_ready.columns = df_ready.columns.str.strip()
    except Exception as e:
        st.error("Errore nella lettura del file ReadyPro: " + str(e))
    
    # Verifica e rinomina le colonne essenziali in ReadyPro
    if "Codice(ASIN)" in df_ready.columns:
        df_ready.rename(columns={"Codice(ASIN)":"ASIN"}, inplace=True)
        unique_asin = df_ready["ASIN"].unique()
        st.subheader("Lista Completa di ASIN")
        st.write(unique_asin)
    else:
        st.error("Il file ReadyPro deve contenere la colonna 'Codice(ASIN)'.")
    
    if "Descrizione sul marketplace" in df_ready.columns:
        df_ready.rename(columns={"Descrizione sul marketplace": "Descrizione"}, inplace=True)
    else:
        st.error("Il file ReadyPro deve contenere la colonna 'Descrizione sul marketplace'.")
    if "Q.aggiornata" in df_ready.columns:
        df_ready.rename(columns={"Q.aggiornata": "Quantita"}, inplace=True)
    else:
        st.error("Il file ReadyPro deve contenere la colonna 'Q.aggiornata'.")
    if "Prz.sito" in df_ready.columns:
        df_ready.rename(columns={"Prz.sito": "Prezzo di vendita attuale"}, inplace=True)
    else:
        st.error("Il file ReadyPro deve contenere la colonna 'Prz.sito'.")
    
    # Parsing del prezzo in ReadyPro
    try:
        df_ready["Prezzo di vendita attuale"] = df_ready["Prezzo di vendita attuale"].apply(parse_price)
    except Exception as e:
        st.error("Errore nel parsing del prezzo in ReadyPro: " + str(e))

# Se sono stati caricati file Keepa, combinane tutti in un unico DataFrame
if keepa_files is not None and len(keepa_files) > 0:
    list_df_keepa = []
    for file in keepa_files:
        try:
            df_temp = pd.read_excel(file, engine="openpyxl")
            df_temp.columns = df_temp.columns.str.strip()
            # Controlla che il file contenga le colonne essenziali: ASIN, Buy Box: Current e Sito
            if "ASIN" not in df_temp.columns:
                st.error(f"Il file {file.name} non contiene la colonna 'ASIN'.")
            if "Buy Box: Current" not in df_temp.columns:
                st.error(f"Il file {file.name} non contiene la colonna 'Buy Box: Current'.")
            if "Sito" not in df_temp.columns:
                st.error(f"Il file {file.name} non contiene la colonna 'Sito'.")
            df_temp["Prezzo di riferimento"] = df_temp["Buy Box: Current"].apply(parse_price)
            list_df_keepa.append(df_temp)
        except Exception as e:
            st.error("Errore nella lettura del file Keepa " + file.name + ": " + str(e))
    if list_df_keepa:
        df_keepa = pd.concat(list_df_keepa, ignore_index=True)
    else:
        df_keepa = None
else:
    df_keepa = None

# Se entrambi i file sono disponibili, esegui il merge e l'analisi
if ready_pro_file is not None and df_keepa is not None:
    # Esegui il merge su ASIN e Sito
    try:
        df = pd.merge(df_ready, df_keepa, on=["ASIN", "Sito"], how="inner")
    except Exception as e:
        st.error("Errore durante il merge dei dati: " + str(e))
    
    # Calcolo della differenza percentuale tra Prezzo di riferimento e Prezzo di vendita attuale
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
    
    # Colonne da visualizzare (incluse quelle necessarie per aggiornare le inserzioni da ReadyPro)
    colonne_visualizzate = [
        "SKU", "Sito", "ASIN", "Descrizione", "Quantita",
        "Prezzo di vendita attuale", "Prezzo di riferimento",
        "Differenza %", "Stato Prodotto"
    ]
    
    st.subheader("Dati Analizzati")
    st.dataframe(df[colonne_visualizzate])
    
    # Filtri interattivi (sidebar)
    st.sidebar.subheader("Filtra Risultati")
    stati = df["Stato Prodotto"].unique().tolist()
    selected_stati = st.sidebar.multiselect("Seleziona Stato Prodotto", options=stati, default=stati)
    min_diff, max_diff = st.sidebar.slider("Intervallo Differenza %", min_value=-100.0, max_value=100.0, value=(-100.0, 100.0), step=1.0)
    filtered_df = df[(df["Stato Prodotto"].isin(selected_stati)) &
                     (df["Differenza %"] >= min_diff) &
                     (df["Differenza %"] <= max_diff)]
    
    st.subheader("Risultati Filtrati")
    st.dataframe(filtered_df[colonne_visualizzate])
    
    # Sezione per modificare i prezzi
    st.subheader("Modifica Prezzi")
    edited_df = st.data_editor(filtered_df, key="editor", num_rows="dynamic")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Allinea esattamente"):
            edited_df["Prezzo di vendita attuale"] = edited_df["Prezzo di riferimento"]
            st.success("Prezzi allineati al prezzo di riferimento!")
    with col2:
        if st.button("Allinea a -0,10€"):
            edited_df["Prezzo di vendita attuale"] = edited_df["Prezzo di riferimento"] - 0.10
            st.success("Prezzi aggiornati a prezzo di riferimento - 0,10€!")
    with col3:
        new_price = st.number_input("Imposta Nuovo Prezzo per tutte le righe filtrate", min_value=0.0, step=0.1)
        if st.button("Applica Modifica di Massa"):
            edited_df["Prezzo di vendita attuale"] = new_price
            st.success("Modifica di massa applicata!")
    with col4:
        if st.button("Aggiorna Calcoli"):
            try:
                edited_df["Differenza %"] = ((edited_df["Prezzo di riferimento"] - edited_df["Prezzo di vendita attuale"]) /
                                              edited_df["Prezzo di vendita attuale"]) * 100
                edited_df["Stato Prodotto"] = edited_df["Differenza %"].apply(calcola_stato)
                df.update(edited_df)
                st.success("Calcoli aggiornati!")
            except Exception as e:
                st.error("Errore nell'aggiornamento dei calcoli: " + str(e))
    
    st.subheader("Dati Aggiornati")
    st.dataframe(df[colonne_visualizzate])
    
    # Statistiche di Pricing
    st.subheader("Statistiche di Pricing")
    total_products = df.shape[0]
    avg_sale_price = df["Prezzo di vendita attuale"].mean()
    avg_ref_price = df["Prezzo di riferimento"].mean()
    avg_diff = df["Differenza %"].mean()
    st.write(f"Numero totale di prodotti: {total_products}")
    st.write(f"Prezzo di vendita medio: €{avg_sale_price:.2f}")
    st.write(f"Prezzo di riferimento medio: €{avg_ref_price:.2f}")
    st.write(f"Differenza percentuale media: {avg_diff:.2f}%")
    
    # Istogramma della differenza percentuale
    st.subheader("Distribuzione della Differenza Percentuale")
    fig, ax = plt.subplots()
    ax.hist(df["Differenza %"].dropna(), bins=20, edgecolor="black")
    ax.set_xlabel("Differenza %")
    ax.set_ylabel("Numero di prodotti")
    ax.set_title("Istogramma della Differenza Percentuale")
    st.pyplot(fig)
    
    # Esportazione del report
    st.subheader("Esporta Report")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label="Download CSV", data=csv, file_name="report.csv", mime="text/csv")
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="Report")
    writer.close()
    st.download_button(label="Download Excel", data=output.getvalue(),
                       file_name="report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Attendere il caricamento del file ReadyPro e dei file Keepa.")
