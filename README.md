# 🛒 E-Commerce Backend API

A scalable E-commerce REST API built using Django and Django REST Framework.

## 🚀 Features

- JWT Authentication (Register, Login, Logout)
- Email Verification & Password Reset
- Product & Category Management
- Cart & Wishlist System
- Order Creation Workflow
- Coupon Validation
- Payment Integration (Intent + Webhook)
- Admin Dashboard APIs
- Role-Based Access Control
- Pagination, Filtering & Search

---

## 🛠 Tech Stack

- Python
- Django
- Django REST Framework
- SQLite / PostgreSQL
- JWT Authentication
- Git & GitHub

---

## 📂 Project Structure

```
api/                # Core app (models, views, serializers)
ecommerce/          # Project settings
manage.py
```

---

## ⚙️ Installation & Setup

1️⃣ Clone repository

```
git clone https://github.com/nitish1238/ecommerce-backend.git
cd ecommerce-backend
```

2️⃣ Create virtual environment

```
python -m venv venv
venv\Scripts\activate
```

3️⃣ Install dependencies

```
pip install -r requirements.txt
```

4️⃣ Run migrations

```
python manage.py migrate
```

5️⃣ Start server

```
python manage.py runserver
```

Server runs at:
```
http://127.0.0.1:8000/
```

---

## 🔐 Authentication

This project uses JWT-based authentication.

Protected endpoints require:

```
Authorization: Bearer <your_access_token>
```

---

## 📌 Author

Nitish Kumar