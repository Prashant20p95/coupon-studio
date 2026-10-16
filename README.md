---
title: Umang Coupon Studio
emoji: 🎫
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Umang Utsav Event Card Coupon Studio

A complete, high-speed vector coupon generator for Umang Utsav events. Supports single-card live generation and bulk CSV processing (up to 100K+ cards).

Ready to run locally on Windows or deploy to **Vercel** with one click.

---

## Features

- **Full Gift Category Palette**:
  - **Category E**: Yellow / Gold (`#F59E0B` / `cmyk(0, 0.251, 1, 0)`) — Counter `- E`
  - **Category A, B, C, D**: Pink (`#EC4899` / `cmyk(0, 1, 0, 0)`) — Counter `A-D`
  - **Category F**: Orange (`#F97316` / `cmyk(0, 0.6, 1, 0)`) — Counter `- F`
  - **Category G**: Green (`#10B981` / `cmyk(0.4, 0, 1, 0)`) — Counter `- G`
  - **Category H**: Sky Blue (`#0284C7` / `cmyk(0.8, 0.102, 0, 0)`) — Counter `- H`
- **Clean Styles**: Select simply **English** (title: *UMANG UTSAV*) or **Hindi** (title: *उमंग उत्सव*).
- **Industrial Speed**: Generates hundreds of cards per second via shared Form XObjects.
- **Compact Print Files**: Background artwork is embedded once, resulting in 60x smaller PDFs (~25 MB for 1,000 cards instead of 1.2 GB).
- **Scanner-Ready QR Codes**: Byte-mode Error-Correction Level H, 21×21 grid.
- **Dynamic Font Scaling**: Long guest names automatically scale to fit perfectly.

---

## How to Run Locally

### 1. Launch Web Dashboard (Recommended)
Double-click `Launch_Card_Generator_UI.bat` (or run `python app.py`).
Opens `http://localhost:5000` in your web browser.

### 2. Command Line (CLI)

- **Single Card**:
  ```bash
  python make_cards.py --name "Subash singh" --location Raiganj --category E --otp 28693 --style english -o card.pdf
  ```

- **Bulk CSV (Single Combined PDF)**:
  ```bash
  python make_cards.py --csv sample_guests.csv -o output_cards/all_cards.pdf
  ```

- **Bulk CSV (Partitioned by Location)**:
  ```bash
  python make_cards.py --csv sample_guests.csv --by-location output_cards/by_location/
  ```

- **Massive Runs (Chunked into 5,000-card press volumes)**:
  ```bash
  python make_cards.py --csv guests_100k.csv -o output_cards/volumes/ --chunk-size 5000
  ```

---

## How to Deploy on Vercel

1. Push this folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Umang Utsav Coupon Generator"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```
2. Go to [vercel.com](https://vercel.com) and click **Add New > Project**.
3. Import your GitHub repository.
4. Vercel will automatically detect `vercel.json`, `api/index.py`, and `requirements.txt`.
5. Click **Deploy**. Your team will now have a live online link to generate cards from any device!

---

## File Structure

```
Card_Generator/
├── api/
│   └── index.py                  <-- Vercel serverless entry point
├── fonts/
│   └── uufont.json               <-- Original vector glyph curves
├── templates/                    <-- Master print plates (B, E, F, G, H)
├── app.py                        <-- Web Studio application (Flask)
├── make_cards.py                 <-- Industrial generation engine
├── qrmake.py                     <-- QR code matrix generator
├── sample_guests.csv             <-- Ready-to-use CSV template
├── requirements.txt              <-- Python dependencies
├── vercel.json                   <-- Vercel configuration
├── Launch_Card_Generator_UI.bat  <-- Windows 1-click Web launcher
└── Generate_Sample_Cards.bat     <-- Windows 1-click batch runner
```
