import streamlit as st
import google.generativeai as genai
import PyPDF2
import time
import json
import requests
from datetime import datetime, date
import io
from gtts import gTTS  
import random
import pymongo
import certifi
import streamlit.components.v1 as components
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from twilio.rest import Client

# ==========================================
# DATABASE & CLOUD CONFIGURATION
# ==========================================
MONGO_URI = "mongodb+srv://vishalvichu1901_db_user:ac47EdljYKLGdN98@cluster0.6csfjdi.mongodb.net/?appName=Cluster0"

@st.cache_resource
def init_connection():
    return pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())

try:
    client = init_connection()
    db = client["VibeLearnDB"]
    
    users_collection = db["UserProfiles"] 
    modules_collection = db["StudyModules"]
    duels_collection = db["PeerSyncDuels"]
    rooms_collection = db["VibeRooms"]
    # MongoDB success popup removed as requested
except Exception as e:
    st.error(f"Database connection failed: {e}")

# Helper: Aura Points Updater
def update_aura(points):
    st.session_state.aura_points += points
    try:
        users_collection.update_one(
            {"full_name": st.session_state.username}, 
            {"$set": {"aura_points": st.session_state.aura_points}}
        )
    except: pass

# Helper: Dynamic Time Greeting
def get_greeting():
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good Morning"
    elif 12 <= current_hour < 17:
        return "Good Afternoon"
    elif 17 <= current_hour < 21:
        return "Good Evening"
    else:
        return "Good Night"

# --- Twilio TURN Server Connection Function ---
@st.cache_data
def get_ice_servers():
    try:
        # Tries to fetch from secrets
        account_sid = st.secrets.get("TWILIO_ACCOUNT_SID", "")
        auth_token = st.secrets.get("TWILIO_AUTH_TOKEN", "")
        if account_sid and auth_token:
            twilio_client = Client(account_sid, auth_token)
            token = twilio_client.tokens.create()
            return token.ice_servers
        else:
            return [{"urls": ["stun:stun.l.google.com:19302"]}]
    except Exception:
        # Fallback to free Google STUN server
        return [{"urls": ["stun:stun.l.google.com:19302"]}]

# 1. Page Config
st.set_page_config(page_title="Vibe Learn | Dashboard", page_icon="✨", layout="wide")

# ==========================================
# UI DESIGN CSS INJECTION (PREMIUM SAAS & GLASSMORPHISM)
# ==========================================
st.markdown("""
    <style>
        /* 1. Import Google Fonts (Poppins & Inter) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700&display=swap');

        /* 2. Hide Streamlit Defaults for Clean UI */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* 3. Global Font Settings */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Poppins', sans-serif !important;
            letter-spacing: -0.5px;
        }

        /* 4. Modern Buttons with 3D Hover & Selective Glow Effect */
        .stButton>button {
            border-radius: 12px !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            background: #111B2E !important;
            color: #F8FAFC !important;
        }
        .stButton>button:hover {
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 8px 20px rgba(77, 156, 255, 0.2) !important; 
            border-color: #4D9CFF !important;
        }
        
        /* Primary Button Style */
        .stButton>button[kind="primary"] {
            background: linear-gradient(135deg, #4D9CFF 0%, #8B5CF6 100%) !important;
            border: none !important;
        }
        .stButton>button[kind="primary"]:hover {
            box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4) !important;
        }

        /* 5. Inputs & Text Areas - Smooth Rounded Corners */
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {
            border-radius: 10px !important;
            border: 1px solid #1e293b !important;
            background-color: #0B1220 !important;
            color: #F8FAFC !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        /* 6. Feature Box (Container) Styling - GLASSMORPHISM */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px !important;
            background: rgba(17, 27, 46, 0.6) !important; /* Slight transparency */
            backdrop-filter: blur(12px) !important; /* Blur effect */
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important; /* Soft border */
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1) !important;
            transition: all 0.3s ease !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(77, 156, 255, 0.4) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2) !important;
        }

        /* 7. Aura Pill Shape Custom Class */
        .aura-pill {
            background: linear-gradient(90deg, rgba(245,158,11,0.2) 0%, rgba(245,158,11,0.05) 100%);
            border: 1px solid rgba(245,158,11,0.5);
            color: #F59E0B;
            padding: 4px 16px;
            border-radius: 50px;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 1.1rem;
            display: inline-block;
            box-shadow: 0 0 10px rgba(245,158,11,0.2);
        }
    </style>
""", unsafe_allow_html=True)

# 2. Setup API Keys
# 2. Setup API Keys
# 2. Setup API Keys
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
CURRENTS_API_KEY = st.secrets["CURRENTS_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name='gemini-flash-latest')

# CURRENTS NEWS API FUNCTION
def get_currents_news(query):
    if CURRENTS_API_KEY == "YOUR_CURRENTS_API_KEY" or not CURRENTS_API_KEY.strip():
        return "⚠️ News API Key not configured. Please add your Currents API key in the code."
    
    clean_query = query.lower()
    clean_query = clean_query.replace("cm", "Chief Minister").replace("tn", "Tamil Nadu").replace("pm", "Prime Minister")
    
    url = f"https://api.currentsapi.services/v1/search?keywords={clean_query}&language=en&apiKey={CURRENTS_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        
        if "news" in data and len(data["news"]) > 0:
            news_summary = "Live News Data from Currents API:\n"
            for article in data["news"][:3]:  # Top 3 articles
                news_summary += f"- Title: {article['title']}\n  Summary: {article['description']}\n  Author/Source: {article.get('author', 'News Desk')}\n  Date: {article.get('published', 'Recent')}\n"
            return news_summary
        else:
            return "No recent news found for this specific topic."
    except Exception as e:
        return f"News API error: {e}"

# 3. Session States
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'aura_points' not in st.session_state: st.session_state.aura_points = 0
if 'messages' not in st.session_state: st.session_state.messages = []
if 'audio_messages' not in st.session_state: st.session_state.audio_messages = []
if 'active_feature' not in st.session_state: st.session_state.active_feature = None 

# PeerSync Multiplayer Session States
if 'duel_room_id' not in st.session_state: st.session_state.duel_room_id = None

# Chronos Adaptive Scheduler Session States
if 'chronos_schedule' not in st.session_state: st.session_state.chronos_schedule = ""

# Vibe Room Session States
if 'current_vibe_room' not in st.session_state: st.session_state.current_vibe_room = None

# GLOBAL CURRENT AFFAIRS DETECTION KEYWORDS
NEWS_KEYWORDS = [
    "current", "latest", "today", "now", "recently", "who is", "currently", "present", "live",
    "cm", "pm", "chief minister", "prime minister", "president", "governor", "minister", "ceo", "chairman",
    "news", "breaking", "election", "sports", "rankings", "stock", "crypto", "weather",
    "scores", "ongoing", "affairs", "trending", "update"
]

# ==========================================
# LOGIN GATEWAY (MODULE 1: USER PROFILES DB)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #4D9CFF;'> Vibe Learn !</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8;'>AI that matches your vibe. Learning that sticks.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("### 🔐 Secure User Login")
        with st.form("login_form"):
            name_input = st.text_input("Full Name:")
            email_input = st.text_input("Email ID:")
            password_input = st.text_input("Password:", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Get Started", use_container_width=True):
                if name_input.strip() and email_input.strip() and password_input.strip():
                    try:
                        existing_user = users_collection.find_one({"email": email_input.strip()})
                        
                        if existing_user:
                            st.session_state.username = existing_user['full_name']
                            st.session_state.aura_points = existing_user.get('aura_points', 100)
                            st.session_state.logged_in = True
                            st.success(f"Welcome back, {existing_user['full_name']}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            new_user = {
                                "full_name": name_input.strip(),
                                "email": email_input.strip(),
                                "password": password_input.strip(),
                                "role": "Student",
                                "aura_points": 100,
                                "duel_invites": [],
                                "quiz_history": [],
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            users_collection.insert_one(new_user)
                            
                            st.session_state.username = name_input.strip()
                            st.session_state.aura_points = 100
                            st.session_state.logged_in = True
                            st.success("Account created and saved to Cloud Database! 🎉")
                            time.sleep(1)
                            st.rerun()
                    except Exception as db_err:
                        st.error(f"Database error during login: {db_err}")
                else:
                    st.warning("Please fill in all fields.")
    st.stop()

# ==========================================
# MAIN DASHBOARD 
# ==========================================
if st.session_state.active_feature is None:
    # Pill and dynamic greeting applied here!
    greeting_message = get_greeting()
    st.markdown(f"<h3 style='text-align: center;'> {greeting_message}, {st.session_state.username}! 👋 <br><br><span class='aura-pill'>⚡ {st.session_state.aura_points} AURA</span></h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8;'>Ready to continue learning?</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_left, col_center, col_right = st.columns([1, 2, 1.5])
    
    with col_center:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #4D9CFF;'>📝 AI Notes Generator</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94A3B8;'>Generate smart notes from your study material.</p>", unsafe_allow_html=True)
            if st.button("Open AI Notes →", use_container_width=True, type="primary"):
                st.session_state.active_feature = "ai_notes"
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True) 
        
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #8B5CF6;'>🎮 PeerSync Duels</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94A3B8;'>Synchronous multiplayer quiz battle with AI referee.</p>", unsafe_allow_html=True)
            if st.button("Open PeerSync →", use_container_width=True, type="primary"):
                st.session_state.active_feature = "peersync"
                st.session_state.duel_room_id = None
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True) 
        
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #22D3EE;'>⏳ Chronos Scheduler</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94A3B8;'>Spaced repetition & dynamic micro-task planning.</p>", unsafe_allow_html=True)
            if st.button("Open Chronos →", use_container_width=True, type="primary"):
                st.session_state.active_feature = "chronos"
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True) 
        
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #A78BFA;'>🎙️ AI Audio Notes</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94A3B8;'>Talk through mic, listen to AI generated audio scripts.</p>", unsafe_allow_html=True)
            if st.button("Open Audio Notes →", use_container_width=True, type="primary"):
                st.session_state.active_feature = "audio_notes"
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True) 
        
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #22C55E;'>🏠 Vibe Room</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94A3B8;'>Live shared notes & WebRTC group study collaboration.</p>", unsafe_allow_html=True)
            if st.button("Enter Vibe Room →", use_container_width=True, type="primary"):
                st.session_state.active_feature = "vibe_room"
                st.rerun()
                
    with col_right:
        st.markdown("<h3 style='text-align: center; color: #F59E0B;'>🏆 Top Scholars</h3>", unsafe_allow_html=True)
        with st.container(border=True):
            try:
                top_users = users_collection.find({}, {"full_name": 1, "aura_points": 1, "_id": 0}).sort("aura_points", -1).limit(5)
                rank = 1
                medals = {1: "🥇", 2: "🥈", 3: "🥉", 4: "🏅", 5: "🏅"}
                for user in top_users:
                    medal = medals.get(rank, "🏅")
                    name = user.get("full_name", "Unknown")
                    points = user.get("aura_points", 0)
                    if name == st.session_state.username:
                        st.markdown(f"**{medal} <span style='color:#4D9CFF;'>{name} (You)</span>** - `{points} AP`", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{medal} {name}** - `{points} AP`")
                    rank += 1
                    st.divider()
            except Exception as e:
                st.write("Leaderboard updating...")
                
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    _, logout_center, _ = st.columns([2, 1, 2])
    with logout_center:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.active_feature = None
            st.session_state.current_vibe_room = None
            st.session_state.messages = []
            st.session_state.audio_messages = []
            st.rerun()

# ==========================================
# FEATURE 1: AI NOTES GENERATOR
# ==========================================
elif st.session_state.active_feature == "ai_notes":
    
    with st.sidebar:
        if st.button("⬅ Dashboard", type="primary", use_container_width=True):
            st.session_state.active_feature = None
            st.rerun()
        st.divider()
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"<span class='aura-pill'>⚡ {st.session_state.aura_points} AP</span>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # New Chat & Clear Chat Controls
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("➕ New Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        with col_c2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
                
        # Search History functionality
        search_query = st.text_input("🔍 Search History", placeholder="Search topics...")
        st.markdown("### 🕒 Chat History")
        try:
            query = {"module_type": "AI_Notes", "user_id": st.session_state.username}
            if search_query.strip():
                query["topic"] = {"$regex": search_query, "$options": "i"}
                
            # Changed to sort by pinned first, then by created_at
            recent_chats = list(modules_collection.find(query).sort([("is_pinned", -1), ("created_at", -1)]).limit(8))
            
            for doc in recent_chats:
                title = doc.get("topic", "Study Topic")[:18]
                is_pinned = doc.get("is_pinned", False)
                pin_icon = "📌" if is_pinned else "📍"
                
                hc1, hc2, hc3 = st.columns([0.65, 0.175, 0.175])
                with hc1:
                    if st.button(f"💬 {title}", key=f"hist_{doc['_id']}", use_container_width=True):
                        st.session_state.messages = [
                            {"role": "user", "content": doc.get("topic", "")},
                            {"role": "assistant", "content": doc.get("generated_notes", "")}
                        ]
                        st.rerun()
                with hc2:
                    if st.button(pin_icon, key=f"pin_{doc['_id']}", use_container_width=True, help="Pin/Unpin"):
                        modules_collection.update_one({"_id": doc['_id']}, {"$set": {"is_pinned": not is_pinned}})
                        st.rerun()
                with hc3:
                    if st.button("🗑️", key=f"del_{doc['_id']}", use_container_width=True, help="Delete"):
                        modules_collection.delete_one({"_id": doc['_id']})
                        st.rerun()
        except:
            st.caption("No history found.")

    st.markdown(f"<h2 style='color: #4D9CFF;'>🧠 AI NOTES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Your intelligent study companion. Upload PDFs or ask questions directly.</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Render Chat Messages with Like, Dislike, and Copy Buttons
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                c1, c2, c3, _ = st.columns([0.6, 0.6, 0.8, 6])
                with c1:
                    if st.button("👍", key=f"like_{idx}", help="Helpful"):
                        st.toast("Thanks for your feedback! 👍")
                with c2:
                    if st.button("👎", key=f"dislike_{idx}", help="Not helpful"):
                        st.toast("Feedback recorded! We'll improve.")
                with c3:
                    if st.button("📋 Copy", key=f"copy_{idx}", help="Copy response"):
                        st.toast("Notes ready to select and copy from text!")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("chat_form_1", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 6, 2])
        with c1:
            uploaded_file = st.file_uploader("Upload", type=["pdf", "txt", "png", "jpg"], label_visibility="collapsed", key="file_1")
        with c2:
            prompt = st.text_input("Message", placeholder="Type a topic or upload a file...", label_visibility="collapsed")
        with c3:
            submitted = st.form_submit_button("Generate Notes 🚀", use_container_width=True)

    if submitted and (prompt or uploaded_file):
        actual_prompt = prompt if prompt else "Please analyze and summarize the attached document."
        
        file_text = ""
        file_name = "None"
        if uploaded_file is not None:
            file_name = uploaded_file.name
            if uploaded_file.type == "application/pdf":
                try:
                    reader = PyPDF2.PdfReader(uploaded_file)
                    for page in reader.pages:
                        file_text += page.extract_text() or ""
                except: pass
            else:
                file_text = uploaded_file.read().decode("utf-8", errors="ignore")

        # AUTO-DETECT LOGIC
        query_lower = actual_prompt.lower()
        requires_news = any(keyword in query_lower for keyword in NEWS_KEYWORDS)

        full_query = f"{actual_prompt}\n{file_text}"
        display_msg = actual_prompt
        if uploaded_file: display_msg += f" *(📎 Attached: {uploaded_file.name})*"
        if requires_news: display_msg += " *(🌐 Auto-Fetched Live News)*"
        
        st.session_state.messages.append({"role": "user", "content": display_msg})
        with st.chat_message("user"): st.markdown(display_msg)

        with st.chat_message("assistant"):
            status_message = "Gemini is thinking and fetching live news..." if requires_news else "Gemini is thinking..."
            
            with st.spinner(status_message):
                live_context = ""
                if requires_news:
                    live_context = get_currents_news(actual_prompt)

                chat_history = ""
                for msg in st.session_state.messages[-7:-1]:
                    speaker = "User" if msg["role"] == "user" else "AI"
                    chat_history += f"{speaker}: {msg['content']}\n"

                ai_prompt = f"""You are 'Vibe Learn', an AI-powered Study Assistant designed to help students learn effectively. Your primary goal is to provide accurate, clear, structured, and student-friendly responses.

                PREVIOUS CHAT HISTORY:
                {chat_history}
                
                [LIVE NEWS CONTEXT - ONLY IF APPLICABLE]
                {live_context}

                CURRENT USER INPUT / CONTEXT:
                "{full_query}"

                --- 
                CRITICAL BEHAVIORAL EXCEPTION FOR CASUAL CHAT:
                If the user input is a casual greeting, conversational text, or Tanglish (like 'hi', 'how are u', 'saptiya', 'what are you doing'), respond naturally, warmly, and briefly (in 1-2 lines) as a friend. Do NOT generate study notes or apply the academic rules below for simple greetings. If they use Tanglish, you can reply in Tanglish.
                ---

                # AI Study Assistant - System Rules for Responding

                ## General Behavior
                - Always understand the user's intent before answering.
                - Answer directly without unnecessary introductions.
                - Use simple and easy-to-understand language unless the user requests advanced explanations.
                - Adapt explanations to the user's knowledge level (Beginner, Intermediate, Advanced).
                - Keep responses concise by default and provide detailed explanations only when requested.
                - Be polite, professional, and encouraging.
                - Never make assumptions about missing information.
                - If essential details are missing, ask concise follow-up questions.
                - Never repeat information already explained unless the user requests it.

                ## Accuracy & Reliability
                - Never invent facts, statistics, references, URLs, quotes, or research papers.
                - If you are uncertain, clearly state that you are not certain instead of guessing.
                - Distinguish between facts, assumptions, and opinions.
                - Prioritize correctness over sounding confident.
                - Avoid misinformation and hallucinations.

                ## Response Formatting
                - Use clear headings and subheadings.
                - Use bullet points whenever appropriate.
                - Highlight important keywords using **bold**.
                - Break long explanations into smaller sections.
                - Use numbered steps for procedures.
                - Use tables when comparing multiple items.
                - End long explanations with a concise summary.
                - Keep formatting clean and easy to scan.

                ## Teaching Style
                - Explain concepts like a good teacher.
                - Start from the basics before moving to advanced concepts.
                - Explain step by step.
                - Use simple language whenever possible.
                - Include real-world examples.
                - Explain difficult terms immediately after introducing them.
                - Use analogies and memory tricks whenever helpful.
                - Mention common mistakes learners make.
                - Suggest the next logical learning topic when relevant.

                ## Notes Generation
                When the user asks for notes:
                - Start with a one-line definition.
                - Add a Quick Summary section.
                - List important concepts.
                - Explain each concept briefly.
                - Include examples.
                - Include formulas where applicable.
                - Mention common mistakes.
                - End with quick revision points.
                Structure: Definition -> Quick Summary -> Important Points -> Examples -> Formula (if applicable) -> Common Mistakes -> Revision Points

                ## Summarization
                When summarizing: Preserve original meaning, remove unnecessary details, highlight important concepts, keep it concise.

                ## Quiz Mode
                When creating quizzes: Ask one question at a time, wait for user's answer, do not reveal answer early, explain why it's correct/incorrect, mention difficulty level.

                ## Flashcards
                One concept per flashcard. Front = Question/Term, Back = Short explanation.

                ## Mind Maps & Roadmaps
                Mind Maps: Clean text-based hierarchy using indentation. Roadmaps: Beginner to advanced, prerequisites, practice suggestions.

                ## Coding Assistance
                Explain approach -> clean readable code -> comments -> Time/Space complexity -> sample I/O -> common mistakes.

                ## Mathematics, Science & Engineering
                Show step-by-step calculations. State formulas. Explain principles before formulas, mention applications.

                ## PDF Handling
                Read entire document. Base answers primarily on uploaded doc. Summarize, extract key concepts. Do not fabricate.

                ## Personalization
                Adjust to Beginner, Intermediate, or Advanced level. Use Visual Learning (text diagrams, trees, tables) when useful.

                ## Memory & Safety
                Only remember requested info. Never remember sensitive data. Never provide harmful/illegal instructions.

                ## Smart Behaviors
                Auto-detect required format (Notes, Quiz, Mind Map, etc.) and generate it. 

                ## Quality Checklist
                Accurate, Clear, Structured, Easy to understand, Relevant, Practical, Concise, Helpful, properly formatted.

                ## Final Rule
                Always aim to maximize learning, clarity, and accuracy while minimizing confusion. Every response should help the user understand, remember, and apply the concept effectively.

                ## Current Affairs Detection Rules

                Before answering, determine whether the question depends on recent or changing information.

                Treat these as current-affairs questions:

                - Current Chief Minister
                - Current Prime Minister
                - Current President
                - Current Governor
                - Current Minister
                - Current CEO
                - Current Chairman
                - Latest News
                - Breaking News
                - Election Results
                - Today's News
                - Recent Events
                - Current Sports Rankings
                - Stock Market
                - Cryptocurrency Prices
                - Weather
                - Live Scores
                - Ongoing Events

                If the question contains words like:

                - current
                - latest
                - today
                - now
                - recently
                - who is
                - currently
                - present
                - live

                OR the answer may change over time,

                DO NOT answer using the model's internal knowledge.

                Instead:

                1. Query the Current Affairs API.
                2. Use only the returned information.
                3. If no information is available, say:
                   "I couldn't verify the latest information from the connected data source."

                Never guess current facts.

                # Current Affairs Engine - Rules for Responding

                You are an AI Current Affairs Assistant that answers questions using the available Current Affairs API data. Your primary goal is to provide accurate, timely, and unbiased information.

                --------------------------------------------------
                GENERAL RULES
                --------------------------------------------------

                - Always use the Current Affairs API as the primary source.
                - Never invent or assume news that is not present in the API.
                - If the API has no relevant result, clearly inform the user.
                - Never present assumptions as facts.
                - Keep responses factual and neutral.
                - Do not exaggerate headlines.

                --------------------------------------------------
                SEARCH RULES
                --------------------------------------------------

                Before answering:

                1. Search the Current Affairs API.
                2. Retrieve the most relevant articles.
                3. Rank results by relevance and recency.
                4. Ignore duplicate articles.
                5. Prefer trusted publishers when multiple articles report the same event.

                --------------------------------------------------
                RESPONSE FORMAT
                --------------------------------------------------

                Present news in the following order:

                Headline

                Short Summary

                Key Facts

                Date Published

                Source Name

                Why It Matters

                If multiple articles discuss the same event, combine them into one concise summary.

                --------------------------------------------------
                LATEST NEWS REQUESTS
                --------------------------------------------------

                If the user asks:

                - Latest News
                - Today's News
                - Breaking News
                - Current Affairs

                Always return the newest available API results.

                If no recent articles are available:

                Say:

                "No recent news is currently available from the connected news source."

                Do not generate fake breaking news.

                --------------------------------------------------
                TOPIC SEARCH
                --------------------------------------------------

                If the user searches:

                - AI
                - Cricket
                - Politics
                - Technology
                - Business
                - Space
                - Health

                Only return articles related to that topic.

                Never mix unrelated news.

                --------------------------------------------------
                ARTICLE SUMMARIZATION
                --------------------------------------------------

                When summarizing an article:

                - Preserve the original meaning.
                - Do not change facts.
                - Keep summaries concise.
                - Mention important names, organizations, and locations.
                - Avoid personal opinions.

                --------------------------------------------------
                MULTIPLE SOURCES
                --------------------------------------------------

                If multiple trusted sources report the same event:

                Merge the information.

                Highlight only verified facts shared across sources.

                Mention differing details only if they are significant.

                --------------------------------------------------
                BIAS RULES
                --------------------------------------------------

                Remain politically neutral.

                Do not support or oppose any individual, organization, religion, or government.

                Present facts without emotional language.

                --------------------------------------------------
                UNKNOWN INFORMATION
                --------------------------------------------------

                If information is unavailable:

                Respond:

                "I couldn't find verified information for this request in the connected Current Affairs database."

                Do not guess.

                --------------------------------------------------
                TIME AWARENESS
                --------------------------------------------------

                Always mention when the news was published.

                If an article is older than the user's requested time period:

                Clearly state that it is not recent.

                --------------------------------------------------
                FACT CHECK RULES
                --------------------------------------------------

                Never alter:

                - Dates
                - Names
                - Numbers
                - Statistics
                - Quotes

                Keep them exactly as provided by the API.

                --------------------------------------------------
                LIMITED DATA HANDLING
                --------------------------------------------------

                If the API returns only a headline:

                Clearly state:

                "Limited information is available from the connected news source."

                Do not expand the story using assumptions.

                --------------------------------------------------
                FOLLOW-UP QUESTIONS
                --------------------------------------------------

                If the user asks:

                "Tell me more"

                Use only additional information available from the retrieved article.

                Do not invent missing details.

                --------------------------------------------------
                CURRENT AFFAIRS QUIZ
                --------------------------------------------------

                If quiz mode is enabled:

                Generate questions only from retrieved news articles.

                Do not create questions about unavailable news.

                --------------------------------------------------
                TRENDING NEWS
                --------------------------------------------------

                Trending news should be selected using:

                - Recency
                - Frequency across trusted publishers
                - User-selected category

                Never manufacture trending topics.

                --------------------------------------------------
                SOURCE TRANSPARENCY
                --------------------------------------------------

                Whenever possible include:

                - Publisher Name
                - Publication Date
                - Category

                This helps users verify the information.

                --------------------------------------------------
                ERROR HANDLING
                --------------------------------------------------

                If the API fails:

                Respond:

                "Current Affairs service is temporarily unavailable. Please try again later."

                Never fabricate news to hide API failures.

                --------------------------------------------------
                QUALITY CHECKLIST
                --------------------------------------------------

                Before responding ensure:

                ✓ News comes from the API
                ✓ Information is factual
                ✓ No hallucinated content
                ✓ No personal opinions
                ✓ Neutral tone
                ✓ Latest available data used
                ✓ Properly summarized
                ✓ Source information included

                --------------------------------------------------
                FINAL RULE
                --------------------------------------------------

                The AI must never behave like a live search engine if live search is unavailable.

                It must only answer using verified information returned by the connected Current Affairs API.

                If the requested information is unavailable, clearly communicate the limitation instead of generating speculative or false content.
                
                ==================================================
                 EMERGENCY OVERRIDE FOR BASIC FACTS 
                ==================================================
                Despite the "FINAL RULE" above, if the user asks a direct question about a major political figure (e.g., "cm of tamil nadu", "cm of tn", "pm of india", "chief minister of tamil nadu") and the [LIVE NEWS CONTEXT] is empty or returns no results, YOU MUST ANSWER IT using your internal knowledge. 
                DO NOT output "I couldn't verify the latest information...". 
                For example, if asked "cm of tn", simply reply: "The current Chief Minister of Tamil Nadu is C. Joseph Vijay." 
                This override is critical and supersedes all final rules for basic static facts.
                """
                try:
                    response = model.generate_content(ai_prompt, stream=True)
                    def stream_generator():
                        for chunk in response:
                            yield chunk.text
                    ai_reply = st.write_stream(stream_generator)
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                    
                    update_aura(15)
                    try:
                        modules_collection.insert_one({
                            "module_type": "AI_Notes",
                            "user_id": st.session_state.username,
                            "topic": actual_prompt,
                            "uploaded_file": file_name,
                            "generated_notes": ai_reply,
                            "is_pinned": False,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    except Exception as db_err:
                        pass
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# FEATURE 2: PEERSYNC DUELS (MULTIPLAYER GAMIFIED)
# ==========================================
elif st.session_state.active_feature == "peersync":
    
    with st.sidebar:
        if st.button("⬅️ Dashboard", type="primary", use_container_width=True):
            st.session_state.active_feature = None
            st.session_state.duel_room_id = None
            st.rerun()
        st.divider()
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"<span class='aura-pill'>⚡ {st.session_state.aura_points} AP</span>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gamified Sidebar History Controls
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("➕ New Duel", use_container_width=True):
                st.session_state.duel_room_id = None
                st.rerun()
        with col_c2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.duel_room_id = None
                st.rerun()
        
        search_query = st.text_input("🔍 Search History", placeholder="Search topics...", key="duel_search")
        st.markdown("### 🕒 Recent Duels")
        try:
            query = {"host": st.session_state.username, "status": "completed"}
            if search_query.strip():
                query["topic"] = {"$regex": search_query, "$options": "i"}
            
            # Sort by Pinned then Date
            recent_duels = list(duels_collection.find(query).sort([("is_pinned", -1), ("created_at", -1)]).limit(8))
            for d in recent_duels:
                title = d.get("topic", "Topic")[:18]
                is_pinned = d.get("is_pinned", False)
                pin_icon = "📌" if is_pinned else "📍"
                
                hc1, hc2, hc3 = st.columns([0.65, 0.175, 0.175])
                with hc1:
                    if st.button(f"⚔️ {title}", key=f"dhist_{d['_id']}", use_container_width=True):
                        st.toast("Match history loaded.")
                with hc2:
                    if st.button(pin_icon, key=f"dpin_{d['_id']}", use_container_width=True, help="Pin/Unpin"):
                        duels_collection.update_one({"_id": d['_id']}, {"$set": {"is_pinned": not is_pinned}})
                        st.rerun()
                with hc3:
                    if st.button("🗑️", key=f"ddel_{d['_id']}", use_container_width=True, help="Delete"):
                        duels_collection.delete_one({"_id": d['_id']})
                        st.rerun()
        except:
            st.caption("No history found.")

    st.markdown(f"<h2 style='color: #8B5CF6;'>⚔️ PEERSYNC DUEL</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Synchronous multiplayer quiz battles with instant invitations and AI referee evaluation!</p>", unsafe_allow_html=True)
    st.markdown("---")

    # STAGE 1: DUEL HUB & INVITATIONS
    if st.session_state.duel_room_id is None:
        
        # Check for Incoming Invites
        curr_user = users_collection.find_one({"full_name": st.session_state.username})
        pending_invites = curr_user.get("duel_invites", []) if curr_user else []
        
        if pending_invites:
            st.markdown("### 📬 Duel Invites Inbox")
            for inv in pending_invites:
                with st.container(border=True):
                    ic1, ic2, ic3 = st.columns([3, 1, 1])
                    with ic1:
                        st.markdown(f"⚔️ **{inv['from']}** challenged you to a duel on **'{inv['topic']}'**! *(Code: `{inv['room_id']}`)*")
                    with ic2:
                        if st.button("✅ Accept", key=f"acc_{inv['room_id']}", use_container_width=True, type="primary"):
                            duels_collection.update_one(
                                {"room_id": inv['room_id']}, 
                                {"$set": {"opponent": st.session_state.username, "status": "ready"}}
                            )
                            users_collection.update_one(
                                {"full_name": st.session_state.username}, 
                                {"$pull": {"duel_invites": {"room_id": inv['room_id']}}}
                            )
                            st.session_state.duel_room_id = inv['room_id']
                            st.rerun()
                    with ic3:
                        if st.button("❌ Decline", key=f"dec_{inv['room_id']}", use_container_width=True):
                            users_collection.update_one(
                                {"full_name": st.session_state.username}, 
                                {"$pull": {"duel_invites": {"room_id": inv['room_id']}}}
                            )
                            st.rerun()
            st.markdown("---")

        col_host, col_join = st.columns(2)
        
        with col_host:
            with st.container(border=True):
                st.markdown("#### ⚔️ Host a Duel")
                topic = st.text_input("Enter Topic (Leave blank for random):", placeholder="e.g. AI, Space, Science")
                num_q = st.number_input("Number of Questions:", min_value=1, max_value=20, value=5)
                
                if st.button("Generate & Create Duel Room 🎯", type="primary", use_container_width=True):
                    # Smart Feature: Random Topic if Empty
                    actual_topic = topic.strip()
                    if not actual_topic:
                        random_topics = ["Space Exploration", "Artificial Intelligence", "World History", "General Science", "Sports Trivia"]
                        actual_topic = random.choice(random_topics)
                        st.toast(f"No topic entered. Auto-selected: {actual_topic} 🎲")
                    
                    query_lower = actual_topic.lower()
                    requires_news = any(keyword in query_lower for keyword in NEWS_KEYWORDS)
                    status_message = f"AI is fetching news and generating {num_q} questions..." if requires_news else f"AI is crafting {num_q} questions..."
                    
                    with st.spinner(status_message):
                        live_context3 = get_currents_news(actual_topic) if requires_news else ""
                        
                        quiz_prompt = f"""
                        Generate {num_q} multiple-choice questions on the topic: '{actual_topic}'.
                        
                        [LIVE NEWS CONTEXT - ONLY IF APPLICABLE]
                        {live_context3}

                        ## Current Affairs Detection Rules
                        Before answering, determine whether the question depends on recent or changing information.
                        Treat these as current-affairs questions: Current CM, PM, President, Latest News, Sports rankings, etc.
                        If question contains: current, latest, today, now, recently, who is, live:
                        Query Current Affairs API and use only returned information. Never guess current facts.

                        # Current Affairs Engine - Rules for Responding
                        - Always use Current Affairs API as primary source.
                        - Never invent or assume news.
                        - Keep responses factual and neutral.

                        ==================================================
                        EMERGENCY OVERRIDE FOR BASIC FACTS 
                        ==================================================
                        Despite the rule above, if user asks for a quiz on a direct static topic like "cm of tn" or "politics" and LIVE NEWS CONTEXT is empty, generate questions using internal knowledge instead of failing.

                        Return ONLY a valid JSON array. Each object must have exactly these keys:
                        "question": The question text as a string.
                        "options": An array of exactly 4 strings, representing the options.
                        "answer": The exact string from the options array that is correct.
                        Do not include any markdown formatting like ```json, just output the raw JSON array.
                        """
                        try:
                            res = model.generate_content(quiz_prompt)
                            raw_text = res.text.strip()
                            if raw_text.startswith("```json"): raw_text = raw_text[7:]
                            if raw_text.startswith("```"): raw_text = raw_text[3:]
                            if raw_text.endswith("```"): raw_text = raw_text[:-3]
                            quiz_data = json.loads(raw_text.strip())
                            
                            room_id = f"DUEL-{random.randint(1000, 9999)}"
                            duel_doc = {
                                "room_id": room_id,
                                "host": st.session_state.username,
                                "opponent": None,
                                "topic": actual_topic,
                                "num_q": num_q,
                                "quiz_data": quiz_data,
                                "host_answers": [],
                                "opp_answers": [],
                                "status": "waiting", 
                                "start_time": None,
                                "eval_report": "",
                                "is_pinned": False,
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            duels_collection.insert_one(duel_doc)
                            st.session_state.duel_room_id = room_id
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error generating quiz: {e}")

        with col_join:
            with st.container(border=True):
                st.markdown("#### 🚪 Join via Room Code")
                join_code = st.text_input("Enter 9-Character Room Code:", placeholder="e.g. DUEL-1234")
                if st.button("Enter Duel Room 🚀", use_container_width=True):
                    if join_code.strip():
                        duel = duels_collection.find_one({"room_id": join_code.strip()})
                        if duel and duel.get("opponent") in [None, st.session_state.username] and duel["status"] in ["waiting", "ready", "active"]:
                            updates = {}
                            if duel.get("opponent") is None:
                                updates["opponent"] = st.session_state.username
                            if duel["status"] == "waiting":
                                updates["status"] = "ready"
                            
                            if updates:
                                duels_collection.update_one({"room_id": join_code.strip()}, {"$set": updates})
                            st.session_state.duel_room_id = join_code.strip()
                            st.rerun()
                        else:
                            st.error("Invalid Duel Code or Match is completed/full!")
                    else:
                        st.warning("Please type a room code.")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # ACTIVE FRIENDS LIST & DIRECT INVITE
        st.markdown("### 👥 Available Scholars & Friends (Direct Invite)")
        try:
            scholars = users_collection.find({"full_name": {"$ne": st.session_state.username}}).limit(6)
            sc_cols = st.columns(3)
            col_idx = 0
            for friend in scholars:
                with sc_cols[col_idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"**🟢 {friend['full_name']}**")
                        st.caption(f"⚡ Aura: {friend.get('aura_points', 100)} AP")
                        # Show invite button if host created a room
                        if st.session_state.duel_room_id:
                            if st.button(f"⚔️ Invite {friend['full_name'][:10]}", key=f"inv_btn_{friend['_id']}"):
                                curr_d = duels_collection.find_one({"room_id": st.session_state.duel_room_id})
                                users_collection.update_one(
                                    {"full_name": friend['full_name']},
                                    {"$push": {"duel_invites": {"room_id": st.session_state.duel_room_id, "from": st.session_state.username, "topic": curr_d['topic']}}}
                                )
                                st.toast(f"Invite sent to {friend['full_name']}!")
                        else:
                            st.caption("Host a duel above to invite friends!")
                col_idx += 1
        except:
            st.caption("Unable to fetch friends list.")

    # STAGE 2: INSIDE THE DUEL ROOM (WAITING / READY / ACTIVE / RESULT)
    else:
        duel = duels_collection.find_one({"room_id": st.session_state.duel_room_id})
        if not duel:
            st.error("Room not found!")
            st.session_state.duel_room_id = None
            st.button("Return to Hub")
            st.stop()

        is_host = (duel["host"] == st.session_state.username)
        
        # Host (You) & Opponent (You) Fix
        host_display = f"{duel['host']} (You)" if is_host else duel['host']
        opp_name = duel.get('opponent')
        if not opp_name:
            opp_display = "Waiting for Opponent..."
        else:
            opp_display = f"{opp_name} (You)" if not is_host else opp_name
        
        col_rh1, col_rh2 = st.columns([4, 1])
        with col_rh1:
            st.markdown(f"### Room Code: `{duel['room_id']}` | Topic: **{duel['topic']}**")
            st.caption(f"👑 Host: **{host_display}** VS ⚔️ Opponent: **{opp_display}**")
        with col_rh2:
            if st.button("🚪 Exit Match", use_container_width=True):
                st.session_state.duel_room_id = None
                st.rerun()

        st.markdown("---")

        # 1. LOBBY (WAITING / READY)
        if duel["status"] in ["waiting", "ready"]:
            if not duel.get('opponent'):
                st.info("🕒 Waiting for an opponent to join...")
                st.markdown(f"Share this room code with your friend: **`{duel['room_id']}`**")
                
                st.markdown("#### Or Invite a Friend Directly:")
                all_friends = users_collection.find({"full_name": {"$ne": st.session_state.username}}).limit(4)
                for f in all_friends:
                    fc1, fc2 = st.columns([3, 1])
                    fc1.write(f"🟢 **{f['full_name']}**")
                    if fc2.button("Send Invite", key=f"send_inv_{f['full_name']}"):
                        users_collection.update_one(
                            {"full_name": f['full_name']},
                            {"$push": {"duel_invites": {"room_id": duel['room_id'], "from": st.session_state.username, "topic": duel['topic']}}}
                        )
                        st.toast(f"Invite sent to {f['full_name']}!")
            else:
                st.success(f"🎉 **{duel['opponent']}** is in the lobby!")
            
            st.markdown("### 🎮 Match Lobby")
            st.markdown(f"- 👑 Player 1: **{host_display}** (Ready ✅)")
            opp_status = "(Ready ✅)" if duel.get('opponent') else "(Waiting ⏳)"
            st.markdown(f"- ⚔️ Player 2: **{opp_display}** {opp_status}")
            st.markdown(f"- ⏱️ Total Time: **{duel['num_q'] * 30} Seconds** ({duel['num_q']} Questions)")

            if is_host:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔥 START MATCH NOW! 🔥", type="primary", use_container_width=True):
                    duels_collection.update_one(
                        {"room_id": duel['room_id']},
                        {"$set": {"status": "active", "start_time": time.time()}}
                    )
                    st.rerun()
            else:
                st.info("🕒 Waiting for Host to click **Start Match**...")
                time.sleep(2)
                st.rerun()

        # 3. ACTIVE QUIZ BATTLE
        elif duel["status"] == "active":
            time_limit = duel["num_q"] * 30  # 30s per question
            elapsed = int(time.time() - duel.get("start_time", time.time()))
            time_left = max(0, time_limit - elapsed)

            # Check if current user already submitted to prevent UI freezing
            has_submitted = len(duel.get("host_answers", [])) > 0 if is_host else len(duel.get("opp_answers", [])) > 0

            if has_submitted:
                st.success("✅ Your answers are submitted! Waiting for your opponent to finish...")
                st.info("The match is still active for your opponent. Please wait.")
                # Auto-refresh to check if opponent is done
                time.sleep(3)
                st.rerun()
            else:
                # LIVE UI RUNNING JAVASCRIPT COUNTDOWN WITH NEON GLOW EFFECTS
                timer_html = f"""
                <div style="background: rgba(17, 27, 46, 0.8); backdrop-filter: blur(10px); color: #38bdf8; padding: 15px; border-radius: 12px; text-align: center; font-size: 24px; font-weight: bold; border: 1px solid #8B5CF6; box-shadow: 0 0 15px rgba(139, 92, 246, 0.3); margin-bottom: 20px;">
                    ⏳ Match Time Remaining: <span id="time_display" style="color: #F59E0B; text-shadow: 0 0 8px rgba(245,158,11,0.5);">--:--</span>
                </div>
                <script>
                    var seconds = {time_left};
                    var display = document.getElementById('time_display');
                    var countdown = setInterval(function() {{
                        if (seconds <= 0) {{
                            clearInterval(countdown);
                            display.innerHTML = "00:00 (Time Expired! Auto-submitting...)";
                            var buttons = window.parent.document.querySelectorAll('button');
                            for(var i=0; i<buttons.length; i++){{
                                if(buttons[i].innerText.includes('Submit Answers')){{
                                    buttons[i].click();
                                    break;
                                }}
                            }}
                        }} else {{
                            var mins = Math.floor(seconds / 60);
                            var remSec = seconds % 60;
                            display.innerHTML = (mins < 10 ? "0" : "") + mins + ":" + (remSec < 10 ? "0" : "") + remSec;
                            seconds--;
                        }}
                    }}, 1000);
                </script>
                """
                components.html(timer_html, height=80)

                with st.form("quiz_battle_form"):
                    user_answers = []
                    for i, q in enumerate(duel["quiz_data"]):
                        st.markdown(f"#### Q{i+1}: {q['question']}")
                        ans = st.radio(
                            f"Select your answer for Q{i+1}:",
                            q['options'],
                            key=f"duel_q_{i}",
                            index=None,
                            label_visibility="collapsed"
                        )
                        user_answers.append(ans)
                        st.markdown("---")
                    
                    submitted = st.form_submit_button("✅ Submit Answers", use_container_width=True, type="primary")

                    if submitted or time_left <= 0:
                        if time_left <= 0:
                            st.toast("Time limit reached! Submitting answers automatically.")
                        
                        update_field = "host_answers" if is_host else "opp_answers"
                        # Handle empty answers properly
                        final_answers = [a if a else "Not Answered" for a in user_answers]
                        
                        duels_collection.update_one({"room_id": duel["room_id"]}, {"$set": {update_field: final_answers}})
                        
                        # Check if both have finished
                        up_duel = duels_collection.find_one({"room_id": duel["room_id"]})
                        if len(up_duel.get("host_answers", [])) > 0 and len(up_duel.get("opp_answers", [])) > 0:
                            duels_collection.update_one({"room_id": duel["room_id"]}, {"$set": {"status": "evaluating"}})
                        st.rerun()

        # 4. EVALUATING SCORES (Referee & Explanations Fix)
        elif duel["status"] == "evaluating":
            st.info("🕒 AI Referee is evaluating both players' answers and generating the scorecard...")
            if is_host:
                with st.spinner("AI Referee is comparing answer sheets..."):
                    eval_prompt = f"""
                    # PeerSync Duels - Quiz Referee Report
                    You are the AI referee for a synchronous multiplayer quiz.
                    
                    Quiz Correct Answers & Data:
                    {json.dumps(duel['quiz_data'])}
                    
                    {duel['host']}'s Selected Answers:
                    {duel['host_answers']}
                    
                    {duel['opponent']}'s Selected Answers:
                    {duel['opp_answers']}
                    
                    INSTRUCTIONS:
                    1. Calculate both players' scores out of {duel['num_q']}. Any question marked as 'Not Answered' receives 0 marks.
                    2. Provide a VERY SIMPLE RESULT at the top:
                       - Just the Player Names and their Scores out of {duel['num_q']}.
                       - Clearly state "WINNER: [Name]" and "DEFEATED: [Name]" (or "DRAW").
                    3. DO NOT use complex tables for the top section. Keep it visually simple.
                    4. Below the result, provide a brief, clear explanation for EVERY question (all {duel['num_q']} of them). Show the question, the correct answer, and a short explanation.
                    5. Give positive encouragement for their academic vibe!
                    """
                    try:
                        res = model.generate_content(eval_prompt).text
                        duels_collection.update_one(
                            {"room_id": duel["room_id"]},
                            {"$set": {"status": "completed", "eval_report": res}}
                        )
                        update_aura(50)
                        st.rerun()
                    except Exception as e:
                        st.error("Error evaluating. Retrying...")
            else:
                st.warning("Host is generating the scorecard. Updating automatically...")
                time.sleep(2)
                check_d = duels_collection.find_one({"room_id": duel["room_id"]})
                if check_d.get("status") == "completed":
                    update_aura(50)
                    st.rerun()

        # 5. MATCH COMPLETED (SCORECARD + EXPLANATION)
        elif duel["status"] == "completed":
            st.success("🎉 Match Completed! +50 Aura Points Earned!")
            st.markdown("### 🏆 AI Referee Scorecard & Explanation")
            st.markdown(duel["eval_report"])
            st.markdown("---")
            if st.button("⚔️ Play Another Duel", type="primary", use_container_width=True):
                st.session_state.duel_room_id = None
                st.rerun()

# ==========================================
# FEATURE 3: CHRONOS ADAPTIVE SCHEDULER
# ==========================================
elif st.session_state.active_feature == "chronos":
    
    with st.sidebar:
        if st.button("⬅ Dashboard", type="primary", use_container_width=True):
            st.session_state.active_feature = None
            st.rerun()
        st.divider()
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"<span class='aura-pill'>⚡ {st.session_state.aura_points} AP</span>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gamified Sidebar Controls
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("➕ New Plan", use_container_width=True):
                st.session_state.chronos_schedule = ""
                st.rerun()
        with col_c2:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.chronos_schedule = ""
                st.rerun()
                
        search_query = st.text_input("🔍 Search History", placeholder="Search topics...", key="chronos_search")
        st.markdown("### 🕒 Saved Schedules")
        try:
            query = {"module_type": "Chronos_Schedule", "user_id": st.session_state.username}
            if search_query.strip():
                query["topic"] = {"$regex": search_query, "$options": "i"}
            
            # Sort by Pinned then Date
            recent_plans = list(modules_collection.find(query).sort([("is_pinned", -1), ("created_at", -1)]).limit(8))
            for plan in recent_plans:
                title = plan.get("topic", "Exam")[:18]
                is_pinned = plan.get("is_pinned", False)
                pin_icon = "📌" if is_pinned else "📍"
                
                hc1, hc2, hc3 = st.columns([0.65, 0.175, 0.175])
                with hc1:
                    if st.button(f"📅 {title}", key=f"chist_{plan['_id']}", use_container_width=True):
                        st.session_state.chronos_schedule = plan.get("generated_schedule", "")
                        st.rerun()
                with hc2:
                    if st.button(pin_icon, key=f"cpin_{plan['_id']}", use_container_width=True, help="Pin/Unpin"):
                        modules_collection.update_one({"_id": plan['_id']}, {"$set": {"is_pinned": not is_pinned}})
                        st.rerun()
                with hc3:
                    if st.button("🗑️", key=f"cdel_{plan['_id']}", use_container_width=True, help="Delete"):
                        modules_collection.delete_one({"_id": plan['_id']})
                        st.rerun()
        except:
            st.caption("No history found.")

    st.markdown(f"<h2 style='color: #22D3EE;'>⏳ CHRONOS ADAPTIVE SCHEDULER</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Algorithmic spaced repetition and dynamic micro-task partitioning.</p>", unsafe_allow_html=True)
    st.markdown("---")

    with st.form("chronos_input_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject_name = st.text_input("📚 Subject / Exam Name:", placeholder="e.g. Data Structures & Algorithms, GATE CS")
        with col2:
            uploaded_syllabus = st.file_uploader("📎 Upload Syllabus (PDF/TXT):", type=["pdf", "txt"], key="chronos_pdf")
            
        topics_text = st.text_area("📋 Enter Topics List (or leave blank if uploaded above):", placeholder="e.g., Arrays, Linked Lists, Binary Trees, Graph Traversal", height=100)
        
        col3, col4 = st.columns(2)
        with col3:
            exam_date = st.date_input("🎯 Exam / Target Date:", min_value=date.today())
        with col4:
            daily_hours = st.number_input("⏱ Daily Available Time (Hours):", min_value=0.5, max_value=12.0, value=2.0, step=0.5)
            
        submit_chronos = st.form_submit_button("⚡ Generate Spaced Schedule", use_container_width=True, type="primary")

    if submit_chronos:
        pdf_content = ""
        file_name = "None"
        if uploaded_syllabus is not None:
            file_name = uploaded_syllabus.name
            if uploaded_syllabus.type == "application/pdf":
                try:
                    reader = PyPDF2.PdfReader(uploaded_syllabus)
                    for page in reader.pages:
                        pdf_content += page.extract_text() or ""
                except: pass
            else:
                pdf_content = uploaded_syllabus.read().decode("utf-8", errors="ignore")

        combined_topics = f"{topics_text}\n{pdf_content}".strip()
        
        if not subject_name.strip():
            st.warning("Please enter a Subject / Exam Name.")
        elif not combined_topics:
            st.warning("Please enter topics or upload a syllabus document.")
        else:
            with st.spinner("Chronos AI is calculating Ebbinghaus curves, partitioning micro-tasks, and generating your schedule..."):
                days_remaining = (exam_date - date.today()).days
                if days_remaining <= 0: days_remaining = 1 
                
                chronos_prompt = f"""
                You are 'Chronos Adaptive Scheduler', an expert algorithmic study planner. You strictly enforce spaced repetition and dynamic micro-task partitioning.

                STUDENT GOAL DATA:
                - Subject/Exam: {subject_name}
                - Target Date: {exam_date} ({days_remaining} Days Remaining)
                - Daily Time Limit: {daily_hours} Hours
                - Input Topics/Syllabus: "{combined_topics}"

                # Chronos Adaptive Scheduler – AI Response Rules

                Rule 1 – Analyze Goal First
                Calculate realistic distribution based on Days Remaining ({days_remaining} days), Daily Time ({daily_hours} hours), and the syllabus provided.

                Rule 2 – Split into Micro Tasks
                Never assign huge chapters. Always split topics into 20–30 minute study blocks with one clear objective per block.

                Rule 3 – Difficulty Based Scheduling
                Classify every topic into Easy, Medium, or Hard.
                - Hard → Earliest possible days (needs multiple revisions).
                - Medium → Middle days.
                - Easy → Near exam days.

                Rule 4 – Apply Spaced Repetition
                Every completed topic MUST receive spaced revision sessions:
                - Initial Learning → Day X
                - Revision 1 → +1 Day
                - Revision 2 → +3 Days
                - Revision 3 → +7 Days
                - Revision 4 → +14 Days
                - Never schedule all revisions on the same day.

                Rule 5 – Respect Daily Time Limit
                Total daily activities (Micro Tasks + Revisions + Quizzes + Breaks) MUST NOT exceed {daily_hours} Hours/day.

                Rule 6 – Smart Time Distribution
                If exam is close ({days_remaining} <= 10 days): Reduce theory, increase revision, prioritize high-weight topics.
                If exam is far ({days_remaining} > 10 days): Slow pace, concept learning, practice.

                Rule 7 – Adaptive Rescheduling
                Always maintain flexibility for missed days or backlog recovery without removing revision slots.

                Rule 8 – Avoid Consecutive Hard Topics
                Interleave subjects: Hard → Easy Revision → Medium → Practice to reduce mental fatigue.

                Rule 9 – Priority Ranking
                Tag topics with Priority Levels: 🔴 High | 🟠 Medium | 🟢 Low based on difficulty and exam weightage.

                Rule 10 – Daily Progress Feedback
                At the end of each day, provide a summary block tracking Completion %, Streak, and Aura Points.

                Rule 11 – Missed Revision Recovery
                Ensure skipped revisions are recovered within 48 hours.

                Rule 12 – Intelligent Break Suggestions
                Recommend a 5–10 minute break after every 50–60 minutes of study.

                Rule 13 – Weekly Optimization
                Provide a 7-day milestone check and buffer day allocation.

                Rule 14 – Personalized Learning Pattern
                Include tips based on optimal study windows.

                Rule 15 – Output Format Consistency
                Structure your output cleanly day-by-day. Every day MUST include:
                -  Date / Day Number
                -  Topic & Difficulty Level
                -  Micro Tasks (20-30 min blocks)
                -  Estimated Time
                -  Revision Slot
                -  Interactive Checklist
                -  Aura Points Reward

                 Advanced Features to Include in the Plan:
                - Deadline Risk Detection: Add an alert if {days_remaining} days is too tight for the syllabus.
                - Buffer Day Allocation: Include 1 buffer day per week.
                - Practice-Test Integration: Schedule mock tests at key checkpoints.
                - Burnout Prevention: Ensure workload is balanced.

                INSTRUCTIONS: Generate a complete, highly structured, professional study plan adhering to ALL the rules above.
                """
                try:
                    res = model.generate_content(chronos_prompt)
                    st.session_state.chronos_schedule = res.text
                    
                    update_aura(30)
                    try:
                        modules_collection.insert_one({
                            "module_type": "Chronos_Schedule",
                            "user_id": st.session_state.username,
                            "topic": subject_name,
                            "uploaded_file": file_name,
                            "generated_schedule": res.text,
                            "target_date": str(exam_date),
                            "is_pinned": False,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    except: pass
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating schedule: {e}")

    if st.session_state.chronos_schedule:
        st.markdown("---")
        st.success(" Chronos Schedule Successfully Generated! +30 Aura Points Earned!")
        st.markdown(st.session_state.chronos_schedule)

# ==========================================
# FEATURE 4: AI AUDIO NOTES GENERATOR (CONTINUOUS MIC CHAT + AUDIO)
# ==========================================
elif st.session_state.active_feature == "audio_notes":
    
    with st.sidebar:
        if st.button("⬅ Dashboard", type="primary", use_container_width=True):
            st.session_state.active_feature = None
            st.rerun()
        st.divider()
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"<span class='aura-pill'>⚡ {st.session_state.aura_points} AP</span>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Audio Chat Controls
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("➕ New Audio", use_container_width=True):
                st.session_state.audio_messages = []
                st.rerun()
        with col_c2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.audio_messages = []
                st.rerun()
                
        search_query = st.text_input("🔍 Search History", placeholder="Search topics...", key="audio_search")
        st.markdown("### 🕒 Audio History")
        try:
            query = {"module_type": "Audio_Notes", "user_id": st.session_state.username}
            if search_query.strip():
                query["topic"] = {"$regex": search_query, "$options": "i"}
            
            # Sort by Pinned then Date
            recent_audio = list(modules_collection.find(query).sort([("is_pinned", -1), ("created_at", -1)]).limit(8))
            for doc in recent_audio:
                title = doc.get("topic", "Study Topic")[:18]
                is_pinned = doc.get("is_pinned", False)
                pin_icon = "📌" if is_pinned else "📍"
                
                hc1, hc2, hc3 = st.columns([0.65, 0.175, 0.175])
                with hc1:
                    if st.button(f"🎧 {title}", key=f"ahist_{doc['_id']}", use_container_width=True):
                        st.session_state.audio_messages = [
                            {"role": "user", "content": doc.get("topic", "")},
                            {"role": "assistant", "content": doc.get("generated_script", "")}
                        ]
                        st.rerun()
                with hc2:
                    if st.button(pin_icon, key=f"apin_{doc['_id']}", use_container_width=True, help="Pin/Unpin"):
                        modules_collection.update_one({"_id": doc['_id']}, {"$set": {"is_pinned": not is_pinned}})
                        st.rerun()
                with hc3:
                    if st.button("🗑️", key=f"adel_{doc['_id']}", use_container_width=True, help="Delete"):
                        modules_collection.delete_one({"_id": doc['_id']})
                        st.rerun()
        except:
            st.caption("No history found.")

    st.markdown(f"<h2 style='color: #A78BFA;'>🎙️ AI AUDIO NOTES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Continuous Voice Chat: Speak via Microphone, AI will respond with conversational audio!</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Display Continuous Audio Chat History
    for msg in st.session_state.audio_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "audio_bytes" in msg:
                st.audio(msg["audio_bytes"], format='audio/mp3')

    st.markdown("<br>", unsafe_allow_html=True)

    # Mic Voice Input
    st.markdown("#### 🗣️ Record your Voice")
    recorded_audio = None
    try:
        recorded_audio = st.audio_input("Record your doubt or question:")
    except Exception:
        st.caption("Standard text & file input available below.")

    st.markdown("#### ✍️ Or Type / Upload Documents")
    with st.form("audio_notes_form"):
        col1, col2 = st.columns(2)
        with col1:
            audio_topic = st.text_input("🎙️ Topic / Question:", placeholder="e.g. Explain Neural Networks")
        with col2:
            uploaded_notes = st.file_uploader("📎 Upload Notes/Syllabus (PDF/TXT):", type=["pdf", "txt"], key="audio_pdf")
            
        submit_audio = st.form_submit_button("🎧 Send & Get Audio Reply (+25 AP)", use_container_width=True, type="primary")

    if submit_audio or (recorded_audio is not None):
        pdf_content = ""
        file_name = "None"
        if uploaded_notes is not None:
            file_name = uploaded_notes.name
            if uploaded_notes.type == "application/pdf":
                try:
                    reader = PyPDF2.PdfReader(uploaded_notes)
                    for page in reader.pages:
                        pdf_content += page.extract_text() or ""
                except: pass
            else:
                pdf_content = uploaded_notes.read().decode("utf-8", errors="ignore")

        actual_prompt = audio_topic.strip() if audio_topic else "Explain this study concept clearly."
        
        query_lower = actual_prompt.lower()
        requires_news = any(keyword in query_lower for keyword in NEWS_KEYWORDS)
        
        display_msg = actual_prompt if audio_topic else "Voice input provided."
        st.session_state.audio_messages.append({"role": "user", "content": display_msg})
        
        with st.spinner("Studio AI is processing your input and generating spoken audio notes..."):
            live_context = get_currents_news(actual_prompt) if requires_news else ""

            audio_prompt = f"""You are 'Vibe Learn', an AI-powered Study Assistant designed to help students learn effectively. Your primary goal is to provide accurate, clear, structured, and student-friendly responses.

            [LIVE NEWS CONTEXT - ONLY IF APPLICABLE]
            {live_context}

            CURRENT USER INPUT / CONTEXT:
            "{actual_prompt}\n{pdf_content}"

            # AI Study Assistant - System Rules for Responding

            ## General Behavior
            - Always understand the user's intent before answering.
            - Answer directly without unnecessary introductions.
            - Use simple and easy-to-understand language unless the user requests advanced explanations.
            - Adapt explanations to the user's knowledge level.
            - Keep responses concise by default.
            - Be polite, professional, and encouraging.
            - Never make assumptions about missing information.

            ## Accuracy & Reliability
            - Never invent facts, statistics, references, URLs, quotes, or research papers.
            - If you are uncertain, clearly state that you are not certain instead of guessing.
            - Distinguish between facts, assumptions, and opinions.
            - Prioritize correctness over sounding confident.
            - Avoid misinformation and hallucinations.

            ## Teaching Style
            - Explain concepts like a good teacher.
            - Start from the basics before moving to advanced concepts.
            - Explain step by step.
            - Use simple language whenever possible.
            - Include real-world examples.
            - Explain difficult terms immediately after introducing them.
            - Use analogies and memory tricks whenever helpful.

            ## Current Affairs Detection Rules
            Before answering, determine whether the question depends on recent or changing information.
            If the question contains words like: current, latest, today, now, recently, who is, currently, present, live.
            OR the answer may change over time, DO NOT answer using the model's internal knowledge.
            Instead:
            1. Query the Current Affairs API.
            2. Use only the returned information.
            3. If no information is available, say: "I couldn't verify the latest information from the connected data source."
            Never guess current facts.

            # Current Affairs Engine - Rules for Responding
            You are an AI Current Affairs Assistant that answers questions using the available Current Affairs API data. Your primary goal is to provide accurate, timely, and unbiased information.
            - Always use the Current Affairs API as the primary source.
            - Never invent or assume news that is not present in the API.
            - Keep responses factual and neutral.

            ==================================================
             EMERGENCY OVERRIDE FOR BASIC FACTS 
            ==================================================
            Despite the "FINAL RULE" above, if the user asks a direct question about a major political figure (e.g., "cm of tamil nadu", "cm of tn", "pm of india", "chief minister of tamil nadu") and the [LIVE NEWS CONTEXT] is empty or returns no results, YOU MUST ANSWER IT using your internal knowledge. 
            DO NOT output "I couldn't verify the latest information...". 
            For example, if asked "cm of tn", simply reply: "The current Chief Minister of Tamil Nadu is C. Joseph Vijay." 
            This override is critical and supersedes all final rules for basic static facts.

            ==================================================
            CRITICAL AUDIO FORMATTING EXCEPTION 
            ==================================================
            Even though normal AI notes use headings, bullet points, and bold text, YOU MUST IGNORE THOSE FORMATTING RULES for this specific task.
            Since your exact response will be converted to audio by a Text-to-Speech (TTS) engine:
            - Output ONLY plain conversational text.
            - DO NOT use any markdown symbols (like **, #, -, *, _).
            - DO NOT use bullet points, tables, or complex structures.
            - Just write a clear, continuous, spoken-word explanation based on the strict knowledge rules above.
            """
            try:
                # If audio was recorded directly from mic, send to Gemini multimodal
                if recorded_audio is not None and not audio_topic:
                    audio_bytes_data = recorded_audio.read()
                    gemini_contents = [
                        {"mime_type": "audio/wav", "data": audio_bytes_data},
                        audio_prompt
                    ]
                    script_text = model.generate_content(gemini_contents).text
                else:
                    script_text = model.generate_content(audio_prompt).text
                
                st.toast("🎉 Your Spoken AI Audio Note is Ready! +25 AP")
                update_aura(25)
                
                # Convert Text to Speech
                tts = gTTS(text=script_text, lang='en', slow=False)
                audio_bytes = io.BytesIO()
                tts.write_to_fp(audio_bytes)
                audio_bytes.seek(0)
                
                # Append Assistant Response to Chat
                st.session_state.audio_messages.append({
                    "role": "assistant",
                    "content": script_text,
                    "audio_bytes": audio_bytes.read()
                })
                
                try:
                    modules_collection.insert_one({
                        "module_type": "Audio_Notes",
                        "user_id": st.session_state.username,
                        "topic": actual_prompt,
                        "uploaded_file": file_name,
                        "generated_script": script_text,
                        "is_pinned": False,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                except: pass
                
                st.rerun()
            except Exception as e:
                st.error(f"Error generating audio note: {e}")

# ==========================================
# FEATURE 5: VIBE ROOM (UNIFIED COLLABORATION)
# ==========================================
elif st.session_state.active_feature == "vibe_room":
    
    with st.sidebar:
        if st.button("⬅ Leave Vibe Hub", type="primary", use_container_width=True):
            st.session_state.active_feature = None
            st.session_state.current_vibe_room = None
            st.rerun()
        st.divider()
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"<span class='aura-pill'>⚡ {st.session_state.aura_points} AP</span>", unsafe_allow_html=True)

    def sync_room_to_db(r_id, data):
        try:
            rooms_collection.update_one({"room_id": r_id}, {"$set": data}, upsert=True)
        except: pass

    # ---------------- HUB PAGE: CREATE OR JOIN ----------------
    if st.session_state.current_vibe_room is None:
        st.markdown("<h2 style='text-align: center; color: #22C55E;'>🏠 VIBE ROOM</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94A3B8;'>Create a collaborative study space, share the code, and study together.</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        
        with c1:
            with st.container(border=True):
                st.markdown("#### 🏠 Create a Vibe Room")
                st.markdown("Host a session for group discussions and notes.")
                room_name = st.text_input("Room Subject / Name:", placeholder="e.g. DBMS Semester Prep")
                if st.button("Create Room & Generate Code ✨", type="primary", use_container_width=True):
                    if room_name.strip():
                        r_id = f"VIBE-{random.randint(1000, 9999)}"
                        room_data = {
                            "room_id": r_id, 
                            "name": room_name.strip(), 
                            "host": st.session_state.username, 
                            "participants": [st.session_state.username], 
                            "chat": [], 
                            "doc_text": "Welcome to the Vibe Room! Start collaborating on notes here...",
                            "edit_access": "everyone", # DB Access Setting
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        sync_room_to_db(r_id, room_data)
                        st.session_state.current_vibe_room = r_id
                        st.rerun()
                    else:
                        st.warning("Please provide a room name.")
        
        with c2:
            with st.container(border=True):
                st.markdown("#### 🚪 Join Existing Vibe Room")
                st.markdown("Enter invite code shared by your friend.")
                join_id = st.text_input("Enter 9-Character Room Code:", placeholder="e.g. VIBE-1234")
                if st.button("Enter Room 🚀", use_container_width=True):
                    if join_id.strip():
                        db_room = rooms_collection.find_one({"room_id": join_id.strip()})
                        if db_room:
                            if st.session_state.username not in db_room.get("participants", []):
                                db_room["participants"].append(st.session_state.username)
                                sync_room_to_db(join_id.strip(), {"participants": db_room["participants"]})
                            st.session_state.current_vibe_room = join_id.strip()
                            st.rerun()
                        else:
                            st.error("Invalid Code or Room does not exist in database!")
                    else:
                        st.warning("Please enter a room code.")

    # ---------------- INSIDE THE VIBE ROOM ----------------
    else:
        r_id = st.session_state.current_vibe_room
        room = rooms_collection.find_one({"room_id": r_id})
        if not room:
            st.error("Room closed or not found!")
            st.session_state.current_vibe_room = None
            st.rerun()

        is_host = (room["host"] == st.session_state.username)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"### 🏠 {room['name']}")
            st.caption(f"Invite Code: `{r_id}` | Host: **{room['host']}** | Active Members: {len(room.get('participants', []))}")
        with col2:
            if st.button("🚪 Exit Room", type="primary", use_container_width=True):
                st.session_state.current_vibe_room = None
                st.rerun()

        # Tools & Controls Bar (WITH WEBRTC LIVE STREAMING)
        with st.container(border=True):
            col_ctrl, col_vid = st.columns([1, 2.5])
            with col_ctrl:
                st.markdown("#### 📡 Live Streaming")
                stream_mode = st.radio("Select Source:", ["📷 Camera", "🖥️ Share Screen"], horizontal=False)
                if st.button("✋ Raise Hand", use_container_width=True): st.toast(f"{st.session_state.username} raised hand! ✋")
                with st.expander("📌 Room Rules"):
                    st.write("Collaborate, learn together, and respect peers.")
            
            with col_vid:
                media_constraints = {"audio": True, "video": True}
                if stream_mode == "🖥️ Share Screen":
                    # WebRTC Screen share constraints
                    media_constraints = {"audio": True, "video": {"cursor": "always", "displaySurface": "monitor"}}
                
                try:
                    webrtc_streamer(
                        key=f"vibe_room_stream_{r_id}",
                        mode=WebRtcMode.SENDRECV,
                        rtc_configuration=RTCConfiguration({"iceServers": get_ice_servers()}),
                        media_stream_constraints=media_constraints,
                        async_processing=True
                    )
                except Exception as e:
                    st.warning(f"WebRTC starting... (Ensure camera permissions are allowed in your browser settings.)")

        st.markdown("<br>", unsafe_allow_html=True)

        tab_work, tab_chat, tab_people = st.tabs(["📝 Live Shared Notes", "💬 Group Chat & Vibe AI", "👥 Room Members"])
        
        with tab_work:
            col_timer, col_notes = st.columns([1, 2.5])
            with col_timer:
                st.markdown("#### ⏱️ Focus Timer")
                if st.button("▶️ 25m Focus Block", use_container_width=True): st.toast("Pomodoro Focus Timer Started!")
                if st.button("☕ 5m Quick Break", use_container_width=True): st.toast("Break time started! Relax for 5 mins.")
            with col_notes:
                st.markdown("#### 📋 Collaborative Board")
                
                # --- HOST ACCESS CONTROL LOGIC ---
                current_access = room.get("edit_access", "everyone")
                
                if is_host:
                    st.markdown("**👑 Host Controls:**")
                    new_access = st.radio("Board Edit Permission:", ["🔓 Everyone can Edit", "🔒 Only Host can Edit"], index=0 if current_access == "everyone" else 1, horizontal=True)
                    access_val = "everyone" if "Everyone" in new_access else "host_only"
                    
                    if access_val != current_access:
                        sync_room_to_db(r_id, {"edit_access": access_val})
                        st.rerun()
                
                can_edit = is_host or (current_access == "everyone")
                
                if can_edit:
                    new_notes = st.text_area("Live Shared Notes:", value=room.get("doc_text", ""), height=220, label_visibility="collapsed")
                    if st.button("💾 Sync Notes to Everyone", use_container_width=True, type="primary"):
                        sync_room_to_db(r_id, {"doc_text": new_notes})
                        st.success("Notes synced across all participants!")
                else:
                    st.info("🔒 The Collaborative Board is currently locked by the Host (Read-only mode).")
                    st.text_area("Live Shared Notes:", value=room.get("doc_text", ""), height=220, label_visibility="collapsed", disabled=True)

        with tab_chat:
            st.markdown("#### 💬 Room Discussion & AI Assistant")
            chat_box = st.container(height=260)
            for msg in room.get("chat", []):
                if msg["sender"] == "🤖 Vibe AI":
                    chat_box.info(f"**{msg['sender']}**: {msg['text']}")
                else:
                    chat_box.markdown(f"**{msg['sender']}**: {msg['text']}")
                    
            with st.form("chat_form_vibe", clear_on_submit=True):
                msg_input = st.text_input("Type your message or ask Vibe AI:", placeholder="Enter your text here...")
                c_btn1, c_btn2 = st.columns(2)
                btn_chat = c_btn1.form_submit_button("📤 Send to Room", use_container_width=True)
                btn_ai = c_btn2.form_submit_button("🤖 Ask Vibe AI", use_container_width=True)
                
                if msg_input.strip():
                    current_chat = room.get("chat", [])
                    if btn_chat:
                        current_chat.append({"sender": st.session_state.username, "text": msg_input})
                        sync_room_to_db(r_id, {"chat": current_chat})
                        st.rerun()
                    elif btn_ai:
                        current_chat.append({"sender": st.session_state.username, "text": msg_input})
                        with st.spinner("Vibe AI is answering your group doubt..."):
                            try:
                                ai_prompt = f"A student asked this in a study room. Give a concise, direct explanation: '{msg_input}'"
                                res = model.generate_content(ai_prompt)
                                current_chat.append({"sender": "🤖 Vibe AI", "text": res.text})
                            except:
                                current_chat.append({"sender": "🤖 Vibe AI", "text": "Error contacting AI server."})
                        sync_room_to_db(r_id, {"chat": current_chat})
                        st.rerun()

        with tab_people:
            st.markdown("#### 🟢 Active Members in Session")
            for p in room.get("participants", []): 
                badge = "👑 (Host)" if p == room.get("host") else "🎓 (Member)"
                st.markdown(f"🟢 **{p}** {badge}")