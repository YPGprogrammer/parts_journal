import streamlit as st
import pandas as pd
from core.utils import get_services

st.set_page_config(page_title="Мастерские", layout="wide")
st.title("Управление мастерскими")

services = get_services()

# Вкладки
tab1, tab2, tab3 = st.tabs(["Список мастерских", "Добавить мастерскую", "Редактировать мастерскую"])

with tab1:
    st.subheader("Список всех мастерских")
    workshops = services.workshops.list()

    if workshops:
        # Формируем данные для таблицы
        workshops_data = []
        for workshop in workshops:
            # Подсчитываем количество замен в этой мастерской
            replacements = services.replacements.list()
            replacements_count = len([r for r in replacements if r.workshop_id == workshop.id])

            workshops_data.append({
                'ID': workshop.id,
                'Наименование': workshop.name,
                'Адрес': workshop.addr,
                'Количество замен': replacements_count
            })

        df = pd.DataFrame(workshops_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Статистика
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Всего мастерских", len(workshops))
        with col2:
            total_replacements = sum(len([r for r in services.replacements.list() if r.workshop_id == w.id]) for w in workshops)
            st.metric("Всего замен", total_replacements)
    else:
        st.info("Нет мастерских. Добавьте первую мастерскую во вкладке 'Добавить мастерскую'.")

with tab2:
    st.subheader("Добавить новую мастерскую")

    with st.form("add_workshop_form", clear_on_submit=True):
        name = st.text_input("Наименование мастерской *", max_chars=50)
        addr = st.text_input("Адрес мастерской *", max_chars=100)

        submitted = st.form_submit_button("Добавить мастерскую", type="primary")

        if submitted:
            if not name:
                st.error("Пожалуйста, заполните наименование мастерской")
            elif not addr:
                st.error("Пожалуйста, заполните адрес мастерской")
            else:
                try:
                    new_workshop = services.workshops.create(
                        name=name,
                        addr=addr
                    )
                    st.success(f"Мастерская '{name}' успешно добавлена!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка при добавлении мастерской: {str(e)}")

with tab3:
    st.subheader("Редактировать мастерскую")

    workshops = services.workshops.list()
    if not workshops:
        st.info("Нет мастерских для редактирования.")
    else:
        selected_workshop = st.selectbox(
            "Выберите мастерскую для редактирования",
            options=workshops,
            format_func=lambda w: f"{w.name} - {w.addr} (ID: {w.id})"
        )

        if selected_workshop:
            with st.form("edit_workshop_form"):
                name = st.text_input("Наименование мастерской *", value=selected_workshop.name, max_chars=50)
                addr = st.text_input("Адрес мастерской *", value=selected_workshop.addr, max_chars=100)

                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Сохранить изменения", type="primary")
                with col2:
                    delete_clicked = st.form_submit_button("Удалить мастерскую", type="secondary")

                if submitted:
                    if not name:
                        st.error("Пожалуйста, заполните наименование мастерской")
                    elif not addr:
                        st.error("Пожалуйста, заполните адрес мастерской")
                    else:
                        try:
                            services.workshops.update(
                                selected_workshop.id,
                                name=name,
                                addr=addr
                            )
                            st.success(f"Мастерская '{name}' успешно обновлена!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка при обновлении мастерской: {str(e)}")

                if delete_clicked:
                    # Проверяем, есть ли замены, связанные с этой мастерской
                    replacements = services.replacements.list()
                    related_replacements = [r for r in replacements if r.workshop_id == selected_workshop.id]

                    if related_replacements:
                        st.error(f"Нельзя удалить мастерскую, так как с ней связано {len(related_replacements)} замен. Сначала удалите или измените замены.")
                    else:
                        try:
                            services.workshops.delete(selected_workshop.id)
                            st.success(f"Мастерская '{selected_workshop.name}' успешно удалена!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка при удалении мастерской: {str(e)}")
