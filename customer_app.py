import psycopg2
import streamlit as st
import json
from datetime import datetime
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- ตั้งค่าหน้าตาเว็บไซต์ ---
st.set_page_config(
    page_title="Order Drink 🧋", 
    page_icon="🧋", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ระบบเชื่อมต่อ DB แบบ Cached Connection ---
@st.cache_resource
def init_connection():
    db_url = None
    if "postgres" in st.secrets and "url" in st.secrets["postgres"]:
        db_url = st.secrets["postgres"]["url"]
    elif "postgres_url" in st.secrets:
        db_url = st.secrets["postgres_url"]
    elif "DATABASE_URL" in st.secrets:
        db_url = st.secrets["DATABASE_URL"]
    
    if not db_url:
        st.error("❌ ไม่พบการตั้งค่า Secrets บน Streamlit Cloud")
        st.stop()
        
    return psycopg2.connect(db_url)

# --- CSS ตกแต่ง ---
st.markdown(
    """
    <style>
    [data-testid="stToolbar"], #MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }

    html, body, .stApp {
        overflow-x: hidden !important;
        max-width: 100vw !important;
        background-color: #F4EFEA !important;
        color: #3D342F !important;
    }

    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }

    .customer-header {
        background: linear-gradient(135deg, #8C6D58 0%, #6E5341 100%);
        padding: 8px;
        border-radius: 10px;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 10px;
    }

    /* 📌 บังคับรูปให้อยู่ตรงกลาง 100% */
    .menu-img-container {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-bottom: 8px;
    }

    .menu-img {
        max-height: 160px;
        width: auto;
        border-radius: 8px;
        object-fit: contain;
        display: block;
        margin: 0 auto;
    }

    div.stButton > button {
        background: #8C6D58 !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        padding: 2px 0px !important;
        border: none !important;
        width: 100% !important;
        min-height: 32px !important;
    }

    div.stButton > button:hover {
        background: #6E5341 !important;
    }

    .cart-container {
        background-color: #FFFFFF !important;
        border: 2px solid #C8B2A2 !important;
        border-radius: 12px !important;
        padding: 10px 12px !important;
        box-shadow: 0 4px 10px rgba(140, 109, 88, 0.1) !important;
        margin-top: 8px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# ==========================================
# 🌐 พจนานุกรมแปลภาษา UI
# ==========================================
LANGUAGES = {
    "🇹🇭 ไทย": {
        "header_title": "🧋 สั่งเครื่องดื่ม (กลับบ้าน)",
        "date_label": "📅 วันที่สั่งออเดอร์:",
        "table_label": "👤 ชื่อลูกค้า / คิวที่:",
        "table_default": "สั่งกลับบ้าน",
        "search_label": "🔍 ค้นหา:",
        "search_placeholder": "พิมพ์ชื่อ...",
        "select_menu": "👇 เลือกเมนู:",
        "price": "ราคา",
        "baht": "บ.",
        "topping_label": "ท็อปปิ้ง:",
        "no_topping": "เลือก...",
        "btn_add": "➕ สั่ง",
        "cart_title": "รายการที่เลือก",
        "cart_empty": "ยังไม่ได้เลือกรายการ",
        "total_price": "ราคารวม",
        "btn_order": "🚀 ยืนยันสั่งซื้อ",
        "btn_clear": "🗑️ ล้างรายการ",
        "err_table": "⚠️ กรุณาระบุชื่อหรือวิธีเรียกคิว",
        "success_msg": "🎉 ส่งออเดอร์เรียบร้อย นั่งรอเรียกคิวได้เลยครับ!",
        "success_backend_msg": "🎉 สั่งซื้อสำเร็จ! ออเดอร์ของคุณถูกส่งเข้าหลังบ้านแล้ว กรุณารอเรียกคิวครับ",
        "toast_added": "เพิ่มรายการแล้ว!"
    },
    "🇲🇲 Myanmar": {
        "header_title": "🧋 အဖျော်ယမကာ မှာယူရန် (ပါဆယ်)",
        "date_label": "📅 ရက်စွဲ:",
        "table_label": "👤 အမည် / ကူပွန်:",
        "table_default": "ပါဆယ်",
        "search_label": "🔍 ရှာရန်:",
        "search_placeholder": "ရှာရန်...",
        "select_menu": "👇 မီနူးရွေးပါ:",
        "price": "ဈေး",
        "baht": "ဘတ်",
        "topping_label": "ထပ်ဆောင်း:",
        "no_topping": "ရွေးပါ...",
        "btn_add": "➕ မှာမည်",
        "cart_title": "ခြင်းတောင်း",
        "cart_empty": "ခြင်းတောင်းထဲတွင် မရှိပါ",
        "total_price": "စုစုပေါင်း",
        "btn_order": "🚀 မှာယူမည်",
        "btn_clear": "🗑️ ပယ်ဖျက်",
        "err_table": "⚠️ အမည် ထည့်ပါ",
        "success_msg": "🎉 မှာယူမှု အောင်မြင်ပါသည်!",
        "success_backend_msg": "🎉 မှာယူမှု အောင်မြင်ပါသည်! အော်ဒါကို နောက်ဘက်စနစ်သို့ ပို့ပြီးပါပြီ",
        "toast_added": "ထည့်ပြီးပါပြီ!"
    },
    "🇨🇳 中文": {
        "header_title": "🧋 Takeaway Order 🥤",
        "date_label": "📅 Date:",
        "table_label": "👤 Name / Queue:",
        "table_default": "Takeaway",
        "search_label": "🔍 Search:",
        "search_placeholder": "Search...",
        "select_menu": "👇 Select:",
        "price": "ราคา",
        "baht": "฿",
        "topping_label": "Topping:",
        "no_topping": "Select...",
        "btn_add": "➕ Order",
        "cart_title": "Cart",
        "cart_empty": "Cart Empty",
        "total_price": "Total",
        "btn_order": "🚀 Confirm",
        "btn_clear": "🗑️ Clear",
        "err_table": "⚠️ Please enter Name / Queue No.",
        "success_msg": "🎉 Order Sent! Please take a seat.",
        "success_backend_msg": "🎉 Order successful! Your order has been sent to the kitchen.",
        "toast_added": "Added!"
    },
    "🇬🇧 English": {
        "header_title": "🧋 Takeaway Order 🥤",
        "date_label": "📅 Date:",
        "table_label": "👤 Name / Queue:",
        "table_default": "Takeaway",
        "search_label": "🔍 Search:",
        "search_placeholder": "Search...",
        "select_menu": "👇 Select menu:",
        "price": "Price",
        "baht": "THB",
        "topping_label": "Topping:",
        "no_topping": "Select...",
        "btn_add": "➕ Add",
        "cart_title": "Cart",
        "cart_empty": "Cart Empty",
        "total_price": "Total",
        "btn_order": "🚀 Confirm Order",
        "btn_clear": "🗑️ Clear",
        "err_table": "⚠️ Please enter Name / Queue No.",
        "success_msg": "🎉 Order sent successfully!",
        "success_backend_msg": "🎉 Order successful! Your order has been sent to the kitchen.",
        "toast_added": "Added!"
    }
}

# เก็บตารางแปลเดิมไว้เป็นข้อมูลสำรอง แต่ระบบด้านล่างจะใช้ Google Translate
MENU_TRANSLATIONS = {
    "ชาดำเย็น": {"🇲🇲 Myanmar": "လက်ဖက်ရည်အေး", "🇨🇳 中文": "冰红茶 Tea"},
    "ชามะนาว": {"🇲🇲 Myanmar": "သံပုရာ လက်ဖက်ရည်", "🇨🇳 中文": "柠檬茶 Lemon Tea"},
    "ชาเขียวมะนาว": {"🇲🇲 Myanmar": "သံပုရာ လက်ဖက်စိမ်း", "🇨🇳 中文": "柠檬绿 Lemon Green"},
    "ชาเขียวใส": {"🇲🇲 Myanmar": "လက်ဖက်စိမ်း", "🇨🇳 中文": "绿茶 Green Tea"},
    "โอเลี้ยง": {"🇲🇲 Myanmar": "ကော်ဖီနက်အေး", "🇨🇳 中文": "黑咖啡 Black Coffee"},
    "โกโก้": {"🇲🇲 Myanmar": "ကိုကိုး", "🇨🇳 中文": "可可 Cocoa"},
    "โอวัลติน": {"🇲🇲 Myanmar": "အိုဗာတင်း", "🇨🇳 中文": "阿华田 Ovaltine"},
    "เนสกาแฟ": {"🇲🇲 Myanmar": "နက်စ်ကဖေး", "🇨🇳 中文": "雀巢 Nescafe"},
    "กาแฟโบราณ": {"🇲🇲 Myanmar": "ရှေးဟောင်း ကော်ဖီ", "🇨🇳 中文": "古早咖啡 Thai Coffee"},
    "นมชมพู": {"🇲🇲 Myanmar": "နို့ဆီ ပန်းရောင်", "🇨🇳 中文": "粉红奶 Pink Milk"},
    "ชาไต้หวัน": {"🇲🇲 Myanmar": "ထိုင်ဝမ် လက်ဖက်ရည်", "🇨🇳 中文": "台湾奶茶 Taiwan Tea"},
    "ชาเย็น(ชานมไทย)": {"🇲🇲 Myanmar": "ထိုင်း နို့လက်ဖက်ရည်", "🇨🇳 中文": "泰奶 Thai Milk Tea"},
    "ชาเขียว(ชาเขียวนม)": {"🇲🇲 Myanmar": "နို့ လက်ဖက်စိမ်း", "🇨🇳 中文": "绿奶茶 Green Milk"},
    "กล้วยนมสด": {"🇲🇲 Myanmar": "ငှက်ပျော နို့အေး", "🇨🇳 中文": "香蕉鲜奶 Banana Milk"},
    "ชาแคนตาลูป(แคนตาลูป)": {"🇲🇲 Myanmar": "သခွားမွှေး လက်ဖက်ရည်", "🇨🇳 中文": "哈密瓜茶 Melon Tea"},
    "ชาแคนตาลูป": {"🇲🇲 Myanmar": "သခွားမွှေး လက်ဖက်ရည်", "🇨🇳 中文": "哈密瓜茶 Melon Tea"},
    "ชาแดงน้ำผึ้งมะนาว": {"🇲🇲 Myanmar": "ပျားရည် သံပုရာ လက်ဖက်နီ", "🇨🇳 中文": "蜂蜜柠檬红茶 Honey Lemon Red Tea"},
    "ชาแดงปั่น": {"🇲🇲 Myanmar": "လက်ဖက်နီ ဖျော်စက်", "🇨🇳 中文": "冰沙红茶 Red Tea Smoothie"},
    "ชาไต้หวันบราวน์ชูการ์ปั่น": {"🇲🇲 Myanmar": "ထိုင်ဝမ် စိမ်းလမ်း သကြား ဖျော်စက်", "🇨🇳 中文": "黑糖台湾奶茶冰沙 Brown Sugar Milk Tea Smoothie"},
    "ชาไต้หวันปั่น": {"🇲🇲 Myanmar": "ထိုင်ဝမ် လက်ဖက်ရည် ဖျော်စက်", "🇨🇳 中文": "台湾奶茶冰沙 Taiwan Milk Tea Smoothie"},
    "ชานมกาแฟ": {"🇲🇲 Myanmar": "နို့ ကော်ဖီ", "🇨🇳 中文": "咖啡奶茶 Coffee Milk Tea"},
    "ชานมโกโก้": {"🇲🇲 Myanmar": "နို့ ကိုကိုး", "🇨🇳 中文": "可可奶茶 Cocoa Milk Tea"},
    "ชานมโกโก้ปั่น": {"🇲🇲 Myanmar": "နို့ ကိုကိုး ဖျော်စက်", "🇨🇳 中文": "可可奶茶冰沙 Cocoa Milk Tea Smoothie"},
    "ชานมคาราเมล": {"🇲🇲 Myanmar": "ကာရာမဲလ် နို့လက်ဖက်ရည်", "🇨🇳 中文": "焦糖奶茶 Caramel Milk Tea"},
    "ชานมไต้หวันบราวน์ชูการ์": {"🇲🇲 Myanmar": "ထိုင်ဝမ် စိမ်းလမ်း သကြား နို့လက်ဖက်ရည်", "🇨🇳 中文": "黑糖台湾奶茶 Brown Sugar Taiwan Milk Tea"},
    "ชานมน้ำผึ้ง": {"🇲🇲 Myanmar": "ပျားရည် နို့လက်ဖက်ရည်", "🇨🇳 中文": "蜂蜜奶茶 Honey Milk Tea"},
    "ชานมผลไม้": {"🇲🇲 Myanmar": "သစ်သီး နို့လက်ဖက်ရည်", "🇨🇳 中文": "水果奶茶 Fruit Milk Tea"},
    "ชานมเผือก": {"🇲🇲 Myanmar": "ပိန်းဥ နို့လက်ဖက်ရည်", "🇨🇳 中文": "香芋奶茶 Taro Milk Tea"}
}

WORD_MAP = {
    "🇲🇲 Myanmar": {
        "ชา": "လက်ဖက်ရည်", "นม": "နို့", "เขียว": "စိမ်း", "แดง": "နီ", 
        "ไต้หวัน": "ထိုင်ဝမ်", "ปั่น": "ဖျော်စက်", "มะนาว": "သံပုရာ", 
        "น้ำผึ้ง": "ပျားရည်", "เผือก": "ပိန်းဥ", "โกโก้": "ကိုကိုး", 
        "กาแฟ": "ကော်ဖီ", "คาราเมล": "ကာရာမဲလ်", "บราวน์ชูการ์": "စိမ်းလမ်း သကြား"
    },
    "🇨🇳 中文": {
        "ชา": "Tea", "นม": "Milk", "เขียว": "Green", "แดง": "Red", 
        "ไต้หวัน": "Taiwan", "ปั่น": "Smoothie", "มะนาว": "Lemon", 
        "น้ำผึ้ง": "Honey", "เผือก": "Taro", "โกโก้": "Cocoa", 
        "กาแฟ": "Coffee", "คาราเมล": "Caramel", "บราวน์ชูการ์": "Brown Sugar"
    }
}

@st.cache_data(ttl=86400, show_spinner=False)
def _translate_text_cached(text, target):
    """แปลข้อความ 1 รายการและเก็บ cache 24 ชั่วโมง"""
    if not text or not str(text).strip():
        return str(text or "")
    try:
        return GoogleTranslator(source="th", target=target).translate(str(text))
    except Exception:
        return str(text)

@st.cache_data(ttl=86400, show_spinner=False)
def _translate_many_cached(texts, target):
    """
    แปลหลายรายการพร้อมกัน แล้ว cache ผลลัพธ์
    ลดเวลาค้างตอนเปลี่ยนภาษา และไม่เรียก API ซ้ำในทุกการ rerun
    """
    unique_texts = list(dict.fromkeys(str(x) for x in texts if str(x).strip()))
    if not unique_texts:
        return {}

    # ภาษาไทยไม่ต้องส่งออกไปแปล
    if target == "th":
        return {x: x for x in unique_texts}

    results = {x: x for x in unique_texts}

    def worker(value):
        return value, _translate_text_cached(value, target)

    # จำกัดจำนวนการเชื่อมต่อพร้อมกัน เพื่อลดโอกาสถูกบริการแปลบล็อก
    with ThreadPoolExecutor(max_workers=min(6, len(unique_texts))) as executor:
        futures = [executor.submit(worker, value) for value in unique_texts]
        for future in as_completed(futures):
            try:
                original, translated = future.result()
                results[original] = translated or original
            except Exception:
                pass

    return results

def get_translation_target(lang):
    return {
        "🇹🇭 ไทย": "th",
        "🇲🇲 Myanmar": "my",
        "🇨🇳 中文": "zh-CN",
        "🇬🇧 English": "en"
    }.get(lang, "th")

def translate_item(name_th, lang, translated_map=None):
    """แปลจากแผนที่ที่สร้างครั้งเดียวต่อภาษา เพื่อลดการค้างของหน้าเว็บ"""
    name_th = str(name_th or "")
    if lang == "🇹🇭 ไทย":
        return name_th
    if translated_map is not None:
        return translated_map.get(name_th, name_th)
    return _translate_text_cached(name_th, get_translation_target(lang))

# --- ดึงข้อมูลเมนูและท็อปปิ้ง ---
@st.cache_data(ttl=60)
def load_db_data():
    menu_dict = {}
    topping_dict = {}
    try:
        conn = init_connection()
        if conn.closed != 0:
            st.cache_resource.clear()
            conn = init_connection()

        with conn.cursor() as c:
            c.execute("SELECT name, cost, price, image_url FROM menu_items ORDER BY name ASC")
            for r in c.fetchall():
                img = str(r[3]).strip() if len(r) > 3 and r[3] and str(r[3]).strip() != "" else None
                menu_dict[r[0]] = {"cost": float(r[1]), "price": float(r[2]), "image_url": img}
            
            c.execute("SELECT name, price FROM toppings ORDER BY price ASC, name ASC")
            for r in c.fetchall():
                topping_dict[r[0]] = {"cost": 1.0, "price": float(r[1])}
    except Exception as e:
        st.error(f"❌ Error ดึงข้อมูล DB: {e}")
    return menu_dict, topping_dict

if "cart" not in st.session_state:
    st.session_state.cart = []

# สถานะยืนยันการส่งออเดอร์สำเร็จ
if "order_success" not in st.session_state:
    st.session_state.order_success = False

# --- เลือกภาษา ---
selected_lang = st.segmented_control(
    "Language",
    options=["🇹🇭 ไทย", "🇲🇲 Myanmar", "🇨🇳 中文", "🇬🇧 English"],
    default="🇹🇭 ไทย",
    key="lang_segmented"
) or "🇹🇭 ไทย"

t = LANGUAGES[selected_lang]

# แสดงข้อความยืนยันหลังจากบันทึกออเดอร์สำเร็จแล้ว
if st.session_state.order_success:
    st.success(t["success_backend_msg"], icon="🎉")
    st.toast(t["success_backend_msg"], icon="🎉")
    # แสดงข้อความเฉพาะรอบการโหลดนี้ เพื่อไม่ให้ขึ้นซ้ำเมื่อผู้ใช้ใช้งานต่อ
    st.session_state.order_success = False

# --- Header ---
st.markdown(
    f"""
    <div class="customer-header">
        <h3 style="margin: 0; font-size: 16px; font-weight: 700;">{t['header_title']}</h3>
    </div>
    """, 
    unsafe_allow_html=True
)

col_top1, col_top2, col_top3 = st.columns([1, 1, 1])
with col_top1:
    order_date = st.date_input(t['date_label'], datetime.now().date(), key="order_date_input")
with col_top2:
    table_number = st.text_input(t['table_label'], value=t['table_default'], key="table_no_input")
with col_top3:
    search_query = st.text_input(t['search_label'], "", placeholder=t['search_placeholder'])

current_menu, current_toppings = load_db_data()

# ===== แปลข้อมูลครั้งเดียวต่อภาษา แล้วนำผลไปใช้ทั้งหน้า =====
# ปัญหาเดิม: translate_item ถูกเรียกซ้ำหลายครั้งในลูปเมนู/ค้นหา/ท็อปปิ้ง
# ทำให้การเปลี่ยนภาษาเกิด network request จำนวนมากและหน้า Streamlit ดูเหมือนค้าง
target_lang = get_translation_target(selected_lang)

all_texts_to_translate = list(current_menu.keys()) + list(current_toppings.keys())
if selected_lang == "🇹🇭 ไทย":
    translated_map = {str(x): str(x) for x in all_texts_to_translate}
else:
    translated_map = _translate_many_cached(tuple(all_texts_to_translate), target_lang)

menu_display_map = {
    name_th: translate_item(name_th, selected_lang, translated_map)
    for name_th in current_menu.keys()
}
topping_display_map = {
    translate_item(name_th, selected_lang, translated_map): name_th
    for name_th in current_toppings.keys()
}

topping_options = [
    f"{display_name} (+{int(current_toppings[th_name]['price'])} {t['baht']})"
    for display_name, th_name in topping_display_map.items()
]

if not current_menu:
    st.info("⏳ กำลังโหลดรายการเมนู...")
else:
    # ใช้คำแปลที่สร้างไว้แล้ว ห้ามเรียก API ซ้ำในลูปนี้
    filtered_items = [
        (name_th, menu_display_map.get(name_th, name_th), info)
        for name_th, info in current_menu.items()
        if (
            search_query.lower() in name_th.lower()
            or search_query.lower() in menu_display_map.get(name_th, name_th).lower()
        )
    ]

    NUM_COLS = 2
    for i in range(0, len(filtered_items), NUM_COLS):
        cols = st.columns(NUM_COLS)
        for j in range(NUM_COLS):
            if i + j < len(filtered_items):
                item_name_th, display_name, info = filtered_items[i + j]
                price, cost, image_url = info["price"], info["cost"], info.get("image_url")

                counter_key = f"counter_{item_name_th}"
                if counter_key not in st.session_state:
                    st.session_state[counter_key] = 0

                with cols[j]:
                    # 📌 ใช้ HTML Tag แสดงรูปภาพโดยตรงเพื่อบังคับจัดกึ่งกลาง 100%
                    if image_url:
                        st.markdown(
                            f"""
                            <div class="menu-img-container">
                                <img src="{image_url}" class="menu-img" />
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )

                    st.markdown(
                        f"""
                        <div style="background-color: #FFFFFF; border: 1.5px solid #C8B2A2; border-radius: 10px; padding: 8px; text-align: center; margin-bottom: 6px;">
                            <div style="font-weight: 700; font-size: 13px; min-height: 28px; display: flex; align-items: center; justify-content: center; line-height: 1.2; color: #2C221E;">{display_name}</div>
                            <div style="color: #8C6D58; font-weight: 800; font-size: 13px; margin-top: 2px;">{price:.0f} {t['baht']}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    multiselect_key = f"tp_{item_name_th}_{st.session_state[counter_key]}"
                    selected_tps = st.multiselect(
                        t['topping_label'], 
                        options=topping_options, 
                        key=multiselect_key,
                        placeholder=t['no_topping']
                    )
                    
                    if st.button(t['btn_add'], key=f"b_{item_name_th}", use_container_width=True):
                        selected_tp_display_names = [tp.split(" (+")[0] for tp in selected_tps]
                        selected_tp_names = [
                            topping_display_map.get(display_name, display_name)
                            for display_name in selected_tp_display_names
                        ]

                        total_tp_price = sum(
                            current_toppings.get(tp_name, {}).get("price", 0)
                            for tp_name in selected_tp_names
                        )
                        total_tp_cost = sum(
                            current_toppings.get(tp_name, {}).get("cost", 0)
                            for tp_name in selected_tp_names
                        )

                        # เก็บ name เป็นภาษาไทยสำหรับหลังบ้าน และ display_name เป็นภาษาที่ลูกค้าเลือก
                        tp_text_th = f" (+{', '.join(selected_tp_names)})" if selected_tp_names else ""
                        tp_text_display = (
                            f" (+{', '.join(selected_tp_display_names)})"
                            if selected_tp_display_names else ""
                        )

                        st.session_state.cart.append({
                            "name": f"{item_name_th}{tp_text_th}",
                            "display_name": f"{display_name}{tp_text_display}",
                            "price": price + total_tp_price,
                            "cost": cost + total_tp_cost
                        })

                        st.session_state[counter_key] += 1
                        st.toast(t['toast_added'], icon="🛒")
                        st.rerun()

# ==========================================
# 🛒 ตะกร้าสินค้า
# ==========================================
st.divider()

if not st.session_state.cart:
    st.info(f"🛒 {t['cart_title']}: {t['cart_empty']}")
else:
    total_price = sum(item['price'] for item in st.session_state.cart)
    total_cost = sum(item['cost'] for item in st.session_state.cart)

    st.markdown(
        f"""
        <div class="cart-container">
            <h3 style="margin-top:0; margin-bottom: 8px; color: #3D342F; font-size: 15px;">🛒 {t['cart_title']}</h3>
        """, 
        unsafe_allow_html=True
    )

    for idx, cart_item in enumerate(st.session_state.cart):
        col_name, col_price, col_del = st.columns([5, 3, 1], vertical_alignment="center")
        
        with col_name:
            st.markdown(f"<span style='font-size: 12px; font-weight: 600; color: #2C221E;'>• {cart_item['display_name']}</span>", unsafe_allow_html=True)
        
        with col_price:
            st.markdown(f"<span style='font-size: 12px; font-weight: 700; color: #8C6D58;'>{cart_item['price']:.0f} {t['baht']}</span>", unsafe_allow_html=True)
        
        with col_del:
            if st.button("❌", key=f"remove_cart_{idx}", help="ลบรายการนี้"):
                st.session_state.cart.pop(idx)
                st.rerun()

    st.markdown("<hr style='border: 0; border-top: 1.5px dashed #C8B2A2; margin: 8px 0;'>", unsafe_allow_html=True)

    col_tot_label, col_tot_val = st.columns([5, 4], vertical_alignment="center")
    with col_tot_label:
        st.markdown(f"<h4 style='margin:0; color: #3D342F; font-size: 13px;'>💰 {t['total_price']}:</h4>", unsafe_allow_html=True)
    with col_tot_val:
        st.markdown(f"<h3 style='margin:0; color: #8C6D58; font-weight: 800; font-size: 15px;'>{total_price:.0f} {t['baht']}</h3>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    col_order_btn, col_clear_btn = st.columns([2, 1])

    with col_order_btn:
        if st.button(t['btn_order'], type="primary", use_container_width=True):
            if not table_number.strip():
                st.error(t['err_table'])
            else:
                try:
                    conn = init_connection()
                    with conn.cursor() as c:
                        items_json = json.dumps(st.session_state.cart, ensure_ascii=False)
                        created_timestamp = datetime.combine(order_date, datetime.now().time())
                        
                        c.execute("""
                            INSERT INTO orders (table_number, items_json, total_price, total_cost, status, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (table_number.strip(), items_json, total_price, total_cost, 'pending', created_timestamp))
                        conn.commit()

                    # บันทึกสำเร็จแล้ว จึงล้างตะกร้าและแสดงการยืนยันหลัง rerun
                    st.session_state.cart = []
                    st.session_state.order_success = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error submitting order: {e}")

    with col_clear_btn:
        if st.button(t['btn_clear'], use_container_width=True):
            st.session_state.cart = []
            st.rerun()
