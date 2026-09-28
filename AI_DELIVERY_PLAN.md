# LocalQwenAgent Yükleme ve Teslim Planı

## Durum
- Instagram token doğrulaması hazır.
- Job history ve media job akışı birleştirildi.
- Video progress pipeline çalışıyor.
- Progress UI görünümü eklendi.
- İlgili regresyon testi başarıyla geçti.

## Doğrulanan komut
```powershell
Set-Location -LiteralPath 'D:\DeepPanda-Proje\Yapay Zeka'; py -m pytest -q test_agent.py -k 'media_jobs_expose_progress_and_events_in_list or job_history_lists_research_and_media_entries or instagram_status_reports_missing_or_valid_token or expired_browser_session_is_closed_and_rejected or memory_taxonomy_entry_is_saved_with_labels or library_knowledge_category_is_persisted_and_deduplicated'
```

## Sonuç
- 6 passed
- 22 deselected
- exit code: 0

## Aktif öncelik sırası
1. Self-audit ve küçük temizlik
2. Kod ve UI final görünümünü netleştirme
3. Final teslim notu hazırlama
4. Düşük öncelikli iyileştirmeleri backlog'a alma

## Uygulanacak AI davranış kuralı
- Her yeni değişiklik için önce bir hedef testi yaz.
- Hata oluşursa kök nedenini doğrula; rastgele patch atma.
- Job, media, browser ve Instagram akışları ayrı ayrı kontrol et.
- Değişiklik sonrası en küçük doğrulama setini çalıştır.
- Her adım sonunda kısa bir durum özeti tut.

## Riskler
- Gerçek medya üretimi bazı sistemlerde model eksikliği nedeniyle başarısız olabilir.
- Browser ve Instagram akışları dış erişim/açık izin gerektirir.
- UI ve backend senkronizasyonu için polling ve job lifecycle kontrolü gerekir.

## Sonraki hedef
- Producing a final ready-to-ship checklist
- Kalan küçük temizlikleri bitir
- Kullanıcıya net teslim özeti hazırla
