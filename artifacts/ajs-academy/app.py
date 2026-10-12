"""AJ's Academy: a single-family Streamlit application, with server-side role gates."""
import hashlib
import io
import math
import re
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from urllib.parse import quote
import pandas as pd
import streamlit as st
from PIL import Image
import store as db
import finance as fin
import content
import visuals as v
from schools import baseline

st.set_page_config(page_title="AJ’s Academy", page_icon=None, layout="wide", initial_sidebar_state="collapsed")
v.apply_theme()

PAGES = [
    ("Home", "home", "A little progress, every day"),
    ("My Investments", "investments", "Save for my future"),
    ("My College Dream", "college", "Discover where I could learn"),
    ("My Diary", "diary", "Tell the story of my day"),
    ("AJ’s Reminders", "reminders", "One small step at a time"),
    ("Soccer", "soccer", "Learn, play, and follow"),
    ("LEGO", "lego", "Build my next big idea"),
    ("AI Discoveries", "ai", "Explore how computers learn"),
    ("My Arcade", "arcade", "A game I built myself"),
    ("AJ’s Social Skills", "social", "Something new is coming"),
]

def go(page):
    st.session_state.page = page
    st.rerun()

def notify(message):
    st.session_state.notice = message
    st.rerun()

def safe_error(message, exc):
    # Never print provider errors, connection strings or private content into the browser.
    st.error(message)

def login(parent=False):
    if not parent:
        v.welcome_art()
        st.title("Your next adventure starts here.")
        st.write("Learn something. Try something. Grow a little.")
    else:
        v.hero("Parent portal", "A private place for the grown-up details.")
    with st.form("parent_login" if parent else "login"):
        role = "parent" if parent else st.radio("Who’s here?", ["AJ", "Parent"], horizontal=True)
        password = st.text_input("Parent password" if parent else "Your password", type="password")
        approval = ""
        if not parent:
            approval = st.text_input("Parent authorization for AJ’s session", type="password",
                                    help="A parent enters their password once to open a private child session. Not needed when signing in as Parent.")
        submit = st.form_submit_button("Let’s begin" if not parent else "Unlock parent portal", type="primary", use_container_width=True)
    if submit:
        target = "parent" if role in ("Parent","parent") else "child"
        if target == "child":
            authorized, reason = db.authenticate("parent", approval)
            if not authorized:
                st.error("A parent needs to authorize this session. " + reason)
                return
        ok, reason = db.authenticate(target, password)
        if ok:
            st.session_state.clear()
            st.session_state.role = target
            st.session_state.last_active = db.now().timestamp()
            st.session_state.page = "Parent portal" if target == "parent" else "Home"
            st.rerun()
        st.error(reason)
    st.caption("Private family access. A parent authorizes each new child session. Sessions expire after 30 minutes without interaction.")

if st.session_state.get("role") and db.now().timestamp() - st.session_state.get("last_active",0) > 1800:
    st.session_state.clear()
if not st.session_state.get("role"):
    login()
    st.stop()
st.session_state.last_active = db.now().timestamp()
parent = st.session_state.role == "parent"
state = db.load()
settings = state["settings"]
page = st.session_state.get("page","Home")

with st.sidebar:
    st.title("AJ’s Academy")
    st.caption("Little steps. Big possibilities.")
    st.metric("My points", f"{db.balance(state):,}")
    for label, _, _ in PAGES:
        if st.button(label, use_container_width=True, type="primary" if page == label else "secondary"):
            go(label)
    if st.button("Parent portal", use_container_width=True):
        go("Parent portal")
    if parent and st.button("Switch to AJ’s view", use_container_width=True):
        st.session_state.clear()
        st.session_state.role = "child"
        st.session_state.last_active = db.now().timestamp()
        go("Home")
    if st.button("Sign out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

nav = st.columns([2,1,1])
with nav[0]:
    if st.button("AJ’s Academy / Home", use_container_width=True):
        go("Home")
with nav[1]:
    st.caption(f"{db.now():%A, %B %d} · {db.balance(state):,} points")
with nav[2]:
    if st.button("Parent portal", key="top-parent", use_container_width=True):
        go("Parent portal")
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

def media(meta):
    try:
        raw = db.download(meta)
        if meta["mime"].startswith("image/"):
            st.image(raw, width=300)
        elif meta["mime"].startswith("audio/"):
            st.audio(raw)
        elif meta["mime"].startswith("video/"):
            st.video(raw)
    except Exception as exc:
        safe_error("This attachment could not be loaded. Please try again.", exc)

def photo_upload(file):
    image = Image.open(file)
    image.verify()
    image = Image.open(file).convert("RGB")
    image.thumbnail((1800,1800))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=85)  # strips EXIF location metadata
    return db.upload(out.getvalue(), "image/jpeg", "diary-photo.jpg")

def request_reward(item):
    def update(s):
        source = next((x for x in s["rewards"] + s["wishes"] if x["id"] == item["id"]), None)
        if not source or not source.get("approved"):
            raise ValueError("This reward needs parent approval first.")
        if any(r["item"] == source["id"] and r["status"] == "pending" for r in s["requests"]):
            return
        s["requests"].append({"id":uuid.uuid4().hex, "item":source["id"], "title":source["title"],
                              "points":source["points"], "status":"pending", "date":db.today()})
    db.change(update)
    notify("Your reward request is ready for your parent.")

def rewards():
    st.subheader("My reward shelf")
    st.caption("Your points carry over. Nothing resets at the end of the week.")
    items = [x for x in state["rewards"] + state["wishes"] if x.get("approved")]
    if not items:
        st.info("Your parent can add TV time, iPad time, pocket money, or a LEGO goal.")
    for item in items:
        with st.container(border=True):
            st.write("**" + item["title"] + "**")
            pts = item["points"]
            st.progress(min(1., max(0., db.balance(state)/max(1,pts))), text=f"{max(0,pts-db.balance(state)):,} points to go")
            if st.button(f"Ask for this reward · {pts:,} points", key="reward-"+item["id"], disabled=db.balance(state)<pts):
                request_reward(item)
    for r in state["requests"][-5:][::-1]:
        st.caption(f"{r['title']} · {r['status']}")

def home():
    v.hero("Hi AJ, what will you discover today?", "Pick a little adventure. Every small step counts.")
    done = sum(1 for key in state["completions"] if key.startswith(f"task:{db.today()}:"))
    a,b,c = st.columns(3)
    a.metric("Today’s small wins", f"{done} / {len(db.TASKS)}")
    b.metric("Points I’m saving", f"{db.balance(state):,}")
    c.metric("Practice days", len({p["date"] for p in state["practice"]}))
    for row in range(3):
        cols = st.columns(3)
        for col, (label,art,desc) in zip(cols, PAGES[1+row*3:4+row*3]):
            with col, st.container(border=True):
                v.illustration(art, 130)
                st.subheader(label)
                st.caption(desc)
                if st.button("Coming soon" if art=="social" else "Let’s explore", key="tile-"+art, use_container_width=True):
                    go(label)
    rewards()

def reminders():
    v.hero("Small steps, big smiles.", "Choose one thing. Give it a try. Celebrate your effort.")
    group = st.segmented_control("Time of day", ["Morning","After school","Evening","Extra kindness"], default="Morning")
    tasks = [t for t in db.TASKS if t[2] == group]
    for i in range(0,len(tasks),2):
        for col,t in zip(st.columns(2),tasks[i:i+2]):
            tid,label,_,art=t
            with col,st.container(border=True):
                v.illustration(art,120)
                st.subheader(label)
                points=settings["task_points"].get(tid,0) if settings["points_enabled"] else 0
                st.caption(f"Could earn {points} points" if points else "Points will be chosen together")
                completed=f"task:{db.today()}:{tid}" in state["completions"]
                if st.button("I did it!" if not completed else "Done for today",disabled=completed,key=tid,use_container_width=True):
                    db.complete_task(tid)
                    notify("Great effort! You finished a small step.")
    rewards()

QUESTIONS = ["What is the best part of the day?", "What made you sad or unhappy?", "What are you looking forward to tomorrow?"]

def diary():
    v.hero("A little space for my thoughts", "You and your parent can read this journal. All feelings are welcome.")
    write,history,weekly=st.tabs(["Today’s story","My past days","My week"])
    with write:
        if st.session_state.get("diary_day") != db.today():
            st.session_state.diary_day=db.today()
            entry=next((e for e in state["diary"] if e["date"]==db.today()),None)
            for i in range(3):
                st.session_state[f"answer-{i}"]=entry["answers"][i] if entry else ""
        for i,q in enumerate(QUESTIONS):
            st.subheader(q)
            if settings["transcription"]:
                audio=st.audio_input("Tell me in your own words",key=f"voice-{i}")
                if audio and st.button("Turn my voice into words",key=f"transcribe-{i}"):
                    try:
                        with st.spinner("Listening to your recording…"):
                            st.session_state[f"answer-{i}"]=content.transcribe(audio.getvalue())
                        st.success("Check the words below before saving.")
                    except Exception as exc:
                        safe_error("Transcription is unavailable. You can type, or try again.",exc)
                st.caption("Recording is sent to the AI service only when you choose transcription. Audio is not saved.")
            st.text_area("My answer",key=f"answer-{i}",max_chars=3000,label_visibility="collapsed")
        if not settings["transcription"]:
            st.caption("Voice mode is available after your parent enables transcription.")
        photos=st.file_uploader("Add a picture",type=["png","jpg","jpeg","webp"],accept_multiple_files=True)
        if st.button("Save my day",type="primary",use_container_width=True):
            answers=[st.session_state[f"answer-{i}"].strip() for i in range(3)]
            if not any(answers):
                st.warning("Tell us one thing about your day first.")
            elif len(photos)>3:
                st.warning("Choose up to three photos.")
            else:
                try:
                    uploaded=[photo_upload(p) for p in photos]
                    def save(s):
                        old=next((e for e in s["diary"] if e["date"]==db.today()),None)
                        if old:
                            old["answers"]=answers
                            old["photos"]=(old.get("photos",[])+uploaded)[-6:]
                        else:
                            s["diary"].append({"id":uuid.uuid4().hex,"date":db.today(),"answers":answers,"photos":uploaded})
                    db.change(save)
                    notify("Your day is saved. Thank you for sharing.")
                except Exception as exc:
                    safe_error("Your entry could not be saved. Your words are still here; please try again.",exc)
    with history:
        if not state["diary"]:
            st.info("Your first story will appear here.")
        for e in sorted(state["diary"],key=lambda x:x["date"],reverse=True):
            with st.expander(e["date"]):
                for q,a in zip(QUESTIONS,e["answers"]):
                    st.write("**"+q+"**");st.write(a or "Not answered")
                for p in e.get("photos",[]):media(p)
                if parent and st.checkbox("Confirm permanent deletion",key="confirm-"+e["id"]):
                    if st.button("Delete this entry",key="delete-"+e["id"]):
                        from google.api_core.exceptions import NotFound
                        for attachment in e.get("photos",[]):
                            try:
                                db.storage_client().bucket(attachment["bucket"]).blob(attachment["path"]).delete()
                            except NotFound:
                                pass
                        db.change(lambda s:s.__setitem__("diary",[x for x in s["diary"] if x["id"]!=e["id"]]))
                        notify("Entry and its attached photos deleted.")
    with weekly:
        cutoff=(db.now().date()-timedelta(days=6)).isoformat()
        recent=[e for e in state["diary"] if e["date"]>=cutoff]
        prev_start=(db.now().date()-timedelta(days=13)).isoformat()
        prev=[e for e in state["diary"] if prev_start<=e["date"]<cutoff]
        st.metric("Days I shared this week",len(recent),f"{len(recent)-len(prev):+} vs last week")
        st.caption("This measures journal participation, not emotional or developmental growth.")
        for i,label in [(0,"Good moments I shared"),(1,"Hard moments I shared"),(2,"Things I’m looking forward to")]:
            st.subheader(label)
            for e in recent:
                if e["answers"][i]:st.write(f"{e['date']}: {e['answers'][i]}")
        words=Counter(w.lower() for e in recent for a in e["answers"] for w in re.findall(r"[A-Za-z]{4,}",a)
                      if w.lower() not in {"that","this","with","have","were","there","about","because","tomorrow"})
        if words:
            st.subheader("Words from my week")
            st.write(" · ".join(f"{w} ({n})" for w,n in words.most_common(18)))
        else:st.info("After a few entries, your own words and themes will appear here.")

def soccer():
    v.hero("My soccer clubhouse", "Choose a skill. Give it a go. Practice is how we learn.")
    learn,play,follow=st.tabs(["Learn soccer","Play soccer","Follow soccer"])
    with learn:
        for col,d in zip(st.columns(3),content.DRILLS):
            with col,st.container(border=True):
                v.illustration(d["art"],120)
                st.subheader(d["title"])
                st.caption(d["skill"])
                if st.button("Pick this drill",key="pick-"+d["id"],use_container_width=True):
                    st.session_state.drill=d["id"]
        drill=next(d for d in content.DRILLS if d["id"]==st.session_state.get("drill","toetaps"))
        st.subheader(drill["title"])
        st.caption(drill["source"]+" · "+drill["note"])
        if drill["id"] in state["approved_videos"]:
            st.video(drill["url"])
            st.caption("YouTube may show ads or recommendations. Practice in a clear space with a grown-up nearby.")
        else:
            st.info("A parent needs to review this video before it plays here. You can still follow the picture steps.")
        for col,(n,step) in zip(st.columns(3),enumerate(drill["steps"],1)):
            with col:
                v.illustration(drill["art"],100)
                st.write(f"**Step {n}**");st.write(step)
        st.caption("Try for five minutes. Pause whenever you need to. The illustrations are practice cues, not copied video frames.")
    with play:
        st.subheader("Show what you tried")
        drill_id=st.selectbox("My drill",[d["id"] for d in content.DRILLS],format_func=lambda x:next(d["title"] for d in content.DRILLS if d["id"]==x))
        st.caption("Record a short clip with the iPad camera, then upload it here. Private to this family. Maximum 40 MB.")
        clip=st.file_uploader("My practice video",type=["mp4","mov","webm"])
        effort=st.text_input("What did I try?",max_chars=300)
        if st.button("Save my practice · 50 points",type="primary",disabled=not clip):
            try:
                if clip.size>40*1024*1024:raise ValueError("File too big")
                suffix=clip.name.rsplit(".",1)[-1].lower()
                meta=db.upload(clip.getvalue(),{"mp4":"video/mp4","mov":"video/quicktime","webm":"video/webm"}[suffix],"practice."+suffix)
                def update(s):
                    s["practice"].append({"id":uuid.uuid4().hex,"date":db.today(),"drill":drill_id,"note":effort,"video":meta})
                    return db.award(s,"soccer:"+db.today(),50,"Soccer practice")
                earned=db.change(update)
                notify("Practice saved! You earned 50 points." if earned else "Practice saved! Today’s 50 points were already earned.")
            except Exception as exc:
                safe_error("The video could not be saved. Try an MP4 under 40 MB.",exc)
        st.caption("One 50-point award per day. Uploads reward participation; the app does not grade technique.")
        for p in state["practice"][-8:][::-1]:
            with st.expander(p["date"]+" · "+p["drill"]):
                st.write(p["note"]);media(p["video"])
    with follow:
        news_reader(["Manchester United","Real Madrid","FC Barcelona","UEFA Nations League",
                     "Cristiano Ronaldo","Kylian Mbappe","Erling Haaland","Lamine Yamal"],"football soccer")

def news_reader(topics,suffix):
    topic=st.selectbox("Who shall we follow?",topics)
    st.caption("Source headlines may include adult topics. Open and read with a parent; no unrestricted browsing inside the app.")
    if st.button("Get latest headlines",key="news-"+suffix):
        try:
            with st.spinner("Checking sources…"):
                st.session_state["news-"+suffix]={"topic":topic,"items":content.news(topic+" "+suffix)}
        except Exception as exc:safe_error("News is unavailable right now. Please try again later.",exc)
    saved=st.session_state.get("news-"+suffix)
    if saved and saved["topic"]==topic:
        for n in saved["items"]:
            st.write("**"+n["title"]+"**")
            st.caption(n["published"])
            st.link_button("Read source with a parent",n["url"])

def lego():
    v.hero("Big ideas, one brick at a time", "Find an idea. Save a wish. Build toward it.")
    category=st.segmented_control("What would you like to build?",["STEM","Soccer","Space","Robots","Landmarks"],default="Space")
    v.illustration("lego",170)
    st.caption("Browse with a parent. Live prices and best-deal comparisons are not connected; no purchases happen here.")
    a,b=st.columns(2)
    a.link_button("Explore LEGO sets","https://www.lego.com/en-us/search?q="+quote(category or "Space"),use_container_width=True)
    b.link_button("Compare on Amazon with a parent","https://www.amazon.com/s?k="+quote("LEGO "+(category or "Space")),use_container_width=True)
    with st.form("wish"):
        title=st.text_input("What set would you like?",max_chars=150)
        link=st.text_input("Product link (optional)")
        if st.form_submit_button("Add to my wishlist",type="primary"):
            if not title.strip():st.warning("Give your wish a name.")
            elif link and not content.safe_link(link):st.warning("Please use a complete HTTPS product link.")
            else:
                db.change(lambda s:s["wishes"].append({"id":uuid.uuid4().hex,"title":title.strip(),"category":category,
                    "url":link,"approved":False,"points":0,"price":None}))
                notify("Wish saved! Your parent can set its points price.")
    for w in state["wishes"]:
        with st.container(border=True):
            st.write("**"+w["title"]+"**");st.caption(w["category"])
            if w.get("approved"):
                st.progress(min(1.,max(0.,db.balance(state)/max(1,w["points"]))),text=f"{w['points']:,} points")
                if st.button("Ask to redeem",key="wish-redeem-"+w["id"],disabled=db.balance(state)<w["points"]):request_reward(w)
            else:st.caption("Waiting for a parent to choose the points.")
            if not w.get("approved") and st.button("Remove wish",key="remove-"+w["id"]):
                db.change(lambda s:s.__setitem__("wishes",[x for x in s["wishes"] if x["id"]!=w["id"]]))
                notify("Wish removed.")

def ai():
    v.hero("Big ideas, made little", "Two stories to explore. One small experiment to try.")
    if not state["stories"]:
        v.illustration("ai",180)
        st.info("Your parent can prepare two stories from The Batch and add a Gen Academy update. Approved stories will appear here.")
    for story in sorted(state["stories"],key=lambda x:x["date"],reverse=True):
        if not story.get("approved"):continue
        with st.container(border=True):
            st.subheader(story["title"])
            st.caption(f"{story['source']} · Added {story['date']} · AI-assisted, parent reviewed")
            st.write(story["story"])
            st.write("**Try this together**");st.write(story["challenge"])
            st.write(story["question"])
            if story.get("url"):st.link_button("Original source",story["url"])
            key="ai:"+story["id"]
            done=any(x["key"]==key for x in state["ledger"])
            if st.button("I tried the challenge!" if not done else "Challenge tried",disabled=done,key=key):
                db.change(lambda s:db.award(s,key,s["settings"]["ai_points"],"AI discovery challenge"))
                notify("Well done for trying a new idea!")

def arcade():
    v.hero("I built this!", "Your own creation deserves a special place.")
    v.illustration("arcade",220)
    deadline=settings.get("arcade_until")
    weekend=db.now().weekday()>=5
    unlocked=bool(deadline and datetime.fromisoformat(deadline)>db.now() and (weekend or settings.get("arcade_override")))
    if unlocked:
        st.success("Your parent has unlocked the arcade. Have fun!")
        st.link_button("Play my mini arcade","https://ajs-miniarcade-activities.lovable.app/",type="primary",use_container_width=True)
        st.caption("Unlock ends "+datetime.fromisoformat(deadline).strftime("%A at %I:%M %p"))
    else:
        st.info("Your arcade is resting. Ask a parent to unlock it for the weekend.")
    st.caption("No points needed—you built this. This lock controls the Academy link, not direct access to the external game.")

def investments():
    v.hero("Little savings, big possibilities", "Owning a stock means owning a tiny part of a company.")
    for col,(art,title) in zip(st.columns(3),[("home","My first home"),("vacation","A vacation each year"),("car","My first car")]):
        with col,st.container(border=True):v.illustration(art,140);st.subheader(title)
    if settings.get("custody_balance") is not None:
        nominal=settings["goal"]*(1+settings["inflation"]/100)**13
        progress=min(1.,max(0.,settings["custody_balance"]/nominal))
        st.progress(progress,text=f"{progress:.1%} toward my future savings goal")
        st.caption("Based on a balance entered by your parent—not a live account value. These dreams share one savings goal.")
    else:st.info("Your parent is checking the account balance. Your progress will appear once it is confirmed.")
    st.write("**A good investor asks questions:** What does the company do? Can it earn money? What could go wrong?")
    st.write("Spreading savings across different investments can reduce the risk of depending on just one company.")
    data=state["finance"].get("custody")
    if data:
        symbols=sorted({r["Symbol"] for r in data["records"] if r["Symbol"] not in ("--","MSPBNA")})
        symbol=st.selectbox("Explore a company from the account history",symbols)
        st.caption("A symbol in this list does not mean you still own it.")
        if st.button("See its market performance"):
            try:
                with st.spinner("Checking historical prices…"):
                    prices=fin.market_history(symbol,data["start"])
                change=(float(prices.iloc[-1,0])/float(prices.iloc[0,0])-1)*100
                st.metric("Adjusted market price change",f"{change:+.1f}%")
                st.line_chart(prices/prices.iloc[0]*100,y_label="Starting value = 100")
                st.caption(f"Yahoo Finance via yfinance · {prices.index[0].date()} to {prices.index[-1].date()}. Adjusted prices include corporate-action adjustments. This is not your personal account return.")
            except Exception as exc:safe_error("Market history is unavailable for this symbol. No return has been estimated.",exc)
        news_reader([symbol],"stock company")
    if parent:
        st.divider();finance_parent("custody")

def college():
    v.hero("Where could my curiosity take me?", "Build things. Start a business. Play soccer.")
    favorite=st.selectbox("Explore a school",[s[0] for s in fin.SCHOOLS],index=[s[0] for s in fin.SCHOOLS].index(settings["favorite_school"]))
    school=next(s for s in fin.SCHOOLS if s[0]==favorite)
    v.illustration("college",200)
    st.subheader(school[0]);st.write(school[3])
    st.caption(f"{school[1]} · {school[2]}")
    if st.button("Save as my dream school"):
        db.change(lambda s:s["settings"].__setitem__("favorite_school",favorite));notify("Dream school saved. You can change your mind anytime.")
    data=state["finance"].get("college")
    costs=settings["school_costs"].get(f"{favorite}|{settings['residency']}",baseline(favorite,settings["residency"]))
    if data and costs:
        goal=fin.future_cost(costs["annual"],settings["college_years"],settings["college_inflation"])
        pct=min(1.,data["balance"]/max(1,goal))
        st.progress(pct,text=f"{pct:.1%} toward our college cost estimate")
    else:st.info("Your parent is setting up this school’s full-cost estimate.")
    st.caption("These are places to explore, not promises of admission or a professional soccer career. College soccer and professional soccer are different.")
    if parent:st.divider();finance_parent("college")

def finance_parent(kind):
    if not parent:st.stop()
    data=state["finance"].get(kind)
    st.subheader("529 savings details" if kind=="college" else "Custodial account details")
    f=st.file_uploader("Replace the account export",type=["csv"],key="csv-"+kind)
    if f and st.button("Import this CSV",key="import-"+kind):
        try:
            parsed=fin.parse_csv(f.getvalue(),kind)
            db.change(lambda s:s["finance"].__setitem__(kind,parsed));notify("Import saved. Account identifiers were removed.")
        except Exception as exc:st.error(str(exc) if isinstance(exc,ValueError) else "Import could not be saved.")
    if not data:
        st.info("Upload the account export to begin.");return
    st.caption(f"Export history: {data['start']} through {data['end']} · {len(data['records'])} records")
    if kind=="college":
        monthly=fin.contribution_summary(data)
        a,b=st.columns(2)
        a.metric("Exported balance",f"${data['balance']:,.2f}")
        b.metric("Contributions within export",f"${sum(monthly.values()):,.2f}")
        st.caption("Balance is from the uploaded snapshot; its exact valuation date is not supplied. Contributions are not investment growth.")
        st.warning("The holding is a 2040–2041 enrollment portfolio, while the requested college start is about 2037. Review the intended enrollment year with your plan provider.")
        st.write("Current portfolio: "+data["fund"])
        st.bar_chart(pd.DataFrame({"Month":monthly.keys(),"Contributions":monthly.values()}).set_index("Month"))
        st.caption("Fund conversions are internal movements, not contributions or investment gains. Accurate historical account returns need a dated opening balance.")
        school_name=st.selectbox("School for cost planning",[x[0] for x in fin.SCHOOLS],key="cost-school")
        school=next(x for x in fin.SCHOOLS if x[0]==school_name)
        residency=st.radio("Residency scenario",["Florida","California"],index=0 if settings["residency"]=="Florida" else 1,horizontal=True)
        key=school_name+"|"+residency
        old=settings["school_costs"].get(key,baseline(school_name,residency))
        st.link_button("Official school cost-of-attendance source",school[4])
        st.caption("Use tuition, mandatory fees, housing, meals, books, travel, and personal expenses. Residency eligibility is conditional. No scholarships assumed.")
        st.info(old["note"])
        base=st.number_input("Annual published budget ($)",min_value=0.,value=float(old.get("annual",0))-float(old.get("travel",0))-float(old.get("extras",0)),step=1000.,key="annual-"+key)
        travel=st.number_input("Additional annual travel not already included ($)",min_value=0.,value=float(old.get("travel",0)),step=100.,key="travel-"+key)
        extras=st.number_input("Additional annual insurance / other costs ($)",min_value=0.,value=float(old.get("extras",0)),step=100.,key="extras-"+key)
        annual=base+travel+extras
        cost_date=st.text_input("Cost academic year / source note",value=old.get("note",""),key="cost-note-"+key)
        years=st.number_input("Years until college",1,25,int(settings["college_years"]))
        inflation=st.slider("Annual college-cost increase (%)",0.,10.,float(settings["college_inflation"]),.5)
        if st.button("Save college assumptions"):
            if annual<=0:st.warning("Enter a sourced annual full cost first.")
            else:
                def save(s):
                    s["settings"].update(residency=residency,college_years=years,college_inflation=inflation)
                    s["settings"]["school_costs"][key]={"annual":annual,"note":cost_date,"updated":db.today(),"travel":travel,"extras":extras}
                db.change(save);notify("College assumptions saved.")
        if annual>0:
            target=fin.future_cost(annual,years,inflation)
            st.metric("Projected four-year full cost",f"${target:,.0f}")
            st.dataframe(pd.DataFrame([{"Assumed annual return":f"{r}%","Monthly saving":round(fin.payment(data["balance"],target,years,r))} for r in [3,5,7]]),hide_index=True)
            st.caption("Contributions at month-end until enrollment; conservative assumption that all four years are funded by then, with no further return during college. Scenarios are not guarantees. Travel and personal costs generally are not qualified 529 expenses.")
    else:
        frame=fin.positions(data)
        st.dataframe(frame,hide_index=True,use_container_width=True)
        st.caption("Net unit changes within this export—not verified holdings. Opening positions, transfers, splits, exchanges and cancelled trades may affect reconciliation. Trade cash flow is not profit.")
        with st.form("balance"):
            amount=st.number_input("Confirmed current account balance",min_value=0.,value=float(settings.get("custody_balance") or 0),step=100.)
            asof=st.date_input("Balance as of")
            target=st.number_input("Age-21 target in today’s dollars",min_value=1000.,value=float(settings["goal"]),step=10000.)
            infl=st.slider("Inflation assumption (%)",0.,8.,float(settings["inflation"]),.5)
            if st.form_submit_button("Save parent-only figures"):
                db.change(lambda s:s["settings"].update(custody_balance=amount,custody_asof=asof.isoformat(),goal=target,inflation=infl))
                notify("Private savings assumptions saved.")
        future=target*(1+infl/100)**13
        st.metric("Inflation-adjusted age-21 target",f"${future:,.0f}")
        st.dataframe(pd.DataFrame([{"Annual return assumption":f"{r}%","Monthly contribution":round(fin.payment(amount,future,13,r)),
                                   "Annual contribution":round(fin.payment(amount,future,13,r)*12)} for r in [3,5,7]]),hide_index=True)
        st.caption("13-year horizon; monthly end-of-month deposits, annual effective returns, no taxes or fees modeled. Returns are uncertain; these are planning scenarios, not investment advice.")
        st.info("Personal realized gains, total return, and allocation by current market value remain unverified until we reconcile opening holdings and current positions. The exported “Total” is not treated as an account balance.")
    with st.expander("Sanitized transaction report"):
        df=pd.DataFrame(data["records"])
        st.dataframe(df,hide_index=True)
        st.download_button("Download this report",df.to_csv(index=False).encode(),"transactions.csv","text/csv",key="download-"+kind)

def parent_portal():
    if not parent:
        login(parent=True)
        return
    v.hero("The grown-up corner", "Encourage the effort. Adjust the plan. Keep the important things private.")
    st.info("Private family prototype. Each new child session requires parent authorization. Do not share your parent password; use “Switch to AJ’s view” to hand over the iPad.")
    tab=st.selectbox("Manage",["Points & tasks","Rewards & wishlist","Arcade access","Diary & privacy","Soccer videos","AI story studio","Financial reports"])
    if tab=="Points & tasks":
        with st.form("settings"):
            enabled=st.toggle("Award points for routines",value=settings["points_enabled"])
            st.caption("Task values start at zero until you choose them. Changing a value affects future completions, not past points.")
            points={tid:st.number_input(label+" points",0,10000,int(settings["task_points"].get(tid,0)),key="pts-"+tid) for tid,label,_,_ in db.TASKS}
            aip=st.number_input("AI challenge points",0,10000,int(settings["ai_points"]))
            if st.form_submit_button("Save point settings"):
                db.change(lambda s:s["settings"].update(task_points=points,points_enabled=enabled,ai_points=aip));notify("Point settings saved.")
        with st.form("adjust"):
            delta=st.number_input("Adjust points (+ or −)",-100000,100000,0)
            reason=st.text_input("Reason",max_chars=150)
            if st.form_submit_button("Apply adjustment"):
                if not reason.strip():st.warning("Add a reason.")
                elif db.balance(state)+delta<0:st.warning("The balance cannot be negative.")
                else:
                    def adjust(s):
                        if db.balance(s)+delta<0:raise ValueError("Balance changed; refresh.")
                        db.award(s,"adjust:"+uuid.uuid4().hex,delta,reason)
                    db.change(adjust);notify("Points adjusted.")
        st.dataframe(pd.DataFrame(state["ledger"]),hide_index=True)
    elif tab=="Rewards & wishlist":
        rate=st.number_input("Default points per dollar",1,10000,int(settings["conversion"]))
        st.caption("Suggested starting rate only; not active until you save it. Existing approved rewards keep their points price.")
        if st.button("Save conversion rate"):
            db.change(lambda s:s["settings"].update(conversion=rate,conversion_confirmed=True));notify("Conversion rate saved.")
        for w in state["wishes"]:
            with st.expander(w["title"]):
                if w.get("url"):st.link_button("Check current product price",w["url"])
                price=st.number_input("Verified price ($)",0.,10000.,float(w.get("price") or 0),key="price-"+w["id"])
                default=math.ceil(price*rate)
                points=st.number_input("Points price (override allowed)",0,10000000,int(w["points"] if w.get("approved") else default),key=f"wishpts-{w['id']}-{default}")
                st.caption("No live price verification. Include tax or shipping if desired.")
                if st.button("Approve / update reward",key="approve-"+w["id"],disabled=not settings["conversion_confirmed"]):
                    def update(s):
                        item=next(x for x in s["wishes"] if x["id"]==w["id"])
                        item.update(price=price,points=points,approved=True,priced_at=db.today())
                    db.change(update);notify("Reward approved.")
        with st.form("newreward"):
            title=st.text_input("Reward name (TV time, iPad time, pocket money…)",max_chars=150)
            pts=st.number_input("Points needed",0,100000,100)
            if st.form_submit_button("Add reward"):
                if title.strip():
                    db.change(lambda s:s["rewards"].append({"id":uuid.uuid4().hex,"title":title.strip(),"points":pts,"approved":True}));notify("Reward added.")
        for r in state["requests"]:
            if r["status"]!="pending":continue
            st.write(f"**{r['title']}** · {r['points']} points")
            a,b=st.columns(2)
            if a.button("Approve redemption",key="redeem-"+r["id"]):
                try:db.approve_redemption(r["id"]);notify("Approved. Points deducted once.")
                except ValueError as exc:st.warning(str(exc))
            if b.button("Decline",key="decline-"+r["id"]):
                def decline(s):next(x for x in s["requests"] if x["id"]==r["id"])["status"]="declined"
                db.change(decline);notify("Request declined; no points deducted.")
    elif tab=="Arcade access":
        st.write("Weekend access requires a parent unlock. It never costs points.")
        override=st.checkbox("Allow a special weekday session",value=False)
        if st.button("Unlock for this weekend" if db.now().weekday()>=5 else "Unlock arcade",disabled=db.now().weekday()<5 and not override):
            now=db.now()
            deadline=(now+timedelta(days=(7-now.weekday())%7 or 7)).replace(hour=0,minute=0,second=0,microsecond=0) if now.weekday()>=5 else now+timedelta(hours=2)
            db.change(lambda s:s["settings"].update(arcade_until=deadline.isoformat(),arcade_override=override));notify("Arcade unlocked.")
        if st.button("Lock now"):
            db.change(lambda s:s["settings"].update(arcade_until="",arcade_override=False));notify("Arcade locked.")
    elif tab=="Diary & privacy":
        allow=st.toggle("Enable voice-to-text transcription",value=settings["transcription"])
        st.caption("When used, audio is sent to OpenAI through Replit AI Integrations. Only the reviewed text is saved; original audio is not stored. AI usage uses credits. You can read every entry.")
        if st.button("Save privacy setting"):
            db.change(lambda s:s["settings"].__setitem__("transcription",allow));notify("Privacy setting saved.")
        if st.button("Read all diary entries"):go("My Diary")
    elif tab=="Soccer videos":
        st.caption("Review the complete video, duration, language and embedding behavior before approving. YouTube may show ads and recommendations.")
        selected=[]
        for d in content.DRILLS:
            st.subheader(d["title"]);st.video(d["url"]);st.caption(d["source"]+" · "+d["note"])
            if st.checkbox("Approved for AJ",value=d["id"] in state["approved_videos"],key="approve-video-"+d["id"]):selected.append(d["id"])
        if st.button("Save video approvals"):
            db.change(lambda s:s.__setitem__("approved_videos",selected));notify("Video approvals saved.")
    elif tab=="AI story studio":
        st.caption("Prepare two stories from The Batch each week, plus suitable Gen Academy posts when available. All generated stories require your review.")
        st.link_button("The Batch","https://www.deeplearning.ai/the-batch/")
        st.link_button("The Gen Academy","https://thegenacademy.com/")
        st.link_button("Aishwarya Srinivasan on LinkedIn","https://www.linkedin.com/in/aishwarya-srinivasan/")
        if st.button("Find public Batch articles"):
            try:st.session_state.articles=content.batch_articles()
            except Exception as exc:safe_error("Could not read The Batch. You can paste a source excerpt below.",exc)
        articles=st.session_state.get("articles",[])
        if articles:
            selected=st.selectbox("Article",range(len(articles)),format_func=lambda i:articles[i]["title"])
            if st.button("Prepare selected article"):
                try:
                    with st.spinner("Preparing a child-friendly draft…"):
                        a=articles[selected];draft=content.simplify(content.article_text(a["url"]))
                        st.session_state.draft={**draft,"source":"The Batch","url":a["url"]}
                except Exception as exc:safe_error("The draft could not be prepared. Paste the source text below or try again.",exc)
        with st.expander("Use a Gen Academy post or another Batch excerpt"):
            src=st.selectbox("Source",["The Gen Academy / Aishwarya Srinivasan","The Batch"])
            url=st.text_input("Original public source link")
            text=st.text_area("Paste the source excerpt",max_chars=16000)
            st.caption("LinkedIn is not automatically monitored. Paste posts you have access to; do not paste private information.")
            if st.button("Prepare a story and challenge"):
                if len(text.strip())<50:st.warning("Paste enough source text to summarize.")
                elif url and not content.safe_link(url):st.warning("Use an HTTPS source link.")
                else:
                    try:
                        with st.spinner("Preparing draft…"):st.session_state.draft={**content.simplify(text),"source":src,"url":url}
                    except Exception as exc:safe_error("AI drafting is unavailable. Please try again later.",exc)
        draft=st.session_state.get("draft")
        if draft:
            with st.form("publishstory"):
                title=st.text_input("Review title",value=draft["title"])
                story=st.text_area("Review story",value=draft["story"])
                challenge=st.text_area("Review challenge",value=draft["challenge"])
                question=st.text_input("Reflection",value=draft["question"])
                if st.form_submit_button("Approve for AJ"):
                    db.change(lambda s:s["stories"].append({**draft,"id":uuid.uuid4().hex,"title":title,"story":story,
                        "challenge":challenge,"question":question,"date":db.today(),"approved":True}))
                    del st.session_state.draft;notify("Story approved and available to AJ.")
    elif tab=="Financial reports":
        kind=st.radio("Account",["custody","college"],format_func=lambda x:"Custodial account" if x=="custody" else "529 college plan",horizontal=True)
        finance_parent(kind)

try:
    if page=="Home":home()
    elif page=="My Investments":investments()
    elif page=="My College Dream":college()
    elif page=="My Diary":diary()
    elif page=="AJ’s Reminders":reminders()
    elif page=="Soccer":soccer()
    elif page=="LEGO":lego()
    elif page=="AI Discoveries":ai()
    elif page=="My Arcade":arcade()
    elif page=="AJ’s Social Skills":
        v.hero("AJ’s Social Skills", "A new place to learn, together.")
        v.illustration("social",230)
        st.info("Coming soon. We’ll choose these activities together. Nothing here is assessed or scored.")
    elif page=="Parent portal":parent_portal()
except Exception:
    st.error("This section could not load. Please refresh or try again shortly. Private details have not been displayed.")
