# 🤖 SHEIN Price Calculator Bot

بوت تليغرام لحساب أسعار منتجات SHEIN بسهولة

## 📋 المتطلبات

- Python 3.8+
- حساب Railway (مجاني)
- توكن بوت تليغرام

## 🚀 خطوات النشر على Railway

### الخطوة 1: إنشاء حساب على GitHub

1. اذهب إلى [github.com](https://github.com)
2. اضغط على "Sign up"
3. أملأ البيانات (اسم مستخدم، بريد، كلمة مرور)
4. أنشئ حساباً جديداً

### الخطوة 2: إنشاء Repository على GitHub

1. اضغط على "New" (أيقونة +)
2. اختر "New repository"
3. اسم الـ Repo: `shein-price-bot` (أو أي اسم تريده)
4. اختر "Public"
5. اضغط "Create repository"

### الخطوة 3: رفع الملفات إلى GitHub

#### الطريقة الأسهل (Web Upload):

1. اضغط على "Add file" → "Upload files"
2. اختر الملفات الآتية من جهازك:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`
   - `.env.example` (بدون القيم الحقيقية)

3. اكتب رسالة: `Initial commit`
4. اضغط "Commit changes"

#### الطريقة المتقدمة (Command Line):

```bash
cd d:\rama_bot
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/shein-price-bot.git
git push -u origin main
```

### الخطوة 4: إنشاء حساب على Railway

1. اذهب إلى [railway.app](https://railway.app)
2. اضغط على "Sign up with GitHub"
3. وافق على الأذونات
4. أتم إنشاء الحساب

### الخطوة 5: نشر البوت على Railway

1. في لوحة تحكم Railway، اضغط على "New Project"
2. اختر "Deploy from GitHub repo"
3. اختر الـ Repository `shein-price-bot`
4. اضغط "Deploy"

### الخطوة 6: إضافة المتغيرات البيئية

1. في صفحة المشروع، اضغط على "Variables"
2. أضف المتغيرات التالية:

```
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_ID=YOUR_ADMIN_ID_HERE
```

3. احفظ التغييرات

### الخطوة 7: تشغيل البوت

يجب نشر عامل (worker) لتشغيل البوت:

1. اضغط على "Service" في الأعلى
2. اختر "Worker" من القائمة المنسدلة
3. اضغط "Deploy"

كل شيء تمام! 🎉

---

## 📱 الاستخدام المحلي

```bash
# تثبيت المكتبات
pip install -r requirements.txt

# تعيين متغيرات البيئة (قم بإنشاء ملف .env)
# أضف فيه التوكن والمعلومات

# تشغيل البوت
python bot.py
```

## 🔐 الأمان

- **لا تنسخ التوكن على GitHub عام**
- استخدم `.env` للبيانات الحساسة
- لا تشارك الـ Token مع أحد

## 📊 الإعدادات

تُحفظ في ملف `config.json`:
- `exchange_rate`: سعر الصرف SAR → SYP
- `clothing_fee`: أجور الملابس والأحذية
- `other_fee`: أجور المنتجات الأخرى
- `whatsapp`: رقم الواتس

يمكن تعديلها من خلال أمر `/admin`

---

## ⚙️ الأوامر

- `/start` - بداية الاستخدام
- `/admin` - قائمة إدارة الأدمن فقط

---

Made with ❤️ for SHEIN customers
