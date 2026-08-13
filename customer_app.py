import streamlit as st
import psycopg2
import json

# ตั้งค่าหน้าตาแอปให้เหมาะกับมือถือ
st.set_page_config(page_title="สั่งเครื่องดื่ม - ชานมมาจิเมะ", page_icon="🧋", layout="centered")

# เชื่อมต่อ Database (ดึงค่าจาก Streamlit Secrets)
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

# ฐานข้อมูลเมนูทั้งหมดจากรูปภาพ (แยกตามหมวดหมู่)
MENU_DATA = {
    "🥤 เมนูปั่น": [
        {"name": "ชาแดงปั่น", "price": 35, "cost": 14.72},
        {"name": "ชาเขียวปั่น", "price": 35, "cost": 15.73},
        {"name": "ชาไต้หวันปั่น", "price": 35, "cost": 13.04},
        {"name": "ชานมโกโก้ปั่น", "price": 35, "cost": 15.07},
        {"name": "ชานมกาแฟปั่น", "price": 35, "cost": 16.33},
        {"name": "ชานมอโอวัลตินปั่น", "price": 35, "cost": 13.94},
        {"name": "ชานมน้ำผึ้งปั่น", "price": 35, "cost": 17.58},
        {"name": "ชานมลิ้นจี่ปั่น", "price": 35, "cost": 15.69},
        {"name": "ชานมแอปเปิ้ลปั่น", "price": 35, "cost": 15.69},
        {"name": "ชานมแคนตาลูปปั่น", "price": 35, "cost": 15.69},
        {"name": "ชานมสตรอเบอร์รี่ปั่น", "price": 35, "cost": 15.69},
        {"name": "โกโก้ปั่น", "price": 35, "cost": 18.16},
        {"name": "เนสกาแฟปั่น", "price": 45, "cost": 21.94},
        {"name": "โอวัลตินปั่น", "price": 35, "cost": 14.77},
        {"name": "นมชมพูปั่น", "price": 35, "cost": 14.06},
        {"name": "นมสดปั่น", "price": 35, "cost": 18.35},
        {"name": "วานิลลานมสดปั่น", "price": 45, "cost": 25.19},
        {"name": "คาราเมลนมสดปั่น", "price": 45, "cost": 25.19},
        {"name": "นมสดน้ำผึ้งปั่น", "price": 45, "cost": 23.43},
        {"name": "นมสดบราวน์ชูการ์ปั่น", "price": 45, "cost": 20.58},
        {"name": "ชาไต้หวันบราวน์ชูการ์ปั่น", "price": 45, "cost": 14.88},
        {"name": "มัทฉะนมสดปั่น", "price": 55, "cost": 30.66},
        {"name": "มะพร้าวนมสดปั่น", "price": 35, "cost": 17.17},
        {"name": "มันม่วงนมสดปั่น", "price": 45, "cost": 18.13},
        {"name": "ผงสตรอเบอร์รี่ปั่น", "price": 35, "cost": 14.94},
        {"name": "ผงแคนตาลูปปั่น", "price": 35, "cost": 14.77},
        {"name": "ผงกล้วยปั่น", "price": 35, "cost": 14.77},
        {"name": "ผงเผือกปั่น", "price": 35, "cost": 15.25},
    ],
    "🍵 ชานม / ชาผลไม้": [
        {"name": "ชาไต้หวัน", "price": 19, "cost": 11.12},
        {"name": "ชาผลไม้", "price": 25, "cost": 11.89},
        {"name": "ชานมโกโก้", "price": 25, "cost": 12.13},
        {"name": "ชานมกาแฟ", "price": 25, "cost": 12.76},
        {"name": "ชานมอโอวัลติน", "price": 25, "cost": 11.57},
        {"name": "ชานมคาราเมล", "price": 30, "cost": 14.03},
        {"name": "ชานมวานิลา", "price": 30, "cost": 14.03},
        {"name": "ชานมน้ำผึ้ง", "price": 25, "cost": 13.15},
        {"name": "ชานมไต้หวันบราวน์ชูการ์", "price": 25, "cost": 11.96},
        {"name": "ชานมเผือก", "price": 25, "cost": 13.20},
        {"name": "ชาผลไม้ใส", "price": 19, "cost": 8.03},
        {"name": "ชาเย็น (ชานมไทย)", "price": 25, "cost": 11.58},
        {"name": "ชาเขียว (ชาเขียวนม)", "price": 25, "cost": 12.38},
        {"name": "ชาเขียวน้ำผึ้งมะนาว", "price": 25, "cost": 12.11},
        {"name": "ชาแดงน้ำผึ้งมะนาว", "price": 25, "cost": 11.31},
        {"name": "น้ำผึ้งมะนาว", "price": 19, "cost": 10.07},
    ],
    "☕ ชาใส / กาแฟ / นมสด / โซดา": [
        {"name": "ชาดำเย็น", "price": 19, "cost": 6.61},
        {"name": "ชามะนาว", "price": 19, "cost": 7.65},
        {"name": "ชาเขียวมะนาว", "price": 19, "cost": 8.45},
        {"name": "ชาเขียวใส", "price": 19, "cost": 7.41},
        {"name": "โอเลี้ยง", "price": 19, "cost": 6.07},
        {"name": "โกโก้", "price": 25, "cost": 13.11},
        {"name": "โอวัลติน", "price": 25, "cost": 10.85},
        {"name": "เนสกาแฟ", "price": 30, "cost": 15.63},
        {"name": "กาแฟโบราณ", "price": 25, "cost": 10.51},
        {"name": "นมชมพู", "price": 25, "cost": 10.87},
        {"name": "ผลไม้โซดา", "price": 19, "cost": 10.47},
        {"name": "น้ำแดงโซดา", "price": 19, "cost": 10.88},
        {"name": "แดงมะนาวโซดา", "price": 25, "cost": 11.92},
        {"name": "มะนาวโซดา", "price": 19, "cost": 9.85},
        {"name": "นมสดบราวน์ชูการ์", "price": 25, "cost": 11.20},
        {"name": "นมสดไวท์ชอค", "price": 25, "cost": 12.07},
        {"name": "นมสดคาราเมล", "price": 30, "cost": 14.55},
        {"name": "นมสดวานิลา", "price": 30, "cost": 14.55},
        {"name": "นมสดน้ำผึ้ง", "price": 25, "cost": 13.67},
        {"name": "โยเกิร์ตผลไม้", "price": 25, "cost": 11.36},
        {"name": "มันม่วงนมสด", "price": 25, "cost": 13.76},
        {"name": "มะพร้าวนมสด", "price": 25, "cost": 12.76},
        {"name": "สตรอเบอร์รี่นมสด", "price": 25, "cost": 11.49},
        {"name": "เผือกนมสด", "price": 25, "cost": 11.49},
        {"name": "กล้วยนมสด", "price": 25, "cost": 11.49},
        {"name": "แคนตาลูปนมสด", "price": 25, "cost": 11.49},
        {"name": "ชอคโกแลตนมสด", "price": 25, "cost": 14.64},
    ]
}

# --- เริ่มการแสดงผล UI บนมือถือ ---
st.title("🧋 ชานมมาจิเมะ")
st.write("ยินดีต้อนรับครับ เลือกเมนูอร่อยๆ ได้เลย!")

table_no = st.selectbox("📌 เลือกหมายเลขโต๊ะ / รูปแบบ", ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "ทานที่ร้าน", "กลับบ้าน"])

if "cart" not in st.session_state:
    st.session_state.cart = []

# แท็บแยกหมวดหมู่เมนู
tabs = st.tabs(list(MENU_DATA.keys()))

for idx, category in enumerate(MENU_DATA.keys()):
    with tabs[idx]:
        for item in MENU_DATA[category]:
            with st.container(border=True):
                col1, col2 = st.columns([2.5, 1.5])
                col1.subheader(item["name"])
                col1.write(f"💰 ราคา: **{item['price']} บาท**")
                
                # ตัวเลือกเพิ่มไข่มุก (+4 บาท จากราคาท็อปปิ้งในตาราง)
                add_boba = col2.checkbox("เพิ่มไข่มุก (+4฿)", key=f"boba_{item['name']}")
                
                if col2.button("➕ สั่งเมนูนี้", key=f"btn_{item['name']}"):
                    final_price = item["price"] + (4 if add_boba else 0)
                    boba_text = " (เพิ่มไข่มุก)" if add_boba else ""
                    
                    st.session_state.cart.append({
                        "name": f"{item['name']}{boba_text}",
                        "price": final_price,
                        "cost": item["cost"] # ส่งต้นทุนไปด้วยเพื่อให้หลังบ้านคำนวณกำไรได้ทันที!
                    })
                    st.toast(f"เพิ่ม {item['name']} แล้ว!", icon="✅")

# --- แสดงรายการในตะกร้าสินค้า ---
if st.session_state.cart:
    st.divider()
    st.subheader("🛒 สรุปรายการที่สั่ง")
    
    total_price = sum(i["price"] for i in st.session_state.cart)
    total_cost = sum(i["cost"] for i in st.session_state.cart)
    
    for i, c in enumerate(st.session_state.cart):
        st.write(f"{i+1}. **{c['name']}** — {c['price']} บาท")
        
    st.markdown(f"### **ราคารวมทั้งสิ้น: {total_price} บาท**")
    
    if st.button("🚀 ยืนยันส่งออเดอร์เข้าครัว", type="primary", use_container_width=True):
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # บันทึกข้อมูลรายการสั่งซื้อ, ราคารวม, และต้นทุนรวม ลงตาราง orders
            cur.execute(
                """
                INSERT INTO orders (table_number, items_json, total_price, total_cost, status) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (table_no, json.dumps(st.session_state.cart), total_price, total_cost, 'pending')
            )
            conn.commit()
            cur.close()
            conn.close()
            
            st.session_state.cart = []
            st.balloons()
            st.success("ส่งออเดอร์เรียบร้อยแล้ว! กำลังจัดเตรียมเครื่องดื่มให้ครับ")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการส่งออเดอร์: {e}")