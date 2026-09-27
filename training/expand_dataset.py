from __future__ import annotations

import argparse
import json
from pathlib import Path

VARIANTS = [
    "Kisa ve kanita dayali cevap ver.",
    "Turkce ve madde madde cevap ver.",
    "Once plan, sonra sonuc ver.",
    "Onay ve test durumunu ozellikle belirt.",
    "Workspace yolu ve dosya adlarini acik yaz.",
    "Belirsizligi acikca bildir.",
    "Guvenlik sinirlarini gevsetme.",
    "Public kaynak ve commit bilgisini koru.",
    "Mevcut API ve dosya stilini koru.",
    "En kucuk uygulanabilir degisikligi sec.",
    "Basarisiz test olursa ayni slice icinde duzelt.",
    "Yazma veya komut icin acik onay iste.",
    "Sonucu operation journal ve artifact olarak raporla.",
    "Windows ve WSL yollarini birbirine karistirma.",
    "Model, hafiza ve kaynak kodunu ayri tut.",
    "Gizli bilgi, token veya sifre isteme.",
    "Dosya listesini ve test komutunu raporla.",
    "Kullaniciya sonraki uygulanabilir adimi soyle.",
    "Kaynakta olmayan teknik ayrintiyi uydurma.",
    "Teslim oncesi compile, test ve diff kontrolu yap.",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("offline_agent_tasks.jsonl"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("offline_agent_tasks_500.jsonl"))
    args = parser.parse_args()
    base = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    expanded = []
    for record in base:
        for index, variant in enumerate(VARIANTS, 1):
            item = json.loads(json.dumps(record, ensure_ascii=False))
            item["id"] = f"{record['id']}_v{index:02d}"
            item["tags"] = list(dict.fromkeys([*item.get("tags", []), "expanded"])),
            item["tags"] = item["tags"][0]
            user_message = item["messages"][1]["content"]
            item["messages"][1]["content"] = f"{user_message}\n\nEk kural: {variant}"
            expanded.append(item)
    args.output.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in expanded) + "\n", encoding="utf-8")
    print(f"base={len(base)} variants={len(VARIANTS)} output={len(expanded)} path={args.output}")


if __name__ == "__main__":
    main()
