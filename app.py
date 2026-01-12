# -*- coding: utf-8 -*-
import json
import os
import random
import math
from datetime import date
from collections import defaultdict, Counter

import time
import ssl
import socket
from googleapiclient.errors import HttpError

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# =========================================================
# 0) 기본 설정 / 파일 경로
# =========================================================
APP_TITLE = "마리아 상암포바 도우미 MSA (Beta)"
ROSTER_FILE = "players.json"
SESSIONS_FILE = "sessions.json"

COURT_TYPES = ["인조잔디", "하드", "클레이"]
NTRP_OPTIONS = ["모름", "2.0", "2.5", "3.0", "3.5", "4.0", "4.5", "5.0"]
SCORE_OPTIONS = list(range(0, 8))  # 0~7 (원하면 수정)

WIN_POINT = 3
DRAW_POINT = 1
LOSE_POINT = 0





DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_drive_service():
    info = dict(st.secrets["google_service_account"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def drive_download_text(file_id: str) -> str:
    service = get_drive_service()
    req = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue().decode("utf-8")

def drive_upload_text(file_id: str, text: str):
    service = get_drive_service()
    media = MediaIoBaseUpload(
        io.BytesIO(text.encode("utf-8")),
        mimetype="application/json",
        resumable=False,
    )
    service.files().update(
        fileId=file_id,
        media_body=media,
        supportsAllDrives=True,
    ).execute()

def load_json_drive(file_id: str, default):
    try:
        raw = drive_download_text(file_id)
        return json.loads(raw) if raw.strip() else default
    except Exception:
        return default

def save_json_drive(file_id: str, data):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    drive_upload_text(file_id, text)

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


PLAYERS_FILE_ID = st.secrets["drive"]["players_file_id"]
SESSIONS_FILE_ID = st.secrets["drive"]["sessions_file_id"]

def load_players():
    return load_json_drive(PLAYERS_FILE_ID, [])

def save_players(players):
    save_json_drive(PLAYERS_FILE_ID, players)

def load_sessions():
    return load_json_drive(SESSIONS_FILE_ID, {})

def save_sessions(sessions):
    save_json_drive(SESSIONS_FILE_ID, sessions)



# =========================================================
# 2) Streamlit 기본 UI / CSS
# =========================================================
st.set_page_config(
    page_title=APP_TITLE,
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
/* 버튼 래핑 */
.main-primary-btn button {
  width: 100%;
  border-radius: 12px !important;
  font-weight: 800 !important;
  padding: 0.65rem 0.85rem !important;
}
.main-danger-btn button {
  width: 100%;
  border-radius: 12px !important;
  font-weight: 800 !important;
  padding: 0.65rem 0.85rem !important;
}

/* 게임 미리보기 row */
.msa-game-row{
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 12px;
  padding: 10px 12px;
  margin: 8px 0;
}
.msa-game-meta{
  font-size: 0.82rem;
  color: #6b7280;
  margin-bottom: 6px;
  font-weight: 700;
}
.msa-game-line{
  font-size: 0.98rem;
  line-height: 1.25;
}

/* 배지 */
.name-badge{
  display: inline-block;
  padding: 2px 8px;
  margin: 0 3px 3px 0;
  border-radius: 999px;
  font-weight: 800;
  font-size: 0.88rem;
  border: 1px solid rgba(0,0,0,0.06);
  white-space: nowrap;
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 3) 공용 유틸
# =========================================================
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def get_index_or_default(options, value, default_index=0):
    try:
        return options.index(value)
    except Exception:
        return default_index


def section_card(title, emoji=""):
    st.markdown(
        f"""
        <div style="
            padding: 0.9rem 1.0rem;
            border-radius: 14px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            margin: 0.4rem 0 0.9rem 0;
        ">
            <div style="font-size:1.05rem; font-weight:900;">
                {emoji} {title}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_name_badge(name: str, roster_by_name: dict):
    info = roster_by_name.get(name, {}) or {}
    gender = info.get("gender", "남")
    grp = info.get("group", "미배정")

    if gender == "여":
        bg = "#fee2e2"
    else:
        bg = "#dbeafe"

    # 조 표시 테두리 살짝
    border = "#ef4444" if "A" in str(grp) else "#3b82f6" if "B" in str(grp) else "rgba(0,0,0,0.08)"
    return f"<span class='name-badge' style='background:{bg};border-color:{border};'>{name}</span>"


def get_ntrp_value(meta: dict):
    v = meta.get("ntrp", None)
    if v in (None, "", "모름"):
        return None
    try:
        return float(v)
    except Exception:
        return None


def is_guest_name(name: str, roster_list: list):
    # roster_list에 없는 이름이면 게스트로 간주(간단 규칙)
    names = {p.get("name") for p in (roster_list or [])}
    return name not in names


def guest_bucket(name: str, roster_list: list):
    # 게스트는 통계에서 "게스트"로 묶고 싶으면 여기서 처리 가능
    # 지금은 그냥 이름 그대로 반환
    return name


def normalize_schedule(raw):
    """
    sessions.json에서 불러온 schedule이 list 형태일 수 있으니
    화면에서는 항상 (gt, t1, t2, court) 튜플로 쓰게 정리.
    """
    out = []
    for item in (raw or []):
        try:
            gt, t1, t2, court = item
            out.append((gt, list(t1), list(t2), court))
        except Exception:
            pass
    return out


def schedule_to_jsonable(schedule):
    """
    저장 직전에 list로 바꿔서 json dump 가능하게.
    """
    out = []
    for gt, t1, t2, court in (schedule or []):
        out.append([gt, list(t1), list(t2), court])
    return out


def count_player_games(schedule):
    cnt = Counter()
    for gt, t1, t2, court in (schedule or []):
        for p in list(t1) + list(t2):
            cnt[p] += 1
    return cnt


def calc_result(s1, s2):
    # 팀1 기준 결과: s1>s2 => W, s1<s2 => L, 같으면 D
    if s1 is None or s2 is None:
        return None
    try:
        a = int(s1)
        b = int(s2)
    except Exception:
        return None
    if a > b:
        return "W"
    if a < b:
        return "L"
    return "D"


def classify_game_group(all_players, roster_by_name, day_groups_snapshot=None):
    """
    all_players가 전부 A조면 "A", 전부 B조면 "B", 그 외 "O"
    day_groups_snapshot이 있으면 그 값을 우선 사용.
    """
    groups = []
    snap = day_groups_snapshot or {}
    for p in all_players:
        g = snap.get(p)
        if not g:
            g = roster_by_name.get(p, {}).get("group", "미배정")
        groups.append(g)

    onlyA = all(("A" in str(g)) for g in groups)
    onlyB = all(("B" in str(g)) for g in groups)
    if onlyA:
        return "A"
    if onlyB:
        return "B"
    return "O"


def detect_score_warnings(day_data):
    """
    5:5는 정상으로 간주, 그 외 동점은 경고.
    """
    warnings = []
    schedule = normalize_schedule(day_data.get("schedule", []))
    results = day_data.get("results", {}) or {}

    for idx, (gt, t1, t2, court) in enumerate(schedule, start=1):
        res = results.get(str(idx)) or results.get(idx) or {}
        s1 = res.get("t1", None)
        s2 = res.get("t2", None)
        if s1 is None or s2 is None:
            continue
        try:
            a = int(s1)
            b = int(s2)
        except Exception:
            continue
        if a == b and not (a == 5 and b == 5):
            warnings.append(f"{idx}번 게임이 동점입니다: {a}:{b}")
    return warnings


def build_daily_report(sel_date, day_data):
    """
    아주 간단한 요약 리포트(원하면 더 화려하게 확장 가능)
    """
    schedule = normalize_schedule(day_data.get("schedule", []))
    results = day_data.get("results", {}) or {}
    if not schedule:
        return []

    lines = []
    decided = 0
    for i, (gt, t1, t2, court) in enumerate(schedule, start=1):
        res = results.get(str(i)) or results.get(i) or {}
        s1 = res.get("t1")
        s2 = res.get("t2")
        r = calc_result(s1, s2)
        if r is None:
            continue
        decided += 1
    lines.append(f"총 {len(schedule)}게임 중 점수 입력 완료: {decided}게임")

    # 득실 TOP 간단
    score_for = Counter()
    score_against = Counter()
    for i, (gt, t1, t2, court) in enumerate(schedule, start=1):
        res = results.get(str(i)) or results.get(i) or {}
        s1 = res.get("t1")
        s2 = res.get("t2")
        r = calc_result(s1, s2)
        if r is None:
            continue
        try:
            a = int(s1)
            b = int(s2)
        except Exception:
            continue
        for p in t1:
            score_for[p] += a
            score_against[p] += b
        for p in t2:
            score_for[p] += b
            score_against[p] += a

    if score_for:
        top = score_for.most_common(1)[0]
        lines.append(f"최다 득점: {top[0]} ({top[1]}점)")
    if score_against:
        low = min(score_against.items(), key=lambda x: x[1])
        lines.append(f"최소 실점(누적): {low[0]} ({low[1]}점)")

    return lines


def get_daily_fortune(name: str):
    # 가벼운 랜덤 운세
    tips = [
        "오늘은 리턴 타이밍이 잘 맞는 날이에요. 자신 있게 들어가봐요!",
        "서브 넣을 때 1초만 더 멈추고 루틴 지키면 실수가 확 줄어요.",
        "스트로크보다 발이 먼저! 스플릿스텝만 잘해도 경기 흐름이 바뀌어요.",
        "포핸드로 마무리 욕심내지 말고, 한 번 더 깊게 보내면 이겨요.",
        "오늘은 네트 플레이가 통하는 날. 짧은 공 오면 과감하게 들어가요!",
    ]
    random.seed(hash(name) % (10**9))
    return random.choice(tips)


def colorize_df_names(df, roster_by_name, cols):
    """
    pandas Styler로 이름 컬럼에 성별 색을 살짝 입힘.
    """
    def style_cell(val):
        info = roster_by_name.get(val, {}) or {}
        g = info.get("gender", "남")
        if g == "여":
            return "background-color:#fee2e2; font-weight:800;"
        return "background-color:#dbeafe; font-weight:800;"

    sty = df.style
    for c in cols:
        if c in df.columns:
            sty = sty.applymap(style_cell, subset=[c])
    return sty


def smart_table(df_or_styler, use_container_width=True):
    # 모바일이면 간단 HTML 렌더(원하면 더 개선 가능)
    mobile_mode = st.session_state.get("mobile_mode", False)
    if mobile_mode:
        try:
            html = df_or_styler.to_html()
        except Exception:
            html = pd.DataFrame(df_or_styler).to_html()
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.dataframe(df_or_styler, use_container_width=use_container_width)


def render_score_summary_table(rows, roster_by_name):
    """
    rows: [{게임, 코트, 타입, t1, t2, t1_score, t2_score}, ...]
    """
    out_rows = []
    for r in rows:
        t1 = r.get("t1", [])
        t2 = r.get("t2", [])
        t1_txt = " ".join([x for x in t1])
        t2_txt = " ".join([x for x in t2])
        out_rows.append(
            {
                "게임": r.get("게임"),
                "코트": r.get("코트"),
                "타입": r.get("타입"),
                "팀1": t1_txt,
                "팀2": t2_txt,
                "점수": f"{r.get('t1_score','')}:{r.get('t2_score','')}",
            }
        )

    df = pd.DataFrame(out_rows)
    df = df.set_index("게임")
    df.index.name = "게임"
    st.dataframe(df, use_container_width=True)


def iter_games(sessions, include_special=False):
    """
    sessions 구조:
      sessions[date_str] = {
        "schedule": [...],
        "results": {...},
        "court_type": "...",
        "special_match": bool,
        "groups_snapshot": {...}
      }
    yield: (d, idx, gdict)
    """
    for d, day_data in (sessions or {}).items():
        if d == "전체":
            continue
        if not include_special and bool(day_data.get("special_match", False)):
            continue

        schedule = normalize_schedule(day_data.get("schedule", []))
        results = day_data.get("results", {}) or {}
        court_type = day_data.get("court_type", COURT_TYPES[0])
        groups_snapshot = day_data.get("groups_snapshot") or {}

        for idx, (gt, t1, t2, court) in enumerate(schedule, start=1):
            res = results.get(str(idx)) or results.get(idx) or {}
            s1 = res.get("t1")
            s2 = res.get("t2")
            sides = res.get("sides", {}) or {}
            yield d, idx, {
                "type": gt,
                "court": court,
                "t1": list(t1),
                "t2": list(t2),
                "score1": s1,
                "score2": s2,
                "court_type": court_type,
                "sides": sides,
                "groups_snapshot": groups_snapshot,
            }


# =========================================================
# 4) 대진 생성 알고리즘 (간단 구현 / 필요시 교체)
# =========================================================
def _gender_of(name, roster_by_name):
    return roster_by_name.get(name, {}).get("gender", "남")


def _ntrp_of(name, roster_by_name):
    v = roster_by_name.get(name, {}).get("ntrp", None)
    try:
        return None if v in (None, "", "모름") else float(v)
    except Exception:
        return None


def _pick_by_ntrp_closest(cands, target_ntrp, roster_by_name):
    if not cands:
        return None
    if target_ntrp is None:
        return random.choice(cands)

    scored = []
    for p in cands:
        pn = _ntrp_of(p, roster_by_name)
        if pn is None:
            scored.append((9999.0, random.random(), p))
        else:
            scored.append((abs(pn - target_ntrp), random.random(), p))
    scored.sort(key=lambda x: (x[0], x[1]))
    return scored[0][2] if scored else random.choice(cands)


def build_schedule_by_total_rounds(players, gtype, court_count, total_rounds, mode_name, use_ntrp, roster_by_name):
    schedule = []
    players = list(players)

    def pick_four(pool, mode):
        pool = pool[:]
        if mode == "동성복식 (남+남 / 여+여)":
            men = [p for p in pool if _gender_of(p, roster_by_name) == "남"]
            women = [p for p in pool if _gender_of(p, roster_by_name) == "여"]
            cand = men if len(men) >= 4 else women
            if len(cand) < 4:
                return None
            return random.sample(cand, 4)

        if mode == "혼합복식 (남+여 짝)":
            men = [p for p in pool if _gender_of(p, roster_by_name) == "남"]
            women = [p for p in pool if _gender_of(p, roster_by_name) == "여"]
            if len(men) < 2 or len(women) < 2:
                return None
            return random.sample(men, 2) + random.sample(women, 2)

        if len(pool) < 4:
            return None
        return random.sample(pool, 4)

    def pick_two(pool, mode):
        pool = pool[:]
        if mode == "동성 단식":
            men = [p for p in pool if _gender_of(p, roster_by_name) == "남"]
            women = [p for p in pool if _gender_of(p, roster_by_name) == "여"]
            cand = men if len(men) >= 2 else women
            if len(cand) < 2:
                return None
            return random.sample(cand, 2)
        if len(pool) < 2:
            return None
        return random.sample(pool, 2)

    total_games = int(total_rounds) * int(court_count)
    for gi in range(total_games):
        court = (gi % int(court_count)) + 1

        if gtype == "복식":
            four = pick_four(players, mode_name)
            if not four:
                continue

            # 팀 구성(혼복이면 남+여로 묶기)
            if mode_name == "혼합복식 (남+여 짝)":
                men = [p for p in four if _gender_of(p, roster_by_name) == "남"]
                women = [p for p in four if _gender_of(p, roster_by_name) == "여"]
                t1 = [men[0], women[0]]
                t2 = [men[1], women[1]]
            else:
                # NTRP 켜면 비슷하게 섞기(아주 간단)
                if use_ntrp:
                    four_sorted = sorted(
                        four,
                        key=lambda x: (_ntrp_of(x, roster_by_name) is None, _ntrp_of(x, roster_by_name) or 999),
                    )
                    t1 = [four_sorted[0], four_sorted[3]]
                    t2 = [four_sorted[1], four_sorted[2]]
                else:
                    t1 = [four[0], four[1]]
                    t2 = [four[2], four[3]]

            schedule.append(("복식", t1, t2, court))

        else:
            two = pick_two(players, mode_name)
            if not two:
                continue
            schedule.append(("단식", [two[0]], [two[1]], court))

    return schedule


def build_doubles_schedule(players, max_games, court_count, mode, use_ntrp, group_only, roster_by_name):
    players = list(players)
    max_games = int(max_games)
    court_count = int(court_count)

    # 그룹만 옵션(간단): A/B 외는 제외
    if group_only:
        players = [p for p in players if roster_by_name.get(p, {}).get("group") in ("A조", "B조")]

    games_cnt = Counter({p: 0 for p in players})
    schedule = []

    def can_play(p):
        return games_cnt[p] < max_games

    def pick_team(pool, want_gender=None):
        cand = [p for p in pool if can_play(p)]
        if want_gender:
            cand = [p for p in cand if _gender_of(p, roster_by_name) == want_gender]
        return cand

    # 총 게임 목표: 모든 사람 max_games 채우려고 시도
    target_total_games = len(players) * max_games // 4
    tries = 4000

    while tries > 0 and len(schedule) < target_total_games:
        tries -= 1

        # 라운드당 코트 수만큼 뽑음
        round_pool = [p for p in players if can_play(p)]
        if len(round_pool) < 4:
            break

        for court in range(1, court_count + 1):
            round_pool = [p for p in players if can_play(p)]
            if len(round_pool) < 4:
                break

            if mode == "혼합복식":
                men = pick_team(round_pool, "남")
                women = pick_team(round_pool, "여")
                if len(men) < 2 or len(women) < 2:
                    continue
                m1, m2 = random.sample(men, 2)
                w1, w2 = random.sample(women, 2)

                # NTRP 켜면 대충 비슷하게
                if use_ntrp:
                    # 남 중 하나 고르고, 그와 비슷한 여 고르기
                    m1 = random.choice([m1, m2])
                    target = _ntrp_of(m1, roster_by_name)
                    w1 = _pick_by_ntrp_closest(women, target, roster_by_name) or w1
                    # 나머지
                    m_rest = [x for x in (m1, m2) if x != m1][0]
                    w_rest = [x for x in (w1, w2) if x != w1] or [w2]
                    w2 = w_rest[0]

                t1 = [m1, w1]
                t2 = [m2, w2]
                picked = t1 + t2

            elif mode == "동성복식":
                men = pick_team(round_pool, "남")
                women = pick_team(round_pool, "여")
                cand = men if len(men) >= 4 else women
                if len(cand) < 4:
                    continue
                picked = random.sample(cand, 4)
                t1 = [picked[0], picked[1]]
                t2 = [picked[2], picked[3]]

            else:
                picked = random.sample(round_pool, 4)
                # NTRP 켜면 실력 비슷하게 분배(초간단)
                if use_ntrp:
                    picked_sorted = sorted(
                        picked,
                        key=lambda x: (_ntrp_of(x, roster_by_name) is None, _ntrp_of(x, roster_by_name) or 999),
                    )
                    t1 = [picked_sorted[0], picked_sorted[3]]
                    t2 = [picked_sorted[1], picked_sorted[2]]
                else:
                    t1 = [picked[0], picked[1]]
                    t2 = [picked[2], picked[3]]

            # 카운트 반영
            for p in picked:
                games_cnt[p] += 1
            schedule.append(("복식", t1, t2, court))

            if len(schedule) >= target_total_games:
                break

    return schedule


def build_singles_schedule(players, max_games, court_count, mode, use_ntrp, group_only, roster_by_name):
    players = list(players)
    max_games = int(max_games)
    court_count = int(court_count)

    if group_only:
        players = [p for p in players if roster_by_name.get(p, {}).get("group") in ("A조", "B조")]

    games_cnt = Counter({p: 0 for p in players})
    schedule = []

    target_total_games = len(players) * max_games // 2
    tries = 4000

    def can_play(p):
        return games_cnt[p] < max_games

    while tries > 0 and len(schedule) < target_total_games:
        tries -= 1

        pool = [p for p in players if can_play(p)]
        if len(pool) < 2:
            break

        for court in range(1, court_count + 1):
            pool = [p for p in players if can_play(p)]
            if len(pool) < 2:
                break

            if mode == "동성 단식":
                men = [p for p in pool if _gender_of(p, roster_by_name) == "남"]
                women = [p for p in pool if _gender_of(p, roster_by_name) == "여"]
                cand = men if len(men) >= 2 else women
                if len(cand) < 2:
                    continue
                a, b = random.sample(cand, 2)
            else:
                a, b = random.sample(pool, 2)

            if use_ntrp:
                # a 고르고, a와 가장 비슷한 b로
                target = _ntrp_of(a, roster_by_name)
                cand = [x for x in pool if x != a]
                b2 = _pick_by_ntrp_closest(cand, target, roster_by_name)
                if b2:
                    b = b2

            games_cnt[a] += 1
            games_cnt[b] += 1
            schedule.append(("단식", [a], [b], court))

            if len(schedule) >= target_total_games:
                break

    return schedule


def build_hanul_aa_schedule(ordered_players, court_count):
    """
    ✅ "한울 AA 방식" 대체용 간단 고정 패턴 (결정적/고정)
    - 입력 순서가 같으면 항상 같은 대진이 나옴(버튼 눌러도 안 바뀌게)
    - 1인당 4게임이 되도록 설계(5~16명 권장)
    - 정확히 원본 AA 테이블이 있으시면, 이 함수만 원본으로 교체하면 됨
    """
    players = list(ordered_players)
    n = len(players)
    cc = max(1, int(court_count))

    if n < 5:
        return []

    # 총 슬롯 = n*4, 게임당 4명 => 총 게임수 = n
    total_games = n

    schedule = []
    for gi in range(total_games):
        court = (gi % cc) + 1

        # 4명 선택: 결정적(모듈러)
        a = players[(gi + 0) % n]
        b = players[(gi + 1) % n]
        c = players[(gi + 2) % n]
        d = players[(gi + 3) % n]

        # 팀 구성도 섞어줌(gi parity로 변형)
        if gi % 2 == 0:
            t1 = [a, c]
            t2 = [b, d]
        else:
            t1 = [a, b]
            t2 = [c, d]

        # 중복 4명일 수 있는 n=5 같은 케이스 방지(아주 드물게 발생 가능)
        if len(set(t1 + t2)) < 4:
            # fallback: 다음 인덱스도 끌어다 쓰기
            e = players[(gi + 4) % n]
            t2 = [c, e]
            if len(set(t1 + t2)) < 4:
                continue

        schedule.append(("복식", t1, t2, court))

    return schedule


# =========================================================
# 5) 상태 초기화: roster / sessions
# =========================================================
if "mobile_mode" not in st.session_state:
    st.session_state.mobile_mode = False

with st.sidebar:
    st.checkbox("📱 모바일 모드(간단 렌더)", key="mobile_mode")
    st.caption("모바일 모드는 표 렌더를 가볍게 합니다.")

if "roster" not in st.session_state:
    st.session_state.roster = load_players()

if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions()

roster = st.session_state.roster
sessions = st.session_state.sessions

# roster_by_name 구성
roster_by_name = {p.get("name"): p for p in roster if p.get("name")}


# =========================================================
# 6) 탭 구성
# =========================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["1) 선수 관리", "2) 오늘 경기 세션", "3) 경기 기록 / 통계", "4) 개인별 통계", "5) 월별 통계"]
)


# =========================================================
# TAB1) 선수 관리 (간단 편집)
# =========================================================
with tab1:
    section_card("선수 관리", "👥")

    if not roster:
        st.info("선수가 없습니다. 아래에서 추가해 주세요.")

    df = pd.DataFrame(roster) if roster else pd.DataFrame(
        columns=["name", "gender", "group", "ntrp", "age_group", "racket", "hand", "mbti"]
    )

    # 컬럼 보장
    for col in ["name", "gender", "group", "ntrp", "age_group", "racket", "hand", "mbti"]:
        if col not in df.columns:
            df[col] = ""

    st.markdown("### 선수 명단")
    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("이름", required=True),
            "gender": st.column_config.SelectboxColumn("성별", options=["남", "여"], required=False),
            "group": st.column_config.SelectboxColumn("조", options=["미배정", "A조", "B조"], required=False),
            "ntrp": st.column_config.SelectboxColumn("NTRP", options=NTRP_OPTIONS, required=False),
            "age_group": st.column_config.TextColumn("연령대", required=False),
            "racket": st.column_config.TextColumn("라켓", required=False),
            "hand": st.column_config.SelectboxColumn("주손", options=["오른손", "왼손", "양손"], required=False),
            "mbti": st.column_config.TextColumn("MBTI", required=False),
        },
        key="roster_editor",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
        if st.button("명단 저장", key="btn_save_roster", use_container_width=True):
            # 빈 이름 제거
            rows = edited.to_dict(orient="records")
            clean = []
            for r in rows:
                nm = (r.get("name") or "").strip()
                if not nm:
                    continue
                r["name"] = nm
                # 기본값들
                r["gender"] = r.get("gender") or "남"
                r["group"] = r.get("group") or "미배정"
                r["ntrp"] = r.get("ntrp") or "모름"
                r["age_group"] = r.get("age_group") or "비밀"
                r["racket"] = r.get("racket") or "모름"
                r["hand"] = r.get("hand") or "오른손"
                r["mbti"] = (r.get("mbti") or "모름").upper()
                clean.append(r)

            st.session_state.roster = clean
            save_players(clean)
            st.success("선수 명단을 저장했습니다.")
            safe_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="main-danger-btn">', unsafe_allow_html=True)
        if st.button("세션 데이터 저장(강제)", key="btn_force_save_sessions", use_container_width=True):
            save_sessions(st.session_state.sessions)
            st.success("sessions.json 저장 완료")
        st.markdown("</div>", unsafe_allow_html=True)


# roster/sessions 재동기화
roster = st.session_state.roster
sessions = st.session_state.sessions
roster_by_name = {p.get("name"): p for p in roster if p.get("name")}


# =========================================================
# TAB2) 오늘 경기 세션  (✅ 사용자가 준 코드 중심)
# =========================================================
with tab2:
    section_card("오늘 경기 세션", "🎾")

    # =========================================================
    # [TAB2] 수동 배정 유틸 (중복 방지 + 빈칸만 채우기)
    # =========================================================
    def _ensure_manual_prefill():
        if "_manual_prefill" not in st.session_state or not isinstance(st.session_state.get("_manual_prefill"), dict):
            st.session_state["_manual_prefill"] = {}
        if "_manual_prefill_used" not in st.session_state:
            st.session_state["_manual_prefill_used"] = False

    def _set_manual_prefill(plan: dict):
        _ensure_manual_prefill()
        st.session_state["_manual_prefill"].update(plan)
        st.session_state["_manual_prefill_used"] = True

    def _manual_key(r: int, c: int, pos: int, gtype: str) -> str:
        gt = "D" if gtype == "복식" else "S"
        return f"man_{gt}_r{r}_c{c}_p{pos}"

    def _manual_all_keys_for_round(r: int, court_count: int, gtype: str):
        keys = []
        if gtype == "단식":
            for c in range(1, int(court_count) + 1):
                keys.append(_manual_key(r, c, 1, gtype))
                keys.append(_manual_key(r, c, 2, gtype))
        else:
            for c in range(1, int(court_count) + 1):
                for pos in (1, 2, 3, 4):
                    keys.append(_manual_key(r, c, pos, gtype))
        return keys

    def _get_manual_value(k: str) -> str:
        return st.session_state.get(k, "선택")

    def _round_used_set(r: int, court_count: int, gtype: str):
        used = set()
        for k in _manual_all_keys_for_round(r, court_count, gtype):
            v = _get_manual_value(k)
            if v and v != "선택":
                used.add(v)
        return used

    def _make_on_change_validator(r: int, key: str, court_count: int, gtype: str):
        def _cb():
            cur = st.session_state.get(key, "선택")
            if not cur or cur == "선택":
                st.session_state[f"_prev_{key}"] = "선택"
                return

            # 같은 라운드 내 중복 선택 방지
            for k in _manual_all_keys_for_round(r, court_count, gtype):
                if k == key:
                    continue
                if st.session_state.get(k, "선택") == cur:
                    st.session_state[key] = st.session_state.get(f"_prev_{key}", "선택")
                    return

            st.session_state[f"_prev_{key}"] = cur

        return _cb

    def _apply_manual_pending():
        pending = st.session_state.pop("_manual_pending_set", None)
        if isinstance(pending, dict) and pending:
            # ✅ 위젯 생성 전에 state에 박아넣어야 화면에 반영됨
            for k, v in pending.items():
                if v and v != "선택":
                    st.session_state[k] = v
                    st.session_state[f"_prev_{k}"] = v

    def _court_group_tag(view_mode: str, court_index: int):
        if view_mode == "조별 분리 (A/B조)":
            return "A" if (court_index % 2 == 1) else "B"
        return None

    def _pool_by_group(players_selected, grp_tag):
        if not grp_tag:
            return players_selected
        if grp_tag == "A":
            return [p for p in players_selected if roster_by_name.get(p, {}).get("group") == "A조"]
        if grp_tag == "B":
            return [p for p in players_selected if roster_by_name.get(p, {}).get("group") == "B조"]
        return players_selected

    def _build_filtered_options_for_key(r: int, k: str, pool, court_count: int, gtype: str):
        current = _get_manual_value(k)

        used = _round_used_set(r, court_count, gtype)
        if current and current != "선택":
            used = set(used) - {current}

        opts = ["선택"] + [p for p in sorted(pool) if p not in used]
        if current and current != "선택" and current not in opts:
            opts.insert(1, current)

        idx = opts.index(current) if current in opts else 0
        return opts, idx

    def _fill_round_plan(
        r: int,
        players_selected,
        court_count: int,
        gtype: str,
        view_mode: str,
        gender_mode: str,  # "랜덤" / "동성" / "혼합"
        ntrp_on: bool,
    ):
        plan = {}

        keys_round = _manual_all_keys_for_round(r, court_count, gtype)
        fixed = {k: _get_manual_value(k) for k in keys_round}
        used = {v for v in fixed.values() if v and v != "선택"}

        for c in range(1, int(court_count) + 1):
            grp_tag = _court_group_tag(view_mode, c)
            pool = _pool_by_group(players_selected, grp_tag)

            if gtype == "단식":
                k1 = _manual_key(r, c, 1, gtype)
                k2 = _manual_key(r, c, 2, gtype)
                v1 = fixed.get(k1, "선택")
                v2 = fixed.get(k2, "선택")

                if v1 != "선택" and v2 != "선택":
                    continue

                avail = [p for p in pool if p not in used]

                if v1 != "선택" and v2 == "선택":
                    cand = avail
                    if gender_mode == "동성":
                        g1 = _gender_of(v1, roster_by_name)
                        cand = [p for p in cand if _gender_of(p, roster_by_name) == g1]
                    pick = (
                        _pick_by_ntrp_closest(cand, _ntrp_of(v1, roster_by_name), roster_by_name)
                        if ntrp_on
                        else (random.choice(cand) if cand else None)
                    )
                    if pick:
                        plan[k2] = pick
                        used.add(pick)
                    continue

                if v1 == "선택" and v2 != "선택":
                    cand = avail
                    if gender_mode == "동성":
                        g2 = _gender_of(v2, roster_by_name)
                        cand = [p for p in cand if _gender_of(p, roster_by_name) == g2]
                    pick = (
                        _pick_by_ntrp_closest(cand, _ntrp_of(v2, roster_by_name), roster_by_name)
                        if ntrp_on
                        else (random.choice(cand) if cand else None)
                    )
                    if pick:
                        plan[k1] = pick
                        used.add(pick)
                    continue

                if v1 == "선택" and v2 == "선택":
                    cand = avail
                    if len(cand) >= 2:
                        if ntrp_on:
                            a = random.choice(cand)
                            cand2 = [x for x in cand if x != a]
                            b = _pick_by_ntrp_closest(cand2, _ntrp_of(a, roster_by_name), roster_by_name)
                            if b:
                                plan[k1], plan[k2] = a, b
                                used.update([a, b])
                        else:
                            a, b = random.sample(cand, 2)
                            plan[k1], plan[k2] = a, b
                            used.update([a, b])
                continue

            # ---------------- 복식 ----------------
            ks = [_manual_key(r, c, i, gtype) for i in (1, 2, 3, 4)]
            vs = [fixed.get(k, "선택") for k in ks]
            empty_keys = [k for k, v in zip(ks, vs) if v == "선택"]
            if not empty_keys:
                continue

            already = [v for v in vs if v != "선택"]
            avail = [p for p in pool if p not in used]
            men = [p for p in avail if _gender_of(p, roster_by_name) == "남"]
            women = [p for p in avail if _gender_of(p, roster_by_name) == "여"]

            need = len(empty_keys)
            picks = []

            if gender_mode == "혼합":
                already_m = sum(1 for x in already if _gender_of(x, roster_by_name) == "남")
                already_w = sum(1 for x in already if _gender_of(x, roster_by_name) == "여")

                while len(picks) < need:
                    want_m = (already_m + sum(1 for x in picks if _gender_of(x, roster_by_name) == "남")) < 2
                    want_w = (already_w + sum(1 for x in picks if _gender_of(x, roster_by_name) == "여")) < 2

                    if want_m and men:
                        pick = random.choice(men) if not ntrp_on else _pick_by_ntrp_closest(men, None, roster_by_name)
                        men.remove(pick)
                    elif want_w and women:
                        pick = random.choice(women) if not ntrp_on else _pick_by_ntrp_closest(women, None, roster_by_name)
                        women.remove(pick)
                    else:
                        rest = men + women
                        if not rest:
                            break
                        pick = random.choice(rest) if not ntrp_on else _pick_by_ntrp_closest(rest, None, roster_by_name)
                        if pick in men:
                            men.remove(pick)
                        else:
                            women.remove(pick)

                    picks.append(pick)

            elif gender_mode == "동성":
                already_gender = _gender_of(already[0], roster_by_name) if already else None
                cand = men if already_gender == "남" else women if already_gender == "여" else (men if len(men) >= need else women)
                if len(cand) >= need:
                    picks = random.sample(cand, need)

            else:
                rest = men + women
                if len(rest) >= need:
                    picks = random.sample(rest, need)

            for k, p in zip(empty_keys, picks):
                plan[k] = p
                used.add(p)

        # ✅ 기존 값은 유지
        for k, v in fixed.items():
            if v and v != "선택":
                plan.setdefault(k, v)

        return plan

    # =========================================================
    # ✅ 조별 분리 대진 생성용 헬퍼 (핵심)
    # =========================================================
    def _split_players_ab(players, roster_by_name):
        a = [p for p in players if roster_by_name.get(p, {}).get("group") == "A조"]
        b = [p for p in players if roster_by_name.get(p, {}).get("group") == "B조"]
        other = [p for p in players if p not in set(a) and p not in set(b)]
        return a, b, other

    def _remap_courts(schedule_list, court_map):
        out = []
        for gt, t1, t2, c in schedule_list:
            try:
                ci = int(c)
            except Exception:
                ci = None

            if ci is not None and 1 <= ci <= len(court_map):
                out.append((gt, t1, t2, court_map[ci - 1]))
            else:
                out.append((gt, t1, t2, c))
        return out

    def _interleave_by_round(sa, sb, ca, cb, total_rounds=None):
        out = []
        if total_rounds is not None:
            for r in range(int(total_rounds)):
                out += sa[r * ca:(r + 1) * ca]
                out += sb[r * cb:(r + 1) * cb]
            return out

        ia = ib = 0
        while ia < len(sa) or ib < len(sb):
            out += sa[ia:ia + ca]
            ia += ca
            out += sb[ib:ib + cb]
            ib += cb
        return out

    # =========================================================
    # 0. 저장할 날짜 선택
    # =========================================================
    st.subheader("1. 저장할 날짜 선택")

    if "save_date" not in st.session_state:
        st.session_state.save_date = date.today()

    st.session_state.save_date = st.date_input(
        "이 날짜 기준으로 대진을 관리합니다.",
        value=st.session_state.save_date,
        key="save_date_input",
    )

    save_date = st.session_state.save_date
    save_date_str = save_date.strftime("%Y-%m-%d")
    st.session_state["save_target_date"] = save_date_str

    # =========================================================
    # 1. 참가자 선택 + 게스트 + 스페셜 매치
    # =========================================================
    st.subheader("2. 참가자 선택")

    if "current_order" not in st.session_state:
        st.session_state.current_order = []
    if "shuffle_count" not in st.session_state:
        st.session_state.shuffle_count = 0

    if "guest_mode" not in st.session_state:
        st.session_state.guest_mode = False
    if "special_match" not in st.session_state:
        st.session_state.special_match = False
    if "guest_list" not in st.session_state:
        st.session_state.guest_list = []
    if "_injected_guest_names" not in st.session_state:
        st.session_state._injected_guest_names = []

    guest_list = st.session_state.guest_list
    names_all_members = [p["name"] for p in roster]

    def _on_guest_toggle():
        if st.session_state.get("chk_guest_mode", False):
            st.session_state["chk_special_match"] = False
            st.session_state.special_match = False
            st.session_state.guest_mode = True
        else:
            st.session_state.guest_mode = False

    def _on_special_toggle():
        if st.session_state.get("chk_special_match", False):
            st.session_state["chk_guest_mode"] = False
            st.session_state.guest_mode = False
            st.session_state.special_match = True
        else:
            st.session_state.special_match = False

    col_ms, col_sp = st.columns([3, 2])
    with col_sp:
        guest_mode_ui = st.checkbox(
            "👥 게스트 추가",
            value=st.session_state.guest_mode,
            help="게스트를 오늘만 임시 추가합니다. 회원 명단에는 저장되지 않습니다.",
            key="chk_guest_mode",
            on_change=_on_guest_toggle,
        )
        special_match_ui = st.checkbox(
            "🌟 스페셜 매치 (교류전)",
            value=st.session_state.special_match,
            help="스페셜 매치로 저장된 날짜는 월별/개인 통계에서 제외됩니다.",
            key="chk_special_match",
            on_change=_on_special_toggle,
        )
        st.session_state.guest_mode = bool(guest_mode_ui)
        st.session_state.special_match = bool(special_match_ui)

    guest_enabled = bool(st.session_state.guest_mode or st.session_state.special_match)

    if not guest_enabled and st.session_state._injected_guest_names:
        for nm in list(st.session_state._injected_guest_names):
            if roster_by_name.get(nm, {}).get("is_guest", False):
                roster_by_name.pop(nm, None)
        st.session_state._injected_guest_names = []

    if guest_enabled:
        st.markdown(
            """
            <div style="
                margin:0.3rem 0 0.5rem 0;
                padding:0.7rem 1.0rem;
                border-radius:10px;
                background:#eff6ff;
                border:1px solid #bfdbfe;
                font-size:0.9rem;
            ">
                게스트를 추가할 수 있습니다.<br/>
                게스트는 오늘 날짜에만 사용되며, 회원 명단에는 저장되지 않습니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

        GUEST_GROUP_OPTIONS = ["미배정", "A조", "B조"]
        gc1, gc2, gc3, gc4, gc5 = st.columns([2.5, 1.0, 1.2, 1.1, 1.2])

        with gc1:
            guest_name = st.text_input("게스트 이름", key="guest_name_input", placeholder="예: 차은우")
        with gc2:
            guest_gender = st.selectbox("성별", ["남", "여"], index=0, key="guest_gender_input")
        with gc3:
            guest_group = st.selectbox("조", GUEST_GROUP_OPTIONS, index=0, key="guest_group_input")
        with gc4:
            guest_ntrp = st.selectbox("NTRP", NTRP_OPTIONS, index=0, key="guest_ntrp_input")
        with gc5:
            st.markdown("<div style='margin-top:1.65rem;'></div>", unsafe_allow_html=True)
            add_guest_clicked = st.button("게스트 추가", use_container_width=True, key="btn_add_guest_once")

        if add_guest_clicked:
            name_clean = (guest_name or "").strip()
            if not name_clean:
                st.warning("게스트 이름을 입력해 주세요.")
            else:
                if any(g.get("name") == name_clean for g in guest_list):
                    st.warning("이미 같은 이름의 게스트가 있습니다.")
                else:
                    guest_list.append(
                        {"name": name_clean, "gender": guest_gender, "group": guest_group, "ntrp": guest_ntrp}
                    )
                    st.session_state.guest_list = guest_list
                    st.session_state["guest_add_msg"] = f"게스트 '{name_clean}' 추가되었습니다."
                    safe_rerun()

        if st.session_state.get("guest_add_msg"):
            st.success(st.session_state["guest_add_msg"])
            st.session_state["guest_add_msg"] = None

        if guest_list:
            st.markdown("#### 오늘 게스트 목록")
            for i, g in enumerate(guest_list, start=1):
                c1, c2, c3 = st.columns([2.0, 3.0, 1.0])
                with c1:
                    st.write(f"{i}. {g['name']}")
                with c2:
                    st.write(
                        f"성별: {g.get('gender', '남')} / "
                        f"조: {g.get('group', '미배정')} / "
                        f"NTRP: {g.get('ntrp', '모름')}"
                    )
                with c3:
                    if st.button("삭제", use_container_width=True, key=f"btn_del_guest_{i}"):
                        guest_list.pop(i - 1)
                        st.session_state.guest_list = guest_list
                        safe_rerun()

    guest_names = [g["name"] for g in guest_list] if guest_enabled else []
    names_all = names_all_members + guest_names
    names_sorted = sorted(names_all, key=lambda n: n)

    with col_ms:
        sel_players = st.multiselect("오늘 참가 선수들", names_sorted, default=[], key="ms_today_players")

    if guest_enabled:
        players_for_today = sorted(set(sel_players) | set(guest_names), key=lambda n: n)
    else:
        players_for_today = sel_players

    st.write(f"현재 참가 인원: {len(players_for_today)}명")

    if guest_enabled and guest_list:
        injected = []
        for g in guest_list:
            nm = g["name"]
            roster_by_name[nm] = {
                "name": nm,
                "gender": g.get("gender", "남"),
                "ntrp": None if g.get("ntrp") in ("모름", None, "") else float(g.get("ntrp")),
                "group": g.get("group", "미배정"),
                "age_group": "비밀",
                "racket": "모름",
                "hand": "오른손",
                "mbti": "모름",
                "is_guest": True,
            }
            injected.append(nm)
        st.session_state._injected_guest_names = injected

    # =========================================================
    # 순서 초기화
    # =========================================================
    if players_for_today:
        prev = st.session_state.current_order
        if (not prev) or (set(prev) != set(players_for_today)):
            st.session_state.current_order = players_for_today.copy()
            st.session_state.shuffle_count = 0
    else:
        st.session_state.current_order = []
        st.session_state.shuffle_count = 0

    current_order = st.session_state.current_order

    # =========================================================
    # 2. 순서 정하기
    # =========================================================
    st.subheader("3. 순서 정하기")

    order_mode_ui = st.radio(
        "순서 방식",
        ["랜덤 섞기", "수동 입력"],
        horizontal=True,
        key="order_mode_radio",
    )
    st.session_state.order_mode = "자동" if order_mode_ui == "랜덤 섞기" else "수동"

    if order_mode_ui == "랜덤 섞기":
        cb, ci = st.columns([1.6, 2.4])
        with cb:
            st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
            if st.button("랜덤으로 순서 섞기", use_container_width=True, key="btn_shuffle_order"):
                random.shuffle(current_order)
                st.session_state.current_order = current_order
                st.session_state.shuffle_count += 1
            st.markdown("</div>", unsafe_allow_html=True)
        with ci:
            st.write(f"섞은 횟수: {st.session_state.shuffle_count} 회")
    else:
        default_text = "\n".join(current_order) if current_order else ""
        text = st.text_area(
            "한 줄에 한 명씩 이름을 입력 (선택한 사람들만)",
            value=default_text,
            height=140,
            key="manual_order_text",
        )
        if st.button("수동 순서 적용", key="btn_apply_manual_order"):
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                st.warning("한 명 이상 입력해 주세요.")
            elif set(lines) != set(players_for_today):
                st.error("선택된 참가자와 이름 목록이 일치하지 않습니다.")
            else:
                st.session_state.current_order = lines
                current_order = lines
                st.success("수동 순서가 적용되었습니다.")

    # =========================================================
    # 현재 순서 표시 (전체 / 조별 분리)
    # =========================================================
    view_mode = "전체"
    if current_order:
        default_view = st.session_state.get("order_view_mode", "전체")
        default_idx = 0 if default_view == "전체" else 1

        view_mode = st.radio(
            "순서 표시 방식",
            ["전체", "조별 분리 (A/B조)"],
            horizontal=True,
            index=default_idx,
            key="order_view_mode",
        )

        if view_mode == "전체":
            st.write("현재 순서:")
            for i, n in enumerate(current_order, start=1):
                badge = render_name_badge(n, roster_by_name)
                st.markdown(f"{i}. {badge}", unsafe_allow_html=True)
        else:
            groups = {name: roster_by_name.get(name, {}).get("group", "미배정") for name in current_order}
            a_list = [p for p in current_order if groups.get(p) == "A조"]
            b_list = [p for p in current_order if groups.get(p) == "B조"]

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**현재 순서: A조**")
                if a_list:
                    for i, n in enumerate(a_list, start=1):
                        badge = render_name_badge(n, roster_by_name)
                        st.markdown(f"{i}. {badge}", unsafe_allow_html=True)
                else:
                    st.caption("A조 선수 없음")

            with col_b:
                st.markdown("**현재 순서: B조**")
                if b_list:
                    for i, n in enumerate(b_list, start=1):
                        badge = render_name_badge(n, roster_by_name)
                        st.markdown(f"{i}. {badge}", unsafe_allow_html=True)
                else:
                    st.caption("B조 선수 없음")

    # =========================================================
    # 3. 대진 설정
    # =========================================================
    st.subheader("4. 대진 설정")

    players_selected = current_order.copy()

    gtype = st.radio("게임 타입", ["복식", "단식"], horizontal=True, key="gtype_radio")
    make_mode = st.radio("대진 생성 방식", ["자동 생성", "직접 배정(수동)"], horizontal=True, key="make_mode_radio")
    is_manual_mode = (make_mode == "직접 배정(수동)")

    auto_basis = "개인당 경기 수 기준"
    if not is_manual_mode:
        auto_basis = st.radio(
            "자동 생성 기준",
            ["개인당 경기 수 기준", "총 게임 수(라운드 수) 기준"],
            horizontal=True,
            key="auto_basis_radio",
        )

    mode_label = None
    singles_mode = None

    if gtype == "복식":
        doubles_modes = [
            "랜덤 복식",
            "동성복식 (남+남 / 여+여)",
            "혼합복식 (남+여 짝)",
            "한울 AA 방식 (4게임 고정)",
        ]
        mode_label = st.selectbox(
            "복식 대진 방식",
            doubles_modes,
            index=3,
            key="doubles_mode_select",
            disabled=is_manual_mode,
        )
        is_aa_mode = ("한울 AA" in str(mode_label))
    else:
        singles_mode = st.selectbox(
            "단식 대진 방식",
            ["랜덤 단식", "동성 단식", "혼합 단식"],
            key="singles_mode_select",
            disabled=is_manual_mode,
        )
        is_aa_mode = False

    unit = 4 if gtype == "복식" else 2

    cg1, cg2 = st.columns(2)
    with cg1:
        if is_manual_mode:
            max_games = st.number_input(
                "개인당 경기 수 (수동에서는 비활성화)",
                min_value=1, max_value=10, value=4, step=1,
                disabled=True, key="max_games_input",
            )
        else:
            if auto_basis != "개인당 경기 수 기준":
                max_games = st.number_input(
                    "개인당 경기 수",
                    min_value=1, max_value=10, value=4, step=1,
                    disabled=True, key="max_games_input",
                    help="총 게임 수(라운드 수) 기준에서는 사용되지 않습니다.",
                )
            else:
                if gtype == "복식" and is_aa_mode:
                    max_games = st.number_input(
                        "개인당 경기 수 (한울 AA: 4게임 고정)",
                        min_value=4, max_value=4, value=4, step=1,
                        disabled=True, key="max_games_input",
                    )
                else:
                    max_games = st.number_input(
                        "개인당 경기 수 (정확히 이 횟수로 배정)",
                        min_value=1, max_value=10, value=4, step=1,
                        key="max_games_input",
                    )

        total_rounds_enabled = is_manual_mode or (auto_basis == "총 게임 수(라운드 수) 기준")

        if total_rounds_enabled:
            total_rounds = st.number_input(
                "총 게임 수 (라운드 수)",
                min_value=1, max_value=80,
                value=int(st.session_state.get("total_rounds_input", 2)),
                step=1, key="total_rounds_input",
                help="수동 배정 또는 자동 생성(총 게임 수 기준)일 때 입력합니다.",
            )
        else:
            total_rounds = int(st.session_state.get("total_rounds_input", 2))
            if players_selected:
                needed_slots = len(players_selected) * int(max_games)
                matches = needed_slots / unit if unit else 0
                court_hint = int(st.session_state.get("court_count_input", 2)) or 1
                rounds_hint = math.ceil(matches / court_hint) if matches else 0
                st.caption(f"총 게임 수(라운드 수)는 개인당 기준에서는 자동 계산됩니다. (대략 {rounds_hint} 라운드 예상)")

    with cg2:
        if (gtype == "복식" and is_aa_mode and (not is_manual_mode)):
            court_count = st.number_input(
                "사용 코트 수 (한울 AA 모드에서는 고정값)",
                min_value=1, max_value=6, value=2, step=1,
                disabled=True, key="court_count_input",
            )
        else:
            court_count = st.number_input(
                "사용 코트 수",
                min_value=1, max_value=6, value=2, step=1,
                key="court_count_input",
            )

    opt1, opt2 = st.columns(2)
    with opt1:
        use_ntrp = st.checkbox(
            "NTRP 고려 (비슷한 실력끼리 매칭)",
            value=False,
            disabled=(is_manual_mode or (gtype == "복식" and is_aa_mode)),
            key="use_ntrp_chk",
        )
    with opt2:
        group_only_option = st.checkbox(
            "조별로만 매칭 (A/B조만, C조 제외)",
            value=False,
            disabled=(is_manual_mode or (gtype == "복식" and is_aa_mode)),
            key="group_only_chk",
        )

    view_mode_for_schedule = st.session_state.get("order_view_mode", "전체")
    group_only = bool(group_only_option)

    if (gtype == "복식") and is_aa_mode and (not is_manual_mode):
        st.info(
            "한울 AA 방식은 5~16명에서 사용하는 고정 패턴입니다.\n"
            "- 항상 복식 전용, 개인당 4게임 고정입니다.\n"
            "- NTRP / 조별 매칭 / 혼복 옵션은 적용되지 않습니다.\n"
            "- 사용 코트 수는 현재 값으로 고정됩니다."
        )

    # =========================================================
    # 4-1. 직접 배정(수동) 입력
    # =========================================================
    if is_manual_mode:
        st.markdown("---")
        st.subheader("4-1. 직접 배정(수동) 입력")
        st.caption("※ 한 라운드 안에서는 같은 선수가 중복 선택되지 않도록 제한됩니다.")

        # ✅ pending → session_state (위젯 렌더 전에만!)
        _apply_manual_pending()

        st.markdown("**성별 옵션**")
        manual_gender_mode = st.radio(
            "성별 옵션",
            ["성별랜덤", "동성", "혼합"],
            horizontal=True,
            key="manual_gender_mode",
            label_visibility="collapsed",
        )
        manual_fill_ntrp = st.checkbox("NTRP 고려", key="manual_fill_ntrp")



        b1, b2, b3 = st.columns(3)
        with b1:
            st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
            fill_all_clicked = st.button(
                "빈칸 자동 채우기(전체 라운드)",
                use_container_width=True,
                key="btn_fill_all_rounds",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with b2:
            st.markdown('<div class="main-danger-btn">', unsafe_allow_html=True)
            clear_all_clicked = st.button(
                "전체 초기화(수동 입력)",
                use_container_width=True,
                key="btn_clear_all_rounds",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with b3:
            st.caption("라운드별 자동 채우기/초기화는 아래 라운드 박스에서도 가능")

        # ✅ plan을 '바로' state에 반영 (pending/rerun 제거)
        def _apply_plan_to_state(plan: dict):
            if not isinstance(plan, dict):
                return
            for k, v in plan.items():
                if v and v != "선택":
                    st.session_state[k] = v
                    st.session_state[f"_prev_{k}"] = v

        # -------------------------
        # 전체 초기화
        # -------------------------
        if clear_all_clicked:
            for rr in range(1, int(total_rounds) + 1):
                for k in _manual_all_keys_for_round(rr, court_count, gtype):
                    st.session_state[k] = "선택"
                    st.session_state[f"_prev_{k}"] = "선택"

            st.session_state["_manual_prefill"] = {}
            st.session_state["_manual_prefill_used"] = False
            st.session_state.pop("_manual_pending_set", None)  # 혹시 남아있던 거 제거

        # -------------------------
        # 전체 라운드 빈칸 채우기
        # -------------------------
        if fill_all_clicked and players_selected:
            plan_all = {}
            for rr in range(1, int(total_rounds) + 1):
                plan_r = _fill_round_plan(
                    r=rr,
                    players_selected=players_selected,
                    court_count=court_count,
                    gtype=gtype,
                    view_mode=view_mode_for_schedule,
                    gender_mode=("혼합" if manual_gender_mode == "혼합" else "동성" if manual_gender_mode == "동성" else "랜덤"),
                    ntrp_on=bool(manual_fill_ntrp),
                )
                plan_all.update(plan_r)

            if plan_all:
                _apply_plan_to_state(plan_all)
            else:
                st.info("이미 채울 빈칸이 없어.")

        # -------------------------
        # 라운드 UI
        # -------------------------
        for r in range(1, int(total_rounds) + 1):
            with st.expander(f"라운드 {r}", expanded=(r == 1)):

                used = _round_used_set(r, court_count, gtype)

                top1, top2, top3 = st.columns([3.2, 3.2, 1.6], vertical_alignment="center")

                with top1:
                    st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
                    fill_round_clicked = st.button(
                        "이 라운드 빈칸 채우기",
                        use_container_width=True,
                        key=f"btn_fill_round_{r}",
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

                with top2:
                    st.markdown('<div class="main-danger-btn">', unsafe_allow_html=True)
                    clear_round_clicked = st.button(
                        "이 라운드 초기화",
                        use_container_width=True,
                        key=f"btn_clear_round_{r}",
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

                with top3:
                    st.markdown(
                        f"<div style='text-align:right; font-weight:700; color:#374151;'>선택됨: {len(used)}명</div>",
                        unsafe_allow_html=True
                    )

                # ✅ 이 라운드 초기화
                if clear_round_clicked:
                    for k in _manual_all_keys_for_round(r, court_count, gtype):
                        st.session_state[k] = "선택"
                        st.session_state[f"_prev_{k}"] = "선택"

                    pre = st.session_state.get("_manual_prefill", {})
                    for k in _manual_all_keys_for_round(r, court_count, gtype):
                        pre.pop(k, None)
                    st.session_state["_manual_prefill"] = pre

                # ✅ 이 라운드 빈칸 채우기
                if fill_round_clicked:
                    plan = _fill_round_plan(
                        r=r,
                        players_selected=players_selected,
                        court_count=court_count,
                        gtype=gtype,
                        view_mode=view_mode_for_schedule,
                        gender_mode=("혼합" if manual_gender_mode == "혼합" else "동성" if manual_gender_mode == "동성" else "랜덤"),
                        ntrp_on=bool(manual_fill_ntrp),
                    )
                    if plan:
                        _apply_plan_to_state(plan)
                    else:
                        st.info("이 라운드는 이미 빈칸이 없어.")

                st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

                # (👇 여기 아래 코트별 selectbox 렌더 부분은 너 원래 코드 그대로 두면 됨)

                st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

                for c in range(1, int(court_count) + 1):
                    st.markdown(f"**코트 {c}**")

                    grp_tag = _court_group_tag(view_mode_for_schedule, c)
                    pool = _pool_by_group(players_selected, grp_tag)

                    if gtype == "단식":
                        k1 = _manual_key(r, c, 1, gtype)
                        k2 = _manual_key(r, c, 2, gtype)

                        col1, colVS, col2 = st.columns([3.2, 0.9, 3.2], vertical_alignment="center")

                        with col1:
                            opts, idx = _build_filtered_options_for_key(r, k1, pool, court_count, gtype)
                            st.selectbox(
                                "p1",
                                opts,
                                index=idx,
                                key=k1,
                                label_visibility="collapsed",
                                on_change=_make_on_change_validator(r, k1, court_count, gtype),
                            )
                            st.session_state[f"_prev_{k1}"] = st.session_state.get(k1, "선택")

                        with colVS:
                            st.markdown("<div style='text-align:center; font-weight:900;'>VS</div>", unsafe_allow_html=True)

                        with col2:
                            opts, idx = _build_filtered_options_for_key(r, k2, pool, court_count, gtype)
                            st.selectbox(
                                "p2",
                                opts,
                                index=idx,
                                key=k2,
                                label_visibility="collapsed",
                                on_change=_make_on_change_validator(r, k2, court_count, gtype),
                            )
                            st.session_state[f"_prev_{k2}"] = st.session_state.get(k2, "선택")

                    else:
                        k1 = _manual_key(r, c, 1, gtype)
                        k2 = _manual_key(r, c, 2, gtype)
                        k3 = _manual_key(r, c, 3, gtype)
                        k4 = _manual_key(r, c, 4, gtype)

                        col1, col2, colVS, col3, col4 = st.columns(
                            [2.6, 2.6, 0.9, 2.6, 2.6],
                            vertical_alignment="center"
                        )

                        with col1:
                            opts, idx = _build_filtered_options_for_key(r, k1, pool, court_count, gtype)
                            st.selectbox(
                                "t1a",
                                opts,
                                index=idx,
                                key=k1,
                                label_visibility="collapsed",
                                on_change=_make_on_change_validator(r, k1, court_count, gtype),
                            )
                            st.session_state[f"_prev_{k1}"] = st.session_state.get(k1, "선택")

                        with col2:
                            opts, idx = _build_filtered_options_for_key(r, k2, pool, court_count, gtype)
                            st.selectbox(
                                "t1b",
                                opts,
                                index=idx,
                                key=k2,
                                label_visibility="collapsed",
                                on_change=_make_on_change_validator(r, k2, court_count, gtype),
                            )
                            st.session_state[f"_prev_{k2}"] = st.session_state.get(k2, "선택")

                        with colVS:
                            st.markdown("<div style='text-align:center; font-weight:900;'>VS</div>", unsafe_allow_html=True)

                        with col3:
                            opts, idx = _build_filtered_options_for_key(r, k3, pool, court_count, gtype)
                            st.selectbox(
                                "t2a",
                                opts,
                                index=idx,
                                key=k3,
                                label_visibility="collapsed",
                                on_change=_make_on_change_validator(r, k3, court_count, gtype),
                            )
                            st.session_state[f"_prev_{k3}"] = st.session_state.get(k3, "선택")

                        with col4:
                            opts, idx = _build_filtered_options_for_key(r, k4, pool, court_count, gtype)
                            st.selectbox(
                                "t2b",
                                opts,
                                index=idx,
                                key=k4,
                                label_visibility="collapsed",
                                on_change=_make_on_change_validator(r, k4, court_count, gtype),
                            )
                            st.session_state[f"_prev_{k4}"] = st.session_state.get(k4, "선택")

                    st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

                st.markdown("---")

        # -------------------------
        # 수동 대진 리스트 만들기 (실제 위젯 값 기준)
        # -------------------------
        manual_schedule = []
        for rr in range(1, int(total_rounds) + 1):
            for cc in range(1, int(court_count) + 1):
                if gtype == "단식":
                    k1 = _manual_key(rr, cc, 1, gtype)
                    k2 = _manual_key(rr, cc, 2, gtype)
                    a = st.session_state.get(k1, "선택")
                    b = st.session_state.get(k2, "선택")
                    if a != "선택" and b != "선택" and a != b:
                        manual_schedule.append(("단식", [a], [b], cc))
                else:
                    ks = [_manual_key(rr, cc, i, gtype) for i in (1, 2, 3, 4)]
                    vals = [st.session_state.get(k, "선택") for k in ks]
                    if all(v != "선택" for v in vals) and len(set(vals)) == 4:
                        manual_schedule.append(("복식", [vals[0], vals[1]], [vals[2], vals[3]], cc))

        st.session_state.today_schedule = manual_schedule


    # =========================================================
    # 5. 대진표 생성 / 미리보기 / 저장  (✅ 자동/수동 공통 영역)
    # =========================================================
    st.markdown("---")
    st.subheader("5. 대진표 생성 / 미리보기")

    col_gen, col_save = st.columns(2)
    with col_gen:
        st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
        gen_clicked = st.button("대진표 생성하기", use_container_width=True, key="gen_btn")
        st.markdown("</div>", unsafe_allow_html=True)
    with col_save:
        st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
        save_clicked = st.button("저장하기", use_container_width=True, key="save_btn")
        st.markdown("</div>", unsafe_allow_html=True)

    def build_best_auto_schedule():
        if not players_selected:
            return []

        # AA 모드
        if (gtype == "복식") and ("한울 AA" in str(mode_label)):
            ordered = players_selected[:]
            return build_hanul_aa_schedule(ordered, int(court_count))

        # 일반 모드: 목표 게임수 추정
        if auto_basis == "개인당 경기 수 기준":
            target_games = int(max_games)
        else:
            schedule_len_guess = int(total_rounds) * int(court_count)
            total_slots = schedule_len_guess * (4 if gtype == "복식" else 2)
            target_games = max(1, int(round(total_slots / max(1, len(players_selected)))))

        mode_name = mode_label if gtype == "복식" else singles_mode

        def build_group(players_group, cc):
            if len(players_group) < (4 if gtype == "복식" else 2):
                return []

            if gtype == "복식":
                mode_arg = "랜덤 복식"
                if mode_name == "동성복식 (남+남 / 여+여)":
                    mode_arg = "동성복식"
                elif mode_name == "혼합복식 (남+여 짝)":
                    mode_arg = "혼합복식"

                if auto_basis == "총 게임 수(라운드 수) 기준":
                    return build_schedule_by_total_rounds(
                        players=players_group,
                        gtype="복식",
                        court_count=int(cc),
                        total_rounds=int(total_rounds),
                        mode_name=mode_name,
                        use_ntrp=bool(use_ntrp),
                        roster_by_name=roster_by_name,
                    )

                return build_doubles_schedule(
                    players=players_group,
                    max_games=int(target_games),
                    court_count=int(cc),
                    mode=mode_arg,
                    use_ntrp=bool(use_ntrp),
                    group_only=bool(group_only),
                    roster_by_name=roster_by_name,

                )

            else:
                mode_arg = "랜덤 단식"
                if mode_name == "동성 단식":
                    mode_arg = "동성 단식"
                elif mode_name == "혼합 단식":
                    mode_arg = "혼합 단식"

                if auto_basis == "총 게임 수(라운드 수) 기준":
                    return build_schedule_by_total_rounds(
                        players=players_group,
                        gtype="단식",
                        court_count=int(cc),
                        total_rounds=int(total_rounds),
                        mode_name=mode_name,
                        use_ntrp=bool(use_ntrp),
                        roster_by_name=roster_by_name,
                    )

                return build_singles_schedule(
                    players=players_group,
                    max_games=int(target_games),
                    court_count=int(cc),
                    mode=mode_arg,
                    use_ntrp=bool(use_ntrp),
                    group_only=bool(group_only),
                    roster_by_name=roster_by_name,
                )

        # ✅ 조별 분리면: A/B를 "코트 홀수/짝수"로 나눠 따로 생성 후 합침
        if view_mode_for_schedule == "조별 분리 (A/B조)":
            courts_A = [c for c in range(1, int(court_count) + 1) if c % 2 == 1]
            courts_B = [c for c in range(1, int(court_count) + 1) if c % 2 == 0]
            ca, cb = len(courts_A), len(courts_B)

            if ca > 0 and cb > 0:
                players_A, players_B, _ = _split_players_ab(players_selected, roster_by_name)

                tries = 80
                for _ in range(tries):
                    sched_A = build_group(players_A, ca)
                    sched_B = build_group(players_B, cb)

                    if sched_A and sched_B:
                        sched_A = _remap_courts(sched_A, courts_A)
                        sched_B = _remap_courts(sched_B, courts_B)

                        if auto_basis == "총 게임 수(라운드 수) 기준":
                            merged = _interleave_by_round(sched_A, sched_B, ca, cb, total_rounds=int(total_rounds))
                        else:
                            merged = _interleave_by_round(sched_A, sched_B, ca, cb, total_rounds=None)

                        if merged:
                            return merged

            # 폴백: 조별 분리인데 한쪽 코트가 없거나 생성 실패하면 전체 생성
            tries = 80
            best = []
            for _ in range(tries):
                cand = build_group(players_selected, int(court_count))
                if cand:
                    best = cand
                    break
            return best

        # ✅ 전체 모드면: 기존처럼 전체 생성
        tries = 80
        best = []
        for _ in range(tries):
            cand = build_group(players_selected, int(court_count))
            if cand:
                best = cand
                break
        return best

    # 생성
    if gen_clicked:
        if len(players_selected) < (4 if gtype == "복식" else 2):
            st.error("인원이 부족합니다.")
        else:
            if is_manual_mode:
                st.success("수동 입력 대진을 미리보기로 반영했어요.")
            else:
                sched = build_best_auto_schedule()
                st.session_state.today_schedule = sched
                if not sched:
                    st.warning("대진 생성에 실패했어요. 옵션을 완화하거나(코트/라운드/혼복/NTRP/조별) 인원을 확인해줘.")

    schedule = st.session_state.get("today_schedule", [])

    # =========================================================
    # ✅ 미리보기
    # =========================================================
    if schedule:
        st.markdown("### ✅ 오늘 대진표 미리보기")

        if view_mode_for_schedule == "조별 분리 (A/B조)":
            sched_A = [(gt, t1, t2, court) for (gt, t1, t2, court) in schedule if int(court) % 2 == 1]
            sched_B = [(gt, t1, t2, court) for (gt, t1, t2, court) in schedule if int(court) % 2 == 0]

            if sched_A:
                st.markdown("#### 🅰️ A조 (홀수 코트)")
                for i, (gt, t1, t2, court) in enumerate(sched_A, start=1):
                    t1_badges = "".join(render_name_badge(n, roster_by_name) for n in t1)
                    t2_badges = "".join(render_name_badge(n, roster_by_name) for n in t2)
                    st.markdown(
                        f"""
                        <div class="msa-game-row">
                          <div class="msa-game-meta">#{i} · 코트 {court} · {gt}</div>
                          <div class="msa-game-line">
                            <b>{t1_badges}</b> <span style="margin:0 6px;font-weight:800;">vs</span> <b>{t2_badges}</b>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            if sched_B:
                st.markdown("#### 🅱️ B조 (짝수 코트)")
                for i, (gt, t1, t2, court) in enumerate(sched_B, start=1):
                    t1_badges = "".join(render_name_badge(n, roster_by_name) for n in t1)
                    t2_badges = "".join(render_name_badge(n, roster_by_name) for n in t2)
                    st.markdown(
                        f"""
                        <div class="msa-game-row">
                          <div class="msa-game-meta">#{i} · 코트 {court} · {gt}</div>
                          <div class="msa-game-line">
                            <b>{t1_badges}</b> <span style="margin:0 6px;font-weight:800;">vs</span> <b>{t2_badges}</b>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            for i, (gt, t1, t2, court) in enumerate(schedule, start=1):
                t1_badges = "".join(render_name_badge(n, roster_by_name) for n in t1)
                t2_badges = "".join(render_name_badge(n, roster_by_name) for n in t2)
                st.markdown(
                    f"""
                    <div class="msa-game-row">
                      <div class="msa-game-meta">#{i} · 코트 {court} · {gt}</div>
                      <div class="msa-game-line">
                        <b>{t1_badges}</b> <span style="margin:0 6px;font-weight:800;">vs</span> <b>{t2_badges}</b>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("### 👤 인당 경기수")
        cnt = count_player_games(schedule)
        by_games = defaultdict(list)
        for p in players_selected:
            by_games[int(cnt.get(p, 0))].append(p)

        for gnum in sorted(by_games.keys()):
            names = by_games[gnum]
            badges = ", ".join(render_name_badge(n, roster_by_name) for n in sorted(names))
            st.markdown(f"**{gnum} :** {badges}", unsafe_allow_html=True)

    # 저장
    if save_clicked:
        if not schedule:
            st.warning("저장할 대진이 없습니다. 먼저 대진표를 생성해 주세요.")
        else:
            sessions = st.session_state.sessions
            day_data = sessions.get(save_date_str, {})

            if "results" not in day_data or not isinstance(day_data.get("results"), dict):
                day_data["results"] = {}

            groups_snapshot = {n: roster_by_name.get(n, {}).get("group", "미배정") for n in players_selected}

            day_data.update({
                "schedule": schedule,
                "court_type": st.session_state.get("today_court_type", COURT_TYPES[0]),
                "special_match": bool(st.session_state.get("special_match", False)),
                "groups_snapshot": groups_snapshot,
            })

            sessions[save_date_str] = day_data
            save_sessions(sessions)
            st.session_state.sessions = sessions
            st.success(f"{save_date_str} 대진이 저장됐어! (스페셜 매치: {'ON' if day_data['special_match'] else 'OFF'})")

# =========================================================
# 3) 경기 기록 / 통계 (날짜별)
# =========================================================

mobile_mode = st.session_state.get("mobile_mode", False)

with tab3:
    section_card("경기 기록 / 통계", "📊")

    if not sessions:
        st.info("저장된 경기 기록이 없습니다.")
    else:
        # 날짜 선택 (최근 날짜가 위로 오도록 정렬)
        all_keys = list(sessions.keys())

        # "전체" 키가 있을 수도 있으니 분리
        has_total = "전체" in all_keys
        date_keys = sorted(
            [d for d in all_keys if d != "전체"],
            reverse=True,           # 🔽 최근 날짜가 위로 오도록
        )

        if has_total:
            # "전체"를 맨 위에 두고, 그 다음부터 최근 날짜 순
            dates = ["전체"] + date_keys
            # 기본 선택은 가장 최근 날짜
            default_index = 1 if date_keys else 0
        else:
            dates = date_keys
            default_index = 0 if date_keys else 0

        sel_date = st.selectbox("날짜 선택", dates, index=default_index)


        day_data = sessions.get(sel_date, {})
        schedule = day_data.get("schedule", [])
        results = day_data.get("results", {})

        # 🔹 이 날짜의 스코어 보기/잠금 설정 읽기
        saved_view = day_data.get("score_view_mode")        # "전체" 또는 "조별 보기 (A/B조)" 또는 None
        lock_view = day_data.get("score_view_lock", False)  # True면 전체로 고정

        # 🏟 코트 종류 선택 (인조잔디 / 하드 / 클레이)
        default_court = day_data.get("court_type", COURT_TYPES[0])
        default_idx = get_index_or_default(COURT_TYPES, default_court, 0)

        new_court = st.radio(
            "코트 종류",
            COURT_TYPES,
            index=default_idx,
            horizontal=True,
        )

        # 변경되면 바로 sessions.json에 저장
        if new_court != default_court:
            day_data["court_type"] = new_court
            sessions[sel_date] = day_data
            st.session_state.sessions = sessions
            save_sessions(sessions)
            st.caption("🏟️ 코트 종류가 저장되었습니다.")

        # 날짜 전체일 때는 라디오 숨기고 자동 전체로
        if sel_date == "전체":
            view_mode_scores = "전체"
        else:
            # lock_view=True면 전체로 고정하고 라디오를 안 보여줌
            if lock_view:
                view_mode_scores = "전체"
            else:
                # ✅ 저장된 값이 없으면 기본은 "전체"
                saved_view = day_data.get("score_view_mode", "전체")

                default_view_index = 1 if saved_view == "전체" else 0  # ["조별", "전체"]에서 전체=1

                view_mode_scores = st.radio(
                    "표시 방식",
                    ["조별 보기 (A/B조)", "전체"],
                    horizontal=True,
                    key=f"tab3_view_mode_scores_{sel_date}",   # ✅ 날짜별 key로 분리
                    index=default_view_index,
                )

                # ✅ 선택값 저장(다음에 다시 들어와도 유지)
                if view_mode_scores != saved_view:
                    day_data["score_view_mode"] = view_mode_scores
                    sessions[sel_date] = day_data
                    st.session_state.sessions = sessions
                    save_sessions(sessions)



        # 나중에 다시 그리기 위한 요약 컨테이너
        summary_container = st.container()

        st.markdown("---")


        # -----------------------------
        # ✅ PC에서만 스코어 입력 줄바꿈 방지 CSS
        # -----------------------------
        if not mobile_mode:
            st.markdown("""
            <style>
            /* ✅ PC 라디오: 너무 빡센 'nowrap' 제거하고 간격 줄이기 */
            .stRadio [role="radiogroup"]{
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: wrap !important;          /* ✅ 핵심: 겹침 방지 */
                gap: 0.25rem 0.6rem !important;      /* ✅ 옵션 간 간격 축소 */
                align-items: center !important;
            }

            /* ✅ 라디오 동그라미와 텍스트 사이 간격 줄이기 */
            .stRadio label{
                gap: 0.25rem !important;
                padding-right: 0.1rem !important;
            }

            .stRadio label span{
                white-space: nowrap !important;
                font-size: 0.92rem !important;      /* ✅ 살짝만 줄여서 안정화 */
            }

            /* 너가 이미 쓰는 이름 배지 class */
            .name-badge{
                white-space: nowrap !important;
                display: inline-block !important;
            }

            .score-row *{
                white-space: nowrap !important;
            }
            </style>
            """, unsafe_allow_html=True)




        # -----------------------------
        # 2. 경기 스코어 입력 + 점수 잠금
        # -----------------------------



        # 복식 게임 포함 여부 체크 (단식이면 안내문 숨김)
        show_side_notice = any(
            len(t1) == 2 and len(t2) == 2
            for (gtype, t1, t2, court) in schedule
        )


        if show_side_notice:
            st.markdown(
                """
                <div style="
                    margin-top:-10px;
                    font-size:1rem;
                    font-weight:600;
                    color:#a155e9;
                    background:#feffb2;
                    padding:10px 14px;
                    border-radius:8px;
                    border:1px solid #a155e9;
                    display:inline-block;
                ">
                    🎾 포(듀스) 사이드에 있는 선수에게 체크해주세요!
                </div>
                """,
                unsafe_allow_html=True,
            )

        if schedule:
            score_options = SCORE_OPTIONS



            # ------------------------------
            # 게임을 A조 / B조 / 기타로 분류
            # ------------------------------
            games_A, games_B, games_other = [], [], []
            day_groups_snapshot = day_data.get("groups_snapshot")
            
            for idx, (gtype, t1, t2, court) in enumerate(schedule, start=1):
                all_players = list(t1) + list(t2)
            
                grp_flag = classify_game_group(
                    all_players,
                    roster_by_name,
                    day_groups_snapshot,
                )
            
                item = (idx, gtype, t1, t2, court)
            
                if grp_flag == "A":
                    games_A.append(item)
                elif grp_flag == "B":
                    games_B.append(item)
                else:
                    games_other.append(item)


            # ------------------------------
            # A/B조별 스코어 입력 블록
            # ------------------------------


            def render_score_inputs_block(title, game_list):
                """title: 'A조 경기 스코어', 'B조 경기 스코어' 등
                   if not game_list:
                       return
                   game_list: [(idx, gtype, t1, t2, court), ...]"""
                if not game_list:
                    return

                # 🔒 이 날짜의 잠금 상태
                locked = day_data.get("scores_locked", False)

                # 헤더 색상
                if ("A조" in title) or ("전체 경기 스코어" in title):
                    color = "#ec4899"   # 핑크
                    bg = "#fdf2f8"
                elif "B조" in title:
                    color = "#3b82f6"   # 파랑
                    bg = "#eff6ff"
                else:
                    color = "#6b7280"   # 회색
                    bg = "#f3f4f6"

                # 🔒 이 날짜의 잠금 상태
                lock_key = f"{sel_date}_scores_locked"
                locked = day_data.get("scores_locked", False)

                # -------------------------------------------------
                # ✅ 잠금 UI를 "이 날짜에서 딱 한 번만" 보여주기 위한 플래그
                #    - A조/전체가 없어도 첫 번째 블록에 잠금이 뜨게 됨
                # -------------------------------------------------
                lock_ui_flag = f"{sel_date}_lock_ui_rendered"
                if lock_ui_flag not in st.session_state:
                    st.session_state[lock_ui_flag] = False

                # ✅ 잠금 UI를 보여줄 조건
                # 1) A조 헤더일 때
                # 2) 전체 경기 스코어 헤더일 때
                # 3) 위 둘 다 아니어도, 아직 잠금 UI를 한 번도 안 보여줬다면
                should_show_lock = (
                    ("A조" in title)
                    or ("전체 경기 스코어" in title)
                    or (not st.session_state[lock_ui_flag])
                )

                # -------------------------------------------------
                # ✅ 헤더 렌더 + 잠금 UI
                # -------------------------------------------------
                if should_show_lock:
                    # 이 날짜에서 잠금 UI가 이미 한 번 렌더됐다고 기록
                    st.session_state[lock_ui_flag] = True

                    col_h, col_ck, col_txt = st.columns([8, 1.2, 1.8], vertical_alignment="center")

                    with col_h:
                        st.markdown(
                            f"""
                            <div style="
                                margin-top: 1.2rem;
                                padding: 0.5rem 0.8rem;
                                border-radius: 10px;
                                background-color: {bg};
                                border: 1px solid {color}33;
                            ">
                                <span style="font-weight:700; font-size:1.02rem; color:{color};">
                                    {title}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with col_ck:
                        scores_locked = st.checkbox(
                            "",
                            key=lock_key,
                            value=locked,
                            label_visibility="collapsed",
                            help="체크하면 이 날짜의 점수를 수정할 수 없습니다.",
                        )

                    with col_txt:
                        st.markdown(
                            "<div style='margin-top:6px; font-weight:600; font-size:0.9rem;'>🔒 잠금</div>",
                            unsafe_allow_html=True,
                        )

                    if scores_locked != locked:
                        day_data["scores_locked"] = scores_locked
                        sessions[sel_date] = day_data
                        st.session_state.sessions = sessions
                        save_sessions(sessions)

                    locked = scores_locked

                else:
                    # ✅ 잠금 UI 없이 헤더만 표시
                    st.markdown(
                        f"""
                        <div style="
                            margin-top: 1.2rem;
                            padding: 0.5rem 0.8rem;
                            border-radius: 10px;
                            background-color: {bg};
                            border: 1px solid {color}33;
                        ">
                            <span style="font-weight:700; font-size:1.02rem; color:{color};">
                                {title}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                # 배지 모양 이름 줄 (성별에 따라 배경색 다르게)
                def render_name_pills(players):
                    html_parts = []
                    for p in players:
                        info = roster_by_name.get(p, {}) or {}
                        g = info.get("gender")

                        if g == "남":
                            bg = "#dbeafe"   # 연한 파랑
                        elif g == "여":
                            bg = "#fee2e2"   # 연한 빨강
                        else:
                            bg = "#f3f4f6"   # 회색

                        html_parts.append(
                            f"<span class='name-badge' style='"
                            f"background:{bg};"
                            f"padding:3px 8px;"
                            f"border-radius:8px;"
                            f"margin-right:4px;"
                            f"font-weight:700;"
                            f"color:#111111;"
                            f"display:inline-block;"
                            f"white-space:nowrap;"
                            f"'>"
                            f"{p}"
                            f"</span>"
                        )
                    return "".join(html_parts)
                # 라디오 옵션에 붙일 성별 색상 라벨 (남 🔵 / 여 🔴)
                def gender_badge_label(name: str) -> str:
                    if name == "모름":
                        return "모름"

                    info = roster_by_name.get(name, {}) or {}
                    gender = info.get("gender") or info.get("성별")

                    if gender == "여":
                        return f"🔴 {name}"
                    elif gender == "남":
                        return f"🔵 {name}"
                    return name

                # ✅ 여기서 한 번 정의해줘야 해
                score_options_local = SCORE_OPTIONS

                # 실제 게임들
                for local_no, (idx, gtype, t1, t2, court) in enumerate(game_list, start=1):
                    st.markdown(
                        f"""
                        <div style="
                            margin-top:0.6rem;
                            padding-top:0.4rem;
                            border-top:1px solid #e5e7eb;
                            margin-bottom:0.18rem;
                        ">
                            <span style="font-weight:600; font-size:0.96rem;">
                                게임 {local_no}
                            </span>
                            <span style="font-size:0.82rem; color:#6b7280; margin-left:6px;">
                                ({gtype}{', 코트 ' + str(court) if court else ''})
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # 저장돼 있던 값
                    res = results.get(str(idx)) or results.get(idx) or {}
                    prev_s1 = res.get("t1", 0)
                    prev_s2 = res.get("t2", 0)

                    all_players = list(t1) + list(t2)


                    # 1) 복식(2:2) → 사이드는 항상 수정 가능, 점수만 잠금
                    # 1) 복식(2:2) → 사이드는 라디오, 점수는 잠금만 적용
                    if len(t1) == 2 and len(t2) == 2:
                        a, b = t1
                        c, d = t2

                        prev_sides = res.get("sides", {}) or {}

                        def normalize_side_label(label: str) -> str:
                            if label is None:
                                return "모름"
                            label = str(label)
                            if "모름" in label:
                                return "모름"
                            if "포" in label or "듀스" in label:
                                return "포(듀스)"
                            if "백" in label or "애드" in label:
                                return "백(애드)"
                            return label

                        # ---- 팀1 기본 선택값 ----
                        prev_a = normalize_side_label(prev_sides.get(a))
                        prev_b = normalize_side_label(prev_sides.get(b))
                        if prev_a == "포(듀스)":
                            default_t1 = a
                        elif prev_b == "포(듀스)":
                            default_t1 = b
                        else:
                            default_t1 = "모름"

                        # ---- 팀2 기본 선택값 ----
                        prev_c = normalize_side_label(prev_sides.get(c))
                        prev_d = normalize_side_label(prev_sides.get(d))
                        if prev_c == "포(듀스)":
                            default_t2 = c
                        elif prev_d == "포(듀스)":
                            default_t2 = d
                        else:
                            default_t2 = "모름"

                        t1_side_options = [a, b, "모름"]
                        t2_side_options = [c, d, "모름"]

                        idx_t1 = t1_side_options.index(default_t1)
                        idx_t2 = t2_side_options.index(default_t2)

                        # 🔹 레이아웃: [왼쪽 라디오] [팀1 점수] [VS] [팀2 점수] [오른쪽 라디오]
                        if mobile_mode:
                            col_t1_side, col_s1, col_vs, col_s2, col_t2_side = st.columns(
                                [2.7, 1.1, 0.7, 1.1, 2.7]
                            )
                        else:
                            # ✅ PC에서는 좌우를 확 넓혀서 이름이 절대 안 꺾이게
                            col_t1_side, col_s1, col_vs, col_s2, col_t2_side = st.columns(
                                [3.8, 0.9, 0.4, 0.9, 3.8]
                            )

                        # 왼쪽 팀 (유대한 / 배성균 / 모름)
                        with col_t1_side:
                            choice_t1 = st.radio(
                                "왼쪽 팀 포(듀스) 선수",
                                t1_side_options,
                                index=idx_t1,
                                key=f"{sel_date}_side_radio_{idx}_t1",
                                label_visibility="collapsed",
                                format_func=gender_badge_label,  # 🔵/🔴 표시
                                disabled=locked,
                            )

                        # 팀1 점수 (왼쪽 숫자)
                        with col_s1:
                            idx1 = get_index_or_default(score_options_local, prev_s1, 0)
                            s1 = st.selectbox(
                                "팀1 점수",
                                score_options_local,
                                index=idx1,
                                key=f"{sel_date}_s1_{idx}",
                                label_visibility="collapsed",
                                disabled=locked,   # 🔒 잠금
                            )

                        # 가운데 VS
                        with col_vs:
                            st.markdown(
                                """
                                <div style="
                                    text-align:center;
                                    font-weight:600;
                                    font-size:0.8rem;
                                    line-height:1;
                                    margin-top:6px;
                                ">VS</div>
                                """,
                                unsafe_allow_html=True,
                            )

                        # 팀2 점수 (오른쪽 숫자)
                        with col_s2:
                            idx2 = get_index_or_default(score_options_local, prev_s2, 0)
                            s2 = st.selectbox(
                                "팀2 점수",
                                score_options_local,
                                index=idx2,
                                key=f"{sel_date}_s2_{idx}",
                                label_visibility="collapsed",
                                disabled=locked,   # 🔒 잠금
                            )

                        # 오른쪽 팀 (박상희 / 김재호 / 모름)
                        with col_t2_side:
                            choice_t2 = st.radio(
                                "오른쪽 팀 포(듀스) 선수",
                                t2_side_options,
                                index=idx_t2,
                                key=f"{sel_date}_side_radio_{idx}_t2",
                                label_visibility="collapsed",
                                format_func=gender_badge_label,  # 🔵/🔴 표시
                                disabled=locked,
                            )

                        def sides_from_choice(choice, p1, p2):
                            if choice == "모름":
                                return {p1: "모름", p2: "모름"}
                            if choice == p1:
                                return {p1: "포(듀스)", p2: "백(애드)"}
                            return {p1: "백(애드)", p2: "포(듀스)"}

                        sides_left = sides_from_choice(choice_t1, a, b)
                        sides_right = sides_from_choice(choice_t2, c, d)
                        sides = {**sides_left, **sides_right}

                        results[str(idx)] = {"t1": s1, "t2": s2, "sides": sides}

                    # 2) 단식 / 기타
                    else:
                        st.markdown(
                            f"<div class='score-row' id='score-row-{sel_date}-{idx}'>",
                            unsafe_allow_html=True,
                        )
                        if mobile_mode:
                            cols = st.columns([3, 1, 0.7, 1, 3])
                        else:
                            cols = st.columns([4, 0.9, 0.4, 0.9, 4])


                        with cols[0]:
                            st.markdown(
                                render_name_pills(t1),
                                unsafe_allow_html=True,
                            )

                        with cols[1]:
                            idx1 = get_index_or_default(score_options_local, prev_s1, 0)
                            s1 = st.selectbox(
                                "팀1 점수",
                                score_options_local,
                                index=idx1,
                                key=f"{sel_date}_s1_{idx}",
                                label_visibility="collapsed",
                                disabled=locked,   # 🔒 잠금
                            )

                        with cols[2]:
                            st.markdown(
                                """
                                <div style="
                                    text-align:center;
                                    font-weight:600;
                                    font-size:0.8rem;
                                    line-height:1;
                                    margin-top:2px;
                                ">VS</div>
                                """,
                                unsafe_allow_html=True,
                            )

                        with cols[3]:
                            idx2 = get_index_or_default(score_options_local, prev_s2, 0)
                            s2 = st.selectbox(
                                "팀2 점수",
                                score_options_local,
                                index=idx2,
                                key=f"{sel_date}_s2_{idx}",
                                label_visibility="collapsed",
                                disabled=locked,   # 🔒 잠금
                            )

                        with cols[4]:
                            st.markdown(
                                "<div style='text-align:right;'>"
                                + render_name_pills(t2)
                                + "</div>",
                                unsafe_allow_html=True,
                            )

                        st.markdown("</div>", unsafe_allow_html=True)

                        sides = {p: None for p in all_players}
                        results[str(idx)] = {"t1": s1, "t2": s2, "sides": sides}

            # 레이아웃 처리
            has_AB_games = bool(games_A or games_B)

            # ✅ 레이아웃: A/B조를 절대 양옆 2컬럼으로 나누지 않음
            if view_mode_scores == "조별 보기 (A/B조)" and has_AB_games:
                render_score_inputs_block("A조 경기 스코어", games_A)
                render_score_inputs_block("B조 경기 스코어", games_B)
                if games_other:
                    render_score_inputs_block("기타 경기 스코어", games_other)

            else:
                all_games = games_A + games_B + games_other
                all_games = sorted(all_games, key=lambda x: x[0])  # ✅ idx 기준 정렬
                render_score_inputs_block("전체 경기 스코어", all_games)

            # 🔄 스코어 자동 저장
            day_data["results"] = results
            sessions[sel_date] = day_data
            st.session_state.sessions = sessions
            save_sessions(sessions)

            # -----------------------------
            # 3) 실수 방지 체크 (5:5 무승부는 제외)
            # -----------------------------


            warnings = detect_score_warnings(day_data)

            if warnings:
                st.markdown(
                    """
                    <div style="
                        margin:0.2rem 0 0.6rem 0;
                        padding:0.7rem 1.0rem;
                        border-radius:10px;
                        background:#fef2f2;
                        border:1px solid #fecaca;
                        font-size:0.9rem;
                        line-height:1.5;
                    ">
                        <b>⚠ 점수 입력을 한 번 더 확인해 주세요.</b><br/>
                        (5:5 무승부는 정상으로 간주하고, 그 외의 동점 점수만 표시합니다.)
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                for msg in warnings:
                    st.markdown(f"- {msg}")
            else:
                st.markdown(
                    """
                    <div style="
                        margin:0.2rem 0 0.6rem 0;
                        padding:0.7rem 1.0rem;
                        border-radius:10px;
                        background:#ecfdf5;
                        border:1px solid #6ee7b7;
                        font-size:0.9rem;
                        line-height:1.5;
                    ">
                        ✅ 입력된 점수에서 특별히 잘못 기입된 점수는 없습니다.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # =====================================================
            # 2. 오늘의 요약 리포트 (자동 생성)
            # =====================================================
            report_lines = build_daily_report(sel_date, day_data)

            st.markdown("---")

            if not report_lines:
                st.info("점수가 입력된 경기가 아직 없어서 요약 리포트를 만들 수 없습니다.")
            else:
                html_lines = "".join(f"<li>{line}</li>" for line in report_lines)
                st.markdown(
                    f"""
                    <div style="
                        margin-top:0.3rem;
                        padding:0.9rem 1.1rem;
                        border-radius:12px;
                        background:#eef2ff;
                        border:1px solid #c7d2fe;
                        font-size:0.9rem;
                        line-height:1.5;
                    ">
                        <div style="font-weight:700;font-size:0.98rem;margin-bottom:0.4rem;">
                            📋 {sel_date} 요약 리포트
                        </div>
                        <ul style="padding-left:1.1rem;margin:0;">
                            {html_lines}
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # -----------------------------
            # 4) 오늘 경기 전체 삭제
            # -----------------------------
            confirm_container = st.container()

            st.markdown('<div class="main-danger-btn">', unsafe_allow_html=True)
            # ✅ 이 날짜 잠금 여부
            locked = sessions.get(sel_date, {}).get("scores_locked", False)

            delete_start = st.button(
                "🗑 이 날짜의 경기 기록 전체 삭제",
                use_container_width=True,
                key="delete_start",
                disabled=locked,  # ✅ 잠금이면 삭제 시작 자체 불가
            )

            st.markdown("</div>", unsafe_allow_html=True)

            if delete_start:
                st.session_state.pending_delete = sel_date

            pending = st.session_state.get("pending_delete")

            with confirm_container:
                if pending == sel_date:

                    # ✅ 잠금이면 삭제 확인 UI 대신 안내만
                    if locked:
                        st.warning("잠금을 먼저 해제하세요.")
                        st.session_state.pending_delete = None

                    else:
                        st.markdown(
                            f"""
                            <div style="
                                color:#1f2933;
                                background:#fff9c4;
                                padding:16px 20px;
                                border-radius:12px;
                                font-size:1rem;
                                font-weight:500;
                                margin-bottom:5px;
                            ">
                                {sel_date} 날짜의 모든 경기 기록을 정말 삭제하시겠습니까?
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        col_ok, col_cancel = st.columns(2)

                        with col_ok:
                            st.markdown(
                                '<div class="main-danger-btn" style="margin-bottom:4px;">',
                                unsafe_allow_html=True,
                            )
                            yes_clicked = st.button(
                                "네, 삭제합니다",
                                use_container_width=True,
                                key="delete_yes",
                            )

                        with col_cancel:
                            st.markdown(
                                '<div class="main-danger-btn" style="margin-bottom:4px;">',
                                unsafe_allow_html=True,
                            )
                            cancel_clicked = st.button(
                                "취소",
                                use_container_width=True,
                                key="delete_cancel",
                            )

                        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

                        if yes_clicked:
                            # ✅ 안전망: 혹시 잠금이 그 사이 켜졌을 경우까지 방지
                            if sessions.get(sel_date, {}).get("scores_locked", False):
                                st.warning("잠금을 먼저 해제하세요.")
                            else:
                                sessions.pop(sel_date, None)
                                st.session_state.sessions = sessions
                                save_sessions(sessions)
                                st.session_state.pending_delete = None
                                st.success(
                                    "해당 날짜의 기록이 모두 삭제되었습니다. "
                                    "위의 날짜 선택 박스를 다시 확인해 주세요."
                                )

                        if cancel_clicked:
                            st.session_state.pending_delete = None
                            st.info("삭제를 취소했습니다.")


                st.markdown("<br>", unsafe_allow_html=True)

            # =====================================================
            # 1. 현재 스코어 요약 (표) - 최신 results 기준
            # =====================================================
            with summary_container:
                st.subheader("1. 현재 스코어 요약 (표)")

                if not schedule:
                    st.info("이 날짜에는 저장된 대진이 없습니다.")
                else:
                    summary_view_mode = st.radio(
                        "요약 보기 방식",
                        ["대진별 보기", "개인별 보기"],
                        horizontal=True,
                        key="tab3_summary_view_mode",
                    )

                    games_A_sum, games_B_sum, games_other_sum = [], [], []
                    day_groups_snapshot = day_data.get("groups_snapshot")

                    per_player_all = defaultdict(list)
                    per_player_A = defaultdict(list)
                    per_player_B = defaultdict(list)
                    per_player_other = defaultdict(list)

                    for idx, (gtype, t1, t2, court) in enumerate(schedule, start=1):
                        res = results.get(str(idx)) or results.get(idx) or {}
                        s1, s2 = res.get("t1"), res.get("t2")

                        row = {
                            "게임": idx,
                            "코트": court,
                            "타입": gtype,
                            "t1": t1,
                            "t2": t2,
                            "t1_score": s1,
                            "t2_score": s2,
                        }

                        all_players = t1 + t2
                        grp_flag = classify_game_group(
                            all_players,
                            roster_by_name,
                            day_groups_snapshot,
                        )

                        if grp_flag == "A":
                            games_A_sum.append(row)
                        elif grp_flag == "B":
                            games_B_sum.append(row)
                        else:
                            games_other_sum.append(row)

                        if s1 is None or s2 is None:
                            score_t1 = ""
                            score_t2 = ""
                        else:
                            score_t1 = f"{s1} : {s2}"
                            score_t2 = f"{s2} : {s1}"

                        for p in t1:
                            per_player_all[p].append(score_t1)
                        for p in t2:
                            per_player_all[p].append(score_t2)

                        target_dict = per_player_other
                        if grp_flag == "A":
                            target_dict = per_player_A
                        elif grp_flag == "B":
                            target_dict = per_player_B

                        for p in t1:
                            target_dict[p].append(score_t1)
                        for p in t2:
                            target_dict[p].append(score_t2)

                    if summary_view_mode == "대진별 보기":
                        if view_mode_scores == "조별 보기 (A/B조)":
                            if games_A_sum:
                                st.markdown("### A조 경기 요약")
                                render_score_summary_table(games_A_sum, roster_by_name)
                            if games_B_sum:
                                st.markdown("### B조 경기 요약")
                                render_score_summary_table(games_B_sum, roster_by_name)
                            if games_other_sum:
                                st.markdown("### 조가 섞인 경기 / 기타")
                                render_score_summary_table(games_other_sum, roster_by_name)
                        else:
                            all_games_sum = games_A_sum + games_B_sum + games_other_sum
                            render_score_summary_table(all_games_sum, roster_by_name)
                    else:
                        def render_player_score_table(title, per_dict):
                            if not per_dict:
                                return
                            st.markdown(f"### {title}")

                            players_sorted = sorted(per_dict.keys())
                            rows = []
                            for no, name in enumerate(players_sorted, start=1):
                                games_list = per_dict[name]
                                row = {
                                    "번호": no,
                                    "이름": name,
                                    "1게임": games_list[0] if len(games_list) >= 1 else "",
                                    "2게임": games_list[1] if len(games_list) >= 2 else "",
                                    "3게임": games_list[2] if len(games_list) >= 3 else "",
                                    "4게임": games_list[3] if len(games_list) >= 4 else "",
                                }
                                rows.append(row)

                            df_players = pd.DataFrame(rows)
                            df_players = df_players.set_index("번호")
                            df_players.index.name = ""

                            df_players.index.name = None
                            df_players.columns.name = None
                            def calc_wdl(values):
                                w = d = l = 0
                                for v in values:
                                    if not isinstance(v, str):
                                        continue
                                    s = v.replace(" ", "")
                                    if ":" not in s:
                                        continue
                                    left, right = s.split(":", 1)
                                    try:
                                        a = int(left)
                                        b = int(right)
                                    except ValueError:
                                        continue
                            
                                    if a > b:
                                        w += 1
                                    elif a == b:
                                        d += 1
                                    else:
                                        l += 1
                                return pd.Series([w, d, l], index=["승", "무", "패"])
                            
                            game_cols = ["1게임", "2게임", "3게임", "4게임"]
                            df_players[["승", "무", "패"]] = df_players[game_cols].apply(calc_wdl, axis=1)
                            
                            # (원하면 컬럼 순서 바꾸기: 이름 다음에 승무패 나오게)
                            df_players = df_players[["이름", "승", "무", "패"] + game_cols]



                            # 이긴 게임 / 진 게임 색
                            def highlight_win_loss(val):
                                if not isinstance(val, str):
                                    return ""
                                s = val.replace(" ", "")
                                if ":" not in s:
                                    return ""
                                left, right = s.split(":", 1)
                                try:
                                    a = int(left)
                                    b = int(right)
                                except ValueError:
                                    return ""

                                if a > b:
                                    return "background-color: #fef9c3;"  # 노랑
                                elif a < b:
                                    return "background-color: #e5e7eb;"  # 회색
                                else:
                                    return ""

                            game_cols = ["1게임", "2게임", "3게임", "4게임"]

                            sty_players = colorize_df_names(df_players, roster_by_name, ["이름"])
                            sty_players = sty_players.applymap(highlight_win_loss, subset=game_cols)
                            smart_table(sty_players)



                        if view_mode_scores == "조별 보기 (A/B조)":
                            has_any = False
                            if per_player_A:
                                render_player_score_table("A조 개인별 스코어", per_player_A)
                                has_any = True
                            if per_player_B:
                                render_player_score_table("B조 개인별 스코어", per_player_B)
                                has_any = True
                            if per_player_other:
                                render_player_score_table("조가 섞인 경기 / 기타 개인별 스코어", per_player_other)
                                has_any = True
                            if not has_any:
                                st.info("개인별로 표시할 스코어가 없습니다.")
                        else:
                            if not per_player_all:
                                st.info("개인별로 표시할 스코어가 없습니다.")
                            else:
                                render_player_score_table("전체 개인별 스코어", per_player_all)
        else:
            st.info("이 날짜에는 저장된 대진이 없습니다.")



# =========================================================
# 4) 개인별 통계
# =========================================================
with tab4:
    section_card("개인별 통계", "👤")

    if not sessions:
        st.info("저장된 기록이 없습니다.")
    else:
        names = [p["name"] for p in roster]
        # 🔤 이름 가나다 순 정렬
        names_sorted = sorted(names, key=lambda x: x)

        if not names_sorted:
            st.info("선수가 없습니다.")
        else:
            sel_player = st.selectbox("선수 선택", names_sorted, key="stat_player_select")

            # 🎾 오늘의 테니스 운세
            if sel_player:
                fortune_text = get_daily_fortune(sel_player)

                st.markdown(
                    f"""
                    <div style="
                        margin-top:0.5rem;
                        margin-bottom:1.0rem;
                        padding:0.7rem 1.0rem;
                        border-radius:10px;
                        background-color:#fff7c2;
                        border:1px solid #ffd84d;
                    ">
                        <div style="font-weight:700; font-size:1.05rem; margin-bottom:0.25rem;">
                            🍀 오늘의 테니스 운세
                        </div>
                        <div style="font-size:0.99rem;">
                            {fortune_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # -------------------------------
            # 기간 선택
            # -------------------------------
            range_mode = st.radio("기간 선택", ["전체 시즌", "월별"], horizontal=True)
            month_key = None
            if range_mode == "월별":
                months = sorted({d[:7] for d in sessions.keys()})
                if months:
                    sel_month = st.selectbox(
                        "월 선택 (YYYY-MM)",
                        months,
                        index=len(months) - 1,
                        key="player_stats_month_select",
                    )
                    month_key = sel_month

            # -------------------------------
            # 통계 누적용 변수
            # -------------------------------
            rec = {
                "G": 0, "W": 0, "D": 0, "L": 0, "points": 0,
                "score_for": 0, "score_against": 0
            }

            # ✅ 이 선수가 경기를 한 날짜(점수 있는 경기 기준)
            player_days = set()

            vs_opponent = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            with_partner = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_court_type = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_side = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_racket = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_ntrp = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_gender = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_hand = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_mbti = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})

            # -------------------------------
            # 경기 순회
            # -------------------------------
            for d, idx, g in iter_games(sessions, include_special=False):
                if month_key and not d.startswith(month_key):
                    continue

                t1, t2 = g["t1"], g["t2"]
                s1, s2 = g["score1"], g["score2"]
                r = calc_result(s1, s2)
                if r is None:
                    continue

                in_t1 = sel_player in t1
                in_t2 = sel_player in t2
                if not (in_t1 or in_t2):
                    continue

                # ✅ 점수 있는 경기에서만 '출석일'로 카운트
                player_days.add(d)

                rec["G"] += 1
                if in_t1:
                    my_score, opp_score = s1, s2
                else:
                    my_score, opp_score = s2, s1

                rec["score_for"] += my_score if my_score is not None else 0
                rec["score_against"] += opp_score if opp_score is not None else 0

                # 결과(내 기준)
                if (in_t1 and r == "W") or (in_t2 and r == "L"):
                    rec["W"] += 1
                    rec["points"] += WIN_POINT
                    res_self = "W"
                elif (in_t1 and r == "L") or (in_t2 and r == "W"):
                    rec["L"] += 1
                    rec["points"] += LOSE_POINT
                    res_self = "L"
                else:
                    rec["D"] += 1
                    rec["points"] += DRAW_POINT
                    res_self = "D"

                # 코트 타입별
                court_type = g.get("court_type", "모름")
                by_court_type[court_type]["G"] += 1
                by_court_type[court_type][res_self] += 1

                # 코트 사이드(포/백) 통계
                sides = g.get("sides", {})
                side_raw = sides.get(sel_player)

                if side_raw:
                    s = str(side_raw)

                    # 모름이면 통계에서 제외
                    if "모름" in s:
                        pass
                    else:
                        if ("포" in s) or ("듀스" in s):
                            side_key = "포(듀스)"
                        elif ("백" in s) or ("애드" in s):
                            side_key = "백(애드)"
                        else:
                            side_key = s

                        by_side[side_key]["G"] += 1
                        by_side[side_key][res_self] += 1

                # 파트너/상대
                if in_t1:
                    partners = [x for x in t1 if x != sel_player]
                    opponents = t2
                else:
                    partners = [x for x in t2 if x != sel_player]
                    opponents = t1

                for op in opponents:
                    vs_opponent[op]["G"] += 1
                    vs_opponent[op][res_self] += 1
                for pt in partners:
                    with_partner[pt]["G"] += 1
                    with_partner[pt][res_self] += 1

                # 상대의 메타(라켓/NTRP/성별/주손/MBTI)로 분류
                for person in opponents:
                    m = roster_by_name.get(person, {})

                    # 라켓: "모름" 은 통계에서 제외
                    racket = m.get("racket", "모름")
                    if racket != "모름":
                        by_racket[racket]["G"] += 1
                        by_racket[racket][res_self] += 1

                    # NTRP: "모름" 은 통계에서 제외
                    ntrp_str = m.get("ntrp", "모름")
                    if ntrp_str != "모름":
                        ntrp_val = get_ntrp_value(m)
                        ntrp_key = f"{ntrp_val:.1f}"
                        by_ntrp[ntrp_key]["G"] += 1
                        by_ntrp[ntrp_key][res_self] += 1

                    # 성별 / 주손은 그대로 집계
                    gender = m.get("gender", "남")
                    by_gender[gender]["G"] += 1
                    by_gender[gender][res_self] += 1

                    hand = m.get("hand", "오른손")
                    by_hand[hand]["G"] += 1
                    by_hand[hand][res_self] += 1

                    # MBTI: 빈 값 / "모름" 은 통계에서 제외
                    mbti = (m.get("mbti", "") or "").strip().upper()
                    if mbti and mbti not in ("모름",):
                        by_mbti[mbti]["G"] += 1
                        by_mbti[mbti][res_self] += 1

            # -------------------------------
            # 요약 출력
            # -------------------------------
            st.subheader(f"{sel_player} 요약 ({'전체' if not month_key else month_key})")
            if rec["G"] == 0:
                st.info("해당 기간에 경기 기록이 없습니다.")
            else:
                win_rate = rec["W"] / rec["G"] * 100
                avg_for = rec["score_for"] / rec["G"]
                avg_against = rec["score_against"] / rec["G"]

                st.write(f"- 경기수: {rec['G']}")
                st.write(f"- 승 / 무 / 패: {rec['W']} / {rec['D']} / {rec['L']}")
                st.write(f"- 승률: {win_rate:.1f}%")
                st.write(f"- 점수(승=3, 무=1, 패=0): {rec['points']}")
                st.write(f"- 평균 득점: {avg_for:.2f} 점")
                st.write(f"- 평균 실점: {avg_against:.2f} 점")

                # ✅ 하루 평균 승/무/패
                days_cnt = len(player_days)
                if days_cnt > 0:
                    avg_w = rec["W"] / days_cnt
                    avg_d = rec["D"] / days_cnt
                    avg_l = rec["L"] / days_cnt
                    st.write(
                        f"- 하루 평균 승/무/패: {avg_w:.1f}승 / {avg_d:.1f}무 / {avg_l:.1f}패 (총 {days_cnt}일 기준)"
                    )

            st.markdown("---")
            cL, cR = st.columns(2)

            # -------------------------------
            # 좌측: 상대/파트너
            # -------------------------------
            with cL:
                st.markdown("상대별 승률")
                if vs_opponent:
                    rows = []
                    for name, r in vs_opponent.items():
                        if r["G"] == 0:
                            continue
                        win_rate = r["W"] / r["G"] * 100
                        rows.append(
                            {
                                "상대": name,
                                "경기수": r["G"],
                                "승": r["W"],
                                "무": r["D"],
                                "패": r["L"],
                                "승률": win_rate,
                            }
                        )
                    if rows:
                        df_vs = pd.DataFrame(rows).sort_values(
                            ["승률", "경기수"], ascending=False
                        ).reset_index(drop=True)

                        df_vs.index = df_vs.index + 1
                        df_vs.index.name = "순위"

                        sty_vs = colorize_df_names(df_vs, roster_by_name, ["상대"])
                        sty_vs = sty_vs.format({"승률": "{:.1f}%"})
                        st.dataframe(sty_vs, use_container_width=True)
                    else:
                        st.info("상대 기록이 없습니다.")
                else:
                    st.info("상대 기록이 없습니다.")

                st.markdown("파트너별 승률")
                if with_partner:
                    rows = []
                    for name, r in with_partner.items():
                        if r["G"] == 0:
                            continue
                        win_rate = r["W"] / r["G"] * 100
                        rows.append(
                            {
                                "파트너": name,
                                "경기수": r["G"],
                                "승": r["W"],
                                "무": r["D"],
                                "패": r["L"],
                                "승률": win_rate,
                            }
                        )
                    if rows:
                        df_pt = pd.DataFrame(rows).sort_values(
                            ["승률", "경기수"], ascending=False
                        ).reset_index(drop=True)

                        df_pt.index = df_pt.index + 1
                        df_pt.index.name = "순위"

                        sty_pt = colorize_df_names(df_pt, roster_by_name, ["파트너"])
                        sty_pt = sty_pt.format({"승률": "{:.1f}%"})
                        st.dataframe(sty_pt, use_container_width=True)
                    else:
                        st.info("파트너 기록이 없습니다.")
                else:
                    st.info("파트너 기록이 없습니다.")

            # -------------------------------
            # 우측: 그룹별 통계
            # -------------------------------
            with cR:
                def make_group_df(title, data_dict, label):
                    st.markdown(title)
                    if not data_dict:
                        st.info("데이터 없음")
                        return

                    rows = []
                    for k, r in data_dict.items():
                        if r["G"] == 0:
                            continue

                        # ✔ 통계에서 제외할 값 필터
                        if label == "연령대" and k == "비밀":
                            continue
                        if label == "라켓" and k == "모름":
                            continue
                        if label == "실력조" and k == "미배정":
                            continue
                        if label == "NTRP" and k in ("모름", "0.0"):
                            continue
                        if label == "사이드" and k == "모름":
                            continue
                        if label == "MBTI" and k in ("", "모름"):
                            continue

                        rows.append(
                            {
                                label: k,
                                "경기수": r["G"],
                                "승": r["W"],
                                "무": r["D"],
                                "패": r["L"],
                                "승률": r["W"] / r["G"] * 100,
                            }
                        )

                    if not rows:
                        st.info("데이터 없음")
                        return

                    df_g = pd.DataFrame(rows).sort_values(
                        ["승률", "경기수"], ascending=False
                    ).reset_index(drop=True)

                    df_g.index = df_g.index + 1
                    df_g.index.name = "순위"

                    df_g["승률"] = df_g["승률"].map(lambda x: f"{x:.1f}%")
                    st.dataframe(df_g, use_container_width=True)

                make_group_df("코트 타입별 승률", by_court_type, "코트")
                make_group_df("코트 사이드(듀스/애드)별 승률", by_side, "사이드")
                make_group_df("라켓별 상대 승률", by_racket, "라켓")
                make_group_df("NTRP별 상대 승률", by_ntrp, "NTRP")
                make_group_df("성별별 상대 승률", by_gender, "성별")
                make_group_df("주손별 상대 승률", by_hand, "주손")
                make_group_df("MBTI별 상대 승률", by_mbti, "MBTI")

# =========================================================
# 5) 월별 통계
# =========================================================
with tab5:
    section_card("월별 통계", "📆")

    if not sessions:
        st.info("저장된 기록이 없습니다.")
    else:
        # ---------------------------------------------------------
        # 0) 월 선택
        # ---------------------------------------------------------
        months = sorted({d[:7] for d in sessions.keys() if d != "전체"})
        if not months:
            st.info("월별로 표시할 기록이 없습니다.")
        else:
            sel_month = st.selectbox("월 선택 (YYYY-MM)", months, index=len(months) - 1)

            # ---------------------------------------------------------
            # 1) 이 달의 게임 모으기 (스페셜 매치 제외)
            # ---------------------------------------------------------
            month_games = []
            for d, idx, g in iter_games(sessions, include_special=False):
                if not d.startswith(sel_month):
                    continue
                month_games.append((d, idx, g))

            if not month_games:
                st.info("이 달에 경기 기록이 없습니다.")
            else:
                # =========================================================
                # 1. 월간 선수 순위표
                # =========================================================
                st.subheader("1. 월간 선수 순위표")

                rank_view_mode = st.radio(
                    "순위표 보기 방식",
                    ["전체", "조별 보기 (A/B조)"],
                    horizontal=True,
                    key="month_rank_view_mode",
                )

                # ---------------------------------------------------------
                # ✅ 집계는 '항상 전체 기준'으로 1번만 만든다
                #    - 출석일수/경기수: 점수 없어도(결과 None) 참여하면 카운트
                #    - 승/무/패/점수/득실: 점수가 있을 때만 반영
                # ---------------------------------------------------------
                def make_recs():
                    return defaultdict(
                        lambda: {
                            "days": set(),          # 출석 날짜들
                            "G": 0,                 # 참여 경기수(점수 없어도 포함)
                            "W": 0,
                            "D": 0,
                            "L": 0,
                            "points": 0,
                            "score_for": 0,
                            "score_against": 0,
                        }
                    )

                recs_all = make_recs()
                partners_by_player = defaultdict(set)

                def update_recs(target_recs, d, t1, t2, s1, s2, r):
                    players_all = t1 + t2

                    # 1) 출석/경기수(참여) — 점수 없어도 카운트
                    for p in players_all:
                        if is_guest_name(p, roster):
                            continue
                        target_recs[p]["days"].add(d)
                        target_recs[p]["G"] += 1

                    # 2) 점수 없으면 여기서 종료 (승/무/패/득실은 미반영)
                    if r is None:
                        return

                    # 3) 득/실 (점수 있을 때만)
                    s1_val = s1 if (s1 is not None) else 0
                    s2_val = s2 if (s2 is not None) else 0

                    for p in t1:
                        if is_guest_name(p, roster):
                            continue
                        target_recs[p]["score_for"] += s1_val
                        target_recs[p]["score_against"] += s2_val

                    for p in t2:
                        if is_guest_name(p, roster):
                            continue
                        target_recs[p]["score_for"] += s2_val
                        target_recs[p]["score_against"] += s1_val

                    # 4) 승/무/패 + 점수
                    if r == "W":
                        for p in t1:
                            if is_guest_name(p, roster):
                                continue
                            target_recs[p]["W"] += 1
                            target_recs[p]["points"] += WIN_POINT
                        for p in t2:
                            if is_guest_name(p, roster):
                                continue
                            target_recs[p]["L"] += 1
                            target_recs[p]["points"] += LOSE_POINT

                    elif r == "L":
                        for p in t1:
                            if is_guest_name(p, roster):
                                continue
                            target_recs[p]["L"] += 1
                            target_recs[p]["points"] += LOSE_POINT
                        for p in t2:
                            if is_guest_name(p, roster):
                                continue
                            target_recs[p]["W"] += 1
                            target_recs[p]["points"] += WIN_POINT

                    else:  # "D"
                        for p in players_all:
                            if is_guest_name(p, roster):
                                continue
                            target_recs[p]["D"] += 1
                            target_recs[p]["points"] += DRAW_POINT

                # ---------------------------------------------------------
                # 1-1) 월간 데이터 집계 (전체 기준 1회)
                # ---------------------------------------------------------
                for d, idx, g in month_games:
                    t1, t2 = g["t1"], g["t2"]
                    s1, s2 = g["score1"], g["score2"]
                    r = calc_result(s1, s2)  # 점수 없으면 None

                    # 전체 기록(참여는 항상, 결과는 점수 있을 때만)
                    update_recs(recs_all, d, t1, t2, s1, s2, r)

                    # 🤝 파트너 집계 (점수 없어도 복식이면 파트너는 만난 걸로)
                    for team in (t1, t2):
                        if len(team) >= 2:
                            for i, p in enumerate(team):
                                if is_guest_name(p, roster):
                                    continue
                                for j, q in enumerate(team):
                                    if i == j:
                                        continue
                                    partners_by_player[p].add(guest_bucket(q, roster))

                # ---------------------------------------------------------
                # ✅ "조별 보기"는 선수만 A/B로 분리 (집계는 동일 recs_all)
                #    - 그 달에 groups_snapshot이 있으면 그걸 우선 참고
                #    - 없으면 roster_by_name의 group 사용
                # ---------------------------------------------------------
                def normalize_group(g):
                    if not g:
                        return None
                    if g in ("A", "A조", "A조 ", "A group"):
                        return "A"
                    if g in ("B", "B조", "B조 ", "B group"):
                        return "B"
                    if g == "A조":
                        return "A"
                    if g == "B조":
                        return "B"
                    # roster에 "A조"/"B조"로 들어있는 경우
                    if "A" in str(g) and "조" in str(g):
                        return "A"
                    if "B" in str(g) and "조" in str(g):
                        return "B"
                    return None

                # 선수별 월 그룹 결정(해당 월 출석일들의 snapshot/roster를 보고 다수결)
                player_month_group = {}
                for name, rr in recs_all.items():
                    if is_guest_name(name, roster):
                        continue
                    if rr["G"] == 0:
                        continue

                    cnt = Counter()
                    for d in rr["days"]:
                        snap = sessions.get(d, {}).get("groups_snapshot") or {}
                        g = snap.get(name)
                        if not g:
                            g = roster_by_name.get(name, {}).get("group")
                        ng = normalize_group(g)
                        if ng in ("A", "B"):
                            cnt[ng] += 1

                    if cnt:
                        player_month_group[name] = cnt.most_common(1)[0][0]
                    else:
                        # 마지막 fallback: roster 기준
                        g = roster_by_name.get(name, {}).get("group")
                        player_month_group[name] = normalize_group(g)

                # ---------------------------------------------------------
                # 1-2) 순위표 DF 생성 (전체 집계 recs_all을 그대로 사용)
                #     - 승률은 '점수 입력된 경기(W+D+L)' 기준으로 계산
                # ---------------------------------------------------------
                def build_rank_df(recs_dict, allowed_names=None):
                    rows = []
                    for name, r in recs_dict.items():
                        if r["G"] == 0:
                            continue
                        if is_guest_name(name, roster):
                            continue
                        if allowed_names is not None and name not in allowed_names:
                            continue

                        decided = r["W"] + r["D"] + r["L"]  # 점수 입력된 경기수
                        win_rate = (r["W"] / decided * 100) if decided > 0 else 0.0

                        rows.append(
                            {
                                "이름": name,
                                "출석일수": len(r["days"]),
                                "경기수": r["G"],
                                "승": r["W"],
                                "무": r["D"],
                                "패": r["L"],
                                "점수": r["points"],
                                "승률": win_rate,
                            }
                        )
                    if not rows:
                        return None

                    df = (
                        pd.DataFrame(rows)
                        .sort_values(["점수", "승률"], ascending=False)
                        .reset_index(drop=True)
                    )
                    df.index = df.index + 1
                    df.index.name = "순위"
                    df["승률"] = df["승률"].map(lambda x: f"{x:.1f}%")
                    return df

                # ---------------------------------------------------------
                # 1-3) 순위표 출력
                # ---------------------------------------------------------
                if rank_view_mode == "전체":
                    rank_df = build_rank_df(recs_all)
                    if rank_df is None:
                        st.info("표시할 데이터가 없습니다.")
                    else:
                        sty_rank = colorize_df_names(rank_df, roster_by_name, ["이름"])
                        st.dataframe(sty_rank, use_container_width=True)

                else:
                    # ✅ 조별보기: 집계는 동일(recs_all), 선수만 A/B로 나누기
                    names_A = sorted([n for n, g in player_month_group.items() if g == "A"])
                    names_B = sorted([n for n, g in player_month_group.items() if g == "B"])

                    rank_df_A = build_rank_df(recs_all, allowed_names=set(names_A))
                    rank_df_B = build_rank_df(recs_all, allowed_names=set(names_B))

                    has_any = False
                    if rank_df_A is not None:
                        has_any = True
                        st.markdown("### 🟥 A조 월간 선수 순위표")
                        sty_A = colorize_df_names(rank_df_A, roster_by_name, ["이름"])
                        st.dataframe(sty_A, use_container_width=True)

                    if rank_df_B is not None:
                        has_any = True
                        st.markdown("### 🟦 B조 월간 선수 순위표")
                        sty_B = colorize_df_names(rank_df_B, roster_by_name, ["이름"])
                        st.dataframe(sty_B, use_container_width=True)

                    if not has_any:
                        st.info("A조 / B조로 나눠서 표시할 데이터가 없습니다.")

                # =========================================================
                # 2. 월 전체 경기 요약 (일별)
                # =========================================================
                st.subheader("2. 월 전체 경기 요약 (일별)")

                days_sorted = sorted({d for d, idx, g in month_games})
                for d in days_sorted:
                    st.markdown("<hr style='margin: 0.6rem 0 0.9rem 0;'>", unsafe_allow_html=True)
                    st.markdown(f"**📅 {d}**")

                    rows_all = []
                    rows_A, rows_B, rows_other = [], [], []

                    for d2, idx, g in month_games:
                        if d2 != d:
                            continue

                        row = {
                            "게임": idx,
                            "코트": g["court"],
                            "타입": g["type"],
                            "t1": g["t1"],
                            "t2": g["t2"],
                            "t1_score": g["score1"],
                            "t2_score": g["score2"],
                        }
                        rows_all.append(row)

                        all_players = g["t1"] + g["t2"]
                        day_groups_snapshot = sessions.get(d2, {}).get("groups_snapshot")
                        grp_flag = classify_game_group(
                            all_players,
                            roster_by_name,
                            day_groups_snapshot,
                        )

                        if grp_flag == "A":
                            rows_A.append(row)
                        elif grp_flag == "B":
                            rows_B.append(row)
                        else:
                            rows_other.append(row)

                    if rows_A and rows_B:
                        if rows_A:
                            st.markdown("#### 🟥 A조 경기 요약")
                            render_score_summary_table(rows_A, roster_by_name)
                        if rows_B:
                            st.markdown("#### 🟦 B조 경기 요약")
                            render_score_summary_table(rows_B, roster_by_name)
                        if rows_other:
                            st.markdown("#### ⚪ 조가 섞인 경기 / 기타")
                            render_score_summary_table(rows_other, roster_by_name)
                    else:
                        render_score_summary_table(rows_all, roster_by_name)

                # =========================================================
                # 3. 이 달의 BEST
                # =========================================================
                st.subheader("3. 이 달의 BEST (주손/라켓/연령대/성별)")

                # 👉 BEST 계산은 전체 집계 기준 유지
                recs = recs_all

                def best_by_category(label, key_func, exclude_values=None):
                    if exclude_values is None:
                        exclude_values = set()

                    stats = defaultdict(lambda: {"G": 0, "W": 0})

                    for d, idx, g in month_games:
                        t1, t2 = g["t1"], g["t2"]
                        s1, s2 = g["score1"], g["score2"]
                        r = calc_result(s1, s2)
                        if r is None:
                            continue

                        players_all = t1 + t2

                        for p in players_all:
                            if is_guest_name(p, roster):
                                continue
                            meta = roster_by_name.get(p, {})
                            grp = key_func(meta)
                            if grp in exclude_values:
                                continue
                            stats[grp]["G"] += 1

                        winners = t1 if r == "W" else (t2 if r == "L" else [])
                        for p in winners:
                            if is_guest_name(p, roster):
                                continue
                            meta = roster_by_name.get(p, {})
                            grp = key_func(meta)
                            if grp in exclude_values:
                                continue
                            stats[grp]["W"] += 1

                    best_grps = []
                    best_rate = -1.0

                    for grp, v in stats.items():
                        if v["G"] < 3:
                            continue
                        rate = v["W"] / v["G"]
                        if rate > best_rate:
                            best_rate = rate
                            best_grps = [grp]
                        elif rate == best_rate:
                            best_grps.append(grp)

                    if not best_grps:
                        return "데이터 부족"

                    grp_text = ", ".join(best_grps)
                    games = stats[best_grps[0]]["G"]
                    return f"{grp_text} (승률 {best_rate*100:.1f}%, 경기수 {games})"

                best_hand = best_by_category("주손", lambda m: m.get("hand", "오른손"))
                best_racket = best_by_category("라켓", lambda m: m.get("racket", "모름"))
                best_age = best_by_category("연령대", lambda m: m.get("age_group", "비밀"))
                best_gender = best_by_category("성별", lambda m: m.get("gender", "남"))
                best_mbti = best_by_category("MBTI", lambda m: m.get("mbti", "모름"), exclude_values={"모름"})

                # 🎯 노자비왕(득-실) — 점수 입력된 경기 기준으로 평균
                diff_stats = []
                for name, r in recs.items():
                    if is_guest_name(name, roster):
                        continue
                    decided = r["W"] + r["D"] + r["L"]
                    if decided == 0:
                        continue
                    avg_for = r["score_for"] / decided
                    avg_against = r["score_against"] / decided
                    diff = avg_for - avg_against
                    diff_stats.append({"name": name, "avg_for": avg_for, "avg_against": avg_against, "diff": diff})

                if diff_stats:
                    best_diff_value = max(x["diff"] for x in diff_stats)
                    winners = [x for x in diff_stats if x["diff"] == best_diff_value]
                    if len(winners) == 1:
                        w = winners[0]
                        diff_line = (
                            f"{w['name']} (평균 득점 {w['avg_for']:.2f}, "
                            f"평균 실점 {w['avg_against']:.2f}, 격차 {w['diff']:.2f})"
                        )
                    else:
                        names = ", ".join(w["name"] for w in winners)
                        diff_line = f"{names} (공동 노자비왕 · 최대 격차 {best_diff_value:.2f})"
                else:
                    diff_line = "데이터 부족"

                # 🤝 파트너왕 (공동우승 허용)
                partner_counts = []
                for name, partner_set in partners_by_player.items():
                    if is_guest_name(name, roster):
                        continue
                    partner_counts.append((name, len(partner_set)))

                if partner_counts:
                    most_partner_count = max(cnt for _, cnt in partner_counts)
                    winners = [name for name, cnt in partner_counts if cnt == most_partner_count]
                    if most_partner_count > 0:
                        names = ", ".join(winners)
                        partner_line = (
                            f"{names} (공동 파트너왕 · 만난 파트너 수 {most_partner_count}명)"
                            if len(winners) > 1
                            else f"{names} (만난 파트너 수 {most_partner_count}명)"
                        )
                    else:
                        partner_line = "데이터 부족 (복식 경기 없음)"
                else:
                    partner_line = "데이터 부족 (복식 경기 없음)"

                # 👑 출석왕 — recs(순위표)와 동일 기준(출석 날짜 set)
                attendance_count = {p: len(r["days"]) for p, r in recs.items() if r["G"] > 0 and not is_guest_name(p, roster)}
                if attendance_count:
                    max_days = max(attendance_count.values())
                    att_winners = [p for p, v in attendance_count.items() if v == max_days]
                    attendance_line = (
                        f"{', '.join(att_winners)} (참석 {max_days}일)"
                        if len(att_winners) > 1
                        else f"{att_winners[0]} (참석 {max_days}일)"
                    )
                else:
                    attendance_line = "데이터 부족"

                # 🔥 연승왕 – 점수 있는 경기만으로 계산
                streak_now = defaultdict(int)
                streak_best = defaultdict(int)

                for d, idx, g in sorted(month_games, key=lambda x: (x[0], x[1])):
                    t1, t2 = g["t1"], g["t2"]
                    s1, s2 = g["score1"], g["score2"]
                    r = calc_result(s1, s2)
                    if r is None:
                        continue

                    if r == "D":
                        for p in t1 + t2:
                            if is_guest_name(p, roster):
                                continue
                            streak_best[p] = max(streak_best[p], streak_now[p])
                            streak_now[p] = 0
                        continue

                    winners, losers = (t1, t2) if r == "W" else (t2, t1)

                    for p in winners:
                        if is_guest_name(p, roster):
                            continue
                        streak_now[p] += 1
                        streak_best[p] = max(streak_best[p], streak_now[p])

                    for p in losers:
                        if is_guest_name(p, roster):
                            continue
                        streak_best[p] = max(streak_best[p], streak_now[p])
                        streak_now[p] = 0

                for p, cur in streak_now.items():
                    if is_guest_name(p, roster):
                        continue
                    streak_best[p] = max(streak_best[p], cur)

                streak_line = "데이터 부족"
                if streak_best:
                    max_streak = max(streak_best.values())
                    if max_streak >= 2:
                        winners_streak = sorted([p for p, v in streak_best.items() if v == max_streak])
                        streak_line = f"{', '.join(winners_streak)} (최대 {max_streak}연승)"

                # 🥖 제빵왕 – 상대 0점 만든 경기 수 (점수 있는 경기만)
                baker_counter = Counter()
                for d, idx, g in month_games:
                    t1, t2 = g["t1"], g["t2"]
                    s1, s2 = g["score1"], g["score2"]
                    if s1 is None or s2 is None:
                        continue
                    if s1 > 0 and s2 == 0:
                        for p in t1:
                            if not is_guest_name(p, roster):
                                baker_counter[p] += 1
                    elif s2 > 0 and s1 == 0:
                        for p in t2:
                            if not is_guest_name(p, roster):
                                baker_counter[p] += 1

                if baker_counter:
                    max_cnt = max(baker_counter.values())
                    winners = [p for p, c in baker_counter.items() if c == max_cnt]
                    baker_line = (
                        f"{', '.join(winners)} (상대를 0점으로 이긴 경기 {max_cnt}번)"
                        if max_cnt > 0
                        else "데이터 부족"
                    )
                else:
                    baker_line = "데이터 부족"

                # --------------------------------
                # 3-3) 카드 UI 출력
                # --------------------------------
                st.markdown(
                    f"""
                    <div style="
                        margin-top:0.4rem;
                        padding:0.9rem 1.1rem;
                        border-radius:12px;
                        background:#f9fafb;
                        border:1px solid #e5e7eb;
                        margin-bottom:0.7rem;
                    ">
                        <div style="font-weight:700;font-size:0.98rem;margin-bottom:0.4rem;">
                            📊 카테고리별 BEST
                        </div>
                        <ul style="padding-left:1.1rem;margin:0;font-size:0.9rem;">
                            <li>주손&nbsp;:&nbsp;{best_hand}</li>
                            <li>라켓&nbsp;:&nbsp;{best_racket}</li>
                            <li>연령대&nbsp;:&nbsp;{best_age}</li>
                            <li>성별&nbsp;:&nbsp;{best_gender}</li>
                            <li>MBTI&nbsp;:&nbsp;{best_mbti}</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f"""
                    <div style="
                        margin-top:0.1rem;
                        padding:0.9rem 1.1rem;
                        border-radius:12px;
                        background:#fefce8;
                        border:1px solid #facc15;
                    ">
                        <div style="font-weight:700;font-size:0.98rem;margin-bottom:0.4rem;">
                            🏅 선수별 BEST
                        </div>
                        <ul style="padding-left:1.1rem;margin:0;font-size:0.9rem;">
                            <li>🎯 격차왕&nbsp;:&nbsp;{diff_line}</li>
                            <li>🤝 우정왕&nbsp;:&nbsp;{partner_line}</li>
                            <li>👑 출석왕&nbsp;:&nbsp;{attendance_line}</li>
                            <li>🔥 연승왕&nbsp;:&nbsp;{streak_line}</li>
                            <li>🥖 제빵왕&nbsp;:&nbsp;{baker_line}</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
