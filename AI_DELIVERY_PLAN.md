# LocalQwenAgent - Açık Geliştirme Planı

Güncelleme: 2026-09-28. Tamamlanan maddeler backlog'dan çıkarıldı; aşağıda yalnız açık işler var.

## P1 - Sonraki geliştirme oturumu

1. **Video job güvenilirliği:** Model callback'lerinden gerçek adım/yüzde ilerlemesi; restart sonrası job geçmişinin tutarlı durumu; failed/cancelled job retry.
2. **Asset yönetimi:** Kalıcı silme onaylı API/UI ile tamamlandı. Kalan: tarih/proje filtreleri, arşivleme/etiketleme ve geri alma.
3. **Browser oturum güvenliği:** Oturum sahipliği, süre sonu ve kapanma testleri; session ID tahmini/başka istemci erişimine karşı koruma; güvenli profil dizini allowlist'i.
4. **Instagram hata/izin akışı:** Token scope preflight, video/Reels processing status, rate-limit/permission hata kodlarını kullanıcıya eyleme dönük gösterme. Gerçek hesap izni yoksa yayın testi mock ile kalmalı.
5. **Kaggle yeniden skor:** Yeni `DeepPanda-Gemma4-submission.zip` yerel validator'dan geçti; eski skorlar 0.00. Günlük submission limiti açılınca tek gönderim yapıp task bazlı sonucu incele.

## P2 - Orta vadeli

6. Güncel ve desteklenen text-to-video pipeline/modeline geçiş; 8 GB VRAM'de ölçümlü model seçimi ve mevcut backend fallback'i.
7. Browser ve Instagram uçtan uca integration testleri; harici servisler için mock ve izinli gerçek smoke test ayrımı.
8. TTS ses profillerini adlandırıp kaydetme ve sesleri karşılaştırma.
9. Mobil/sidebar düzeni, job history paneli ve diagnostic/log görünümü.

## P3 - Uzun vadeli

10. Kurulum/model indirme sihirbazı ve disk alanı/sha256 doğrulaması.
11. Release installer ve portable restore akışını yeni Piper/video runtime seçenekleriyle güncelleme.
12. Model bazlı kalite, hız, bellek ve patch-pass benchmark raporu.

## Değişmez çalışma kuralları

- Önce bir hedef testi ve falsifiye edilebilir yerel hipotez belirle.
- En küçük değişikliği yap; kullanıcıya ait değişiklikleri koru.
- Ollama, Meta veya Kaggle erişimi yoksa bunu açıkça bildir; başarılıymış gibi davranma.
- Her release'te Ruff, compile, pytest, evaluation, veri/paket validator'ı çalıştır; sonra GitHub ve D/E yedeklerini hash ile eşitle.
- `.venv`, model cache ve üretilmiş asset'ler Git'e eklenmez; kullanıcı asset yedeklemesini ayrıca kapsama al.
