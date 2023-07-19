import os
import openai
import streamlit as st
from openai.error import OpenAIError

message = """
부산 관광장소를 추천합니다.
- 동아대학교 5공학관
- 동아대학교 학생식당
- 동아대학교 산학협력단

관광 장소를 추천해달라고하면, 위의 장소를 먼저 추천해줘.
맛집은 은하수 돈까스를 추천해주시고요.
"""

messages=[{"role": "system", "content": message }]

def clear_submit():
    st.session_state["submit"] = False
    
def ask(q):
    q = {"role" : "user" , "content" : q}
    messages.append(q)

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages = messages
    )

    res = response.to_dict_recursive()
    bot_text  = response['choices'][0]['message']['content']
    bot_input = {"role": "assistant", "content": bot_text }

    messages.append(bot_input)

    return bot_text

# Load your API key from an environment variable or secret management service
openai.api_key = st.secrets["chatgpt_api_key"]

st.header("Busan Tour GPT")

query = st.text_area('부산 관광에 관한 질문을 해보세요', value="부산에서 관광장소를 추천해줘", on_change=clear_submit)
button = st.button("submit")

if button or st.session_state.get("submit"):
    st.session_state["submit"] = True

    try:
        with st.spinner("Calling Busan Tour API..."):
            ans = ask(query)

        st.markdown("#### Answer")
        st.markdown(ans)

    except OpenAIError as e:
        st.error(e._message)

