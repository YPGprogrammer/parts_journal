import streamlit as st
from core.db import init_db, get_session
from core.services import ServiceContainer

def main():
    init_db()

    if "services" not in st.session_state:
        session = get_session()
        st.session_state["services"] = ServiceContainer(session)

    st.title("Журнал запасных частей")

if __name__ == "__main__":
    main()


