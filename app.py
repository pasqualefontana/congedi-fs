import json
import os
from datetime import datetime, date
import streamlit as st
import io

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    canvas = None

FILE_DATI = "congedi_parentali_figli_anagrafica_fs.json"

st.set_page_config(
    page_title="Gestione Congedi Parentali - Gruppo FS",
    page_icon="📅",
    layout="wide"
)

def carica_dati():
    if os.path.exists(FILE_DATI):
        with open(FILE_DATI, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "figli": {
            "Gabriele": {"data_nascita": "2020-01-01"},
            "Rosa": {"data_nascita": "2022-01-01"}
        },
        "storico": []
    }

def salva_dati(dati):
    with open(FILE_DATI, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=4, ensure_ascii=False)

def format_mesi_giorni(tot_giorni):
    mesi = tot_giorni // 30
    giorni = tot_giorni % 30
    if mesi > 0 and giorni > 0:
        return f"{mesi} mesi e {giorni} gg"
    elif mesi > 0:
        return f"{mesi} mesi"
    else:
        return f"{giorni} gg"

def calcola_trattamento_automatico(storico_esistente, figlio, genitore, nuovo_giorni, escludi_index=None):
    giorni_gia_usati = 0
    for idx, item in enumerate(storico_esistente):
        if idx != escludi_index and item.get("figlio", "Gabriele") == figlio and item["genitore"] == genitore:
            giorni_gia_usati += item["giorni"]
    
    assegnazioni = []
    giorni_rimanenti = nuovo_giorni
    giorni_correnti = giorni_gia_usati

    while giorni_rimanenti > 0:
        if giorni_correnti < 30:
            scaglione = "100% (Integrato 1° Mese)"
            disponibili_scaglione = 30 - giorni_correnti
        elif giorni_correnti < 60:
            scaglione = "80% (Integrato 2° Mese)"
            disponibili_scaglione = 60 - giorni_correnti
        elif giorni_correnti < 270:
            scaglione = "30% (Standard INPS)"
            disponibili_scaglione = 270 - giorni_correnti
        else:
            scaglione = "0% (Non Retribuito)"
            disponibili_scaglione = giorni_rimanenti

        giorni_in_questo_scaglione = min(giorni_rimanenti, disponibili_scaglione)
        assegnazioni.append((scaglione, giorni_in_questo_scaglione))
        
        giorni_rimanenti -= giorni_in_questo_scaglione
        giorni_correnti += giorni_in_questo_scaglione

    return assegnazioni

def ricalcola_totali_per_genitore_e_figlio(storico, figlio, genitore):
    totali = {
        "100% (Integrato 1° Mese)": 0,
        "80% (Integrato 2° Mese)": 0,
        "30% (Standard INPS)": 0,
        "0% (Non Retribuito)": 0
    }
    
    storico_filtrato = [item for item in storico if item.get("figlio", "Gabriele") == figlio and item["genitore"] == genitore]
    simulazione_storico = []
    for item in storico_filtrato:
        scaglioni = calcola_trattamento_automatico(simulazione_storico, figlio, genitore, item["giorni"])
        for fascia, qta in scaglioni:
            if fascia in totali:
                totali[fascia] += qta
        simulazione_storico.append(item)
        
    return totali

def genera_pdf_bytes(storico_filtrato, totali_diz, titolo_report, info_figlio):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"REPORT CONGEDI PARENTALI - {titolo_report.upper()}")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Gruppo FS Italiane - Generato il: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    y -= 15
    if info_figlio:
        c.drawString(50, y, f"Data di Nascita Figlio: {info_figlio}")
    y -= 25
    c.line(50, y, 550, y)
    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Riepilogo Totale:")
    y -= 15
    c.setFont("Helvetica", 10)
    tot_gg = sum(totali_diz.values())
    c.drawString(60, y, f"• Giorni totali: {tot_gg} ({format_mesi_giorni(tot_gg)})")
    y -= 15
    for k, v in totali_diz.items():
        if v > 0:
            c.drawString(60, y, f"  - {k}: {v} giorni ({format_mesi_giorni(v)})")
            y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Dettaglio Periodi Registrati:")
    y -= 20

    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, y, "Figlio")
    c.drawString(95, y, "Genitore")
    c.drawString(145, y, "Inizio")
    c.drawString(205, y, "Fine")
    c.drawString(260, y, "Giorni")
    c.drawString(300, y, "Trattamento Economico")
    c.drawString(440, y, "Note")
    y -= 10
    c.line(50, y, 550, y)
    y -= 15

    c.setFont("Helvetica", 8)
    for item in storico_filtrato:
        if y < 100:
            c.showPage()
            y = 750
        c.drawString(50, y, item.get("figlio", "Gabriele"))
        c.drawString(95, y, item["genitore"])
        c.drawString(145, y, item["data_inizio_it"])
        c.drawString(205, y, item["data_fine_it"])
        c.drawString(260, y, str(item["giorni"]))
        c.drawString(300, y, item["tipo"][:25])
        c.drawString(440, y, str(item["note"])[:18])
        y -= 18

    y -= 30
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Firma Dipendente: ________________________")
    c.drawString(330, y, "Visto Ufficio Personale: ________________________")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


dati = carica_dati()
if "figli" not in dati:
    dati["figli"] = {
        "Gabriele": {"data_nascita": "2020-01-01"},
        "Rosa": {"data_nascita": "2022-01-01"}
    }

st.title("📅 Gestione Congedi Parentali per Figlio (Gruppo FS)")
st.caption("Tracciamento con anagrafica anno di nascita, scaglioni automatici e report")

tab_gestione, tab_anagrafica, tab_anteprima = st.tabs(["📝 Inserisci / Visualizza Storico", "👶 Anagrafica Figli", "🔍 Anteprima & Stampa PDF"])

FASCE_TIPO = [
    "100% (Integrato 1° Mese)",
    "80% (Integrato 2° Mese)",
    "30% (Standard INPS)",
    "0% (Non Retribuito)"
]

with tab_anagrafica:
    st.subheader("Gestione Anagrafica e Anno di Nascita dei Figli")
    st.write("Imposta o aggiorna la data di nascita di Gabriele e Rosa per verificare la regolarità dei periodi.")
    
    # Selezione del figlio FUORI dal form per permettere l'aggiornamento immediato della data visualizzata
    figlio_up = st.selectbox("Seleziona Figlio da aggiornare", ["Gabriele", "Rosa"], key="sel_figlio_anag")
    
    data_salvata_str = dati["figli"].get(figlio_up, {}).get("data_nascita", "2020-01-01")
    dt_default = datetime.strptime(data_salvata_str, "%Y-%m-%d").date()

    with st.form("form_anagrafica"):
        nuova_data_nascita = st.date_input("Data di Nascita", value=dt_default, format="DD-MM-YYYY")
        
        btn_salva_anag = st.form_submit_button("💾 Salva Anagrafica Figlio")
        if btn_salva_anag:
            dati["figli"][figlio_up]["data_nascita"] = nuova_data_nascita.strftime("%Y-%m-%d")
            salva_dati(dati)
            st.success(f"✅ Anagrafica di {figlio_up} aggiornata con successo (Nato/a il {nuova_data_nascita.strftime('%d-%m-%Y')})!")
            st.rerun()

with tab_gestione:
    st.subheader("Registra un nuovo periodo di congedo")
    with st.form("form_congedo", clear_on_submit=True):
        col_f, col_g = st.columns(2)
        with col_f:
            figlio_sel = st.selectbox("Seleziona Figlio", ["Gabriele", "Rosa"])
            nascita_figlio = dati["figli"].get(figlio_sel, {}).get("data_nascita", "N.D.")
            st.caption(f"📅 Nato/a il: {datetime.strptime(nascita_figlio, '%Y-%m-%d').strftime('%d-%m-%Y') if nascita_figlio!='N.D.' else 'N.D.'}")
        with col_g:
            genitore = st.selectbox("Genitore Richiedente", ["Padre", "Madre"])
        
        col1, col2 = st.columns(2)
        with col1:
            d_inizio = st.date_input("Data Inizio", value=date.today(), format="DD-MM-YYYY")
        with col2:
            d_fine = st.date_input("Data Fine", value=date.today(), format="DD-MM-YYYY")

        note = st.text_input("Note / Protocollo", placeholder="Es. Periodo estivo")

        btn_submit = st.form_submit_button("➕ Calcola e Registra Automaticamente")

        if btn_submit:
            if d_fine < d_inizio:
                st.error("❌ La data di fine non può essere antecedente alla data di inizio.")
            else:
                giorni_totali_periodo = (d_fine - d_inizio).days + 1
                
                scaglioni = calcola_trattamento_automatico(dati["storico"], figlio_sel, genitore, giorni_totali_periodo)
                
                descrizione_tipo = ", ".join([f"{q} gg al {t}" for t, q in scaglioni])
                tipo_principale = scaglioni[0][0] if len(scaglioni) == 1 else descrizione_tipo

                nuovo_record = {
                    "figlio": figlio_sel,
                    "genitore": genitore,
                    "data_inizio_it": d_inizio.strftime("%d-%m-%Y"),
                    "data_fine_it": d_fine.strftime("%d-%m-%Y"),
                    "giorni": giorni_totali_periodo,
                    "tipo": tipo_principale,
                    "note": note if note else "-",
                    "inserito_il": datetime.now().strftime("%d-%m-%Y %H:%M")
                }
                dati["storico"].append(nuovo_record)
                salva_dati(dati)
                st.success(f"✅ Registrato per {figlio_sel} ({genitore}) - {giorni_totali_periodo} giorni!")
                st.rerun()

    st.markdown("---")
    
    figlio_tab = st.radio("Seleziona il figlio da visualizzare nei cruscotti:", ["Gabriele", "Rosa"], horizontal=True)
    
    nascita_curr = dati["figli"].get(figlio_tab, {}).get("data_nascita", "Non impostata")
    nascita_formattata = datetime.strptime(nascita_curr, "%Y-%m-%d").strftime('%d-%m-%Y') if nascita_curr != "Non impostata" else "Non impostata"
    st.info(f"👶 **Figlio Selezionato:** {figlio_tab} | 🎂 **Data di Nascita:** {nascita_formattata}")

    totali_madre = ricalcola_totali_per_genitore_e_figlio(dati["storico"], figlio_tab, "Madre")
    totali_padre = ricalcola_totali_per_genitore_e_figlio(dati["storico"], figlio_tab, "Padre")
    
    totali_figlio = {k: totali_madre[k] + totali_padre[k] for k in FASCE_TIPO}
    giorni_totali_figlio = sum(totali_figlio.values())
    giorni_totali_madre = sum(totali_madre.values())
    giorni_totali_padre = sum(totali_padre.values())

    st.subheader(f"🏆 Totale Complessivo per {figlio_tab} (Madre + Padre)")
    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
    tc1.metric("📌 Totale Usati", f"{giorni_totali_figlio} gg")
    st.caption(f"⏱️ **Equivalente per {figlio_tab}:** {format_mesi_giorni(giorni_totali_figlio)}")
    
    tc2.metric("🔵 100% Totale", f"{totali_figlio['100% (Integrato 1° Mese)']} gg")
    tc3.metric("🟢 80% Totale", f"{totali_figlio['80% (Integrato 2° Mese)']} gg")
    tc4.metric("🟡 30% Totale", f"{totali_figlio['30% (Standard INPS)']} gg")
    tc5.metric("🔴 0% Totale", f"{totali_figlio['0% (Non Retribuito)']} gg")

    st.markdown("---")
    st.subheader(f"📊 Dettaglio per Genitore ({figlio_tab})")
    
    col_m, col_p = st.columns(2)
    with col_m:
        st.markdown("##### 👩‍🦰 Stato Giorni - MADRE")
        st.info(f"⏱️ **Totale Madre:** {format_mesi_giorni(giorni_totali_madre)} ({giorni_totali_madre} giorni)")
        st.metric("100% (1° Mese)", f"{totali_madre['100% (Integrato 1° Mese)']} gg")
        st.metric("80% (2° Mese)", f"{totali_madre['80% (Integrato 2° Mese)']} gg")
        st.metric("30% INPS", f"{totali_madre['30% (Standard INPS)']} gg")
        st.metric("0% Non Retrib.", f"{totali_madre['0% (Non Retribuito)']} gg")

    with col_p:
        st.markdown("##### 👨‍🦰 Stato Giorni - PADRE")
        st.info(f"⏱️ **Totale Padre:** {format_mesi_giorni(giorni_totali_padre)} ({giorni_totali_padre} giorni)")
        st.metric("100% (1° Mese)", f"{totali_padre['100% (Integrato 1° Mese)']} gg")
        st.metric("80% (2° Mese)", f"{totali_padre['80% (Integrato 2° Mese)']} gg")
        st.metric("30% INPS", f"{totali_padre['30% (Standard INPS)']} gg")
        st.metric("0% Non Retrib.", f"{totali_padre['0% (Non Retribuito)']} gg")

    st.markdown("---")
    st.subheader("📋 Storico Periodi Registrati")

    if not dati["storico"]:
        st.info("Nessun congedo inserito finora.")
    else:
        for idx, item in enumerate(dati["storico"]):
            col_a, col_fig, col_b, col_c, col_d, col_e, col_f, col_g, col_h = st.columns([1.2, 1.3, 1.8, 1.8, 0.9, 2.5, 1.8, 0.6, 0.6])
            col_a.write(f"**{item['genitore']}**")
            col_fig.write(f"👶 {item.get('figlio', 'Gabriele')}")
            col_b.write(f"Dal: {item['data_inizio_it']}")
            col_c.write(f"Al: {item['data_fine_it']}")
            col_d.write(f"**{item['giorni']} gg**")
            col_e.write(f"Tipo: {item['tipo']}")
            col_f.write(f"Note: {item['note']}")
            
            with col_g.popover("✏️", help="Modifica periodo"):
                st.markdown(f"**Modifica Periodo #{idx+1}**")
                with st.form(f"form_mod_{idx}"):
                    current_figlio = item.get("figlio", "Gabriele")
                    new_figlio = st.selectbox("Figlio", ["Gabriele", "Rosa"], index=0 if current_figlio=="Gabriele" else 1)
                    new_gen = st.selectbox("Genitore", ["Padre", "Madre"], index=0 if item["genitore"]=="Padre" else 1)
                    new_ini = st.date_input("Inizio", value=datetime.strptime(item["data_inizio_it"], "%d-%m-%Y").date(), format="DD-MM-YYYY")
                    new_fin = st.date_input("Fine", value=datetime.strptime(item["data_fine_it"], "%d-%m-%Y").date(), format="DD-MM-YYYY")
                    new_note = st.text_input("Note", value=item["note"] if item["note"] != "-" else "")
                    
                    btn_salva_mod = st.form_submit_button("Salva Modifiche")
                    
                    if btn_salva_mod:
                        if new_fin < new_ini:
                            st.error("La fine non può precedere l'inizio.")
                        else:
                            giorni_mod = (new_fin - new_ini).days + 1
                            scaglioni_mod = calcola_trattamento_automatico(dati["storico"], new_figlio, new_gen, giorni_mod, escludi_index=idx)
                            desc_mod = ", ".join([f"{q} gg al {t}" for t, q in scaglioni_mod])
                            tipo_mod = scaglioni_mod[0][0] if len(scaglioni_mod) == 1 else desc_mod
                            
                            dati["storico"][idx] = {
                                "figlio": new_figlio,
                                "genitore": new_gen,
                                "data_inizio_it": new_ini.strftime("%d-%m-%Y"),
                                "data_fine_it": new_fin.strftime("%d-%m-%Y"),
                                "giorni": giorni_mod,
                                "tipo": tipo_mod,
                                "note": new_note if new_note else "-",
                                "inserito_il": item.get("inserito_il", datetime.now().strftime("%d-%m-%Y %H:%M"))
                            }
                            salva_dati(dati)
                            st.success("Modificato con successo!")
                            st.rerun()

            if col_h.button("🗑️", key=f"del_{idx}", help="Elimina periodo"):
                del dati["storico"][idx]
                salva_dati(dati)
                st.rerun()

with tab_anteprima:
    st.subheader("🔍 Anteprima di Stampa del Documento")
    
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        figlio_report = st.selectbox("Seleziona il Figlio per il Report:", ["Gabriele", "Rosa"], key="rep_figlio")
    with col_rep2:
        tipo_report = st.selectbox(
            "Seleziona il tipo di Report:",
            ["Complessivo di Coppia", "Solo Madre", "Solo Padre"],
            key="rep_tipo"
        )

    rep_totale_madre = ricalcola_totali_per_genitore_e_figlio(dati["storico"], figlio_report, "Madre")
    rep_totale_padre = ricalcola_totali_per_genitore_e_figlio(dati["storico"], figlio_report, "Padre")
    rep_totale_coppia = {k: rep_totale_madre[k] + rep_totale_padre[k] for k in FASCE_TIPO}

    if tipo_report == "Solo Madre":
        storico_filtrato = [i for i in dati["storico"] if i.get("figlio", "Gabriele") == figlio_report and i["genitore"] == "Madre"]
        totali_filtrati = rep_totale_madre
        totale_gg_sel = sum(rep_totale_madre.values())
        titolo_doc = f"REPORT CONGEDI - MADRE ({figlio_report.upper()})"
    elif tipo_report == "Solo Padre":
        storico_filtrato = [i for i in dati["storico"] if i.get("figlio", "Gabriele") == figlio_report and i["genitore"] == "Padre"]
        totali_filtrati = rep_totale_padre
        totale_gg_sel = sum(rep_totale_padre.values())
        titolo_doc = f"REPORT CONGEDI - PADRE ({figlio_report.upper()})"
    else:
        storico_filtrato = [i for i in dati["storico"] if i.get("figlio", "Gabriele") == figlio_report]
        totali_filtrati = rep_totale_coppia
        totale_gg_sel = sum(rep_totale_coppia.values())
        titolo_doc = f"REPORT CONGEDI - COMPLESSIVO COPPIA ({figlio_report.upper()})"

    nascita_pdf_str = dati["figli"].get(figlio_report, {}).get("data_nascita", "")
    nascita_pdf_fmt = datetime.strptime(nascita_pdf_str, "%Y-%m-%d").strftime('%d-%m-%Y') if nascita_pdf_str else "N.D."

    st.markdown("""
        <style>
            .preview-box {
                background-color: white;
                color: black;
                padding: 30px;
                border: 1px solid #ccc;
                border-radius: 5px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                font-family: Arial, sans-serif;
            }
        </style>
    """, unsafe_allow_html=True)

    anteprima_html = f"""
    <div class="preview-box">
        <h3 style="text-align: center; margin-bottom: 5px;">{titolo_doc}</h3>
        <p style="text-align: center; color: #555; font-size: 0.9em;">Gruppo FS Italiane — Generato il: {datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
        <p style="text-align: center; color: #333; font-size: 0.95em;"><b>Data di Nascita di {figlio_report}:</b> {nascita_pdf_fmt}</p>
        <hr>
        <h5>Riepilogo Totale ({figlio_report} - {tipo_report}):</h5>
        <ul>
            <li><b>Giorni complessivi usati:</b> {totale_gg_sel} giorni ({format_mesi_giorni(totale_gg_sel)})</li>
            {"".join([f"<li><b>{k}:</b> {v} giorni</li>" for k, v in totali_filtrati.items() if v > 0])}
        </ul>
        <br>
        <h5>Elenco Periodi Registrati:</h5>
        <table style="width: 100%; border-collapse: collapse; text-align: left;" border="1" cellpadding="6">
            <tr style="background-color: #f2f2f2;">
                <th>Figlio</th>
                <th>Genitore</th>
                <th>Data Inizio</th>
                <th>Data Fine</th>
                <th>Giorni</th>
                <th>Trattamento Economico Automatico</th>
                <th>Note</th>
            </tr>
            {"".join([f"<tr><td>{i.get('figlio', 'Gabriele')}</td><td><b>{i['genitore']}</b></td><td>{i['data_inizio_it']}</td><td>{i['data_fine_it']}</td><td>{i['giorni']}</td><td>{i['tipo']}</td><td>{i['note']}</td></tr>" for i in storico_filtrato]) if storico_filtrato else "<tr><td colspan='7' style='text-align:center;'>Nessun periodo registrato per questa selezione</td></tr>"}
        </table>
        <br><br><br>
        <div style="display: flex; justify-content: space-between;">
            <span>Firma Dipendente: ________________________</span>
            <span>Visto Ufficio Personale: ________________________</span>
        </div>
    </div>
    """
    st.markdown(anteprima_html, unsafe_allow_html=True)
    st.write("")

    if canvas:
        pdf_bytes = genera_pdf_bytes(storico_filtrato, totali_filtrati, f"{figlio_report} - {tipo_report}", nascita_pdf_fmt)
        st.download_button(
            label=f"📥 Scarica Report PDF ({figlio_report} - {tipo_report})",
            data=pdf_bytes,
            file_name=f"Report_Congedi_{figlio_report}_{tipo_report.replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("⚠️ Installa `reportlab` (`pip install reportlab`) per abilitare il tasto di download PDF diretto.")