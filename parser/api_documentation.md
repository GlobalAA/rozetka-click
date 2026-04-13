# Документація API (rozetka-click)

Цей документ описує існуючі API "ручки" (ендпоінти) сервісу `rozetka-click`, які необхідні для інтеграції та створення Desktop-додатку. 
Сервіс працює на базі `aiohttp` за замовчуванням на хості `0.0.0.0` та порту `8080`.

## Ендпоінти

### 1. Перевірка статусу парсера
- **URL**: `/api/status`
- **Метод**: `GET`
- **Опис**: Повертає поточний статус парсера (чи запущений він у даний момент на рівні БД або завдання).

**Відповідь (200 OK):**
```json
{
  "running": true
}
```

---

### 2. Запуск парсера
- **URL**: `/api/start`
- **Метод**: `POST`
- **Опис**: Запускає фоновий процес парсингу. Якщо парсер вже запущений, сервер поверне помилку, перешкоджаючи дублюванню процесів.

**Приклад успішної відповіді (200 OK):**
```json
{
  "status": "ok",
  "message": "Parser started"
}
```

**Приклад помилки (400 Bad Request) - парсер вже працює:**
```json
{
  "status": "error",
  "message": "Parser is already running"
}
```

---

### 3. Зупинка парсера
- **URL**: `/api/stop`
- **Метод**: `POST`
- **Опис**: Примусово зупиняє фонове завдання парсера (cancels the task) та оновлює статус у базі даних (`status = False`).

**Приклад успішної відповіді (200 OK):**
```json
{
  "status": "ok",
  "message": "Parser stopped" 
}
```
*(Примітка: Якщо парсер не було локально запущено як завдання (task), але він міститься в БД як запущений, API примусово змінить статус в БД і замість цього поверне `"message": "Forced status to stopped in DB"`).*

**Приклад помилки (400 Bad Request) - парсер до цього не був запущений:**
```json
{
  "status": "error",
  "message": "Parser is not running"
}
```

---

### 4. Додавання проксі
- **URL**: `/api/proxy`
- **Метод**: `POST`
- **Опис**: Додає новий проксі сервер до бази даних. Дані передаються у форматі JSON у тілі запиту.

**Тіло запиту (JSON):**
```json
{
  "server": "http://proxy.example.com:8000",
  "username": "user123",
  "password": "password123"
}
```
*(Всі 3 поля є обов'язковими).*

**Приклад успішної відповіді (200 OK):**
```json
{
  "status": "ok",
  "message": "Proxy added successfully"
}
```

**Приклад помилки (400 Bad Request) - передано не всі параметри:**
```json
{
  "status": "error",
  "message": "Invalid request parameters. Expected: server, username, password"
}
```

---

### 5. Додавання магазину (Shop)
- **URL**: `/api/shop`
- **Метод**: `POST`
- **Опис**: Додає дані про новий магазин до бази даних для його подальшого парсингу. 

**Тіло запиту (JSON):**
```json
{
  "url": "https://rozetka.com.ua/.../...",
  "category_id": 1
}
```
*(Обидва поля є обов'язковими).*

**Приклад успішної відповіді (200 OK):**
```json
{
  "status": "ok",
  "message": "Shop added successfully",
  "shop_id": 1 
}
```
*(Повертається `shop_id` - унікальний ідентифікатор створеного запису в базі даних).*

**Приклад помилки (400 Bad Request) - передано не всі параметри:**
```json
{
  "status": "error",
  "message": "Invalid request parameters. Expected: url, category_id"
}
```

---

### 6. Додавання категорії (Category)
- **URL**: `/api/category`
- **Метод**: `POST`
- **Опис**: Додає нову категорію товарів до бази даних.

**Тіло запиту (JSON):**
```json
{
  "target_product": "Назва товару",
  "target_category": "Назва категорії"
}
```
*(Обидва поля є обов'язковими).*

**Приклад успішної відповіді (200 OK):**
```json
{
  "status": "ok",
  "message": "Category added successfully",
  "category_id": 1 
}
```

**Приклад помилки (400 Bad Request) - передано не всі параметри:**
```json
{
  "status": "error",
  "message": "Invalid request parameters. Expected: target_product, target_category"
}
```

---

### 7. Отримання списку категорій
- **URL**: `/api/categories`
- **Метод**: `GET`
- **Опис**: Повертає список всіх категорій, які збережено у базі.

**Відповідь (200 OK):**
```json
{
  "status": "ok",
  "categories": [
    {
      "id": 1,
      "target_product": "Назва товару",
      "target_category": "Назва категорії"
    }
  ]
}
```

---

### 8. Отримання списку магазинів (Shops)
- **URL**: `/api/shops`
- **Метод**: `GET`
- **Опис**: Повертає список всіх магазинів, які збережено у базі.

**Відповідь (200 OK):**
```json
{
  "status": "ok",
  "shops": [
    {
      "id": 1,
      "url": "https://rozetka.com.ua/...",
      "target_product": "Назва товару",
      "target_category": "Назва категорії"
    }
  ]
}
```

---

### 9. Отримання списку проксі (Proxies)
- **URL**: `/api/proxies`
- **Метод**: `GET`
- **Опис**: Повертає список всіх проксі-серверів. Паролі в цьому ендпоінті не повертаються для безпеки.

**Відповідь (200 OK):**
```json
{
  "status": "ok",
  "proxies": [
    {
      "id": 1,
      "server": "http://proxy.example.com:8000",
      "username": "user123"
    }
  ]
}
```
