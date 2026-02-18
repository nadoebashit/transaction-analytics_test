# Transaction Analytics API

**Шаг 1: Клонируем проект**

```bash
git clone <repository-url>
cd transaction-analytics_test
```

**Шаг 2: Запускаем сервисы**

```bash
docker-compose up -d
```

**Шаг 3: Создаем таблицы в базе**

```bash
docker-compose exec api alembic upgrade head
```

**Шаг 4: Добавляем тестовые данные**

```bash
docker-compose exec api python seed_data.py
```

**Шаг 5: Проверяем, что все работает**

```bash
curl http://localhost:8000/health
```

Должен увидеть: `{"status": "healthy"}`

**Готово!** Теперь можешь открыть http://localhost:8000/docs и увидеть всю документацию API.

## Как пользоваться API?

### Базовый адрес: `http://localhost:8000`

### Основные эндпоинты:

**Проверка здоровья**

- `GET /health` — Просто проверяем, что сервис жив

**Аналитика транзакций**

- `GET /report/` — Главная функция для анализа транзакций
  - Можно фильтровать по датам, статусам, типам
  - Добавлять средние значения, минимумы, максимумы
  - Включать тренды по дням и месяцам
  - Показывать топ-транзакции

**Быстрая сводка**

- `GET /report/summary` — Краткая статистика за последние N дней

**Аналитика по странам**

- `GET /report/by-country` — Смотрим, в каких странах что происходит
  - Сортировка по количеству, сумме или среднему
  - Ограничение топ-N стран

### Примеры запросов:

**Хочу увидеть общую статистику:**

```bash
curl "http://localhost:8000/report/?include_avg=true"
```

**Нужны данные по конкретным датам:**

```bash
curl "http://localhost:8000/report/?start_date=2024-01-01&end_date=2024-01-31&include_daily_shift=true"
```

**Какие страны самые активные?**

```bash
curl "http://localhost:8000/report/by-country?sort_by=total&top_n=5"
```

**Быстрая сводка за последний месяц:**

```bash
curl "http://localhost:8000/report/summary?days=30"
```

## Тестирование

### Все тесты сразу

```bash
docker-compose exec api python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

### Отдельные группы тестов

```bash
# Только тесты моделей данных
docker-compose exec api python -m pytest tests/test_models.py -v

# Только тесты основного API
docker-compose exec api python -m pytest tests/test_reports.py -v

# Только тесты API по странам
docker-compose exec api python -m pytest tests/test_country_reports.py -v
```

### Хочешь красивый отчет покрытия?

```bash
# Создаем HTML отчет
docker-compose exec api python -m pytest tests/ --cov=app --cov-report=html

# Открываем в браузере
open htmlcov/index.html
```

## Подключение к базе данных

### Как подключиться к базе?

```bash
# Прямо в консоли PostgreSQL
docker-compose exec postgres psql -U user -d transaction_analytics

# Или через pgAdmin
open http://localhost:5050
```

### Миграции — обновляем структуру БД

```bash
# Создать новую миграцию
docker-compose exec api alembic revision --autogenerate -m "Добавил новое поле"

# Применить все миграции
docker-compose exec api alembic upgrade head

# Откатить последнюю миграцию
docker-compose exec api alembic downgrade -1
```

### Тестовые данные

```bash

docker-compose exec api python seed_data.py


```

### Локальная разработка (если хочешь кодить)

```bash
# Ставим зависимости
pip install -r requirements.txt

# Создаем виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Запускаем локально
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Если что-то пошло не так... 🛠️

### Частые проблемы и их решения

**"Не подключается к базе данных"**

```bash
# Проверяем, работает ли база
docker-compose logs postgres

# Перезапускаем все сервисы
docker-compose down && docker-compose up -d
```

**"Миграции не применяются"**

```bash
# Смотрим текущий статус
docker-compose exec api alembic current

# Принудительно применяем
docker-compose exec api alembic upgrade head
```

**"API не отвечает"**

```bash
# Смотрим логи API
docker-compose logs api

# Проверяем статус контейнеров
docker-compose ps
```

```bash
# Простая проверка здоровья
curl http://localhost:8000/health

# Проверка подключения к БД из приложения
docker-compose exec api python -c "
from app.database import engine
try:
    with engine.connect() as conn:
        print('База данных: ✅ OK')
except Exception as e:
    print(f'База данных: ❌ Ошибка - {e}')
"
```

## Мониторинг 📊

```bash
# Логи в реальном времени
docker-compose logs -f api

# Нагрузка на систему
docker stats
```

### Статистика базы данных

```bash
# Сколько активных подключений
docker-compose exec postgres psql -U user -d transaction_analytics -c "
SELECT count(*) FROM pg_stat_activity;
"

# Размер базы данных
docker-compose exec postgres psql -U user -d transaction_analytics -c "
SELECT pg_size_pretty(pg_database_size('transaction_analytics'));
"
```
