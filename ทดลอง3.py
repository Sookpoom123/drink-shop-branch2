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
    page_title="ร้านน้ำสร้างตัว 🧋 (ระบบหลังบ้าน/ครัว)", 
    page_icon="🧋", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- เชื่อมต่อฐานข้อมูล (รองรับ Secrets หลายรูปแบบ) ---
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
            padding: 14px;
            border-radius: 16px;
            border: 1px solid #EADFD8;
            box-shadow: 0 2px 10px rgba(0,0,0,0.02);
            margin-bottom: 16px;
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
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

load_app_styles()

ADMIN_SECRET_KEY = "3475"

# --- รายการเมนูใหม่ 46 รายการจากป้ายหน้าร้าน ---
DEFAULT_MENU = {
    # TAIWAN MILK TEA
    "ชานมไต้หวัน": {"cost": 8.0, "price": 19},
    "ชานมวนิลา": {"cost": 10.0, "price": 24},
    "ชานมคาราเมล": {"cost": 10.0, "price": 24},
    "ชานมน้ำผึ้ง": {"cost": 10.0, "price": 24},
    "ชานมลิ้นจี่": {"cost": 10.0, "price": 24},
    "ชานมเมล่อน": {"cost": 10.0, "price": 24},
    "ชานมสตรอเบอร์รี่": {"cost": 10.0, "price": 24},
    "ชานมแอปเปิ้ล": {"cost": 10.0, "price": 24},
    "ชานมกาแฟ": {"cost": 10.0, "price": 24},
    "ชานมโกโก้": {"cost": 10.0, "price": 24},
    "ชานมโอวัลติน": {"cost": 10.0, "price": 24},
    "ชานมเผือก": {"cost": 10.0, "price": 24},

    # COFFEE
    "โอเลี้ยง": {"cost": 8.0, "price": 19},
    "กาแฟโบราณ": {"cost": 10.0, "price": 24},
    "เนสกาแฟ": {"cost": 10.0, "price": 24},

    # THAI TEA & GREEN TEA
    "ชาดำเย็น": {"cost": 8.0, "price": 19},
    "ชามะนาว": {"cost": 8.0, "price": 19},
    "ชาแดงน้ำผึ้งมะนาว": {"cost": 8.0, "price": 19},
    "ชาไทยนม": {"cost": 10.0, "price": 24},
    "ชาเขียวนม": {"cost": 10.0, "price": 24},
    "ชาเขียวมะนาว": {"cost": 8.0, "price": 19},
    "ชาเขียวน้ำผึ้งมะนาว": {"cost": 8.0, "price": 19},
    "ชาเขียวใส": {"cost": 8.0, "price": 19},

    # OTHER / FRESH MILK
    "โกโก้": {"cost": 10.0, "price": 24},
    "นมชมพู": {"cost": 10.0, "price": 24},
    "โอวัลติน": {"cost": 10.0, "price": 24},
    "นมสดน้ำผึ้ง": {"cost": 10.0, "price": 24},
    "นมสดคาราเมล": {"cost": 10.0, "price": 24},
    "นมสดสีขาว": {"cost": 10.0, "price": 24},

    # FRUIT TEA
    "ชาสตรอเบอร์รี่": {"cost": 8.0, "price": 19},
    "ชาลิ้นจี่": {"cost": 8.0, "price": 19},
    "ชาเมล่อน": {"cost": 8.0, "price": 19},
    "ชาแอปเปิ้ล": {"cost": 8.0, "price": 19},

    # SMOOTHIE
    "กล้วยนมสดปั่น": {"cost": 15.0, "price": 34},
    "เผือกนมสดปั่น": {"cost": 15.0, "price": 34},
    "มะพร้าวนมสดปั่น": {"cost": 15.0, "price": 34},
    "เมล่อนนมสดปั่น": {"cost": 15.0, "price": 34},
    "มันม่วงนมสดปั่น": {"cost": 15.0, "price": 34},
    "สตรอเบอร์รี่นมสดปั่น": {"cost": 15.0, "price": 34},
    "โกโก้ปั่น": {"cost": 15.0, "price": 34},
    "โอวัลตินปั่น": {"cost": 15.0, "price": 34},
    "นมสดปั่น": {"cost": 15.0, "price": 34},
    "ชานมไต้หวันปั่น": {"cost": 15.0, "price": 34},
    "ชาไทยนมปั่น": {"cost": 15.0, "price": 34},
    "ชาเขียวนมปั่น": {"cost": 15.0, "price": 34},
    "มัทฉะนมสดปั่น": {"cost": 18.0, "price": 44},
}

# --- รายการท็อปปิ้งจากรูปภาพป้ายหน้าร้าน ---
DEFAULT_TOPPINGS = {
    # ท็อปปิ้ง 5 บาท
    "ไข่มุกสีดำ": 5.0,
    "ไข่มุกสีทอง": 5.0,
    "ฟรุ้ตสลัด": 5.0,
    "บุกนมสด": 5.0,
    # ท็อปปิ้ง 10 บาท
    "บุกเฉาก๊วย": 10.0,
    "บุกน้ำผึ้ง": 10.0,
    "บุกบราวน์ชูการ์": 10.0
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

    # 5. ตาราง toppings
    c.execute('''
        CREATE TABLE IF NOT EXISTS toppings (
            name TEXT PRIMARY KEY,
            price REAL
        )
    ''')
    
    # เติมข้อมูลเมนูเริ่มต้น
    c.execute("SELECT COUNT(*) FROM menu_items")
    if c.fetchone()[0] == 0:
        for name, info in DEFAULT_MENU.items():
            c.execute("INSERT INTO menu_items (name, cost, price) VALUES (%s, %s, %s) ON CONFLICT (name) DO NOTHING",
                        (name, info['cost'], info['price']))

    # เติมข้อมูลท็อปปิ้งเริ่มต้น
    c.execute("SELECT COUNT(*) FROM toppings")
    if c.fetchone()[0] == 0:
        for name, price in DEFAULT_TOPPINGS.items():
            c.execute("INSERT INTO toppings (name, price) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                        (name, price))
            
    conn.commit()
    conn.close()

def reset_and_sync_all_menu():
    """ฟังก์ชั่นสำหรับซิงค์เมนูใหม่ทั้ง 46 รายการเข้า Database"""
    conn = get_db_connection()
    c = conn.cursor()
    for name, info in DEFAULT_MENU.items():
        c.execute("""
            INSERT INTO menu_items (name, cost, price)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET cost = EXCLUDED.cost, price = EXCLUDED.price
        """, (name, info['cost'], info['price']))
    conn.commit()
    conn.close()
    st.cache_data.clear()

def reset_and_sync_toppings():
    """ฟังก์ชั่นสำหรับซิงค์ท็อปปิ้งจากป้ายร้านเข้า Database"""
    conn = get_db_connection()
    c = conn.cursor()
    for name, price in DEFAULT_TOPPINGS.items():
        c.execute("""
            INSERT INTO toppings (name, price)
            VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET price = EXCLUDED.price
        """, (name, price))
    conn.commit()
    conn.close()
    st.cache_data.clear()

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

@st.cache_data(ttl=10)
def get_toppings_from_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, price FROM toppings ORDER BY price ASC, name ASC")
    rows = c.fetchall()
    conn.close()
    toppings_dict = {}
    for r in rows:
        toppings_dict[r[0]] = float(r[1])
    return toppings_dict

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

def save_topping_db(name, price):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO toppings (name, price) 
        VALUES (%s, %s)
        ON CONFLICT (name) DO UPDATE SET price = EXCLUDED.price
    """, (name, price))
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

def delete_topping_db(name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM toppings WHERE name = %s", (name,))
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

@st.dialog("⚠️ ยืนยันการลบท็อปปิ้ง")
def confirm_delete_topping_dialog(topping_name):
    st.write(f"คุณต้องการลบท็อปปิ้ง **{topping_name}** ออกจากระบบใช่หรือไม่?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("✅ ยืนยันลบ", use_container_width=True, key="btn_confirm_del_topping"):
            delete_topping_db(topping_name)
            st.success(f"ลบท็อปปิ้ง '{topping_name}' เรียบร้อย!")
            time.sleep(0.5)
            st.rerun()
    with col_cancel:
        if st.button("❌ ยกเลิก", use_container_width=True, key="btn_cancel_del_topping"):
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
                            topping = item.get('topping', 'ไม่ใส่ท็อปปิ้ง')
                            topping_price = item.get('topping_price', 0)
                            
                            topping_str = f" 🧋 [{topping}] (+{topping_price}บ.)" if topping and topping != "ไม่ใส่ท็อปปิ้ง" else " (ไม่ใส่ท็อปปิ้ง)"
                            
                            st.write(f"- **{item['name']}**{topping_str} ({item['price']} บาท)")
                            item_summary_text.append(f"{item['name']}{topping_str}")
                        
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
current_toppings = get_toppings_from_db()

# ==========================================
# 1. หน้าเข้าสู่ระบบ / สมัครสมาชิก
# ==========================================
if not st.session_state.logged_in:

    st.markdown(
        """
        <div class="mobile-header">
            <h2 style="margin: 0; font-size: 24px; font-weight: 700;">🧋 ร้านน้ำสร้างตัว</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.90;">ระบบรับออเดอร์ครัว & จัดการหลังบ้าน</p>
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
# 2. หน้าหลักระบบหลังบ้าน / ครัว (Kitchen Display)
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

    # --- ส่วนที่ 1: 🔔 รายการออเดอร์เด้งเข้าครัวจากฝั่งลูกค้า (Auto-refresh) ---
    render_kitchen_orders()

    # --- ส่วนที่ 2: ตารางราคาเมนู & ท็อปปิ้ง ---
    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    st.subheader("📋 ตารางราคาเมนู (เชื่อมหน้าร้าน/ลูกค้า)")

    if st.session_state.role == "admin":
        st.caption("💡 **สำหรับ Admin:** คุณสามารถแก้ไขช่อง **'ต้นทุน'** หรือ **'ราคาขาย'** แล้วกดบันทึกได้เลย")
    else:
        st.caption("ℹ️ ตารางดูราคาหน้าร้าน")

    search_top_table = st.text_input("🔍 ค้นหาราคา...", "", key="m_search_top_table", placeholder="พิมพ์ชื่อเมนูที่นี่...")

    if current_menu:
        top_menu_list = []
        for item, info in current_menu.items():
            if search_top_table.lower() in item.lower():
                top_menu_list.append({
                    "เมนู": item,
                    "ต้นทุน": float(info['cost']),
                    "ราคาปกติ": float(info['price']),
                    "กำไรปกติ": float(round(info['price'] - info['cost'], 2))
                })
        
        df_menu_view = pd.DataFrame(top_menu_list)

        disabled_cols = ["เมนู", "กำไรปกติ"]
        if st.session_state.role != "admin":
            disabled_cols = True

        edited_df = st.data_editor(
            df_menu_view,
            use_container_width=True,
            height=250,
            disabled=disabled_cols,
            column_config={
                "ต้นทุน": st.column_config.NumberColumn("ต้นทุน (บ.)", format="%.2f"),
                "ราคาปกติ": st.column_config.NumberColumn("ราคาปกติ (บ.)", format="%.0f"),
                "กำไรปกติ": st.column_config.NumberColumn("กำไรปกติ (บ.)", format="%.1f")
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
                    new_p = row["ราคาปกติ"]
                    
                    old_c = current_menu[m_name]["cost"]
                    old_p = current_menu[m_name]["price"]
                    
                    if new_c != old_c or new_p != old_p:
                        save_menu_item_db(m_name, new_c, new_p)
                        updated_count += 1
                
                if updated_count > 0:
                    st.success(f"🎉 อัปเดตราคาเรียบร้อย {updated_count} รายการ!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.info("ไม่มีรายการที่เปลี่ยนแปลง")

    st.write("---")
    st.subheader("🧋 รายการท็อปปิ้ง (Topping)")
    if current_toppings:
        topping_list = [{"ท็อปปิ้ง": k, "ราคาบวกเพิ่ม (บาท)": f"+{v:.0f} บ."} for k, v in current_toppings.items()]
        st.dataframe(pd.DataFrame(topping_list), use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลท็อปปิ้งในระบบ")

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
    selected_date = st.date_input("📅 ดูประวัติยอดขายของวันที่", value=date.today())

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
    # ⚙️ ส่วนจัดการระบบ (เพิ่ม/ลบเมนู, ท็อปปิ้ง & สมาชิก)
    # ==========================================
    with st.expander("⚙️ **จัดการระบบ (เมนู / ท็อปปิ้ง / สมาชิก)**", expanded=False):
        tab_add_menu, tab_del_menu, tab_topping, tab_users = st.tabs(["➕ เพิ่ม/ซิงค์เมนู", "🗑️ ลบเมนู", "🧋 จัดการท็อปปิ้ง", "👥 สมาชิก"])

        # TAB 1: เพิ่ม/ซิงค์เมนู
        with tab_add_menu:
            if st.session_state.role == "admin":
                st.write("🔄 **อัปเดตเมนูใหม่ทั้งหมด (46 รายการจากป้ายร้าน):**")
                if st.button("⚡ ซิงค์เมนู 46 รายการใหม่เข้า Database ทันที", use_container_width=True, key="btn_sync_all_46"):
                    reset_and_sync_all_menu()
                    st.success("🎉 ซิงค์รายการเมนูใหม่ทั้ง 46 รายการเข้าฐานข้อมูลเรียบร้อยแล้ว!")
                    time.sleep(0.5)
                    st.rerun()
                st.divider()

            st.write("➕ **เพิ่มเมนูแบบกำหนดเอง:**")
            new_name = st.text_input("ชื่อเมนูใหม่", key="m_add_name")
            new_cost = st.number_input("ราคาต้นทุน (บาท)", min_value=0.0, value=10.0, step=0.5, key="m_add_cost")
            new_price = st.number_input("ราคาขายปกติ (บาท)", min_value=0, value=24, key="m_add_price")
            
            if st.button("💾 บันทึกเมนูใหม่", use_container_width=True, key="btn_save_m"):
                if new_name.strip() != "":
                    save_menu_item_db(new_name.strip(), new_cost, new_price)
                    st.success(f"เพิ่มเมนู '{new_name}' เรียบร้อย!")
                    st.rerun()
                else:
                    st.warning("กรุณากรอกชื่อเมนู")

        # TAB 2: ลบเมนู
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

        # TAB 3: จัดการท็อปปิ้ง
        with tab_topping:
            if st.session_state.role == "admin":
                st.write("🔄 **รีเซ็ต/ซิงค์ท็อปปิ้งจากป้ายร้าน:**")
                if st.button("⚡ ซิงค์ท็อปปิ้งจากป้ายร้าน (5บ./10บ.) เข้า Database", use_container_width=True, key="btn_sync_toppings"):
                    reset_and_sync_toppings()
                    st.success("🎉 ซิงค์ท็อปปิ้งเรียบร้อยแล้ว!")
                    time.sleep(0.5)
                    st.rerun()

                st.divider()
                st.write("➕ **เพิ่มท็อปปิ้งใหม่:**")
                t_name = st.text_input("ชื่อท็อปปิ้ง", key="t_add_name")
                t_price = st.number_input("ราคาบวกเพิ่ม (บาท)", min_value=0.0, value=5.0, step=1.0, key="t_add_price")
                if st.button("💾 บันทึกท็อปปิ้ง", use_container_width=True, key="btn_save_t"):
                    if t_name.strip() != "":
                        save_topping_db(t_name.strip(), t_price)
                        st.success(f"บันทึกท็อปปิ้ง '{t_name}' เรียบร้อย!")
                        st.rerun()
                    else:
                        st.warning("กรุณากรอกชื่อท็อปปิ้ง")

                st.divider()
                st.write("🗑️ **ลบท็อปปิ้ง:**")
                if current_toppings:
                    del_t_name = st.selectbox("เลือกท็อปปิ้งที่ต้องการลบ", list(current_toppings.keys()), key="t_del_select")
                    if st.button("❌ ลบท็อปปิ้งนี้", use_container_width=True, key="btn_del_t"):
                        confirm_delete_topping_dialog(del_t_name)
                else:
                    st.info("ไม่มีท็อปปิ้งให้ลบ")
            else:
                st.error("🔒 เฉพาะ Admin เท่านั้นที่จัดการท็อปปิ้งได้")

        # TAB 4: จัดการสมาชิก
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
