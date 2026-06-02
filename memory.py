from langchain_community.chat_message_histories import SQLChatMessageHistory
import config

def get_long_term_memory(session_id):
    return SQLChatMessageHistory(
        session_id=session_id,
        connection=config.SQLITE_DB_URL
    )