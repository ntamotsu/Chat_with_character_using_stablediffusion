import os
import streamlit as st
import openai
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///chat.db"
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]  # API key
MAX_HISTORY = 5  # ChatGPT APIに突っ込む会話履歴数(往復)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_table_if_not_exists():
    with engine.connect() as connection:
        connection.execute(text("""CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY,
            user_msg TEXT NOT NULL,
            assistant_msg TEXT NOT NULL
        )"""))

def fetch_chat_history(session):
    result = session.execute(text(f"SELECT user_msg, assistant_msg FROM chats ORDER BY id ASC")).fetchall()
    return [{"role": "user" if i%2==0 else "assistant", "content": user_msg if i%2==0 else assistant_msg} for i, (user_msg, assistant_msg) in enumerate(result)]

def save_chat(session, user_msg, assistant_msg):
    session.execute(text("INSERT INTO chats (user_msg, assistant_msg) VALUES (:user_msg, :assistant_msg)"), {"user_msg": user_msg, "assistant_msg": assistant_msg})
    session.commit()

def get_latest_chats(session):
    result = session.execute(text(f"SELECT user_msg, assistant_msg FROM chats ORDER BY id DESC LIMIT {MAX_HISTORY}")).fetchall()
    return [{"role": "user" if i%2==0 else "assistant", "content": user_msg if i%2==0 else assistant_msg} for i, (user_msg, assistant_msg) in enumerate(result[::-1])]

def chat_with_gpt(user_msg, history):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history + [{"role": "user", "content": user_msg}]
    )
    return response.choices[0].message.content

def main():
    st.set_page_config(page_title='Chat with GPT', layout='wide')
    st.text_input("Enter your message", key="message")
    send_button = st.button("Send")
    chat_hist_area = st.empty()

    session = SessionLocal()
    create_table_if_not_exists()

    if "chat_hist" not in st.session_state:
        st.session_state.chat_hist = fetch_chat_history(session)

    if send_button:
        user_msg = st.session_state.message
        history = get_latest_chats(session)
        try:
            assistant_msg = chat_with_gpt(user_msg, history)
            save_chat(session, user_msg, assistant_msg)
            st.session_state.chat_hist.extend([
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg}
            ])
        except Exception as e:
            st.error(f"An error occurred: {e}")
        finally:
            chat_hist_area.text("Chat History:\n" + "\n".join([f"{chat['role'].title()}: {chat['content']}" for chat in st.session_state.chat_hist]))

    session.close()

if __name__ == "__main__":
    openai.api_key = OPENAI_API_KEY
    main()