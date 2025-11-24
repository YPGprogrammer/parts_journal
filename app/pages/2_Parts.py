import streamlit as st
import pandas as pd
from core.utils import get_services

st.set_page_config(page_title="Запчасти", layout="wide")
st.title("Управление запчастями")

services = get_services()

# Получаем список оборудования для выбора
equipment_list = services.equipment.list()

if not equipment_list:
    st.warning("Сначала добавьте оборудование, чтобы создавать запчасти.")
    st.stop()

# Создание словаря для быстрого поиска
equipment_dict = {eq.id: eq.name for eq in equipment_list}

# Вкладки
tab1, tab2, tab3 = st.tabs(["Список запчастей", "Добавить запчасть", "Редактировать запчасть"])

with tab1:
    st.subheader("Список всех запчастей")
    parts = services.parts.list()

    if parts:
        # Формируем данные для таблицы
        parts_data = []
        for part in parts:
            equipment_name = equipment_dict.get(part.parent_equipment_id, "Неизвестно")
            parts_data.append({
                'ID': part.id,
                'Наименование': part.name,
                'Оборудование': equipment_name,
                'Срок службы (дней)': part.useful_life_days,
                'Кол-во в единице': part.qty_per_unit,
                'На складе': part.qty_in_stock,
                'Срок закупки (дней)': part.lead_time_days
            })

        df = pd.DataFrame(parts_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Статистика
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего запчастей", len(parts))
        with col2:
            total_in_stock = sum(p.qty_in_stock for p in parts)
            st.metric("Всего на складе", total_in_stock)
        with col3:
            unique_equipment = len(set(p.parent_equipment_id for p in parts))
            st.metric("Типов оборудования", unique_equipment)
    else:
        st.info("Нет запчастей. Добавьте первую запчасть во вкладке 'Добавить запчасть'.")

with tab2:
    st.subheader("Добавить новую запчасть")

    with st.form("add_part_form", clear_on_submit=True):
        name = st.text_input("Наименование запчасти *", max_chars=50)

        col1, col2 = st.columns(2)
        with col1:
            equipment_id = st.selectbox(
                "Родительское оборудование *",
                options=equipment_list,
                format_func=lambda x: x.name,
                key="new_equipment"
            )
            useful_life_days = st.number_input(
                "Срок полезного использования (дней) *",
                min_value=1,
                value=100,
                step=1
            )
            qty_per_unit = st.number_input(
                "Количество в единице оборудования *",
                min_value=1,
                value=1,
                step=1
            )

        with col2:
            qty_in_stock = st.number_input(
                "Количество на складе *",
                min_value=0,
                value=0,
                step=1
            )
            lead_time_days = st.number_input(
                "Срок закупки запчасти (дней) *",
                min_value=0,
                value=2,
                step=1
            )

        submitted = st.form_submit_button("Добавить запчасть", type="primary")

        if submitted:
            if not name:
                st.error("Пожалуйста, заполните наименование запчасти")
            else:
                try:
                    new_part = services.parts.create(
                        name=name,
                        parent_equipment_id=equipment_id.id,
                        useful_life_days=useful_life_days,
                        qty_per_unit=qty_per_unit,
                        qty_in_stock=qty_in_stock,
                        lead_time_days=lead_time_days
                    )
                    st.success(f"Запчасть '{name}' успешно добавлена!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка при добавлении запчасти: {str(e)}")

with tab3:
    st.subheader("Редактировать запчасть")

    parts = services.parts.list()
    if not parts:
        st.info("Нет запчастей для редактирования.")
    else:
        selected_part = st.selectbox(
            "Выберите запчасть для редактирования",
            options=parts,
            format_func=lambda p: f"{p.name} (ID: {p.id})"
        )

        if selected_part:
            with st.form("edit_part_form"):
                name = st.text_input("Наименование запчасти *", value=selected_part.name, max_chars=50)

                col1, col2 = st.columns(2)
                with col1:
                    equipment_id = st.selectbox(
                        "Родительское оборудование *",
                        options=equipment_list,
                        format_func=lambda x: x.name,
                        index=[eq.id for eq in equipment_list].index(selected_part.parent_equipment_id) if selected_part.parent_equipment_id in [eq.id for eq in equipment_list] else 0
                    )
                    useful_life_days = st.number_input(
                        "Срок полезного использования (дней) *",
                        min_value=1,
                        value=selected_part.useful_life_days,
                        step=1
                    )
                    qty_per_unit = st.number_input(
                        "Количество в единице оборудования *",
                        min_value=1,
                        value=selected_part.qty_per_unit,
                        step=1
                    )

                with col2:
                    qty_in_stock = st.number_input(
                        "Количество на складе *",
                        min_value=0,
                        value=selected_part.qty_in_stock,
                        step=1
                    )
                    lead_time_days = st.number_input(
                        "Срок закупки запчасти (дней) *",
                        min_value=0,
                        value=selected_part.lead_time_days,
                        step=1
                    )

                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Сохранить изменения", type="primary")
                with col2:
                    delete_clicked = st.form_submit_button("Удалить запчасть", type="secondary")

                if submitted:
                    if not name:
                        st.error("Пожалуйста, заполните наименование запчасти")
                    else:
                        try:
                            services.parts.update(
                                selected_part.id,
                                name=name,
                                parent_equipment_id=equipment_id.id,
                                useful_life_days=useful_life_days,
                                qty_per_unit=qty_per_unit,
                                qty_in_stock=qty_in_stock,
                                lead_time_days=lead_time_days
                            )
                            st.success(f"Запчасть '{name}' успешно обновлена!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка при обновлении запчасти: {str(e)}")

                if delete_clicked:
                    try:
                        services.parts.delete(selected_part.id)
                        st.success(f"Запчасть '{selected_part.name}' успешно удалена!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка при удалении запчасти: {str(e)}")
