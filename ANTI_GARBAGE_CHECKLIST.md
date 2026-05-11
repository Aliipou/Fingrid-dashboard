# Anti-Garbage Engineering Checklist

## 0. قبل از کدنویسی: آیا اصلاً باید اینو بسازیم؟

سؤال اجباری:
- مشکل دقیق چیست؟
- چرا این راه‌حل انتخاب شده؟
- ساده‌ترش چیست؟
- آیا existing abstraction کافی نیست؟
- آیا داریم abstraction زودهنگام می‌سازیم؟
- آیا complexity از value بیشتر شده؟

بیشتر کثافت‌ها از unnecessary code شروع می‌شوند.
**Best code = code that never existed.**

---

## 1. Rule: AI حق تصمیم معمواقعی ندارد

### Reviewer باید بپرسد:

#### آیا این code قابل حذف شدن است؟
اولین سؤال.

---

#### آیا naming واضح است؟
اگر naming گیج‌کننده است: design مشکل دارد.

---

#### آیا state flow قابل فهم است؟
اگر tracking state سخت است: future bug قطعی است.

---

#### آیا این abstraction premature است؟
بیشتر abstraction ها premature اند.

---

#### آیا error handling واقعی است؟
یا فقط:
```js
catch (e) {
  console.log(e)
}
```

---

#### آیا logging مفید است؟
AI معمولاً logging garbage تولید می‌کند.

---

#### آیا این test meaningful است؟
یا فقط coverage theater؟

---

## 5. قانون طلایی

اگر developer نتواند بدون AI توضیح دهد:
- code چه می‌کند
- چرا اینطوری طراحی شده
- failure mode چیست

=> **merge ممنوع.**

---

## 6. تیم‌ها باید metric عوض کنند

این metric ها garbage اند:
- lines of code
- PR count
- tickets closed

Metric واقعی:
- bug escape rate
- rollback frequency
- MTTR
- architectural stability
- onboarding clarity
- cognitive load
- deploy confidence

---

## 7. AI Usage Policy

### AI خوب است برای:
- boilerplate
- repetitive transformation
- documentation draft
- test scaffolding
- migration assistance
- syntax recall

### AI خطرناک است برای:
- auth/security
- concurrency
- distributed systems
- financial logic
- architecture
- performance-sensitive code
- infra automation

---

## 8. قانون نهایی

قبل merge:

> "آیا ۶ ماه بعد، نسخه خسته و عصبانی خودم از این code متنفر خواهد شد؟"

اگر جواب: "احتمالاً آره"
=> هنوز آماده merge نیست.
