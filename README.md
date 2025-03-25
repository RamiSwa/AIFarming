# 🌱 AI Farming – AI-Powered Precision Agriculture SaaS 🚜

**AI Farming** is a scalable, sensor-ready SaaS platform built to empower farmers with AI-driven soil reports, real-time weather insights, and personalized crop recommendations — all without requiring any IoT hardware. Designed as a complete MVP, it's monetized, Dockerized, and ready for production or pitching.

---

## 📸 Preview

![AI Farming Screenshot](https://github.com/user-attachments/assets/f92bf4ae-e82d-413f-906b-2236feef7962)

🔗 **Live Demo**: [smartfarmai.online](https://smartfarmai.online)

---

## 🚀 Features

- ✅ **AI Soil Analysis** – Generate expert-level PDF soil reports sent directly via email.
- ✅ **Sensor-Ready APIs** – Manual inputs now, designed for IoT expansion later.
- ✅ **Real-Time Weather** – Integrated Open-Meteo & geolocation-based insights.
- ✅ **Subscription Payments** – One-time, monthly, or annual plans via PayPal + Stripe.
- ✅ **Modular Architecture** – Five Django apps: `accounts`, `weather`, `soil`, `recommendations`, `monetization`.
- ✅ **CMS & Pages** – Includes landing, blog, contact, FAQ, privacy, and newsletter.
- ✅ **Production-Ready** – Dockerized with auth, static handling, and Postman-tested endpoints.

---

## 🧠 Tech Stack

| Category      | Tech                                                |
|---------------|------------------------------------------------------|
| **Backend**   | Django, Django REST Framework, PostgreSQL           |
| **AI Logic**  | Predictive crop suitability, soil risk analysis     |
| **Frontend**  | Django Templates, Bootstrap 5, JS (alerts & validation) |
| **Payments**  | PayPal SDK, Stripe API                              |
| **Infra/DevOps** | Docker, Railway, Whitenoise, Celery, Redis       |
| **External APIs** | Open-Meteo, Geocoding API                       |
| **Reports**   | Auto-generated PDF reports with charts & summaries |

---

## 📦 Ideal For

- 🌾 Freelancers pitching AgTech projects
- 🧠 Developers showcasing AI + SaaS delivery
- 🚀 Founders launching MVPs
- 💼 Clients seeking scalable, data-driven platforms

---

## 🧪 Features by App

- **Accounts** – Registration, login, profile, avatar, admin.
- **Weather** – Realtime forecasts via Open-Meteo + location detection.
- **Soil** – AI soil analyzer with PDF generation & email delivery.
- **Recommendations** – Risk-scored crop suggestions + map clusters.
- **Monetization** – PayPal/Stripe integration, subscription models, invoices.

---

## 🐳 Local Setup (Docker)


```bash
git clone https://github.com/yourusername/ai-farming.git
cd ai-farming
python -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

pip install -r requirements.txt

docker-compose up --build
```


⚙️ Environment Variables (.env example)

```envSECRET_KEY=
DEBUG=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_USE_TLS=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
RECAPTCHA_PRIVATE_KEY=
REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
REDIS_PASSWORD=
REDISHOST=
REDISPASSWORD=
REDISPORT=
REDISUSER=
DATABASE_URL=
POSTGRES_USER=
POSTGRES_PASSWORD=
PGPORT=
POSTGRES_DB=
R2_ACCESS_KEY_ID=
R2_BUCKET_NAME=
R2_ENDPOINT_URL=
R2_SECRET_ACCESS_KEY=
ALLOWED_HOSTS=
OPENCAGE_API_KEY=

```

📬 Contact
Feel free to reach out for collaboration or customization:

🌐 Portfolio: https://impactbyrami.com/

📫 Email: rami@impactbyrami.com
