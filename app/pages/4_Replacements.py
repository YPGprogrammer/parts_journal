import streamlit as st
import pandas as pd
from datetime import date
from core.utils import get_services

st.set_page_config(page_title="Журнал замен", layout="wide")
st.title("Журнал замен запчастей")

services = get_services()

# Получаем справочники
parts = services.parts.list()
equipment_list = services.equipment.list()
workshops = services.workshops.list()
replacement_types = services.replacement_types.list()

if not parts:
    st.warning("Сначала добавьте запчасти.")
    st.stop()

if not equipment_list:
    st.warning("Сначала добавьте оборудование.")
    st.stop()

if not replacement_types:
    st.warning("Типы замен не инициализированы. Перезагрузите страницу.")
    st.stop()

# Если нет мастерских, показываем форму для создания
if not workshops:
    st.warning("Нет мастерских. Создайте первую мастерскую:")
    with st.form("create_first_workshop", clear_on_submit=True):
        name = st.text_input("Название мастерской *", max_chars=50)
        addr = st.text_input("Адрес мастерской *", max_chars=100)
        submitted = st.form_submit_button("Создать мастерскую", type="primary")
        if submitted:
            if name and addr:
                try:
                    services.workshops.create(name=name, addr=addr)
                    st.success("Мастерская создана!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {str(e)}")
            else:
                st.error("Заполните все поля")
    st.stop()

# Создаем словари для быстрого поиска
parts_dict = {p.id: p.name for p in parts}
equipment_dict = {eq.id: eq.name for eq in equipment_list}
workshops_dict = {w.id: w.name for w in workshops}
types_dict = {t.id: t.name.value for t in replacement_types}

# Вкладки
tab1, tab2, tab3 = st.tabs(["История замен", "Добавить замену", "Редактировать замену"])

with tab1:
    st.subheader("История замен")

    # Фильтр по оборудованию
    filter_equipment = st.selectbox(
        "Фильтр по оборудованию",
        options=[None] + equipment_list,
        format_func=lambda x: "Все оборудование" if x is None else x.name
    )

    # Получаем замены
    if filter_equipment:
        replacements = services.replacements.get_by_equipment(filter_equipment.id)
    else:
        replacements = services.replacements.list()

    if replacements:
        # Формируем данные для таблицы
        replacements_data = []
        for rep in replacements:
            replacements_data.append({
                'ID': rep.id,
                'Запчасть': parts_dict.get(rep.part_id, "Неизвестно"),
                'Оборудование': equipment_dict.get(rep.equipment_id, "Неизвестно"),
                'Серийный номер': rep.unit_serial_number,
                'Мастерская': workshops_dict.get(rep.workshop_id, "Неизвестно"),
                'Тип замены': types_dict.get(rep.replacement_type_id, "Неизвестно"),
                'Дата установки': rep.installation_date,
                'Дата замены': rep.replacement_date if rep.replacement_date else "Не заменена",
                'Комментарий': rep.comments if rep.comments else "-"
            })

        df = pd.DataFrame(replacements_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Статистика
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего записей", len(replacements))
        with col2:
            replaced_count = len([r for r in replacements if r.replacement_date])
            st.metric("Заменено", replaced_count)
        with col3:
            not_replaced_count = len([r for r in replacements if not r.replacement_date])
            st.metric("В эксплуатации", not_replaced_count)
    else:
        st.info("Нет записей о заменах. Добавьте первую запись во вкладке 'Добавить замену'.")

with tab2:
    st.subheader("Добавить новую замену")

    with st.form("add_replacement_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            selected_part = st.selectbox(
                "Запчасть *",
                options=parts,
                format_func=lambda p: f"{p.name} (ID: {p.id})"
            )
            selected_equipment = st.selectbox(
                "Оборудование *",
                options=equipment_list,
                format_func=lambda e: f"{e.name} (ID: {e.id})"
            )
            unit_serial_number = st.text_input("Серийный номер единицы оборудования *", max_chars=30)
            selected_workshop = st.selectbox(
                "Мастерская *",
                options=workshops,
                format_func=lambda w: f"{w.name} - {w.addr}"
            )

        with col2:
            selected_type = st.selectbox(
                "Тип замены *",
                options=replacement_types,
                format_func=lambda t: t.name.value
            )
            installation_date = st.date_input(
                "Дата установки *",
                value=date.today()
            )
            replacement_date = st.date_input(
                "Дата замены (если уже заменена)",
                value=None
            )
            comments = st.text_area("Комментарий", max_chars=200)

        submitted = st.form_submit_button("Добавить замену", type="primary")

        if submitted:
            if not unit_serial_number:
                st.error("Пожалуйста, заполните серийный номер")
            elif replacement_date and replacement_date < installation_date:
                st.error("Дата замены не может быть раньше даты установки")
            else:
                try:
                    new_replacement = services.replacements.create(
                        part_id=selected_part.id,
                        equipment_id=selected_equipment.id,
                        unit_serial_number=unit_serial_number,
                        workshop_id=selected_workshop.id,
                        replacement_type_id=selected_type.id,
                        installation_date=installation_date,
                        replacement_date=replacement_date if replacement_date else None,
                        comments=comments if comments else None
                    )
                    st.success(f"Замена успешно добавлена!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка при добавлении замены: {str(e)}")

with tab3:
    st.subheader("Редактировать замену")

    replacements = services.replacements.list()
    if not replacements:
        st.info("Нет записей для редактирования.")
    else:
        selected_replacement = st.selectbox(
            "Выберите замену для редактирования",
            options=replacements,
            format_func=lambda r: f"{parts_dict.get(r.part_id, 'N/A')} - {equipment_dict.get(r.equipment_id, 'N/A')} ({r.installation_date})"
        )

        if selected_replacement:
            with st.form("edit_replacement_form"):
                col1, col2 = st.columns(2)

                with col1:
                    selected_part = st.selectbox(
                        "Запчасть *",
                        options=parts,
                        format_func=lambda p: f"{p.name} (ID: {p.id})",
                        index=[p.id for p in parts].index(selected_replacement.part_id) if selected_replacement.part_id in [p.id for p in parts] else 0
                    )
                    selected_equipment = st.selectbox(
                        "Оборудование *",
                        options=equipment_list,
                        format_func=lambda e: f"{e.name} (ID: {e.id})",
                        index=[e.id for e in equipment_list].index(selected_replacement.equipment_id) if selected_replacement.equipment_id in [e.id for e in equipment_list] else 0
                    )
                    unit_serial_number = st.text_input(
                        "Серийный номер единицы оборудования *",
                        value=selected_replacement.unit_serial_number,
                        max_chars=30
                    )
                    selected_workshop = st.selectbox(
                        "Мастерская *",
                        options=workshops,
                        format_func=lambda w: f"{w.name} - {w.addr}",
                        index=[w.id for w in workshops].index(selected_replacement.workshop_id) if selected_replacement.workshop_id in [w.id for w in workshops] else 0
                    )

                with col2:
                    selected_type = st.selectbox(
                        "Тип замены *",
                        options=replacement_types,
                        format_func=lambda t: t.name.value,
                        index=[t.id for t in replacement_types].index(selected_replacement.replacement_type_id) if selected_replacement.replacement_type_id in [t.id for t in replacement_types] else 0
                    )
                    installation_date = st.date_input(
                        "Дата установки *",
                        value=selected_replacement.installation_date
                    )
                    replacement_date = st.date_input(
                        "Дата замены (если уже заменена)",
                        value=selected_replacement.replacement_date
                    )
                    comments = st.text_area(
                        "Комментарий",
                        value=selected_replacement.comments if selected_replacement.comments else "",
                        max_chars=200
                    )

                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Сохранить изменения", type="primary")
                with col2:
                    delete_clicked = st.form_submit_button("Удалить замену", type="secondary")

                if submitted:
                    if not unit_serial_number:
                        st.error("Пожалуйста, заполните серийный номер")
                    elif replacement_date and replacement_date < installation_date:
                        st.error("Дата замены не может быть раньше даты установки")
                    else:
                        try:
                            services.replacements.update(
                                selected_replacement.id,
                                part_id=selected_part.id,
                                equipment_id=selected_equipment.id,
                                unit_serial_number=unit_serial_number,
                                workshop_id=selected_workshop.id,
                                replacement_type_id=selected_type.id,
                                installation_date=installation_date,
                                replacement_date=replacement_date if replacement_date else None,
                                comments=comments if comments else None
                            )
                            st.success(f"Замена успешно обновлена!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка при обновлении замены: {str(e)}")

                if delete_clicked:
                    try:
                        services.replacements.delete(selected_replacement.id)
                        st.success(f"Замена успешно удалена!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка при удалении замены: {str(e)}")
