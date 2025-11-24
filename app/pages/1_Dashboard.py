import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, timedelta
from core.utils import get_services
from core.services import compute_wear

# Настройка matplotlib для русского языка
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['figure.figsize'] = (10, 6)

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("Сводка по статусам")

services = get_services()

# Получаем все данные
parts = services.parts.list()
equipment_list = services.equipment.list()
replacements = services.replacements.list()

if not parts:
    st.info("Нет данных для отображения. Добавьте запчасти и оборудование.")
    st.stop()

# Подсчет статусов износа
green_count = 0
yellow_count = 0
red_count = 0

wear_data = []
wear_percentage_data = []  # Для агрегации wear % по деталям
equipment_red_zone_data = []  # Для агрегации красных зон по оборудованию
wear_timeline_data = []  # Для графика износа по времени

for part in parts:
    # Находим последнюю установку этой запчасти (которая еще не заменена)
    part_replacements = [r for r in replacements if r.part_id == part.id and not r.replacement_date]

    if part_replacements:
        # Берем последнюю установку
        latest_replacement = max(part_replacements, key=lambda x: x.installation_date)
        installation_date = latest_replacement.installation_date
        replacement_date = latest_replacement.replacement_date

        # Получаем оборудование
        equipment = next((e for e in equipment_list if e.id == latest_replacement.equipment_id), None)
        equipment_name = equipment.name if equipment else 'N/A'

        percentage, remaining_days, zone = compute_wear(
            part.useful_life_days,
            installation_date,
            replacement_date,
            part.qty_in_stock,
            part.lead_time_days
        )

        wear_percentage = percentage * 100

        # Рассчитываем потребность: количество запчастей на единицу * количество единиц оборудования
        demand = part.qty_per_unit * (equipment.available_units if equipment else 1)

        wear_data.append({
            'Запчасть': part.name,
            'Оборудование': equipment_name,
            'Осталось дней': int(remaining_days),
            'Осталось %': f"{wear_percentage:.1f}%",
            'Осталось % (число)': wear_percentage,
            'Зона': zone,
            'Дата установки': installation_date,
            'На складе': part.qty_in_stock,
            'Потребность': demand,
            'ID запчасти': part.id
        })

        # Агрегат: wear % по детали
        wear_percentage_data.append({
            'Запчасть': part.name,
            'Износ %': wear_percentage,
            'Зона': zone
        })

        # Агрегат: красные зоны по оборудованию
        if zone == 'red':
            equipment_red_zone_data.append({
                'Оборудование': equipment_name,
                'Запчасть': part.name
            })

        # Данные для графика износа по времени
        if installation_date != 'N/A':
            # Генерируем точки для графика износа (каждую неделю)
            days_since_install = (date.today() - installation_date).days
            for week in range(0, min(days_since_install + 7, part.useful_life_days + 7), 7):
                check_date = installation_date + timedelta(days=week)
                if check_date <= date.today():
                    used_days = (check_date - installation_date).days
                    remaining = part.useful_life_days - used_days
                    wear_pct = (remaining / part.useful_life_days * 100) if part.useful_life_days > 0 else 0

                    wear_timeline_data.append({
                        'Дата': check_date,
                        'Оборудование': equipment_name,
                        'Запчасть': part.name,
                        'Износ %': wear_pct
                    })

        if zone == "green":
            green_count += 1
        elif zone == "yellow":
            yellow_count += 1
        else:
            red_count += 1
    else:
        # Если нет активных замен, считаем что запчасть новая или не установлена
        wear_data.append({
            'Запчасть': part.name,
            'Оборудование': 'Не установлена',
            'Осталось дней': part.useful_life_days,
            'Осталось %': '100.0%',
            'Осталось % (число)': 100.0,
            'Зона': 'green',
            'Дата установки': 'N/A',
            'На складе': part.qty_in_stock,
            'Потребность': 0,
            'ID запчасти': part.id
        })
        green_count += 1

# Метрики
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Всего запчастей", len(parts))

with col2:
    st.metric("Зеленая зона", green_count, delta=None)

with col3:
    st.metric("Желтая зона", yellow_count, delta=None)

with col4:
    st.metric("Красная зона", red_count, delta=None)

st.divider()

# Графики
if wear_data:
    df = pd.DataFrame(wear_data)
    df_wear_pct = pd.DataFrame(wear_percentage_data) if wear_percentage_data else pd.DataFrame()
    df_red_zones = pd.DataFrame(equipment_red_zone_data) if equipment_red_zone_data else pd.DataFrame()
    df_timeline = pd.DataFrame(wear_timeline_data) if wear_timeline_data else pd.DataFrame()

    # ========== 1. BAR CHART: Количество деталей по зоне ==========
    st.subheader("График 1: Количество деталей по зоне износа")

    fig1, ax1 = plt.subplots(figsize=(10, 6))
    zone_counts = df['Зона'].value_counts().sort_index()
    colors_map = {'green': '#90EE90', 'yellow': '#FFD700', 'red': '#FF6B6B'}
    colors = [colors_map.get(zone, '#808080') for zone in zone_counts.index]

    bars = ax1.bar(zone_counts.index, zone_counts.values, color=colors, edgecolor='black', linewidth=1.5)
    ax1.set_xlabel('Зона износа', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Количество деталей', fontsize=12, fontweight='bold')
    ax1.set_title('Распределение деталей по зонам износа', fontsize=14, fontweight='bold', pad=20)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # Добавляем значения на столбцы
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    st.pyplot(fig1)
    plt.close(fig1)

    st.divider()

    # ========== 2. LINE CHART: Износ по времени по оборудованию ==========
    st.subheader("График 2: Износ по времени по оборудованию")

    if not df_timeline.empty:
        fig2, ax2 = plt.subplots(figsize=(12, 6))

        # Группируем по оборудованию
        equipment_names = df_timeline['Оборудование'].unique()
        colors_equipment = plt.cm.Set3(range(len(equipment_names)))

        for idx, equipment in enumerate(equipment_names):
            equipment_data = df_timeline[df_timeline['Оборудование'] == equipment]
            equipment_data = equipment_data.sort_values('Дата')

            # Группируем по дате и берем средний износ
            daily_wear = equipment_data.groupby('Дата')['Износ %'].mean().reset_index()

            ax2.plot(daily_wear['Дата'], daily_wear['Износ %'],
                    marker='o', label=equipment, linewidth=2, markersize=4,
                    color=colors_equipment[idx])

        ax2.set_xlabel('Дата', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Износ, %', fontsize=12, fontweight='bold')
        ax2.set_title('Динамика износа запчастей по оборудованию', fontsize=14, fontweight='bold', pad=20)
        ax2.legend(loc='best', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')

        # Форматирование дат на оси X
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # Добавляем линии зон
        ax2.axhline(y=25, color='#FFD700', linestyle='--', alpha=0.5, label='Желтая зона (25%)')
        ax2.axhline(y=10, color='#FF6B6B', linestyle='--', alpha=0.5, label='Красная зона (10%)')

        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)
    else:
        st.info("Нет данных для графика износа по времени. Добавьте установленные запчасти.")

    st.divider()

    # ========== 3. STACKED BAR CHART: Склад/Потребность ==========
    st.subheader("График 3: Наличие на складе vs Потребность")

    # Подготовка данных для stacked chart
    stock_data = df[df['Оборудование'] != 'Не установлена'].copy()

    if not stock_data.empty:
        # Группируем по запчастям и суммируем потребность (так как одна запчасть может быть на разных единицах)
        stock_summary = stock_data.groupby(['ID запчасти', 'Запчасть']).agg({
            'На складе': 'first',
            'Потребность': 'sum'  # Суммируем потребность по всем установкам
        }).reset_index()

        # Рассчитываем дефицит
        stock_summary['Дефицит'] = stock_summary['Потребность'] - stock_summary['На складе']
        stock_summary['Дефицит'] = stock_summary['Дефицит'].clip(lower=0)  # Только положительные значения

        # Сортируем по потребности
        stock_summary = stock_summary.sort_values('Потребность', ascending=False).head(15)

        fig3, ax3 = plt.subplots(figsize=(12, 7))

        x_pos = range(len(stock_summary))
        width = 0.6

        # Создаем stacked bars
        bars1 = ax3.bar(x_pos, stock_summary['На складе'], width,
                       label='На складе', color='#4CAF50', edgecolor='black', linewidth=1)
        bars2 = ax3.bar(x_pos, stock_summary['Дефицит'],
                       width, bottom=stock_summary['На складе'],
                       label='Дефицит', color='#FF6B6B', edgecolor='black', linewidth=1)

        ax3.set_xlabel('Запчасть', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Количество', fontsize=12, fontweight='bold')
        ax3.set_title('Наличие на складе vs Потребность по запчастям',
                      fontsize=14, fontweight='bold', pad=20)
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(stock_summary['Запчасть'], rotation=45, ha='right', fontsize=9)
        ax3.legend(loc='upper right', fontsize=10)
        ax3.grid(axis='y', alpha=0.3, linestyle='--')

        # Добавляем значения на столбцы
        for i, (stock, deficit, need) in enumerate(zip(
            stock_summary['На складе'],
            stock_summary['Дефицит'],
            stock_summary['Потребность']
        )):
            if stock > 0:
                ax3.text(i, stock/2, f'{int(stock)}', ha='center', va='center',
                        fontsize=8, fontweight='bold', color='white')
            if deficit > 0:
                ax3.text(i, stock + deficit/2, f'{int(deficit)}',
                        ha='center', va='center', fontsize=8, fontweight='bold', color='white')

        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)
    else:
        st.info("Нет данных для графика склад/потребность.")

    st.divider()

    # ========== Дополнительные агрегаты ==========
    st.subheader("Агрегированные данные")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Износ % по каждой детали:**")
        if not df_wear_pct.empty:
            display_wear = df_wear_pct[['Запчасть', 'Износ %', 'Зона']].copy()
            display_wear = display_wear.sort_values('Износ %')
            st.dataframe(display_wear, use_container_width=True, hide_index=True)
        else:
            st.info("Нет данных")

    with col2:
        st.write("**Количество деталей в красной зоне по оборудованию:**")
        if not df_red_zones.empty:
            red_zones_summary = df_red_zones.groupby('Оборудование').size().reset_index()
            red_zones_summary.columns = ['Оборудование', 'Количество критичных деталей']
            red_zones_summary = red_zones_summary.sort_values('Количество критичных деталей', ascending=False)
            st.dataframe(red_zones_summary, use_container_width=True, hide_index=True)
        else:
            st.info("Нет критичных деталей")

    st.divider()

    # Таблица с данными
    st.subheader("Детальная информация по запчастям")

    # Цветовая индикация
    def color_zone(val):
        if val == 'green':
            return 'background-color: #90EE90'
        elif val == 'yellow':
            return 'background-color: #FFD700'
        elif val == 'red':
            return 'background-color: #FF6B6B'
        return ''

    display_df = df[['Запчасть', 'Оборудование', 'Осталось дней', 'Осталось %', 'Зона', 'Дата установки', 'На складе']].copy()
    styled_df = display_df.style.applymap(color_zone, subset=['Зона'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
else:
    st.info("Нет данных для графиков")
