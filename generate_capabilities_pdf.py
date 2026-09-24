from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "DeepPanda-AI-Yetenekleri-Rehberi.pdf"
FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")

if FONT.exists() and FONT_BOLD.exists():
    pdfmetrics.registerFont(TTFont("SegoeUI", str(FONT)))
    pdfmetrics.registerFont(TTFont("SegoeUI-Bold", str(FONT_BOLD)))
    BODY_FONT = "SegoeUI"
    BOLD_FONT = "SegoeUI-Bold"
else:
    BODY_FONT = "Helvetica"
    BOLD_FONT = "Helvetica-Bold"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", fontName=BOLD_FONT, fontSize=25, leading=31, alignment=TA_CENTER, textColor=colors.HexColor("#123047"), spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", fontName=BODY_FONT, fontSize=12, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#405465"), spaceAfter=8))
styles.add(ParagraphStyle(name="Section", fontName=BOLD_FONT, fontSize=16, leading=21, textColor=colors.HexColor("#123047"), spaceBefore=10, spaceAfter=8))
styles.add(ParagraphStyle(name="Subsection", fontName=BOLD_FONT, fontSize=11.5, leading=15, textColor=colors.HexColor("#1b6075"), spaceBefore=7, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyTR", fontName=BODY_FONT, fontSize=9.5, leading=14, textColor=colors.HexColor("#202b33"), spaceAfter=5))
styles.add(ParagraphStyle(name="BulletTR", parent=styles["BodyTR"], leftIndent=12, firstLineIndent=-7, bulletIndent=0, spaceAfter=3))
styles.add(ParagraphStyle(name="Small", fontName=BODY_FONT, fontSize=8, leading=11, textColor=colors.HexColor("#53636e"), spaceAfter=4))


def p(text, style="BodyTR"):
    return Paragraph(text, styles[style])


def bullets(items):
    return [p("• " + item, "BulletTR") for item in items]


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d9e2e8"))
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#667985"))
    canvas.drawString(18 * mm, 9 * mm, "DeepPanda / LocalQwenAgent")
    canvas.drawRightString(192 * mm, 9 * mm, f"Sayfa {doc.page}")
    canvas.restoreState()


story = []
story.extend([Spacer(1, 30 * mm), p("DeepPanda AI", "CoverTitle"), p("LocalQwenAgent yetenek ve kullanım rehberi", "CoverSub"), Spacer(1, 8 * mm), p("Yerel çalışan sohbet, kodlama, araştırma, dosya ve medya ajanı", "CoverSub"), Spacer(1, 22 * mm), p("Sürüm: 24 Eylül 2026", "Small"), p("Bu belge, mevcut Yapay Zeka projesindeki gerçek özellikler ve endpoint'ler incelenerek hazırlanmıştır.", "Small"), PageBreak()])

story.extend([p("1. Kısa Tanım", "Section"), p("DeepPanda AI, Ollama üzerinden çalışan yerel bir Qwen çalışma alanıdır. Sohbet edebilir, proje dosyalarını okuyabilir, kontrollü biçimde dosya değişikliği önerebilir, araştırma yapabilir ve belgeleri analiz edebilir. Tasarımın temel ilkesi: komut çalıştırma, paket kurma ve dosya yazma işlemleri açık kullanıcı onayı olmadan yapılmaz.")])
story.extend(bullets([
    "Yerel model: Ollama ve seçilen Qwen/model profilleri.",
    "Web arayüzü: http://127.0.0.1:8787.",
    "OpenAI uyumlu API: http://127.0.0.1:8787/v1.",
    "Kalıcı hafıza: memory.db içindeki SQLite tabloları.",
    "Çalışma alanı: WORKSPACE_ROOT ile sınırlandırılmış proje klasörü.",
]))

story.extend([p("2. Neler Yapabilir?", "Section"), p("Sohbet ve akıl yürütme", "Subsection")])
story.extend(bullets([
    "Soruyu answer, learn, research veya action_request niyetlerinden biri olarak sınıflandırır.",
    "İşlem gerektiren istekler için adım adım plan çıkarır.",
    "Belirsizliği belirtir; kaynakta olmayan bilgiyi uydurmamaya yönlendirilmiştir.",
    "Türkçe ve İngilizce isteklerde kelime tabanlı niyet algılama kullanır.",
]))
story.extend([p("Kalıcı hafıza ve RAG", "Subsection")])
story.extend(bullets([
    "Kullanıcı notlarını kategori, proje ve kaynak bilgisiyle kaydeder.",
    "Anahtar kelime araması, RAG context ve embedding tabanlı semantic search destekler.",
    "Hafıza export/import, kaynak önizleme ve kaynağa göre silme işlemleri vardır.",
    "GitHub kütüphanelerinin README ve kurulum belgelerini memory.db içine indeksleyebilir.",
]))
story.extend([p("Kodlama ajanı", "Subsection")])
story.extend(bullets([
    "Workspace dosyalarını okur ve proje mimarisini açıklar.",
    "Yeni modül, test, README veya proje iskeleti üretebilir.",
    "Yazmadan önce diff önizlemesi sunar.",
    "Mevcut dosyayı .localqwen-backups altında yedekler.",
    "Onaylı değişiklikleri geri alma endpoint'i vardır.",
    "Pytest, Ruff, Python, Node, npm, FFmpeg ve Ollama gibi sınırlı araçları çalıştırabilir.",
]))
story.append(PageBreak())

story.extend([p("3. Dosya ve Medya İşleme", "Section"), p("Belge analizi", "Subsection")])
story.extend(bullets([
    "PDF metni çıkarma ve PDF'ye ek içerik ekleme.",
    "DOCX, PPTX ve XLSX dosyalarından metin/yapı çıkarma.",
    "Markdown veya PDF raporu oluşturma.",
    "Kaynak listesi ve rapor özetlerini dışa aktarma.",
]))
story.extend([p("Görsel, ses ve video", "Subsection")])
story.extend(bullets([
    "Vision destekli Ollama modeli varsa görsel yükleme ve analiz.",
    "FFmpeg ile videodan ses ve kare örnekleme.",
    "faster-whisper ile yerel ses transkripsiyonu.",
    "Tesseract kuruluysa OCR hazırlığı ve OCR durum kontrolü.",
    "Görüntü, transcript ve zaman bilgilerini rapor akışında kullanmaya uygun altyapı.",
]))
story.extend([p("4. Araştırma Özellikleri", "Section")])
story.extend(bullets([
    "Public HTTP sayfalarından içerik çıkarma.",
    "JavaScript ağırlıklı sayfalar için Playwright/Chromium snapshot.",
    "Public GitHub repository ve README araştırması.",
    "Kaynak URL'lerini kaydetme ve araştırma notlarını hafızaya yazma.",
    "Uzun araştırma işleri için başlatma, durum sorgulama, iptal ve retry.",
    "Özel/local ağ adresleri güvenlik amacıyla engellenir.",
]))
story.extend([p("5. Kontrol ve Güvenlik", "Section")])
story.extend(bullets([
    "Dosya yazma sadece WORKSPACE_ROOT içinde yapılabilir.",
    "Path traversal ve workspace dışı yollar reddedilir.",
    "Komutlar approved=true olmadan çalıştırılmaz.",
    "Shell=False kullanılır; izinli araç listesi sınırlıdır.",
    "Mevcut dosyalar yazmadan önce yedeklenir.",
    "İşlemler operation journal ve task records tablolarına kaydedilir.",
    "Arbitrary OS administration, registry, servis ve sistem klasörü işlemleri tasarım gereği yoktur.",
]))
story.append(PageBreak())

story.extend([p("6. VS Code ve Continue Bağlantısı", "Section"), p("LocalQwenAgent, OpenAI uyumlu endpoint sunduğu için Continue gibi VS Code eklentilerine bağlanabilir.")])
story.extend([p("Gerekli ayar", "Subsection"), p("Continue config.yaml içine aşağıdaki model tanımını ekleyin:")])
config = """name: LocalQwenAgent\nversion: 1.0.0\nschema: v1\nmodels:\n  - name: local-qwen\n    provider: openai\n    model: local-qwen\n    apiBase: http://127.0.0.1:8787/v1\n    apiKey: local-only"""
config_table = Table([[p(config.replace("\n", "<br/>"), "Small")]], colWidths=[174 * mm])
config_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef4f6")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfd0d8")), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
story.append(config_table)
story.extend(bullets([
    "Önce Ollama'yı ve LocalQwenAgent'ı başlatın.",
    "VS Code'da Continue eklentisini açın ve local-qwen modelini seçin.",
    "Gerekirse Developer: Reload Window çalıştırın.",
    "Endpoint yalnızca 127.0.0.1'e bağlı tutulmalıdır; uzaktan erişim için authentication eklenmeden port açılmamalıdır.",
]))
story.extend([p("API uyumluluğu", "Subsection")])
story.extend(bullets([
    "GET /v1/models: model listesini döndürür.",
    "POST /v1/chat/completions: Continue ve OpenAI uyumlu istemciler için sohbet endpoint'i.",
    "POST /api/agent/plan: görev planı.",
    "POST /api/agent/generate: kod üretimi.",
    "POST /api/agent/apply: onaylı dosya uygulama.",
    "POST /api/agent/rollback: değişikliği geri alma.",
]))

story.extend([p("7. Başlatma ve İlk Kullanım", "Section")])
story.extend(bullets([
    "Yapay Zeka klasöründe .venv oluşturun veya mevcut sanal ortamı kullanın.",
    "requirements.txt paketlerini kurun.",
    "Ollama'yı başlatın ve bir sohbet modeli indirin.",
    "python app.py komutunu çalıştırın.",
    "Tarayıcıdan http://127.0.0.1:8787 adresini açın.",
]))
story.extend([p("Örnek istekler", "Subsection")])
story.extend(bullets([
    "Bu projeyi incele, riskleri ve test eksiklerini listele.",
    "Bu Python dosyasını değiştir, önce diff göster ve pytest çalıştır.",
    "Bu PDF'yi özetle ve kaynaklı bir rapor hazırla.",
    "Bu GitHub projesini araştır, önemli kütüphaneleri hafızaya kaydet.",
    "Bu video için konuşma dökümü ve kısa içerik özeti çıkar.",
]))
story.append(PageBreak())

story.extend([p("8. Öğretme ve Kütüphane Bilgi Tabanı", "Section"), p("Projede iki farklı kavramı ayırmak önemli:")])
story.extend(bullets([
    "Bilgi tabanı öğretimi: README, dokümantasyon, proje kuralları ve araştırma notlarını memory.db içine kaydetmek.",
    "Model eğitimi/fine-tuning: model ağırlıklarını veri setiyle yeniden eğitmek; GPU, veri hazırlığı ve ayrı eğitim pipeline'ı gerektirir.",
]))
story.extend([p("İndirilen/indekslenen AI ekosistemi", "Subsection")])
rows = [[p("Kütüphane", "Small"), p("Kullanım", "Small")]]
for name, use in [("Transformers", "Model ve pipeline ekosistemi"), ("PEFT", "LoRA/parametre verimli fine-tuning"), ("Accelerate", "CPU/GPU eğitim ve dağıtık çalışma"), ("Datasets", "Veri seti hazırlama"), ("Tokenizers", "Tokenizasyon"), ("Sentence-Transformers", "Embedding ve semantic search"), ("Unsloth", "Hızlı fine-tuning"), ("llama.cpp", "Ollama dışı yerel inference"), ("KTransformers", "Model inference optimizasyonu")]:
    rows.append([p(name, "Small"), p(use, "Small")])
table = Table(rows, colWidths=[50 * mm, 124 * mm], repeatRows=1)
table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcecf0")), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#bfd0d8")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
story.append(table)
story.extend([p("Mevcut katalog script'i bu depoların README, pyproject.toml, setup.py ve requirements.txt dosyalarını okuyup library_knowledge kategorisiyle hafızaya indeksler. Bu, ajanın ilgili kütüphaneler hakkında yerel kaynaklara erişmesini sağlar; otomatik model eğitimi yapmaz.")])

story.extend([p("9. Sınırlar ve Dikkat", "Section")])
story.extend(bullets([
    "Ollama servisi çalışmıyorsa sohbet modeli yanıt veremez.",
    "Vision, OCR, Whisper ve embedding özellikleri ilgili model/harici aracın kurulu olmasına bağlıdır.",
    "Paket kurulumu ve model indirme disk alanı, RAM/VRAM ve ağ bağlantısı gerektirir.",
    "Özel GitHub depoları ve oturum gerektiren web siteleri otomatik olarak okunamaz.",
    "Fine-tuning için veri seti, GPU planı, checkpoint ve değerlendirme süreci ayrıca hazırlanmalıdır.",
    "Güvenlik nedeniyle sınırsız işletim sistemi yönetimi desteklenmez.",
]))
story.extend([p("10. WSL2 ve Ubuntu Notu", "Section"), p("Projenin AI master planında WSL2 üzerinde CUDA, KTransformers kernel import ve GPU smoke testi tamamlanmış olarak işaretlenmiştir. WSL/Ubuntu, Windows üzerinde Linux tabanlı AI araçlarını ve GPU destekli inference/fine-tuning akışlarını çalıştırmak için kullanılabilir.")])
story.extend([p("Önerilen WSL2 akışı", "Subsection")])
story.extend(bullets([
    "Windows tarafında WSL2 ve Ubuntu dağıtımını kurun; yeniden başlatma gerekebilir.",
    "Ubuntu içinde güncelleme yapın: sudo apt update && sudo apt upgrade.",
    "Proje klasörünü Ubuntu tarafından /mnt/c/Users/emre/Desktop/DeepPanda-Proje altında kullanın veya Linux dosya sistemine kopyalayın.",
    "CUDA uyumlu NVIDIA sürücüsü Windows tarafında, CUDA/yardımcı paketler ise WSL akışına uygun biçimde kurulmalıdır.",
    "KTransformers ve llama.cpp gibi inference araçlarını WSL içinde ayrı bir sanal ortamda test edin.",
    "GPU kontrolü için nvidia-smi ve proje smoke testlerini çalıştırın.",
]))
story.extend([p("Önemli ayrım", "Subsection"), p("WSL/Ubuntu kurulumu bu Windows PDF'si hazırlanırken otomatik olarak yeniden kurulmadı; belge mevcut proje planındaki WSL2 + CUDA + KTransformers çalışmasını ve önerilen işletim akışını açıklar. Donanım sürücüsü, CUDA sürümü ve GPU belleği makineye göre ayrıca doğrulanmalıdır.")])
story.extend([p("11. Hızlı Kontrol Listesi", "Section")])
story.extend(bullets([
    "[ ] Ollama çalışıyor.",
    "[ ] İstenen model indirilmiş.",
    "[ ] LocalQwenAgent 127.0.0.1:8787 üzerinde açık.",
    "[ ] Continue config.yaml ayarlanmış.",
    "[ ] Proje workspace kökü doğru.",
    "[ ] Yazma/komut işlemlerinde diff ve onay kontrol ediliyor.",
    "[ ] Önemli hafıza ve proje dosyaları yedekleniyor.",
]))
story.extend([p("12. Bu Bilgisayarda Doğrulanan Bağlantılar", "Section")])
story.extend(bullets([
    "C:\\Users\\emre\\Desktop\\DeepPanda-Proje, D:\\DeepPanda-Proje klasörüne junction olarak bağlıdır; iki konumdaki app.py SHA-256 değeri eşleşmektedir.",
    "WSL2 üzerinde varsayılan Ubuntu dağıtımı çalışıyor ve /mnt/d/DeepPanda-Proje/Yapay Zeka/app.py erişilebilir.",
    "WSL Ubuntu, NVIDIA GeForce RTX 4060 Laptop GPU'yu 8 GB VRAM ve 617.14 sürücüsüyle görüyor.",
    "LocalQwenAgent 127.0.0.1:8787, Ollama 127.0.0.1:11434 üzerinde dinliyor.",
    "Ollama modelleri: qwen3.6:latest, codellama:7b, llama3.1:8b ve nomic-embed-text:latest.",
    "llama.cpp için GGUF model mevcut; 8090 portu doğrulama sırasında kapalıydı.",
    "Windows KTransformers derlemesi yol aşamasını geçti ancak NUMA kütüphanesi bulunamadığı için tamamlanmadı; GPU destekli akış WSL Ubuntu tarafında yürütülmelidir.",
]))
story.extend([Spacer(1, 10 * mm), p("Kaynak dosyalar: README.md, AGENT_CAPABILITIES.md, AGENT_ROADMAP.md, agent_tools.py, app.py ve agent_orchestrator.py", "Small")])

doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title="DeepPanda AI Yetenekleri Rehberi", author="DeepPanda")
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(OUTPUT)
