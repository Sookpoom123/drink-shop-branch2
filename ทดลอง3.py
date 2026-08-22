import base64
import hashlib
import psycopg2
from psycopg2 import pool
import streamlit as st
import time
import json
import re
from datetime import datetime, date
import pandas as pd

# --- ตั้งค่าหน้าตาเว็บไซต์รองรับ Mobile Screen ---
st.set_page_config(
    page_title="ร้านน้ำสร้างตัว 🧋 (ระบบหลังบ้าน/ครัว)", 
    page_icon="🧋", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# ⚡ ระบบ DATABASE CONNECTION POOLING
# ==========================================
@st.cache_resource
def get_db_pool():
    db_url = None
    if "postgres" in st.secrets and "url" in st.secrets["postgres"]:
        db_url = st.secrets["postgres"]["url"]
    elif "postgres_url" in st.secrets:
        db_url = st.secrets["postgres_url"]
    elif "DATABASE_URL" in st.secrets:
        db_url = st.secrets["DATABASE_URL"]
    
    if not db_url:
        st.error("❌ ไม่พบการตั้งค่า Database URL ใน Secrets")
        st.stop()
        
    return pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=db_url)

def get_db_connection():
    db_pool = get_db_pool()
    return db_pool.getconn()

def release_db_connection(conn):
    if conn:
        db_pool = get_db_pool()
        db_pool.putconn(conn)

# ==========================================
# 🌐 พจนานุกรมและระบบแปลภาษา (Foreign -> Thai)
# ==========================================
TRANSLATION_MAP = {
    # --- กล้วยนมสด ---
    "香蕉鲜奶冰沙": "กล้วยนมสดปั่น", "香蕉鲜奶": "กล้วยนมสด",
    "Banana Milkshake": "กล้วยนมสดปั่น", "Banana Milk": "กล้วยนมสด",
    "ငှက်ပျော နို့အေး": "กล้วยนมสด", "ငှက်ပျောနို့အေး": "กล้วยนมสด",

    # --- อังกฤษ (English) ---
    "Taiwan Milk Tea": "ชานมไต้หวัน", "Vanilla Milk Tea": "ชานมวนิลา", "Caramel Milk Tea": "ชานมคาราเมล",
    "Honey Milk Tea": "ชานมน้ำผึ้ง", "Lychee Milk Tea": "ชานมลิ้นจี่", "Melon Milk Tea": "ชานมเมล่อน",
    "Strawberry Milk Tea": "ชานมสตรอเบอร์รี่", "Apple Milk Tea": "ชานมแอปเปิ้ล", "Coffee Milk Tea": "ชานมกาแฟ",
    "Cocoa Milk Tea": "ชานมโกโก้", "Ovaltine Milk Tea": "ชานมโอวัลติน", "Taro Milk Tea": "ชานมเผือก",
    "O-Liang": "โอเลี้ยง", "Traditional Coffee": "กาแฟโบราณ", "Nescafe": "เนสกาแฟ",
    "Iced Black Tea": "ชาดำเย็น", "Lemon Tea": "ชามะนาว", "Honey Lemon Tea": "ชาแดงน้ำผึ้งมะนาว",
    "Thai Milk Tea": "ชาไทยนม", "Green Milk Tea": "ชาเขียวนม", "Lemon Green Tea": "ชาเขียวมะนาว",
    "Honey Lemon Green Tea": "ชาเขียวน้ำผึ้งมะนาว", "Jasmine Green Tea": "ชาเขียวใส", "Cocoa": "โกโก้",
    "Pink Milk": "นมชมพู", "Ovaltine": "โอวัลติน", "Honey Fresh Milk": "นมสดน้ำผึ้ง",
    "Caramel Fresh Milk": "นมสดคาราเมล", "Fresh Milk": "นมสดสีขาว", "Strawberry Tea": "ชาสตรอเบอร์รี่",
    "Lychee Tea": "ชาลิ้นจี่", "Melon Tea": "ชาเมล่อน", "Apple Tea": "ชาแอปเปิ้ล",
    "Taro Milkshake": "เผือกนมสดปั่น", "Coconut Milkshake": "มะพร้าวนมสดปั่น",
    "Melon Milkshake": "เมล่อนนมสดปั่น", "Purple Sweet Potato Milkshake": "มันม่วงนมสดปั่น", 
    "Strawberry Milkshake": "สตรอเบอร์รี่นมสดปั่น", "Cocoa Smoothie": "โกโก้ปั่น", "Ovaltine Smoothie": "โอวัลตินปั่น",
    "Milk Smoothie": "นมสดปั่น", "Taiwan Milk Tea Smoothie": "ชานมไต้หวันปั่น", "Thai Tea Smoothie": "ชาไทยนมปั่น",
    "Green Tea Smoothie": "ชาเขียวนมปั่น", "Matcha Fresh Milk Smoothie": "มัทฉะนมสดปั่น",
    "Black Boba": "ไข่มุกสีดำ", "Gold Boba": "ไข่มุกสีทอง", "Fruit Salad": "ฟรุ้ตสลัด",
    "Milk Jelly": "บุกนมสด", "Grass Jelly": "บุกเฉาก๊วย", "Honey Jelly": "บุกน้ำผึ้ง", "Brown Sugar Jelly": "บุกบราวน์ชูการ์",
    "No Topping": "ไม่ใส่ท็อปปิ้ง", "Takeaway": "สั่งกลับบ้าน", "Dine-in": "ทานที่ร้าน",

    # --- จีน (Chinese) ---
    "台湾奶茶": "ชานมไต้หวัน", "香草奶茶": "ชานมวนิลา", "焦糖奶茶": "ชานมคาราเมล", "蜂蜜奶茶": "ชานมน้ำผึ้ง",
    "荔枝奶茶": "ชานมลิ้นจี่", "哈蜜瓜奶茶": "ชานมเมล่อน", "草莓奶茶": "ชานมสตรอเบอร์รี่", "苹果奶茶": "ชานมแอปเปิ้ล",
    "咖啡奶茶": "ชานมกาแฟ", "可可奶茶": "ชานมโกโก้", "阿华田奶茶": "ชานมโอวัลติน", "香芋奶茶": "ชานมเผือก",
    "泰式黑咖啡": "โอเลี้ยง", "传统咖啡": "กาแฟโบราณ", "雀巢咖啡": "เนสกาแฟ", "冰红茶": "ชาดำเย็น",
    "柠檬茶": "ชามะนาว", "蜂蜜柠檬红茶": "ชาแดงน้ำผึ้งมะนาว", "泰式奶茶": "ชาไทยนม", "泰式绿奶茶": "ชาเขียวนม",
    "柠檬绿茶": "ชาเขียวมะนาว", "蜂蜜柠檬绿茶": "ชาเขียวน้ำผึ้งมะนาว", "清绿茶": "ชาเขียวใส", "可可": "โกโก้",
    "粉红奶": "นมชมพู", "阿华田": "โอวัลติน", "蜂蜜鲜奶": "นมสดน้ำผึ้ง", "焦糖鲜奶": "นมสดคาราเมล",
    "纯鲜奶": "นมสดสีขาว", "草莓茶": "ชาสตรอเบอร์รี่", "荔枝茶": "ชาลิ้นจี่", "哈蜜瓜茶": "ชาเมล่อน",
    "苹果茶": "ชาแอปเปิ้ล", "香芋鲜奶冰沙": "เผือกนมสดปั่น", "椰香鲜奶冰沙": "มะพร้าวนมสดปั่น",
    "哈蜜瓜鲜奶冰沙": "เมล่อนนมสดปั่น", "紫薯鲜奶冰沙": "มันม่วงนมสดปั่น", "草莓鲜奶冰沙": "สตรอเบอร์รี่นมสดปั่น",
    "可可冰沙": "โกโก้ปั่น", "阿华田冰沙": "โอวัลตินปั่น", "鲜奶冰沙": "นมสดปั่น", "台湾奶茶冰沙": "ชานมไต้หวันปั่น",
    "泰式奶茶冰沙": "ชาไทยนมปั่น", "泰式绿奶茶冰沙": "ชาเขียวนมปั่น", "抹茶鲜奶冰沙": "มัทฉะนมสดปั่น",
    "黑珍珠": "ไข่มุกสีดำ", "金珍珠": "ไข่มุกสีทอง", "水果波霸": "ฟรุ้ตสลัด", "牛奶魔芋": "บุกนมสด",
    "仙草魔芋": "บุกเฉาก๊วย", "蜂蜜魔芋": "บุกน้ำผึ้ง", "黑糖魔芋": "บุกบราวน์ชูการ์", "不加配料": "ไม่ใส่ท็อปปิ้ง",
    "外带": "สั่งกลับบ้าน", "堂食": "ทานที่ร้าน",

    # --- พม่า (Myanmar) ---
    "လက်ဖက်ရည် စိမ်း ပျားရည် သံပုရာ": "ชาเขียวน้ำผึ้งมะนาว",
    "လက်ဖက်ရည်စိမ်း ပျားရည် သံပုရာ": "ชาเขียวน้ำผึ้งมะนาว",
    "ပျားသံပုရာ လက်ဖက်ရည်စိမ်း": "ชาเขียวน้ำผึ้งมะนาว",
    "တိုင်ဝမ် နို့လက်ဖက်ရည်": "ชานมไต้หวัน", "ဗနီလာ နို့လက်ဖက်ရည်": "ชานมวนิลา",
    "ကာရာမဲလ် နို့လက်ဖက်ရည်": "ชานมคาราเมล", "ပျားရည် နို့လက်ဖက်ရည်": "ชานมน้ำผึ้ง", "လိုင်ချီး နို့လက်ဖက်ရည်": "ชานมลิ้นจี่",
    "ဖရဲသီး နို့လက်ဖက်ရည်": "ชานมเมล่อน", "စထရော်ဘယ်ရီ နို့လက်ဖက်ရည်": "ชานมสตรอเบอร์รี่", "ပန်းသီး နို့လက်ဖက်ရည်": "ชานมแอปเปิ้ล",
    "ကော်ဖီ နို့လက်ဖက်ရည်": "ชานมกาแฟ", "ကိုကိုး နို့လက်ဖက်ရည်": "ชานมโกโก้", "အိုဗာတင်း နို့လက်ဖက်ရည်": "ชานมโอวัลติน",
    "ပိန်းဥ နို့လက်ဖက်ရည်": "ชานมเผือก", "ထိုင်း ကော်ဖီနက်": "โอเลี้ยง", "ရှေးဟောင်း ကော်ဖီ": "กาแฟโบราณ",
    "နက်စကော်ဖီ": "เนสกาแฟ", "လက်ဖက်ရည်နက်အေး": "ชาดำเย็น", "သံပုရာ လက်ဖက်ရည်": "ชามะนาว",
    "ပျားသံပုရာ လက်ဖက်ရည်နီ": "ชาแดงน้ำผึ้งมะนาว", "ထိုင်း နို့လက်ဖက်ရည်": "ชาไทยนม", "လက်ဖက်ရည်စိမ်းနို့": "ชาเขียวนม",
    "သံပုရာ လက်ဖက်ရည်စိမ်း": "ชาเขียวมะนาว", "လက်ဖက်ရည်စိမ်း": "ชาเขียวใส",
    "ကိုကိုး": "โกโก้", "နို့န်းရောင်": "นมชมพู", "အိုဗာတင်း": "โอวัลติน", "ပျားရည် နို့စိမ်း": "นมสดน้ำผึ้ง",
    "ကာရာမဲလ် နို့စိမ်း": "นมสดคาราเมล", "နို့စိမ်း": "นมสดสีขาว", "စထရော်ဘယ်ရီ လက်ဖက်ရည်": "ชาสตรอเบอร์รี่",
    "လိုင်ချီး လက်ဖက်ရည်": "ชาลิ้นจี่", "ဖရဲသီး လက်ဖက်ရည်": "ชาเมล่อน", "ပန်းသီး လက်ဖက်ရည်": "ชาแอปเปิ้ล",
    "ပိန်းဥ နို့စိမ်းဖျော်ရည်": "เผือกนมสดปั่น", "အုန်းသီး နို့စိမ်းဖျော်ရည်": "มะพร้าวนมสดปั่น", "ဖရဲသီး နို့စိမ်းဖျော်ရည်": "เมล่อนนมสดปั่น",
    "ကန်စွန်းဥဝါ နို့စိမ်းဖျော်ရည်": "มันม่วงนมสดปั่น", "စထရော်ဘယ်ရီ နို့စိမ်းဖျော်ရည်": "สตรอเบอร์รี่นมสดปั่น",
    "ကိုကိုး ဖျော်ရည်": "โกโก้ปั่น", "အိုဗာတင်း ဖျော်ရည်": "โอวัลตินปั่น", "နို့စိမ်း ဖျော်ရည်": "นมสดปั่น",
    "တိုင်ဝမ် နို့လက်ဖက်ရည်ဖျော်ရည်": "ชานมไต้หวันปั่น", "ထိုင်း နို့လက်ဖက်ရည်ဖျော်ရည်": "ชาไทยนมปั่น",
    "လက်ဖက်ရည်စိမ်းနို့ ဖျော်ရည်": "ชาเขียวนมปั่น", "မက်ချာ နို့စိမ်းဖျော်ရည်": "มัทฉะนมสดปั่น",
    "အမဲ ရာဘာလုံး": "ไข่มุกสีดำ", "ရွှေရောင် ရာဘာလုံး": "ไข่มุกสีทอง", "သစ်သီးစုံ": "ฟรု้တสလัด",
    "နို့ဂျယ်လီ": "บุกนมสด", "ကျောက်ကျောဂျယ်လီ": "บุกเฉาก๊วย", "ပျားရည်ဂျယ်လီ": "บุกน้ำผึ้ง",
    "သကြားညိုဂျယ်လီ": "บุกဘရာတ်စူဂါ", "အပိုမပါ": "ไม่ใส่ท็อปပิ้ง", "ပါဆယ်": "สั่งกลับบ้าน", "ဆိုင်မှာစားမည်": "ทานที่ร้าน"
}

MONTH_NAMES_TH = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
}

def translate_to_thai(text):
    if not text:
        return text
    
    translated_text = str(text).strip()
    sorted_keys = sorted(TRANSLATION_MAP.keys(), key=len, reverse=True)

    for foreign_str in sorted_keys:
        if foreign_str in translated_text:
            translated_text = translated_text.replace(foreign_str, TRANSLATION_MAP[foreign_str])
            
    clean_text = re.sub(r'\s+', ' ', translated_text).strip()
    for foreign_str in sorted_keys:
        clean_foreign = re.sub(r'\s+', ' ', foreign_str).strip()
        if clean_foreign in clean_text:
            clean_text = clean_text.replace(clean_foreign, TRANSLATION_MAP[foreign_str])

    words = clean_text.split()
    dedup_words = []
    for w in words:
        if not dedup_words or w != dedup_words[-1]:
            dedup_words.append(w)
            
    return " ".join(dedup_words)

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

DEFAULT_MENU = {
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
    "โอเลี้ยง": {"cost": 8.0, "price": 19},
    "กาแฟโบราณ": {"cost": 10.0, "price": 24},
    "เนสกาแฟ": {"cost": 10.0, "price": 24},
    "ชาดำเย็น": {"cost": 8.0, "price": 19},
    "ชามะนาว": {"cost": 8.0, "price": 19},
    "ชาแดงน้ำผึ้งมะนาว": {"cost": 8.0, "price": 19},
    "ชาไทยนม": {"cost": 10.0, "price": 24},
    "ชาเขียวนม": {"cost": 10.0, "price": 24},
    "ชาเขียวมะนาว": {"cost": 8.0, "price": 19},
    "ชาเขียวน้ำผึ้งมะนาว": {"cost": 8.0, "price": 19},
    "ชาเขียวใส": {"cost": 8.0, "price": 19},
    "โกโก้": {"cost": 10.0, "price": 24},
    "นมชมพู": {"cost": 10.0, "price": 24},
    "โอวัลติน": {"cost": 10.0, "price": 24},
    "นมสดน้ำผึ้ง": {"cost": 10.0, "price": 24},
    "นมสดคาราเมล": {"cost": 10.0, "price": 24},
    "นมสดสีขาว": {"cost": 10.0, "price": 24},
    "ชาสตรอเบอร์รี่": {"cost": 8.0, "price": 19},
    "ชาลิ้นจี่": {"cost": 8.0, "price": 19},
    "ชาเมล่อน": {"cost": 8.0, "price": 19},
    "ชาแอปเปิ้ล": {"cost": 8.0, "price": 19},
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

DEFAULT_TOPPINGS = {
    "ไข่มุกสีดำ": 5.0,
    "ไข่มุกสีทอง": 5.0,
    "ฟรุ้ตสลัด": 5.0,
    "บุกนมสด": 5.0,
    "บุกเฉาก๊วย": 10.0,
    "บุกน้ำผึ้ง": 10.0,
    "บุกบราวน์ชูการ์": 10.0
}

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    try:
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                role TEXT DEFAULT 'user',
                last_active TEXT,
                profile_img TEXT
            )
        ''')
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS menu_items (
                name TEXT PRIMARY KEY,
                cost REAL,
                price REAL,
                image_url TEXT
            )
        ''')
        # ตรวจสอบคอลัมน์ image_url ก่อนทำ ALTER TABLE
        # ป้องกันการพยายามล็อกตารางทุกครั้งที่ Streamlit รัน init_db()
        c.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'menu_items'
              AND column_name = 'image_url'
            LIMIT 1
        """)
        if c.fetchone() is None:
            c.execute("ALTER TABLE menu_items ADD COLUMN image_url TEXT;")

        c.execute('''
            CREATE TABLE IF NOT EXISTS toppings (
                name TEXT PRIMARY KEY,
                price REAL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                expense_date TEXT,
                title TEXT,
                amount REAL,
                note TEXT,
                recorded_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)")
        
        c.execute("SELECT COUNT(*) FROM menu_items")
        if c.fetchone()[0] == 0:
            for name, info in DEFAULT_MENU.items():
                c.execute("INSERT INTO menu_items (name, cost, price, image_url) VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO NOTHING",
                            (name, info['cost'], info['price'], ""))

        c.execute("SELECT COUNT(*) FROM toppings")
        if c.fetchone()[0] == 0:
            for name, price in DEFAULT_TOPPINGS.items():
                c.execute("INSERT INTO toppings (name, price) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                            (name, price))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)

def reset_and_sync_toppings():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        for name, price in DEFAULT_TOPPINGS.items():
            c.execute("""
                INSERT INTO toppings (name, price)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET price = EXCLUDED.price
            """, (name, price))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

def update_user_activity(username):
    if username:
        conn = get_db_connection()
        c = conn.cursor()
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("UPDATE users SET last_active = %s WHERE username = %s", (now_str, username))
            conn.commit()
        finally:
            c.close()
            release_db_connection(conn)

def update_user_profile_img(username, img_bytes):
    encoded_img = base64.b64encode(img_bytes).decode('utf-8')
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET profile_img = %s WHERE username = %s", (encoded_img, username))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)

def get_user_profile_img(username):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT profile_img FROM users WHERE username = %s", (username,))
        row = c.fetchone()
        return row[0] if row and row[0] else None
    finally:
        c.close()
        release_db_connection(conn)

@st.cache_data(ttl=60)
def get_menu_from_db():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT name, cost, price, image_url FROM menu_items ORDER BY name ASC")
        rows = c.fetchall()
        menu_dict = {}
        for r in rows:
            menu_dict[r[0]] = {
                "cost": float(r[1]) if r[1] is not None else 0.0, 
                "price": float(r[2]),
                "image_url": r[3] if len(r) > 3 and r[3] else ""
            }
        return menu_dict
    finally:
        c.close()
        release_db_connection(conn)

@st.cache_data(ttl=60)
def get_toppings_from_db():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT name, price FROM toppings ORDER BY price ASC, name ASC")
        rows = c.fetchall()
        toppings_dict = {}
        for r in rows:
            toppings_dict[r[0]] = float(r[1])
        return toppings_dict
    finally:
        c.close()
        release_db_connection(conn)

def save_menu_item_db(name, price, cost=0.0, image_url=""):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        if image_url == "KEEP_OLD":
            c.execute("""
                INSERT INTO menu_items (name, cost, price, image_url) 
                VALUES (%s, %s, %s, '')
                ON CONFLICT (name) DO UPDATE SET 
                    cost = EXCLUDED.cost,
                    price = EXCLUDED.price
            """, (name, cost, price))
        else:
            c.execute("""
                INSERT INTO menu_items (name, cost, price, image_url) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET 
                    cost = EXCLUDED.cost,
                    price = EXCLUDED.price,
                    image_url = EXCLUDED.image_url
            """, (name, cost, price, image_url))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

def save_topping_db(name, price):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO toppings (name, price) 
            VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET price = EXCLUDED.price
        """, (name, price))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

def delete_menu_item_db(name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM menu_items WHERE name = %s", (name,))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

def delete_topping_db(name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM toppings WHERE name = %s", (name,))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

def add_user(username, password, role='user'):
    conn = get_db_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute('INSERT INTO users (username, password, role, last_active) VALUES (%s, %s, %s, %s)', 
                    (username, make_hashes(password), role, now_str))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        return False
    finally:
        c.close()
        release_db_connection(conn)

def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT username, role FROM users WHERE username = %s AND password = %s',
                    (username, make_hashes(password)))
        return c.fetchone()
    finally:
        c.close()
        release_db_connection(conn)

def get_user_role(username):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT role FROM users WHERE username = %s', (username,))
        data = c.fetchone()
        return data[0] if data else "user"
    finally:
        c.close()
        release_db_connection(conn)

def get_all_users_with_status():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT username, role, last_active FROM users')
        rows = c.fetchall()
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
    finally:
        c.close()
        release_db_connection(conn)

def delete_user(username):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM users WHERE username = %s', (username,))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)

def set_user_offline(username):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET last_active = NULL WHERE username = %s", (username,))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)

@st.cache_data(ttl=15)
def get_sales_by_date(selected_date_str):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM sales WHERE sale_date = %s", conn, params=(selected_date_str,))
        return df
    finally:
        release_db_connection(conn)

@st.cache_data(ttl=30)
def get_sales_by_month(year, month):
    conn = get_db_connection()
    try:
        pattern = f"{year:04d}-{month:02d}-%"
        df = pd.read_sql_query("SELECT * FROM sales WHERE sale_date LIKE %s ORDER BY sale_date DESC, id DESC", conn, params=(pattern,))
        return df
    finally:
        release_db_connection(conn)

@st.cache_data(ttl=30)
def get_all_sales():
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM sales ORDER BY sale_date DESC, id DESC", conn)
        return df
    finally:
        release_db_connection(conn)

def delete_sale_by_id(record_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM sales WHERE id = %s", (record_id,))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

def add_expense(expense_date, title, amount, note, recorded_by):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO expenses (expense_date, title, amount, note, recorded_by)
            VALUES (%s, %s, %s, %s, %s)
        ''', (str(expense_date), title, amount, note, recorded_by))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

@st.cache_data(ttl=15)
def get_expenses_by_date(selected_date_str):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM expenses WHERE expense_date = %s ORDER BY id DESC", conn, params=(selected_date_str,))
        return df
    finally:
        release_db_connection(conn)

@st.cache_data(ttl=30)
def get_expenses_by_month(year, month):
    conn = get_db_connection()
    try:
        pattern = f"{year:04d}-{month:02d}-%"
        df = pd.read_sql_query("SELECT * FROM expenses WHERE expense_date LIKE %s ORDER BY expense_date DESC, id DESC", conn, params=(pattern,))
        return df
    finally:
        release_db_connection(conn)

@st.cache_data(ttl=30)
def get_all_expenses():
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM expenses ORDER BY expense_date DESC, id DESC", conn)
        return df
    finally:
        release_db_connection(conn)

def delete_expense_by_id(record_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM expenses WHERE id = %s", (record_id,))
        conn.commit()
    finally:
        c.close()
        release_db_connection(conn)
    st.cache_data.clear()

def complete_order_and_record_sale(order_id, table_no_translated, item_summary_text, items_count, o_total_price, o_total_cost, created_at=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order_id,))
        
        combined_item_names = ", ".join(item_summary_text) if isinstance(item_summary_text, list) else str(item_summary_text)
        total_price_f = float(o_total_price) if o_total_price is not None else 0.0
        total_cost_f = float(o_total_cost) if o_total_cost is not None else 0.0
        total_profit = total_price_f - total_cost_f
        
        if created_at:
            if isinstance(created_at, (datetime, date)):
                sale_date_str = str(created_at.date())
            else:
                sale_date_str = str(created_at).split()[0]
        else:
            sale_date_str = str(date.today())

        cur.execute('''
            INSERT INTO sales (sale_date, item_name, qty, total_price, total_cost, total_profit, seller_name, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (sale_date_str, f"📱 {table_no_translated}: {combined_item_names}", items_count, total_price_f, total_cost_f, total_profit, "ลูกค้าสั่งเอง", "📱 QR/Scan"))
        
        conn.commit()
        st.cache_data.clear()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"เกิดข้อผิดพลาดในการทำรายการ: {e}")
        return False
    finally:
        cur.close()
        release_db_connection(conn)

# ==========================================
# 🔔 POP-UP DIALOGS
# ==========================================
@st.dialog("🖼️ จัดการรูปภาพเมนู")
def edit_menu_image_dialog(menu_name, current_img_url):
    st.write(f"แก้ไขรูปภาพสำหรับเมนู: **{menu_name}**")
    
    if current_img_url:
        st.write("🖼️ รูปภาพปัจจุบัน:")
        st.image(current_img_url, width=150)
    else:
        st.info("ยังไม่มีรูปภาพสำหรับเมนูนี้")
        
    uploaded_file = st.file_uploader("เลือกรูปภาพใหม่ (PNG, JPG)", type=["png", "jpg", "jpeg"], key=f"dialog_img_{menu_name}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 บันทึกรูปภาพ", use_container_width=True, key="btn_save_m_img"):
            if uploaded_file is not None:
                img_bytes = uploaded_file.read()
                base64_str = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
                
                # ดึงราคาปัจจุบันมาคงเดิม
                m_info = current_menu.get(menu_name, {"price": 0.0, "cost": 0.0})
                save_menu_item_db(menu_name, m_info["price"], cost=m_info["cost"], image_url=base64_str)
                st.success("อัปเดตรูปภาพเรียบร้อย!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("กรุณาเลือกไฟล์รูปภาพก่อน")
    with col2:
        if st.button("❌ ปิด", use_container_width=True, key="btn_close_m_img"):
            st.rerun()

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

@st.dialog("⚠️ ยืนยันการลบรายการรายจ่าย")
def confirm_delete_expense_dialog(exp_id, title, amount):
    st.write(f"คุณต้องการลบรายจ่าย **{title}** ({amount:,.0f} บาท) ใช่หรือไม่?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("✅ ยืนยันลบ", use_container_width=True, key="btn_confirm_del_exp"):
            delete_expense_by_id(exp_id)
            st.success("ลบรายการรายจ่ายเรียบร้อย!")
            time.sleep(0.5)
            st.rerun()
    with col_cancel:
        if st.button("❌ ยกเลิก", use_container_width=True, key="btn_cancel_del_exp"):
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

# --- ส่วนของการแสดงออเดอร์เด้งเข้าครัวแบบ Auto-refresh (10s) ---
@st.fragment(run_every="10s")
def render_kitchen_orders():
    st.markdown('<div class="pos-card" style="border: 2px solid #8C6D58;">', unsafe_allow_html=True)
    st.subheader("🔔 ออเดอร์เด้งเข้าครัว (สั่งจากลูกค้า)")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, table_number, items_json, total_price, total_cost, created_at FROM orders WHERE status = 'pending' ORDER BY id ASC")
        pending_orders = cur.fetchall()
        cur.close()
        release_db_connection(conn)

        if not pending_orders:
            st.info("🟢 ยังไม่มีออเดอร์ใหม่เข้ามา...")
        else:
            st.warning(f"⚠️ มีออเดอร์ค้างทำอยู่ **{len(pending_orders)}** รายการ")
            for order in pending_orders:
                order_id, table_no, items_json, o_total_price, o_total_cost, created_at = order
                table_no_translated = translate_to_thai(table_no)
                
                if isinstance(items_json, str):
                    try:
                        items = json.loads(items_json)
                    except json.JSONDecodeError:
                        items = []
                else:
                    items = items_json if items_json else []
                
                with st.container(border=True):
                    col_o1, col_o2 = st.columns([3, 1])
                    item_summary_text = []

                    with col_o1:
                        st.markdown(f"### 📌 **{table_no_translated}** (ออเดอร์ #{order_id})")
                        st.caption(f"🕒 เวลาที่สั่ง: {created_at}")
                        
                        for item in items:
                            raw_display = item.get('display_name') or item.get('name', 'ไม่ระบุรายการ')
                            item_display = translate_to_thai(raw_display)
                            item_price = item.get('price', 0.0)
                            
                            topping_val = item.get('topping')
                            topping_translated = translate_to_thai(topping_val) if topping_val else ""
                            
                            has_topping = (topping_translated and topping_translated != "ไม่ใส่ท็อปปิ้ง") or ("(+" in item_display)
                            
                            if not has_topping:
                                full_item_text = f"{item_display} (ไม่ใส่ท็อปปิ้ง)"
                            else:
                                full_item_text = item_display

                            st.write(f"- **{full_item_text}** ({item_price} บาท)")
                            item_summary_text.append(full_item_text)
                        
                        st.write(f"💰 **ราคารวม: {o_total_price} บาท**")

                    with col_o2:
                        if st.button("✅ ทำเสร็จแล้ว", key=f"done_order_{order_id}", type="primary", use_container_width=True):
                            if complete_order_and_record_sale(order_id, table_no_translated, item_summary_text, len(items), o_total_price, o_total_cost, created_at=created_at):
                                st.success("ทำเสร็จแล้วและบันทึกลงยอดขายเรียบร้อย!")
                                time.sleep(0.5)
                                st.rerun()

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

today = date.today()
today_str = str(today)

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

    # --- ส่วนที่ 1: 🔔 รายการออเดอร์เด้งเข้าครัวจากฝั่งลูกค้า ---
    render_kitchen_orders()

    # --- ส่วนที่ 2: ตารางราคาและรูปภาพเมนู ---
    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    st.subheader("📋 ตารางราคาและรูปภาพเมนู (เชื่อมหน้าร้าน/ลูกค้า)")

    if st.session_state.role == "admin":
        st.caption("💡 **สำหรับ Admin:** คุณสามารถแก้ไขช่อง **'ราคาปกติ'** แล้วกดบันทึก หรือกดปุ่ม **🖼️ จัดการรูป** เพื่ออัปเดตรูปภาพได้เลย")
    else:
        st.caption("ℹ️ ตารางดูราคาหน้าร้าน")

    search_top_table = st.text_input("🔍 ค้นหาราคา...", "", key="m_search_top_table", placeholder="พิมพ์ชื่อเมนูที่นี่...")

    if current_menu:
        top_menu_list = []
        for item, info in current_menu.items():
            if search_top_table.lower() in item.lower():
                top_menu_list.append({
                    "เมนู": item,
                    "ราคาปกติ": float(info['price']),
                    "มีรูปภาพ": "✅ มีรูปแล้ว" if info.get("image_url") else "❌ ยังไม่มีรูป"
                })
        
        df_menu_view = pd.DataFrame(top_menu_list)

        disabled_cols = ["เมนู", "มีรูปภาพ"]
        if st.session_state.role != "admin":
            disabled_cols = True

        edited_df = st.data_editor(
            df_menu_view,
            use_container_width=True,
            height=250,
            disabled=disabled_cols,
            column_config={
                "ราคาปกติ": st.column_config.NumberColumn("ราคาปกติ (บ.)", format="%.0f")
            },
            hide_index=True,
            key="direct_menu_editor"
        )

        if st.session_state.role == "admin":
            col_save_tbl, col_manage_img = st.columns(2)
            with col_save_tbl:
                if st.button("💾 บันทึกการแก้ไขราคาในตาราง", use_container_width=True, key="btn_save_inline_table"):
                    updated_count = 0
                    for _, row in edited_df.iterrows():
                        m_name = row["เมนู"]
                        new_p = float(row["ราคาปกติ"])
                        
                        old_c = current_menu[m_name]["cost"]
                        old_p = current_menu[m_name]["price"]
                        old_img = current_menu[m_name].get("image_url", "")
                        
                        if new_p != old_p:
                            save_menu_item_db(m_name, new_p, cost=old_c, image_url=old_img)
                            updated_count += 1
                    
                    if updated_count > 0:
                        st.cache_data.clear()
                        st.success(f"🎉 อัปเดตราคาเรียบร้อย {updated_count} รายการ!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.info("ไม่มีรายการที่เปลี่ยนแปลง")

            with col_manage_img:
                selected_menu_to_img = st.selectbox("เลือกเมนูเพื่อจัดการรูปภาพ:", list(current_menu.keys()), key="select_m_img_popup")
                if st.button("🖼️ จัดการรูปภาพเมนูนี้", use_container_width=True, key="btn_open_m_img_dialog"):
                    curr_img = current_menu[selected_menu_to_img].get("image_url", "")
                    edit_menu_image_dialog(selected_menu_to_img, curr_img)

    st.write("---")
    st.subheader("🧋 รายการท็อปปิ้ง (Topping)")
    if current_toppings:
        topping_list = [{"ท็อปปิ้ง": k, "ราคาบวกเพิ่ม (บาท)": f"+{v:.0f} บ."} for k, v in current_toppings.items()]
        st.dataframe(pd.DataFrame(topping_list), use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลท็อปปิ้งในระบบ")

    st.markdown('</div>', unsafe_allow_html=True)

    # --- ส่วนที่ 3: สรุปยอดขายวันนี้ ---
    df_today_sales = get_sales_by_date(today_str)
    
    today_sales = df_today_sales['total_price'].sum() if not df_today_sales.empty else 0
    today_cups = df_today_sales['qty'].sum() if not df_today_sales.empty else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="📅 ยอดขายวันนี้", value=f"{today_sales:,.0f} บาท", delta=f"{today_cups:,} แก้ว")
    with col2:
        st.metric(label="📊 ยอดสั่งซื้อวันนี้ (ออเดอร์)", value=f"{len(df_today_sales):,} รายการ")

    st.divider()

    # ==========================================
    # 📌 ✨ ส่วนสรุปทางการเงินตามรายวัน / รายเดือน ✨
    # ==========================================
    report_view_type = st.radio(
        "📌 เลือกโหมดการดูสรุปทางการเงิน:",
        ["📅 รายวัน (ดูเฉพาะวันที่เลือก)", "🗓️ รายเดือน (เดือนนี้ / เดือนอื่นๆ)"],
        horizontal=True
    )

    if report_view_type.startswith("📅 รายวัน"):
        st.markdown('<div class="pos-card">', unsafe_allow_html=True)
        st.subheader("📆 เลือกวันที่ต้องการดูสรุปยอดขายและประวัติย้อนหลัง")
        selected_date = st.date_input("เลือกวันที่:", value=date.today(), key="view_selected_date")

        selected_date_str = str(selected_date)
        df_day_sales = get_sales_by_date(selected_date_str)
        df_day_exp = get_expenses_by_date(selected_date_str)

        total_sales = df_day_sales["total_price"].sum() if not df_day_sales.empty else 0.0
        total_expenses = df_day_exp["amount"].sum() if not df_day_exp.empty else 0.0
        net_profit = total_sales - total_expenses
        total_cups = df_day_sales["qty"].sum() if not df_day_sales.empty else 0

        cash_total = df_day_sales[df_day_sales["payment_method"] == "💵 เงินสด"]["total_price"].sum() if not df_day_sales.empty else 0.0
        qr_total = df_day_sales[df_day_sales["payment_method"].str.contains("QR", na=False)]["total_price"].sum() if not df_day_sales.empty else 0.0

        st.markdown(f"### 📊 สรุปทางการเงินวันที่ **{selected_date.strftime('%d/%m/%Y')}**")

        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("💵 ยอดขายรวม", f"{total_sales:,.0f} บ.")
        m_col2.metric("💸 รายจ่ายรวม", f"{total_expenses:,.0f} บ.")
        m_col3.metric("🎉 กำไรคงเหลือสุทธิ", f"{net_profit:,.0f} บ.")

        st.write(f"🥤 **จำนวนขายได้:** `{total_cups:,} แก้ว` | 💵 เงินสด `{cash_total:,.0f} บ.` | 📱 QR/Scan `{qr_total:,.0f} บ.`")

        st.divider()
        
        # --- รายการบันทึกรายจ่ายประจำวัน ---
        st.subheader(f"💸 รายการบันทึกรายจ่ายประจำวันที่ {selected_date.strftime('%d/%m/%Y')}")
        if not df_day_exp.empty:
            for index, row in df_day_exp.iterrows():
                with st.container():
                    c_exp_info, c_exp_del = st.columns([4, 1])
                    with c_exp_info:
                        note_str = f" ({row['note']})" if pd.notna(row['note']) and row['note'] else ""
                        st.markdown(f"**{row['title']}**{note_str}")
                        st.caption(f"จำนวนเงิน: **{row['amount']:,.0f} บ.** | 👤 ผู้บันทึก: **{row['recorded_by']}**")
                    with c_exp_del:
                        if st.button("❌", key=f"btn_del_exp_{row['id']}"):
                            confirm_delete_expense_dialog(row['id'], row['title'], row['amount'])
                st.markdown("<hr style='margin: 5px 0; border-color: #EADFD8;'>", unsafe_allow_html=True)
        else:
            st.info(f"ยังไม่มีรายการบันทึกรายจ่ายในวันที่ {selected_date.strftime('%d/%m/%Y')}")

        st.divider()

        # --- รายการขายประจำวัน ---
        st.subheader(f"📋 รายละเอียดรายการขายประจำวันที่ {selected_date.strftime('%d/%m/%Y')}")
        if not df_day_sales.empty:
            for index, row in df_day_sales.iterrows():
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

            csv_data = df_day_sales.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 ดาวน์โหลดประวัติขายเฉพาะวันที่ {selected_date.strftime('%d/%m/%Y')} (.CSV)",
                data=csv_data,
                file_name=f"sales_report_{selected_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info(f"ยังไม่มีรายการขายในวันที่ {selected_date.strftime('%d/%m/%Y')}")

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # 🗓️ โหมดดูสรุปรายเดือน (เดือนนี้/เดือนต่อๆ ไป/ย้อนหลัง)
        st.markdown('<div class="pos-card">', unsafe_allow_html=True)
        st.subheader("🗓️ สรุปทางการเงินรายเดือน (เดือนนี้ / เดือนต่อๆ ไป และดูย้อนหลัง)")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            selected_year = st.selectbox(
                "เลือกปี (พ.ศ. / ค.ศ.):",
                options=list(range(today.year - 3, today.year + 5)),
                index=3,
                key="month_view_year"
            )
        with col_m2:
            selected_month = st.selectbox(
                "เลือกเดือน:",
                options=list(range(1, 13)),
                format_func=lambda x: f"{x:02d} - {MONTH_NAMES_TH[x]}",
                index=today.month - 1,
                key="month_view_month"
            )

        df_month_sales = get_sales_by_month(selected_year, selected_month)
        df_month_exp = get_expenses_by_month(selected_year, selected_month)

        m_total_sales = df_month_sales["total_price"].sum() if not df_month_sales.empty else 0.0
        m_total_expenses = df_month_exp["amount"].sum() if not df_month_exp.empty else 0.0
        m_net_profit = m_total_sales - m_total_expenses
        m_total_cups = df_month_sales["qty"].sum() if not df_month_sales.empty else 0

        month_label = f"{MONTH_NAMES_TH[selected_month]} {selected_year}"
        st.markdown(f"### 📈 สรุปทางการเงินประจำเดือน **{month_label}**")

        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("💵 ยอดขายรวมทั้งเดือน", f"{m_total_sales:,.0f} บ.")
        c_m2.metric("💸 รายจ่ายรวมทั้งเดือน", f"{m_total_expenses:,.0f} บ.")
        c_m3.metric("🎉 กำไรสุทธิคงเหลือ", f"{m_net_profit:,.0f} บ.")

        st.write(f"🥤 **จำนวนขายได้รวมทั้งเดือน:** `{m_total_cups:,} แก้ว` | **ออเดอร์ทั้งหมด:** `{len(df_month_sales):,} รายการ`")

        st.divider()

        # --- ตารางเปรียบเทียบรายวันในเดือนนั้น ---
        st.subheader(f"📊 สรุปยอดขายและรายจ่ายแยกรายวันประจำเดือน {month_label}")
        if not df_month_sales.empty or not df_month_exp.empty:
            sales_daily = df_month_sales.groupby("sale_date").agg(
                ยอดขาย=('total_price', 'sum'),
                แก้ว=('qty', 'sum')
            ).reset_index().rename(columns={"sale_date": "วันที่"}) if not df_month_sales.empty else pd.DataFrame(columns=["วันที่", "ยอดขาย", "แก้ว"])

            exp_daily = df_month_exp.groupby("expense_date").agg(
                รายจ่าย=('amount', 'sum')
            ).reset_index().rename(columns={"expense_date": "วันที่"}) if not df_month_exp.empty else pd.DataFrame(columns=["วันที่", "รายจ่าย"])

            daily_summary = pd.merge(sales_daily, exp_daily, on="วันที่", how="outer").fillna(0)
            daily_summary["กำไรสุทธิ"] = daily_summary["ยอดขาย"] - daily_summary["รายจ่าย"]
            daily_summary = daily_summary.sort_values(by="วันที่", ascending=False).reset_index(drop=True)

            st.dataframe(
                daily_summary.style.format({
                    "ยอดขาย": "{:,.0f} บ.",
                    "รายจ่าย": "{:,.0f} บ.",
                    "กำไรสุทธิ": "{:,.0f} บ.",
                    "แก้ว": "{:,.0f}"
                }),
                use_container_width=True
            )

            csv_month_data = df_month_sales.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 ดาวน์โหลดรายงานยอดขายประจำเดือน {month_label} (.CSV)",
                data=csv_month_data,
                file_name=f"sales_monthly_{selected_year}_{selected_month:02d}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info(f"ไม่มีข้อมูลการขายหรือรายจ่ายในเดือน {month_label}")

        st.markdown('</div>', unsafe_allow_html=True)

    # --- ส่วนที่ 4: สรุปยอดขายรวมและอันดับขายดี ---
    st.markdown('<div class="pos-card">', unsafe_allow_html=True)
    st.subheader("📈 สรุปยอดขายและอันดับขายดี")

    filter_time = st.radio("เลือกช่วงเวลาในการดูอันดับขายดี:", ["เดือนที่เลือก", "ทั้งหมดสะสม"], horizontal=True)

    if filter_time == "เดือนที่เลือก":
        target_df = get_sales_by_month(selected_year, selected_month) if 'selected_year' in locals() else df_today_sales
    else:
        target_df = get_all_sales()

    if not target_df.empty:
        total_money_summary = target_df["total_price"].sum()
        total_cups_summary = target_df["qty"].sum()

        col_sum1, col_sum2 = st.columns(2)
        col_sum1.metric("ยอดขายรวมตามช่วงเวลา", f"{total_money_summary:,.0f} บาท")
        col_sum2.metric("จำนวนขายรวมตามช่วงเวลา", f"{total_cups_summary:,} แก้ว")

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
    st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # ⚙️ ส่วนจัดการระบบ (เพิ่ม/ลบเมนู, ท็อปปิ้ง, รายจ่าย & สมาชิก)
    # ==========================================
    with st.expander("⚙️ **จัดการระบบ (เมนู / ท็อปปิ้ง / รายจ่าย / สมาชิก)**", expanded=False):
        tab_add_menu, tab_del_menu, tab_topping, tab_expense, tab_users = st.tabs(
            ["➕ เพิ่มเมนูใหม่", "🗑️ ลบเมนู", "🧋 จัดการท็อปปิ้ง", "💸 บันทึกรายจ่าย", "👥 สมาชิก"]
        )

        # TAB 1: เพิ่มเมนูใหม่ (พร้อมอัปโหลดรูปภาพ)
        with tab_add_menu:
            st.write("➕ **เพิ่มเมนูใหม่แบบกำหนดเอง:**")
            new_name = st.text_input("ชื่อเมนูใหม่", key="m_add_name")
            new_price = st.number_input("ราคาขายปกติ (บาท)", min_value=0, value=24, key="m_add_price")
            new_img_file = st.file_uploader("🖼️ เลือกรูปภาพเมนู (PNG, JPG)", type=["png", "jpg", "jpeg"], key="m_add_img")
            
            if st.button("💾 บันทึกเมนูใหม่", use_container_width=True, key="btn_save_m"):
                if new_name.strip() != "":
                    img_base64_str = ""
                    if new_img_file is not None:
                        img_bytes = new_img_file.read()
                        img_base64_str = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"

                    save_menu_item_db(new_name.strip(), float(new_price), image_url=img_base64_str)
                    st.cache_data.clear()
                    st.success(f"เพิ่มเมนู '{new_name}' เรียบร้อยแล้ว!")
                    time.sleep(0.5)
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
                        save_topping_db(t_name.strip(), float(t_price))
                        st.cache_data.clear()
                        st.success(f"บันทึกท็อปปิ้ง '{t_name}' เรียบร้อย!")
                        time.sleep(0.5)
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

        # TAB 4: บันทึกรายจ่าย
        with tab_expense:
            st.write("💸 **ลงบันทึกรายจ่ายประจำวัน:**")
            exp_date = st.date_input("วันที่จ่าย", value=date.today(), key="exp_date_input")
            exp_title = st.text_input("รายการรายจ่าย (เช่น ค่าซื้อน้ำแข็ง, ค่าวัตถุดิบชา)", key="exp_title_input")
            exp_amount = st.number_input("จำนวนเงิน (บาท)", min_value=1.0, value=100.0, step=10.0, key="exp_amount_input")
            exp_note = st.text_input("หมายเหตุเพิ่มเติม (ถ้ามี)", key="exp_note_input")

            if st.button("💾 บันทึกรายจ่าย", use_container_width=True, key="btn_save_expense"):
                if exp_title.strip() != "":
                    add_expense(exp_date, exp_title.strip(), float(exp_amount), exp_note.strip(), st.session_state.username)
                    st.success(f"บันทึกรายจ่าย '{exp_title}' จำนวน {exp_amount:,.0f} บาท เรียบร้อย!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("กรุณากรอกชื่อรายการรายจ่าย")

        # TAB 5: จัดการสมาชิก
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
