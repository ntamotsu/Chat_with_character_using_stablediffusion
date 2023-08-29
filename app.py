import os
from typing import Generator, Union
import streamlit as st
import openai
from sqlalchemy import create_engine, Column, Integer, String, TEXT, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# 定数の定義
DATABASE_URL = "sqlite:///chat.db"  # データベースのパス
MAX_HISTORY = 5  # ChatGPT APIに突っ込む会話履歴数(往復)
MODEL = "gpt-3.5-turbo"
ROLE = "role"
USER = "user"
ASSISTANT = "assistant"
CONTENT = "content"

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
    def __init__(self, id: int, thread_id: int, role: str, message: str, timestamp: datetime):
        self.id = id
        self.thread_id = thread_id
        self.role = role
        self.message = message
        self.timestamp = timestamp


def create_table_if_not_exists() -> None:
    """テーブルが存在しない場合は、chatsテーブルを作成する"""
    Base.metadata.create_all(bind=engine)

def fetch_chat_history(session: SessionLocal) -> list[ChatObject]:
    """データベースからチャット履歴を取得する"""
    result = session.query(Chat).order_by(Chat.id.asc()).all()
    return [ChatObject(chat.id, chat.thread_id, chat.role, chat.message, chat.timestamp) for chat in result]

def save_chat(session: SessionLocal, role: str, message: str) -> None:
    """メッセージ1つをデータベースに保存する"""
    chat = Chat(role=role, message=message)
    session.add(chat)
    session.commit()

def get_latest_chats(session: SessionLocal) -> list[ChatObject]:
    """データベースから最新のチャット履歴を取得する"""
    result = session.query(Chat).order_by(Chat.id.desc()).limit(MAX_HISTORY).all()
    return [ChatObject(chat.id, chat.thread_id, chat.role, chat.message, chat.timestamp) for chat in result[::-1]]

def get_gpt_resp(user_msg: str, history: list[ChatObject], max_tokens: Integer = None, temperature: Integer = None, functions: dict = None, function_call: str = None, stream: bool = False) -> Union[Generator[dict[str, str], None, None], Generator[str, None, None], dict[str, str], str]:
    """GPTとのチャットを行う"""
    history_dict = [{ROLE: chat.role, CONTENT: chat.message} for chat in history]
    response = openai.ChatCompletion.create(
        # 値が None である引数はAPIに渡さない
        **{k: v for k, v in {
            "model": MODEL,
            "messages": history_dict + [{ROLE: USER, CONTENT: user_msg}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "functions": functions,
            "function_call": function_call,
            "stream": stream
        }.items() if v is not None}
    )
    
    if stream:
        for chunk in response:
            if chunk.choices[0].delta.get('function_call'):
                yield {chunk.choices[0].delta.function_call.name : chunk.choices[0].delta.function_call.arguments}
            else:
                yield chunk.choices[0].delta.get('content', '')
    else:
        if response.choices[0].message.get('function_call'):
            yield {response.choices[0].message.function_call.name : response.choices[0].message.function_call.arguments}
        else:
            yield response.choices[0].message.get('content', '')


def main():
    """Streamlitアプリケーションのメイン関数"""
    st.set_page_config(page_title='Chat with GPT', page_icon=':robot_face:', layout='wide')
    with st.sidebar:
        st.title("Chat with GPT")
        openai_api_key = st.text_input("Enter your OpenAI API key", type="password")
        set_button = st.button("Set API key")
    st.header("Chat History")
    user_msg = st.chat_input("Enter your message")

    session = SessionLocal()
    create_table_if_not_exists()

    # チャット履歴を表示する
    for chat in fetch_chat_history(session):
        with st.chat_message(chat.role):
            st.write(chat.message)

    # APIキーを設定する
    if set_button and openai_api_key:
        openai.api_key = openai_api_key
        st.sidebar.success("Set your API key successfully!")

    # ユーザーがメッセージを送信した場合
    if user_msg:
        with st.chat_message(USER):
            st.markdown(user_msg)
        history = get_latest_chats(session)
        try:
            with st.chat_message(ASSISTANT):
                placeholder = st.empty()
                assistant_msg = ""
                for chunk in get_gpt_resp(user_msg, history, stream=True):
                    assistant_msg += chunk
                    placeholder.markdown(assistant_msg + "▌")
            save_chat(session, USER, user_msg)
            save_chat(session, ASSISTANT, assistant_msg)
        except Exception as e:
            st.error(f"An error occurred: {e}")
    session.close()

if __name__ == "__main__":
    main()