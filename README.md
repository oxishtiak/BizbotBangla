# BizBot Bangla 🤖
## চালানোর নিয়ম (A to Z)

### Step 1 — Python ইনস্টল করুন
https://www.python.org/downloads/ থেকে Python 3.10+ ডাউনলোড করুন

### Step 2 — ZIP extract করুন
BizBot_Bangla_v2.zip extract করুন। একটা folder দেখবেন: bizbot2

### Step 3 — Terminal/Command Prompt খুলুন
Windows: bizbot2 folder এ ঢুকে Shift+Right Click → "Open PowerShell/Terminal here"
Mac/Linux: Terminal এ cd bizbot2

### Step 4 — Django ইনস্টল করুন
```
pip install django pandas openpyxl
```

### Step 5 — Database তৈরি করুন
```
python manage.py migrate
```

### Step 6 — চালু করুন
```
python manage.py runserver
```

### Step 7 — Browser এ খুলুন
http://127.0.0.1:8000

---
## Features
✅ Login / Register (দোকানের নাম দিয়ে account)
✅ বিক্রয় Voice — বলুন কী বেচলেন
✅ ক্রয় Voice — বলুন দোকানের জন্য কী কিনলেন
✅ আজ / সাপ্তাহিক / মাসিক হিসাব
✅ CSV ডাউনলোড (Excel এ খোলা যাবে)
✅ লেনদেন মুছে ফেলার অপশন
✅ পণ্য স্টক ট্র্যাকিং + কম স্টক সতর্কতা
✅ পণ্য add / edit / delete
✅ Dashboard — বিক্রয়, ক্রয়, লাভের chart

## Voice ব্যবহারের নিয়ম
Chrome বা Edge browser ব্যবহার করুন।
প্রথমবার মাইক্রোফোন permission দিন।
