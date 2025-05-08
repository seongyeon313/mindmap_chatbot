import streamlit as st
import json
import re
import difflib
import logging
import random

# ---------------------
# 로깅 설정
# ---------------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# ---------------------
# Comfort 메시지
# ---------------------
comfort_messages = [
    "힘드셨겠어요, 이런 정보가 도움이 되길 바랍니다 💛",
    "조금이나마 위로가 되었으면 해요 💛",
    "혼자가 아니에요, 언제든 물어봐 주세요 💛"
]

# ---------------------
# 파일 로드
# ---------------------
mental_disorders_path = '질병_증상_치료법_치료제.json'
medications_path = '치료제_부작용.json'
synonyms_path = 'final_synonym_dict.json'

with open(mental_disorders_path, 'r', encoding='utf-8') as f:
    mental_disorders = json.load(f)
with open(medications_path, 'r', encoding='utf-8') as f:
    medications = json.load(f)
with open(synonyms_path, 'r', encoding='utf-8') as f:
    synonyms = json.load(f)

# ---------------------
# 약물 동의어 맵 생성
# ---------------------
def build_medication_synonym_map(medications):
    med_synonyms = {}
    for med in medications:
        med_field = med.get('약물 (일반명/상품명)', '')
        match = re.match(r'(.+?)\s*\((.+?)\)', med_field)
        if match:
            names = [match.group(1).strip(), match.group(2).strip()]
        else:
            names = [med_field.strip()]
        med_synonyms[names[0]] = names
    return med_synonyms

med_synonym_map = build_medication_synonym_map(medications)
for key, values in med_synonym_map.items():
    synonyms[key] = list(set(synonyms.get(key, []) + values))

# ---------------------
# 오타 교정 함수
# ---------------------
def correct_input(user_input, known_words):
    words = user_input.split()
    corrected = []
    for word in words:
        matches = difflib.get_close_matches(word, known_words, n=1, cutoff=0.8)
        corrected_word = matches[0] if matches else word
        corrected.append(corrected_word)
    corrected_input = ' '.join(corrected)
    logging.info(f'Original input: {user_input}')
    logging.info(f'Corrected input: {corrected_input}')
    return corrected_input

# ---------------------
# 동의어 매칭
# ---------------------
def match_synonym(user_input, target_key):
    return any(re.search(rf'\b{re.escape(word)}\b', user_input) for word in synonyms.get(target_key, [target_key]))

# ---------------------
# 민감 트리거
# ---------------------
sensitive_triggers = ['죽고 싶', '자살', '극단', '해치']
med_keywords = ['약', '약물', '치료', '복용', '추천', '먹는 약']

# ---------------------
# 챗봇 메인 함수
# ---------------------
def chatbot(user_input):
    try:
        known_words = list(synonyms.keys()) + [m.get('약물 (일반명/상품명)', '') for m in medications]
        user_input_corrected = correct_input(user_input, known_words)
        user_input_clean = re.sub(r'[^\w\s]', '', user_input_corrected.strip())
        logging.info(f'Clean input: {user_input_clean}')

        comfort = random.choice(comfort_messages)

        if any(trigger in user_input_clean for trigger in sensitive_triggers):
            return f"⚠️ 위험한 생각이 드신다면 가까운 사람이나 전문가에게 꼭 도움을 요청하세요. 💛 당신은 혼자가 아닙니다."

        if '부작용' in user_input_clean:
            for med in medications:
                med_field = med.get('약물 (일반명/상품명)', '')
                med_names = med_synonym_map.get(med_field.split()[0], [med_field])
                if any(med_name in user_input_clean for med_name in med_names):
                    side_effects = med.get('부작용 상세', '부작용 정보 없음')
                    return f"💊 {med_field} 부작용:<br>- {side_effects}<br>{comfort}"

            return f"앗, 해당 약물의 부작용 정보를 아직 찾지 못했어요.<br>{comfort}"

        if any(kw in user_input_clean for kw in med_keywords):
            for disorder in mental_disorders:
                disorder_name = disorder.get('질병', '')
                if disorder_name == '성격장애':
                    continue
                if match_synonym(user_input_clean, disorder_name):
                    treatments = disorder.get('치료제', '')
                    symptoms = disorder.get('증상', '')
                    treatments_msg = treatments if treatments else '데이터에 정보가 없습니다'
                    symptoms_msg = symptoms.replace('·', ',').replace(';', ',')
                    symptom_list = [s.strip() for s in re.split(r'[,\n]', symptoms_msg) if s.strip()]
                    symptom_html = "<ul>" + "".join(f"<li>{s}</li>" for s in symptom_list) + "</ul>"
                    return f"💊 <b>{disorder_name}</b>에 사용되는 약물:<br>- {treatments_msg}<br>📌 특징 증상:<br>{symptom_html}<br>{comfort}"

        matched_diseases = []
        for disorder in mental_disorders:
            disorder_name = disorder.get('질병', '')
            symptoms = disorder.get('증상', '')
            symptom_words = re.split(r'[·, ]', symptoms)
            match_count = sum(1 for word in symptom_words if word and word in user_input_clean)
            if match_synonym(user_input_clean, disorder_name) or match_count >= 1:
                if disorder_name != '성격장애':
                    matched_diseases.append((disorder_name, symptoms))

        if matched_diseases:
            response = "🔍 관련 질병 및 특징:<br><ul>"
            for name, symptoms in matched_diseases[:3]:
                symptoms_msg = symptoms.replace('·', ',').replace(';', ',')
                symptom_list = [s.strip() for s in re.split(r'[,\n]', symptoms_msg) if s.strip()]
                symptom_html = "<ul>" + "".join(f"<li>{s}</li>" for s in symptom_list) + "</ul>"
                response += f"<li><b>{name}</b>: {symptom_html}</li>"
            response += f"</ul>{comfort}"
            return response

        personality = next((d for d in mental_disorders if d.get('질병') == '성격장애'), None)
        if personality:
            symptoms = personality.get('증상', '')
            symptoms_msg = symptoms.replace('·', ',').replace(';', ',')
            symptom_list = [s.strip() for s in re.split(r'[,\n]', symptoms_msg) if s.strip()]
            symptom_html = "<ul>" + "".join(f"<li>{s}</li>" for s in symptom_list) + "</ul>"
            return f"💬 현재 질문에 맞는 정확한 데이터를 찾지 못했어요.<br>성격장애 정보 참고:<br>{symptom_html}<br>{comfort}"

    except Exception as e:
        logging.error(f'Error: {e}')
        return f"앗, 오류가 발생했어요! 잠시 후 다시 시도해 주세요.<br>(오류 내용: {str(e)})"

# ---------------------
# Streamlit UI
# ---------------------
st.set_page_config(page_title="💬 마음 챗봇", page_icon="💬", layout="centered")

st.markdown("""
<style>
.user-message {
    background-color: #DCF8C6;
    padding: 12px 16px;
    border-radius: 12px;
    margin: 10px;
    max-width: 80%;
    float: right;
    clear: both;
    word-wrap: break-word;
    font-size: 16px;
    line-height: 1.6;
}
.bot-message {
    background-color: #E6E6FA;
    padding: 12px 16px;
    border-radius: 12px;
    margin: 10px;
    max-width: 80%;
    float: left;
    clear: both;
    word-wrap: break-word;
    font-size: 16px;
    line-height: 1.6;
}
ul {
    margin: 0;
    padding-left: 20px;
}
</style>
""", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("💬 마음 챗봇")
st.markdown("""
안녕하세요! 저는 **마음 건강 챗봇**이에요.  
증상, 질병, 약물, 부작용 관련 질문을 자유롭게 해보세요.

⚠️ **주의:** 이 챗봇은 참고용입니다.  
정확한 진단 및 치료는 반드시 의료진과 상담하세요!
""")

with st.form(key='chat_form', clear_on_submit=True):
    col1, col2 = st.columns([9, 2])
    with col1:
        user_input = st.text_input("궁금한 걸 입력해주세요 :", key="user_input", label_visibility="collapsed")
    with col2:
        submit_button = st.form_submit_button("🚀 보내기")

if submit_button and user_input:
    response = chatbot(user_input)
    st.session_state.chat_history.append(("user", user_input))
    st.session_state.chat_history.append(("bot", response))

for sender, message in st.session_state.chat_history:
    css_class = "user-message" if sender == "user" else "bot-message"
    st.markdown(f"<div class='{css_class}'>{message}</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("✅ 만든 사람: MINDMAP | 📌 마음건강 챗봇 | 🩺 의료상담은 전문가와 함께하세요")


# 경로 확인 후  
# cd C:\\Users\\jimin\\Downloads  
# streamlit run final_chatbot.py
