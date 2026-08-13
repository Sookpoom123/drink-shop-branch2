import psycopg2
import streamlit as st
import time
import json
from datetime import datetime

# --- ตั้งค่าหน้าตาเว็บไซต์สำหรับลูกค้า (Mobile First) ---
st.set_page_config(
    page_title="สั่งน้ำออนไลน์ 🧋", 
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

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

PEARL_PRICE = 4.0  # ราคาไข่มุกฝั่งลูกค้า (หรือปรับเป็น 5 บาทตามระบบคุณ)
PEARL_COST = 1.0

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

# --- ส่วนหัวของเว็บ ---
st.markdown(
    """
    <div class="customer-header">
        <h2 style="margin: 0; font-size: 22px; font-weight: 700;">🧋 เมนูเครื่องดื่ม</h2>
        <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.90;">เลือกรอบสั่งและสแกนจ่ายได้ทันที</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# --- ระบุหมายเลขโต๊ะ/ชื่อลูกค้า ---
table_number = st.text_input("📍 ระบุหมายเลขโต๊ะ / ชื่อของคุณ:", value="โต๊ะ 1", key="table_no_input")

# --- ดึงข้อมูลเมนูล่าสุดจาก Database ---
current_menu = get_menu_from_db()

# --- ค้นหาเมนู ---
search_query = st.text_input("🔍 ค้นหาเมนูด่วน...", "", placeholder="พิมพ์ชื่อเมนูเพื่อกรอง...")

st.write("👇 **คลิกเลือกเมนูที่ต้องการ:**")

if not current_menu:
    st.warning("⏳ กำลังโหลดเมนู หรือยังไม่มีรายการเมนูในระบบ...")
else:
    # แสดงการ์ดเมนู
    for item_name, info in current_menu.items():
        if search_query.lower() in item_name.lower():
            price = info["price"]
            cost = info["cost"]

            st.markdown('<div class="menu-card">', unsafe_allow_html=True)
            col_m1, col_m2 = st.columns([2, 1])

            with col_m1:
                st.markdown(f"### **{item_name}**")
                st.markdown(f"💰 **ราคา: {price:.0f} บาท**")

            with col_m2:
                add_pearl = st.checkbox(f"เพิ่มไข่มุก (+{PEARL_PRICE:.0f}฿)", key=f"pearl_{item_name}")
                
                if st.button("➕ สั่งเมนูนี้", key=f"btn_add_{item_name}", use_container_width=True):
                    final_price = price + (PEARL_PRICE if add_pearl else 0)
                    final_cost = cost + (PEARL_COST if add_pearl else 0)
                    item_display_name = f"{item_name} (+ไข่มุก)" if add_pearl else item_name

                    st.session_state.cart.append({
                        "name": item_display_name,
                        "price": final_price,
                        "cost": final_cost
                    })
                    st.toast(f"เพิ่ม {item_display_name} ลงตะกร้าแล้ว!", icon="🛒")
                    time.sleep(0.3)
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 🛒 ตะกร้าสินค้าและการส่งออเดอร์
# ==========================================
st.divider()
st.subheader("🛒 ตะกร้าสินค้าของคุณ")

if not st.session_state.cart:
    st.info("ยังไม่มีรายการในตะกร้า เลือกเมนูด้านบนได้เลยครับ")
else:
    total_price = 0
    total_cost = 0

    for idx, cart_item in enumerate(st.session_state.cart):
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{cart_item['name']}**")
        c2.write(f"{cart_item['price']:.0f} บาท")
        if c3.button("❌", key=f"remove_cart_{idx}"):
            st.session_state.cart.pop(idx)
            st.rerun()
            
        total_price += cart_item['price']
        total_cost += cart_item['cost']

    st.markdown(f"### 💰 **ราคารวมทั้งหมด: {total_price:.0f} บาท**")

    col_order_btn, col_clear_btn = st.columns([2, 1])

    with col_order_btn:
        if st.button("🚀 ยืนยันการสั่งซื้อ (ส่งเข้าครัว)", type="primary", use_container_width=True):
            if not table_number.strip():
                st.error("⚠️ กรุณาระบุหมายเลขโต๊ะหรือชื่อก่อนสั่งซื้อ")
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
                    st.success("🎉 ส่งออเดอร์เข้าครัวเรียบร้อยแล้วครับ! กรุณารอรับเครื่องดื่ม")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการส่งออเดอร์: {e}")

    with col_clear_btn:
        if st.button("🗑️ ล้างตะกร้า", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
