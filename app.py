import os
import streamlit as st
import openai
from sqlalchemy import create_engine, Column, Integer, String, TEXT, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# 定数の定義
DATABASE_URL = "sqlite:///chat.db"  # データベースのパス
MAX_HISTORY = 5  # ChatGPT APIに突っ込む会話履歴数(往復)

# データベースのセットアップ
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Chat(Base):
    """チャット履歴を保存するテーブル"""
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, default=0)
    role = Column(String(10))
    message = Column(TEXT)
    timestamp = Column(DateTime, default=datetime.now)

class ChatObject:
    """チャットオブジェクト"""
    def __init__(self, id, thread_id, role, message, timestamp):
        self.id = id
        self.thread_id = thread_id
        self.role = role
        self.message = message
        self.timestamp = timestamp

def create_table_if_not_exists():
    """テーブルが存在しない場合は、chatsテーブルを作成する"""
    Base.metadata.create_all(bind=engine)

def fetch_chat_history(session):
    """データベースからチャット履歴を取得する"""
    result = session.query(Chat).order_by(Chat.id.asc()).all()
    return [ChatObject(chat.id, chat.thread_id, chat.role, chat.message, chat.timestamp) for chat in result]

def save_chat(session, role, message):
    """ユーザーのメッセージとGPTからの返信をデータベースに保存する"""
    chat = Chat(role=role, message=message)
    session.add(chat)
    session.commit()

def get_latest_chats(session):
    """データベースから最新のチャット履歴を取得する"""
    result = session.query(Chat).order_by(Chat.id.desc()).limit(MAX_HISTORY).all()
    return [ChatObject(chat.id, chat.thread_id, chat.role, chat.message, chat.timestamp) for chat in result[::-1]]

def get_gpt_resp(user_msg, history):
    """GPTとのチャットを行う"""
    history_dict = [{"role": chat.role, "content": chat.message} for chat in history]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history_dict + [{"role": "user", "content": user_msg}]
    )
    return response.choices[0].message.content

def main():
    """Streamlitアプリケーションのメイン関数"""
    st.set_page_config(page_title='Chat with GPT', page_icon=':robot_face:', layout='wide')
    with st.sidebar:
        st.title("Chat with GPT")
        user_msg = st.text_input("Enter your message", key="user_msg")
        send_button = st.button("Send")
        openai_api_key = st.text_input("Enter your OpenAI API key", type="password")
        set_button = st.button("Set API key")
    st.header("Chat History")

    session = SessionLocal()
    create_table_if_not_exists()

    # チャット履歴を表示する
    for chat in fetch_chat_history(session):
        if chat.role == "user":
            with st.chat_message(chat.role):
                st.write(chat.message)
        else:
            with st.chat_message(chat.role):
                st.write(chat.message)

    # APIキーを設定する
    if set_button:
        openai.api_key = openai_api_key
        st.sidebar.success("Set your API key successfully!")

    # メッセージが空の場合、sendボタンを非活性にする
    if not user_msg:
        send_button = False

    # ユーザーがメッセージを送信した場合
    if send_button and user_msg:
        with st.chat_message("user"):
            st.write(user_msg)
        history = get_latest_chats(session)
        try:
            assistant_msg = get_gpt_resp(user_msg, history)
            save_chat(session, "user", user_msg)
            save_chat(session, "assistant", assistant_msg)
        except Exception as e:
            st.error(f"An error occurred: {e}")
        with st.chat_message("assistant"):
            st.write(assistant_msg)
    session.close()

if __name__ == "__main__":
    main()