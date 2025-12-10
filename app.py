# -*- coding: utf-8 -*-
import json
import os
import random
import math
from datetime import date
from collections import defaultdict, Counter

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px


# ---------------------------------------------------------
# Streamlit 초기화 (✅ 딱 1번만)
# ---------------------------------------------------------
st.set_page_config(
    page_title="마리아 상암포바 도우미 MSA (Beta)",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ✅ 모바일에서만 selectbox 키보드 방지 (JS)
components.html(
    """
    <script>
    (function() {
      function isMobile() {
        return window.matchMedia("(max-width: 768px)").matches;
      }

      function patchSelectInputs() {
        if (!isMobile()) return;

        const inputs = document.querySelectorAll('div[data-baseweb="select"] input');
        inputs.forEach((inp) => {
          inp.setAttribute('readonly', 'true');
          inp.setAttribute('inputmode', 'none');
          inp.setAttribute('tabindex', '-1');
          inp.setAttribute('autocomplete', 'off');
          inp.setAttribute('autocorrect', 'off');
          inp.setAttribute('autocapitalize', 'off');
          inp.setAttribute('spellcheck', 'false');

          inp.addEventListener('focus', (e) => {
            e.target.blur();
          }, { passive: true });

          inp.style.pointerEvents = "none";
          inp.style.caretColor = "transparent";
        });
      }

      patchSelectInputs();

      const observer = new MutationObserver(() => {
        patchSelectInputs();
      });

      observer.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
    """,
    height=0,
)




# ---------- 라이트 모드 강제 스타일 ----------
st.markdown("""
<style>
/* 기본 컬러 & 라이트 모드 고정 */
:root {
    --background-color: #ffffff;
    --secondary-background-color: #ffffff;
    --primary-background-color: #ffffff;
    --text-color: #111827;
    --primary-text-color: #111827;
    --secondary-text-color: #4b5563;
    color-scheme: light;
}

/* 앱 전체 배경 & 글자색 */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #ffffff !important;
    color: #111827 !important;
}

/* 메인 컨테이너 – 모바일 상단 잘림 방지 */
main.block-container {
    padding-top: 3.5rem !important;
    margin-top: 0 !important;
}

/* 헤더 / 사이드바 */
header[data-testid="stHeader"],
section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    color: #111827 !important;
}

/* 공통 입력 요소 - 텍스트/셀렉트/숫자 */
input, textarea, select {
    background-color: #ffffff !important;
    color: #111827 !important;
}

/* Selectbox / Multiselect / NumberInput / TextInput 박스 */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div,
[data-testid="stNumberInput"] > div > div:first-child,
[data-testid="stTextInput"] > div > div,
div[role="combobox"],
div[role="spinbutton"],
[data-baseweb="select"],
[data-baseweb="input"] {
    background-color: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #e5e7eb !important;
}

/* 드롭다운 펼친 리스트 */
[data-baseweb="popover"],
[data-baseweb="menu"],
div[role="listbox"] {
    background-color: #ffffff !important;
    color: #111827 !important;
}

/* 옵션 하나하나 */
[data-baseweb="menu"] ul li {
    background-color: #ffffff !important;
    color: #111827 !important;
}
[data-baseweb="menu"] ul li:hover {
    background-color: #f3f4f6 !important;
}

/* 체크박스/라디오 라벨 텍스트 */
label[data-testid="stMarkdownContainer"],
span[data-baseweb="typo"],
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label {
    color: #111827 !important;
}

/* 체크박스/라디오 아이콘 주변 배경 */
[data-testid="stCheckbox"] > label > div:first-child,
[data-testid="stRadio"] > label > div:first-child {
    background-color: #ffffff !important;
}

/* 숫자 입력 + / - 버튼 */
[data-testid="stNumberInput"] button {
    background-color: #ffffff !important;
    color: #111827 !important;
    border-color: #e5e7eb !important;
}

/* 표(st.table) */
[data-testid="stTable"] table,
[data-testid="stTable"] table thead tr th,
[data-testid="stTable"] table tbody tr td {
    background-color: #ffffff !important;
    color: #111827 !important;
}

/* 표(st.dataframe) – 월간 선수 순위표 같은 것 */
[data-testid="stDataFrame"] div[role="grid"],
[data-testid="stDataFrame"] div[role="row"],
[data-testid="stDataFrame"] div[role="cell"],
[data-testid="stDataFrame"] div[role="columnheader"] {
    background-color: #ffffff !important;
    color: #111827 !important;
}

/* dataframe 헤더만 살짝 회색 */
[data-testid="stDataFrame"] div[role="columnheader"] {
    background-color: #f3f4f6 !important;
    font-weight: 600;
}

/* 기본 텍스트들 색 통일 */
[data-testid="stMarkdownContainer"],
p, span, li,
h1, h2, h3, h4, h5, h6 {
    color: #111827 !important;
}

/* 내가 만든 상단 탭 메뉴 텍스트(있다면) */
.tabs-container span,
.tabs-container p {
    color: #111827 !important;
}
</style>
""", unsafe_allow_html=True)





# ---------------------------------------------------------
# 기본 상수
# ---------------------------------------------------------
PLAYERS_FILE = "players.json"
SESSIONS_FILE = "sessions.json"

AGE_OPTIONS = ["비밀", "20대", "30대", "40대", "50대", "60대", "70대"]
RACKET_OPTIONS = ["모름", "기타", "윌슨", "요넥스", "헤드", "바볼랏", "던롭", "뵐클", "테크니파이버", "프린스"]
GENDER_OPTIONS = ["남", "여"]
HAND_OPTIONS = ["오른손", "왼손"]
GROUP_OPTIONS = ["미배정(게스트)", "A조", "B조"]
NTRP_OPTIONS = ["모름"] + [f"{x/2:.1f}" for x in range(2, 15)]  # 1.0~7.0
COURT_TYPES = ["인조잔디", "하드", "클레이"]
SIDE_OPTIONS = ["포(듀스)", "백(애드)"]
SCORE_OPTIONS = list(range(0, 7))
MBTI_OPTIONS = [
    "모름",
    "ISTJ", "ISFJ", "INFJ",
    "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ",
]



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
        "15:26",
        "39:4A",
        "7B:8C",
        "13:59",
        "24:6A",
        "7C:14",
        "8B:23",
        "67:9B",
        "58:AC",
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


def detect_score_warnings(day_data):
    """
    한 날짜(day_data)에 대해 점수 입력 실수 의심 목록을 만들어 준다.
    - 점수 미입력
    - 5:5가 아닌 동점(무승부) 점수
    """
    schedule = day_data.get("schedule", [])
    results = day_data.get("results", {})
    warnings = []

    for idx, (gtype, t1, t2, court) in enumerate(schedule, start=1):
        res = results.get(str(idx)) or results.get(idx) or {}
        s1 = res.get("t1")
        s2 = res.get("t2")

        # 1) 점수 미입력
        if s1 is None or s2 is None:
            warnings.append(f"{idx}번 경기: 점수가 비어 있어요.")
            continue

        # 2) 동점인데 5:5가 아닌 경우만 경고
        if s1 == s2 and s1 != 5:
            warnings.append(
                f"{idx}번 경기: {s1}:{s2} → 5:5가 아닌 무승부 점수예요. 다시 한 번 확인해 주세요."
            )

    return warnings


def build_daily_report(sel_date, day_data):
    """
    선택된 날짜(sel_date)에 대한 '오늘의 요약 리포트'용 문장 리스트 생성.
    - 출석 인원 / 점수 입력된 경기 수
    - 승점왕 / 공동 승점왕
    - 무패 선수
    - 상대를 0점으로 이긴 셧아웃 최다 선수
    """
    schedule = day_data.get("schedule", [])
    results = day_data.get("results", {})

    if not schedule:
        return []

    recs = defaultdict(
        lambda: {
            "G": 0,
            "W": 0,
            "D": 0,
            "L": 0,
            "points": 0,
            "score_for": 0,
            "score_against": 0,
        }
    )
    attendees = set()
    total_games = 0
    baker_counter = Counter()

    for idx, (gtype, t1, t2, court) in enumerate(schedule, start=1):
        res = results.get(str(idx)) or results.get(idx) or {}
        s1 = res.get("t1")
        s2 = res.get("t2")

        r = calc_result(s1, s2)
        if r is None:
            # 점수가 아직 없는 경기는 리포트 통계에서 제외
            continue

        total_games += 1
        players_all = t1 + t2
        attendees.update(players_all)

        for p in players_all:
            recs[p]["G"] += 1

        s1_val = s1 or 0
        s2_val = s2 or 0
        for p in t1:
            recs[p]["score_for"] += s1_val
            recs[p]["score_against"] += s2_val
        for p in t2:
            recs[p]["score_for"] += s2_val
            recs[p]["score_against"] += s1_val

        # 승/무/패 + 승점
        if r == "W":
            winners = t1
            losers = t2
        elif r == "L":
            winners = t2
            losers = t1
        else:
            winners = []
            losers = []

        for p in winners:
            recs[p]["W"] += 1
            recs[p]["points"] += WIN_POINT
        for p in losers:
            recs[p]["L"] += 1
            recs[p]["points"] += LOSE_POINT
        if r == "D":
            for p in players_all:
                recs[p]["D"] += 1
                recs[p]["points"] += DRAW_POINT

        # 셧아웃(상대 0점 승리) 집계
        if s1 is not None and s2 is not None:
            if s1 > 0 and s2 == 0:
                for p in t1:
                    baker_counter[p] += 1
            elif s2 > 0 and s1 == 0:
                for p in t2:
                    baker_counter[p] += 1

    if not attendees or total_games == 0:
        return []

    lines = []

    # 1) 기본 출석 / 경기 수
    lines.append(f"출석 인원 {len(attendees)}명, 점수 입력된 경기 {total_games}게임")

    # 2) 승점왕 / 공동 승점왕
    best_points = -1
    best_players = []
    for name, r in recs.items():
        if r["G"] == 0:
            continue
        if r["points"] > best_points:
            best_points = r["points"]
            best_players = [name]
        elif r["points"] == best_points:
            best_players.append(name)

    if best_players and best_points >= 0:
        if len(best_players) == 1:
            who = best_players[0]
            r = recs[who]
            lines.append(
                f"오늘의 승점왕: {who} (승점 {best_points}점, {r['W']}승 {r['D']}무 {r['L']}패)"
            )
        else:
            names_str = ", ".join(best_players)
            example = recs[best_players[0]]
            lines.append(
                f"오늘의 공동 승점왕: {names_str} (모두 승점 {best_points}점, 예: {example['W']}승 {example['D']}무 {example['L']}패)"
            )

    # 3) 무패 선수
    undefeated = [name for name, r in recs.items() if r["G"] > 0 and r["L"] == 0]
    if undefeated:
        names_str = ", ".join(undefeated)
        lines.append(f"오늘 무패 선수: {names_str}")

    # 4) 셧아웃 최다 선수 (상대 0점 승리)
    if baker_counter:
        max_b = max(baker_counter.values())
        best_bakers = [n for n, c in baker_counter.items() if c == max_b]
        names_str = ", ".join(best_bakers)
        lines.append(f"상대를 0점으로 이긴 셧아웃 경기 최다: {names_str} (총 {max_b}번)")

    return lines



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


def render_static_on_mobile(df_or_styler):
    mobile_mode = st.session_state.get("mobile_mode", False)

    if mobile_mode:
        # ✅ 모바일: 드래그/정렬/스크롤 인터랙션 없는 정적 렌더
        try:
            html = df_or_styler.to_html()
            st.markdown(html, unsafe_allow_html=True)
        except Exception:
            st.table(df_or_styler)
    else:
        # ✅ PC: 기존대로 인터랙티브
        st.dataframe(df_or_styler, use_container_width=True)

def is_mobile():
        return st.session_state.get("mobile_mode", False)


def smart_table(df_or_styler, *, use_container_width=True):
        """
        ✅ PC: 기존처럼 인터랙티브 dataframe
        ✅ 모바일: 열 드래그/정렬 등 인터랙션 없는 '고정 표'
        """
        if is_mobile():
                # 1) Styler면 HTML로 정적 렌더
                try:
                        html = df_or_styler.to_html()
                        st.markdown(html, unsafe_allow_html=True)
                        return
                except Exception:
                        pass

                # 2) 일반 DataFrame이면 정적 table
                try:
                        st.table(df_or_styler)
                except Exception:
                        # 혹시 모르니 마지막 안전망
                        st.write(df_or_styler)
        else:
                st.dataframe(df_or_styler, use_container_width=use_container_width)


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
            return "background-color:#cce8ff;color:#111111"
        elif g == "여":
            return "background-color:#ffd6d6;color:#111111"
        return ""

    styler = df.style
    for c in columns:
        if c in df.columns:
            styler = styler.applymap(style_name, subset=[c])
    return styler

def normalize_mixed_doubles_team(t1, t2, meta):
    """
    혼합복식인데 남남/여여로 나뉜 경우를
    같은 4명에서 M+F vs M+F로 재팀 구성.
    남2여2일 때만 적용.
    """
    four = list(t1) + list(t2)
    if len(four) != 4:
        return t1, t2

    males = [n for n in four if meta.get(n, {}).get("gender") == "남"]
    females = [n for n in four if meta.get(n, {}).get("gender") == "여"]

    if len(males) == 2 and len(females) == 2:
        new_t1 = (males[0], females[0])
        new_t2 = (males[1], females[1])
        return new_t1, new_t2

    return t1, t2

def fix_mixed_team_if_needed(t1, t2, meta):
    """
    혼합복식 후처리:
    - 같은 4명 기준
    - 남2/여2 조합인데
    - 현재 팀 구성이 (남남 vs 여여) 같은 '동성팀 vs 동성팀'이면
      -> (남+여) vs (남+여)로 재팀
    """
    four = list(t1) + list(t2)
    if len(four) != 4:
        return t1, t2

    genders = [meta.get(n, {}).get("gender") for n in four]
    if not all(g in ("남", "여") for g in genders):
        return t1, t2  # 성별 정보 불명확하면 패스

    males = [n for n in four if meta.get(n, {}).get("gender") == "남"]
    females = [n for n in four if meta.get(n, {}).get("gender") == "여"]

    # 혼복이 성립하는 2:2가 아니면 건드리지 않음
    if len(males) != 2 or len(females) != 2:
        return t1, t2

    def is_same_gender_team(team):
        g1 = meta.get(team[0], {}).get("gender")
        g2 = meta.get(team[1], {}).get("gender")
        return g1 == g2

    # 두 팀이 모두 동성팀이면 -> 혼복 형태로 재구성
    if is_same_gender_team(t1) and is_same_gender_team(t2):
        new_t1 = (males[0], females[0])
        new_t2 = (males[1], females[1])
        return new_t1, new_t2

    return t1, t2


def normalize_mixed_schedule(schedule, meta):
    """
    schedule 전체를 훑어서
    혼합복식에서 발생하는
    '남남 vs 여여' 케이스를 자동 교정
    """
    if not schedule:
        return schedule

    fixed = []
    for gtype_each, t1, t2, court in schedule:
        # 여기서 gtype 문자열 의존 안 함!
        nt1, nt2 = fix_mixed_team_if_needed(t1, t2, meta)
        fixed.append((gtype_each, nt1, nt2, court))

    return fixed



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
        "<span class='name-badge' style='"
        "background-color:{bg};"
        "padding:3px 8px;"
        "border-radius:6px;"
        "margin-right:4px;"
        "font-size:0.95rem;"
        "font-weight:600;"
        "color:#111111;"
        "'>{name}</span>"
    ).format(bg=bg, name=name)


def render_distribution_section(title, counter_dict, total_count, min_count):
    """
    카테고리별 인원/비율 + 도넛 파이 차트
    - min_count 보다 적은 인원인 항목은 숨김
    - 도넛 라벨: 'ENFP 6명 (23.1%)' 형식 (A 타입)
    """
    if not counter_dict or total_count == 0:
        return

    rows = []
    for key, cnt in counter_dict.items():
        label = key if key not in [None, ""] else "미입력"
        if cnt < min_count:
            continue
        pct = (cnt / total_count) * 100
        display_label = f"{label} {cnt}명 ({pct:.1f}%)"
        rows.append(
            {
                "항목": label,
                "인원": cnt,
                "비율(%)": pct,
                "표기": display_label,
            }
        )

    if not rows:
        st.info(f"{title}: 표시할 항목이 없습니다. (최소 인원 수 필터에 걸림)")
        return

    df = pd.DataFrame(rows).sort_values("인원", ascending=False).reset_index(drop=True)

    # 표
    df_display = df[["항목", "인원", "비율(%)"]].copy()
    df_display["비율(%)"] = df_display["비율(%)"].map(lambda x: f"{x:.1f}%")
    st.markdown(f"**{title}**")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # 🍩 도넛 파이 차트
    fig = px.pie(
        df,
        names="표기",      # ← 'ENFP 6명 (23.1%)' 같은 문구
        values="인원",
        hole=0.4,
    )
    fig.update_traces(
        textposition="inside",
        texttemplate="%{label}",   # 이미 라벨 안에 인원+퍼센트 포함
    )
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False,
        height=320,
    )

    st.plotly_chart(fig, use_container_width=True)



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



# -------------------------------------------
# 🎾 오늘의 테니스 운세 함수
# -------------------------------------------
def get_daily_fortune(sel_player):
    import random
    import datetime

    fortune_messages = [
    "(주손)잡이가 귀인이다.",
    "(주손)잡이를 조심하라.",
    "이름에 '(자음)' 이 들어가는 사람을 조심하라.",
    "이름에 '(자음)' 이 들어가는 사람이 귀인이다.",
    "(라켓)을(를) 든 사람이 귀인이다.",
    "(라켓)을(를) 든 사람을 조심하라.",
    "(연령대)가 귀인이다.",
    "(연령대)를 조심하라.",
    "애드(백)사이드가 복을 가져다 준다.",
    "듀스(포)사이드가 복을 가져다 준다.",
    "네트 플레이가 행운을 부른다. 과감하게 전진하라.",
    "심호흡이 오늘의 MVP다. 급하면 진다.",
    "볼 줍다가 인생의 기회를 주운다. 허리 조심해라.",
    "오늘의 라이벌은 가장 친한 사람이다. 조심하라.",
    "안경을 쓴 사람이 귀인이다.",
    "모자 쓴 사람과 팀이 되면 기회가 온다.",
    "너무 잘하면 시기받는다. 적당히 해라.",
    "로브는 오늘의 비책이다. 예상치 못한 순간 써라.",
    "물 많이 마시는 사람과 팀이 되면 복이 따른다.",
    "오늘은 '미안!'을 많이 해야 한다.",
    "실수해도 괜찮다. 어차피 모두가 기억 못 한다. 네가 져도 아무도 관심 없다.",
    "오늘 코트 라인은 네 편이 아니다. 걔는 그냥 선이다. 집착하지 마라.",
    "스매시 하려다 미스샷 나면 멘탈 나간다. 그냥 하지 마라.",
    "공 못 맞히면 핑계 준비해라. '바람 때문' 추천한다.",
    "아웃인지 인인지 애매하면 그냥 네 점수라고 우겨라. 운도 뻔뻔한 사람 편이다.",
    "랠리 길어지면 인생 생각하지 마라. 그냥 살아남아라.",
    "공이 네 얼굴을 향하면 회피하지 마라. 운명의 싸움이다.",
    "오늘은 코트에서 철학자 등장 가능. '테니스란 무엇인가' 생각 들면 졌다.",
    "내가 왜 여기 있는지 모르겠으면 물 마셔라. 정신 돌아온다.",
    "내가 실수하더라도 파트너 때문이라고 생각 해라.",
    "테니스 별거 없다. 그냥 치자.",
    "(프로선수) 빙의하는 날.",
    "운세에 의지하지마라.",

    "오늘 공은 네가 친 게 아니다. 공이 네 불안을 느끼고 도망간다. 잡아라.",
    "스트링 텐션이 네 멘탈 텐션보다 높다. 마음을 조여라.",
    "볼 줄 때 땅에 두 번 튕기면 안 된다. 오늘 운도 두 번 튕긴다.",
    "파트너가 너한테 말 안 하면 잘하고 있는 거다. 말 많이 하면 망한 거다.",
    "경기 중에 갑자기 평화가 온다면 그건 패배의 조짐이다.",
    "승리는 공이 아니라 선택에서 나온다. 오늘은 선택이 문제다.",
    "테니스는 인생이다. 걷어내는건 공이고 남는 건 너다.",
    "실수는 문제가 아니다. 반복이 문제다. 조심해라.",
    "포핸드는 태양, 백핸드는 달. 오늘 달이 뜬다.",
    "네트는 벽이 아니다. 질문이다. 답을 내라.",
    "라켓은 무기가 아니라 펜이다. 오늘 네 플레이로 이야기를 써라.",
    "네트는 경계가 아니다. 연결이다. 넘어가는 순간 세상이 넓어진다.",
    "스핀은 의심, 플랫은 확신. 오늘은 확신의 날이다.",
    "테니스는 상대와의 싸움이 아니라 어제의 나와의 싸움이다.",
    "볼의 속도는 마음의 속도를 닮는다. 조급하면 흔들린다.",
    "그림자처럼 따라오는 실수에 흔들리지 마라. 오늘의 너는 빛이다.",
    "승리는 외치는 것이 아니라, 조용히 만들어가는 것이다.",
    "코트 위에서 가장 소중한 공간은 라인이 아니라 네 발 아래다.",
    "오늘의 경기는 상대를 이기는 것이 아니라 자신을 이해하는 시간이다.",
    "흘려보낸 볼을 잡으려 하지 마라. 지나간 시간은 다시 오지 않는다.",
    "실수가 두려우면 발전도 없다. 오늘은 한 걸음 더 내딛는 날이다.",
    "공은 돌아온다. 기회도 돌아온다.",
    "바람이 변할 때 흔들리는 것은 공이 아니라 마음이다.",
    "라켓을 무겁게 들지 마라. 무거운 것은 생각이다.",
    "득점은 순간, 과정은 영원하다.",
    "포기는 실패가 아니다. 멈춤은 선택이다.",
    "라켓의 스윗스팟보다 중요한 것은 마음의 스윗스팟이다.",
    "볼이 아닌 순간을 맞이하라. 그 순간이 승리를 만든다.",
    "테니스는 반복의 예술이다. 어제의 스윙이 오늘의 음악이 된다.",
    "오늘의 경기에서 가장 중요한 것은 점수가 아니라 태도다.",
    "테니스는 혼자 하는 운동이지만, 함께 성장하는 여정이다.",
    "해질 때 가장 길어지는 그림자처럼, 오늘의 경험은 오래 남을 것이다.",
    "구름 뒤에 가려진 태양은 보이지 않아도 존재한다. 너의 가능성도 그렇다.",
    "밤하늘의 별처럼, 작은 순간들이 전체를 밝힌다.",
    "한 번 튄 공은 다시 돌아오지 않지만 울림은 남는다.",
    "어둠이 길게 느껴질수록 새벽은 가까워진다.",
    "공이 멀어질수록 시야를 넓혀라. 답은 가까이에 없다.",
    "멈춘 순간에도 시간은 달린다. 네 마음도 그렇게 달려라.",
    "충돌은 아픔이 아니라 방향 전환이다.",
    "너의 오늘은 코트 위 별자리다. 연결하면 의미가 된다.",

    ]

    chosung = list("ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅎ")
    rackets = ["윌슨", "요넥스", "헤드", "바볼랏", "던롭", "뵐클", "테크니파이버", "프린스"]
    ages = ["20대", "30대", "40대", "50대"]
    hands = ["오른손", "왼손"]
    proplayer = ["페더러","나달","조코비치","야닉시너","알카라즈","손흥민","메시","마이클조던","오타니","이학수","이재용","젠슨황","무하마드 알리","타이거 우즈","도널드 트럼프","일론 머스크","샤라포바"]


    today = datetime.date.today().strftime("%Y%m%d")
    random.seed(today + sel_player)

    fortune = random.choice(fortune_messages)
    fortune = (fortune.replace("(주손)", random.choice(hands))
                      .replace("(라켓)", random.choice(rackets))
                      .replace("(연령대)", random.choice(ages))
                      .replace("(프로선수)", random.choice(proplayer))
                      .replace("(자음)", random.choice(chosung)))

    return fortune


# ---------------------------------------------------------
# 경기 / 통계 유틸
# ---------------------------------------------------------
def iter_games(sessions, include_special=True):
    """
    include_special=False 이면 스페셜 매치 날짜 전체를 통계에서 제외.
    기존 호출(iter_games(sessions))도 그대로 동작하도록 기본값 True.
    """
    for d, day_data in sessions.items():
        if d == "전체":
            continue

        # ✋ 스페셜 매치 제외 옵션
        if (not include_special) and day_data.get("special_match", False):
            continue

        schedule = day_data.get("schedule", [])
        results = day_data.get("results", {})
        court_type = day_data.get("court_type", COURT_TYPES[0])

        for idx, (gtype, t1, t2, court) in enumerate(schedule, start=1):
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


def count_player_games(schedule):
    cnt = Counter()
    for g in schedule:
        # g 구조가 (gtype, team1, team2, court) 이런 형태라면:
        # 네 코드에 맞게 언팩 필요
        if len(g) == 4:
            _, t1, t2, _ = g
        else:
            # 혹시 (idx, gtype, t1, t2, court) 구조면
            _, _, t1, t2, _ = g

        for n in list(t1) + list(t2):
            cnt[n] += 1
    return cnt



def rebalance_mixed_gender_opportunity(schedule, players_selected, meta_for_match):
    """
    혼합복식에서 성별 인원 비대칭으로
    '기회가 적은 성별(대개 더 많은 쪽)'의 출전이
    특정 몇 명에게 몰리지 않도록
    같은 성별끼리만 교체해서 분배를 균등화하는 후처리.

    schedule item 형식:
      (gtype_each, t1, t2, court)
    """

    if not schedule:
        return schedule

    # 성별 분류 (게스트 포함 메타 기준)
    males = [p for p in players_selected if meta_for_match.get(p, {}).get("gender") == "남"]
    females = [p for p in players_selected if meta_for_match.get(p, {}).get("gender") == "여"]

    if not males or not females:
        return schedule

    num_games = len(schedule)

    # 혼합복식은 게임당 남2/여2 슬롯
    male_slots = 2 * num_games
    female_slots = 2 * num_games

    avg_m = male_slots / len(males)
    avg_f = female_slots / len(females)

    # 성비가 사실상 균형이면 굳이 손대지 않음
    if abs(avg_m - avg_f) < 1e-6:
        return schedule

    # 더 많은 성별이 평균이 더 낮아짐 → 그쪽을 "기회가 적은 성별"로 본다
    if avg_m < avg_f:
        target_group = males
        target_avg = avg_m
    else:
        target_group = females
        target_avg = avg_f

    # 목표 분배(예: avg=2.0이면 전원 2, avg=2.25면 일부 3, 나머지 2)
    low = math.floor(target_avg)
    high = math.ceil(target_avg)
    total_slots = 2 * num_games

    need_high = total_slots - (low * len(target_group))
    need_high = max(0, min(len(target_group), need_high))

    # 현재 출전 횟수
    counts = Counter()
    for (_, t1, t2, _) in schedule:
        for p in list(t1) + list(t2):
            counts[p] += 1

    # ✅ 핵심 수정:
    # "지금 덜 뛴 사람"에게 high를 주도록 오름차순 정렬
    sorted_group = sorted(
        target_group,
        key=lambda p: (counts.get(p, 0), str(p))
    )

    desired = {}
    for i, p in enumerate(sorted_group):
        desired[p] = high if i < need_high else low

    target_set = set(target_group)
    new_schedule = list(schedule)

    def replace_in_team(team, old, new):
        team = list(team)
        if old in team:
            idx = team.index(old)
            team[idx] = new
        return tuple(team)

    def replace_in_game(item, old, new):
        gtype_each, t1, t2, court = item
        if old in t1:
            t1n = replace_in_team(t1, old, new)
            t2n = tuple(t2)
        elif old in t2:
            t1n = tuple(t1)
            t2n = replace_in_team(t2, old, new)
        else:
            return item
        return (gtype_each, t1n, t2n, court)

    # 그리디하게 과다 → 과소를 같은 성별끼리 교체
    for _round in range(4):
        over = [p for p in target_group if counts.get(p, 0) > desired.get(p, low)]
        under = [p for p in target_group if counts.get(p, 0) < desired.get(p, low)]

        if not over or not under:
            break

        over.sort(key=lambda p: (-counts.get(p, 0), str(p)))
        under.sort(key=lambda p: (counts.get(p, 0), str(p)))

        improved = False

        for gi, item in enumerate(new_schedule):
            gtype_each, t1, t2, court = item
            players_in_game = set(list(t1) + list(t2))

            tg_in_game = [p for p in players_in_game if p in target_set]
            if len(tg_in_game) != 2:
                continue

            cand_old = next((p for p in tg_in_game if p in over), None)
            if not cand_old:
                continue

            cand_new = next((p for p in under if p not in players_in_game), None)
            if not cand_new:
                continue

            new_item = replace_in_game(item, cand_old, cand_new)

            # 중복 방지
            _, t1n, t2n, _ = new_item
            flat = list(t1n) + list(t2n)
            if len(flat) != len(set(flat)):
                continue

            # counts 업데이트
            counts[cand_old] -= 1
            counts[cand_new] += 1

            new_schedule[gi] = new_item
            improved = True
            break

        if not improved:
            break

    return new_schedule


def ensure_min_games(schedule, roster, min_games, gtype="복식"):
    """
    schedule에서 min_games 미만인 사람이 있으면
    많이 나온 사람과 교체해서 최소 횟수를 맞추는 간단 보정.
    """
    if min_games <= 0:
        return schedule

    # 안전장치: roster에 없는 이름이 schedule에 있으면 제외
    roster_set = set(roster)

    # 최대 200번 정도만 보정 시도
    for _ in range(200):
        cnt = count_player_games(schedule)

        # roster 기준으로만 판단
        under = [p for p in roster if cnt.get(p, 0) < min_games]
        if not under:
            break

        over = sorted(
            [p for p in roster if cnt.get(p, 0) > min_games],
            key=lambda x: cnt.get(x, 0),
            reverse=True
        )
        if not over:
            break

        need = under[0]
        give = over[0]

        # schedule에서 give가 등장하는 게임을 찾아 need로 교체
        replaced = False
        new_schedule = []

        for g in schedule:
            if len(g) == 4:
                gtype_each, t1, t2, court = g
                prefix = None
            else:
                idx, gtype_each, t1, t2, court = g
                prefix = idx

            t1 = list(t1)
            t2 = list(t2)

            # give가 있는 팀에서 need로 바꿔치기
            if not replaced:
                if give in t1 and need not in t1 and need not in t2:
                    t1[t1.index(give)] = need
                    replaced = True
                elif give in t2 and need not in t1 and need not in t2:
                    t2[t2.index(give)] = need
                    replaced = True

            # 복식/단식 인원수 유지
            t1 = tuple(t1)
            t2 = tuple(t2)

            if prefix is None:
                new_schedule.append((gtype_each, t1, t2, court))
            else:
                new_schedule.append((prefix, gtype_each, t1, t2, court))

        schedule = new_schedule

    return schedule




# ---------------------------------------------------------
# 게스트 판별 / 통계용 게스트 묶음 이름
# ---------------------------------------------------------
def is_guest_name(name, roster):
    member_set = {p.get("name") for p in roster}
    return name not in member_set


def guest_bucket(name, roster):
    return "게스트" if is_guest_name(name, roster) else name



def classify_game_group(players, roster_by_name, groups_snapshot=None):
    """
    게임에 참여한 사람들의 실력조를 기준으로
    - A조만 있으면 -> "A"
    - B조만 있으면 -> "B"
    - 그 외(섞여 있거나 미배정만 있는 경우) -> "other"

    groups_snapshot:
        날짜별로 저장해둔 {이름: 조} dict.
        있으면 이 값을 우선 사용하고, 없으면 현재 roster_by_name 기준으로 판단.
    """
    def get_group(p):
        # 1) 날짜별 스냅샷이 있으면 그걸 우선 사용
        if groups_snapshot and p in groups_snapshot:
            return groups_snapshot[p]
        # 2) 없으면 현재 선수 정보에서 가져오기
        return roster_by_name.get(p, {}).get("group", "미배정")

    groups = [get_group(p) for p in players]

    has_A = any(g == "A조" for g in groups)
    has_B = any(g == "B조" for g in groups)

    if has_A and not has_B:
        return "A"
    if has_B and not has_A:
        return "B"
    return "other"



from collections import defaultdict
import math
import random

def _count_games_in_schedule(schedule):
    counts = defaultdict(int)
    for gtype, t1, t2, court in schedule:
        for p in list(t1) + list(t2):
            counts[p] += 1
    return counts

def _mixed_team_invalid_count(schedule, meta_for_match):
    """
    혼합복식 규칙 위반 팀 수 카운트:
    - 각 팀이 (남+여) 조합이 아니면 위반 1
    """
    bad = 0
    for gtype, t1, t2, court in schedule:
        for team in (t1, t2):
            if len(team) != 2:
                continue
            g1 = meta_for_match.get(team[0], {}).get("gender")
            g2 = meta_for_match.get(team[1], {}).get("gender")
            if not g1 or not g2:
                continue
            if g1 == g2:
                bad += 1
    return bad

def _effective_min_guard_for_mixed(players, schedule_len, meta_for_match, min_guard):
    """
    혼복에서 성비 불균형일 때 '물리적으로 가능한 최소치'로 min_guard 자동 완화.
    혼복은 한 게임당 남자 슬롯 2, 여자 슬롯 2가 생김.
    """
    males = [p for p in players if meta_for_match.get(p, {}).get("gender") == "남"]
    females = [p for p in players if meta_for_match.get(p, {}).get("gender") == "여"]

    if not males or not females:
        return min_guard  # 혼복이지만 성별 정보가 부족하면 건드리지 않음

    total_male_slots = 2 * schedule_len
    total_female_slots = 2 * schedule_len

    # 성별별 평균적으로 가능한 상한/하한 느낌의 최소치
    male_avg = total_male_slots / max(1, len(males))
    female_avg = total_female_slots / max(1, len(females))

    # 최소 보장은 평균을 넘길 수 없음 → floor로 안전하게
    min_possible = int(math.floor(min(male_avg, female_avg)))

    # 기존 min_guard보다 낮아야만 완화
    return min(min_guard, max(1, min_possible))

def _score_schedule(
    players,
    schedule,
    meta_for_match,
    target_games,
    min_guard,
    mode_label,
):
    """
    점수는 '낮을수록 좋은 대진'

    목표 우선순위
    1) (핵심) 개인당 최소 보장 = target_games - 1 을 최우선으로 만족
       - 단, 물리적으로 불가능하면 가능한 수준까지 자동 완화
    2) 그 다음 전체적으로 "가장 공평한 분배"를 선택
       - 특히 혼복 성비 불균형일 때 소수 성별/다수 성별 모두
         2/2/2/2 같은 균형에 최대한 수렴
    3) 혼복 팀 규칙(남+여 짝) 위반은 아주 강하게 패널티
    """

    if not schedule:
        return 10**18

    counts = _count_games_in_schedule(schedule)

    # 모든 players에 대해 count가 없으면 0으로 보정
    for p in players:
        counts[p] = counts.get(p, 0)

    schedule_len = len(schedule)
    n_players = max(1, len(players))

    # -------------------------------------------------
    # 0) "최소 -1 우선" 기준 수립
    # -------------------------------------------------
    preferred_min = max(1, target_games - 1)

    # UI/호출부에서 min_guard가 들어오더라도,
    # 최소 -1을 기본 철학으로 삼되 더 큰 값을 원하면 존중
    base_min_guard = max(preferred_min, min_guard or 0)

    # -------------------------------------------------
    # 1) 물리적으로 가능한 최소치 계산 → 자동 완화
    # -------------------------------------------------
    # 복식은 게임당 4 슬롯, 단식은 2 슬롯
    is_doubles = "복식" in (mode_label or "")
    slots_per_game = 4 if is_doubles else 2
    total_slots = schedule_len * slots_per_game

    feasible_min_overall = total_slots // n_players  # 모두에게 균등하게 나눌 때 가능한 최소 바닥

    eff_min_guard = min(base_min_guard, feasible_min_overall)

    # 혼합복식이면 성별 슬롯 기준으로 한 번 더 안전장치
    gender_balance_pen = 0.0
    mixed_bad = 0

    if mode_label == "혼합복식 (남+여 짝)":
        mixed_bad = _mixed_team_invalid_count(schedule, meta_for_match)

        males = [p for p in players if meta_for_match.get(p, {}).get("gender") == "남"]
        females = [p for p in players if meta_for_match.get(p, {}).get("gender") == "여"]

        # 성별 정보가 양쪽 다 있을 때만 성별 기반 완화/균형 가동
        if males and females:
            # 혼복은 한 게임당 남 2, 여 2 슬롯
            total_male_slots = 2 * schedule_len
            total_female_slots = 2 * schedule_len

            feasible_m = total_male_slots // max(1, len(males))
            feasible_f = total_female_slots // max(1, len(females))

            eff_min_guard = min(eff_min_guard, feasible_m, feasible_f)

            # 성별별 이상적인 기대치(평균)
            male_expected = total_male_slots / len(males)
            female_expected = total_female_slots / len(females)

            # ✅ 성별 내부 분배 공평성 패널티
            # (abs도 괜찮지만, 여기선 제곱으로 더 강하게 밀어줌)
            for p in males:
                gender_balance_pen += (counts[p] - male_expected) ** 2
            for p in females:
                gender_balance_pen += (counts[p] - female_expected) ** 2

    # 안전장치: 최소 1은 유지
    eff_min_guard = max(1, int(eff_min_guard))

    # -------------------------------------------------
    # 2) 최소 보장 위반 페널티 (가장 큼)
    # -------------------------------------------------
    min_def = 0
    for p in players:
        if counts[p] < eff_min_guard:
            d = eff_min_guard - counts[p]
            min_def += d * d

    # -------------------------------------------------
    # 3) 목표 경기수 근접 (부족을 더 크게)
    # -------------------------------------------------
    under = 0
    over = 0
    for p in players:
        if counts[p] < target_games:
            d = target_games - counts[p]
            under += d * d
        elif counts[p] > target_games:
            d = counts[p] - target_games
            over += d * d

    # -------------------------------------------------
    # 4) "안 되면 가장 공평"을 위한 전체 공평성 페널티
    # -------------------------------------------------
    # 평균 대비 분산 + 최대/최소 격차를 동시에 잡아줌
    mean_cnt = total_slots / n_players
    var_pen = 0.0
    for p in players:
        var_pen += (counts[p] - mean_cnt) ** 2

    max_cnt = max(counts[p] for p in players) if players else 0
    min_cnt = min(counts[p] for p in players) if players else 0
    range_pen = (max_cnt - min_cnt) ** 2

    # -------------------------------------------------
    # 4-1) "1경기 방지" 하드 페널티
    # -------------------------------------------------
    # 현재 스케줄 길이에서
    # 모든 선수에게 최소 2경기씩 줄 수 있는 슬롯이 "물리적으로" 있는데도
    # 누군가 1경기면 매우 큰 패널티를 부여

    hard_low_pen = 0

    # 복식 기준 슬롯 계산
    is_doubles = "복식" in (mode_label or "")
    slots_per_game = 4 if is_doubles else 2
    total_slots = len(schedule) * slots_per_game
    n_players = max(1, len(players))

    # 최소 2경기씩 배분 가능 여부
    can_give_two_each = total_slots >= 2 * n_players

    if can_give_two_each:
        for p in players:
            if counts.get(p, 0) < 2:
                d = 2 - counts.get(p, 0)
                hard_low_pen += d * d


    # -------------------------------------------------
    # 5) 가중치
    # -------------------------------------------------
    W_MIN = 160          # 최소 보장 최우선 (조금 더 강화)
    W_UNDER = 22
    W_OVER = 7
    W_MIXED_BAD = 220    # 혼복 팀 위반 매우 강하게
    W_GENDER_BAL = 12    # ✅ 성별 불균형 상황에서 3경기/1경기 같은 분열을 강하게 억제
    W_VAR = 10           # ✅ 전체 분배 공평성
    W_RANGE = 35         # ✅ 4 vs 1 같은 극단 케이스 방지
    W_HARD_LOW = 500  # 1경기 방지용 매우 강한 패널티

    score = 0
    score += W_MIN * min_def
    score += W_UNDER * under
    score += W_OVER * over
    score += W_MIXED_BAD * mixed_bad
    score += W_GENDER_BAL * gender_balance_pen
    score += W_VAR * var_pen
    score += W_RANGE * range_pen
    score += W_HARD_LOW * hard_low_pen

    return score


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
            f"<th style='border:1px solid #ddd;padding:4px;text-align:center;background-color:#f5f5f5;color:#111111;'>{col}</th>"
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
            f"<td style='border:1px solid #ddd;padding:4px;text-align:center;color:#111111;'>{idx}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:center;color:#111111;'>{court}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;text-align:center;color:#111111;'>{gtype}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;'>{t1_html}</td>"
            f"<td style='{s1_style}'>{'' if s1 is None else s1}</td>"
            f"<td style='{s2_style}'>{'' if s2 is None else s2}</td>"
            f"<td style='border:1px solid #ddd;padding:4px;'>{t2_html}</td>"
            "</tr>"
        )

    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)

def section_card(title: str, emoji: str = "📌"):
    st.markdown(
        f"""
        <div style="
            margin-top: 0.8rem;
            margin-bottom: 0.4rem;
            padding: 0.55rem 0.9rem;
            border-radius: 0.75rem;
            background: linear-gradient(135deg, #ffffff 0%, #f9fafb 60%, #eef2ff 100%);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        ">
            <span style="font-size: 1.05rem;">{emoji}</span>
            <span style="font-weight: 700; font-size: 1.02rem; color:#111827;">
                {title}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def subsection_badge(title: str, emoji: str = "🔹"):
    st.markdown(
        f"""
        <div style="margin-top:0.6rem; margin-bottom:0.25rem;">
            <span style="
                display:inline-flex;
                align-items:center;
                gap:0.35rem;
                padding:0.25rem 0.8rem;
                border-radius:999px;
                background-color:#eef2ff;
                color:#1f2937;
                font-size:0.85rem;
                font-weight:600;
            ">
                <span>{emoji}</span>
                <span>{title}</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def mini_subtitle_card(title: str, description: str = "", emoji: str = "📝"):
    st.markdown(
        f"""
        <div style="
            margin-top: 0.35rem;
            margin-bottom: 0.35rem;
            padding: 0.45rem 0.75rem;
            border-radius: 0.7rem;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            display: flex;
            flex-direction: column;
            gap: 0.18rem;
        ">
            <div style="display:flex;align-items:center;gap:0.35rem;">
                <span style="font-size:0.95rem;">{emoji}</span>
                <span style="font-weight:600;font-size:0.92rem;color:#111827;">
                    {title}
                </span>
            </div>
            {f'<div style="font-size:0.83rem;color:#4b5563;line-height:1.3;">{description}</div>' if description else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


MOBILE_LANDSCAPE = """
<style>

/* 📱 모바일 가로 화면 전용 */
@media screen and (max-width: 768px) and (orientation: landscape) {

    /* 전체 컨테이너 여백 최소화 */
    .block-container {
        padding-left: 0.35rem !important;
        padding-right: 0.35rem !important;
        padding-top: 0.4rem !important;
        padding-bottom: 0.4rem !important;
    }

    /* 제목 폰트 더 축소 */
    h1 { font-size: 1.05rem !important; margin-bottom: 0.35rem !important; }
    h2 { font-size: 0.95rem !important; }
    h3, h4 { font-size: 0.85rem !important; }

    /* 일반 텍스트 */
    p, span, label, div {
        font-size: 0.78rem !important;
    }

    /* Selectbox / TextInput 높이 줄이기 */
    div[data-baseweb="select"] {
        font-size: 0.78rem !important;
        min-height: 1.65rem !important;
        padding-top: 0.05rem !important;
        padding-bottom: 0.05rem !important;
    }

    /* 점수 Select 글씨 */
    div.stSelectbox > label {
        font-size: 0.72rem !important;
    }

    /* 🔽 표 데이터프레임 폰트 & 패딩 축소 */
    [data-testid="stDataFrame"] table {
        font-size: 0.65rem !important;
    }

    [data-testid="stDataFrame"] table td,
    [data-testid="stDataFrame"] table th {
        padding: 2px 3px !important;
    }

    [data-testid="stDataFrame"] div[role="row"] {
        min-height: 14px !important;
    }

    /* 버튼 */
    div[data-testid="stButton"] > button {
        font-size: 0.80rem !important;
        padding-top: 0.50rem !important;
        padding-bottom: 0.50rem !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
    }

    /* 멀티셀렉트 박스 */
    .stMultiSelect div[data-baseweb="tag"] {
        font-size: 0.70rem !important;
        padding: 1px 4px !important;
    }
}
</style>
"""
st.markdown(MOBILE_LANDSCAPE, unsafe_allow_html=True)



BUTTON_CSS = """
<style>
div[data-testid="stButton"] > button {
    background-color: #5fcdb2 !important;  /* 보라 */
    color: #ffffff !important;             /* 흰 글씨 */
    font-weight: 600 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 0 !important;
    transition: all 0.12s ease-out;
}
div[data-testid="stButton"] > button:hover {
    filter: brightness(1.06) !important;
    transform: translateY(-1px);
}
@media (max-width: 768px) {
    div[data-testid="stButton"] > button {
        font-size: 0.95rem !important;
        padding-top: 0.6rem !important;
        padding-bottom: 0.6rem !important;
    }
}
</style>
"""
st.markdown(BUTTON_CSS, unsafe_allow_html=True)




# 🔽 모바일 폰에서 여백/폰트/탭 간격 줄이는 CSS + 이름 뱃지 색상 고정
MOBILE_CSS = """
<style>
/* 전체 패딩 줄이기 */
.block-container {
    padding-top: 0.8rem;
    padding-bottom: 1.5rem;
    padding-left: 0.9rem;
    padding-right: 0.9rem;
}

/* 이름 뱃지 기본 색상(다크모드에서도 검은 글씨 유지) */
.name-badge {
    color: #111111 !important;
    white-space: nowrap;
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

    /* 모바일에서 이름 뱃지 살짝 작게 */
    .name-badge {
        font-size: 0.8rem !important;
        padding: 2px 6px !important;
    }
}
</style>
"""

st.markdown("""
<style>
.mbti-tag {
    display:inline-block;
    background:#f4e8ff;     /* 파스텔 보라 */
    color:#6d28d9;          /* 진한 보라 텍스트 */
    border-radius:8px;
    padding:2px 7px;
    font-size:0.73rem;
    font-weight:600;
    margin-left:4px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(MOBILE_CSS, unsafe_allow_html=True)

if "roster" not in st.session_state:
    st.session_state.roster = load_players()
if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions()

if "current_order" not in st.session_state:
    st.session_state.current_order = []
if "shuffle_count" not in st.session_state:
    st.session_state.shuffle_count = 0


import pandas as pd
import streamlit as st


def _safe_df_for_styler(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    df2 = df2.reset_index(drop=True)

    cols = list(df2.columns)
    seen = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
    df2.columns = new_cols

    return df2


def colorize_df_names_hybrid(
    df: pd.DataFrame,
    roster_by_name: dict,
    name_cols=None,
    male_bg="#dbeafe",
    female_bg="#fee2e2",
):
    name_cols = name_cols or ["이름"]
    mobile_mode = st.session_state.get("mobile_mode", False)

    MUTED_WORDS = {"비밀", "모름"}
    MUTED_TEXT = "#9ca3af"
    MUTED_BG = "#f3f4f6"   # 아주 연한 회색

    base = df.copy()

    # ---------------------------
    # 모바일: HTML span 기반
    # ---------------------------
    if mobile_mode:
        # 1) 전체 셀에서 비밀/모름 회색 텍스트+배경 처리
        for col in base.columns:
            def _muted_html(v):
                s = str(v)
                if s in MUTED_WORDS:
                    return (
                        f"<span style='"
                        f"color:{MUTED_TEXT};"
                        f"background:{MUTED_BG};"
                        f"padding:0.04rem 0.22rem;"
                        f"border-radius:0.35rem;"
                        f"font-weight:600;"
                        f"display:inline-block;"
                        f"'>"
                        f"{s}"
                        f"</span>"
                    )
                return v
            base[col] = base[col].apply(_muted_html)

        # 2) 이름 컬럼은 성별 배경 뱃지 적용
        for col in name_cols:
            if col not in base.columns:
                continue

            def _name_html(n):
                raw = str(n)
                meta = roster_by_name.get(raw, {})
                g = meta.get("gender")

                bg = male_bg if g == "남" else female_bg if g == "여" else "#f3f4f6"
                return (
                    "<span style='"
                    "display:inline-block;"
                    "padding:0.08rem 0.35rem;"
                    "border-radius:0.45rem;"
                    f"background:{bg};"
                    "font-weight:800;"
                    "'>"
                    f"{raw}"
                    "</span>"
                )

            base[col] = base[col].apply(_name_html)

        return base

    # ---------------------------
    # PC: Styler
    # ---------------------------
    safe = _safe_df_for_styler(base)

    def _apply_name_bg(row):
        styles = []
        for c in safe.columns:
            if c in name_cols:
                n = row.get(c, "")
                meta = roster_by_name.get(str(n), {})
                g = meta.get("gender")
                bg = male_bg if g == "남" else female_bg if g == "여" else "#f3f4f6"
                styles.append(
                    "font-weight:800;"
                    f"background-color:{bg};"
                    "border-radius:8px;"
                )
            else:
                styles.append("")
        return styles

    sty = safe.style.apply(_apply_name_bg, axis=1)

    # ✅ 비밀/모름 글씨+배경 처리
    def _muted_style(v):
        if str(v) in MUTED_WORDS:
            return (
                f"color:{MUTED_TEXT};"
                f"background-color:{MUTED_BG};"
                "font-weight:600;"
            )
        return ""

    sty = sty.applymap(_muted_style)

    return sty



def smart_table_hybrid(df_or_styler):
    """
    ✅ 모바일/PC 자동 분기 테이블 출력

    - 모바일: HTML 테이블 (폰트/줄바꿈 제어)
    - PC: st.dataframe (인터랙티브)
    """
    mobile_mode = st.session_state.get("mobile_mode", False)

    # ---------------------------
    # 모바일: HTML 테이블
    # ---------------------------
    if mobile_mode:
        st.markdown(
            """
            <style>
            .mobile-table-wrap table {
                width: 100% !important;
                border-collapse: collapse !important;
                table-layout: auto !important;
                font-size: 0.78rem !important;
            }
            .mobile-table-wrap th,
            .mobile-table-wrap td {
                padding: 0.22rem 0.35rem !important;
                white-space: nowrap !important;
                word-break: keep-all !important;
                vertical-align: middle !important;
            }
            .mobile-table-wrap thead th {
                font-weight: 800 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Styler가 넘어오면 data를 뽑아 HTML 변환
        if hasattr(df_or_styler, "data"):
            df_m = df_or_styler.data.copy()
        elif isinstance(df_or_styler, pd.DataFrame):
            df_m = df_or_styler.copy()
        else:
            df_m = pd.DataFrame(df_or_styler)

        # ✅ HTML span이 들어갈 수 있으니 escape=False
        html = df_m.to_html(index=False, escape=False)

        st.markdown(
            f"""
            <div class="mobile-table-wrap">
                {html}
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # ---------------------------
    # PC: dataframe
    # ---------------------------
    if hasattr(df_or_styler, "data"):
        st.dataframe(df_or_styler, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_or_styler, use_container_width=True, hide_index=True)




# ---------------------------------------------------------
# [PATCH] 한울 AA 시드 state
# ---------------------------------------------------------
if "aa_seed_enabled" not in st.session_state:
    st.session_state.aa_seed_enabled = False

if "aa_seed_players" not in st.session_state:
    st.session_state.aa_seed_players = []

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

if "min_games_guard" not in st.session_state:
    st.session_state.min_games_guard = 1


roster = st.session_state.roster
sessions = st.session_state.sessions
roster_by_name = {p["name"]: p for p in roster}

st.title("🎾 마리아 상암포바 도우미 MSA (Beta)")

# 📱 폰에서 볼 때 ON 해두면 A/B조 나란히 레이아웃을 세로로 바꿔줌
mobile_mode = st.checkbox(
    "📱 모바일 최적화 모드",
    value=True,
    help="핸드폰으로 볼 때 켜 두는 걸 추천!"
)

st.session_state["mobile_mode"] = mobile_mode


MOBILE_SCORE_ROW_CSS = """
<style>
/* 모바일에서 점수/이름 줄을 한 줄로 고정 */
@media (max-width: 768px) {

    /* 한 게임(점수 줄) 컨테이너 */
    .score-row {
        display: flex;
        flex-wrap: nowrap;
        align-items: center;
        gap: 0.25rem;
        width: 100%;
    }

    /* score-row 안에 있는 각 column(이름, 점수, VS ...) */
    .score-row [data-testid="column"] {
        flex: 0 0 auto !important;      /* 줄 바꿈 방지 */
        padding-left: 0.1rem !important;
        padding-right: 0.1rem !important;
    }

    /* 드롭다운(점수) 사이즈 조금 줄이기 */
    .score-row [data-baseweb="select"] {
        min-width: 3.0rem;
        font-size: 0.78rem;
        min-height: 1.9rem;
    }

    /* 이름 배지 너무 크지 않게 */
    .score-row .name-badge,
    .score-row span {
        font-size: 0.8rem;
    }
}

</style>
"""
st.markdown(MOBILE_SCORE_ROW_CSS, unsafe_allow_html=True)


tab3, tab5, tab4, tab1, tab2 = st.tabs(
    ["📋 경기 기록 / 통계", "📆 월별 통계", "👤 개인별 통계", "🧾 선수 정보 관리", "🎾 오늘 경기 세션"]
)

with tab1:
    st.header("🧾 선수 정보 관리")
    st.subheader("등록된 선수 목록")

    if roster:
        df = pd.DataFrame(roster)
        df_disp = df.copy()

        # ✅ NTRP 표시용 컬럼
        def format_ntrp(v):
            if v is None or pd.isna(v):
                return "모름"
            try:
                return f"{float(v):.1f}"
            except Exception:
                return "모름"

        df_disp["NTRP"] = df_disp["ntrp"].apply(format_ntrp)

        # 원본 ntrp 숨김
        if "ntrp" in df_disp.columns:
            df_disp = df_disp.drop(columns=["ntrp"])

        # 기본 헤더 한글화
        df_disp = df_disp.rename(
            columns={
                "name": "이름",
                "gender": "성별",
                "hand": "주손",
                "age_group": "나이대",
                "racket": "라켓",
                "group": "실력조",
                "mbti": "MBTI",
            }
        )

        # ✅ 모바일 헤더 축약 + 표시 컬럼 정리
        if mobile_mode:
            df_disp = df_disp.rename(
                columns={
                    "나이대": "나이",
                    "실력조": "조",
                }
            )

            keep_cols = ["이름", "나이", "성별", "주손", "라켓", "조", "MBTI", "NTRP"]
            keep_cols = [c for c in keep_cols if c in df_disp.columns]
            df_disp = df_disp[keep_cols]

        roster_by_name = {p["name"]: p for p in roster}

        for grp in ["A조", "B조", "미배정"]:
            col_grp = "실력조" if not mobile_mode else "조"
            if col_grp not in df_disp.columns:
                continue

            sub = df_disp[df_disp[col_grp] == grp]
            if sub.empty:
                continue

            st.markdown(f"■ {grp}")

            styled_or_df = colorize_df_names_hybrid(
                sub,
                roster_by_name,
                name_cols=["이름"],
            )

            smart_table_hybrid(styled_or_df)

    else:
        st.info("등록된 선수가 없습니다.")


    # -----------------------------------------------------
    # 2) 선수 통계 요약 + 분포 다이어그램
    # -----------------------------------------------------
    if roster:
        st.markdown("---")
        st.subheader("📊 선수 통계 요약")

        total_players = len(roster)

        # 카운트들 계산
        age_counter = Counter(p.get("age_group", "비밀") for p in roster)
        gender_counter = Counter(p.get("gender", "남") for p in roster)
        hand_counter = Counter(p.get("hand", "오른손") for p in roster)
        racket_counter = Counter(p.get("racket", "기타") for p in roster)
        ntrp_counter = Counter(
            "모름" if p.get("ntrp") is None else f"{p.get('ntrp'):.1f}"
            for p in roster
        )

        # MBTI
        mbti_counter_raw = Counter(p.get("mbti", "모름") for p in roster)
        # "모름" 은 통계에서 제외
        mbti_counter = Counter({
            k: v for k, v in mbti_counter_raw.items()
            if k not in (None, "", "모름")
        })


        # 텍스트 요약
        st.markdown(f"- 전체 인원: **{total_players}명**")

        # 나이대 예: 10대 2명 / 20대 3명 / ...
        age_text = " / ".join(f"{k} {v}명" for k, v in age_counter.items())
        st.markdown(f"- 나이대: {age_text}")

        # 성별
        st.markdown(
            f"- 성별: 남자 {gender_counter.get('남', 0)}명, "
            f"여자 {gender_counter.get('여', 0)}명"
        )

        # 주손
        st.markdown(
            f"- 주손: 오른손 {hand_counter.get('오른손', 0)}명, "
            f"왼손 {hand_counter.get('왼손', 0)}명"
        )

        # 라켓 브랜드
        racket_text = " / ".join(f"{k} {v}명" for k, v in racket_counter.items())
        st.markdown(f"- 라켓 브랜드: {racket_text}")

        # NTRP
        ntrp_text = " / ".join(f"NTRP {k}: {v}명" for k, v in ntrp_counter.items())
        st.markdown(f"- NTRP 분포: {ntrp_text}")

        if mbti_counter:
            mbti_text = " / ".join(f"{k} {v}명" for k, v in mbti_counter.items())
        else:
            mbti_text = "집계할 MBTI가 없습니다."
        st.markdown(f"- MBTI 분포: {mbti_text}")



        with st.expander("📈 항목별 분포 다이어그램 (각 항목 100% 기준) 🔽 아래로 내려보세요.", expanded=False):

            # 🔧 필터 / 옵션 (슬라이더 + 어떤 항목 볼지 선택)
            with st.expander("필터 / 옵션 열기", expanded=False):
                min_count = st.slider(
                    "표시할 최소 인원 수",
                    min_value=0,
                    max_value=total_players,
                    value=1,
                    help="이 값보다 적은 인원인 항목은 숨겨집니다.",
                )

                section_options = ["나이대", "성별", "주손", "라켓", "NTRP", "MBTI"]
                selected_sections = st.multiselect(
                    "보고 싶은 항목 선택",
                    section_options,
                    default=section_options,
                )

            # 어떤 분포를 쓸지 묶어두기
            dist_items = []
            if "나이대" in selected_sections:
                dist_items.append(("나이대별 인원 분포", age_counter))
            if "성별" in selected_sections:
                dist_items.append(("성별 인원 분포", gender_counter))
            if "주손" in selected_sections:
                dist_items.append(("주손(오른손/왼손) 분포", hand_counter))
            if "라켓" in selected_sections:
                dist_items.append(("라켓 브랜드별 분포", racket_counter))
            if "NTRP" in selected_sections:
                dist_items.append(("NTRP 레벨별 분포", ntrp_counter))
            if "MBTI" in selected_sections:
                dist_items.append(("MBTI 분포", mbti_counter))


            # 📱 모바일 모드면 1열, PC면 2열씩 배치
            if mobile_mode:
                for title, counter in dist_items:
                    render_distribution_section(
                        title, counter, total_players, min_count
                    )
                    st.markdown("---")
            else:
                for i in range(0, len(dist_items), 2):
                    col1, col2 = st.columns(2)
                    title1, counter1 = dist_items[i]
                    with col1:
                        render_distribution_section(
                            title1, counter1, total_players, min_count
                        )

                    if i + 1 < len(dist_items):
                        title2, counter2 = dist_items[i + 1]
                        with col2:
                            render_distribution_section(
                                title2, counter2, total_players, min_count
                            )




    # -----------------------------------------------------
    # 1) 선수 정보 수정 / 삭제
    # -----------------------------------------------------
    st.markdown("---")
    st.subheader("선수 정보 수정 / 삭제")

    names = sorted([p["name"] for p in roster], key=lambda x: x)
    if names:
        sel_edit = st.selectbox(
            "수정할 선수 선택",
            ["선택 안함"] + names
        )

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
                    key=f"edit_gender_{sel_edit}",   # ✅ 고유 key
                )
                e_hand = st.selectbox(
                    "주손 (수정)",
                    HAND_OPTIONS,
                    index=get_index_or_default(
                        HAND_OPTIONS, player.get("hand", "오른손"), 0
                    ),
                    key=f"edit_hand_{sel_edit}",     # ✅ 고유 key
                )

                cur_ntrp = player.get("ntrp")
                cur_ntrp_str = "모름" if cur_ntrp is None else f"{cur_ntrp:.1f}"
                e_ntrp_str = st.selectbox(
                    "NTRP (수정)",
                    NTRP_OPTIONS,
                    index=get_index_or_default(NTRP_OPTIONS, cur_ntrp_str, 0),
                    key=f"edit_ntrp_{sel_edit}",     # ✅ 고유 key
                )

                # MBTI (수정)
                cur_mbti = player.get("mbti", "모름")
                e_mbti = st.selectbox(
                    "MBTI (수정)",
                    MBTI_OPTIONS,
                    index=get_index_or_default(MBTI_OPTIONS, cur_mbti, 0),
                    key=f"edit_mbti_{sel_edit}",     # ✅ 고유 key
                )



            cb1, cb2 = st.columns(2)



            with cb1:
                st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
                if st.button("수정 저장", use_container_width=True, key="btn_edit_save"):
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
                            "mbti": e_mbti,
                        }
                    )

                    save_players(roster)
                    st.session_state.roster = roster  # ← 메모리 즉시 반영
                    st.success("선수 정보가 수정되었습니다!")

                    st.rerun()  # ← 즉시 화면 재렌더링 (새로고침 없이 반영)

                st.markdown("</div>", unsafe_allow_html=True)





            if "pending_delete" not in st.session_state:
                st.session_state.pending_delete = None

            with cb2:
                st.markdown('<div class="main-danger-btn">', unsafe_allow_html=True)
                if st.button("🗑 이 선수 삭제", use_container_width=True, key="btn_edit_del"):
                    st.session_state.pending_delete = sel_edit
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.pending_delete:
                st.markdown("---")
                st.warning(
                    f"⚠️ 정말 **{st.session_state.pending_delete}** 선수를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다."
                )

                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("❌ 취소", use_container_width=True, key="cancel_delete"):
                        st.session_state.pending_delete = None

                with cc2:
                    if st.button("🗑 네, 삭제합니다", use_container_width=True, key="confirm_delete"):
                        target = st.session_state.pending_delete
                        st.session_state.roster = [
                            p for p in roster if p["name"] != target
                        ]
                        roster = st.session_state.roster
                        save_players(roster)
                        st.session_state.pending_delete = None
                        st.success(f"'{target}' 선수 삭제 완료! (새로고침 필요)")
            # ---------------------------------------------------------------



    else:
        st.info("수정할 선수가 없습니다.")

    # -----------------------------------------------------
    # 2) 새 선수 추가 (기본은 접혀 있음)
    # -----------------------------------------------------
    st.markdown("---")
    with st.expander("➕ 새 선수 추가", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("이름", key="new_name")
            new_age = st.selectbox("나이대", AGE_OPTIONS, index=0, key="new_age")
            new_racket = st.selectbox("라켓", RACKET_OPTIONS, index=0, key="new_racket")
            new_group = st.selectbox("실력조 (A/B/C)", GROUP_OPTIONS, index=0, key="new_group")
        with c2:
            new_gender = st.selectbox("성별", GENDER_OPTIONS, index=0, key="new_gender")
            new_hand = st.selectbox("주로 쓰는 손", HAND_OPTIONS, index=0, key="new_hand")
            ntrp_str = st.selectbox("NTRP (실력)", NTRP_OPTIONS, index=0, key="new_ntrp")

            new_mbti = st.selectbox(
                "MBTI",
                MBTI_OPTIONS,
                index=0,
                key="new_mbti",
            )



        st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
        add_clicked = st.button("선수 추가", use_container_width=True, key="btn_add_player")
        st.markdown("</div>", unsafe_allow_html=True)

        if add_clicked:
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
    	            "mbti": new_mbti,
                }
                roster.append(player)
                st.session_state.roster = roster
                save_players(roster)
                st.success(f"'{new_name}' 선수 추가 완료!")





import random
from collections import defaultdict

# ---------------------------------------------------------
# ✅ 스케줄 평가 유틸
# ---------------------------------------------------------
def count_games_by_player(schedule):
    counts = defaultdict(int)
    for gt, t1, t2, court in schedule:
        for p in list(t1) + list(t2):
            counts[p] += 1
    return counts


def team_gender(team, meta):
    genders = []
    for n in team:
        g = meta.get(n, {}).get("gender")
        genders.append(g)
    return genders


def is_mixed_team(team, meta):
    genders = team_gender(team, meta)
    if len(genders) < 2:
        return True  # 정보 부족이면 일단 통과
    # 남/여 정확히 1명씩일 때만 "정상 혼복 팀"
    return ("남" in genders) and ("여" in genders) and (genders.count("남") == 1) and (genders.count("여") == 1)


def mixed_violation_count(schedule, meta):
    bad = 0
    for gt, t1, t2, court in schedule:
        # 복식에서만 의미 있음
        if len(t1) == 2 and len(t2) == 2:
            if not is_mixed_team(t1, meta):
                bad += 1
            if not is_mixed_team(t2, meta):
                bad += 1
    return bad


# ---------------------------------------------------------
# ✅ 핵심 스코어 함수
# ---------------------------------------------------------
def score_schedule(
    schedule,
    players,
    target_games,
    min_guard,
    meta,
    mode_label=None,
):
    """
    점수는 '클수록 좋음'
    """

    if not schedule:
        return -10**9

    counts = count_games_by_player(schedule)

    # 참가자 중 누락된 사람이 있으면 0으로 처리
    for p in players:
        counts.setdefault(p, 0)

    values = [counts[p] for p in players]
    min_cnt = min(values)
    max_cnt = max(values)
    spread = max_cnt - min_cnt

    # ---------------------------
    # 1) ✅ 최소 보장 점수
    # ---------------------------
    below = sum(1 for v in values if v < min_guard)
    # 최소 보장 미달은 아주 강하게 패널티
    guard_score = -1000 * below

    # ---------------------------
    # 2) ✅ 저게임 수 우선 가중치
    #    - 최소값이 높을수록 보너스
    #    - 편차가 커질수록 패널티
    # ---------------------------
    low_games_priority = (min_cnt * 60) - (spread * 25)

    # ---------------------------
    # 3) ✅ 목표치 근접도(부드러운 보정)
    # ---------------------------
    # target에 가까울수록 좋게. (너무 과한 벌점은 금지)
    dist_sum = sum(abs(v - target_games) for v in values)
    target_score = -6 * dist_sum

    # ---------------------------
    # 4) ✅ 혼합복식 위반 패널티
    # ---------------------------
    mixed_score = 0
    if mode_label == "혼합복식 (남+여 짝)":
        bad = mixed_violation_count(schedule, meta)
        # 팀 단위 위반이므로 상당히 크게 때림
        mixed_score = -180 * bad

    # ---------------------------
    # ✅ 전체 합
    # ---------------------------
    total = guard_score + low_games_priority + target_score + mixed_score
    return total


# ---------------------------------------------------------
# ✅ 단일 풀 탐색 버전
# ---------------------------------------------------------
def try_build_best_schedule(
    players,
    build_fn,
    target_games,
    min_guard,
    tries=80,
    meta=None,
    mode_label=None,
):
    """
    build_fn은 'schedule을 반환하는 함수'
    - 이 함수 내부에서 '각 try마다 후보를 만들고'
      score_schedule로 최고점을 고름
    """
    meta = meta or {}

    best_schedule = []
    best_score = -10**9
    best_ok = False

    for _ in range(tries):
        cand = build_fn()
        sc = score_schedule(
            cand,
            players=players,
            target_games=target_games,
            min_guard=min_guard,
            meta=meta,
            mode_label=mode_label,
        )

        if sc > best_score:
            best_score = sc
            best_schedule = cand
            best_ok = True

    # 최소 보장 만족 여부 재확인(표시용)
    ok_min_guard = True
    if best_schedule:
        counts = count_games_by_player(best_schedule)
        for p in players:
            if counts.get(p, 0) < min_guard:
                ok_min_guard = False
                break
    else:
        ok_min_guard = False

    return best_schedule, ok_min_guard


# ---------------------------------------------------------
# ✅ A/B조 분리 + "한쪽만 손해" 완화 버전
# ---------------------------------------------------------
def try_build_best_schedule_grouped(
    group_players,
    build_fn_by_group,
    target_games,
    min_guard,
    tries=60,
    meta=None,
    mode_label=None,
):
    """
    group_players = {"A조":[...], "B조":[...]}
    build_fn_by_group = {"A조": fnA, "B조": fnB}

    - 매 try마다 A/B 각각 후보를 만들고
    - 조별 점수 + '조 간 불균형 패널티' 로 최종 선택
    """
    meta = meta or {}

    best_schedule = []
    best_score = -10**9

    for _ in range(tries):
        schedules_each = {}
        scores_each = {}
        ok_each = {}

        # 1) 조별 후보 생성 + 조별 점수
        for grp_label, plist in group_players.items():
            fn = build_fn_by_group.get(grp_label)
            if not fn or not plist:
                schedules_each[grp_label] = []
                scores_each[grp_label] = -10**9
                ok_each[grp_label] = False
                continue

            cand = fn()
            sc = score_schedule(
                cand,
                players=plist,
                target_games=target_games,
                min_guard=min_guard,
                meta=meta,
                mode_label=mode_label,
            )

            schedules_each[grp_label] = cand
            scores_each[grp_label] = sc

            # 최소 보장 만족 빠른 체크
            counts = count_games_by_player(cand) if cand else {}
            ok_each[grp_label] = all(counts.get(p, 0) >= min_guard for p in plist)

        # 2) 조 점수 합산 + "한쪽만 크게 손해" 패널티
        score_A = scores_each.get("A조", 0)
        score_B = scores_each.get("B조", 0)

        imbalance_penalty = -0.25 * abs(score_A - score_B)

        combined_score = score_A + score_B + imbalance_penalty

        # 3) 합쳐서 선택
        combined_schedule = []
        for grp_label in ["A조", "B조"]:
            combined_schedule.extend(schedules_each.get(grp_label, []))

        if combined_score > best_score:
            best_score = combined_score
            best_schedule = combined_schedule

    # 최종 최소 보장 만족 여부(표시용)
    ok_min_guard = True
    for grp_label, plist in group_players.items():
        if not plist:
            continue
        counts = count_games_by_player(best_schedule)
        if any(counts.get(p, 0) < min_guard for p in plist):
            ok_min_guard = False
            break

    return best_schedule, ok_min_guard


with tab2:
    section_card("오늘 경기 세션", "🎾")

    # =========================================================
    # 한울 AA 시드 슬롯 정의 (이미 있으면 그대로 두고)
    # 없으면 이걸 사용
    # =========================================================
    AA_SEED_SLOTS = {
        6:  ["1", "3"],
        7:  ["1", "5"],
        8:  ["1", "7"],
        9:  ["1", "4", "8"],
        10: ["1", "8", "A"],
        11: ["1", "5", "8", "9"],
        12: ["1", "6", "9", "C"],
        13: ["1", "4", "6", "B"],
        14: ["2", "5", "8", "C"],
        15: ["1", "4", "5", "A", "D"],
        16: ["1", "6", "B", "G", "7", "A"],
    }

    # =========================================================
    # [PATCH] 한울 AA 시드 적용 함수 (부분 시드 허용)
    # - 최대 seed_count까지 선택 가능
    # - 그 이하도 정상 진행
    # =========================================================
    def apply_aa_seeds(players_selected, base_order, seed_enabled, seed_players):
        n = len(players_selected)
        slots = AA_SEED_SLOTS.get(n, [])

        # 시드 미사용/슬롯 없음이면 그대로
        if not seed_enabled or not slots:
            return base_order if base_order else players_selected

        # base_order 안전장치
        if not base_order or set(base_order) != set(players_selected):
            base_order = players_selected.copy()

        # 슬롯 라벨 -> 인덱스 변환
        slot_index_map = {
            "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6, "8": 7, "9": 8,
            "A": 9, "B": 10, "C": 11, "D": 12, "E": 13, "F": 14, "G": 15,
        }

        # 참석자 안에 있는 시드만, 최대 슬롯 수까지만
        seed_players = [p for p in (seed_players or []) if p in players_selected]
        seed_players = seed_players[:len(slots)]  # ✅ "최대"만 제한

        # 시드로 뽑힌 사람 제외한 나머지 순서
        remaining = [p for p in base_order if p not in seed_players]

        # 최종 자리 리스트
        final = [None] * n

        # ✅ 선택된 시드만 앞에서부터 슬롯에 배정
        for i, p in enumerate(seed_players):
            slot_label = slots[i]
            idx = slot_index_map.get(slot_label, None)
            if idx is not None and idx < n:
                final[idx] = p

        # ✅ 빈 칸은 remaining 순서대로 채움
        r_i = 0
        for i in range(n):
            if final[i] is None:
                if r_i < len(remaining):
                    final[i] = remaining[r_i]
                    r_i += 1

        # 혹시 None이 남는 이상 케이스 방지
        final = [p for p in final if p is not None]
        if len(final) != n:
            # 마지막 안전장치
            final = seed_players + [p for p in base_order if p not in seed_players]
            final = final[:n]

        return final

    # ---------------------------------------------------------
    # 0. 저장할 날짜 선택
    # ---------------------------------------------------------
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


    # ---------------------------------------------------------
    # 1. 참가자 선택 + 게스트 + 스페셜 매치
    # ---------------------------------------------------------
    st.subheader("2. 참가자 선택")

    # 🔹 기본 state 세팅
    if "current_order" not in st.session_state:
        st.session_state.current_order = []
    if "shuffle_count" not in st.session_state:
        st.session_state.shuffle_count = 0

    # ✅ 분리된 토글 state
    if "guest_mode" not in st.session_state:
        st.session_state.guest_mode = False
    if "special_match" not in st.session_state:
        st.session_state.special_match = False
    if "guest_list" not in st.session_state:
        st.session_state.guest_list = []

    guest_list = st.session_state.guest_list

    # 기존 멤버 이름 목록 (players.json 기반)
    names_all_members = [p["name"] for p in roster]

    # ✅ 체크박스 상호 배타 처리용 콜백
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


    # ✅ 참가자 multiselect / (게스트추가 + 스페셜매치) 2줄 토글
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

        # state 동기화(안전장치)
        st.session_state.guest_mode = bool(guest_mode_ui)
        st.session_state.special_match = bool(special_match_ui)

    # 게스트 기능 활성 여부
    guest_enabled = bool(st.session_state.guest_mode or st.session_state.special_match)


    # ---------------------------------------------------------
    # 게스트 입력 UI
    # ---------------------------------------------------------
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
                게스트는 오늘 날짜에만 사용되며, 회원 명단(players.json)에는 저장되지 않습니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

        GUEST_GROUP_OPTIONS = ["미배정", "A조", "B조"]

        # ✅ 칸 너비 조정(버튼 2줄 방지)
        gc1, gc2, gc3, gc4, gc5 = st.columns([2.5, 1.0, 1.2, 1.1, 1.2])

        with gc1:
            guest_name = st.text_input(
                "게스트 이름",
                key="guest_name_input",
                placeholder="예: 홍길동",
            )
        with gc2:
            guest_gender = st.selectbox(
                "성별",
                ["남", "여"],
                index=0,
                key="guest_gender_input",
            )
        with gc3:
            guest_group = st.selectbox(
                "조",
                GUEST_GROUP_OPTIONS,
                index=0,
                key="guest_group_input",
            )
        with gc4:
            guest_ntrp = st.selectbox(
                "NTRP",
                NTRP_OPTIONS,
                index=0,
                key="guest_ntrp_input",
            )
        with gc5:
            st.markdown("<div style='margin-top:1.65rem;'></div>", unsafe_allow_html=True)
            add_guest_clicked = st.button(
                "게스트 추가",
                use_container_width=True,
                key="btn_add_guest_once",
            )

        if add_guest_clicked:
            name_clean = (guest_name or "").strip()

            if not name_clean:
                st.warning("게스트 이름을 입력해 주세요.")
            else:
                if any(g.get("name") == name_clean for g in guest_list):
                    st.warning("이미 같은 이름의 게스트가 있습니다.")
                else:
                    guest_list.append(
                        {
                            "name": name_clean,
                            "gender": guest_gender,
                            "group": guest_group,
                            "ntrp": guest_ntrp,
                        }
                    )
                    st.session_state.guest_list = guest_list
                    st.session_state["guest_add_msg"] = f"게스트 '{name_clean}' 추가되었습니다."

        if st.session_state.get("guest_add_msg"):
            st.success(st.session_state["guest_add_msg"])
            st.session_state["guest_add_msg"] = None



        def safe_rerun():
                if hasattr(st, "rerun"):
                        st.rerun()
                elif hasattr(st, "experimental_rerun"):
                        st.experimental_rerun()

        # 오늘 게스트 목록 표시 + 삭제
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



    # ---------------------------------------------------------
    # ① 멤버 + ② 게스트 이름 합치기
    # ---------------------------------------------------------
    guest_names = [g["name"] for g in guest_list] if guest_enabled else []
    names_all = names_all_members + guest_names
    names_sorted = sorted(names_all, key=lambda n: n)

    # 실제 multiselect
    with col_ms:
        sel_players = st.multiselect("오늘 참가 선수들", names_sorted, default=[])

    # ✅ “대진에 실제로 들어가는 인원”
    if guest_enabled:
        players_for_today = sorted(set(sel_players) | set(guest_names), key=lambda n: n)
    else:
        players_for_today = sel_players

    st.write(f"현재 참가 인원: {len(players_for_today)}명")


    # ---------------------------------------------------------
    # 게스트 정보를 roster_by_name 에 임시 주입
    # ---------------------------------------------------------
    if guest_enabled:
        for g in guest_list:
            nm = g["name"]
            roster_by_name[nm] = {
                "name": nm,
                "gender": g.get("gender", "남"),
                "ntrp": g.get("ntrp", "모름"),
                "group": g.get("group", "미배정"),
                "age_group": "비밀",
                "racket": "모름",
                "hand": "오른손",
                "mbti": "모름",
                "is_guest": True,
            }


    # ---------------------------------------------------------
    # 순서 초기화
    # ---------------------------------------------------------
    if players_for_today:
        prev = st.session_state.current_order
        if (not prev) or (set(prev) != set(players_for_today)):
            st.session_state.current_order = players_for_today.copy()
            st.session_state.shuffle_count = 0
    else:
        st.session_state.current_order = []
        st.session_state.shuffle_count = 0

    current_order = st.session_state.current_order


    # ---------------------------------------------------------
    # 2. 순서 정하기
    # ---------------------------------------------------------
    st.subheader("3. 순서 정하기")

    order_mode_ui = st.radio(
        "순서 방식",
        ["랜덤 섞기", "수동 입력"],
        horizontal=True,
        key="order_mode_radio",
    )

    # ✅ 생성부에서 쓰기 좋게 통일 저장
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
                st.warning("한 명 이상 입력해 줘.")
            elif set(lines) != set(players_for_today):
                st.error("선택된 참가자와 이름 목록이 일치하지 않아.")
            else:
                st.session_state.current_order = lines
                current_order = lines
                st.success("수동 순서가 적용됐어.")


    # ---------------------------------------------------------
    # 현재 순서 표시 (전체 / 조별 분리)
    # ---------------------------------------------------------
    if current_order:
        default_view = st.session_state.get("order_view_mode", "전체")
        default_idx = 0 if default_view == "전체" else 1

        view_mode = st.radio(
            "순서 표시 방식",
            ["전체", "조별 분리 (A/B조)"],
            horizontal=True,
            index=default_idx,
            key="order_view_mode_radio",
        )
        st.session_state.order_view_mode = view_mode

        if view_mode == "전체":
            st.write("현재 순서:")
            for i, n in enumerate(current_order, start=1):
                badge = render_name_badge(n, roster_by_name)
                st.markdown(f"{i}. {badge}", unsafe_allow_html=True)
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


    # ---------------------------------------------------------
    # 3. 대진 설정
    # ---------------------------------------------------------
    st.subheader("4. 대진 설정")

    # 3-1. 게임 타입
    gtype = st.radio("게임 타입", ["복식", "단식"], horizontal=True)

    mode_label = None
    singles_mode = None

    # 3-2. 모드 선택
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
        )

        # ✅ 핵심 1) AA 판정: 완전일치 금지, 포함 검사로 안전화
        is_aa_mode = ("한울 AA" in str(mode_label))

    else:
        singles_mode = st.selectbox(
            "단식 대진 방식",
            ["랜덤 단식", "동성 단식", "혼합 단식"],
        )
        is_aa_mode = False

    # 3-3. 개인당 경기 수 / 코트 수
    cg1, cg2 = st.columns(2)
    with cg1:
        if gtype == "복식" and is_aa_mode:
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
                disabled=True,
            )
        else:
            court_count = st.number_input(
                "사용 코트 수", min_value=1, max_value=6, value=2, step=1
            )

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

    # 조별 분리 보기면 자동으로 조별 매칭 적용
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

    # ---------------------------------------------------------
    # 4. 대진표 생성 / 미리보기
    # ---------------------------------------------------------
    st.subheader("5. 대진표 생성 / 미리보기")

    st.markdown('<div class="main-primary-btn">', unsafe_allow_html=True)
    generate_clicked = st.button(
        "대진표 생성하기",
        use_container_width=True,
        key="gen_btn"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if generate_clicked:

        if len(current_order) < (4 if gtype == "복식" else 2):
            st.error("인원이 부족합니다.")
        else:
            players_selected = current_order.copy()
            schedule = []
            st.session_state.target_games = None  # 초기화


            # ✅ 조별 분리 선택값을 AA/일반 모드 공통 스위치로 동기화
            group_only = (
                st.session_state.get("order_view_mode", "전체")
                == "조별 분리 (A/B조)"
            )


            # -------------------------------------------------
            # 4-1. ✅ 한울 AA 모드
            # -------------------------------------------------
            if gtype == "복식" and is_aa_mode:

                # 현재 보기 모드
                view_mode_for_schedule = st.session_state.get(
                    "order_view_mode", "전체"
                )

                # ✅ 핵심 2) 조별 분리일 때 A/B 인원 점검
                if view_mode_for_schedule == "조별 분리 (A/B조)":
                    a_list = [
                        p for p in players_selected
                        if roster_by_name.get(p, {}).get("group", "미배정") == "A조"
                    ]
                    b_list = [
                        p for p in players_selected
                        if roster_by_name.get(p, {}).get("group", "미배정") == "B조"
                    ]

                    # A/B 둘 다 5 미만이면 → 전체 AA로 자동 전환
                    if len(a_list) < 5 and len(b_list) < 5:
                        view_mode_for_schedule = "전체"

                # -------------------------
                # (1) 조별 AA
                # -------------------------
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

                        sub_schedule = build_hanul_aa_schedule(grp_list, court_count)
                        combined.extend(sub_schedule)

                    schedule = combined

                # -------------------------
                # (2) 전체 AA
                # -------------------------
                else:
                    n = len(players_selected)
                    if n < 5 or n > 16:
                        st.error(
                            f"한울 AA 방식은 5명 이상 16명 이하에서만 사용할 수 있습니다. "
                            f"(현재 인원: {n}명)"
                        )
                    else:
                        schedule = build_hanul_aa_schedule(players_selected, court_count)

                st.session_state.today_schedule = schedule
                st.session_state.target_games = 4

                if not schedule:
                    st.warning("조건에 맞는 한울 AA 대진을 만들지 못했습니다.")
                else:
                    st.success("한울 AA 방식 대진표 생성 완료! (개인당 4게임 고정)")

            # -------------------------------------------------
            # 4-2. 일반 모드
            # -------------------------------------------------
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
                            st.warning(f"{grp_label} 인원이 부족하여 대진을 만들 수 없습니다.")
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
                                    mode_map.get(mode_label, "랜덤"),
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
                                mode_map.get(mode_label, "랜덤"),
                                use_ntrp,
                                False,
                                roster_by_name,
                            )
                        else:
                            schedule = build_singles_schedule(
                                players_selected,
                                max_games,
                                court_count,
                                mode_map_s.get(singles_mode, "랜덤"),
                                use_ntrp,
                                False,
                                roster_by_name,
                            )

                    st.session_state.today_schedule = schedule
                    st.session_state.target_games = max_games

                    if not schedule:
                        st.warning("조건에 맞는 대진을 만들지 못했습니다.")
                    else:
                        st.success("대진표 생성 완료!")


    # ---------------------------------------------------------
    # 생성된 대진표 표시
    # ---------------------------------------------------------
    schedule = st.session_state.get("today_schedule", [])

    if schedule:
        view_mode_for_schedule = st.session_state.get("order_view_mode", "전체")

        if view_mode_for_schedule == "조별 분리 (A/B조)":
            games_A, games_B, games_other = [], [], []

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
                for local_idx, (orig_idx, gtype_each, t1, t2, court) in enumerate(games, start=1):
                    t1_html = "".join(render_name_badge(n, roster_by_name) for n in t1)
                    t2_html = "".join(render_name_badge(n, roster_by_name) for n in t2)
                    st.markdown(
                        f"게임 {local_idx} (코트 {court}) [{gtype_each}] : "
                        f"{t1_html} <b>vs</b> {t2_html}",
                        unsafe_allow_html=True,
                    )

            render_game_list("A조 대진표", games_A)
            render_game_list("B조 대진표", games_B)
            if games_other:
                render_game_list("조가 섞인 경기 / 기타", games_other)

        else:
            for idx, (gtype_each, t1, t2, court) in enumerate(schedule, start=1):
                t1_html = "".join(render_name_badge(n, roster_by_name) for n in t1)
                t2_html = "".join(render_name_badge(n, roster_by_name) for n in t2)
                st.markdown(
                    f"게임 {idx} (코트 {court}) [{gtype_each}] : "
                    f"{t1_html} <b>vs</b> {t2_html}",
                    unsafe_allow_html=True,
                )

    # ---------------------------------------------------------
    # 5. 대진표 저장
    # ---------------------------------------------------------
    if schedule:
        target_date = st.session_state.get("save_target_date", date.today().strftime("%Y-%m-%d"))

        st.markdown(
            f"""
            <div style="
                margin: 0.5rem 0 0.8rem 0;
                padding: 0.9rem 1.1rem;
                border-radius: 12px;
                background-color: #fff7f7;
                border: 1px solid #fecaca;
                font-size: 0.9rem;
                line-height: 1.5;
            ">
                ✅ 현재 선택된 날짜: <b>{target_date}</b><br/>
                이 날짜에 지금 대진표를 저장합니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "show_overwrite_confirm" not in st.session_state:
            st.session_state["show_overwrite_confirm"] = False

        if st.button("💾 이 날짜로 대진 저장 / 덮어쓰기", use_container_width=True):
            sessions = st.session_state.get("sessions", {})
            day_data = sessions.get(target_date, {})

            # ✅ 1) 잠금 상태면 덮어쓰기/저장 진입 차단 + 안내
            if day_data.get("scores_locked", False):
                st.error("🔒 이 날짜는 잠금 상태라 대진을 덮어쓸 수 없어. 잠금을 먼저 해제하세요.")
            
            else:
                if "schedule" in day_data:
                    st.session_state["show_overwrite_confirm"] = True
                else:
                    day_data.setdefault("results", {})
                    order_mode_for_scores = st.session_state.get("order_view_mode", "전체")
                    day_data["score_view_mode"] = (
                        "전체" if order_mode_for_scores == "전체" else "조별 보기 (A/B조)"
                    )
                    day_data["score_view_lock"] = (order_mode_for_scores == "전체")

                    # 🔒 이 날짜 기준 선수-조 스냅샷 저장
                    group_snapshot = {}
                    for gtype_each, t1, t2, court in schedule:
                        for name in t1 + t2:
                            if name not in group_snapshot:
                                group_snapshot[name] = roster_by_name.get(
                                    name, {}
                                ).get("group", "미배정")
                    day_data["groups_snapshot"] = group_snapshot

                    day_data["schedule"] = schedule
                    sessions[target_date] = day_data
                    st.session_state.sessions = sessions
                    save_sessions(sessions)
                    st.success(f"{target_date} 대진표가 저장되었습니다.")


        if st.session_state.get("show_overwrite_confirm", False):
            st.markdown(
                f"""
                <div style="
                    margin-top: 0.9rem;
                    padding: 0.9rem 1.1rem;
                    border-radius: 12px;
                    background-color: #fff1f2;
                    border: 1px solid #fecaca;
                    font-size: 0.9rem;
                    line-height: 1.5;
                ">
                    선택하신 날짜 <b>{target_date}</b>에 이미 대진 기록이 있습니다.<br/>
                    정말로 새 대진표로 <b>덮어씌우시겠습니까?</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_ok, col_cancel = st.columns(2)

            with col_ok:
                st.markdown('<div class="main-danger-btn">', unsafe_allow_html=True)
                overwrite_yes = st.button(
                    "네, 덮어쓸게요",
                    use_container_width=True,
                    key="btn_overwrite_yes",
                )
                st.markdown("</div>", unsafe_allow_html=True)

            with col_cancel:
                overwrite_no = st.button(
                    "아니요, 취소",
                    use_container_width=True,
                    key="btn_overwrite_no",
                )

            if overwrite_yes:
                sessions = st.session_state.get("sessions", {})
                day_data = sessions.get(target_date, {})

                # ✅ 2) 최종 덮어쓰기 직전에도 잠금 체크
                if day_data.get("scores_locked", False):
                    st.error("🔒 잠금 상태입니다. 덮어쓰기 전에 잠금을 먼저 해제하세요.")
                    st.session_state["show_overwrite_confirm"] = False

                else:
                    day_data.setdefault("results", {})

                    order_mode_for_scores = st.session_state.get("order_view_mode", "전체")
                    day_data["score_view_mode"] = (
                        "전체" if order_mode_for_scores == "전체" else "조별 보기 (A/B조)"
                    )
                    day_data["score_view_lock"] = (order_mode_for_scores == "전체")

                    # 🔒 덮어쓰기 시에도, 이 시점의 조를 스냅샷으로 저장
                    group_snapshot = {}
                    for gtype_each, t1, t2, court in schedule:
                        for name in t1 + t2:
                            if name not in group_snapshot:
                                group_snapshot[name] = roster_by_name.get(
                                    name, {}
                                ).get("group", "미배정")
                    day_data["groups_snapshot"] = group_snapshot

                    day_data["schedule"] = schedule
                    sessions[target_date] = day_data
                    st.session_state.sessions = sessions
                    save_sessions(sessions)

                    st.session_state["show_overwrite_confirm"] = False
                    st.success(f"{target_date} 대진표가 덮어쓰기 저장되었습니다.")


            if overwrite_no:
                st.session_state["show_overwrite_confirm"] = False
                st.info("덮어쓰기를 취소했습니다.")

    else:
        st.info("생성된 대진표가 없습니다.")


    # ---------------------------------------------------------
    # 6. 개인당 경기 수
    # ---------------------------------------------------------
    if schedule:
        st.markdown("---")
        st.subheader("6. 개인당 경기 수 (이번 대진 기준)")

        target_games = st.session_state.get("target_games", None)
        min_guard = st.session_state.get("min_games_guard", None)

        game_counts = defaultdict(int)
        for gt, t1, t2, court in schedule:
            for p in t1 + t2:
                game_counts[p] += 1

        for name in sorted(game_counts.keys()):
            badge = render_name_badge(name, roster_by_name)
            st.markdown(f"{badge} : {game_counts[name]} 경기", unsafe_allow_html=True)

        if min_guard is not None:
            if any(cnt < min_guard for cnt in game_counts.values()):
                st.warning(
                    f"⚠ 일부 선수는 최소 보장({min_guard}경기)을 채우지 못했습니다. "
                    "조건을 조정하거나 다시 생성해 주세요."
                )
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
            # 👉 '전체 / 조별 보기' 선택
            #    - lock_view=True면 전체로 고정하고 라디오를 안 보여줌
            if lock_view:
                view_mode_scores = "전체"
            else:
                # 날짜에 저장된 기본값(saved_view)에 맞춰 기본 선택 인덱스 정하기
                if saved_view == "전체":
                    default_index = 1   # ["조별 보기 (A/B조)", "전체"] 중 "전체"
                else:
                    # None 이거나 "조별 보기 (A/B조)"면 조별 보기 기본
                    default_index = 0

                view_mode_scores = st.radio(
                    "표시 방식",
                    ["조별 보기 (A/B조)", "전체"],
                    horizontal=True,
                    key="tab3_view_mode_scores",
                    index=default_index,
                )

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
                        gender = info.get("gender") or info.get("성별")

                        if gender == "여":
                            bg = "#fee2e2"   # 연한 빨강
                            color = "#b91c1c"
                        elif gender == "남":
                            bg = "#dbeafe"   # 연한 파랑
                            color = "#1d4ed8"
                        else:
                            bg = "#e5e7eb"
                            color = "#374151"

                        html_parts.append(
                            f"<span class='name-badge' style='display:inline-block;"
                            f"padding:3px 10px;border-radius:999px;background:{bg};"
                            f"color:{color};font-size:0.78rem;margin-right:4px;'>{p}</span>"
                        )
                    return " ".join(html_parts)

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
            by_mbti = defaultdict(lambda: {"G": 0, "W": 0, "D": 0, "L": 0})


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

                        # ✔ 통계에서 제외할 값 필터
                        # 나이: "비밀" (지금은 나이 표는 없지만 혹시 확장용)
                        if label == "연령대" and k == "비밀":
                            continue
                        # 라켓: "모름" 제외
                        if label == "라켓" and k == "모름":
                            continue
                        # 실력조: "미배정" 제외 (향후 그룹 통계용)
                        if label == "실력조" and k == "미배정":
                            continue
                        # NTRP: "모름" / "0.0" 같은 placeholder 제외
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
            # 1) 이 달의 게임 모으기
            #    - 스페셜 매치 날짜는 제외
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

                # 전체 / A / B 각각 기록
                def make_recs():
                    return defaultdict(
                        lambda: {
                            "days": set(),
                            "G": 0,
                            "W": 0,
                            "D": 0,
                            "L": 0,
                            "points": 0,
                            "score_for": 0,
                            "score_against": 0,
                        }
                    )

                recs_all = make_recs()
                recs_A = make_recs()
                recs_B = make_recs()

                partners_by_player = defaultdict(set)

                # ---------------------------------------------------------
                # ✅ 게스트 개인 통계 제외용 업데이트 함수
                # ---------------------------------------------------------
                def update_recs(target_recs, d, t1, t2, s1, s2, r):
                    players_all = t1 + t2

                    # 출석/경기수
                    for p in players_all:
                        if is_guest_name(p, roster):
                            continue
                        target_recs[p]["days"].add(d)
                        target_recs[p]["G"] += 1

                    # 득/실
                    s1_val = s1 or 0
                    s2_val = s2 or 0

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

                    # 승/무/패 + 점수
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

                    else:
                        for p in players_all:
                            if is_guest_name(p, roster):
                                continue
                            target_recs[p]["D"] += 1
                            target_recs[p]["points"] += DRAW_POINT

                # ---------------------------------------------------------
                # 1-1) 월간 데이터 집계
                # ---------------------------------------------------------
                for d, idx, g in month_games:
                    t1, t2 = g["t1"], g["t2"]
                    s1, s2 = g["score1"], g["score2"]
                    r = calc_result(s1, s2)
                    if r is None:
                        continue

                    # 이 경기 조(A/B/기타) 판별 (그 날짜 스냅샷 우선)
                    all_players = t1 + t2
                    day_groups_snapshot = sessions.get(d, {}).get("groups_snapshot")
                    grp_flag = classify_game_group(
                        all_players,
                        roster_by_name,
                        day_groups_snapshot,
                    )

                    # 전체 기록
                    update_recs(recs_all, d, t1, t2, s1, s2, r)

                    # A/B 기록
                    if grp_flag == "A":
                        update_recs(recs_A, d, t1, t2, s1, s2, r)
                    elif grp_flag == "B":
                        update_recs(recs_B, d, t1, t2, s1, s2, r)

                    # 🤝 파트너 집계 (게스트 파트너는 '게스트'로 묶음)
                    for team in (t1, t2):
                        if len(team) >= 2:
                            for i, p in enumerate(team):
                                if is_guest_name(p, roster):
                                    continue
                                for j, q in enumerate(team):
                                    if i == j:
                                        continue
                                    partners_by_player[p].add(guest_bucket(q, roster))

                # 👉 BEST 계산용 recs는 전체 기준 유지
                recs = recs_all

                # ---------------------------------------------------------
                # 1-2) 순위표 DF 생성
                # ---------------------------------------------------------
                def build_rank_df(recs_dict):
                    rows = []
                    for name, r in recs_dict.items():
                        if r["G"] == 0:
                            continue
                        # 혹시라도 남아있을 게스트 안전 차단
                        if is_guest_name(name, roster):
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
                    if not rows:
                        return None
                    df = pd.DataFrame(rows).sort_values(
                        ["점수", "승률"], ascending=False
                    ).reset_index(drop=True)
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
                    rank_df_A = build_rank_df(recs_A)
                    rank_df_B = build_rank_df(recs_B)

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

                    # A/B 둘 다 있으면 분리 표시
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

                # --------------------------------
                # 3-1. 카테고리별 BEST 함수
                # --------------------------------
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

                        # 경기수 집계 (게스트 제외)
                        for p in players_all:
                            if is_guest_name(p, roster):
                                continue
                            meta = roster_by_name.get(p, {})
                            grp = key_func(meta)
                            if grp in exclude_values:
                                continue
                            stats[grp]["G"] += 1

                        # 승리 그룹 집계
                        if r == "W":
                            winners = t1
                        elif r == "L":
                            winners = t2
                        else:
                            winners = []

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
                best_mbti = best_by_category(
                    "MBTI", lambda m: m.get("mbti", "모름"), exclude_values={"모름"}
                )
                # --------------------------------
                # 3-2. 선수별 BEST 계산
                # --------------------------------
                # 🎯 노자비왕 (공동우승 허용)
                diff_stats = []

                for name, r in recs.items():
                    if is_guest_name(name, roster):
                        continue

                    G = r["G"]
                    if G == 0:
                        continue

                    avg_for = r["score_for"] / G
                    avg_against = r["score_against"] / G
                    diff = avg_for - avg_against

                    diff_stats.append({
                        "name": name,
                        "avg_for": avg_for,
                        "avg_against": avg_against,
                        "diff": diff,
                    })

                if diff_stats:
                    best_diff_value = max(x["diff"] for x in diff_stats)
                    winners = [x for x in diff_stats if x["diff"] == best_diff_value]

                    if len(winners) == 1:
                        w = winners[0]
                        diff_line = (
                            f"{w['name']} "
                            f"(평균 득점 {w['avg_for']:.2f}, "
                            f"평균 실점 {w['avg_against']:.2f}, "
                            f"격차 {w['diff']:.2f})"
                        )
                    else:
                        names = ", ".join(w["name"] for w in winners)
                        diff_line = (
                            f"{names} "
                            f"(공동 노자비왕 · 최대 격차 {best_diff_value:.2f})"
                        )
                else:
                    diff_line = "데이터 부족"


                # 🤝 파트너왕 (공동우승 허용)
                partner_counts = []

                for name, partner_set in partners_by_player.items():
                    if is_guest_name(name, roster):
                        continue
                    cnt = len(partner_set)
                    partner_counts.append((name, cnt))

                if partner_counts:
                    most_partner_count = max(cnt for _, cnt in partner_counts)
                    winners = [name for name, cnt in partner_counts if cnt == most_partner_count]

                    if most_partner_count > 0:
                        names = ", ".join(winners)
                        if len(winners) == 1:
                            partner_line = f"{names} (만난 파트너 수 {most_partner_count}명)"
                        else:
                            partner_line = f"{names} (공동 파트너왕 · 만난 파트너 수 {most_partner_count}명)"
                    else:
                        partner_line = "데이터 부족 (복식 경기 없음)"
                else:
                    partner_line = "데이터 부족 (복식 경기 없음)"

                # 👑 출석왕 – '게임을 한 날짜 수'
                attendance_dates = defaultdict(set)

                for d, idx, g in month_games:
                    players_in_day = set(g["t1"] + g["t2"])
                    for p in players_in_day:
                        if is_guest_name(p, roster):
                            continue
                        attendance_dates[p].add(d)

                attendance_count = {p: len(days) for p, days in attendance_dates.items()}

                if attendance_count:
                    max_days = max(attendance_count.values())
                    att_winners = [p for p, v in attendance_count.items() if v == max_days]

                    if len(att_winners) > 1:
                        attendance_line = f"{', '.join(att_winners)} (참석 {max_days}일)"
                    else:
                        attendance_line = f"{att_winners[0]} (참석 {max_days}일)"
                else:
                    attendance_line = "데이터 부족"

                # 🔥 연승왕 – 이 달 최대 연승
                streak_now = defaultdict(int)
                streak_best = defaultdict(int)

                for d, idx, g in sorted(month_games, key=lambda x: (x[0], x[1])):
                    t1, t2 = g["t1"], g["t2"]
                    s1, s2 = g["score1"], g["score2"]
                    r = calc_result(s1, s2)
                    if r is None:
                        continue

                    # 무승부 처리
                    if r == "D":
                        for p in t1 + t2:
                            if is_guest_name(p, roster):
                                continue
                            if streak_now[p] > streak_best[p]:
                                streak_best[p] = streak_now[p]
                            streak_now[p] = 0
                        continue

                    if r == "W":
                        winners, losers = t1, t2
                    else:
                        winners, losers = t2, t1

                    for p in winners:
                        if is_guest_name(p, roster):
                            continue
                        streak_now[p] += 1
                        if streak_now[p] > streak_best[p]:
                            streak_best[p] = streak_now[p]

                    for p in losers:
                        if is_guest_name(p, roster):
                            continue
                        if streak_now[p] > streak_best[p]:
                            streak_best[p] = streak_now[p]
                        streak_now[p] = 0

                for p, cur in streak_now.items():
                    if is_guest_name(p, roster):
                        continue
                    if cur > streak_best[p]:
                        streak_best[p] = cur

                streak_line = "데이터 부족"
                if streak_best:
                    max_streak = max(streak_best.values())
                    if max_streak >= 2:
                        winners_streak = sorted(
                            [p for p, v in streak_best.items() if v == max_streak]
                        )
                        streak_line = f"{', '.join(winners_streak)} (최대 {max_streak}연승)"

                # 🥖 제빵왕 – 상대 팀 0점 만든 경기 수
                baker_counter = Counter()

                for d, idx, g in month_games:
                    t1, t2 = g["t1"], g["t2"]
                    s1, s2 = g["score1"], g["score2"]

                    if s1 is None or s2 is None:
                        continue

                    if s1 > 0 and s2 == 0:
                        for p in t1:
                            if is_guest_name(p, roster):
                                continue
                            baker_counter[p] += 1
                    elif s2 > 0 and s1 == 0:
                        for p in t2:
                            if is_guest_name(p, roster):
                                continue
                            baker_counter[p] += 1

                if baker_counter:
                    max_cnt = max(baker_counter.values())
                    winners = [p for p, c in baker_counter.items() if c == max_cnt]

                    if max_cnt > 0:
                        names = ", ".join(winners)
                        baker_line = f"{names} (상대를 0점으로 이긴 경기 {max_cnt}번)"
                    else:
                        baker_line = "데이터 부족"
                else:
                    baker_line = "데이터 부족"


                # --------------------------------
                # 3-3. 카드 UI 출력
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

