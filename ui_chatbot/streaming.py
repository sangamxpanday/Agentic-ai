import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage, AIMessage

CONFIG = {'configurable': {'thread_id': 'my_chat_thread'}} 

#{'role': 'user', 'content': 'HI.'},............

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])


#st.session_state -> dict -> persist data across reruns of the app

user_input = st.chat_input("Type here...")

if user_input:

    #first add message to message history

    st.session_state['message_history'].append({'role': 'user', 'content': user_input})

    with st.chat_message('user'):
        st.text(user_input)
    # st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})

    with st.chat_message('assistant'):
        ai_messages = st.write_stream(
            message_chunk.content for message_chunk,metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]}, config = CONFIG,stream_mode = 'messages'
            )
        )

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_messages})
   