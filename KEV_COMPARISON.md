# Kev'den DeepPanda'ya Alinabilecek Desenler

Kaynak: https://github.com/jaredpalmer/kev

## Benzerlik

- Ikisi de yerel model kodu, test ve deney sonucunu birlikte yonetiyor.
- Ikisi de model agirliklarini kaynak kodundan ayirmali.
- Ikisi de model cevabini sadece sezgiyle degil, olcum ve evaluation ile kontrol etmeli.

## Fark

- Kev: Qwen tabanli karar modelini egitme, LoRA, frozen suite ve benchmark arastirmasi.
- DeepPanda: yerel coding agent, workspace dosya araclari, RAG hafiza, onayli komutlar ve portable runtime.

## Uygulanacak Kev desenleri

1. Provenance: Her evaluation ve model sonucunda git commit, model adi, model revision, suite adi ve timestamp kaydet.
2. Frozen evaluation: Test sorularini sabit JSON dosyasinda tut; model/prompt degisikliginden sonra ayni suite'i tekrar calistir.
3. Source hashing: Kritik Python dosyalarinin SHA256 hash'lerini rapora ekle; sonucun hangi kodla uretildigi bilinsin.
4. Weight separation: GGUF, Ollama modelleri, checkpoint ve cache Git'e girmez; sadece model manifesti ve indirme talimatlari commitlenir.
5. Reproducible artifacts: Her evaluation sonucu JSON artifact olarak yazilsin; gecmis sonuclar ezilmesin.
6. Budget and approval: Uzun/uzak islerde kaynak, sure ve indirme maliyeti onceden gorunsun; kullanici onayi olmadan baslamasin.
7. Canonical helpers: Path, memory, model profile, evaluation ve report kurallari tek bir yardimci uzerinden uygulansin; ayni kural farkli scriptlerde kopyalanmasin.

## DeepPanda'ya ozel yorum

Kev'in "frozen suite + provenance + locked test" yaklasimi bizim offline coding evaluation sistemine uyarlanabilir. Bizim suite; intent classification, dosya okuma/yazma, diff approval, rollback, RAG retrieval, kaynakli research ve model cevap formatini olcmeli. Bu, model agirliklarini degistirmeden davranissal gelisme saglar.

Kev'den kod kopyalanmadi; yalnizca kamuya acik mimari ve test desenleri ogrenme notu olarak kaydedildi.
