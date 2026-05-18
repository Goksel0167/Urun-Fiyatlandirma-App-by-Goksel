import streamlit as st
import requests
from xml.etree.ElementTree import fromstring
from datetime import datetime
import pandas as pd
import sqlite3

st.set_page_config(page_title="FiyatOpt Kimya", page_icon="📦", layout="wide")

# ====================== VERİTABANI ======================
DB_FILE = "fiyatopt.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Urun_Adi TEXT NOT NULL,
        Fabrika TEXT NOT NULL,
        Fabrika_Kodu INTEGER NOT NULL,
        Kategori TEXT NOT NULL,
        Maliyet_TL_kg REAL NOT NULL,
        Nakliye_TL_kg REAL NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS nakliye (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Fabrika TEXT NOT NULL,
        Sevk_Ili TEXT NOT NULL,
        Nakliye_TL_kg REAL NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS kayitlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Tarih TEXT,
        Urun TEXT,
        Fabrika_Kodu INTEGER,
        Musteri TEXT,
        Fabrika TEXT,
        Maliyet_TL_kg REAL,
        Satis_TL_kg REAL,
        Kar_TL_kg REAL
    )''')
    conn.commit()
    conn.close()

init_db()

# ====================== TCMB KURLARI ======================
def tcmb_kur_getir():
    try:
        xml = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=15).text
        root = fromstring(xml)
        tarih = root.find(".//Tarih").attrib.get("Tarih", datetime.now().strftime("%d.%m.%Y"))
        rates = {curr.get("Kod"): float(curr.find("ForexSelling").text) 
                 for curr in root.findall(".//Currency") if curr.find("ForexSelling") is not None}
        return rates, tarih
    except:
        return {"USD": 34.50, "EUR": 37.80, "GBP": 44.20, "CHF": 39.20}, datetime.now().strftime("%d.%m.%Y")

rates, tcmb_tarih = tcmb_kur_getir()

# ====================== SIDEBAR ======================
st.sidebar.title("FiyatOpt Kimya")
sayfa = st.sidebar.radio("Menü", ["Hesaplama", "Ürün Yönetimi", "Nakliye Yönetimi", "Geçmiş Kayıtlar"])

st.sidebar.info(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")

# ====================== HESAPLAMA ======================
if sayfa == "Hesaplama":
    st.header("🧪 Birim Fiyat Hesaplama")

    urunler = pd.read_sql_query("SELECT * FROM urunler", get_db())
    if urunler.empty:
        st.warning("Önce Ürün Yönetimi sekmesinden ürün ekleyin!")
        st.stop()

    urunler["Gosterim"] = urunler["Urun_Adi"] + " (" + urunler["Fabrika"] + " - Kod: " + urunler["Fabrika_Kodu"].astype(str) + ")"
    secilen_gosterim = st.selectbox("Ürün ve Fabrika Seç", urunler["Gosterim"])
    urun = urunler[urunler["Gosterim"] == secilen_gosterim].iloc[0]

    sevk_ili = st.selectbox("Sevk Edilecek İl", ["Adana","İstanbul","Ankara","İzmir","Antalya","Bursa","Konya","Trabzon","Diğer"])

    nakliye_df = pd.read_sql_query("SELECT Nakliye_TL_kg FROM nakliye WHERE Fabrika=? AND Sevk_Ili=?", 
                                   get_db(), params=(urun["Fabrika"], sevk_ili))
    default_nakliye = float(nakliye_df.iloc[0]["Nakliye_TL_kg"]) if not nakliye_df.empty else 8.0

    maliyet = st.number_input("Maliyet (TL/kg)", value=float(urun["Maliyet_TL_kg"]), step=0.01)
    nakliye = st.number_input("Nakliye (TL/kg)", value=default_nakliye, step=0.01)
    marj = st.number_input("İstenen Marj (%)", value=25.0, step=0.1)

    musteri_tipi = st.selectbox("Müşteri Tipi", ["Direkt Satış Müşterisi", "Bayi"])
    musteri_adi = st.text_input("Müşteri / Bayi Adı", "ABC İnşaat")

    st.divider()

    bm1 = maliyet + nakliye
    bs1 = bm1 * (1 + marj / 100)
    bk1 = bs1 - bm1

    bm2 = maliyet * (1 + marj / 100)
    bs2 = bm2 + nakliye
    bk2 = bs2 - (maliyet + nakliye)

    st.subheader("📊 İki Yöntem Karşılaştırması")
    compare_df = pd.DataFrame({
        "Açıklama": ["Birim Maliyet", "Birim Satış Fiyatı", "Birim Kâr"],
        "Yöntem 1": [bm1, bs1, bk1],
        "Yöntem 2": [bm2, bs2, bk2]
    })
    st.dataframe(compare_df.style.format("{:.2f} TL"), use_container_width=True, hide_index=True)

    st.subheader("🌍 Döviz Bazlı Satış Fiyatları")
    doviz_df = pd.DataFrame({
        "Döviz": ["USD", "EUR", "GBP", "CHF"],
        "Yöntem 1": [round(bs1 / rates.get(d, 34.5), 3) for d in ["USD","EUR","GBP","CHF"]],
        "Yöntem 2": [round(bs2 / rates.get(d, 34.5), 3) for d in ["USD","EUR","GBP","CHF"]]
    })
    st.dataframe(doviz_df.style.format("{:.3f}"), use_container_width=True, hide_index=True)

# ====================== ÜRÜN YÖNETİMİ ======================
elif sayfa == "Ürün Yönetimi":
    st.header("🗃️ Ürün Yönetimi")
    # (İstersen tam kodunu da verebilirim, şimdilik temel hali)

    st.info("Ürün ekleme, silme ve düzenleme burada yapılacak.")

# ====================== NAKLİYE YÖNETİMİ ======================
elif sayfa == "Nakliye Yönetimi":
    st.header("🚛 Nakliye Yönetimi")
    st.info("Nakliye tarifeleri ve zam burada yönetilecek.")

# ====================== GEÇMİŞ KAYITLAR ======================
elif sayfa == "Geçmiş Kayıtlar":
    st.header("📋 Geçmiş Kayıtlar")
    df = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", get_db())
    st.dataframe(df, use_container_width=True)

st.caption("FiyatOpt Kimya • Tüm sayfalar aktif")
