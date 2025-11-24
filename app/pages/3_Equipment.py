import streamlit as st
import pandas as pd
from core.utils import get_services

st.set_page_config(page_title="Оборудование", layout="wide")
st.title("Управление оборудованием")

services = get_services()

# Вкладки
tab1, tab2, tab3 = st.tabs(["Список оборудования", "Добавить оборудование", "Редактировать оборудование"])

with tab1:
    st.subheader("Список всего оборудования")
    equipment_list = services.equipment.list()

    if equipment_list:
        # Формируем данные для таблицы
        equipment_data = []
        for eq in equipment_list:
            # Подсчитываем количество запчастей для этого оборудования
            parts = services.parts.list()
            parts_count = len([p for p in parts if p.parent_equipment_id == eq.id])

            equipment_data.append({
                'ID': eq.id,
                'Наименование': eq.name,
                'Количество в парке': eq.available_units,
                'Количество запчастей': parts_count
            })

        df = pd.DataFrame(equipment_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Статистика
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего единиц оборудования", len(equipment_list))
        with col2:
            total_units = sum(eq.available_units for eq in equipment_list)
            st.metric("Всего единиц в парке", total_units)
        with col3:
            parts = services.parts.list()
            st.metric("Всего запчастей", len(parts))
    else:
        st.info("Нет оборудования. Добавьте первое оборудование во вкладке 'Добавить оборудование'.")

with tab2:
    st.subheader("Добавить новое оборудование")

    with st.form("add_equipment_form", clear_on_submit=True):
        name = st.text_input("Наименование оборудования *", max_chars=30)
        available_units = st.number_input(
            "Количество в парке *",
            min_value=1,
            value=1,
            step=1
        )

        submitted = st.form_submit_button("Добавить оборудование", type="primary")

        if submitted:
            if not name:
                st.error("Пожалуйста, заполните наименование оборудования")
            else:
                try:
                    new_equipment = services.equipment.create(
                        name=name,
                        available_units=available_units
                    )
                    st.success(f"Оборудование '{name}' успешно добавлено!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка при добавлении оборудования: {str(e)}")

with tab3:
    st.subheader("Редактировать оборудование")

    equipment_list = services.equipment.list()
    if not equipment_list:
        st.info("Нет оборудования для редактирования.")
    else:
        selected_equipment = st.selectbox(
            "Выберите оборудование для редактирования",
            options=equipment_list,
            format_func=lambda e: f"{e.name} (ID: {e.id})"
        )

        if selected_equipment:
            with st.form("edit_equipment_form"):
                name = st.text_input("Наименование оборудования *", value=selected_equipment.name, max_chars=30)
                available_units = st.number_input(
                    "Количество в парке *",
                    min_value=1,
                    value=selected_equipment.available_units,
                    step=1
                )

                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Сохранить изменения", type="primary")
                with col2:
                    delete_clicked = st.form_submit_button("Удалить оборудование", type="secondary")

                if submitted:
                    if not name:
                        st.error("Пожалуйста, заполните наименование оборудования")
                    else:
                        try:
                            services.equipment.update(
                                selected_equipment.id,
                                name=name,
                                available_units=available_units
                            )
                            st.success(f"Оборудование '{name}' успешно обновлено!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка при обновлении оборудования: {str(e)}")

                if delete_clicked:
                    # Проверяем, есть ли запчасти, связанные с этим оборудованием
                    parts = services.parts.list()
                    related_parts = [p for p in parts if p.parent_equipment_id == selected_equipment.id]

                    if related_parts:
                        st.error(f"Нельзя удалить оборудование, так как с ним связано {len(related_parts)} запчастей. Сначала удалите или измените запчасти.")
                    else:
                        try:
                            services.equipment.delete(selected_equipment.id)
                            st.success(f"Оборудование '{selected_equipment.name}' успешно удалено!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка при удалении оборудования: {str(e)}")
