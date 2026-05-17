import streamlit as st
import requests
from xml.etree.ElementTree import fromstring
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="FiyatOpt Kimya", page_icon="📦", layout="wide")

# ====================== SIDEBAR ======================
st.sidebar.title("FiyatOpt Kimya")
sayfa = st.sidebar.radio("Menü", ["Hesaplama", "Ürün Yönetimi", "Geçmiş Kayıtlar"])

# ====================== VERİ SAKLAMA ======================
if "urunler" not in st.session_state:
    st.session_state.urunler = pd.DataFrame(columns=["Urun_Adi", "Kategori", "Maliyet_TL_kg", "Nakliye_TL_kg"])

if "kayitlar" not in st.session_state:
    st.session_state.kayitlar = []

# ====================== TCMB KURLARI ======================
def tcmb_kur_getir():
    try:
        xml = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=10).text
        root = fromstring(xml)
        rates = {}
        for curr in root.findall(".//Currency"):
            kod = curr.get("Kod")
            selling = curr.find("ForexSelling")
            if selling is not None and selling.text:
                rates[kod] = float(selling.text)
        return rates
    except:
        return {"USD": 34.5, "EUR": 37.8, "GBP": 44.2, "CHF": 39.2}

rates = tcmb_kur_getir()

# ====================== ÜRÜN YÖNETİMİ ======================
if sayfa == "Ürün Yönetimi":
    st.header("🗃️ Ürün Yönetimi")

    # ====================== FİLTRELEME ======================
    st.subheader("🔎 Filtrele")
    kategori_filtre = st.selectbox(
        "Kategori Filtrele",
        ["Tümü", "Lignosülfonat - Ligno Esaslı", "Sülfonat Naftalin - Naftalin Esaslı", "Polikarboksilat Eter - PCE Esaslı"]
    )
    
    df_goster = st.session_state.urunler.copy()
    if kategori_filtre != "Tümü":
        df_goster = df_goster[df_goster["Kategori"] == kategori_filtre]

    # ====================== DÜZENLENEBİLİR TABLO + SİLME ======================
    st.subheader("Ürün Listesi")
    if not df_goster.empty:
        # Düzenlenebilir tablo
        edited_df = st.data_editor(
            df_goster,
            column_config={
                "Urun_Adi": st.column_config.TextColumn("Ürün Adı", disabled=True),
                "Kategori": st.column_config.TextColumn("Kategori", disabled=True),
                "Maliyet_TL_kg": st.column_config.NumberColumn("Maliyet (TL/kg)", format="%.2f"),
                "Nakliye_TL_kg": st.column_config.NumberColumn("Nakliye (TL/kg)", format="%.2f"),
            },
            use_container_width=True,
            num_rows="fixed",
            hide_index=True
        )

        # Değişiklikleri kaydet
        if not edited_df.equals(df_goster):
            # Sadece gösterilen satırları güncelle
            st.session_state.urunler.loc[edited_df.index, ["Maliyet_TL_kg", "Nakliye_TL_kg"]] = edited_df[["Maliyet_TL_kg", "Nakliye_TL_kg"]]

        # Silme için checkbox
        df_goster["Sil"] = False
        df_with_checkbox = st.data_editor(
            df_goster,
            column_config={"Sil": st.column_config.CheckboxColumn("Sil", default=False)},
            use_container_width=True,
            hide_index=True,
            disabled=["Urun_Adi", "Kategori", "Maliyet_TL_kg", "Nakliye_TL_kg"]
        )

        if st.button("Seçili Ürünleri Sil", type="secondary"):
            silinecekler = df_with_checkbox[df_with_checkbox["Sil"] == True].index
            if len(silinecekler) > 0:
                st.session_state.urunler = st.session_state.urunler.drop(silinecekler).reset_index(drop=True)
                st.success(f"✅ {len(silinecekler)} ürün silindi!")
                st.rerun()
            else:
                st.warning("Silinecek ürün seçmediniz.")
    else:
        st.info("Henüz ürün yok veya filtreye uyan ürün bulunamadı.")

    # ====================== YENİ ÜRÜN EKLE ======================
    with st.expander("➕ Yeni Ürün Ekle", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            yeni_urun = st.text_input("Ürün Adı")
            kategori = st.selectbox("Kategori", 
                ["Lignosülfonat - Ligno Esaslı", 
                 "Sülfonat Naftalin - Naftalin Esaslı", 
                 "Polikarboksilat Eter - PCE Esaslı"])
        with col2:
            yeni_maliyet = st.number_input("Maliyet (TL/kg)", min_value=0.0, step=0.01)
            yeni_nakliye = st.number_input("Nakliye (TL/kg)", min_value=0.0, step=0.01)
        
        if st.button("Ürünü Kaydet"):
            if yeni_urun:
                yeni_satir = pd.DataFrame([{
                    "Urun_Adi": yeni_urun,
                    "Kategori": kategori,
                    "Maliyet_TL_kg": yeni_maliyet,
                    "Nakliye_TL_kg": yeni_nakliye
                }])
                st.session_state.urunler = pd.concat([st.session_state.urunler, yeni_satir], ignore_index=True)
                st.success(f"✅ {yeni_urun} eklendi!")
                st.rerun()

    # ====================== KATEGORİ BAZLI TOPLU GÜNCELLEME ======================
    st.subheader("📈 Kategori Bazlı Toplu Güncelleme")
    kategori_secimi = st.selectbox(
        "Hangi kategoriye işlem uygulanacak?",
        ["Tümü", "Lignosülfonat - Ligno Esaslı", "Sülfonat Naftalin - Naftalin Esaslı", "Polikarboksilat Eter - PCE Esaslı"]
    )

    col1, col2 = st.columns(2)
    with col1:
        zam_orani = st.number_input("Zam Oranı (%)", min_value=0.0, step=0.1, value=5.0)
        if st.button("Seçili Kategoriye Zam Uygula", type="primary"):
            if kategori_secimi == "Tümü":
                st.session_state.urunler["Maliyet_TL_kg"] *= (1 + zam_orani / 100)
            else:
                mask = st.session_state.urunler["Kategori"] == kategori_secimi
                st.session_state.urunler.loc[mask, "Maliyet_TL_kg"] *= (1 + zam_orani / 100)
            st.success(f"✅ {kategori_secimi} kategorisine %{zam_orani} zam uygulandı!")
            st.rerun()

    with col2:
        nakliye_artisi = st.number_input("Nakliye Artışı (TL/kg)", min_value=0.0, step=0.01, value=1.0)
        if st.button("Seçili Kategoriye Nakliye Artışı Uygula"):
            if kategori_secimi == "Tümü":
                st.session_state.urunler["Nakliye_TL_kg"] += nakliye_artisi
            else:
                mask = st.session_state.urunler["Kategori"] == kategori_secimi
                st.session_state.urunler.loc[mask, "Nakliye_TL_kg"] += nakliye_artisi
            st.success(f"✅ {kategori_secimi} kategorisine {nakliye_artisi} TL/kg nakliye artışı uygulandı!")
            st.rerun()

# ====================== HESAPLAMA VE GEÇMİŞ KAYITLAR ======================
elif sayfa == "Hesaplama":
    # (Önceki kodun aynı kalıyor - kısaltmak için burada göstermiyorum)
    st.header("🧪 Fiyat Hesaplama")
    if len(st.session_state.urunler) == 0:
        st.warning("Önce Ürün Yönetimi sekmesinden ürün ekleyin!")
    else:
        secilen_urun = st.selectbox("Ürün Seç", st.session_state.urunler["Urun_Adi"])
        urun_bilgi = st.session_state.urunler[st.session_state.urunler["Urun_Adi"] == secilen_urun].iloc[0]
        
        st.info(f"**Kategori:** {urun_bilgi['Kategori']}")
        
        maliyet = st.number_input("Maliyet (TL/kg)", value=float(urun_bilgi["Maliyet_TL_kg"]), step=0.01)
        nakliye = st.number_input("Nakliye (TL/kg)", value=float(urun_bilgi["Nakliye_TL_kg"]), step=0.01)
        
        fabrika = st.selectbox("Fabrika", ["Gebze", "Adana", "Trabzon"])
        musteri_tipi = st.selectbox("Müşteri Tipi", ["Direkt Satış Müşterisi", "Bayi"])
        musteri_adi = st.text_input("Müşteri / Bayi Adı", "ABC İnşaat")
        marj = st.number_input("İstenen Marj (%)", min_value=0.0, step=0.1, value=25.0)

        if st.button("Hesapla ve Kaydet", type="primary"):
            # Hesaplama ve kayıt kodları (önceki versiyondaki aynı)
            birim_maliyet = maliyet + nakliye
            birim_satis = birim_maliyet * (1 + marj / 100)
            birim_kar = birim_satis - birim_maliyet

            st.success("✅ Hesaplandı!")
            st.subheader(f"{secilen_urun} — {fabrika}")
            st.write(f"**Müşteri:** {musteri_tipi} — {musteri_adi}")
            
            col1, col2 = st.columns(2)
            with col1: st.metric("Birim Maliyet", f"{birim_maliyet:.2f} TL")
            with col2: st.metric("Birim Kâr", f"{birim_kar:.2f} TL")

            st.table(pd.DataFrame({
                "Döviz": ["USD", "EUR", "GBP", "CHF"],
                "Maliyet": [round(birim_maliyet / rates.get(k, 34.5), 3) for k in ["USD","EUR","GBP","CHF"]],
                "Satış": [round(birim_satis / rates.get(k, 34.5), 3) for k in ["USD","EUR","GBP","CHF"]],
                "Kâr": [round(birim_kar / rates.get(k, 34.5), 3) for k in ["USD","EUR","GBP","CHF"]]
            }))

            st.session_state.kayitlar.insert(0, {
                "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Ürün": secilen_urun,
                "Kategori": urun_bilgi["Kategori"],
                "Müşteri": f"{musteri_tipi} - {musteri_adi}",
                "Fabrika": fabrika,
                "Maliyet TL/kg": round(birim_maliyet, 2),
                "Satış TL/kg": round(birim_satis, 2),
                "Kâr TL/kg": round(birim_kar, 2)
            })

elif sayfa == "Geçmiş Kayıtlar":
    st.header("📋 Geçmiş Hesaplamalar")
    if st.session_state.kayitlar:
        df = pd.DataFrame(st.session_state.kayitlar)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 Tüm Kayıtları İndir", csv, "fiyatopt_tum_kayitlar.csv", "text/csv")
    else:
        st.info("Henüz kayıt yok.")

st.caption("FiyatOpt Kimya • Tüm özellikler aktif • Kategori bazlı filtre, düzenleme ve silme eklendi")
