"""
FastAPI route (router) modules.

Her endpoint grubu ayri bir dosyada APIRouter olarak tutulur ve
app/main.py içinde `app.include_router(...)` ile bağlanır.

Planlanan router'lar:
- health.py            (Hafta 1)  - GET /health
- professors.py        (Hafta 3)  - hoca endpoint'leri
- courses.py           (Hafta 3)  - ders endpoint'leri
- reviews.py           (Hafta 4)  - yorum & puan endpoint'leri
- upvotes.py           (Hafta 4)  - upvote endpoint'leri
- auth.py              (Hafta 2)  - Cognito auth middleware/bağımlılıkları
"""
