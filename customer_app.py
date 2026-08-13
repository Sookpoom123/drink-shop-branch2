import psycopg2
import streamlit as st
import time
import json
from datetime import datetime

# --- ตั้งค่าหน้าตาเว็บไซต์สำหรับลูกค้า (Mobile First) ---
st.set_page_config(
    page_title="Order Drink 🧋", 
    page_icon="🧋", 
    layout="centered",
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

# --- CSS ตกแต่งฝั่งลูกค้า ---
st.markdown(
    """
    <style>
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { visibility: hidden !important; }

    .stApp {
        background-color: #F8F5F2 !important;
        color: #3D342F !important;
    }

    .customer-header {
        background: linear-gradient(135deg, #8C6D58 0%, #6E5341 100%);
        padding: 18px;
        border-radius: 18px;
        color: #FFFFFF;
        text-align: center;
        box-shadow: 0 4px 15px rgba(110, 83, 65, 0.15);
        margin-bottom: 16px;
    }

    .menu-card {
        background-color: #FFFFFF;
        padding: 14px;
        border-radius: 16px;
        border: 1px solid #EADFD8;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        margin-bottom: 12px;
    }

    div.stButton > button {
        background: #8C6D58 !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: none !important;
    }

    /* ปรับแต่งปุ่มเลือกภาษา */
    div[data-testid="stRadio"] > label {
        display: none !important;
    }
    div[data-testid="stRadio"] > div {
        gap: 6px;
    }

    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

PEARL_PRICE = 4.0  # ราคาไข่มุก
PEARL_COST = 1.0

# ==========================================
# 🌐 พจนานุกรมแปลภาษา (UI Translations)
# ==========================================
LANGUAGES = {
    "🇹🇭 ไทย": {
        "header_title": "🧋 เมนูเครื่องดื่ม",
        "header_sub": "เลือกรอบสั่งและสแกนจ่ายได้ทันที",
        "table_label": "📍 ระบุหมายเลขโต๊ะ / ชื่อของคุณ:",
        "table_default": "โต๊ะ 1",
        "search_label": "🔍 ค้นหาเมนูด่วน...",
        "search_placeholder": "พิมพ์ชื่อเมนูเพื่อกรอง...",
        "select_menu": "👇 คลิกเลือกเมนูที่ต้องการ:",
        "price": "ราคา",
        "baht": "บาท",
        "add_pearl": "เพิ่มไข่มุก",
        "btn_add": "➕ สั่งเมนูนี้",
        "cart_title": "🛒 ตะกร้าสินค้าของคุณ",
        "cart_empty": "ยังไม่มีรายการในตะกร้า เลือกเมนูด้านบนได้เลยครับ",
        "total_price": "ราคารวมทั้งหมด",
        "btn_order": "🚀 ยืนยันการสั่งซื้อ (ส่งเข้าครัว)",
        "btn_clear": "🗑️ ล้างตะกร้า",
        "err_table": "⚠️ กรุณาระบุหมายเลขโต๊ะหรือชื่อก่อนสั่งซื้อ",
        "success_msg": "🎉 ส่งออเดอร์เข้าครัวเรียบร้อยแล้วครับ! กรุณารอรับเครื่องดื่ม",
        "toast_added": "เพิ่มลงตะกร้าแล้ว!"
    },
    "🇲🇲 Myanmar": {
        "header_title": "🧋 အဖျော်ယမကာ မီနူး",
        "header_sub": "စိတ်ကြိုက်မှာယူပြီး ချက်ချင်း ငွေပေးချေနိုင်ပါသည်",
        "table_label": "📍 စားပွဲနံပါတ် / သင့်အမည် ဖော်ပြပါ:",
        "table_default": "စားပွဲ ၁",
        "search_label": "🔍 မီနူးအမြန်ရှာရန်...",
        "search_placeholder": "ရှာဖွေရန် မီနူးအမည်ရိုက်ထည့်ပါ...",
        "select_menu": "👇 လိုချင်သော မီနူးကို ရွေးချယ်ပါ:",
        "price": "ဈေးနှုန်း",
        "baht": "ဘတ်",
        "add_pearl": "ကျောက်ကျောထည့်မည်",
        "btn_add": "➕ မှာယူမည်",
        "cart_title": "🛒 သင့်၏ ဈေးဝယ်ခြင်းတောင်း",
        "cart_empty": "ခြင်းတောင်းထဲတွင် မီနူးမရှိသေးပါ",
        "total_price": "စုစုပေါင်း ကျသင့်ငွေ",
        "btn_order": "🚀 မှာယူမှုကို အတည်ပြုမည်",
        "btn_clear": "🗑️ ပယ်ဖျက်မည်",
        "err_table": "⚠️ မမှာယူမီ စားပွဲနံပါတ် သို့မဟုတ် အမည် ထည့်ပါ",
        "success_msg": "🎉 မှာယူမှု အောင်မြင်ပါသည်။ ခေတ္တစောင့်ဆိုင်းပေးပါ",
        "toast_added": "ခြင်းတောင်းထဲသို့ ထည့်ပြီးပါပြီ!"
    },
    "🇨🇳 中文 / EN": {
        "header_title": "🧋 饮料菜单 Drink Menu",
        "header_sub": "Select items and place your order",
        "table_label": "📍 桌号/姓名 Table No. / Name:",
        "table_default": "Table 1",
        "search_label": "🔍 快速搜索 Search Menu...",
        "search_placeholder": "Type menu name...",
        "select_menu": "👇 选择您喜欢的饮料 Select drinks:",
        "price": "价格 Price",
        "baht": "泰铢 THB",
        "add_pearl": "加珍珠 Add Pearls",
        "btn_add": "➕ 点餐 Order",
        "cart_title": "🛒 您的购物车 Shopping Cart",
        "cart_empty": "购物车是空的 Cart is empty",
        "total_price": "总计 Total Amount",
        "btn_order": "🚀 确认下单 Confirm Order",
        "btn_clear": "🗑️ 清空 Cart Clear",
        "err_table": "⚠️ 请填写桌号或姓名 Please enter table/name",
        "success_msg": "🎉 下单成功！请稍等 Order submitted successfully!",
        "toast_added": "已加入购物车 Added to cart!"
    }
}

# Dictionary แปลชื่อเมนูภาษาไทย -> พม่า & จีน/อังกฤษ
MENU_TRANSLATIONS = {
    "ชาดำเย็น": {"🇲🇲 Myanmar": "လက်ဖက်ရည်အေး", "🇨🇳 中文 / EN": "冰红茶 Ice Black Tea"},
    "ชามะนาว": {"🇲🇲 Myanmar": "သံပုရာ လက်ဖက်ရည်", "🇨🇳 中文 / EN": "柠檬茶 Lemon Tea"},
    "ชาเขียวมะนาว": {"🇲🇲 Myanmar": "သံပုရာ လက်ဖက်စိမ်း", "🇨🇳 中文 / EN": "柠檬绿茶 Lemon Green Tea"},
    "ชาเขียวใส": {"🇲🇲 Myanmar": "လက်ဖက်စိမ်း", "🇨🇳 中文 / EN": "茉莉绿茶 Green Tea"},
    "โอเลี้ยง": {"🇲🇲 Myanmar": "ကော်ဖီနက်အေး", "🇨🇳 中文 / EN": "泰式传统黑咖啡 Oliang Coffee"},
    "โกโก้": {"🇲🇲 Myanmar": "ကိုကိုး", "🇨🇳 中文 / EN": "可可 Cocoa"},
    "โอวัลติน": {"🇲🇲 Myanmar": "အိုဗာတင်း", "🇨🇳 中文 / EN": "阿华田 Ovaltine"},
    "เนสกาแฟ": {"🇲🇲 Myanmar": "နက်စ်ကဖေး", "🇨🇳 中文 / EN": "雀巢咖啡 Nescafe"},
    "กาแฟโบราณ": {"🇲🇲 Myanmar": "ရှေးဟောင်း ကော်ဖီ", "🇨🇳 中文 / EN": "泰式古早味咖啡 Ancient Coffee"},
    "นมชมพู": {"🇲🇲 Myanmar": "နို့ဆီ ပန်းရောင်", "🇨🇳 中文 / EN": "粉红奶茶 Pink Milk"},
    "ชาไต้หวัน": {"🇲🇲 Myanmar": "ထိုင်ဝမ် လက်ဖက်ရည်", "🇨🇳 中文 / EN": "台湾奶茶 Taiwan Milk Tea"},
    "ชาเย็น(ชานมไทย)": {"🇲🇲 Myanmar": "ထိုင်း နို့လက်ဖက်ရည်", "🇨🇳 中文 / EN": "泰式奶茶 Thai Milk Tea"},
    "ชาเขียว(ชาเขียวนม)": {"🇲🇲 Myanmar": "နို့ လက်ဖက်စိမ်း", "🇨🇳 中文 / EN": "泰式绿奶茶 Thai Green Milk Tea"},
    "กล้วยนมสด": {"🇲🇲 Myanmar": "ငှက်ပျော နို့အေး", "🇨🇳 中文 / EN": "香蕉鲜奶 Banana Fresh Milk"}
}

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

# --- จัดการ Session ตะกร้าสินค้า ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- 🔘 ปุ่มเลือกภาษาแบบกดง่าย (Segmented Control) ด้านบนสุด ---
selected_lang = st.segmented_control(
    "เลือกภาษา / Language",
    options=["🇹🇭 ไทย", "🇲🇲 Myanmar", "🇨🇳 中文 / EN"],
    default="🇹🇭 ไทย",
    key="lang_segmented"
)

# กรณีไม่ได้เลือกอะไร ให้ใช้ภาษาไทยเป็นหลัก
if not selected_lang:
    selected_lang = "🇹🇭 ไทย"

t = LANGUAGES[selected_lang] # ดึงข้อความตามภาษาที่เลือก

# --- ส่วนหัวของเว็บ ---
st.markdown(
    f"""
    <div class="customer-header">
        <h2 style="margin: 0; font-size: 22px; font-weight: 700;">{t['header_title']}</h2>
        <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.90;">{t['header_sub']}</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# --- ระบุหมายเลขโต๊ะ/ชื่อลูกค้า ---
table_number = st.text_input(t['table_label'], value=t['table_default'], key="table_no_input")

# --- ดึงข้อมูลเมนูล่าสุดจาก Database ---
current_menu = get_menu_from_db()

# --- ค้นหาเมนู ---
search_query = st.text_input(t['search_label'], "", placeholder=t['search_placeholder'])

st.write(f"**{t['select_menu']}**")

if not current_menu:
    st.warning("⏳ Loading menu...")
else:
    # แสดงการ์ดเมนู
    for item_name_th, info in current_menu.items():
        # แปลชื่อเมนูตามภาษา
        display_name = item_name_th
        if selected_lang in ["🇲🇲 Myanmar", "🇨🇳 中文 / EN"]:
            translated = MENU_TRANSLATIONS.get(item_name_th, {}).get(selected_lang)
            if translated:
                display_name = f"{translated} ({item_name_th})"

        if search_query.lower() in item_name_th.lower() or search_query.lower() in display_name.lower():
            price = info["price"]
            cost = info["cost"]

            st.markdown('<div class="menu-card">', unsafe_allow_html=True)
            col_m1, col_m2 = st.columns([2, 1])

            with col_m1:
                st.markdown(f"### **{display_name}**")
                st.markdown(f"💰 **{t['price']}: {price:.0f} {t['baht']}**")

            with col_m2:
                add_pearl = st.checkbox(f"{t['add_pearl']} (+{PEARL_PRICE:.0f}฿)", key=f"pearl_{item_name_th}")
                
                if st.button(t['btn_add'], key=f"btn_add_{item_name_th}", use_container_width=True):
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
                    time.sleep(0.3)
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 🛒 ตะกร้าสินค้าและการส่งออเดอร์
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

    st.markdown(f"### 💰 **{t['total_price']}: {total_price:.0f} {t['baht']}**")

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

                    st.session_state.cart = []  # ล้างตะกร้า
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
