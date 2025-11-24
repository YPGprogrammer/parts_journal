"""Procurement Plan - план закупок запчастей"""
import streamlit as st
import pandas as pd
from datetime import date
from core.utils import get_services
from core.services import compute_wear

st.set_page_config(page_title="План закупок", layout="wide")
st.title("План закупок запчастей")

services = get_services()

# Получаем данные
parts = services.parts.list()
equipment_list = services.equipment.list()
replacements = services.replacements.list()

if not parts:
    st.warning("Нет запчастей для формирования плана закупок.")
    st.stop()

if not replacements:
    st.warning("Нет установленных запчастей для формирования плана закупок.")
    st.stop()

# Фильтры
col1, col2 = st.columns(2)
with col1:
    filter_equipment = st.selectbox(
        "Фильтр по оборудованию",
        options=[None] + equipment_list,
        format_func=lambda x: "Все оборудование" if x is None else x.name
    )

with col2:
    show_only_critical = st.checkbox("Показать только критичные (красная/желтая зона)", value=False)

# Формируем план закупок
procurement_plan = []

for part in parts:
    # Находим все установки этой запчасти
    part_replacements = [r for r in replacements if r.part_id == part.id]

    if not part_replacements:
        continue

    # Для каждой установки рассчитываем план закупки
    for replacement in part_replacements:
        if replacement.replacement_date:
            # Если уже заменена, пропускаем
            continue

        equipment = next((e for e in equipment_list if e.id == replacement.equipment_id), None)
        if not equipment:
            continue

        # Применяем фильтр по оборудованию
        if filter_equipment and equipment.id != filter_equipment.id:
            continue

        # Рассчитываем износ
        percentage, remaining_days, zone = compute_wear(
            part.useful_life_days,
            replacement.installation_date,
            replacement.replacement_date,
            part.qty_in_stock,
            part.lead_time_days
        )

        # Фильтр по критичности
        if show_only_critical and zone == "green":
            continue

        # Рассчитываем план закупки
        plan_data = services.procurement.calculate_for_part(
            part,
            replacement.installation_date
        )

        procurement_plan.append({
            'Запчасть': part.name,
            'Оборудование': equipment.name,
            'Серийный номер': replacement.unit_serial_number,
            'Дата установки': replacement.installation_date,
            'Осталось дней': int(remaining_days),
            'Осталось %': f"{percentage * 100:.1f}%",
            'Зона': zone,
            'На складе': part.qty_in_stock,
            'Срок закупки (дней)': part.lead_time_days,
            'Дата окончания срока службы': plan_data['failure_date'],
            'Последняя дата инициации закупки': plan_data['latest_init_date'],
            'Дата закупки': plan_data['latest_purchase_date'],
            'Дата получения': plan_data.get('receipt_date', plan_data['latest_purchase_date'])
        })

if procurement_plan:
    df = pd.DataFrame(procurement_plan)

    # Сортируем по дате инициации закупки
    df = df.sort_values('Последняя дата инициации закупки')

    # Статистика
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Всего позиций", len(df))
    with col2:
        red_count = len(df[df['Зона'] == 'red'])
        st.metric("Критичных", red_count)
    with col3:
        yellow_count = len(df[df['Зона'] == 'yellow'])
        st.metric("Требуют внимания", yellow_count)
    with col4:
        no_stock = len(df[df['На складе'] == 0])
        st.metric("Нет на складе", no_stock)

    st.divider()

    # Цветовая индикация
    def color_zone(val):
        if val == 'green':
            return 'background-color: #90EE90'
        elif val == 'yellow':
            return 'background-color: #FFD700'
        elif val == 'red':
            return 'background-color: #FF6B6B'
        return ''

    def color_stock(val):
        if val == 0:
            return 'background-color: #FFB6C1'
        return ''

    # Отображаем таблицу
    display_df = df[[
        'Запчасть',
        'Оборудование',
        'Серийный номер',
        'Дата установки',
        'Осталось дней',
        'Осталось %',
        'Зона',
        'На складе',
        'Последняя дата инициации закупки',
        'Дата закупки',
        'Дата получения',
        'Дата окончания срока службы'
    ]].copy()

    styled_df = display_df.style.applymap(color_zone, subset=['Зона']).applymap(color_stock, subset=['На складе'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Графики
    st.divider()
    st.subheader("Аналитика")

    col1, col2 = st.columns(2)

    with col1:
        st.write("Распределение по зонам износа")
        zone_counts = df['Зона'].value_counts()
        zone_colors = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}
        zone_labels = {k: f"{zone_colors.get(k, '')} {k.capitalize()}" for k in zone_counts.index}

        chart_data = pd.DataFrame({
            'Зона': [zone_labels.get(k, k) for k in zone_counts.index],
            'Количество': zone_counts.values
        })
        st.bar_chart(chart_data.set_index('Зона'))

    with col2:
        st.write("Запчасти без запаса на складе")
        stock_data = df.groupby('На складе').size()
        st.bar_chart(stock_data)

else:
    st.info("Нет данных для формирования плана закупок. Убедитесь, что есть установленные запчасти.")
