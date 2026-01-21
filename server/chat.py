from flask import Flask, request, session, g, current_app
from flask_socketio import emit, join_room, leave_room
from datetime import timezone, datetime
from sqlalchemy import func, exists, and_, select, case, tuple_, or_
from sqlalchemy.orm import aliased
import uuid
import logging
import traceback
from .extensions import socketio, r, db
from .models import Thread, ThreadUser, Message, MessageReaction, User, BlockedUsers, MessageAttachment, FileUpload, Notification
from collections import defaultdict, Counter
import os
from urllib.parse import urljoin
from time import time
import math
import bleach
from .blog import is_effectively_empty, sanitize_title, TITLE_RE
import regex
import boto3
from pathlib import Path

#Logger for current app: current_app.logger.debug(f"JOIN THREAD OK ok sid={request.sid} user={user_id} threadId={thread_id}")



WASABI_ENDPOINT = os.getenv('WASABI_ENDPOINT')
WASABI_ACCESS_KEY   = os.getenv('WASABI_ACCESS_KEY')
WASABI_SECRET_KEY   = os.getenv('WASABI_SECRET_KEY')
WASABI_REGION   = os.getenv('WASABI_REGION')
WASABI_BUCKET   = os.getenv('WASABI_BUCKET')
WASABI_PREFIX   = os.getenv('WASABI_PREFIX')



chat_logger = logging.getLogger("chat")
chat_logger.setLevel(logging.ERROR)
chat_handler = logging.handlers.WatchedFileHandler("/home/webserver/logs/chat_exceptions.log")
chat_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
if not chat_logger.hasHandlers():
    chat_logger.addHandler(chat_handler)


allowed_tags = [
    'p', 'b', 'i', 'u', 'strong', 'em', 'ul', 'ol', 'li', 'br',
    'a', 'span', 'blockquote', 'attachment',
]

allowed_attrs = {
    'a': ['href', 'target', 'rel'],
    'attachment': ['data-id','data-kind'],
    'span' : ['class'],
}

allowed_protocols = ["https", "mailto"]


SID_TO_USER, SID_MAP_KEY = {}, "sid_to_user"


def _set_sid(uid):
    if r: r.hset(SID_MAP_KEY, request.sid, uid)
    else: SID_TO_USER[request.sid] = uid


def _del_sid():
    if r: r.hdel(SID_MAP_KEY, request.sid)
    else: SID_TO_USER.pop(request.sid, None)
    

def _thread_room(thread_id) -> str:
    return f"thread:{thread_id}"
    
    
def _user_room(uid: int) -> str:
    return f"user:{uid}"


def _current_user_id():
    if r:
        uid = r.hget(SID_MAP_KEY, request.sid)
        if uid is None:
            return None
        if isinstance(uid, bytes):
            uid = uid.decode()
        return int(uid) if uid.isdigit() else None
    return SID_TO_USER.get(request.sid)


BUCKET = 20      
REFILL = 10    
WINDOW = 1 
    
    
def allow_event(r, key):
    now = int(time())
    k_now  = f"rl:{key}:{now}"
    k_prev = f"rl:{key}:{now-1}"
    pipe = r.pipeline()
    pipe.incr(k_now, 1)
    pipe.expire(k_now, WINDOW+1)
    used_now, _ = pipe.execute()
    used_prev = int(r.get(k_prev) or 0)
    return (used_now + used_prev) <= (BUCKET + REFILL)
  
  
def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)
    
       
def _user_in_thread(thread_id: int, user_id: int) -> bool:
    return db.session.query(db.exists().where(ThreadUser.thread_id == thread_id, ThreadUser.user_id == user_id)).scalar()
    
    
def to_iso_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:                      
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


ALLOWED_ORIGIN = [os.getenv('FRONTEND_URL'), os.getenv('FRONTEND_URL2'), "capacitor://localhost", "http://localhost", "https://localhost"]
@socketio.on('connect')
def on_connect(auth):
    origin = request.headers.get("Origin")
    if not origin or origin not in ALLOWED_ORIGIN:
        return False
    
    expected = session.get("ws_csrf")
    presented = (auth or {}).get("csrf")
    if not expected or not presented or expected != presented:
        return False
    
    user_id = session.get('user_id')
    if not user_id:
        return False
   
    _set_sid(int(user_id))
    me = _current_user_id() or int(user_id)
    
    if not me:
        return False
    
    if not allow_event(r, me):
        return False
    join_room(_user_room(me))

@socketio.on('disconnect')
def on_disconnect():
    _del_sid()
    return
     
####################################################################################################################
######################################################Chat##########################################################
####################################################################################################################   
   
   
@socketio.on('get_threads')
def get_threads():
 
    me = _current_user_id()
    if not me:
        return []
        
    if not allow_event(r, me):
        return []
        
    join_room(_user_room(me))
    me_link = aliased(ThreadUser)
    msgs = aliased(Message) 
    su   = aliased(User)

    blocked_ids_q = db.session.query(BlockedUsers.blocked_id).filter(BlockedUsers.blocker_id == me)
    blockers_ids_q = db.session.query(BlockedUsers.blocker_id).filter(BlockedUsers.blocked_id == me)
    forbidden_ids_q = blocked_ids_q.union(blockers_ids_q)

    other_participant_exists = exists(select(1).select_from(ThreadUser).join(User, User.id == ThreadUser.user_id).where(ThreadUser.thread_id == Thread.id, ThreadUser.user_id != me, User.is_suspended.is_(False),~ThreadUser.user_id.in_(forbidden_ids_q),)).correlate(Thread)  
    
    lr = func.coalesce(me_link.last_read_message_id, 0)
    usernames_expr = func.group_concat(func.distinct(User.username).op("ORDER BY")(User.username)).label("usernames_csv")
    
    q = (db.session.query(Thread.id, Thread.title, Thread.last_message_at, me_link.last_read_message_id.label("my_last_read_message_id"), usernames_expr, func.count(func.distinct(msgs.id)).label("unread"),).join(me_link, me_link.thread_id == Thread.id).filter(me_link.user_id == me).join(ThreadUser, ThreadUser.thread_id == Thread.id).join(User, User.id == ThreadUser.user_id).filter(ThreadUser.user_id != me, other_participant_exists,).outerjoin(msgs, and_(msgs.thread_id == Thread.id, msgs.id > lr, msgs.sender_id != me, msgs.sender_id != 0,),).outerjoin(su, and_(su.id == msgs.sender_id, su.is_suspended.is_(False),),).group_by(Thread.id, Thread.title, Thread.last_message_at, me_link.last_read_message_id).order_by(Thread.last_message_at.is_(None), Thread.last_message_at.desc()))
    rows = q.all()

    def iso(dt):
        if not dt:
            return None
        return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    threads = []
    for tid, title, last_at, my_last_read_id, usernames_csv, unread in rows:
    
        usernames = usernames_csv.split(",") if usernames_csv else []

        threads.append({
            "id": tid,
            "title": title,
            "lastMessageAt": iso(last_at),
            "lastReadMessageId": my_last_read_id,
            "participants": usernames,
            "unread": int(unread or 0),
        })

    return threads    
    
    
    
@socketio.on('join_thread')
def on_join_thread(data):
    user_id = _current_user_id()
    if not user_id:
        return
     
    if not allow_event(r, user_id):
        return
    try:
        thread_id = int(data.get('threadId'))
    except (TypeError, ValueError):
        return
         
    if not thread_id:
        return
    
    if not _user_in_thread(thread_id, user_id):
        return
    join_room(_thread_room(thread_id))


PUBLIC_BASE_URL = os.getenv('FRONTEND_URL')
def abs_url(path: str) -> str:
    path = "/api/" + path.lstrip("/")
    return urljoin(PUBLIC_BASE_URL, path)




def serialize_upload(fu):    
    variants = getattr(fu, 'variants', None)
    url = None
    thumbnail = None
    if not variants:
        url = abs_url(f"static/uploads/{os.path.basename(fu.path)}")
        if fu.thumbnail is not None:
            thumbnail = abs_url(f"static/uploads/{os.path.basename(fu.thumbnail)}")
    else:
        for k, v in list(variants.items()):
            variants[k] = abs_url(v)

    return {
        "id": int(fu.id),
        "mime": fu.mime,
        "variants": variants,
        "url": url,
        "w_variants": fu.w_variants,
        "w_path": fu.w_path,
        "width": getattr(fu, 'width', None),
        "height": getattr(fu, 'height', None),
        "duration_sec": getattr(fu, 'duration_sec', None),
        "status": fu.status,
        "name": fu.filename,
        "thumbnail": thumbnail
    }



@socketio.on('load_thread')
def on_load_thread(data):
    
    user_id = _current_user_id()
    
    if not user_id:
        return []
    if not allow_event(r, user_id):
        return []
    try:
        thread_id = int(data.get('threadId'))
    except (TypeError, ValueError):
        return []
        
    if not thread_id or not _user_in_thread(thread_id, user_id):
        return []

    messages = (db.session.query(Message).join(User, User.id == Message.sender_id).filter(Message.thread_id==thread_id, User.is_suspended.is_(False)).order_by(Message.created_at.asc()).all())
    if not messages:
        return []
    
    last_read_id = (db.session.query(ThreadUser.last_read_message_id).filter(ThreadUser.thread_id == thread_id, ThreadUser.user_id == user_id).scalar()) or 0
    
    message_ids = [m.id for m in messages]
    atts = (db.session.query(MessageAttachment.message_id, FileUpload).join(FileUpload, FileUpload.id == MessageAttachment.file_upload_id).filter(MessageAttachment.message_id.in_(message_ids)).all())
    
    attachs_by_message = defaultdict(list)
    for cid, fu in atts:
        attachs_by_message[cid].append(fu)
    
    rx_rows = (db.session.query(MessageReaction.message_id, MessageReaction.user_id, MessageReaction.emoji, User.username,).join(User, User.id == MessageReaction.user_id).filter(MessageReaction.message_id.in_(message_ids),User.is_suspended.is_(False),).all())
    raw_by_msg = defaultdict(list)
    counts_by_msg = defaultdict(Counter)
    
    for mid, uid, emoji, username in rx_rows:
        if emoji:
            raw_by_msg[mid].append({"userId": uid, "username":username , "emoji": emoji})
            counts_by_msg[mid][emoji] += 1
            
    first_unread_id = None
    for m in messages:
        if m.id > last_read_id and m.sender_id != user_id and m.sender_id != 0:
            first_unread_id = m.id
            break
        
    out = []
    for m in messages:
        attachs = attachs_by_message.get(m.id, [])
    
        d = m.to_dict()
        raw = raw_by_msg.get(m.id, [])
        cnt = counts_by_msg.get(m.id, Counter())
        d["isFirstUnread"] = (m.id == first_unread_id)
        d["reactions"] = raw
        d["reactionCounts"] = [{"emoji": e, "count": c} for e, c in cnt.most_common()]
        d["attachments"] = [serialize_upload(a) for a in attachs]
        out.append(d)
        
    return out




@socketio.on('send')
def send_message(data):
    try:
        user_id = _current_user_id()
        thread_id = data.get('threadId')
    
        try:
            thread_id = int(data.get('threadId'))
        except (TypeError, ValueError):
            return
    
        text = (data.get('text') or '').strip()
    
        try:
            parentId = int(data.get('pId'))
        except:
            parentId = None
    
        att_ids = data.get('attachment_ids') or []
    
        if not (user_id and thread_id and (text or att_ids)):
            return
        if not _user_in_thread(thread_id, user_id):
            return       
        if not allow_event(r, user_id):
            return
        
        try:
            att_ids = [int(str(i).strip()) for i in att_ids]
        except (TypeError, ValueError):
            return      
        if len(att_ids) != len(set(att_ids)):
            return
        
        uploads = []
        if att_ids:
            uploads = (FileUpload.query.filter(FileUpload.id.in_(att_ids)).all())
            found = {u.id for u in uploads}
            missing = [i for i in att_ids if i not in found]
            if missing:
                return
            bad = [u.id for u in uploads if u.status != 'approved']
            if bad:
                return       
            foreign = [u.id for u in uploads if u.user_id != user_id]
            if foreign:
                return
    
        text = bleach.clean(text, tags=allowed_tags, attributes=allowed_attrs, protocols=allowed_protocols, strip=True)
        if is_effectively_empty(text) and not att_ids:
            return
    
        message = Message(thread_id=thread_id, sender_id=user_id, text=text, parent_id=parentId)
        db.session.add(message)
        db.session.flush()    
    
        for u in uploads:
            db.session.add(MessageAttachment(message_id=message.id, file_upload_id=u.id))
    
        thread = Thread.query.get(thread_id)
        thread.last_message_id = message.id
        thread.last_message_at = message.created_at
    
        db.session.commit()
    
        payload = { **message.to_dict(), "attachments": [serialize_upload(u) for u in uploads] }
        emit("message", payload, room=_thread_room(thread_id))
        return 
       
    except Exception:
        chat_logger.error(f"[{datetime.utcnow()}] USER_ID: {me} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        db.session.rollback()
        return






def _find_exact_thread(participants: set[int]) -> Thread | None:
    if not participants:
        return None

    total_members = (select(func.count()).where(ThreadUser.thread_id == Thread.id)).correlate(Thread).scalar_subquery()
    required_exists = and_(*[exists().where((ThreadUser.thread_id == Thread.id) & (ThreadUser.user_id == uid)) for uid in participants])

    return (db.session.query(Thread).filter(required_exists).filter(total_members == len(participants)).first())

    
@socketio.on('create_thread')
def on_create_thread(data):
    
    me = _current_user_id()
    if not me:
        return
    if not allow_event(r, me):
        return

    incoming = data.get('participantIds') or []
    try:
        part_ids = {int(x) for x in incoming if x is not None}
    except Exception:
        return
        
    usernames = [u.username for u in db.session.query(User).filter(User.id.in_(part_ids)).all()]
    part_ids.add(me)
    
    if len(part_ids) < 2:
        return 

    title = (data.get('title') or '').strip() or None    
    if title:
        title = sanitize_title(title)
        if not title:
            return
    
    thread = _find_exact_thread(part_ids)
    
    if not thread:
        is_new = True
        thread = Thread(title=title, created_at=utcnow_naive())
        db.session.add(thread)
        db.session.flush()
        db.session.bulk_save_objects([ThreadUser(thread_id=thread.id, user_id=uid) for uid in part_ids])
        db.session.commit()
    
    join_room(_thread_room(thread.id))
    if is_new:
        for uid in part_ids:
            if uid == me:
                continue
            emit("threads_refresh", {}, room=_user_room(uid), include_self=False)
    
    payload = {"id": thread.id, "title": thread.title, "participants": usernames, "lastMessageAt": (thread.last_message_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z") if thread.last_message_at else None ),}
    return payload
    
    
@socketio.on('search_thread')
def on_search_thread(data):
    
    user_id = _current_user_id()
    if not user_id:
        return
    if not allow_event(r, user_id):
        return

    incoming = data.get('participantIds') or []
    
    try:
        part_ids = {int(x) for x in incoming if x is not None}
    except Exception:
        return
    
    part_ids.add(user_id)
    
    if len(part_ids) < 2:
        return 

    thread = _find_exact_thread(part_ids)
    
    if not thread:
        return
    
    join_room(_thread_room(thread.id))  
    payload = {"id": thread.id,}
    return payload

    
@socketio.on('change_thread_title')
def on_change_thread_title(data):
  
    tid = data.get("threadId")
    title = data.get("title", "").strip()
    lang = str(data.get("lang") or "en")
    me = _current_user_id()
  
    if not (tid and me and title and lang):
        return {"ok": False}
    if not allow_event(r, me):
        return {"ok": False}
        
    exist = db.session.query(db.exists().where(ThreadUser.thread_id == tid, ThreadUser.user_id == me)).scalar()
    if not exist:
        return {"ok": False}
  
    thread = db.session.get(Thread, tid)
    if not thread:
        return {"ok": False}
    
    title = sanitize_title(title)
    if not title:
        return {"ok": False}
    thread.title = title
    
    username = db.session.scalar(select(User.username).where(User.id == me)) or "Someone"
    text = f'{username} changed the chat title to "{title}"'
    message = Message(thread_id=tid, sender_id=0, text=text)
    db.session.add(message)
    db.session.commit()  
    payload = {"id": thread.id, "title": thread.title,}
    emit("message", message.to_dict(), room=_thread_room(tid))
    emit("thread_updated", payload, room=_thread_room(tid))
    return {"ok": True}
 
 
@socketio.on('leave_group_thread')
def on_leave_group_thread(data):
    me = _current_user_id()
    tid = data.get("threadId")
    lang = str(data.get("lang") or "en")
    if not me or not tid or not lang:
        return {"ok": False}
    if not allow_event(r, me):
        return {"ok": False}

    link = db.session.get(ThreadUser, (tid, me))
    count = db.session.scalar(select(func.count()).select_from(ThreadUser).where(ThreadUser.thread_id == tid))
    
    if not link:
        return {"ok": True}
    db.session.delete(link)
    db.session.flush()
    uname = db.session.scalar(select(User.username).where(User.id == me))
    text = f'{uname} left this chat...'
    message = Message(thread_id=tid, sender_id=0, text=text)
    db.session.add(message)
    db.session.commit()
    emit("message", message.to_dict(), room=_thread_room(tid))
    emit("thread_invited", room=_thread_room(tid))
    leave_room(_thread_room(tid))
    return {"ok": True}



EMOJI_RE = regex.compile(r'^\X$')
def is_emoji(s):
    return EMOJI_RE.match(s) and regex.search(r'\p{Extended_Pictographic}', s) 
    
@socketio.on('add_message_emoji')
def on_add_message_emoji(data):
  
    me = _current_user_id()
    tid = data.get("threadId")
    mid = data.get("messageId")
    emoji = data.get("emoji")
    if not (me and tid and mid and emoji):
        return {"ok": False}
    if not allow_event(r, me):
        return {"ok": False}
    try:
        tid = int(tid)
        mid = int(mid)
    except (TypeError, ValueError):
        return
    
    if not is_emoji(emoji):
        return
    
    reaction = db.session.scalar(select(MessageReaction).where(MessageReaction.message_id == mid, MessageReaction.user_id == me,))
    if reaction:
        if reaction.emoji == emoji:
            db.session.delete(reaction)
        else:
            reaction.emoji = emoji
    else:
        reaction = MessageReaction(user_id=me, message_id=mid, emoji=emoji)
        db.session.add(reaction)

    db.session.commit()

    emit("added_reaction", { "threadId": tid,}, room=_thread_room(tid), include_self=False)
    return {"ok": True}
    
    
@socketio.on('delete_message')
def on_delete_message(data):
    me = _current_user_id()
    tid = data.get("threadId")
    mid = data.get("messageId")
    
    if not (me and isinstance(tid, int) and isinstance(mid, int)):
        return {"ok": False}
    if not allow_event(r, me):
        return {"ok": False}

    try:
        message = (db.session.query(Message).filter(Message.id == mid, Message.thread_id == tid).first())
        if not message:
            return {"ok": False}
        if message.sender_id != me:
            return {"ok": False}

        atts = (db.session.query(MessageAttachment).filter(MessageAttachment.message_id == mid).all())
        att_ids = [a.file_upload_id for a in atts]

        for a in atts:
            db.session.delete(a)
            
        message.text = "This message has been deleted..."
        db.session.commit()

    except Exception:
        chat_logger.error(f"[{datetime.utcnow()}] USER_ID: {me} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        db.session.rollback()
        return {"ok": False}

    emit("message_deleted", {"threadId": tid }, room=_thread_room(tid), include_self=True, )
    return {"ok": True}




def build_english_list(names: list[str]) -> str:
    if not names:
        return ""
    names = [str(n) for n in names if n]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])} and {names[-1]}" 



@socketio.on('add_users')
def on_add_users(data):
    me = _current_user_id()
    tid = data.get("threadId")
    users_id = data.get("users_id")
       
    if not me or not isinstance(tid, int) or not isinstance(users_id, list) or not users_id:
        return {"ok": False}
    if not allow_event(r, me):
        return {"ok": False}

    to_add = {int(uid) for uid in users_id if isinstance(uid, (int, str))}

    if not to_add:
        return {"ok": False}

    existing = set(uid for (uid,) in db.session.query(ThreadUser.user_id).filter_by(thread_id=tid).filter(ThreadUser.user_id.in_(to_add)).all())

    final_to_add = list(to_add - existing)
    if not final_to_add:
        return {"ok": True}

    rows = [ThreadUser(thread_id=tid, user_id=uid) for uid in final_to_add]

    try:
        db.session.add_all(rows)
        adder_username = db.session.query(User.username).filter(User.id == me).scalar() or "Someone"  
        user_rows = (db.session.query(User.id, User.username).filter(User.id.in_(final_to_add)).all())
        added_usernames = [u for (_id, u) in user_rows]
        names_english = build_english_list(added_usernames)
    
        text = f'{adder_username} added {names_english} to the chat.'
        message = Message(thread_id=tid, sender_id=0, text=text)
        db.session.add(message)
        db.session.commit()        
        payload = message.to_dict()
        payload["system"] = { "key": "chatdrawervue.user_added", "params": {"adder": adder_username, "names": added_usernames},}
        emit("message", payload, room=_thread_room(tid))
        for uid in final_to_add:
            emit("thread_invited", room=_user_room(uid))
        
    except Exception as e:
        db.session.rollback()
        chat_logger.error(f"[{datetime.utcnow()}] USER_ID: {me} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return {"ok": False}

    return {"ok": True}




@socketio.on('update_last_message_read')
def on_update_last_message_read(data):
    me = _current_user_id()
    tid = data.get("tid")
    
    if not me or not tid:
        return {"ok": False}
    if not isinstance(tid, int): 
        return {"ok": False}     
    if not allow_event(r, me):
        return {"ok": False}

    try:
        row = (db.session.query(Thread.last_message_id, ThreadUser).join(ThreadUser, ThreadUser.thread_id == Thread.id).filter(Thread.id == tid, ThreadUser.user_id == me).first())
        if not row:
            return {"ok": False}

        last_id, thread_user = row
        last_id = last_id or 0
        
        current = thread_user.last_read_message_id or 0
        if last_id > current:
            thread_user.last_read_message_id = last_id

        db.session.commit()
        return {"ok": True}

    except Exception as e:
        db.session.rollback()
        chat_logger.error(f"[{datetime.utcnow()}] USER_ID: {me} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return {"ok": False}




####################################################################################################################
###################################################Notification#####################################################
####################################################################################################################   

SUPPORTED_LANGS = ['en','it','fr','es','de','pt','ru','zh','ja','hi']

_I18N = {
    "and": {
        "en": "and", "it": "e", "fr": "et", "es": "y", "de": "und",
        "pt": "e", "ru": "и", "zh": "和", "ja": "と", "ar": "و", "hi": " और",
    },
    "others_n": {
        "en": lambda n: f"{n} others",
        "it": lambda n: f"altri {n}",
        "fr": lambda n: f"{n} autres",
        "es": lambda n: f"{n} otros",
        "de": lambda n: f"{n} weitere",
        "pt": lambda n: f"outros {n}",
        "ru": lambda n: f"ещё {n}",
        "zh": lambda n: f"另外 {n} 位",
        "ja": lambda n: f"ほか {n} 人",
        "ar": lambda n: f"{n} آخرين",
        "hi": lambda n: f"अन्य {n} लोग",
    },
    "comma": {
        "en": ", ", "it": ", ", "fr": ", ", "es": ", ", "de": ", ",
        "pt": ", ", "ru": ", ", "zh": "、", "ja": "、", "ar": "، ", "hi": ", ",
    },
    "parent": {
        "post": {
            "en":"post","it":"post","fr":"publication","es":"publicación","de":"Beitrag",
            "pt":"publicação","ru":"пост","zh":"帖子","ja":"投稿","ar":"منشور", "hi":"पोस्ट",
        },
        "comment": {
            "en":"comment","it":"commento","fr":"commentaire","es":"comentario","de":"Kommentar",
            "pt":"comentário","ru":"комментарий","zh":"评论","ja":"コメント","ar":"تعليق", "hi": "टिप्पणी",
        }
    },
    "tpl": {
    "reply": {
        "en": {
            "sing": lambda actors, parent: f"{actors} replied to your {parent}",
            "pl":   lambda actors, parent: f"{actors} replied to your {parent}", 
        },
        "it": {
            "sing": lambda actors, parent: f"{actors} ha risposto al tuo {parent}",
            "pl":   lambda actors, parent: f"{actors} hanno risposto al tuo {parent}",
        },
        "fr": {
            "sing": lambda actors, parent: f"{actors} a répondu à votre {parent}",
            "pl":   lambda actors, parent: f"{actors} ont répondu à votre {parent}",
        },
        "es": {
            "sing": lambda actors, parent: f"{actors} respondió a tu {parent}",
            "pl":   lambda actors, parent: f"{actors} respondieron a tu {parent}",
        },
        "de": {
            "sing": lambda actors, parent: f"{actors} hat auf deinen {parent} geantwortet",
            "pl":   lambda actors, parent: f"{actors} haben auf deinen {parent} geantwortet",
        },
        "pt": {
            "sing": lambda actors, parent: f"{actors} respondeu ao seu {parent}",
            "pl":   lambda actors, parent: f"{actors} responderam ao seu {parent}",
        },
        "ru": {
            "sing": lambda actors, parent: f"{actors} ответил на ваш {parent}",
            "pl":   lambda actors, parent: f"{actors} ответили на ваш {parent}",
        },
        "hi": {
            "sing": lambda actors, parent: f"{actors} ने आपकी {parent} पर उत्तर दिया है",
            "pl":   lambda actors, parent: f"{actors} ने आपकी {parent} पर उत्तर दिए हैं",
        },
        
        "zh": {"sing": lambda a, p: f"{a} 回复了你的{p}", "pl": lambda a, p: f"{a} 回复了你的{p}"},
        "ja": {"sing": lambda a, p: f"{a} があなたの{p}に返信しました", "pl": lambda a, p: f"{a} があなたの{p}に返信しました"},
        "ar": {"sing": lambda a, p: f"{a} ردّ على {p} الخاص بك", "pl": lambda a, p: f"{a} ردّوا على {p} الخاص بك"},
    },

    "mention": {
        "en": {"sing": lambda a, _: f"{a} mentioned you in a comment", "pl": lambda a, _: f"{a} mentioned you in a comment"},
        "it": {"sing": lambda a, _: f"{a} ti ha menzionato in un commento", "pl": lambda a, _: f"{a} ti hanno menzionato in un commento"},
        "fr": {"sing": lambda a, _: f"{a} vous a mentionné dans un commentaire", "pl": lambda a, _: f"{a} vous ont mentionné dans un commentaire"},
        "es": {"sing": lambda a, _: f"{a} te mencionó en un comentario", "pl": lambda a, _: f"{a} te mencionaron en un comentario"},
        "de": {"sing": lambda a, _: f"{a} hat dich in einem Kommentar erwähnt", "pl": lambda a, _: f"{a} haben dich in einem Kommentar erwähnt"},
        "pt": {"sing": lambda a, _: f"{a} mencionou você em um comentário", "pl": lambda a, _: f"{a} mencionaram você em um comentário"},
        "ru": {"sing": lambda a, _: f"{a} упомянул вас в комментарии", "pl": lambda a, _: f"{a} упомянули вас в комментарии"},
        "zh": {"sing": lambda a, _: f"{a} 在评论中提到了你", "pl": lambda a, _: f"{a} 在评论中提到了你"},
        "ja": {"sing": lambda a, _: f"{a} がコメントであなたに言及しました", "pl": lambda a, _: f"{a} がコメントであなたに言及しました"},
        "ar": {"sing": lambda a, _: f"{a} ذكرك في تعليق", "pl": lambda a, _: f"{a} ذكروك في تعليق"},
        "hi": {"sing": lambda a, _: f"{a} ने आपको एक टिप्पणी में उल्लेख किया है", "pl": lambda a, _: f"{a} ने आपको एक टिप्पणी में उल्लेख किया है"},
    },
  }
}


def _lang(lang: str) -> str:
    return lang if lang in SUPPORTED_LANGS else "en"


def _localized_parent(parent_type: str, lang: str) -> str:
    parent_type = (parent_type or "").lower()
    if parent_type in _I18N["parent"]:
        return _I18N["parent"][parent_type][_lang(lang)]
    return parent_type or {"en":"item","it":"elemento","fr":"élément","es":"elemento","de":"Element",
                           "pt":"item","ru":"элемент","zh":"内容","ja":"アイテム","ar":"عنصر", "hi":"आइटम",}[_lang(lang)]


def build_actors_text(lang: str, ordered_unique: list[str], counts: dict[str, int]) -> str:
    L = _lang(lang)
    and_word = _I18N["and"][L]
    comma = _I18N["comma"][L]
    others_n = _I18N["others_n"][L]

    def label(u: str) -> str:
        c = counts.get(u, 1)
        return f"{u} ({c})" if c > 1 else u

    actors_with_counts = [label(u) for u in ordered_unique]

    n = len(actors_with_counts)
    if n == 0:
        return ""
    if n == 1:
        return actors_with_counts[0]
    if n == 2:
        if L in ("zh", "ja"):
            return f"{actors_with_counts[0]}{and_word}{actors_with_counts[1]}"
        if L == "ar":
            return f"{actors_with_counts[0]} {and_word} {actors_with_counts[1]}"
        return f"{actors_with_counts[0]} {and_word} {actors_with_counts[1]}"

    first, second = actors_with_counts[0], actors_with_counts[1]
    remaining = n - 2

    if L in ("zh", "ja"):
        return f"{first}{comma}{second}{and_word}{others_n(remaining)}"
    if L == "ru":
        return f"{first}{comma}{second} {and_word} {others_n(remaining)}"
    if L == "ar":
        return f"{first}{comma}{second} {and_word} {others_n(remaining)}"
    return f"{first}{comma}{second} {and_word} {others_n(remaining)}"
    
    
    
def build_notification_text(lang: str, action: str, parent_type: str, ordered_unique: list[str], counts: dict[str, int] ) -> str:
    L = _lang(lang)
    actors_text = build_actors_text(L, ordered_unique, counts)
    if not actors_text:
        return ""

    parent_local = _localized_parent(parent_type, L)
    plural = len(ordered_unique) > 1
    tpl_group = _I18N["tpl"][action][L]
    form = "pl" if plural else "sing"
    
    return tpl_group[form](actors_text, parent_local)
    


@socketio.on('send_notification')
def on_send_notification(data):
    me = _current_user_id()
    
    try:
        comment_id = int(data.get("comment_id"))
    except (TypeError, ValueError):
        return
        
    if not me or not allow_event(r, me):
        return
        
    lang = str(data.get("lang") or "en")

    try:
        notifs = ( db.session.query(Notification).filter(Notification.comment_id == comment_id, Notification.actor_id == me).all())
        if not notifs:
            return

        actor_username = (db.session.query(User.username).filter(User.id == me).scalar()) or "Someone"
        for n in notifs:
            if n.user_id == me:
                continue
            
            parent_type = 'comment' if n.parent_comment_id else 'post'            
            text = build_notification_text(lang=lang, action=n.action, parent_type=parent_type, ordered_unique=[actor_username], counts={actor_username: 1} )

            payload = {
                "id": n.id,
                "userId": n.user_id,
                "actorId": n.actor_id,
                "action": n.action,             
                "text": text,
                "commentId": n.comment_id,
                "parentType": parent_type,
                "parentText": n.parent_text,     
                "parentId": n.parent_comment_id ,
                "postId": n.parent_post_id,
                "postSlug": n.parent_post_slug,
                "createdAt": to_iso_utc(n.created_at) if n.created_at else None,
                "isRead": bool(n.is_read),
            }
            
            socketio.emit('notifications:new', payload, room=_user_room(n.user_id))

        return

    except Exception as e:
        db.session.rollback()
        chat_logger.error(f"[{datetime.utcnow()}] USER_ID: {me} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return



@socketio.on('notifications:sync_request')
def on_notifications_sync_request(data):
    try:    
    
        me = _current_user_id()
        if not me or not allow_event(r, me):
            return
                
        lang = str(data.get("lang") or "en")
        B = BlockedUsers
        blocked_exists = exists().where( or_( and_(B.blocker_id == me, B.blocked_id == Notification.actor_id), and_(B.blocker_id == Notification.actor_id, B.blocked_id == me), ))
        
        notifs = db.session.query(Notification, User.username).join(User, User.id == Notification.actor_id).filter(Notification.user_id == me).filter(~blocked_exists ,User.is_suspended.is_(False)).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(200).all()
        
        groups = defaultdict(list)

        for notif, actor_username in notifs:
            key = (notif.parent_post_id, notif.parent_comment_id, notif.action, notif.is_read)
            groups[key].append((notif, actor_username))

        items = []
        unread_groups = 0

        for (post_id, parent_comment_id, action, is_read), notif_group in groups.items():
            
            parent_type = "comment" if parent_comment_id else "post"
            notif_latest, _ = max(notif_group, key=lambda t: t[0].created_at or 0)
            
            if not is_read:
                unread_groups += 1
              
            usernames_in_group = [u for _, u in notif_group]    
            counts = Counter(usernames_in_group)
                       
            seen = set()
            ordered_unique = []
            for _, u in notif_group:
                if u not in seen:
                    seen.add(u)
                    ordered_unique.append(u)
                    
            actor_ids = []
            seen_ids = set()
            for n, _ in notif_group:
                if n.actor_id not in seen_ids:
                    seen_ids.add(n.actor_id)
                    actor_ids.append(n.actor_id)
                    
            actors_with_counts = {u: counts[u] for u in ordered_unique}          
            text = build_notification_text(lang=lang, action=action, parent_type=parent_type, ordered_unique=ordered_unique, counts=actors_with_counts )
            
            items.append({
                "id": notif_latest.id,
                "userId": notif_latest.user_id,
                "actorIds": actor_ids,
                "actorUsernames": ordered_unique,
                "action": action,
                "parentType": parent_type,
                "parentText": notif_latest.parent_text,
                "postId": post_id,
                "postSlug": notif_latest.parent_post_slug,
                "parentId": parent_comment_id,
                "commentId": notif_latest.comment_id,
                "text": text,
                "isRead": bool(is_read),
                "createdAt": to_iso_utc(notif_latest.created_at) if notif_latest.created_at else None,
                "total": sum(counts.values()),
            })
            
        items.sort(key=lambda it: it["createdAt"] or "", reverse=True)
        emit("notifications:sync", {"items": items, "unread": unread_groups})
        
    except Exception as e:
        chat_logger.error(f"[{datetime.utcnow()}] USER_ID: {me} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return False  



@socketio.on('notifications:opened')
def on_notifications_opened(data):

    me = _current_user_id()
    if not me or not allow_event(r, me):
        return {"ok": False}
    
    ids_raw = data.get("ids", [])
    if not isinstance(ids_raw, (list, tuple)):
        return {"ok": False }
        
    try:
        ids = [int(x) for x in ids_raw]
    except (TypeError, ValueError):
        return {"ok": False}
    
    N2 = aliased(Notification)
    try:
        groups = (db.session.query(func.coalesce(N2.parent_post_id, -1).label("pp"), func.coalesce(N2.parent_comment_id, -1).label("pc"), N2.action.label("act"),).filter(N2.id.in_(ids), N2.user_id == me).distinct().subquery())

        db.session.query(Notification).filter(Notification.user_id == me).filter(and_(func.coalesce(Notification.parent_post_id, -1) == groups.c.pp, func.coalesce(Notification.parent_comment_id, -1) == groups.c.pc, Notification.action == groups.c.act,)).update({Notification.is_read: True}, synchronize_session=False)
        db.session.commit()
        
    except Exception as e:     
        db.session.rollback()
        chat_logger.error(f"[{datetime.utcnow()}] USER_ID: {me} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return {"ok": False}
    
    return {"ok": True}
    
    
    


