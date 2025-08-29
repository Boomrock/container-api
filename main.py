import os
import re
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, validator
from passlib.context import CryptContext
from datetime import datetime

load_dotenv()

app = FastAPI(title="Container Tracking API", version="1.0")

# Настройка HTTP Basic Auth
security = HTTPBasic()

# Настройка хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Модель для создания контейнера
class ContainerCreate(BaseModel):
    container_number: str = Field(
        ..., 
        min_length=11, 
        max_length=11,
        description="Формат: ТРИ ЗАГЛАВНЫЕ ЛАТИНСКИЕ БУКВЫ + 'U' + СЕМЬ ЦИФР (пример: CXXU7788345)"
    )
    cost: float = Field(
        ..., 
        gt=0,
        description="Положительное число с двумя знаками после запятой"
    )

    @validator('container_number')
    def validate_container_number(cls, v):
        if not re.match(r'^[A-Z]{3}U\d{7}$', v):
            raise ValueError('Неверный формат номера контейнера. Должен быть: ТРИ ЗАГЛАВНЫЕ БУКВЫ + "U" + СЕМЬ ЦИФР (пример: CXXU7788345)')
        return v

    @validator('cost')
    def validate_cost(cls, v):
        if round(v, 2) != v:
            raise ValueError('Стоимость должна иметь ровно два знака после запятой')
        return v

# Получение подключения к БД
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "atkuser"),
            password=os.getenv("DB_PASSWORD", "atkpass"),
            database=os.getenv("DB_NAME", "atk"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        return connection
    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка подключения к базе данных"
        )

# Проверка авторизации
def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (credentials.username,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # Проверка пароля с использованием bcrypt
        if not pwd_context.verify(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username
    finally:
        connection.close()

# Эндпоинт: Поиск контейнеров по номеру
@app.get("/api/containers", response_model=list)
def search_containers(
    q: str = None,
    current_user: str = Depends(get_current_user)
):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        
        if q:
            # Поиск по подстроке
            query = "SELECT id, container_number, cost FROM containers WHERE container_number LIKE %s"
            params = (f"%{q}%",)
        else:
            # Первые 50 записей
            query = "SELECT id, container_number, cost FROM containers LIMIT 50"
            params = ()
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results
    finally:
        connection.close()

# Эндпоинт: Поиск контейнеров по стоимости
@app.get("/api/containers/by-cost", response_model=list)
def search_containers_by_cost(
    cost: float = None,
    min: float = None,
    max: float = None,
    current_user: str = Depends(get_current_user)
):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT id, container_number, cost FROM containers WHERE 1=1"
        params = []
        
        if cost is not None:
            query += " AND cost = %s"
            params.append(cost)
        else:
            if min is not None:
                query += " AND cost >= %s"
                params.append(min)
            if max is not None:
                query += " AND cost <= %s"
                params.append(max)
        
        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        cursor.close()
        return results
    finally:
        connection.close()

# Эндпоинт: Добавление контейнера
@app.post("/api/containers", response_model=dict)
def create_container(
    container: ContainerCreate,
    current_user: str = Depends(get_current_user)
):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        # Проверка уникальности номера
        cursor.execute("SELECT id FROM containers WHERE container_number = %s", (container.container_number,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail="Контейнер с таким номером уже существует"
            )
        
        # Вставка новой записи
        cursor.execute(
            "INSERT INTO containers (container_number, cost) VALUES (%s, %s)",
            (container.container_number, container.cost)
        )
        connection.commit()
        
        # Получение ID новой записи
        container_id = cursor.lastrowid
        
        return {
            "id": container_id,
            "container_number": container.container_number,
            "cost": container.cost
        }
    except mysql.connector.IntegrityError as e:
        # Обработка ошибки колизии
        if e.errno == 1062:
            raise HTTPException(
                status_code=409,
                detail="Контейнер с таким номером уже существует"
            )
        raise HTTPException(
            status_code=400,
            detail="Ошибка при добавлении контейнера"
        )
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)