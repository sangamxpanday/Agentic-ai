from unicodedata import name

import streamlit as st
from langgraph_tool_backend import chatbot, chat_model, retreieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid

#{'role': 'user', 'content': 'HI.'},............

##################UTILITIES FUNCTIONS##########################

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    st.session_state['message_history'] = []
    add_thread(st.session_state['thread_id'])
    st.session_state['thread_id'] = generate_thread_id()

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    #fetch messages for a thread from checkpointer
    #for now we will just return the current message history
    state =  chatbot.get_state(config = {'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])

###################SESSION SETUP##########################

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retreieve_all_threads()

add_thread(st.session_state['thread_id'])

#######################SIDEBAR UI##########################

st.sidebar.title("Langgraph Chatbot")

if st.sidebar.button("New chat"):
    reset_chat()

st.sidebar.header("My Conversations")

# Helper function to safely create a label from UUID
def get_thread_label(tid):
    if not tid:
        return "Unknown Chat"
    # CRITICAL FIX: Convert UUID to string before slicing
    return f"Chat {str(tid)[:8]}"

# 1. Button for the CURRENT active thread (optional, or just highlight it)
# Usually, you don't need a button for the current thread unless you want to reload it.
# Instead, let's list ALL threads from chat_threads.

for tid in st.session_state['chat_threads']:
    # Generate a unique key for each button using the string representation of the UUID
    btn_key = f"thread_btn_{str(tid)}"
    
    # Create a friendly label
    label = get_thread_label(tid)
    
    # Highlight the active thread
    if tid == st.session_state['thread_id']:
        label = f"✅ {label} (Active)"
    
    if st.sidebar.button(label, key=btn_key):
        if tid != st.session_state['thread_id']:
            st.session_state['thread_id'] = tid
            # Load conversation
            messages = load_conversation(tid)
            
            # Convert LangChain messages to dict for UI
            temp_messages = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    temp_messages.append({'role': 'user', 'content': msg.content})
                elif isinstance(msg, AIMessage):
                    temp_messages.append({'role': 'assistant', 'content': msg.content})
            
            st.session_state['message_history'] = temp_messages
            st.rerun() # Rerun to update UI immediately   

# for thread_id in st.session_state['chat_threads']:
#     messages = load_conversation(thread_id) 
#     if not messages:
#         title=  "New Chat"
#     else:
#         title = chat_model.invoke(
#             f"provide a short title for the following conversastion: {messages}"
#         ).content
#     if st.sidebar.button(title):
#         st.session_state['thread_id'] = thread_id
#         messages = load_conversation(thread_id)

#         temp_messages = []

#         for message in messages:
#             if isinstance(message, HumanMessage):
#                 temp_messages.append({'role': 'user', 'content': message.content})
#             elif isinstance(message, AIMessage):
#                 temp_messages.append({'role': 'assistant', 'content': message.content})

#         st.session_state['message_history'] = temp_messages

#######################MAIN UI##########################

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

    #CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
    
    CONFIG = {
        'configurable': {'thread_id': st.session_state['thread_id']},
        'metadata': {
            'thread_id': st.session_state['thread_id'],
        },
        "run_name": "chat_run",
    }

    with st.chat_message("assistant"):
        # Use a mutable holder so the generator can set/modify it
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                # Lazily create & update the SAME status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        # Finalize only if a tool was actually used
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

    # Save assistant message
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )
   