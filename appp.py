import json
import os
import streamlit as st
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# --- 1. Pydantic Schema المطور لنظام Storm 4 ---
class GameState(BaseModel):
    is_created: bool = Field(default=False, description="هل تم إنشاء الشخصية؟")
    name: str = Field(description="اسم النينجا")
    rank: str = Field(description="الرتبة")
    village: str = Field(description="القرية أو الانتماء")
    era: str = Field(description="الحقبة الزمنية للقصة")
    location: str = Field(description="المكان الحالي")
    health: int = Field(default=100, description="الصحة من 0 إلى 100")
    chakra: int = Field(default=100, description="الشاكرا من 0 إلى 100")
    substitutions: int = Field(default=4, description="عدد شخطات الاستبدال المتبقية من 0 إلى 4")
    storm_gauge: int = Field(default=0, description="عداد الستورم من 0 إلى 100%")
    awakening_active: bool = Field(default=False, description="هل طور الصحوة مفعل؟")
    awakening_type: str = Field(description="نوع الصحوة: سوسانو، طور الكيوبي، تفجر البخار والمانغيكيو")
    ultimate_jutsu: str = Field(description="التقنية السرية الأسطورية (Ougi)")
    support_1: str = Field(description="المساعد الأول")
    support_2: str = Field(description="المساعد الثاني")
    jutsus: List[str] = Field(description="التقنيات الأساسية")
    inventory: List[str] = Field(description="الحقيبة والأدوات")
    story_log: List[str] = Field(description="سجل الأحداث")
    current_quest: str = Field(description="المهمة الحالية")
    active_enemy: str = Field(default="لا يوجد", description="اسم الخصم الحالي")
    enemy_health: int = Field(default=100, description="صحة الخصم من 0 إلى 100")
    combo_hits: int = Field(default=0, description="عدد ضربات الكومبو")

class GameResponse(BaseModel):
    story_narration: str = Field(description="الوصف السردي السينمائي بأسلوب Storm 4 Cutscene")
    updated_state: GameState = Field(description="حالة اللعبة المحدثة بالكامل")

STATE_FILE = "naruto_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"is_created": False}

def save_state(state_data: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)

def clamp(val: int, min_val: int = 0, max_val: int = 100) -> int:
    try:
        return max(min_val, min(max_val, int(val)))
    except Exception:
        return min_val

# --- 2. Streamlit HUD UI - Storm 4 Theme ---
st.set_page_config(page_title="Naruto Storm 4 RPG Engine", page_icon="💥", layout="wide")

STORM4_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@600;800;900&family=Orbitron:wght@700;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif !important;
        background-color: #040508 !important;
        color: #F1F5F9 !important;
    }
    
    .stApp {
        background: radial-gradient(circle at 50% 20%, #180828 0%, #030406 90%) !important;
    }
    
    /* Storm 4 Header Banner */
    .storm-header {
        background: linear-gradient(90deg, #990000 0%, #FF2A00 50%, #990000 100%);
        color: #FFFFFF;
        text-align: center;
        padding: 10px;
        font-size: 1.8rem;
        font-weight: 900;
        letter-spacing: 2px;
        text-shadow: 0 0 10px #FFD700, 0 0 20px #FF0000;
        border-bottom: 3px solid #FFD700;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    /* Sidebar Styling */
    div[data-testid="stSidebar"] {
        background: rgba(8, 10, 16, 0.95) !important;
        backdrop-filter: blur(16px);
        border-left: 2px solid #FF2A00 !important;
    }
    
    /* Buttons - Storm 4 Arcade Style */
    .stButton > button {
        background: linear-gradient(135deg, #1F102E 0%, #0A0512 100%) !important;
        color: #FFD700 !important;
        border: 1.5px solid #FF2A00 !important;
        border-radius: 6px !important;
        font-weight: 800 !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.2s ease-in-out !important;
        text-transform: uppercase;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #FF2A00 0%, #990000 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 20px rgba(255, 42, 0, 0.8) !important;
        transform: scale(1.03);
    }
    
    /* Substitution Stock Bars */
    .sub-bar {
        display: inline-block;
        width: 22px;
        height: 12px;
        margin: 2px;
        border-radius: 3px;
        border: 1px solid #00F0FF;
    }
    .sub-filled { background-color: #00F0FF; box-shadow: 0 0 8px #00F0FF; }
    .sub-empty { background-color: #1A202C; }
    
    /* Awakening Banner Glow */
    .awakening-banner {
        background: linear-gradient(90deg, #FF0055, #FF5500);
        color: white;
        padding: 8px;
        text-align: center;
        font-weight: bold;
        border-radius: 6px;
        animation: pulse 1.5s infinite alternate;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 10px #FF0055; }
        100% { box-shadow: 0 0 25px #FF5500; }
    }
    
    .stat-card-storm {
        background: rgba(15, 18, 30, 0.85);
        border: 1px solid rgba(255, 215, 0, 0.25);
        border-radius: 8px;
        padding: 10px;
        text-align: center;
    }
</style>
"""
st.markdown(STORM4_CSS, unsafe_allow_html=True)

if "game_state" not in st.session_state:
    st.session_state.game_state = load_state()

if "messages" not in st.session_state:
    st.session_state.messages = []

state = st.session_state.game_state

# --- 3. شاشة اختيار الشخصية والمساعدين والـ Ougi ---
if not state.get("is_created", False):
    st.markdown("<div class='storm-header'>💥 NARUTO SHIPPUDEN: STORM 4 RPG</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #FFD700;'>اختر نينجاك، المساعدين، والتقنية السرية للبدء بالمواجهة</p>", unsafe_allow_html=True)
    st.divider()
    
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        with st.form("storm_character_creator"):
            st.subheader("🥷 هوية النينجا والـ Ougi")
            char_name = st.text_input("اسم النينجا:", value="أوتشيها شتوي")
            village = st.selectbox("الانتماء / القرية:", [
                "كونوها (قرية الورق)", 
                "منظمة الأكاتسكي (Akatsuki)", 
                "كوموغاكوري (قرية السحاب)", 
                "سوناغاكوري (قرية الرمل)",
                "نينجا فار متمرد (Rogue Ninja)"
            ])
            era = st.selectbox("الحقبة الزمنية للنمط (Arc):", [
                "آرك غزو باين لكونوها - Pain's Assault Arc",
                "قمة الكاجي الخمسة - Five Kage Summit Arc",
                "حرب النينجا العظمى الرابعة - 4th Great Ninja War",
                "حقبة شيبودن الأولى - Early Shippuden"
            ])
            
            st.subheader("🔥 طراز القتال والصحوة (Awakening)")
            awakening_type = st.selectbox("نوع الصحوة الكبرى (Awakening Mode):", [
                "تفجر المانغيكيو والبرق المضغوط (Steam & Mangekyou Burst)",
                "السوسانو الكامل الجسد (Full-Body Susanoo)",
                "طور نمط الرداء الكيوبي (Nine-Tails Chakra Mode)",
                "طور الناسك الأسطوري (Sage Mode)"
            ])
            
            ultimate_jutsu = st.text_input("التقنية السرية الكبرى (Secret Technique / Ougi):", value="إبادة البخار والبرق العظمى: Dragon Steam Ougi")
            
            st.subheader("👥 فريق المساعدة (Team Support Ninjas)")
            support_1 = st.text_input("المساعد الأول (Support 1):", value="إيتاشي أوتشيها (هجومي)")
            support_2 = st.text_input("المساعد الثاني (Support 2):", value="كيسامي هوشيكاكي (دفاعي)")
            
            submit_btn = st.form_submit_button("🔥 دخول حلبة STORM 4")
            
            if submit_btn:
                new_state = {
                    "is_created": True,
                    "name": char_name,
                    "rank": "S-Rank Ninja",
                    "village": village,
                    "era": era,
                    "location": f"ميدان معركة {village}",
                    "health": 100,
                    "chakra": 100,
                    "substitutions": 4,
                    "storm_gauge": 0,
                    "awakening_active": False,
                    "awakening_type": awakening_type,
                    "ultimate_jutsu": ultimate_jutsu,
                    "support_1": support_1,
                    "support_2": support_2,
                    "jutsus": ["تنين البخار الحراري (Steam Dragon)", "البرق المضغوط (Chidori Stream)", "نسخ الظل (Shadow Clones)"],
                    "inventory": ["10 كوناي", "5 لفافات متفجرة", "2 حبوب شاكرا عظيمة"],
                    "story_log": [f"انطلقت المواجهة الملحمية في {era}."],
                    "current_quest": "تدمير قوات العدو وااختبار القوة السرية",
                    "active_enemy": "باين (Pain - Tendo)",
                    "enemy_health": 100,
                    "combo_hits": 0
                }
                st.session_state.game_state = new_state
                save_state(new_state)
                st.rerun()

    st.stop()

# --- 4. القائمة الجانبية (STORM 4 BATTLE HUD) ---
with st.sidebar:
    st.markdown("<h2 style='color: #FF2A00; text-align: center; font-family:Orbitron;'>STORM HUD</h2>", unsafe_allow_html=True)
    api_key = st.text_input("Gemini API Key:", type="password")
    
    st.divider()
    
    if state.get("awakening_active", False):
        st.markdown(f"<div class='awakening-banner'>🔥 AWAKENING ACTIVE: {state.get('awakening_type')}</div>", unsafe_allow_html=True)
        st.write("")

    st.markdown(f"### 🥷 {state.get('name')} <span style='font-size:0.8rem; color:#FFD700;'>[{state.get('village')}]</span>", unsafe_allow_html=True)
    st.caption(f"📍 **الميدان:** {state.get('location')}")
    st.caption(f"👥 **المساعدين:** {state.get('support_1')} | {state.get('support_2')}")
    
    st.markdown("---")
    
    health_val = clamp(state.get("health", 100))
    chakra_val = clamp(state.get("chakra", 100))
    sub_val = clamp(state.get("substitutions", 4), 0, 4)
    storm_val = clamp(state.get("storm_gauge", 0))
    
    # شريط الدم والشاكرا
    st.markdown(f"**❤️ HEALTH BAR ({health_val}%):**")
    st.progress(health_val / 100)
    
    st.markdown(f"**💙 CHAKRA GAUGE ({chakra_val}%):**")
    st.progress(chakra_val / 100)
    
    # مؤشر الكاوريمي (Substitutions Gauge - 4 Bars)
    sub_html = "<b>🛡️ SUBSTITUTIONS:</b><br>"
    for i in range(4):
        if i < sub_val:
            sub_html += "<span class='sub-bar sub-filled'></span>"
        else:
            sub_html += "<span class='sub-bar sub-empty'></span>"
    st.markdown(sub_html, unsafe_allow_html=True)
    st.write("")
    
    # شريط Storm Gauge للضربة الجماعية
    st.markdown(f"**⚡ STORM GAUGE ({storm_val}%):**")
    st.progress(storm_val / 100)
    
    st.markdown("---")
    
    # زر تعبئة الشاكرا المباشر (Chakra Charge)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("⚡ SHIFT/CHARGE CHAKRA"):
            state["chakra"] = clamp(state["chakra"] + 45)
            state["story_log"].append("شحنت الشاكرا الخاصة بك بأسلوب خاطف (+45%).")
            save_state(state)
            st.rerun()
            
    with col_c2:
        # زر تفعيل الصحوة عند تحقّق الشرط
        if health_val <= 40 or storm_val >= 80:
            if st.button("🔥 AWAKEN!"):
                state["awakening_active"] = not state.get("awakening_active", False)
                state["story_log"].append(f"تم تفعيل طور الصحوة الكبرى: ({state.get('awakening_type')})!")
                save_state(state)
                st.rerun()

    st.divider()
    
    with st.expander("💾 إدارة الحفظ وإعادة الضبط"):
        json_str = json.dumps(state, ensure_ascii=False, indent=2)
        st.download_button("📥 تصدير الحفظ (JSON)", json_str, f"storm_save_{state.get('name')}.json", "application/json")
        
        uploaded_file = st.file_uploader("📤 استرجاع حفظ:", type=["json"])
        if uploaded_file:
            try:
                loaded = json.load(uploaded_file)
                if loaded.get("is_created"):
                    st.session_state.game_state = loaded
                    save_state(loaded)
                    st.success("تم استرجاع المواجهة!")
                    st.rerun()
            except Exception:
                st.error("ملف غير صالح")
                
        if st.button("🗑️ تصفير وإعادة تشغيل المباراة"):
            st.session_state.game_state = {"is_created": False}
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)
            st.session_state.messages = []
            st.rerun()

# --- 5. حلبة المعركة الرئيسية (STORM BATTLEFIELD) ---
tab_battle, tab_team, tab_log = st.tabs(["⚔️ حلبة المعركة (Battleground)", "👥 الفريق والـ Ougi", "📖 سجل المعركة (Battle Log)"])

with tab_battle:
    # شريط مواجهة الخصم (VS BAR)
    col_v1, col_v2, col_v3 = st.columns([2, 1, 2])
    with col_v1:
        st.markdown(f"<div class='stat-card-storm'><h3 style='color:#00F0FF; margin:0;'>{state.get('name')}</h3><p style='margin:0;'>HP: {health_val}% | Chakra: {chakra_val}%</p></div>", unsafe_allow_html=True)
    with col_v2:
        st.markdown("<h2 style='text-align:center; color:#FF2A00; font-family:Orbitron; margin:0;'>VS</h2>", unsafe_allow_html=True)
    with col_v3:
        st.markdown(f"<div class='stat-card-storm'><h3 style='color:#FF2A00; margin:0;'>{state.get('active_enemy')}</h3><p style='margin:0;'>HP: {state.get('enemy_health', 100)}%</p></div>", unsafe_allow_html=True)

    st.write("")

    # عرض الحوارات والمشاهد القصصية
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # لوحة أزرار Storm 4 Arcade Controller
    st.markdown("---")
    st.markdown("#### 🎮 لوحة تحكم أزرار المعركة (STORM CONTROLLER)")
    
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    action_prompt = None

    with b_col1:
        selected_jutsu = st.selectbox("🌀 اختر النينجوتسو:", state.get("jutsus", []))
        if st.button("💥 إطلاق النينجوتسو"):
            action_prompt = f"أنفذ حركة النينجوتسو: ({selected_jutsu}) مع توجيه ضربات كومبو خاطفة!"

    with b_col2:
        if st.button("💥 OUGI (التقنية السرية)"):
            if chakra_val >= 60:
                action_prompt = f"أفعل التقنية السرية الكبرى (ULTIMATE JUTSU / 奥義): ({state.get('ultimate_jutsu')}) لإبادة الخصم بشرارة سينمائية!"
            else:
                st.warning("الشاكرا غير كافية للـ Ougi! (تحتاج 60%+)")

    with b_col3:
        if st.button(f"👥 استدعاء المساعد ({state.get('support_1').split(' ')[0]})"):
            action_prompt = f"أستدعي المساعد الأول ({state.get('support_1')}) لتنفيذ ضربة مساعدة مباغتة وتجميع الـ Storm Gauge!"
        if st.button(f"👥 استدعاء المساعد ({state.get('support_2').split(' ')[0]})"):
            action_prompt = f"أستدعي المساعد الثاني ({state.get('support_2')}) للتغطية الدفاعية وضرب الخصم!"

    with b_col4:
        if st.button("🛡️ KAWARIMI (استبدال)"):
            if sub_val > 0:
                state["substitutions"] -= 1
                action_prompt = "أستخدم شخطه استبدال (Substitution Kawarimi) للظهور خلف الخصم ومباغتته!"
                save_state(state)
            else:
                st.error("نفدت شخطات الاستبدال! لا يمكنك التفادي الآن!")

    chat_input = st.chat_input("أو اكتب حركتك القتالية السينمائية هنا...")
    final_input = action_prompt or chat_input

    if final_input:
        if not api_key:
            st.error("أدخل Gemini API Key في القائمة الجانبية أولاً!")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": final_input})
        with st.chat_message("user"):
            st.markdown(final_input)

        client = genai.Client(api_key=api_key)

        contents = []
        for m in st.session_state.messages[-10:]:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))

        system_instruction = f"""
أنت Game Master ومحرك معارك لعبة NARUTO SHIPPUDEN: ULTIMATE NINJA STORM 4.
مهمتك كتابة وصف سينمائي حماسي خاطف شروى أسلوب اللعبة (Cutscenes, Secret Factor, Combo Hits).

بيانات حالة المباراة المسجلة بـ Database:
{json.dumps(st.session_state.game_state, ensure_ascii=False)}

القواعد الصارمة:
1. إرجاع الرد بتركيبة JSON تطابق Schema المحددة حصراً.
2. إذا استخدم اللاعب Ougi (التقنية السرية)، اوصف المشهد بأسلوب قطع سينمائي وإلحاق ضرر عالي بالخصم (`enemy_health`).
3. تجديد شخطات الاستبدال `substitutions` بالتدريج إذا كانت أقل من 4.
4. خصم الشاكرا والدم بدقة وإرجاع عدد ضربات الكومبو بـ `combo_hits`.
"""

        with st.chat_message("assistant"):
            with st.spinner("جاري معالجة ضربات المعركة وإخراج المشهد السينمائي..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                            response_mime_type="application/json",
                            response_schema=GameResponse,
                        )
                    )
                    
                    game_res = GameResponse.model_validate_json(response.text)
                    
                    new_state = game_res.updated_state.model_dump()
                    new_state["health"] = clamp(new_state["health"])
                    new_state["chakra"] = clamp(new_state["chakra"])
                    new_state["substitutions"] = clamp(new_state["substitutions"], 0, 4)
                    
                    st.session_state.game_state = new_state
                    save_state(new_state)
                    
                    story_text = game_res.story_narration
                    st.markdown(story_text)
                    st.session_state.messages.append({"role": "assistant", "content": story_text})
                    st.rerun()

                except Exception as e:
                    st.error(f"حدث خطأ أثناء معالجة القتال: {str(e)}")

with tab_team:
    st.markdown("### 💥 تفاصيل الفريق والـ Ougi")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown(f"<div class='stat-card-storm'><h4>💥 التقنية السرية (Ougi)</h4><p style='color:#FFD700; font-size:1.2rem;'>{state.get('ultimate_jutsu')}</p></div>", unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**🔥 طور الصحوة المتاح:** {state.get('awakening_type')}")
    with col_t2:
        st.markdown(f"<div class='stat-card-storm'><h4>👥 أعضاء الفريق المساعد</h4><p>{state.get('support_1')}<br>{state.get('support_2')}</p></div>", unsafe_allow_html=True)

with tab_log:
    st.markdown("### 📖 سجل المعركة والأحداث")
    st.info(f"🎯 **المهمة:** {state.get('current_quest')}")
    st.divider()
    for log in state.get("story_log", []):
        st.markdown(f"• {log}")
        