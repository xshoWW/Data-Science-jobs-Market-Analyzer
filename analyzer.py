# %% [markdown]
# # Анализ вакансий Data Scientist и ML Engineer (hh.ru)
# %%

import pandas as pd
import requests
import matplotlib.pyplot as plt
import time
import plotly.express as px

# Настройки для красивых графиков
plt.style.use('ggplot')

# %% 
# ==========================================
# БЛОК 1: Сбор данных (API hh.ru)
# ==========================================

def get_hh_vacancies(search_text, num_pages=1):
    """Собирает вакансии с hh.ru по заданному запросу"""

    url = "https://api.hh.ru/vacancies"
    all_vacancies = []

    print(f"Начинаем поиск по запросу: {search_text}...")
    
    for page in range(num_pages):
        params = {
            "text":search_text,
            "area":113, # 113 — это код региона "Россия"
            "per_page":100,
            "page":page
        }
        
        headers = {
            "User-Agent":"MyDataScienceProject/1.0 (contact:renatren25@gmail.com)"
        }

        # requests.get() - отправляет HTTP GET запрос по указанному URL с параметрами и заголовками.
        response = requests.get(url=url, params=params, headers=headers)

        if response.status_code == 200:
            # .json() - встроенный метод requests, превращает JSON-ответ сервера в Python-словарь.
            data = response.json()
            # .get() - безопасно извлекает значение по ключу. Если ключа нет, возвращает пустой список [], чтобы не было ошибки.
            items = data.get("items", [])
            # .extend() - добавляет элементы из списка items в конец списка all_vacancies (в отличие от .append, который добавил бы сам список как один элемент).
            all_vacancies.extend(items)

            print(f"Спарсили страницу {page + 1} из {num_pages}. Найдено вакансий: {len(items)}")
        else:
            print(f"Не удалось получить данные. Код ответа: {response.status_code}")
            break 

        # time.sleep() - приостанавливает выполнение скрипта на 1 секунду, чтобы не получить бан от API за спам запросами.
        time.sleep(1)

    return all_vacancies

vacancies = get_hh_vacancies(search_text="Data Scientist OR Machine Learning Engineer", num_pages=5)
print(f"\nВсего сырых вакансий: {len(vacancies)}")

if vacancies:
    first_vacancy = vacancies[0]
    print("\nКлючи (поля) одной вакансии:")
    print(list(first_vacancy.keys()))
    print(f"\nВакансия номер 1: {first_vacancy.get('name')}")
    print(f"\nЗарплата: {first_vacancy.get('salary')}")

# %%
# ==========================================
# БЛОК 2: Очистка и предобработка данных (Pandas)
# ==========================================

processed_data = []

for item in vacancies:
    salary_info = item.get('salary') or {}
    snippet_info = item.get('snippet') or {}
    
    req_text = snippet_info.get('requirement') or ""
    resp_text = snippet_info.get('responsibility') or ""
    # .strip() - удаляет лишние пробелы в начале и в конце получившейся строки.
    full_description = (req_text + " " + resp_text).strip()
    
    row = {
        'id': item.get('id'),
        'title': item.get('name') or "Без названия", 
        'employer': (item.get('employer') or {}).get('name'),
        'salary_from': salary_info.get('from'),
        'salary_to': salary_info.get('to'),
        'currency': salary_info.get('currency'),
        'experience': (item.get('experience') or {}).get('name'),
        'requirements': full_description, 
        'url': item.get('alternate_url')
    }
    processed_data.append(row)

# pd.DataFrame() - конвертирует список словарей в двумерную табличную структуру (датафрейм).
df = pd.DataFrame(processed_data)

print(f"\nВсего скачано вакансий: {len(df)}")
# .notna() создает маску из True/False (есть ли данные). .sum() считает количество True (т.е. количество заполненных ячеек).
print(f"Указана зарплата от: {df['salary_from'].notna().sum()}")
print(f"Указана зарплата до: {df['salary_to'].notna().sum()}")

# %% 
# ==========================================
# БЛОК 3: Фильтрация и расчет средней ЗП
# ==========================================

# | - это побитовое ИЛИ. Оставляем строки, где есть 'от' ИЛИ 'до'. 
# .copy() - создает независимую копию таблицы в памяти, чтобы избежать предупреждений при дальнейшем изменении данных.
df_clean = df[df["salary_from"].notna() | df["salary_to"].notna()].copy()
df_clean = df_clean[df_clean["currency"] == "RUR"]

def calculate_mean_salary(row):
    s_from = row["salary_from"]
    s_to = row["salary_to"]
    # pd.notna() - функция pandas для проверки конкретного значения на то, является ли оно "не пустотой".
    if pd.notna(s_from) and pd.notna(s_to):
        return (s_from + s_to) / 2 
    return s_from if pd.notna(s_from) else s_to 

# .apply(..., axis=1) - применяет указанную функцию построчно (axis=1 означает строки) ко всему датафрейму.
df_clean["salary_mean"] = df_clean.apply(calculate_mean_salary, axis = 1) 

print(f"Осталось вакансий для анализа (в рублях с конкретной зп): {len(df_clean)}")

# .groupby() - группирует данные по уникальным значениям опыта. 
# .agg() - применяет сразу несколько агрегирующих функций ('mean' - среднее, 'count' - количество) к сгруппированным данным.
experience_stats = df_clean.groupby("experience")["salary_mean"].agg(["mean", "count"]).round()
print("\nСтатистика по опыту работы: ")
print(experience_stats)

# %% 
# ==========================================
# БЛОК 4: Визуализация (Matplotlib)
# ==========================================

# .sort_values() - сортирует результат по возрастанию, чтобы столбцы на графике шли лесенкой.
plot_data = df_clean.groupby("experience")["salary_mean"].mean().sort_values() 

# plt.subplots() - создает "холст" (fig) и "оси/график" (ax). figsize задает размер в дюймах (ширина, высота).
fig, ax = plt.subplots(figsize=(12, 6))

# ax.bar() - рисует столбчатую диаграмму. Мы принудительно делаем индексы строками (.astype(str)), чтобы Matplotlib не запутался в типах данных.
bars = ax.bar(plot_data.index.astype(str), plot_data.values.astype(float), color='skyblue', edgecolor='navy')

for bar in bars:
    # .get_height() - метод объекта "столбец", возвращает его высоту (значение ЗП).
    yval = bar.get_height()
    # ax.text() - пишет текст на графике по координатам X и Y.
    ax.text(bar.get_x() + bar.get_width()/2, yval + 5000, 
            f'{int(yval):,}', ha='center', va='bottom', fontweight='bold') 
    
ax.set_title("Средняя зарплата по опыту работы", fontsize=12)
ax.set_xlabel("Опыт работы", fontsize=12)
ax.set_ylabel("Средняя зарплата", fontsize=12)

# ax.grid() - включает сетку на фоне графика для удобства чтения значений.
ax.grid(axis='y', linestyle='--', alpha=0.7)

# plt.xticks(rotation=15) - немного поворачивает подписи по оси X, чтобы они не накладывались друг на друга.
plt.xticks(rotation=15)
# plt.tight_layout() - автоматически подгоняет отступы, чтобы всё влезло в картинку без обрезаний.
plt.tight_layout()

# %% 
# ==========================================
# БЛОК 5: Навыки + Фундаментальная математика
# ==========================================

keywords = [
    'Python', 'SQL', 'PyTorch', 'TensorFlow', 'Pandas', 'Spark', 'Docker', 'Git', 'MLOps',
    'Statistics', 'Статистика', 'Probability', 'Теорвер', 'Теория вероятностей',
    'Linear Algebra', 'Линейная алгебра', 'Линал', 'Calculus', 'Мат анализ', 'Математический анализ',
    'Machine Learning', 'Обучение моделей'
]

skill_counts = {}

groups = {
    'Math/Stats': ['statistics', 'статистика', 'probability', 'теорвер', 'теория вероятностей'],
    'Linear Algebra': ['linear algebra', 'линейная алгебра', 'линал'],
    'Calculus': ['calculus', 'мат анализ', 'математический анализ'],
    'Python': ['python'],
    'SQL': ['sql'],
    'DL Frameworks': ['pytorch', 'tensorflow'],
    'ML Infrastructure': ['docker', 'git', 'mlops', 'spark']
}

# .dropna() - выкидывает пустые значения (NaN) из колонки requirements, чтобы при попытке привести к нижнему регистру не вылезла ошибка.
for req in df_clean['requirements'].dropna():
    req_lower = req.lower()
    for category, aliases in groups.items():
        # any() - встроенная функция Python, возвращает True, если хотя бы один элемент (алиас) найден в тексте вакансии.
        if any(alias.lower() in req_lower for alias in aliases):
            # .get(category, 0) - берет текущее значение счетчика навыка. Если его еще нет, возвращает 0.
            skill_counts[category] = skill_counts.get(category, 0) + 1

# pd.Series() - преобразует словарь в одномерный массив (колонку) Pandas для удобной отрисовки.
skills_series = pd.Series(skill_counts).sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(10, 7))

# .plot(kind='barh') - метод Pandas, который под капотом вызывает Matplotlib и строит горизонтальную столбчатую диаграмму (bar horizontal).
skills_series.plot(kind='barh', color='mediumseagreen', edgecolor='black', ax=ax)

ax.set_title('Востребованность навыков и мат. базы', fontsize=14)
ax.set_xlabel('Количество уникальных вакансий, в которых встретился навык')
plt.tight_layout()
plt.show()

# %% 
# ==========================================
# БЛОК 6: Финальный анализ и визуализация
# ==========================================
import plotly.express as px

skill_groups = {
    'Python': ['python'],
    'SQL': ['sql'],
    'ML/DL': ['pytorch', 'tensorflow', 'keras', 'machine learning', 'обучение моделей'],
    'Math/Stats': ['statistics', 'статистика', 'probability', 'теорвер', 'теория вероятностей', 'math', 'математика'],
    'Linear Algebra': ['linear algebra', 'линейная алгебра', 'линал'],
    'Calculus': ['calculus', 'мат анализ', 'математический анализ'],
    'Infrastructure': ['docker', 'git', 'mlops', 'spark', 'kubernetes', 'linux']
}

def advanced_skill_count(row):
    text = (str(row['requirements']) + " " + str(row['title'])).lower()
    count = 0
    for category, aliases in skill_groups.items():
        if any(alias in text for alias in aliases):
            count += 1
    
    if count == 0:
        if any(word in text for word in ['senior', 'lead', 'ml', 'machine learning', 'scientist']):
            count = 2
    return count

exp_map = {'Нет опыта': 0, 'От 1 года до 3 лет': 2, 'От 3 до 6 лет': 4.5, 'Более 6 лет': 7}

# .assign() - добавляет новые колонки в датафрейм (или перезаписывает старые), возвращая измененную копию таблицы. Более безопасный метод, чем df['col'] = ...
df_clean = df_clean.assign(
    skills_count = df_clean.apply(advanced_skill_count, axis=1),
    # .map() - заменяет текстовые значения опыта на числа согласно словарю exp_map.
    exp_years = df_clean['experience'].map(exp_map)
)

# .corr() - вычисляет коэффициент корреляции Пирсона между двумя колонками (от -1 до 1).
correlation_val = df_clean["salary_mean"].corr(df_clean["skills_count"]).__round__(2)

# px.scatter() - создает интерактивную точечную (пузырьковую) диаграмму.
# size - размер точки зависит от колонки skills_count. color - цветовая шкала тоже зависит от нее.
# hover_data - определяет, какие данные показывать во всплывающей подсказке при наведении мыши.
fig = px.scatter(
    df_clean, 
    x="exp_years", 
    y="salary_mean", 
    size="skills_count", 
    color="skills_count",
    hover_name="title", 
    hover_data=["employer", "salary_mean", "skills_count"],
    title="Связь опыта, стека и зарплаты в DS/ML",
    labels={"exp_years": "Опыт (годы)", "salary_mean": "Средняя ЗП (руб)", "skills_count": "Категории навыков"},
    color_continuous_scale=px.colors.sequential.Viridis,
    template="plotly_white", 
    size_max=35
)

# fig.update_layout() - модифицирует оси графика. Здесь мы вручную расставляем подписи (ticktext) по оси X на конкретных позициях (tickvals).
fig.update_layout(xaxis=dict(tickmode='array', tickvals=[0, 2, 4.5, 7], ticktext=['0', '1-3', '3-6', '6+']))
fig.show()

print("\n" + "="*50)
print("РЕЗУЛЬТАТЫ АНАЛИЗА ТОП-ВАКАНСИЙ")
print("="*50)
# .nlargest(3, 'col') - быстро находит 3 строки с самыми большими значениями в указанной колонке.
top_3 = df_clean.nlargest(3, 'salary_mean')
print(f"Коэффициент корреляции (Навыки/ЗП): {correlation_val} ")
# .iterrows() - позволяет итерироваться по датафрейму, возвращая индекс (i) и саму строку (row) как Pandas Series.
for i, row in top_3.iterrows():
    print(f" {row['salary_mean']:,} руб. | {row['title']} | {row['employer']}")
    print(f"   Скилл-фактор: {row['skills_count']} (на основе заголовка и требований)\n")

# %%
