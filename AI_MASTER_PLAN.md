# DeepPanda Yapay Zeka Ana Uygulama Listesi

Bu liste LocalQwenAgent'in DeepPanda icindeki gercek yeteneklerini ve siradaki uygulama adimlarini takip eder.

## Durumlar

- [x] Yerel Qwen/Ollama chat ve browser arayuzu
- [x] Continue OpenAI uyumlu `/v1` koprusu
- [x] DeepPanda workspace dosyalarini okuma
- [x] Workspace icine guvenli dosya yazma
- [x] Mevcut dosyayi yazmadan once `.localqwen-backups` altina yedekleme
- [x] Acik onayli Python, test, Node/npm ve FFmpeg komutlari
- [x] SQLite kalici hafiza: `Yapay Zeka/memory.db`
- [x] Operation journal ile islem kaydi
- [x] PDF, DOCX, PPTX, XLSX ve metin cikarma
- [x] Gorsel, ses/video ve Whisper pipeline'i
- [x] Public web/GitHub arastirmasi
- [x] Tasinabilir kurulum ve geri yukleme CMD dosyalari
- [x] Tek tik launcher ve servis kapanis temizligi

## Faz 1: Guvenli kodlama ajani

- [x] Her istek icin kalici task kaydi: niyet, plan, onay, komut, degisen dosyalar, test ve sonuc
- [x] Dosya yazmadan once diff onizleme
- [x] Son onayli degisikligi geri alma endpoint'i
- [x] Python, Node ve DeepPanda icin komut profilleri
- [x] Test/compile/lint sonucunu otomatik raporlama
- [x] Dosya yolu verildiginde okuma, degistirme ve sonuc dogrulama akisi
- [x] Offline coding agent evaluation cases ve niyet/plan kalite testi
- [x] Curated GitHub library source catalogi ve kalici RAG indeksleme

## Faz 2: Hafiza ve ogrenme

- [x] Hafiza arama: anahtar kelime, proje, kaynak ve tarih
- [x] Hafiza turleri: tercih, proje bilgisi, prosedur, arastirma, gorev gecmisi
- [x] Tekrarlanan notlari birlestirme
- [x] Hafiza export/import ve yedekleme CMD akisi
- [x] Kaynaga gore hafiza silme
- [x] SQLite tabanli RAG retrieval aramasi
- [x] Embedding tabanli semantik arama
- [x] Kullanici onayi olmadan ogrenme notu uretmeme secenegi

## Faz 3: Uzun isler ve arka plan

- [x] Test, arastirma ve transkripsiyonu background job olarak calistirma
- [x] UI'da ilerleme olaylari
- [x] Iptal, tekrar deneme ve hata goruntuleme
- [x] Job gecmisi ve cikti artifact klasoru

## Faz 4: Yerel model secimi

- [x] Ollama disinda dogrudan llama.cpp backend'i
- [x] Hizli chat, kod, vision ve planlama model profilleri
- [x] GPU/RAM tespiti ve guvenli context secimi
- [x] Ollama, bridge ve ktransformers fallback sirasi
- [x] WSL2 CUDA + KTransformers kernel import ve GPU smoke testi

## Faz 5: Multimodal raporlama

- [x] Video karelerini vision modeline gonderme
- [x] Whisper transcript + kare + zaman damgasi birlesimi
- [x] Taranmis PDF ve ekran goruntusu icin OCR
- [x] Kaynak referansli Markdown/PDF raporu

## Faz 6: Tasima ve operasyon

- [x] `Yapay Zeka/memory.db` ile kalici gecmis
- [x] `setup_portable.ps1`
- [x] `Restore-DeepPandaAI.cmd`
- [x] `Start-LocalQwenAgent.cmd`
- [x] Tek komutla export paketi olusturma
- [x] Restore sonrasi otomatik self-audit
- [x] Continue config kurulum yardimcisi

## Guvenlik kurali

- Workspace disina yazma yok.
- Dosya degisikligi ve komut calistirma acik onayli.
- Mevcut dosya yazmadan once yedeklenir.
- Private/local web adresleri engellenir.
- Her otomatik islem operation journal'a yazilir.
- Model agirliklari kendiliginden degismez; ogrenme kalici hafiza, retrieval, test sonucu ve kullanici onayli veri akislariyla olur.

## Uygulama sirasi

1. Faz 1: diff, task kaydi ve rollback.
2. Faz 2: hafiza arama, export/import ve tekrar temizleme.
3. Faz 3: background job ve UI ilerleme.
4. Faz 4: model profilleri ve fallback.
5. Faz 5: multimodal raporlama.
6. Faz 6: tek komut tasima/restore otomasyonu.
