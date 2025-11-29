# -*- coding: utf-8 -*-
import json
import os
import random
from datetime import date
from collections import defaultdict

import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# 기본 상수
# ---------------------------------------------------------
PLAYERS_FILE = "players.json"
SESSIONS_FILE = "sessions.json"

AGE_OPTIONS = ["비밀", "10대", "20대", "30대", "40대", "50대", "60대", "70대"]
RACKET_OPTIONS = ["기타", "윌슨", "요넥스", "헤드", "바볼랏", "던롭", "뵐클", "테크니파이버", "프린스"]
GENDER_OPTIONS = ["남", "여"]
HAND_OPTIONS = ["오른손", "왼손"]
GROUP_OPTIONS = ["미배정", "A조", "B조"]
NTRP_OPTIONS = ["모름"] + [f"{x/2:.1f}" for x in range(2, 15)]  # 1.0~7.0
COURT_TYPES = ["인조잔디", "하드", "클레이"]
SIDE_OPTIONS = ["포(듀스)", "백(애드)"]
SCORE_OPTIONS = list(range(0, 7))

WIN_POINT = 3
DRAW_POINT = 1
LOSE_POINT = 0

# ---------------------------------------------------------
# 한울 AA 패턴 (5~16명 전용, 4게임 보장)
# ---------------------------------------------------------
HANUL_AA_PATTERNS = {
    5: [
        "12:34",
        "13:25",
        "14:35",
        "15:24",
        "23:45",
    ],
    6: [
        "12:34",
        "15:46",
        "23:56",
        "14:25",
        "24:36",
        "16:35",
    ],
    7: [
        "12:34",
        "56:17",
        "35:24",
        "14:67",
        "23:57",
        "16:25",
        "46:37",
    ],
    8: [
        "12:34",
        "56:78",
        "13:57",
        "24:68",
        "37:48",
        "15:26",
        "16:38",
        "25:47",
    ],
    9: [
        "12:34",
        "56:78",
        "19:57",
        "23:68",
        "49:38",
        "15:26",
        "17:89",
        "36:45",
        "24:79",
    ],
    10: [
        "12:34",
        "56:78",
        "23:6A",
        "19:58",
        "3A:45",
        "27:89",
        "4A:68",
        "13:79",
        "46:59",
        "17:2A",
    ],
    11: [
        "12:34",
        "56:78",
        "1B:9A",
        "23:68",
        "4A:57",
        "26:9B",
        "13:5B",
        "49:8A",
        "17:28",
        "5A:6B",
        "39:47",
    ],
    12: [
        "12:34",
        "56:78",
        "9A:BC",
        "37:48",
        "29:5A",
        "1B:6C",
        "13:57",
        "24:9B",
        "68:AC",
        "17:2B",
        "35:6A",
        "49:8C",
    ],
    13: [
        "12:34",
        "56:78",
        "9A:BC",
        "1D:25",
        "37:4A",
        "68:9B",
        "CD:13",
        "26:5A",
        "47:8B",
        "9C:2D",
        "15:AB",
        "3C:67",
        "48:9D",
    ],
    14: [
        "12:34",
        "56:78",
        "9A:BC",
        "DE:13",
        "24:57",
        "68:9B",
        "26:CD",
        "79:AE",
        "14:8B",
        "5E:6A",
        "3C:7B",
        "2D:89",
        "3E:45",
        "AC:1D",
    ],
    15: [
        "12:34",
        "56:78",
        "9A:BC",
        "DE:1F",
        "23:57",
        "46:AB",
        "8D:9E",
        "4F:5C",
        "13:6B",
        "27:8A",
        "9C:5E",
        "36:DF",
        "1B:8C",
        "47:EF",
        "2A:9D",
    ],
    16: [
        "12:34",
        "56:78",
        "9A:BC",
        "DE:FG",
        "13:57",
        "24:68",
        "9B:DF",
        "AC:EG",
        "15:9D",
        "37:BF",
        "26:AE",
        "48:CG",
        "19:2A",
        "5D:6E",
        "3B:4C",
        "7F:8G",
    ],
}

def char_to_index(ch: str) -> int:
    """
    한울 AA 패턴 문자열에서 문자 하나를 인덱스로 변환
    - "1"~"9" -> 0~8
    - "A" -> 9 (10번째 사람)
    - "B" -> 10
    - ...
    - "G" -> 15
    """
    if ch.isdigit():
        return int(ch) - 1
    # A=10번째(인덱스 9)부터 시작
    return 9 + (ord(ch) - ord("A"))


def parse_pattern(pattern: str, players: list[str]):
    """
    예: "12:34" -> ( [players[0], players[1]], [players[2], players[3]] )
    예: "9A:BC" -> ( [9번째,10번째], [11번째,12번째] )
    """
    t1_raw, t2_raw = pattern.split(":")
    t1, t2 = [], []

    for c in t1_raw:
        idx = char_to_index(c)
        if 0 <= idx < len(players):
            t1.append(players[idx])

    for c in t2_raw:
        idx = char_to_index(c)
        if 0 <= idx < len(players):
            t2.append(players[idx])

    return t1, t2


def build_hanul_aa_schedule(players, court_count):
    """
    한울 AA 고정 패턴으로 복식 대진표 생성
    - 5~16명에서만 동작
    - 각 인원은 정확히 4게임씩 배정됨
    - 코트 번호는 1 ~ court_count 순서로 라운드 로빈 분배
    """
    n = len(players)
    if n not in HANUL_AA_PATTERNS:
        return []

    patterns = HANUL_AA_PATTERNS[n]
    schedule = []

    for i, p in enumerate(patterns):
        t1, t2 = parse_pattern(p, players)
        # 혹시라도 패턴상 인원이 4명 미만이 되면 스킵
        if len(t1) != 2 or len(t2) != 2:
            continue
        court = (i % court_count) + 1
        schedule.append(("복식", t1, t2, court))

    return schedule



# ---------------------------------------------------------
# 파일 입출력
# ---------------------------------------------------------
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


def load_players():
    return load_json(PLAYERS_FILE, [])


def save_players(players):
    save_json(PLAYERS_FILE, players)


def load_sessions():
    return load_json(SESSIONS_FILE, {})


def save_sessions(sessions):
    save_json(SESSIONS_FILE, sessions)

# ---------------------------------------------------------
# 스타일 / 헬퍼
# ---------------------------------------------------------
def colorize_df_names(df, roster_by_name, columns):
    """DataFrame 안 이름 관련 컬럼에 성별별 배경색 적용"""
    def style_name(val):
        if not isinstance(val, str) or not val:
            return ""
        base = val.split("·")[0].strip().split()[0]
        meta = roster_by_name.get(base)
        if meta is None:
            return ""
        g = meta.get("gender")
        if g == "남":
            return "background-color:#cce8ff"
        elif g == "여":
            return "background-color:#ffd6d6"
        return ""

    styler = df.style
    for c in columns:
        if c in df.columns:
            styler = styler.applymap(style_name, subset=[c])
    return styler


def render_name_badge(name, roster_by_name):
    """이름 + 성별 배경 색깔 뱃지 HTML"""
    meta = roster_by_name.get(name, {})
    g = meta.get("gender")
    if g == "남":
        bg = "#cce8ff"
    elif g == "여":
        bg = "#ffd6d6"
    else:
        bg = "#eeeeee"

    return (
        "<span style='"
        "background-color:{bg};"
        "padding:3px 8px;"
        "border-radius:6px;"
        "margin-right:4px;"
        "font-size:0.95rem;"
        "font-weight:600;"
        "'>{name}</span>"
    ).format(bg=bg, name=name)



def sync_side_select(sel_date, game_idx, player, partner):
    key_p = f"{sel_date}_side_{game_idx}_{player}"
    key_m = f"{sel_date}_side_{game_idx}_{partner}"

    val_p = st.session_state.get(key_p, SIDE_OPTIONS[0])
    opp = SIDE_OPTIONS[1] if val_p == SIDE_OPTIONS[0] else SIDE_OPTIONS[0]

    st.session_state[key_m] = opp


def get_index_or_default(options, value, default_index=0):
    try:
        return options.index(value)
    except ValueError:
        return default_index


def get_ntrp_value(meta):
    v = meta.get("ntrp")
    if v is None:
        return 2.0  # 모름 기본값
    return float(v)


def get_total_games_by_player(sessions):
    """전체 세션 기준 개인 총 경기 수 (정렬용)"""
    counts = defaultdict(int)
    for d, idx, g in iter_games(sessions):
        for p in g["t1"] + g["t2"]:
            counts[p] += 1
    return counts

# ---------------------------------------------------------
# 대진 생성
# ---------------------------------------------------------
def build_doubles_schedule(players, max_games, court_count, mode,
                           use_ntrp, group_only, roster_by_name,
                           relaxed_mixed=False):
    """
    복식 스케줄러
    - 파트너/상대 중복 최소화
    - relaxed_mixed=True 이고 mode=="혼합복식" 이면
      → 2남2녀(혼복)을 우선적으로 선택하지만, 꼭 지키지 않아도 되도록 완화
    """
    if len(players) < 4:
        return []

    meta = {p: roster_by_name.get(p, {}) for p in players}
    genders = {p: meta[p].get("gender") for p in players}
    groups = {p: meta[p].get("group", "미배정") for p in players}

    games_played = {p: 0 for p in players}
    partner_counts = defaultdict(int)   # (a, b) 같은 팀
    opponent_counts = defaultdict(int)  # (a, b) 서로 상대

    schedule = []

    def can_team(team4):
        # 조별 매칭 제한 (이미 그룹을 나눠서 들어왔다면 group_only=False 로 호출)
        if group_only:
            if len({groups[x] for x in team4}) > 1:
                return False

        # 동성복식
        if mode == "동성복식":
            if len({genders[x] for x in team4}) > 1:
                return False

        # 혼합복식 (strict 모드에서만 강제)
        if mode == "혼합복식" and not relaxed_mixed:
            males = [x for x in team4 if genders[x] == "남"]
            females = [x for x in team4 if genders[x] == "여"]
            if len(males) < 2 or len(females) < 2:
                return False

        return True

    total_games = (len(players) * max_games) // 4
    tries = 0
    while len(schedule) < total_games and tries < total_games * 80:
        tries += 1
        available = [p for p in players if games_played[p] < max_games]
        if len(available) < 4:
            break

        # NTRP 적용
        if use_ntrp:
            available.sort(key=lambda x: get_ntrp_value(meta[x]))
        random.shuffle(available)

        picked = None
        best_score = 1e9

        for i in range(len(available) - 3):
            cand = available[i:i+4]
            if not can_team(cand):
                continue

            perms = [(0, 1, 2, 3), (0, 2, 1, 3), (0, 3, 1, 2)]
            for a, b, c, d in perms:
                p1, p2, p3, p4 = cand[a], cand[b], cand[c], cand[d]

                key_t1 = tuple(sorted((p1, p2)))
                key_t2 = tuple(sorted((p3, p4)))
                partner_score = partner_counts[key_t1] + partner_counts[key_t2]

                opp_pairs = [
                    tuple(sorted((p1, p3))), tuple(sorted((p1, p4))),
                    tuple(sorted((p2, p3))), tuple(sorted((p2, p4))),
                ]
                opp_score = sum(opponent_counts[k] for k in opp_pairs)

                # ★ 혼복 완화 모드일 때: 2남2녀가 아니면 약간 페널티
                gender_score = 0
                if mode == "혼합복식" and relaxed_mixed:
                    males = sum(1 for x in [p1, p2, p3, p4] if genders[x] == "남")
                    females = sum(1 for x in [p1, p2, p3, p4] if genders[x] == "여")
                    if not (males == 2 and females == 2):
                        gender_score = 5  # 숫자 클수록 혼복 형태를 더 강하게 선호

                total_score = partner_score * 2 + opp_score + gender_score

                if total_score < best_score:
                    best_score = total_score
                    picked = (p1, p2, p3, p4)

            if picked is not None:
                break

        if not picked:
            continue

        p1, p2, p3, p4 = picked
        t1, t2 = [p1, p2], [p3, p4]

        for p in t1 + t2:
            games_played[p] += 1

        partner_counts[tuple(sorted((p1, p2)))] += 1
        partner_counts[tuple(sorted((p3, p4)))] += 1

        for a in t1:
            for b in t2:
                opponent_counts[tuple(sorted((a, b)))] += 1

        schedule.append(("복식", t1, t2, None))

    # 코트 배정
    for i, (gtype, t1, t2, _) in enumerate(schedule):
        court = (i % court_count) + 1
        schedule[i] = (gtype, t1, t2, court)
    return schedule



def build_singles_schedule(players, max_games, court_count, mode,
                           use_ntrp, group_only, roster_by_name):
    """
    단식 스케줄러
    - 같은 상대 중복 최소화
    """
    if len(players) < 2:
        return []

    meta = {p: roster_by_name.get(p, {}) for p in players}
    genders = {p: meta[p].get("gender") for p in players}
    groups = {p: meta[p].get("group", "미배정") for p in players}

    games_played = {p: 0 for p in players}
    opponent_counts = defaultdict(int)

    schedule = []

    def can_pair(a, b):
        if group_only and groups[a] != groups[b]:
            return False
        if mode == "동성 단식" and genders[a] != genders[b]:
            return False
        if mode == "혼합 단식" and genders[a] == genders[b]:
            return False
        return True

    total_games = (len(players) * max_games) // 2
    tries = 0
    while len(schedule) < total_games and tries < total_games * 80:
        tries += 1
        available = [p for p in players if games_played[p] < max_games]
        if len(available) < 2:
            break

        if use_ntrp:
            available.sort(key=lambda x: get_ntrp_value(meta[x]))
        random.shuffle(available)

        best_pair = None
        best_score = 1e9

        for i in range(len(available) - 1):
            a = available[i]
            for j in range(i + 1, len(available)):
                b = available[j]
                if not can_pair(a, b):
                    continue
                key = tuple(sorted((a, b)))
                score = opponent_counts[key]
                if score < best_score:
                    best_score = score
                    best_pair = (a, b)

        if not best_pair:
            continue

        a, b = best_pair
        games_played[a] += 1
        games_played[b] += 1
        opponent_counts[tuple(sorted((a, b)))] += 1

        schedule.append(("단식", [a], [b], None))

    for i, (gtype, t1, t2, _) in enumerate(schedule):
        court = (i % court_count) + 1
        schedule[i] = (gtype, t1, t2, court)
    return schedule

# ---------------------------------------------------------
# 경기 / 통계 유틸
# ---------------------------------------------------------
def iter_games(sessions):
    """전체 세션에서 (날짜, 인덱스, 게임 dict) yield"""
    for d, data in sessions.items():
        schedule = data.get("schedule", [])
        results = data.get("results", {})
        court_type = data.get("court_type", COURT_TYPES[0])
        for idx, g in enumerate(schedule, start=1):
            gtype, t1, t2, court = g
            res = results.get(str(idx)) or results.get(idx) or {}
            yield d, idx, {
                "type": gtype,
                "t1": t1,
                "t2": t2,
                "court": court,
                "court_type": court_type,
                "score1": res.get("t1"),
                "score2": res.get("t2"),
                "sides": res.get("sides", {}),
            }

def classify_game_group(players, roster_by_name):
    """
    게임에 참여한 사람들의 실력조를 기준으로
    - A조만 있으면 -> "A"
    - B조만 있으면 -> "B"
    - 그 외(섞여 있거나 미배정만 있는 경우) -> "other"
    """
    groups = [
        roster_by_name.get(p, {}).get("group", "미배정")
        for p in players
    ]
    has_A = any(g == "A조" for g in groups)
    has_B = any(g == "B조" for g in groups)

    if has_A and not has_B:
        return "A"
    if has_B and not has_A:
        return "B"
    return "other"


def calc_result(score1, score2):
    if score1 is None or score2 is None:
        return None
    if score1 > score2:
        return "W"
    if score1 < score2:
        return "L"
    return "D"


def update_player_record(rec, result):
    if result == "W":
        rec["W"] += 1
        rec["points"] += WIN_POINT
    elif result == "L":
        rec["L"] += 1
        rec["points"] += LOSE_POINT
    elif result == "D":
        rec["D"] += 1
        rec["points"] += DRAW_POINT


def render_score_summary_table(games, roster_by_name):
    """게임 리스트로 HTML 요약 테이블 렌더링"""
    if not games:
        return
    games_sorted = sorted(games, key=lambda x: x["게임"])

    html = ["<table style='border-collapse:collapse;width:100%;'>"]
    header_cols = ["게임", "코트", "타입", "팀1", "팀1 점수", "팀2 점수", "팀2"]
    html.append("<thead><tr>")
    for col in header_cols:
        html.append(
            f"<th style='border:1px solid #ddd;padding:4px;text-align:center;background-color:#f5f5f5;'>{col}</th>"
        )
    html.append("</tr></thead><tbody>")

    for row in games_sorted:
        idx = row["게임"]
        court = row["코트"]
        gtype = row["타입"]
        t1 = row["t1"]
        t2 = row["t2"]
        s1 = row["t1_score"]
        s2 = row["t2_score"]

        t1_html = "".join(render_name_badge(n, roster_by_name) for n in t1)
        t2_html = "".join(render_name_badge(n, roster_by_name) for n in t2)

        s1_style = "border:1px solid #ddd;padding:4px;text-align:center;"
        s2_style = "border:1px solid #ddd;padding:4px;text-align:center;"
        if s1 is not None and s2 is not None:
            if s1 > s2:
                s1_style += "background-color:#fff6a5;"
            elif s2 > s1:
                s2_style += "background-color:#fff6a5;"
            else:
                s1_style += "background-color:#e0e0e0;"
                s2_style += "background-color:#e0e0e0;"

        html.append(
            "<tr>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:center;'>{idx}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:center;'>{court}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:center;'>{gtype}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;'>{t1_html}</td>"
            f"<td style='{s1_style}'>{'' if s1 is None else s1}</td>"
            f"<td style='{s2_style}'>{'' if s2 is None else s2}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;'>{t2_html}</td>"
            "</tr>"
        )

    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)

# ---------------------------------------------------------
# Streamlit 초기화
# ---------------------------------------------------------
st.set_page_config(
    page_title="테니스 매칭 도우미",
    layout="centered",             # wide → centered 로 변경 (폰에서 덜 퍼져 보이게)
    initial_sidebar_state="collapsed",
)

# 🔽 모바일 폰에서 여백/폰트/탭 간격 줄이는 CSS
MOBILE_CSS = """
<style>
/* 전체 패딩 줄이기 */
.block-container {
    padding-top: 0.8rem;
    padding-bottom: 1.5rem;
    padding-left: 0.9rem;
    padding-right: 0.9rem;
}

/* 작은 화면용 최적화 */
@media (max-width: 768px) {

    .block-container {
        padding-left: 0.6rem;
        padding-right: 0.6rem;
    }

    h1 {
        font-size: 1.4rem;
        margin-bottom: 0.7rem;
    }

    h2 {
        font-size: 1.15rem;
        margin-bottom: 0.5rem;
    }

    h3 {
        font-size: 1.0rem;
        margin-bottom: 0.4rem;
    }

    /* 탭 버튼들 한 줄에 너무 꽉 차지 않게 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.15rem;
        flex-wrap: wrap;
    }
    .stTabs [role="tab"] {
        font-size: 0.8rem;
        padding: 0.2rem 0.45rem;
    }

    /* 데이터프레임 스크롤 영역 조금 낮게 */
    .stDataFrame {
        font-size: 0.8rem;
    }
}
</style>
"""

st.markdown(MOBILE_CSS, unsafe_allow_html=True)


if "roster" not in st.session_state:
    st.session_state.roster = load_players()
if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions()
if "current_order" not in st.session_state:
    st.session_state.current_order = []
if "shuffle_count" not in st.session_state:
    st.session_state.shuffle_count = 0
if "today_schedule" not in st.session_state:
    st.session_state.today_schedule = []
if "today_court_type" not in st.session_state:
    st.session_state.today_court_type = COURT_TYPES[0]
if "save_date" not in st.session_state:
    st.session_state.save_date = date.today()
if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None
if "target_games" not in st.session_state:          # ← 이 줄 추가
    st.session_state.target_games = None


roster = st.session_state.roster
sessions = st.session_state.sessions
roster_by_name = {p["name"]: p for p in roster}

st.title("🎾 테니스 매칭 도우미")

# 📱 폰에서 볼 때 ON 해두면 A/B조 나란히 레이아웃을 세로로 바꿔줌
mobile_mode = st.checkbox(
    "📱 모바일 최적화 모드",
    value=True,
    help="핸드폰에서 볼 때는 켜 두는 걸 추천해!"
)



tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🧾 선수 정보 관리", "🎾 오늘 경기 세션", "📋 경기 기록 / 통계", "👤 개인별 통계", "📆 월별 통계"]
)

# =========================================================
# 1) 선수 정보 관리
# =========================================================
with tab1:
    st.header("🧾 선수 정보 관리")

    # 새 선수 추가
    st.subheader("새 선수 추가")
    c1, c2 = st.columns(2)
    with c1:
        new_name = st.text_input("이름")
        new_age = st.selectbox("나이대", AGE_OPTIONS, index=0)
        new_racket = st.selectbox("라켓", RACKET_OPTIONS, index=0)
        new_group = st.selectbox("실력조 (A/B/C)", GROUP_OPTIONS, index=0)
    with c2:
        new_gender = st.selectbox("성별", GENDER_OPTIONS, index=0)
        new_hand = st.selectbox("주로 쓰는 손", HAND_OPTIONS, index=0)
        ntrp_str = st.selectbox("NTRP (실력)", NTRP_OPTIONS, index=0)

    if st.button("선수 추가"):
        if not new_name.strip():
            st.error("이름을 입력해 주세요.")
        elif any(p["name"] == new_name for p in roster):
            st.error("이미 같은 이름의 선수가 있습니다.")
        else:
            ntrp_val = None
            if ntrp_str != "모름":
                ntrp_val = float(ntrp_str)
            player = {
                "name": new_name.strip(),
                "gender": new_gender,
                "hand": new_hand,
                "age_group": new_age,
                "racket": new_racket,
                "group": new_group,
                "ntrp": ntrp_val,
            }
            roster.append(player)
            st.session_state.roster = roster
            save_players(roster)
            st.success(f"'{new_name}' 선수 추가 완료!")

    st.markdown("---")
    st.subheader("등록된 선수 목록")

    if roster:
        df = pd.DataFrame(roster)
        df_disp = df.copy()
        df_disp["NTRP"] = df_disp["ntrp"].apply(
            lambda v: "-" if v is None else f"{v:.1f}"
        )
        df_disp = df_disp.drop(columns=["ntrp"])
        df_disp = df_disp.rename(
            columns={
                "name": "이름",
                "gender": "성별",
                "hand": "주손",
                "age_group": "나이대",
                "racket": "라켓",
                "group": "실력조",
            }
        )
        roster_by_name = {p["name"]: p for p in roster}
        for grp in ["A조", "B조", "C조", "미배정"]:
            sub = df_disp[df_disp["실력조"] == grp]
            if sub.empty:
                continue
            st.markdown(f"■ {grp}")
            sty = colorize_df_names(sub, roster_by_name, ["이름"])
            st.dataframe(sty, use_container_width=True)
    else:
        st.info("등록된 선수가 없습니다.")

    st.markdown("---")
    st.subheader("선수 정보 수정 / 삭제")

    names = [p["name"] for p in roster]
    if names:
        sel_edit = st.selectbox("수정할 선수 선택", ["선택 안함"] + names)
        if sel_edit != "선택 안함":
            player = next(p for p in roster if p["name"] == sel_edit)
            c1, c2 = st.columns(2)
            with c1:
                e_name = st.text_input("이름 (수정)", value=player["name"])
                e_age = st.selectbox(
                    "나이대 (수정)",
                    AGE_OPTIONS,
                    index=get_index_or_default(
                        AGE_OPTIONS, player.get("age_group", "비밀"), 0
                    ),
                )
                e_racket = st.selectbox(
                    "라켓 (수정)",
                    RACKET_OPTIONS,
                    index=get_index_or_default(
                        RACKET_OPTIONS, player.get("racket", "기타"), 0
                    ),
                )
                e_group = st.selectbox(
                    "실력조 (수정)",
                    GROUP_OPTIONS,
                    index=get_index_or_default(
                        GROUP_OPTIONS, player.get("group", "미배정"), 0
                    ),
                )
            with c2:
                e_gender = st.selectbox(
                    "성별 (수정)",
                    GENDER_OPTIONS,
                    index=get_index_or_default(
                        GENDER_OPTIONS, player.get("gender", "남"), 0
                    ),
                )
                e_hand = st.selectbox(
                    "주손 (수정)",
                    HAND_OPTIONS,
                    index=get_index_or_default(
                        HAND_OPTIONS, player.get("hand", "오른손"), 0
                    ),
                )
                cur_ntrp = player.get("ntrp")
                cur_ntrp_str = "모름" if cur_ntrp is None else f"{cur_ntrp:.1f}"
                e_ntrp_str = st.selectbox(
                    "NTRP (수정)",
                    NTRP_OPTIONS,
                    index=get_index_or_default(NTRP_OPTIONS, cur_ntrp_str, 0),
                )

            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("수정 저장"):
                    ntrp_val = None
                    if e_ntrp_str != "모름":
                        ntrp_val = float(e_ntrp_str)
                    player.update(
                        {
                            "name": e_name.strip(),
                            "age_group": e_age,
                            "racket": e_racket,
                            "group": e_group,
                            "gender": e_gender,
                            "hand": e_hand,
                            "ntrp": ntrp_val,
                        }
                    )
                    save_players(roster)
                    st.success("선수 정보가 수정되었습니다. (새로고침 시 반영)")
            with cb2:
                if st.button("이 선수 삭제"):
                    st.session_state.roster = [
                        p for p in roster if p["name"] != sel_edit
                    ]
                    save_players(st.session_state.roster)
                    st.success("선수 삭제 완료. (새로고침 필요)")
    else:
        st.info("수정할 선수가 없습니다.")

# =========================================================
# 2) 오늘 경기 세션
# =========================================================
with tab2:
    st.header("🎾 오늘 경기 세션")

    # 0. 저장할 날짜
    st.subheader("0. 저장할 날짜 선택")
    st.session_state.save_date = st.date_input(
        "이 날짜 기준으로 대진을 관리합니다.",
        value=st.session_state.save_date,
        key="save_date_input",
    )
    save_date = st.session_state.save_date

    # 1. 참가자 선택
    st.subheader("1. 참가자 선택")
    names_all = [p["name"] for p in roster]
    play_counts = get_total_games_by_player(sessions)
    names_sorted = sorted(
        names_all, key=lambda n: (-play_counts.get(n, 0), n)
    )
    sel_players = st.multiselect("오늘 참가 선수들", names_sorted, default=[])
    st.write(f"현재 참가 인원: {len(sel_players)}명")

    # 순서 초기화
    if sel_players and (
        not st.session_state.current_order
        or set(st.session_state.current_order) != set(sel_players)
    ):
        st.session_state.current_order = sel_players.copy()
        st.session_state.shuffle_count = 0
    current_order = st.session_state.current_order

    # 2. 순서 정하기
    st.subheader("2. 순서 정하기")
    order_mode = st.radio("순서 방식", ["랜덤 섞기", "수동 입력"], horizontal=True)

    if order_mode == "랜덤 섞기":
        cb, ci = st.columns([1, 3])
        with cb:
            if st.button("랜덤으로 순서 섞기"):
                random.shuffle(current_order)
                st.session_state.current_order = current_order
                st.session_state.shuffle_count += 1
        with ci:
            st.write(f"섞은 횟수: {st.session_state.shuffle_count} 회")
    else:
        default_text = "\n".join(current_order) if current_order else ""
        text = st.text_area(
            "한 줄에 한 명씩 이름을 입력 (선택한 사람들만)", value=default_text, height=140
        )
        if st.button("수동 순서 적용"):
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                st.warning("한 명 이상 입력해 주세요.")
            elif set(lines) != set(sel_players):
                st.error("선택된 참가자와 이름 목록이 일치하지 않습니다.")
            else:
                st.session_state.current_order = lines
                current_order = lines
                st.success("수동 순서가 적용되었습니다.")

    # 현재 순서 표시 방식 선택
    if current_order:
        # 이전 선택 기억해서 기본값으로 쓰기
        default_view = st.session_state.get("order_view_mode", "전체")
        default_idx = 0 if default_view == "전체" else 1

        view_mode = st.radio(
            "순서 표시 방식",
            ["전체", "조별 분리 (A/B조)"],
            horizontal=True,
            index=default_idx,
        )
        st.session_state.order_view_mode = view_mode  # ← 여기!

        # 전체 보기
        if view_mode == "전체":
            st.write("현재 순서:")
            for i, n in enumerate(current_order, start=1):
                badge = render_name_badge(n, roster_by_name)
                st.markdown(f"{i}. {badge}", unsafe_allow_html=True)

        # A조 / B조 분리 보기 (C조/미배정은 표시 안 함)
        else:
            groups = {
                name: roster_by_name.get(name, {}).get("group", "미배정")
                for name in current_order
            }

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

    # 3. 대진 설정
    st.subheader("3. 대진 설정")

    # 3-1. 게임 타입
    gtype = st.radio("게임 타입", ["복식", "단식"], horizontal=True)

    # 공통 기본값
    mode_label = None
    singles_mode = None
    is_aa_mode = False

    # 3-2. 모드 선택 (복식 / 단식에 따라 분기)
    if gtype == "복식":
        # 복식 모드는 한울 AA를 디폴트(기본값)로
        doubles_modes = [
            "랜덤 복식",
            "동성복식 (남+남 / 여+여)",
            "혼합복식 (남+여 짝)",
            "한울 AA 방식 (4게임 고정)",
        ]
        mode_label = st.selectbox(
            "복식 대진 방식",
            doubles_modes,
            index=3,  # ← 기본 선택: 한울 AA
        )
        is_aa_mode = (mode_label == "한울 AA 방식 (4게임 고정)")
    else:
        singles_mode = st.selectbox(
            "단식 대진 방식",
            ["랜덤 단식", "동성 단식", "혼합 단식"],
        )

    # 3-3. 개인당 경기 수 / 코트 수
    cg1, cg2 = st.columns(2)
    with cg1:
        if gtype == "복식" and is_aa_mode:
            # AA 모드: 4게임 고정 + 비활성화
            max_games = st.number_input(
                "개인당 경기 수 (한울 AA: 4게임 고정)",
                min_value=4,
                max_value=4,
                value=4,
                step=1,
                disabled=True,
            )
        else:
            max_games = st.number_input(
                "개인당 경기 수 (정확히 이 횟수로 배정)",
                min_value=1,
                max_value=10,
                value=4,
                step=1,
            )

    with cg2:
        if gtype == "복식" and is_aa_mode:
            court_count = st.number_input(
                "사용 코트 수 (한울 AA 모드에서는 고정값)", 
                min_value=1,
                max_value=6,
                value=2,
                step=1,
                disabled=True,   # ← 코트 수도 비활성화
            )
        else:
            court_count = st.number_input(
                "사용 코트 수", min_value=1, max_value=6, value=2, step=1
            )

    # 코트 종류는 그대로 선택 가능
    court_type = st.selectbox("코트 종류", COURT_TYPES, index=0)

    # 3-4. NTRP / 조별 옵션 (AA 모드이면 비활성화)
    opt1, opt2 = st.columns(2)
    with opt1:
        if gtype == "복식" and is_aa_mode:
            use_ntrp = st.checkbox(
                "NTRP 고려 (비슷한 실력끼리 매칭)",
                value=False,
                disabled=True,
            )
        else:
            use_ntrp = st.checkbox("NTRP 고려 (비슷한 실력끼리 매칭)")
    with opt2:
        if gtype == "복식" and is_aa_mode:
            group_only_option = st.checkbox(
                "조별로만 매칭 (A/B조만, C조 제외)",
                value=False,
                disabled=True,
            )
        else:
            group_only_option = st.checkbox("조별로만 매칭 (A/B조만, C조 제외)")

    # 👇 여기 추가: 조별 분리 보기면 자동으로 조별 매칭 적용
    view_mode_for_schedule = st.session_state.get("order_view_mode", "전체")
    group_only = group_only_option or (view_mode_for_schedule == "조별 분리 (A/B조)")

    # 3-5. AA 모드 안내
    if gtype == "복식" and is_aa_mode:
        st.info(
            "한울 AA 방식은 5~16명에서 사용하는 고정 패턴입니다.\n"
            "- 항상 복식 전용, 개인당 4게임 고정입니다.\n"
            "- NTRP / 조별 매칭 / 혼복 옵션은 적용되지 않습니다.\n"
            "- 사용 코트 수는 현재 값으로 고정됩니다."
        )

    # 4. 대진표 생성 / 미리보기
    st.subheader("4. 대진표 생성 / 미리보기")

    if st.button("대진표 생성하기"):
        if len(current_order) < (4 if gtype == "복식" else 2):
            st.error("인원이 부족합니다.")
        else:
            players_selected = current_order.copy()
            schedule = []
            st.session_state.target_games = None  # 초기화

            # ---------------------------
            # 4-1. 한울 AA 모드
            # ---------------------------
            if is_aa_mode:
                # 순서 표시 모드 가져오기 (전체 / 조별 분리)
                view_mode_for_schedule = st.session_state.get(
                    "order_view_mode", "전체"
                )

                # ① 조별 분리 모드면 A조 / B조 따로 AA 패턴 적용
                if view_mode_for_schedule == "조별 분리 (A/B조)":
                    group_players = {"A조": [], "B조": []}
                    for p in players_selected:
                        grp = roster_by_name.get(p, {}).get("group", "미배정")
                        if grp in ("A조", "B조"):
                            group_players[grp].append(p)

                    combined = []
                    for grp_label in ["A조", "B조"]:
                        grp_list = group_players[grp_label]
                        if not grp_list:
                            continue

                        n_grp = len(grp_list)
                        if n_grp < 5 or n_grp > 16:
                            st.warning(
                                f"한울 AA: {grp_label} 인원이 {n_grp}명이라 "
                                "5~16명이 아니어서 이 조에는 AA 패턴을 적용하지 않습니다."
                            )
                            continue

                        sub_schedule = build_hanul_aa_schedule(
                            grp_list, court_count
                        )
                        combined.extend(sub_schedule)

                    schedule = combined

                # ② 전체 보기면 기존처럼 전체 인원 기준으로 한 번만 AA
                else:
                    n = len(players_selected)
                    if n < 5 or n > 16:
                        st.error(
                            f"한울 AA 방식은 5명 이상 16명 이하에서만 사용할 수 있습니다. (현재 인원: {n}명)"
                        )
                    else:
                        schedule = build_hanul_aa_schedule(
                            players_selected, court_count
                        )

                st.session_state.today_schedule = schedule
                st.session_state.today_court_type = court_type
                st.session_state.target_games = 4

                if not schedule:
                    st.warning("조건에 맞는 한울 AA 대진을 만들지 못했습니다.")
                else:
                    st.success("한울 AA 방식 대진표 생성 완료! (개인당 4게임 고정)")

            # ---------------------------
            # 4-2. 일반 랜덤/동성/혼복 모드
            # ---------------------------
            else:
                if gtype == "복식":
                    unit = 4
                    mode_map = {
                        "랜덤 복식": "랜덤",
                        "동성복식 (남+남 / 여+여)": "동성복식",
                        "혼합복식 (남+여 짝)": "혼합복식",
                    }
                else:
                    unit = 2
                    mode_map_s = {
                        "랜덤 단식": "랜덤",
                        "동성 단식": "동성 단식",
                        "혼합 단식": "혼합 단식",
                    }

                can_generate = True

                # 공평 경기수 가능 여부 체크
                if group_only:
                    group_players = {"A조": [], "B조": []}
                    for p in players_selected:
                        grp = roster_by_name.get(p, {}).get("group", "미배정")
                        if grp in ("A조", "B조"):
                            group_players[grp].append(p)

                    for grp_label in ["A조", "B조"]:
                        grp_list = group_players[grp_label]
                        if not grp_list:
                            continue
                        if len(grp_list) < (4 if gtype == "복식" else 2):
                            st.warning(
                                f"{grp_label} 인원이 부족하여 대진을 만들 수 없습니다."
                            )
                            continue
                        needed = len(grp_list) * max_games
                        if needed % unit != 0:
                            st.error(
                                f"{grp_label} 조: 인원수×개인당 경기 수가 {unit}의 배수가 아니어서 "
                                f"모든 선수가 정확히 {max_games}경기씩 할 수 없습니다."
                            )
                            can_generate = False
                    if not any(
                        len(group_players[g]) >= (4 if gtype == "복식" else 2)
                        for g in ["A조", "B조"]
                    ):
                        st.error("A조/B조 모두 인원이 부족하거나 조건이 맞지 않습니다.")
                        can_generate = False
                else:
                    needed = len(players_selected) * max_games
                    if needed % unit != 0:
                        st.error(
                            f"인원수×개인당 경기 수({needed})가 {unit}의 배수가 아니라서 "
                            f"모든 선수가 정확히 {max_games}경기씩 할 수 없습니다."
                        )
                        can_generate = False

                # 스케줄 생성
                if can_generate:
                    if group_only:
                        combined = []
                        group_players = {"A조": [], "B조": []}
                        for p in players_selected:
                            grp = roster_by_name.get(p, {}).get("group", "미배정")
                            if grp in ("A조", "B조"):
                                group_players[grp].append(p)

                        for grp_label in ["A조", "B조"]:
                            grp_list = group_players[grp_label]
                            if not grp_list:
                                continue
                            if gtype == "복식":
                                if len(grp_list) < 4:
                                    continue
                                sub_schedule = build_doubles_schedule(
                                    grp_list,
                                    max_games,
                                    court_count,
                                    mode_map[mode_label],
                                    use_ntrp,
                                    False,
                                    roster_by_name,
                                )
                                combined.extend(sub_schedule)
                        schedule = combined
                    else:
                        if gtype == "복식":
                            schedule = build_doubles_schedule(
                                players_selected,
                                max_games,
                                court_count,
                                mode_map[mode_label],
                                use_ntrp,
                                False,
                                roster_by_name,
                            )
                        else:
                            schedule = build_singles_schedule(
                                players_selected,
                                max_games,
                                court_count,
                                mode_map_s[singles_mode],
                                use_ntrp,
                                False,
                                roster_by_name,
                            )

                    st.session_state.today_schedule = schedule
                    st.session_state.today_court_type = court_type
                    st.session_state.target_games = max_games

                    if not schedule:
                        st.warning("조건에 맞는 대진을 만들지 못했습니다.")
                    else:
                        st.success("대진표 생성 완료!")



    schedule = st.session_state.get("today_schedule", [])

    if schedule:
        # 순서 보기 모드(전체 / 조별 분리) 읽기
        view_mode_for_schedule = st.session_state.get("order_view_mode", "전체")

        # --- 조별 분리 모드일 때: A조 / B조로 나눠서 표시 ---
        if view_mode_for_schedule == "조별 분리 (A/B조)":
            games_A = []
            games_B = []
            games_other = []  # 조 섞인 경기나 미배정이 섞인 경우

            # 각 게임마다 schedule 안에 들어있는 gtype을 사용해야 함
            for idx, (gtype_each, t1, t2, court) in enumerate(schedule, start=1):
                all_players = list(t1) + list(t2)
                item = (idx, gtype_each, t1, t2, court)
                grp_flag = classify_game_group(all_players, roster_by_name)

                if grp_flag == "A":
                    games_A.append(item)
                elif grp_flag == "B":
                    games_B.append(item)
                else:
                    games_other.append(item)

            def render_game_list(title, games):
                if not games:
                    return
                st.markdown(f"### {title}")

                # 조별로 게임 번호를 1번부터 다시 매기기
                for local_idx, (orig_idx, gtype_each, t1, t2, court) in enumerate(games, start=1):
                    t1_html = "".join(render_name_badge(n, roster_by_name) for n in t1)
                    t2_html = "".join(render_name_badge(n, roster_by_name) for n in t2)

                    st.markdown(
                        f"게임 {local_idx} (코트 {court}) [{gtype_each}] : "
                        f"{t1_html} <b>vs</b> {t2_html}",
                        unsafe_allow_html=True,
                    )

            # A조 / B조 / 기타 순서대로 출력
            render_game_list("A조 대진표", games_A)
            render_game_list("B조 대진표", games_B)

            if games_other:
                st.markdown("---")
                render_game_list("조가 섞인 경기 / 기타", games_other)

        # --- 전체 모드일 때: 기존처럼 한 줄로 쭉 표시 ---
        else:
            for idx, (gtype_each, t1, t2, court) in enumerate(schedule, start=1):
                t1_html = "".join(
                    render_name_badge(n, roster_by_name) for n in t1
                )
                t2_html = "".join(
                    render_name_badge(n, roster_by_name) for n in t2
                )
                st.markdown(
                    f"게임 {idx} (코트 {court}) [{gtype_each}] : "
                    f"{t1_html} <b>vs</b> {t2_html}",
                    unsafe_allow_html=True,
                )
    else:
        st.info("생성된 대진표가 없습니다.")




    # 5. 개인당 경기 수 (레이아웃 변경)
    if schedule:
        st.markdown("---")
        st.subheader("5. 개인당 경기 수 (이번 대진 기준)")

        target_games = st.session_state.get("target_games", None)  # ← 추가

        game_counts = defaultdict(int)
        for gt, t1, t2, court in schedule:
            for p in t1 + t2:
                game_counts[p] += 1

        for name in sorted(game_counts.keys()):
            badge = render_name_badge(name, roster_by_name)
            st.markdown(f"{badge} : {game_counts[name]} 경기", unsafe_allow_html=True)

        if target_games is not None and any(
            cnt != target_games for cnt in game_counts.values()
        ):
            st.warning(
                f"⚠ 일부 선수는 목표 경기 수({target_games}경기)를 채우지 못했습니다. "
                "인원/조건을 조정해 주세요."
            )

    st.markdown("---")
    st.subheader("6. 오늘 대진을 날짜에 저장")

    if st.button("이 날짜로 대진 저장/덮어쓰기"):
        schedule = st.session_state.get("today_schedule", [])
        if not schedule:
            st.error("먼저 대진표를 생성해 주세요.")
        else:
            key = save_date.isoformat()
            sessions[key] = {
                "schedule": schedule,
                "results": sessions.get(key, {}).get("results", {}),
                "court_type": st.session_state.get("today_court_type", COURT_TYPES[0]),
            }
            st.session_state.sessions = sessions
            save_sessions(sessions)
            st.success(f"{key} 날짜에 대진이 저장되었습니다.")





# =========================================================
# 3) 경기 기록 / 통계 (날짜별)
# =========================================================
with tab3:
    st.header("📋 경기 기록 / 통계")

    # 👉 요기에서 '전체 / 조별 보기' 선택
    view_mode_scores = st.radio(
        "표시 방식",
        ["조별 보기 (A/B조)","전체"],
        horizontal=True,
        key="tab3_view_mode_scores",
    )

    if not sessions:
        st.info("저장된 경기 기록이 없습니다.")
    else:
        dates = sorted(sessions.keys())
        sel_date = st.selectbox("날짜 선택", dates, index=len(dates) - 1)
        day_data = sessions.get(sel_date, {})
        schedule = day_data.get("schedule", [])
        results = day_data.get("results", {})

        st.subheader("1. 현재 스코어 요약 (표)")
        if not schedule:
            st.info("이 날짜에는 저장된 대진이 없습니다.")
        else:
            # A조 / B조 / 기타로 나누기
            games_A, games_B, games_other = [], [], []

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
                grp_flag = classify_game_group(all_players, roster_by_name)

                if grp_flag == "A":
                    games_A.append(row)
                elif grp_flag == "B":
                    games_B.append(row)
                else:
                    games_other.append(row)


            # ✨ 표시 방식에 따라 다르게 보여주기
            if view_mode_scores == "조별 보기 (A/B조)":
                if games_A:
                    st.markdown("### A조 경기 요약")
                    render_score_summary_table(games_A, roster_by_name)

                if games_B:
                    st.markdown("### B조 경기 요약")
                    render_score_summary_table(games_B, roster_by_name)

                if games_other:
                    st.markdown("### 조가 섞인 경기 / 기타")
                    render_score_summary_table(games_other, roster_by_name)
            else:
                # 전체 보기일 때는 A/B 헤더 없이 한 번에
                all_games = games_A + games_B + games_other
                render_score_summary_table(all_games, roster_by_name)

        st.markdown("---")

    st.subheader("2. 경기 스코어 입력")

    if schedule:
        score_options = SCORE_OPTIONS

        # ------------------------------
        # 게임을 A조 / B조 / 기타로 분류
        # ------------------------------
        games_A, games_B, games_other = [], [], []
        for idx, (gtype, t1, t2, court) in enumerate(schedule, start=1):


            all_players = list(t1) + list(t2)
            grp_flag = classify_game_group(all_players, roster_by_name)

            if grp_flag == "A":
                games_A.append((idx, gtype, t1, t2, court))
            elif grp_flag == "B":
                games_B.append((idx, gtype, t1, t2, court))
            else:
                games_other.append((idx, gtype, t1, t2, court))


        # ------------------------------
        # A/B조별 스코어 입력 블록
        # ------------------------------
        def render_score_inputs_block(title, game_list):
            """title: 'A조 경기 스코어', 'B조 경기 스코어' 등
               game_list: [(idx, gtype, t1, t2, court), ...]"""
            if not game_list:
                return

            # 헤더 색상
            if "A조" in title:
                color = "#ec4899"   # 핑크
                bg    = "#fdf2f8"
            elif "B조" in title:
                color = "#3b82f6"   # 파랑
                bg    = "#eff6ff"
            else:
                color = "#6b7280"   # 회색
                bg    = "#f3f4f6"

            # 헤더 박스
            st.markdown(
                f"""
                <div style="
                    margin-top: 1.5rem;
                    padding: 0.6rem 0.8rem;
                    border-radius: 10px;
                    background-color: {bg};
                    border: 1px solid {color}33;
                ">
                    <span style="font-weight:700; font-size:1.05rem; color:{color};">
                        {title}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 여기서부터는 '표시용 게임 번호'를 1부터 다시 시작
            for local_no, (idx, gtype, t1, t2, court) in enumerate(game_list, start=1):

                # 제목 + 코트 정보 + 위쪽 구분선
                st.markdown(
                    f"""
                    <div style="
                        margin-top:0.9rem;
                        padding-top:0.6rem;
                        border-top:1px solid #e5e7eb;
                        margin-bottom:0.25rem;
                    ">
                        <span style="font-weight:600; font-size:0.98rem;">
                            게임 {local_no}
                        </span>
                        <span style="font-size:0.85rem; color:#6b7280; margin-left:6px;">
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
                prev_sides = res.get("sides", {})

                name1_html = "".join(
                    render_name_badge(n, roster_by_name) for n in t1
                )
                name2_html = "".join(
                    render_name_badge(n, roster_by_name) for n in t2
                )

                # 이름 - 점수 - vs - 점수 - 이름
                c1, c2, c3, c4, c5 = st.columns([3, 1.6, 0.8, 1.6, 3])
                with c1:
                    st.markdown(name1_html, unsafe_allow_html=True)
                with c2:
                    s1 = st.selectbox(
                        " ", score_options,
                        index=get_index_or_default(score_options, prev_s1, 0),
                        key=f"{sel_date}_t1_{idx}",
                    )
                with c3:
                    st.markdown(
                        "<h4 style='text-align:center; margin-top:0.8rem;'>vs</h4>",
                        unsafe_allow_html=True,
                    )
                with c4:
                    s2 = st.selectbox(
                        " ", score_options,
                        index=get_index_or_default(score_options, prev_s2, 0),
                        key=f"{sel_date}_t2_{idx}",
                    )
                with c5:
                    st.markdown(name2_html, unsafe_allow_html=True)

                # --- 사이드(포/백) 선택 ---

                def normalize_side_label(label: str) -> str:
                    """예전 라벨도 모두 '포(듀스) / 백(애드)' 형식으로 통일"""
                    if label is None:
                        return SIDE_OPTIONS[0]
                    if "듀스" in label:
                        return "포(듀스)"
                    if "애드" in label:
                        return "백(애드)"
                    return label

                def opposite_side(label: str) -> str:
                    v = normalize_side_label(label)
                    if "듀스" in v:
                        return "백(애드)"
                    else:
                        return "포(듀스)"

                all_players = list(t1) + list(t2)

                # 🎾 복식(2+2)인 경우: 팀 첫 번째만 선택 가능, 파트너는 자동 반대
                if len(t1) == 2 and len(t2) == 2:
                    a, b = t1  # 팀1
                    c, d = t2  # 팀2

                    side_cols = st.columns(4)

                    # ─ 팀1 ─
                    with side_cols[0]:
                        prev_a = normalize_side_label(
                            prev_sides.get(a, SIDE_OPTIONS[0])
                        )
                        idx_a = get_index_or_default(SIDE_OPTIONS, prev_a, 0)
                        side_a = st.selectbox(
                            a,
                            SIDE_OPTIONS,
                            index=idx_a,
                            key=f"{sel_date}_side_{idx}_{a}",
                        )
                    side_b = opposite_side(side_a)
                    with side_cols[1]:
                        st.markdown(
                            f"<div style='text-align:center;font-size:0.9rem;'>"
                            f"<span style='font-weight:600;'>{b}</span><br>"
                            f"<span style='display:inline-block;margin-top:0.2rem;"
                            f"padding:0.15rem 0.6rem;border-radius:999px;"
                            f"background:#f3f3f3;'>{side_b}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    # ─ 팀2 ─
                    with side_cols[2]:
                        prev_c = normalize_side_label(
                            prev_sides.get(c, SIDE_OPTIONS[0])
                        )
                        idx_c = get_index_or_default(SIDE_OPTIONS, prev_c, 0)
                        side_c = st.selectbox(
                            c,
                            SIDE_OPTIONS,
                            index=idx_c,
                            key=f"{sel_date}_side_{idx}_{c}",
                        )
                    side_d = opposite_side(side_c)
                    with side_cols[3]:
                        st.markdown(
                            f"<div style='text-align:center;font-size:0.9rem;'>"
                            f"<span style='font-weight:600;'>{d}</span><br>"
                            f"<span style='display:inline-block;margin-top:0.2rem;"
                            f"padding:0.15rem 0.6rem;border-radius:999px;"
                            f"background:#f3f3f3;'>{side_d}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    sides = {
                        a: normalize_side_label(side_a),
                        b: normalize_side_label(side_b),
                        c: normalize_side_label(side_c),
                        d: normalize_side_label(side_d),
                    }

                else:
                    # 단식 등 나머지 경우: 기존처럼 각자 선택
                    side_cols = st.columns(len(all_players))
                    sides = {}
                    for j, p in enumerate(all_players):
                        with side_cols[j]:
                            prev_side = normalize_side_label(
                                prev_sides.get(p, SIDE_OPTIONS[0])
                            )
                            idx_side = get_index_or_default(
                                SIDE_OPTIONS, prev_side, 0
                            )
                            sides[p] = st.selectbox(
                                p,
                                SIDE_OPTIONS,
                                index=idx_side,
                                key=f"{sel_date}_side_{idx}_{p}",
                            )

                # 결과 저장
                results[str(idx)] = {"t1": s1, "t2": s2, "sides": sides}

                # 각 게임 블록 아래 얇은 가로줄
                st.markdown(
                    "<div style='border-bottom:1px dashed #e5e7eb; margin:0.6rem 0 0.2rem 0;'></div>",
                    unsafe_allow_html=True,
                )

        # ------------------------------
        # 레이아웃 처리
        # ------------------------------
        has_AB_games = bool(games_A or games_B)

        # 🔽 PC + 조별 보기: A조 | 세로선 | B조 나란히
        if (
            view_mode_scores == "조별 보기 (A/B조)"
            and has_AB_games
            and not mobile_mode    # ← 모바일 모드에서는 이 레이아웃 안 씀
        ):
            colA, colMid, colB = st.columns([1, 0.03, 1])

            with colA:
                render_score_inputs_block("A조 경기 스코어", games_A)

            with colMid:
                # 가운데 세로선
                st.markdown(
                    """
                    <div style="
                        height: 100vh;
                        border-left: 1px solid #e5e7eb;
                        margin: 0 auto;
                    "></div>
                    """,
                    unsafe_allow_html=True,
                )

            with colB:
                render_score_inputs_block("B조 경기 스코어", games_B)

            # A/B조가 아닌 경기(혼합 등)는 아래에 따로 표시
            if games_other:
                st.markdown("---")
                render_score_inputs_block("기타 경기 스코어", games_other)

        else:
            # 🔽 모바일 모드에서 조별 보기인 경우 → A조, B조, 기타를 세로로 순서대로
            if view_mode_scores == "조별 보기 (A/B조)" and has_AB_games and mobile_mode:
                render_score_inputs_block("A조 경기 스코어", games_A)
                render_score_inputs_block("B조 경기 스코어", games_B)
                if games_other:
                    st.markdown("---")
                    render_score_inputs_block("기타 경기 스코어", games_other)
            else:
                # 🔥 전체 보기일 때: A/B 상관없이 전부 한 덩어리로
                all_games = games_A + games_B + games_other
                render_score_inputs_block("전체 경기 스코어", all_games)



        # 여기서부터는 섹션 3) 오늘 경기 삭제
        st.markdown("---")
        st.subheader("3. 오늘 경기 삭제")

        if st.button("이 날짜의 경기 기록 전체 삭제"):
            st.session_state.pending_delete = sel_date

        if st.session_state.pending_delete == sel_date:
            st.warning(f"{sel_date} 날짜의 모든 경기 기록을 정말 삭제하시겠습니까?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("네, 삭제합니다", key="confirm_delete_yes"):
                    if sel_date in sessions:
                        del sessions[sel_date]
                        st.session_state.sessions = sessions
                        save_sessions(sessions)
                    st.session_state.pending_delete = None
                    st.success("해당 날짜의 기록이 삭제되었습니다. 상단 날짜 선택을 다시 해 주세요.")
            with c2:
                if st.button("취소", key="confirm_delete_no"):
                    st.session_state.pending_delete = None
                    st.info("삭제가 취소되었습니다.")





# =========================================================
# 4) 개인별 통계
# =========================================================
with tab4:
    st.header("👤 개인별 통계")

    if not sessions:
        st.info("저장된 기록이 없습니다.")
    else:
        names = [p["name"] for p in roster]
        if not names:
            st.info("선수가 없습니다.")
        else:
            sel_player = st.selectbox("선수 선택", names)

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

            rec = {
                "G": 0, "W": 0, "D": 0, "L": 0, "points": 0,
                "score_for": 0, "score_against": 0
            }
            vs_opponent = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            with_partner = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_court_type = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_side = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_racket = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_ntrp = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_gender = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})
            by_hand = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})

            for d, idx, g in iter_games(sessions):
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

                rec["G"] += 1
                if in_t1:
                    my_score, opp_score = s1, s2
                else:
                    my_score, opp_score = s2, s1
                rec["score_for"] += my_score if my_score is not None else 0
                rec["score_against"] += opp_score if opp_score is not None else 0

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

                court_type = g["court_type"]
                by_court_type[court_type]["G"] += 1
                by_court_type[court_type][res_self] += 1

                sides = g["sides"]
                side = sides.get(sel_player)
                if side:
                    by_side[side]["G"] += 1
                    by_side[side][res_self] += 1

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

                for person in opponents:
                    m = roster_by_name.get(person, {})
                    by_racket[m.get("racket", "기타")]["G"] += 1
                    by_racket[m.get("racket", "기타")][res_self] += 1
                    ntrp_val = get_ntrp_value(m)
                    by_ntrp[f"{ntrp_val:.1f}"]["G"] += 1
                    by_ntrp[f"{ntrp_val:.1f}"][res_self] += 1
                    by_gender[m.get("gender", "남")]["G"] += 1
                    by_gender[m.get("gender", "남")][res_self] += 1
                    by_hand[m.get("hand", "오른손")]["G"] += 1
                    by_hand[m.get("hand", "오른손")][res_self] += 1

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

            st.markdown("---")
            cL, cR = st.columns(2)

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
                        ).reset_index(drop=True)      # 기존 인덱스 제거

                        df_vs.index = df_vs.index + 1  # 1부터 시작
                        df_vs.index.name = "순위"      # 인덱스 이름

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

# =========================================================
# 5) 월별 통계
# =========================================================
with tab5:
    st.header("📆 월별 통계")

    if not sessions:
        st.info("저장된 기록이 없습니다.")
    else:
        months = sorted({d[:7] for d in sessions.keys()})
        sel_month = st.selectbox("월 선택 (YYYY-MM)", months, index=len(months) - 1)

        month_games = []
        for d, idx, g in iter_games(sessions):
            if not d.startswith(sel_month):
                continue
            month_games.append((d, idx, g))

        if not month_games:
            st.info("이 달에 경기 기록이 없습니다.")
        else:
            # 1. 월간 선수 순위표
            st.subheader("1. 월간 선수 순위표")

            recs = defaultdict(lambda: {"days": set(), "G": 0, "W": 0, "D": 0, "L": 0, "points": 0})
            for d, idx, g in month_games:
                t1, t2 = g["t1"], g["t2"]
                s1, s2 = g["score1"], g["score2"]
                r = calc_result(s1, s2)
                if r is None:
                    continue
                players_all = t1 + t2
                for p in players_all:
                    recs[p]["days"].add(d)
                    recs[p]["G"] += 1

                if r == "W":
                    for p in t1:
                        recs[p]["W"] += 1
                        recs[p]["points"] += WIN_POINT
                    for p in t2:
                        recs[p]["L"] += 1
                        recs[p]["points"] += LOSE_POINT
                elif r == "L":
                    for p in t1:
                        recs[p]["L"] += 1
                        recs[p]["points"] += LOSE_POINT
                    for p in t2:
                        recs[p]["W"] += 1
                        recs[p]["points"] += WIN_POINT
                else:
                    for p in players_all:
                        recs[p]["D"] += 1
                        recs[p]["points"] += DRAW_POINT

            rows = []
            for name, r in recs.items():
                if r["G"] == 0:
                    continue
                win_rate = r["W"] / r["G"] * 100
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



            rank_df = pd.DataFrame(rows).sort_values(
                ["점수", "승률"], ascending=False
            ).reset_index(drop=True)  # 기존 인덱스 제거 후 0부터 새로 시작

            rank_df.index = rank_df.index + 1  # 1부터 시작하도록 조정
            rank_df.index.name = "순위"        # 인덱스 이름 지정

            rank_df["승률"] = rank_df["승률"].map(lambda x: f"{x:.1f}%")
            sty_rank = colorize_df_names(rank_df, roster_by_name, ["이름"])
            st.dataframe(sty_rank, use_container_width=True)



            # 2. 월 전체 경기 요약 (일별 + 일별 스코어 표)
            st.subheader("2. 월 전체 경기 요약 (일별)")

            days_sorted = sorted({d for d, idx, g in month_games})
            for d in days_sorted:
                st.markdown(f"**📅 {d}**")
                games_rows = []
                for d2, idx, g in month_games:
                    if d2 != d:
                        continue
                    games_rows.append(
                        {
                            "게임": idx,
                            "코트": g["court"],
                            "타입": g["type"],
                            "t1": g["t1"],
                            "t2": g["t2"],
                            "t1_score": g["score1"],
                            "t2_score": g["score2"],
                        }
                    )
                render_score_summary_table(games_rows, roster_by_name)

            # 3. 이 달의 BEST
            st.subheader("3. 이 달의 BEST (주손/라켓/연령대/성별)")

            def best_by_category(label, key_func):
                stats = defaultdict(lambda: {"G": 0, "W": 0})
                for d, idx, g in month_games:
                    t1, t2 = g["t1"], g["t2"]
                    s1, s2 = g["score1"], g["score2"]
                    r = calc_result(s1, s2)
                    if r is None:
                        continue
                    players_all = t1 + t2
                    for p in players_all:
                        meta = roster_by_name.get(p, {})
                        grp = key_func(meta)
                        stats[grp]["G"] += 1
                    if r == "W":
                        for p in t1:
                            meta = roster_by_name.get(p, {})
                            grp = key_func(meta)
                            stats[grp]["W"] += 1
                    elif r == "L":
                        for p in t2:
                            meta = roster_by_name.get(p, {})
                            grp = key_func(meta)
                            stats[grp]["W"] += 1
                best_grp = None
                best_rate = -1
                for grp, v in stats.items():
                    if v["G"] < 3:
                        continue
                    rate = v["W"] / v["G"]
                    if rate > best_rate:
                        best_rate = rate
                        best_grp = grp
                if best_grp is None:
                    return f"{label}: 데이터 부족"
                return f"{label}: {best_grp} (승률 {best_rate*100:.1f}%, 경기수 {stats[best_grp]['G']})"

            st.write(best_by_category("주손", lambda m: m.get("hand", "오른손")))
            st.write(best_by_category("라켓", lambda m: m.get("racket", "기타")))
            st.write(best_by_category("연령대", lambda m: m.get("age_group", "비밀")))
            st.write(best_by_category("성별", lambda m: m.get("gender", "남")))
