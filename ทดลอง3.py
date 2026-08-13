import base64
import hashlib
import psycopg2
import streamlit as st
import time
import json
from datetime import datetime, date
import pandas as pd

# --- ตั้งค่าหน้าตาเว็บไซต์รองรับ Mobile Screen ---
st.set_page_config(
    page_title="ร้านน้ำสร้างตัว 🧋 (หลังบ้าน/POS)", 
    page_icon="🧋", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- เชื่อมต่อฐานข้อมูล (ปรับให้รองรับ Secrets หลายรูปแบบเพื่อป้องกัน KeyError) ---
def get_db_connection():
    db_url = None
    if "postgres" in st.secrets and "url" in st.secrets["postgres"]:
        db_url = st.secrets["postgres"]["url"]
    elif "postgres_url" in st.secrets:
        db_url = st.secrets["postgres_url"]
    elif "DATABASE_URL" in st.secrets:
        db_url = st.secrets["DATABASE_URL"]
    
    if not db_url:
        st.error("❌ ไม่พบการตั้งค่า Database URL ใน Secrets กรุณาตรวจสอบการตั้งค่า Secrets บน Streamlit Cloud")
        st.stop()
        
    return psycopg2.connect(db_url)

# ==========================================
# 🎨 CSS Optimization
# ==========================================
@st.cache_resource
def load_app_styles():
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

        .mobile-header {
            background: linear-gradient(135deg, #8C6D58 0%, #6E5341 100%);
            padding: 20px;
            border-radius: 18px;
            color: #FFFFFF;
            text-align: center;
            box-shadow: 0 4px 15px rgba(110, 83, 65, 0.15);
            margin-bottom: 16px;
        }

        .pos-card {
            background-color: #FFFFFF;
            padding: 12px;
            border-radius: 16px;
            border: 1px solid #EADFD8;
            box-shadow: 0 2px 10px rgba(0,0,0,0.02);
            margin-bottom: 16px;
        }

        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
        }

        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 0 !important;
            flex: 1 1 0% !important;
        }

        div.stButton > button, div.stFormSubmitButton > button {
            background: #8C6D58 !important;
            color: #FFFFFF !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            height: 44px !important;
            border: none !important;
            box-shadow: 0 2px 6px rgba(140, 109, 88, 0.2) !important;
            width: 100% !important;
            transition: all 0.2s ease-in-out;
        }

        div.stButton > button:hover {
            background: #755946 !important;
        }

        div.stButton > button:active {
            transform: scale(0.98);
        }

        div[data-testid="stColumn"] div.stButton > button {
            height: 58px !important;
            padding: 2px 2px !important;
            background: #FFFFFF !important;
            color: #4A3B32 !important;
            border: 1.5px solid #E5D7CE !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03) !important;
            white-space: pre-line !important;
            line-height: 1.15 !important;
            font-size: 11px !important;
            font-weight: 600 !important;
        }

        div[data-testid="stColumn"] div.stButton > button:hover {
            background: #F4ECE7 !important;
            border-color: #8C6D58 !important;
        }

        div[data-baseweb="input"] {
            border-radius: 10px !important;
            border-color: #D3C4B9 !important;
        }

        button[data-baseweb="tab"] {
            font-weight: 600 !important;
            color: #8C7B70 !important;
        }

        button[aria-selected="true"] {
            color: #6E5341 !important;
            border-bottom-color: #8C6D58 !important;
        }

        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.4rem !important;
            padding-right: 0.4rem !important;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

load_app_styles()

ADMIN_SECRET_KEY = "3475"
PEARL_PRICE = 5.0
PEARL_COST = 1.0

DEFAULT_MENU = {
    "ชาดำเย็น": {"cost": 6.61, "price": 19},
    "ชามะนาว": {"cost": 7.65, "price": 19},
    "ชาเขียวมะนาว": {"cost": 8.45, "price": 19},
    "ชาเขียวใส": {"cost": 7.41, "price": 19},
    "โอเลี้ยง": {"cost": 6.07, "price": 19},
    "โกโก้": {"cost": 13.11, "price": 25},
    "โอวัลติน": {"cost": 10.85, "price": 25},
    "เนสกาแฟ": {"cost": 15.63, "price": 30},
    "กาแฟโบราณ": {"cost": 10.51, "price": 25},
    "นมชมพู": {"cost": 10.87, "price": 25},
    "ผลไม้โซดา": {"cost": 10.47, "price": 19},
    "น้ำแดงโซดา": {"cost": 10.88, "price": 19},
    "แดงมะนาวโซดา": {"cost": 11.92, "price": 25},
    "มะนาวโซดา": {"cost": 9.85, "price": 19},
    "นมสดบราวซูการ์": {"cost": 11.20, "price": 25},
    "นมสดสีขาว": {"cost": 12.07, "price": 25},
    "นมสดคาราเมล": {"cost": 14.55, "price": 30},
    "นมสดวนิลา": {"cost": 14.55, "price": 30},
    "นมสดน้ำผึ้ง": {"cost": 13.67, "price": 25},
    "โยเกิร์ตผลไม้": {"cost": 11.36, "price": 25},
    "มันม่วงนมสด": {"cost": 13.76, "price": 25},
    "มะพร้าวนมสด": {"cost": 12.76, "price": 25},
    "สตรอเบอร์รี่นมสด": {"cost": 11.49, "price": 25},
    "เผือกนมสด": {"cost": 11.49, "price": 25},
    "กล้วยนมสด": {"cost": 11.49, "price": 25},
    "แคนตาลูปนมสด": {"cost": 11.49, "price": 25},
    "ช็อคโกแลตนมสด": {"cost": 14.64, "price": 25},
    "ชาแดงปั่น": {"cost": 14.72, "price": 35},
    "ชาเขียวปั่น": {"cost": 15.73, "price": 35},
    "ชาไต้หวันปั่น": {"cost": 13.04, "price": 35},
    "ชานมโกโก้ปั่น": {"cost": 15.07, "price": 35},
    "ชานมกาแฟ": {"cost": 16.33, "price": 35},
    "ชานมโอวัลติน": {"cost": 13.94, "price": 35},
    "ชานมน้ำผึ้ง": {"cost": 17.58, "price": 35},
    "ชานมลิ้นจี่": {"cost": 15.69, "price": 35},
    "ชานมแอปเปิ้ล": {"cost": 15.69, "price": 35},
    "ชาแชมเมล่อน(แคนตาลูป)": {"cost": 15.69, "price": 35},
    "ชานมสตรอเบอร์รี่": {"cost": 15.69, "price": 35},
    "โกโก้ปั่น": {"cost": 18.16, "price": 35},
    "เนสกาแฟปั่น": {"cost": 21.94, "price": 45},
    "โอวัลตินปั่น": {"cost": 14.77, "price": 35},
    "นมชมพูปั่น": {"cost": 14.06, "price": 35},
    "นมสดปั่น": {"cost": 18.35, "price": 35},
    "วนิลานมสดปั่น": {"cost": 25.19, "price": 45},
    "คาราเมลนมสดปั่น": {"cost": 25.19, "price": 45},
    "นมสดน้ำผึ้งปั่น": {"cost": 23.43, "price": 45},
    "นมสดบราวซูการ์ปั่น": {"cost": 20.58, "price": 45},
    "ชาไต้หวันบราวซูการ์ปั่น": {"cost": 14.88, "price": 45},
    "มัทฉะนมสดปั่น": {"cost": 30.66, "price": 55},
    "มะพร้าวนมสดปั่น": {"cost": 17.17, "price": 35},
    "มันม่วงนมสดปั่น": {"cost": 18.13, "price": 45},
    "ผงสตรอเบอร์รี่": {"cost": 14.94, "price": 35},
    "ผงแคนตาลูป": {"cost": 14.77, "price": 35},
    "ผงกล้วย": {"cost": 14.77, "price": 35},
    "ผงเผือก": {"cost": 15.25, "price": 35},
    "ชาไต้หวัน": {"cost": 11.12, "price": 19},
    "ชานมผลไม้": {"cost": 11.89, "price": 25},
    "ชานมโกโก้": {"cost": 12.13, "price": 25},
    "ชานมคาราเมล": {"cost": 14.03, "price": 30},
    "ชานมวนิลา": {"cost": 14.03, "price": 30},
    "ชานมไต้หวันบราวซูการ์": {"cost": 11.96, "price": 25},
    "ชานมเผือก": {"cost": 13.20, "price": 25},
    "ชาผลไม้ใส": {"cost": 8.03, "price": 19},
    "ชาเย็น(ชานมไทย)": {"cost": 11.58, "price": 25},
    "ชาเขียว(ชาเขียวนม)": {"cost": 12.38, "price": 25},
    "ชาเขียวน้ำผึ้งมะนาว": {"cost": 12.11, "price": 25},
    "ชาแดงน้ำผึ้งมะนาว": {"cost": 11.31, "price": 25},
    "น้ำผึ้งมะนาว": {"cost": 10.07, "price": 19},
    "ชาลูกบ๊วย": {"cost": 9.03, "price": 24},
    "น้ำลูกบ๊วย": {"cost": 6.95, "price": 24},
    "น้ำลูกบ๊วยโซดา": {"cost": 11.94, "price": 24},
    "น้ำผึ้งมะนาวลูกบ๊วย": {"cost": 12.79, "price": 24},
    "น้ำแดงลูกบ๊วย": {"cost": 9.18, "price": 24},
    "น้ำแดงโซดาลูกบ๊วย": {"cost": 14.01, "price": 24},
    "น้ำลูกบ๊วยปั่น": {"cost": 9.70, "price": 29},
}

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. ตาราง sales
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            sale_date TEXT,
            item_name TEXT,
            qty INTEGER,
            total_price REAL,
            total_cost REAL,
            total_profit REAL,
            seller_name TEXT,
            payment_method TEXT
        )
    ''')
    
    # 2. ตาราง users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT DEFAULT 'user',
            last_active TEXT,
            profile_img TEXT
        )
    ''')
    
    # 3. ตาราง orders (สำหรับแอปฝั่งลูกค้า)
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            table_number VARCHAR(50),
            items_json TEXT,
            total_price NUMERIC(10, 2),
            total_cost NUMERIC(10, 2),
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. ตาราง menu_items
    c.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            name TEXT PRIMARY KEY,
            cost REAL,
            price REAL
        )
    ''')
    
    c.execute("SELECT COUNT(*) FROM menu_items")
    if c.fetchone()[0] == 0:
        for name, info in DEFAULT_MENU.items():
            c.execute("INSERT INTO menu_items (name, cost, price) VALUES (%s, %s, %s) ON CONFLICT (name) DO NOTHING",
                        (name, info['cost'], info['price']))
            
    conn.commit()
    conn.close()

def update_user_activity(username):
    if username:
        conn = get_db_connection()
        c = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET last_active = %s WHERE username = %s", (now_str, username))
        conn.commit()
        conn.close()

def update_user_profile_img(username, img_bytes):
    encoded_img = base64.b64encode(img_bytes).decode('utf-8')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET profile_img = %s WHERE username = %s", (encoded_img, username))
    conn.commit()
    conn.close()

def get_user_profile_img(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT profile_img FROM users WHERE username = %s", (username,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return None

@st.cache_data(ttl=10)
def get_menu_from_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, cost, price FROM menu_items ORDER BY name ASC")
    rows = c.fetchall()
    conn.close()
    menu_dict = {}
    for r in rows:
        menu_dict[r[0]] = {"cost": float(r[1]), "price": float(r[2])}
    return menu_dict

def save_menu_item_db(name, cost, price):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO menu_items (name, cost, price) 
        VALUES (%s, %s, %s)
        ON CONFLICT (name) DO UPDATE SET cost = EXCLUDED.cost, price = EXCLUDED.price
    """, (name, cost, price))
    conn.commit()
    conn.close()
    st.cache_data.clear()

def delete_menu_item_db(name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM menu_items WHERE name = %s", (name,))
    conn.commit()
    conn.close()
    st.cache_data.clear()

def add_user(username, password, role='user'):
    conn = get_db_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute('INSERT INTO users (username, password, role, last_active) VALUES (%s, %s, %s, %s)', 
                    (username, make_hashes(password), role, now_str))
        conn.commit()
        conn.close()
        return True
    except psycopg2.IntegrityError:
        conn.close()
        return False

def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username, role FROM users WHERE username = %s AND password = %s',
                (username, make_hashes(password)))
    data = c.fetchone()
    conn.close()
    return data

def get_user_role(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE username = %s', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else "user"

def get_all_users_with_status():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username, role, last_active FROM users')
    rows = c.fetchall()
    conn.close()

    users_status = []
    now = datetime.now()

    for username, role, last_active in rows:
        is_online = False
        if last_active:
            try:
                last_time = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
                if (now - last_time).total_seconds() < 300:
                    is_online = True
            except ValueError:
                pass
        
        status_str = "🟢 Online" if is_online else "⚪ Offline"
        users_status.append({
            "ผู้ใช้งาน": username,
            "สิทธิ์": role.upper() if role else "USER",
            "สถานะ": status_str,
            "ใช้งานล่าสุด": last_active if last_active else "ไม่ระบุ"
        })
    return users_status

def delete_user(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username = %s', (username,))
    conn.commit()
    conn.close()

def set_user_offline(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET last_active = NULL WHERE username = %s", (username,))
    conn.commit()
    conn.close()

def add_sale(sale_date, item_name, qty, total_price, total_cost, total_profit, seller_name, payment_method):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO sales (sale_date, item_name, qty, total_price, total_cost, total_profit, seller_name, payment_method)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (str(sale_date), item_name, qty, total_price, total_cost, total_profit, seller_name, payment_method))
    conn.commit()
    conn.close()
    st.cache_data.clear()

@st.cache_data(ttl=5)
def get_sales():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()
    return df

def delete_sale_by_id(record_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sales WHERE id = %s", (record_id,))
    conn.commit()
    conn.close()
    st.cache_data.clear()

# ==========================================
# 🔔 POP-UP DIALOGS
# ==========================================
@st.dialog("👤 ตั้งค่ารูปโปรไฟล์")
def profile_settings_dialog():
    st.write(f"ผู้ใช้งาน: **{st.session_state.username}**")

    current_img = get_user_profile_img(st.session_state.username)
    if current_img:
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 12px;">
                <img src="data:image/png;base64,{current_img}" style="width: 110px; height: 110px; border-radius: 50%; object-fit: cover; border: 3px solid #8C6D58; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            </div>
            """, 
            unsafe_allow_html=True
        )

    uploaded_file = st.file_uploader("เลือกรูปภาพโปรไฟล์ใหม่ (PNG, JPG)", type=["png", "jpg", "jpeg"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 บันทึกรูป", use_container_width=True, key="btn_save_profile"):
            if uploaded_file is not None:
                img_bytes = uploaded_file.read()
                update_user_profile_img(st.session_state.username, img_bytes)
                st.success("อัปเดตรูปโปรไฟล์เรียบร้อย!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("กรุณาเลือกไฟล์รูปภาพก่อน")
    with col2:
        if st.button("❌ ปิด", use_container_width=True, key="btn_close_profile"):
            st.rerun()

@st.dialog("⚠️ ยืนยันการลบรายการขาย")
def confirm_delete_dialog(item_id, item_name, qty):
    st.write(f"คุณต้องการลบรายการ **{item_name}** ({qty} แก้ว) ใช่หรือไม่?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("✅ ยืนยันลบ", use_container_width=True, key="btn_confirm_del_sale"):
            delete_sale_by_id(item_id)
            st.success("ลบรายการเรียบร้อย!")
            time.sleep(0.5)
            st.rerun()
    with col_cancel:
        if st.button("❌ ยกเลิก", use_container_width=True, key="btn_cancel_del_sale"):
            st.rerun()

@st.dialog("⚠️ ยืนยันการลบเมนู")
def confirm_delete_menu_dialog(menu_name):
    st.write(f"คุณต้องการลบเมนู **{menu_name}** ออกจากระบบใช่หรือไม่?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("✅ ยืนยันลบ", use_container_width=True, key="btn_confirm_del_menu"):
            delete_menu_item_db(menu_name)
            st.success(f"ลบเมนู '{menu_name}' เรียบร้อย!")
            time.sleep(0.5)
            st.rerun()
    with col_cancel:
        if st.button("❌ ยกเลิก", use_container_width=True, key="btn_cancel_del_menu"):
            st.rerun()

@st.dialog("⚠️ ยืนยันการลบบัญชีสมาชิก")
def confirm_delete_user_dialog(username):
    st.write(f"คุณต้องการลบบัญชีผู้ใช้ **{username}** ออกจากระบบใช่หรือไม่?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("✅ ยืนยันลบ", use_container_width=True, key="btn_confirm_del_user"):
            delete_user(username)
            st.success(f"ลบบัญชี '{username}' สำเร็จ!")
            time.sleep(0.5)
            st.rerun()
    with col_cancel:
        if st.button("❌ ยกเลิก", use_container_width=True, key="btn_cancel_del_user"):
            st.rerun()

# --- ส่วนของการแสดงออเดอร์เด้งเข้าครัวแบบ Auto-refresh ทุกๆ 5 วินาที ---
@st.fragment(run_every="5s")
def render_kitchen_orders():
    st.markdown('<div class="pos-card" style="border: 2px solid #8C6D58;">', unsafe_allow_html=True)
    st.subheader("🔔 ออเดอร์เด้งเข้าครัว (สั่งจากลูกค้า)")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, table_number, items_json, total_price, total_cost, created_at FROM orders WHERE status = 'pending' ORDER BY id ASC")
        pending_orders = cur.fetchall()

        if not pending_orders:
            st.info("🟢 ยังไม่มีออเดอร์ใหม่เข้ามา...")
        else:
            st.warning(f"⚠️ มีออเดอร์ค้างทำอยู่ **{len(pending_orders)}** รายการ")
            for order in pending_orders:
                order_id, table_no, items_json, o_total_price, o_total_cost, created_at = order
                items = json.loads(items_json)
                
                with st.container(border=True):
                    col_o1, col_o2 = st.columns([3, 1])
                    with col_o1:
                        st.markdown(f"### 📌 **{table_no}** (ออเดอร์ #{order_id})")
                        item_summary_text = []
                        for item in items:
                            st.write(f"- **{item['name']}** ({item['price']} บาท)")
                            item_summary_text.append(f"{item['name']}")
                        
                        st.write(f"💰 **ราคารวม: {o_total_price} บาท**")

                    with col_o2:
                        if st.button("✅ ทำเสร็จแล้ว", key=f"done_order_{order_id}", type="primary", use_container_width=True):
                            cur.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order_id,))
                            
                            combined_item_names = ", ".join(item_summary_text)
                            total_profit = float(o_total_price) - float(o_total_cost)
                            
                            cur.execute('''
                                INSERT INTO sales (sale_date, item_name, qty, total_price, total_cost, total_profit, seller_name, payment_method)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ''', (str(date.today()), f"📱 {table_no}: {combined_item_names}", len(items), o_total_price, o_total_cost, total_profit, "ลูกค้าสั่งเอง", "📱 QR/Scan"))
                            
                            conn.commit()
                            st.success("ทำเสร็จแล้วและบันทึกลงยอดขายเรียบร้อย!")
                            time.sleep(0.5)
                            st.rerun()

        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดออเดอร์: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# --- เรียกใช้งานระบบฐานข้อมูล ---
init_db()

# ==========================================
# 🔗 ระบบจัดการ Session
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = "user"
if "login_date" not in st.session_state:
    st.session_state.login_date = ""

today_str = str(date.today())

if st.session_state.logged_in and st.session_state.login_date != today_str:
    set_user_offline(st.session_state.username)
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

if not st.session_state.logged_in and "user" in st.query_params and "login_date" in st.query_params:
    saved_user = st.query_params["user"]
    saved_date = st.query_params["login_date"]

    if saved_date == today_str:
        st.session_state.logged_in = True
        st.session_state.username = saved_user
        st.session_state.role = get_user_role(saved_user)
        st.session_state.login_date = saved_date
    else:
        st.query_params.clear()

if st.session_state.logged_in:
    update_user_activity(st.session_state.username)

current_menu = get_menu_from_db()

# ==========================================
# 1. หน้าเข้าสู่ระบบ / สมัครสมาชิก
# ==========================================
if not st.session_state.logged_in:

    st.markdown(
        """
        <div class="mobile-header">
            <h2 style="margin: 0; font-size: 24px; font-weight: 700;">🧋 ร้านน้ำสร้างตัว</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.90;">ระบบบันทึกการขาย Mobile POS & ครัว</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    auth_tab1, auth_tab2 = st.tabs(["🔑 เข้าสู่ระบบ", "📝 สมัครสมาชิก"])

    with auth_tab1:
        st.write("")
        login_user_input = st.text_input("👤 ชื่อผู้ใช้งาน", key="login_user")
        login_pass_input = st.text_input("🔒 รหัสผ่าน", type="password", key="login_pass")
        st.write("")
        
        if st.button("🚀 เข้าสู่ระบบ", use_container_width=True):
            user_data = login_user(login_user_input.strip(), login_pass_input.strip())
            if user_data:
                st.session_state.logged_in = True
                st.session_state.username = user_data[0]
                st.session_state.role = user_data[1] if user_data[1] else "user"
                st.session_state.login_date = str(date.today())
                
                update_user_activity(user_data[0])
                
                st.query_params["user"] = user_data[0]
                st.query_params["login_date"] = str(date.today())
                
                st.success(f"🎉 ต้อนรับคุณ {st.session_state.username}!")
                time.sleep(0.3)
                st.rerun()
            else:
                st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")

    with auth_tab2:
        st.write("")
        role_choice = st.radio(
            "เลือกสิทธิ์การใช้งาน:", 
            ["👤 พนักงาน (User)", "👑 ผู้ดูแล (Admin)"], 
            key="reg_role_choice",
            horizontal=True
        )

        with st.form("register_form"):
            reg_user_input = st.text_input("👤 ตั้งชื่อผู้ใช้งาน", key="reg_user")
            reg_pass_input = st.text_input("🔒 ตั้งรหัสผ่าน", type="password", key="reg_pass")
            reg_confirm_pass = st.text_input("🔁 ยืนยันรหัสผ่าน", type="password", key="reg_confirm")
            
            secret_code_input = ""
            if role_choice == "👑 ผู้ดูแล (Admin)":
                secret_code_input = st.text_input("🔑 รหัสลับแต่งตั้ง Admin", type="password", key="reg_secret")

            st.write("")
            submit_reg = st.form_submit_button("✨ สมัครสมาชิก", use_container_width=True)

        if submit_reg:
            username_clean = reg_user_input.strip()
            password_clean = reg_pass_input.strip()

            if not username_clean or not password_clean:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
            elif password_clean != reg_confirm_pass.strip():
                st.error("❌ รหัสผ่านไม่ตรงกัน")
            elif role_choice == "👑 ผู้ดูแล (Admin)" and secret_code_input.strip() != ADMIN_SECRET_KEY:
                st.error("❌ รหัสลับ Admin ไม่ถูกต้อง!")
            else:
                assigned_role = 'admin' if role_choice == "👑 ผู้ดูแล (Admin)" else 'user'
                if add_user(username_clean, password_clean, role=assigned_role):
                    st.success(f"🎉 สมัครสำเร็จ! สิทธิ์: '{assigned_role.upper()}' ล็อกอินได้เลย")
                else:
                    st.error("❌ ชื่อผู้ใช้งานนี้มีในระบบแล้ว")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. หน้าขายสินค้า Mobile Cashier POS + แสดงออเดอร์จากฝั่งลูกค้า
# ==========================================
else:
    user_img = get_user_profile_img(st.session_state.username)

    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        if user_img:
            avatar_html = f'<img src="data:image/png;base64,{user_img}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #8C6D58; vertical-align: middle; margin-right: 8px;">'
        else:
            avatar_html = '<span style="font-size: 24px; vertical-align: middle; margin-right: 6px;">👤</span>'
        
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; padding-top: 2px;">
                {avatar_html}
                <span style="font-size: 16px; font-weight: 600;">{st.session_state.username}</span>
                <span style="background-color: #EADFD8; color: #6E5341; font-size: 11px; padding: 2px 6px; border-radius: 6px; margin-left: 6px; font-weight: bold;">{st.session_state.role.upper()}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        if st.button("🖼️ เปลี่ยนรูปโปรไฟล์", key="btn_open_profile_dialog"):
            profile_settings_dialog()

    with col_u2:
        st.write("")
        if st.button("🚪 ออก", key="main_logout"):
            set_user_offline(st.session_state.username)
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    # --- ส่วนที่ 0: 🔔 รายการออเดอร์เด้งเข้าครัวจากฝั่งลูกค้า (Auto-refresh) ---
    render_kitchen_orders()

    # --- ส่วนที่ 1: ตารางราคาเมนู (แก้ไขราคาได้ทันที) ---
    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    st.subheader("📋 ตารางราคาเมนู (เชื่อมหน้าร้าน/ลูกค้า)")

    if st.session_state.role == "admin":
        st.caption("💡 **สำหรับ Admin:** คุณสามารถดับเบิ้ลคลิกแก้ไขช่อง **'ต้นทุน'** หรือ **'ราคาขาย'** ในตารางแล้วกดปุ่มบันทึกได้เลย (ลูกค้าจะเห็นราคาใหม่ทันที)")
    else:
        st.caption("ℹ️ ตารางดูราคาหน้าร้าน (การแก้ไขราคาต้องใช้สิทธิ์ Admin)")

    search_top_table = st.text_input("🔍 ค้นหาราคา...", "", key="m_search_top_table", placeholder="พิมพ์ชื่อเมนูที่นี่...")

    if current_menu:
        top_menu_list = []
        for item, info in current_menu.items():
            if search_top_table.lower() in item.lower():
                top_menu_list.append({
                    "เมนู": item,
                    "ต้นทุน": float(info['cost']),
                    "ราคาขาย": float(info['price']),
                    "กำไร": float(round(info['price'] - info['cost'], 2)),
                    "+มุก": float(info['price'] + PEARL_PRICE),
                    "กำไรมุก": float(round((info['price'] + PEARL_PRICE) - (info['cost'] + PEARL_COST), 2))
                })
        
        df_menu_view = pd.DataFrame(top_menu_list)

        disabled_cols = ["เมนู", "กำไร", "+มุก", "กำไรมุก"]
        if st.session_state.role != "admin":
            disabled_cols = True

        edited_df = st.data_editor(
            df_menu_view,
            use_container_width=True,
            height=260,
            disabled=disabled_cols,
            column_config={
                "ต้นทุน": st.column_config.NumberColumn("ต้นทุน (บ.)", format="%.2f"),
                "ราคาขาย": st.column_config.NumberColumn("ราคาขาย (บ.)", format="%.0f"),
                "กำไร": st.column_config.NumberColumn("กำไร (บ.)", format="%.1f"),
                "+มุก": st.column_config.NumberColumn("+มุก (บ.)", format="%.0f"),
                "กำไรมุก": st.column_config.NumberColumn("กำไรมุก (บ.)", format="%.1f")
            },
            hide_index=True,
            key="direct_menu_editor"
        )

        if st.session_state.role == "admin":
            if st.button("💾 บันทึกการแก้ไขราคาในตาราง", use_container_width=True, key="btn_save_inline_table"):
                updated_count = 0
                for _, row in edited_df.iterrows():
                    m_name = row["เมนู"]
                    new_c = row["ต้นทุน"]
                    new_p = row["ราคาขาย"]
                    
                    old_c = current_menu[m_name]["cost"]
                    old_p = current_menu[m_name]["price"]
                    
                    if new_c != old_c or new_p != old_p:
                        save_menu_item_db(m_name, new_c, new_p)
                        updated_count += 1
                
                if updated_count > 0:
                    st.success(f"🎉 อัปเดตราคาเรียบร้อย {updated_count} รายการ! (ฝั่งลูกค้าจะอัปเดตทันที)")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.info("ไม่มีรายการที่เปลี่ยนแปลง")

    st.markdown('</div>', unsafe_allow_html=True)

    # --- ส่วนที่ 2: บันทึกการขาย (ปุ่มกดการ์ดเมนูหน้าร้าน) ---
    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    st.subheader("🛒 บันทึกรายการขาย (หน้าร้าน)")

    selected_date = st.date_input("📅 วันที่รายการ", value=date.today())

    if current_menu:
        search_sale_term = st.text_input("🔍 ค้นหาเมนูด่วน...", placeholder="พิมพ์ชื่อเมนูเพื่อกรอง...", key="search_sale_input")
        
        filtered_menu = {k: v for k, v in current_menu.items() if search_sale_term.strip().lower() in k.lower()}

        if "selected_menu_item" not in st.session_state or st.session_state.selected_menu_item not in current_menu:
            st.session_state.selected_menu_item = list(current_menu.keys())[0]

        st.caption("👇 **คลิกเลือกเมนูที่ต้องการ:**")

        if filtered_menu:
            menu_items_list = list(filtered_menu.items())
            for i in range(0, len(menu_items_list), 3):
                chunk = menu_items_list[i:i+3]
                menu_cols = st.columns(3)
                for idx, (m_name, m_info) in enumerate(chunk):
                    card_label = f"🧋 {m_name}\n🏷️ {m_info['price']:.0f}บ."
                    if menu_cols[idx].button(card_label, key=f"btn_card_{m_name}", use_container_width=True):
                        st.session_state.selected_menu_item = m_name
        else:
            st.warning("ไม่พบเมนูที่ค้นหา")

        selected_item = st.session_state.selected_menu_item
        
        st.markdown(
            f"""
            <div style="background-color: #EADFD8; padding: 10px; border-radius: 10px; margin: 12px 0 6px 0; text-align: center;">
                <span style="font-size: 15px; color: #6E5341; font-weight: 600;">📌 เมนูที่เลือก: <b>{selected_item}</b></span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        if selected_item in current_menu:
            base_cost = current_menu[selected_item]["cost"]
            base_price = current_menu[selected_item]["price"]

            c_opt1, c_opt2 = st.columns(2)
            with c_opt1:
                add_pearl = st.checkbox("🧋 +ไข่มุก (+5บ.)")
            with c_opt2:
                payment_method = st.radio("ชำระเงิน", ["💵 เงินสด", "📱 QR"], horizontal=True)

            unit_price = base_price + (PEARL_PRICE if add_pearl else 0)
            unit_cost = base_cost + (PEARL_COST if add_pearl else 0)
            unit_profit = unit_price - unit_cost

            # --- ส่วนจัดการจำนวนแก้ว ---
            st.write("🔢 **จำนวนแก้ว:**")
            
            def update_qty(change):
                current_v = st.session_state.get("mobile_qty", 1)
                st.session_state.mobile_qty = max(1, current_v + change)

            q_col1, q_col2, q_col3 = st.columns([1, 2, 1])
            with q_col1:
                st.button("➖", key="btn_minus", on_click=update_qty, args=(-1,), use_container_width=True)
            with q_col2:
                st.number_input(
                    "จำนวนแก้ว", 
                    min_value=1, 
                    max_value=999, 
                    value=1,
                    key="mobile_qty", 
                    label_visibility="collapsed"
                )
            with q_col3:
                st.button("➕", key="btn_plus", on_click=update_qty, args=(1,), use_container_width=True)

            qty = st.session_state.get("mobile_qty", 1)
            total_price = unit_price * qty
            total_cost = unit_cost * qty
            total_profit = unit_profit * qty

            st.markdown(
                f"""
                <div style="background-color: #F3ECE7; padding: 12px; border-radius: 12px; margin: 12px 0; text-align: center; border: 1px solid #EADFD8;">
                    <span style="font-size: 18px; color: #6E5341; font-weight: 600;">💰 รวม: <b>{total_price:,.0f} บาท</b></span>
                    <br><small style="color: #8C6D58;">(กำไรสุทธิ {total_profit:,.2f} บาท)</small>
                </div>
                """, 
                unsafe_allow_html=True
            )

            if st.button("✅ บันทึกการขาย", use_container_width=True):
                item_name = f"{selected_item} (+ไข่มุก)" if add_pearl else selected_item
                add_sale(selected_date, item_name, qty, total_price, round(total_cost, 2), round(total_profit, 2), st.session_state.username, payment_method)
                st.session_state.last_sale_msg = f"🎉 บันทึกสำเร็จ: {item_name} ({qty} แก้ว) รวม {total_price:.0f} บาท"
                
                if "mobile_qty" in st.session_state:
                    del st.session_state["mobile_qty"]
                    
                st.rerun()

    if "last_sale_msg" in st.session_state:
        st.success(st.session_state.last_sale_msg)

    st.markdown('</div>', unsafe_allow_html=True)

    # --- ส่วนที่ 3: สรุปยอดขายเรียลไทม์ (วันนี้ & เดือนนี้) ---
    df_all = get_sales()

    if not df_all.empty and 'sale_date' in df_all.columns:
        df_all['date_dt'] = pd.to_datetime(df_all['sale_date'], errors='coerce')
        
        today_str = datetime.today().strftime('%Y-%m-%d')
        current_month = datetime.today().month
        current_year = datetime.today().year

        df_today = df_all[df_all['sale_date'] == today_str]
        today_sales = df_today['total_price'].sum() if not df_today.empty else 0
        today_cups = df_today['qty'].sum() if not df_today.empty else 0

        df_month = df_all[(df_all['date_dt'].dt.month == current_month) & (df_all['date_dt'].dt.year == current_year)]
        month_sales = df_month['total_price'].sum() if not df_month.empty else 0
        month_cups = df_month['qty'].sum() if not df_month.empty else 0
    else:
        today_sales, today_cups, month_sales, month_cups = 0, 0, 0, 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="📅 ยอดขายวันนี้", value=f"{today_sales:,.0f} บาท", delta=f"{today_cups:,} แก้ว")
    with col2:
        st.metric(label="📊 ยอดขายเดือนนี้", value=f"{month_sales:,.0f} บาท", delta=f"{month_cups:,} แก้ว")

    st.divider()

    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    if not df_all.empty:
        df_day = df_all[df_all["sale_date"] == str(selected_date)]
        
        if not df_day.empty:
            total_sales = df_day["total_price"].sum()
            total_costs = df_day["total_cost"].sum()
            total_profits = df_day["total_profit"].sum()
            total_cups = df_day["qty"].sum()

            cash_total = df_day[df_day["payment_method"] == "💵 เงินสด"]["total_price"].sum()
            qr_total = df_day[df_day["payment_method"].str.contains("QR", na=False)]["total_price"].sum()

            m_col1, m_col2 = st.columns(2)
            m_col1.metric("ยอดขายรวม", f"{total_sales:,.0f} บ.")
            m_col2.metric("กำไรสุทธิ", f"{total_profits:,.2f} บ.")
            
            m_col3, m_col4 = st.columns(2)
            m_col3.metric("ต้นทุนรวม", f"{total_costs:,.2f} บ.")
            m_col4.metric("ขายได้ทั้งหมด", f"{total_cups:,} แก้ว")

            st.write(f"💳 **แยกเงินเข้า:** 💵 เงินสด `{cash_total:,.0f} บ.` | 📱 QR/Scan `{qr_total:,.0f} บ.`")

            st.divider()
            st.subheader("📋 รายละเอียดรายการขายวันนี้")
            
            for index, row in df_day.iterrows():
                with st.container():
                    c_info, c_del = st.columns([4, 1])
                    with c_info:
                        seller = row['seller_name'] if pd.notna(row['seller_name']) and row['seller_name'] else "ไม่ระบุ"
                        st.markdown(f"**{row['item_name']}** ({row['qty']} แก้ว)")
                        st.caption(f"ยอดขาย: {row['total_price']:,.0f} บ. | {row['payment_method']} | 👤 ผู้บันทึก: **{seller}**")
                    with c_del:
                        if st.button("❌", key=f"btn_del_row_{row['id']}"):
                            confirm_delete_dialog(row['id'], row['item_name'], row['qty'])
                    st.markdown("<hr style='margin: 5px 0; border-color: #EADFD8;'>", unsafe_allow_html=True)

            csv_data = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดประวัติทั้งหมด (.CSV)",
                data=csv_data,
                file_name=f"sales_report_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )

        else:
            st.info(f"ยังไม่มีรายการขายในวันที่ {selected_date}")
    else:
        st.info("ยังไม่มีข้อมูลรายการขายในระบบ")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- ส่วนที่ 4: สรุปยอดขายรวมและอันดับขายดี ---
    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    st.subheader("📈 สรุปยอดขายรวม")

    if not df_all.empty:
        filter_time = st.radio("เลือกช่วงเวลา:", ["ประจำวัน", "ทั้งหมดสะสม"], horizontal=True)

        if filter_time == "ประจำวัน":
            target_df = df_all[df_all["sale_date"] == str(selected_date)]
        else:
            target_df = df_all

        if not target_df.empty:
            total_money_summary = target_df["total_price"].sum()
            total_cups_summary = target_df["qty"].sum()

            col_sum1, col_sum2 = st.columns(2)
            col_sum1.metric("ยอดขายรวมทั้งหมด", f"{total_money_summary:,.0f} บาท")
            col_sum2.metric("จำนวนขายรวมทั้งหมด", f"{total_cups_summary:,} แก้ว")

            st.divider()

            top_sellers = target_df.groupby("item_name").agg(
                จำนวนแก้ว=('qty', 'sum'),
                ยอดขายรวม_บาท=('total_price', 'sum')
            ).reset_index()

            top_sellers.columns = ["เมนู", "จำนวนแก้ว", "ยอดขายรวม (บาท)"]
            top_sellers = top_sellers.sort_values(by="จำนวนแก้ว", ascending=False).reset_index(drop=True)
            top_sellers.index += 1

            st.write("🏆 **5 อันดับเมนูขายดีที่สุด**")
            st.dataframe(
                top_sellers.head(5).style.format({"ยอดขายรวม (บาท)": "{:,.0f} บ."}), 
                use_container_width=True
            )
        else:
            st.info("ไม่มีข้อมูลการขายในช่วงเวลาที่เลือก")
    else:
        st.info("ยังไม่มีข้อมูลการขายในระบบ")
    st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # ⚙️ ส่วนจัดการระบบ (เพิ่ม/ลบเมนู & สมาชิก)
    # ==========================================
    with st.expander("⚙️ **จัดการระบบ (เพิ่ม/ลบเมนู & สมาชิก)**", expanded=False):
        tab_add_menu, tab_del_menu, tab_users = st.tabs(["➕ เพิ่มเมนู", "🗑️ ลบเมนู", "👥 สมาชิก"])

        with tab_add_menu:
            new_name = st.text_input("ชื่อเมนูใหม่", key="m_add_name")
            new_cost = st.number_input("ราคาต้นทุน (บาท)", min_value=0.0, value=10.0, step=0.5, key="m_add_cost")
            new_price = st.number_input("ราคาขายปกติ (บาท)", min_value=0, value=25, key="m_add_price")
            
            if st.button("💾 บันทึกเมนูใหม่", use_container_width=True, key="btn_save_m"):
                if new_name.strip() != "":
                    save_menu_item_db(new_name.strip(), new_cost, new_price)
                    st.success(f"เพิ่มเมนู '{new_name}' เรียบร้อย! (ลูกค้าเลือกสั่งได้ทันที)")
                    st.rerun()
                else:
                    st.warning("กรุณากรอกชื่อเมนู")

        with tab_del_menu:
            if st.session_state.role == "admin":
                if len(current_menu) > 0:
                    delete_item = st.selectbox("เลือกเมนูที่ต้องการลบออกจากระบบ", list(current_menu.keys()), key="m_del_item")
                    if st.button("❌ ลบเมนูนี้", use_container_width=True, key="btn_del_m"):
                        confirm_delete_menu_dialog(delete_item)
                else:
                    st.info("ไม่มีเมนูในระบบให้ลบ")
            else:
                st.error("🔒 สิทธิ์ไม่ถูกต้อง: เฉพาะ Admin เท่านั้นที่สามารถลบเมนูได้")

        with tab_users:
            if st.session_state.role == "admin":
                st.write("🟢 **สถานะผู้ใช้งาน**")
                all_users_status = get_all_users_with_status()
                st.dataframe(pd.DataFrame(all_users_status), use_container_width=True)
                
                other_users = [u["ผู้ใช้งาน"] for u in all_users_status if u["ผู้ใช้งาน"] != st.session_state.username]
                if other_users:
                    selected_user_str = st.selectbox("เลือกบัญชีที่จะลบ", other_users, key="m_del_user")
                    if st.button("❌ ลบบัญชีนี้", key="btn_del_usr", use_container_width=True):
                        confirm_delete_user_dialog(selected_user_str)
                else:
                    st.info("ไม่มีบัญชีอื่นให้ลบ")
            else:
                st.error("🔒 สิทธิ์ไม่ถูกต้อง: เฉพาะ Admin เท่านั้นที่สามารถจัดการสมาชิกได้")
