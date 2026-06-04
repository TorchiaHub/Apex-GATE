#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json, csv, os
from datetime import datetime

BASE_URL = "https://build.nvidia.com"
MODELS_URL = f"{BASE_URL}/models?filters=nimType%3Anim_type_preview"
OUTPUT_DIR = r"C:\Users\matti\Desktop\free-models"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
}

def scrape_nvidia_nim_models():
    models, page = [], 1
    while True:
        url = f"{MODELS_URL}&page={page}" if page > 1 else MODELS_URL
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Pagina {page}...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Errore: {e}"); break

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("h3")
        if not cards:
            break

        for card in cards:
            link = card.find("a")
            if not link:
                continue
            name = link.get_text(strip=True)
            model_url = BASE_URL + link["href"] if link["href"].startswith("/") else link["href"]
            container = card.find_parent()
            description, publisher, labels = "", "", []
            if container:
                desc = container.find("p")
                if desc: description = desc.get_text(strip=True)
                pubs = container.find_all("a")
                if pubs: publisher = pubs[0].get_text(strip=True)
                label_tags = container.find_all("a", href=lambda h: h and "label=" in str(h))
                labels = [t.get_text(strip=True) for t in label_tags]
            models.append({"name": name, "publisher": publisher, "url": model_url,
                           "description": description, "labels": ", ".join(labels),
                           "type": "Free Endpoint", "scraped_at": datetime.now().isoformat()})

        next_btn = soup.find("button", {"aria-label": "Go to next page"})
        if not next_btn or next_btn.get("disabled"):
            break
        page += 1
    return models

def compare_with_previous(new_models):
    latest_json = os.path.join(OUTPUT_DIR, "latest.json")
    if not os.path.exists(latest_json):
        print("Prima esecuzione."); return [], []
    with open(latest_json, "r", encoding="utf-8") as f:
        old = json.load(f)
    old_names, new_names = {m["name"] for m in old}, {m["name"] for m in new_models}
    added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
    for n in added:   print(f"  ✅ AGGIUNTO: {n}")
    for n in removed: print(f"  ❌ RIMOSSO:  {n}")
    if not added and not removed: print("  ℹ️  Nessuna variazione.")
    return added, removed

def save_results(models, added, removed):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d")
    for path in [os.path.join(OUTPUT_DIR, f"nvidia_nim_{ts}.csv"), os.path.join(OUTPUT_DIR, "latest.csv")]:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=models[0].keys())
            w.writeheader(); w.writerows(models)
    for path in [os.path.join(OUTPUT_DIR, f"nvidia_nim_{ts}.json"), os.path.join(OUTPUT_DIR, "latest.json")]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(models, f, ensure_ascii=False, indent=2)
    if added or removed:
        with open(os.path.join(OUTPUT_DIR, "changes_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n--- {ts} ---\n")
            for n in added:   f.write(f"AGGIUNTO: {n}\n")
            for n in removed: f.write(f"RIMOSSO:  {n}\n")
    print(f"\n📁 Salvati {len(models)} modelli in {OUTPUT_DIR}")

if __name__ == "__main__":
    print(f"=== NVIDIA NIM Scraper | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    models = scrape_nvidia_nim_models()
    if models:
        added, removed = compare_with_previous(models)
        save_results(models, added, removed)
        print(f"📊 Totale modelli free: {len(models)}")
    else:
        print("⚠️  Nessun modello trovato.")