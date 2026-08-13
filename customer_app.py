import psycopg2
import streamlit as st
import time
import json
from datetime import datetime

# --- ตั้งค่าหน้าตาเว็บไซต์ ---
st.set_page_config(
    page_title="Order Drink 🧋", 
    page_icon="🧋", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- เชื่อมต่อฐานข้อมูล Supabase / Postgres ---
def get_db_connection():
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

# --- CSS ตกแต่ง + ทำเส้นขอบล้อมรอบการ์ดเมนูทุกองค์ประกอบ ---
st.markdown(
    """
    <style>
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { visibility: hidden !important; }

    .stApp {
        background-color: #F4EFEA !important;
        color: #3D342F !important;
    }

    .customer-header {
        background: linear-gradient(135deg, #8C6D58 0%, #6E5341 100%);
        padding: 10px;
        border-radius: 12px;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 12px;
    }

    /* ⚡ ล็อก Layout Grid 3 คอลัมน์ ⚡ */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }

    div[data-testid="stHorizontalBlock"] > div {
        width: 33.33% !important;
        min-width: 0 !important;
        flex: 1 1 33.33% !important;
    }

    /* 📦 กรอบการ์ดเมนูแบบมีเส้นขอบชัดเจน (รวมทุกอย่างไว้ในกล่องเดียว) */
    div[data-testid="stColumn"] > div {
        background-color: #FFFFFF !important;
        border: 2px solid #C8B2A2 !important; /* เส้นขอบสีเข้มชัดเจน */
        border-radius: 12px !important;
        padding: 8px 10px !important;
        box-shadow: 0 2px 6px rgba(140, 109, 88, 0.12) !important;
        margin-bottom: 6px !important;
    }

    /* เส้นขีดแบ่งโซนภายในกล่องเมนู */
    .card-divider {
        border-top: 1px dashed #D3C4B8;
        margin: 6px 0;
    }

    /* ปุ่มกดปรับให้เต็มความกว้างในกล่อง */
    div.stButton > button {
        background: #8C6D58 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 4px 8px !important;
        border: none !important;
        width: 100% !important;
    }

    div.stButton > button:hover {
        background: #6E5341 !important;
    }

    /* ปรับแต่ง Checkbox */
    div[data-testid="stCheckbox"] label span {
        font-size: 12px !important;
        font-weight: 500 !important;
        color: #554840 !important;
    }
    
    div[data-testid="stCheckbox"] {
        margin-bottom: 4px !important;
    }

    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

PEARL_PRICE = 4.0  
PEARL_COST = 1.0

# ==========================================
# 🌐 พจนานุกรมแปลภาษา UI
# ==========================================
LANGUAGES = {
    "🇹🇭 ไทย": {
        "header_title": "🧋 เมนูเครื่องดื่ม",
        "table_label": "📍 โต๊ะ/ชื่อ:",
        "table_default": "โต๊ะ 1",
        "search_label": "🔍 ค้นหา:",
        "search_placeholder": "พิมพ์ชื่อ...",
        "select_menu": "👇 เลือกเมนู:",
        "price": "ราคา",
        "baht": "บ.",
        "add_pearl": "+ไข่มุก",
        "btn_add": "➕ สั่ง",
        "cart_title": "🛒 ตะกร้าของคุณ",
        "cart_empty": "ไม่มีรายการในตะกร้า",
        "total_price": "ราคารวม",
        "btn_order": "🚀 ยืนยันการสั่งซื้อ",
        "btn_clear": "🗑️ ล้างตะกร้า",
        "err_table": "⚠️ กรุณาระบุหมายเลขโต๊ะหรือชื่อ",
        "success_msg": "🎉 ส่งออเดอร์เรียบร้อย!",
        "toast_added": "เพิ่มแล้ว!"
    },
    "🇲🇲 Myanmar": {
        "header_title": "🧋 အဖျော်ယမကာ မီနူး",
        "table_label": "📍 စားပွဲ/အမည်:",
        "table_default": "စားပွဲ ၁",
        "search_label": "🔍 ရှာရန်:",
        "search_placeholder": "ရှာရန်...",
        "select_menu": "👇 မီနူးရွေးပါ:",
        "price": "ဈေး",
        "baht": "ဘတ်",
        "add_pearl": "+ကျောက်ကျော",
        "btn_add": "➕ မှာမည်",
        "cart_title": "🛒 ခြင်းတောင်း",
        "cart_empty": "ခြင်းတောင်းထဲတွင် မရှိပါ",
        "total_price": "စုစုပေါင်း",
        "btn_order": "🚀 မှာယူမည်",
        "btn_clear": "🗑️ ပယ်ဖျက်",
        "err_table": "⚠️ စားပွဲနံပါတ် ထည့်ပါ",
        "success_msg": "🎉 မှာယူမှု အောင်မြင်ပါသည်!",
        "toast_added": "ထည့်ပြီးပါပြီ!"
    },
    "🇨🇳 中文/EN": {
        "header_title": "🧋 菜单 Menu",
        "table_label": "📍 桌号 Table:",
        "table_default": "Table 1",
        "search_label": "🔍 搜索 Search:",
        "search_placeholder": "Search...",
        "select_menu": "👇 选择饮料 Select:",
        "price": "ราคา",
        "baht": "฿",
        "add_pearl": "+珍珠 Pearls",
        "btn_add": "➕ 点餐 Order",
        "cart_title": "🛒 购物车 Cart",
        "cart_empty": "购物车为空 Empty",
        "total_price": "总计 Total",
        "btn_order": "🚀 确认下单 Confirm",
        "btn_clear": "🗑️ 清空",
        "err_table": "⚠️ 请填写桌号 Enter table",
        "success_msg": "🎉 下单成功 Order Sent!",
        "toast_added": "已加入 Added!"
    }
}

MENU_TRANSLATIONS = {
    "ชาดำเย็น": {"🇲🇲 Myanmar": "လက်ဖက်ရည်အေး", "🇨🇳 中文/EN": "冰红茶 Tea"},
    "ชามะนาว": {"🇲🇲 Myanmar": "သံပုရာ လက်ဖက်ရည်", "🇨🇳 中文/EN": "柠檬茶 Lemon Tea"},
    "ชาเขียวมะนาว": {"🇲🇲 Myanmar": "သံပုရာ လက်ဖက်စိမ်း", "🇨🇳 中文/EN": "柠檬绿 Lemon Green"},
    "ชาเขียวใส": {"🇲🇲 Myanmar": "လက်ဖက်စိမ်း", "🇨🇳 中文/EN": "绿茶 Green Tea"},
    "โอเลี้ยง": {"🇲🇲 Myanmar": "ကော်ဖီနက်အေး", "🇨🇳 中文/EN": "黑咖啡 Black Coffee"},
    "โกโก้": {"🇲🇲 Myanmar": "ကိုကိုး", "🇨🇳 中文/EN": "可可 Cocoa"},
    "โอวัลติน": {"🇲🇲 Myanmar": "အိုဗာတင်း", "🇨🇳 中文/EN": "阿华田 Ovaltine"},
    "เนสกาแฟ": {"🇲🇲 Myanmar": "နက်စ်ကဖေး", "🇨🇳 中文/EN": "雀巢 Nescafe"},
    "กาแฟโบราณ": {"🇲🇲 Myanmar": "ရှေးဟောင်း ကော်ဖီ", "🇨🇳 中文/EN": "古早咖啡 Thai Coffee"},
    "นมชมพู": {"🇲🇲 Myanmar": "နို့ဆီ ပန်းရောင်", "🇨🇳 中文/EN": "粉红奶 Pink Milk"},
    "ชาไต้หวัน": {"🇲🇲 Myanmar": "ထိုင်ဝမ် လက်ဖက်ရည်", "🇨🇳 中文/EN": "台湾奶茶 Taiwan Tea"},
    "ชาเย็น(ชานมไทย)": {"🇲🇲 Myanmar": "ထိုင်း နို့လက်ဖက်ရည်", "🇨🇳 中文/EN": "泰奶 Thai Milk Tea"},
    "ชาเขียว(ชาเขียวนม)": {"🇲🇲 Myanmar": "နို့ လက်ဖက်စိမ်း", "🇨🇳 中文/EN": "绿奶茶 Green Milk"},
    "กล้วยนมสด": {"🇲🇲 Myanmar": "ငှက်ပျော နို့အေး", "🇨🇳 中文/EN": "香蕉鲜奶 Banana Milk"},
    "ชาแคนตาลูป(แคนตาลูป)": {"🇲🇲 Myanmar": "သခွားမွှေး လက်ဖက်ရည်", "🇨🇳 中文/EN": "哈密瓜茶 Melon Tea"},
    "ชาแคนตาลูป": {"🇲🇲 Myanmar": "သခွားမွှေး လက်ဖက်ရည်", "🇨🇳 中文/EN": "哈密瓜茶 Melon Tea"},
    "ชาแดงน้ำผึ้งมะนาว": {"🇲🇲 Myanmar": "ပျားရည် သံပုရာ လက်ဖက်နီ", "🇨🇳 中文/EN": "蜂蜜柠檬红茶 Honey Lemon Red Tea"},
    "ชาแดงปั่น": {"🇲🇲 Myanmar": "လက်ဖက်နီ ဖျော်စက်", "🇨🇳 中文/EN": "冰沙红茶 Red Tea Smoothie"},
    "ชาไต้หวันบราวน์ชูการ์ปั่น": {"🇲🇲 Myanmar": "ထိုင်ဝမ် စိမ်းလမ်း သကြား ဖျော်စက်", "🇨🇳 中文/EN": "黑糖台湾奶茶冰沙 Brown Sugar Milk Tea Smoothie"},
    "ชาไต้หวันปั่น": {"🇲🇲 Myanmar": "ထိုင်ဝမ် လက်ဖက်ရည် ဖျော်စက်", "🇨🇳 中文/EN": "台湾奶茶冰沙 Taiwan Milk Tea Smoothie"},
    "ชานมกาแฟ": {"🇲🇲 Myanmar": "နို့ ကော်ဖီ", "🇨🇳 中文/EN": "咖啡奶茶 Coffee Milk Tea"},
    "ชานมโกโก้": {"🇲🇲 Myanmar": "နို့ ကိုကိုး", "🇨🇳 中文/EN": "可可奶茶 Cocoa Milk Tea"},
    "ชานมโกโก้ปั่น": {"🇲🇲 Myanmar": "နို့ ကိုကိုး ဖျော်စက်", "🇨🇳 中文/EN": "可可奶茶冰沙 Cocoa Milk Tea Smoothie"},
    "ชานมคาราเมล": {"🇲🇲 Myanmar": "ကာရာမဲလ် နို့လက်ဖက်ရည်", "🇨🇳 中文/EN": "焦糖奶茶 Caramel Milk Tea"},
    "ชานมไต้หวันบราวน์ชูการ์": {"🇲🇲 Myanmar": "ထိုင်ဝမ် စိမ်းလမ်း သကြား နို့လက်ဖက်ရည်", "🇨🇳 中文/EN": "黑糖台湾奶茶 Brown Sugar Taiwan Milk Tea"},
    "ชานมน้ำผึ้ง": {"🇲🇲 Myanmar": "ပျားရည် နို့လက်ဖက်ရည်", "🇨🇳 中文/EN": "蜂蜜奶茶 Honey Milk Tea"},
    "ชานมผลไม้": {"🇲🇲 Myanmar": "သစ်သီး နို့လက်ဖက်ရည်", "🇨🇳 中文/EN": "水果奶茶 Fruit Milk Tea"},
    "ชานมเผือก": {"🇲🇲 Myanmar": "ပိန်းဥ နို့လက်ဖက်ရည်", "🇨🇳 中文/EN": "香芋奶茶 Taro Milk Tea"}
}

WORD_MAP = {
    "🇲🇲 Myanmar": {
        "ชา": "လက်ဖက်ရည်", "นม": "နို့", "เขียว": "စိမ်း", "แดง": "နီ", 
        "ไต้หวัน": "ထိုင်ဝမ်", "ปั่น": "ဖျော်စက်", "มะนาว": "သံပုရာ", 
        "น้ำผึ้ง": "ပျားရည်", "เผือก": "ပိန်းဥ", "โกโก้": "ကိုကိုး", 
        "กาแฟ": "ကော်ဖီ", "คาราเมล": "ကာရာမဲလ်", "บราวน์ชูการ์": "စိမ်းလမ်း သကြား"
    },
    "🇨🇳 中文/EN": {
        "ชา": "Tea", "นม": "Milk", "เขียว": "Green", "แดง": "Red", 
        "ไต้หวัน": "Taiwan", "ปั่น": "Smoothie", "มะนาว": "Lemon", 
        "น้ำผึ้ง": "Honey", "เผือก": "Taro", "โกโก้": "Cocoa", 
        "กาแฟ": "Coffee", "คาราเมล": "Caramel", "บราวน์ชูการ์": "Brown Sugar"
    }
}

def translate_item(name_th, lang):
    if lang == "🇹🇭 ไทย":
        return name_th
    if name_th in MENU_TRANSLATIONS and lang in MENU_TRANSLATIONS[name_th]:
        return MENU_TRANSLATIONS[name_th][lang]
    result = name_th
    words = WORD_MAP.get(lang, {})
    for th_word, target_word in words.items():
        if th_word in result:
            result = result.replace(th_word, f" {target_word} ")
    return result.strip()

# ==========================================
# ⚡ ดึงเมนูแบบ Real-Time (TTL = 2 วินาที)
# ==========================================
@st.cache_data(ttl=2)
def get_menu_from_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name, cost, price FROM menu_items ORDER BY name ASC")
        rows = c.fetchall()
        conn.close()
        
        menu_dict = {}
        for r in rows:
            menu_dict[r[0]] = {"cost": float(r[1]), "price": float(r[2])}
        return menu_dict
    except Exception as e:
        return {}

if "cart" not in st.session_state:
    st.session_state.cart = []

# --- 🔘 เลือกภาษา ---
selected_lang = st.segmented_control(
    "Language",
    options=["🇹🇭 ไทย", "🇲🇲 Myanmar", "🇨🇳 中文/EN"],
    default="🇹🇭 ไทย",
    key="lang_segmented"
)

if not selected_lang:
    selected_lang = "🇹🇭 ไทย"

t = LANGUAGES[selected_lang]

# --- Header ---
st.markdown(
    f"""
    <div class="customer-header">
        <h3 style="margin: 0; font-size: 16px; font-weight: 700;">{t['header_title']}</h3>
    </div>
    """, 
    unsafe_allow_html=True
)

col_top1, col_top2 = st.columns(2)
with col_top1:
    table_number = st.text_input(t['table_label'], value=t['table_default'], key="table_no_input")
with col_top2:
    search_query = st.text_input(t['search_label'], "", placeholder=t['search_placeholder'])

current_menu = get_menu_from_db()

if not current_menu:
    st.warning("⏳ Loading...")
else:
    filtered_items = []
    for item_name_th, info in current_menu.items():
        display_name = translate_item(item_name_th, selected_lang)

        if search_query.lower() in item_name_th.lower() or search_query.lower() in display_name.lower():
            filtered_items.append((item_name_th, display_name, info))

    # ==========================================
    # 🍱 แสดงผลแบบ Card แยกกรอบชัดเจน 3 คอลัมน์
    # ==========================================
    NUM_COLS = 3
    for i in range(0, len(filtered_items), NUM_COLS):
        cols = st.columns(NUM_COLS)
        for j in range(NUM_COLS):
            if i + j < len(filtered_items):
                item_name_th, display_name, info = filtered_items[i + j]
                price = info["price"]
                cost = info["cost"]

                with cols[j]:
                    # หัวข้อการ์ดเมนู + ราคา
                    st.markdown(
                        f"""
                        <div style="text-align: center;">
                            <div style="font-weight: 700; font-size: 13px; min-height: 32px; display: flex; align-items: center; justify-content: center; line-height: 1.2; color: #2C221E;">{display_name}</div>
                            <div style="color: #8C6D58; font-weight: 800; font-size: 14px; margin-top: 2px;">{price:.0f} {t['baht']}</div>
                        </div>
                        <div class="card-divider"></div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    # ตัวเลือก + ปุ่มกด (ถูกรวบอยู่ในกรอบเดียวกัน)
                    add_pearl = st.checkbox(f"{t['add_pearl']}", key=f"p_{item_name_th}")
                    
                    if st.button(t['btn_add'], key=f"b_{item_name_th}", use_container_width=True):
                        final_price = price + (PEARL_PRICE if add_pearl else 0)
                        final_cost = cost + (PEARL_COST if add_pearl else 0)
                        
                        pearl_text = " (+ไข่มุก)" if add_pearl else ""
                        item_save_name = f"{item_name_th}{pearl_text}"

                        st.session_state.cart.append({
                            "name": item_save_name,
                            "display_name": f"{display_name}{pearl_text}",
                            "price": final_price,
                            "cost": final_cost
                        })
                        st.toast(f"{t['toast_added']}", icon="🛒")
                        time.sleep(0.2)
                        st.rerun()

# ==========================================
# 🛒 ตะกร้าสินค้า
# ==========================================
st.divider()
st.subheader(t['cart_title'])

if not st.session_state.cart:
    st.info(t['cart_empty'])
else:
    total_price = 0
    total_cost = 0

    for idx, cart_item in enumerate(st.session_state.cart):
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{cart_item.get('display_name', cart_item['name'])}**")
        c2.write(f"{cart_item['price']:.0f} {t['baht']}")
        if c3.button("❌", key=f"remove_cart_{idx}"):
            st.session_state.cart.pop(idx)
            st.rerun()
            
        total_price += cart_item['price']
        total_cost += cart_item['cost']

    st.markdown(f"#### 💰 {t['total_price']}: {total_price:.0f} {t['baht']}")

    col_order_btn, col_clear_btn = st.columns([2, 1])

    with col_order_btn:
        if st.button(t['btn_order'], type="primary", use_container_width=True):
            if not table_number.strip():
                st.error(t['err_table'])
            else:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    items_json = json.dumps(st.session_state.cart, ensure_ascii=False)
                    
                    c.execute("""
                        INSERT INTO orders (table_number, items_json, total_price, total_cost, status)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (table_number.strip(), items_json, total_price, total_cost, 'pending'))
                    
                    conn.commit()
                    conn.close()

                    st.session_state.cart = []
                    st.balloons()
                    st.success(t['success_msg'])
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error submitting order: {e}")

    with col_clear_btn:
        if st.button(t['btn_clear'], use_container_width=True):
            st.session_state.cart = []
            st.rerun()
