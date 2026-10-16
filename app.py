#!/usr/bin/env python3
"""
Umang Utsav Coupon Studio
=========================
Internal coupon generation application for Umang Utsav events.
"""
import csv
import io
import json
import os
import re
import sys
import time
import uuid
import zipfile
import threading
from collections import OrderedDict
from flask import Flask, request, send_file, jsonify, render_template_string, make_response

import make_cards
import pymupdf

app = Flask(__name__, static_folder="static", static_url_path="/static")

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(HERE) == "api":
    HERE = os.path.dirname(HERE)

if os.environ.get("VERCEL"):
    OUTPUT_DIR = "/tmp/output_cards"
else:
    OUTPUT_DIR = os.path.join(HERE, "output_cards")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global Job Registry for Real-time Batch Progress Tracking
JOBS = {}

ENTERPRISE_UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <title>Umang Utsav Coupon Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --navy: #1e3a8a;
      --navy-deep: #172554;
      --blue: #2563eb;
      --blue-light: #eff6ff;
      --bg: #f8f9fb;
      --surface: #ffffff;
      --border: #e5e7eb;
      --border-focus: #2563eb;
      --text: #111827;
      --text-secondary: #4b5563;
      --text-tertiary: #9ca3af;
      --radius: 10px;
      --radius-lg: 14px;
      --shadow-card: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
      --pink: #ec4899;
      --yellow: #f59e0b;
      --orange: #ea580c;
      --green: #10b981;
      --sky: #0284c7;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    /* ─── HEADER ─── */
    .header {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 0 32px;
      height: 72px;
      display: flex;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .header-inner {
      width: 100%;
      max-width: 1360px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .header-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .brand-logo-main {
      height: 38px;
      width: auto;
      border-radius: 6px;
      object-fit: contain;
      flex-shrink: 0;
    }
    .header-brand h1 {
      font-size: 17px;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.3px;
      white-space: nowrap;
      margin: 0;
    }
    .brand-title-full {
      display: inline;
    }
    .header-right {
      display: flex;
      align-items: center;
      flex-shrink: 0;
    }
    .brand-logo-partner {
      height: 32px;
      width: auto;
      object-fit: contain;
      display: block;
    }

    /* ─── LAYOUT SHELL ─── */
    .shell {
      max-width: 1360px;
      margin: 0 auto;
      padding: 24px 32px 48px;
    }

    /* ─── TABS ─── */
    .tab-bar {
      display: inline-flex;
      background: #eef0f4;
      padding: 4px;
      border-radius: 10px;
      margin-bottom: 24px;
      gap: 3px;
    }
    .tab-bar button {
      padding: 9px 24px;
      font-size: 13.5px;
      font-weight: 600;
      border: none;
      background: transparent;
      color: var(--text-secondary);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .tab-bar button.on {
      background: var(--surface);
      color: var(--navy);
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .tab-bar button:hover:not(.on) { color: var(--text); }

    /* ─── WORKSPACE (DESKTOP) ─── */
    .workspace {
      display: grid;
      grid-template-columns: 460px 1fr;
      gap: 24px;
      align-items: start;
    }
    .hidden, #v-single.hidden, #v-batch.hidden {
      display: none !important;
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-card);
      overflow: hidden;
    }
    .card-head {
      padding: 16px 22px;
      border-bottom: 1px solid #f3f4f6;
      font-size: 14px;
      font-weight: 700;
      color: var(--text);
    }
    .card-body { padding: 22px; }

    /* ─── FORM ─── */
    .form-section {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--text-tertiary);
      margin-bottom: 10px;
      margin-top: 20px;
    }
    .form-section:first-child { margin-top: 0; }

    .fg { margin-bottom: 16px; }
    .fg label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }
    .fg input, .fg select {
      width: 100%;
      padding: 10px 14px;
      border: 1.5px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
      font-family: inherit;
      color: var(--text);
      background: var(--surface);
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .fg input:focus, .fg select:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
    }
    .fg input.mono {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      letter-spacing: 0.5px;
    }
    .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

    /* ─── CATEGORY GRID ─── */
    .cat-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
    }
    .cat-tile {
      border: 1.5px solid var(--border);
      background: var(--surface);
      border-radius: 9px;
      padding: 10px 6px;
      text-align: center;
      cursor: pointer;
      transition: all 0.12s ease;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      min-height: 58px;
      justify-content: center;
    }
    .cat-tile:hover { border-color: #d1d5db; background: #fafbfc; }
    .cat-tile:active { transform: scale(0.97); }
    .cat-tile.on {
      border-color: var(--blue);
      background: var(--blue-light);
      box-shadow: 0 0 0 2px rgba(37,99,235,0.2);
    }
    .cat-dot {
      width: 26px; height: 26px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 13px; font-weight: 800; color: #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    }
    .cat-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-tertiary);
    }
    .cat-tile.on .cat-label { color: var(--navy); }

    .route-bar {
      margin-top: 10px;
      padding: 9px 12px;
      background: #f9fafb;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 12.5px;
      color: var(--text-secondary);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .route-bar b { color: var(--navy); }

    /* ─── STYLE TOGGLE ─── */
    .style-toggle {
      display: grid;
      grid-template-columns: 1fr 1fr;
      background: #f1f5f9;
      padding: 3px;
      border-radius: 8px;
      gap: 3px;
      border: 1px solid #e2e8f0;
      box-sizing: border-box;
    }
    .style-toggle button {
      padding: 8px 10px;
      border: none;
      background: transparent;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      color: #64748b;
      cursor: pointer;
      transition: all 0.12s;
    }
    .style-toggle button.on {
      background: #ffffff;
      color: #0f172a;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      font-weight: 700;
    }

    /* ─── BATCH CONFIGURATION PANEL ─── */
    .batch-config-panel {
      margin-top: 18px;
      padding: 16px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
    }
    .batch-config-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }
    .batch-opt-card {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .batch-opt-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: #64748b;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .batch-select {
      width: 100%;
      height: 40px;
      border: 1.5px solid #cbd5e1;
      border-radius: 8px;
      padding: 0 12px;
      font-size: 13px;
      font-weight: 600;
      color: #0f172a;
      background: #ffffff;
      cursor: pointer;
      box-sizing: border-box;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .batch-select:focus {
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
    }

    /* ─── BUTTONS ─── */
    .actions {
      display: flex;
      gap: 10px;
      margin-top: 22px;
      padding-top: 18px;
      border-top: 1px solid #f3f4f6;
    }
    .btn {
      flex: 1;
      padding: 11px 16px;
      font-size: 13.5px;
      font-weight: 600;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      transition: all 0.12s;
      min-height: 42px;
    }
    .btn:active { transform: scale(0.98); }
    .btn-outline {
      background: var(--surface);
      color: var(--text-secondary);
      border: 1.5px solid var(--border);
    }
    .btn-outline:hover { background: #fafbfc; border-color: #d1d5db; }
    .btn-fill {
      background: var(--navy);
      color: #fff;
      box-shadow: 0 1px 4px rgba(30,58,138,0.2);
    }
    .btn-fill:hover { background: var(--navy-deep); }
    .btn-green { background: #059669; color: #fff; }
    .btn-green:hover { background: #047857; }

    .btn-primary-action {
      background: var(--navy);
      color: #fff;
      font-size: 14.5px;
      font-weight: 700;
      width: 100%;
      min-height: 46px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(30,58,138,0.22);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.15s;
    }
    .btn-primary-action:hover {
      background: var(--navy-deep);
      box-shadow: 0 4px 12px rgba(30,58,138,0.3);
    }
    .btn-primary-action:active {
      transform: scale(0.98);
    }
    .action-grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 10px;
    }
    .btn-secondary-action {
      background: var(--surface);
      color: var(--text-secondary);
      border: 1.5px solid var(--border);
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      min-height: 42px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn-secondary-action:hover {
      background: #fafbfc;
      border-color: #cbd5e1;
    }
    .btn-secondary-action:active {
      transform: scale(0.98);
    }
    .btn-add {
      border-color: #93c5fd !important;
      color: var(--blue) !important;
      font-weight: 700 !important;
      background: #eff6ff !important;
    }
    .btn-add:hover {
      background: #dbeafe !important;
      border-color: var(--blue) !important;
    }
    .btn-whatsapp-action {
      background: #16a34a;
      color: #ffffff;
      border: none;
      font-size: 13.5px;
      font-weight: 700;
      width: 100%;
      min-height: 44px;
      border-radius: 8px;
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(22,163,74,0.25);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-top: 10px;
      transition: all 0.15s ease;
    }
    .btn-whatsapp-action:hover {
      background: #15803d;
      box-shadow: 0 3px 8px rgba(22,163,74,0.32);
    }
    .btn-whatsapp-action:active {
      transform: scale(0.98);
    }

    /* ─── PREVIEW STAGE ─── */
    .preview-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 20px;
    }
    .live-dot-badge {
      font-size: 11px;
      font-weight: 700;
      color: #15803d;
      background: #dcfce7;
      padding: 3px 9px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      letter-spacing: 0.2px;
    }
    .stage {
      background: #0f172a;
      border-radius: 12px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 460px;
      position: relative;
    }
    .stage img {
      max-width: 100%;
      height: auto;
      border-radius: 6px;
      box-shadow: 0 16px 40px -8px rgba(0,0,0,0.6);
      display: block;
      background: #fff;
    }
    .stage-spinner {
      display: none;
      position: absolute;
      top: 50%; left: 50%;
      transform: translate(-50%,-50%);
      background: rgba(15,23,42,0.92);
      color: #fff;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      backdrop-filter: blur(6px);
      z-index: 10;
    }
    @keyframes modalSpinRing {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    @keyframes modalProgressShimmer {
      0% { left: -50%; width: 40%; }
      50% { left: 25%; width: 60%; }
      100% { left: 100%; width: 40%; }
    }
    .pdf-editor-panel {
      transition: all 0.2s ease;
    }
    .pdf-editor-panel:hover {
      border-color: #cbd5e1;
      box-shadow: 0 2px 8px -2px rgba(0,0,0,0.05);
    }

    /* ─── BATCH VIEW & TIMELINE ─── */
    .batch-wrap {
      max-width: 760px;
      margin: 0 auto;
    }
    .drop-zone {
      border: 2px dashed #d1d5db;
      background: #fafbfc;
      border-radius: 12px;
      padding: 36px 24px;
      text-align: center;
      cursor: pointer;
      transition: all 0.15s;
    }
    .drop-zone:hover, .drop-zone.drag-over {
      border-color: var(--blue);
      background: var(--blue-light);
    }
    .drop-zone h3 {
      font-size: 15px;
      font-weight: 700;
      color: var(--text);
      margin-top: 10px;
    }
    .drop-zone p {
      font-size: 12.5px;
      color: var(--text-tertiary);
      margin-top: 4px;
    }

    .summary-box {
      margin-top: 18px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--surface);
      padding: 16px;
      display: none;
    }
    .summary-head {
      font-size: 13px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 10px;
    }
    .stat-row { display: flex; gap: 10px; flex-wrap: wrap; }
    .stat {
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
    }
    .stat-blue { background: #dbeafe; color: #1e40af; }
    .stat-green { background: #dcfce7; color: #15803d; }
    .stat-red { background: #fee2e2; color: #b91c1c; display: none; }
    .cat-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #f3f4f6; }
    .cat-pills span {
      font-size: 11px; font-weight: 700; padding: 3px 8px;
      border-radius: 5px; background: #f3f4f6; color: var(--text-secondary);
    }

    /* ─── REAL-TIME PROGRESS TIMELINE ─── */
    .timeline-container {
      margin-top: 20px;
      border: 1px solid #bfdbfe;
      background: #eff6ff;
      border-radius: 12px;
      padding: 20px;
      display: none;
    }
    .timeline-stepper {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
    }
    .t-step {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
    }
    .t-step.active { color: var(--navy); font-weight: 700; }
    .t-step.done { color: #15803d; }
    .t-circle {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #e2e8f0;
      color: #64748b;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
    }
    .t-step.active .t-circle { background: var(--blue); color: #fff; }
    .t-step.done .t-circle { background: #16a34a; color: #fff; }
    .t-line {
      flex: 1;
      height: 2px;
      background: #cbd5e1;
      margin: 0 8px;
    }
    .t-line.done { background: #16a34a; }

    /* Progress bar */
    .p-bar-outer {
      background: #dbeafe;
      height: 10px;
      border-radius: 5px;
      overflow: hidden;
      margin-top: 6px;
    }
    .p-bar-inner {
      background: var(--blue);
      height: 100%;
      width: 0%;
      transition: width 0.2s ease;
      border-radius: 5px;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 10px;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid #dbeafe;
      font-size: 12px;
    }
    .metrics-grid div {
      color: var(--text-secondary);
    }
    .metrics-grid b {
      color: var(--navy);
      display: block;
      margin-top: 2px;
      font-size: 12.5px;
    }

    /* Live Category Tracker Badges */
    .cat-live-track {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px dashed #bfdbfe;
    }
    .trk-pill {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      color: #64748b;
      transition: all 0.15s;
    }
    .trk-pill.current {
      background: var(--blue);
      color: #ffffff;
      border-color: var(--blue);
      box-shadow: 0 0 0 2px rgba(37,99,235,0.25);
    }
    .trk-pill.done {
      background: #dcfce7;
      color: #15803d;
      border-color: #86efac;
    }

    .done-box {
      margin-top: 20px;
      padding: 18px;
      border-radius: 12px;
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      display: none;
    }
    .done-box h4 { color: #166534; font-size: 15px; font-weight: 700; }
    .done-box p { color: #15803d; font-size: 13.5px; margin-top: 4px; }

    /* ─── OVERRIDES ACCORDION ─── */
    details { margin-top: 14px; }
    details summary {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-tertiary);
      cursor: pointer;
      padding: 4px 0;
    }
    details[open] summary { color: var(--text-secondary); }

    /* ═══════════════════════════════════════════════════
       MOBILE RESPONSIVE UI SPECIFICATIONS (SMARTPHONES)
       ═══════════════════════════════════════════════════ */
    @media (max-width: 900px) {
      .shell {
        padding: 10px 10px 32px !important;
        max-width: 100% !important;
      }
      .workspace {
        display: flex;
        flex-direction: column;
        gap: 14px;
      }
      .hidden, #v-single.hidden, #v-batch.hidden {
        display: none !important;
      }
      
      /* Both cards follow the EXACT SAME container specifications */
      #formCard, #previewCard {
        width: 100% !important;
        background: #ffffff !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05) !important;
        overflow: hidden !important;
        margin: 0 !important;
      }
      #previewCard {
        order: -1;
      }
      
      /* Both card headers follow the EXACT SAME structure and styling */
      #formCard .card-head, #previewCard .card-head {
        padding: 12px 16px !important;
        font-size: 13.5px !important;
        font-weight: 700 !important;
        background: #f8fafc !important;
        border-bottom: 1px solid #e2e8f0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
      }

      /* Both card bodies follow the EXACT SAME horizontal padding (14px) */
      #formCard .card-body, #previewCard .card-body {
        padding: 14px !important;
      }

      /* Live Preview Stage: Remove bulky nested box and border */
      .stage {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
        min-height: auto !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
      }

      /* Live Preview Image: Perfectly matches the exact width of form inputs */
      .stage img {
        width: 100% !important;
        max-width: 100% !important;
        height: auto !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08) !important;
        border: 1px solid #cbd5e1 !important;
        display: block !important;
        margin: 0 auto !important;
      }

      /* Form controls responsive tuning */
      .form-section {
        margin-top: 14px !important;
        margin-bottom: 8px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
      }
      .fg {
        margin-bottom: 12px !important;
      }
      .fg input, .fg select {
        font-size: 16px !important; /* Prevents auto-zoom on iOS */
        padding: 10px 12px !important;
        border-radius: 8px !important;
        border: 1.5px solid #cbd5e1 !important;
      }
      .row2 {
        grid-template-columns: 1fr !important;
        gap: 10px !important;
      }
      .batch-config-grid {
        grid-template-columns: 1fr !important;
        gap: 12px !important;
      }
      .cat-grid {
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 6px !important;
      }
      .cat-tile {
        padding: 8px 4px !important;
        min-height: 52px !important;
      }
      .cat-dot {
        width: 26px !important;
        height: 26px !important;
        font-size: 13px !important;
      }
      .cat-label {
        font-size: 10px !important;
      }
      .tab-bar {
        width: 100% !important;
        display: flex !important;
        margin-bottom: 12px !important;
      }
      .tab-bar button {
        flex: 1 !important;
        text-align: center !important;
        padding: 9px 8px !important;
        font-size: 13px !important;
      }
      .actions-panel {
        margin-top: 16px !important;
      }
      .btn-primary-action {
        min-height: 46px !important;
        font-size: 14px !important;
      }
      .action-grid-2 {
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
        margin-top: 8px !important;
      }
      .btn-secondary-action {
        min-height: 42px !important;
        font-size: 12.5px !important;
      }
      .timeline-stepper {
        display: none !important;
      }
      .brand-title-full {
        display: none !important;
      }
      .header {
        padding: 0 12px !important;
        height: 50px !important;
        min-height: 50px !important;
      }
      .header-inner {
        gap: 8px !important;
      }
      .header-brand {
        gap: 8px !important;
      }
      .brand-logo-main {
        height: 28px !important;
      }
      .header-brand h1 {
        font-size: 14px !important;
      }
      .brand-logo-partner {
        height: 22px !important;
        max-width: 78px !important;
      }
      .sample-btn-group {
        width: 100% !important;
      }
      .sample-btn {
        flex: 1 !important;
        text-align: center !important;
        font-size: 11.5px !important;
        padding: 6px 8px !important;
      }
    }

    @media (max-width: 480px) {
      .shell {
        padding: 8px 8px 28px !important;
      }
      #formCard, #previewCard {
        border-radius: 12px !important;
      }
      #formCard .card-head, #previewCard .card-head {
        padding: 10px 14px !important;
        font-size: 13px !important;
      }
      #formCard .card-body, #previewCard .card-body {
        padding: 12px !important;
      }
      .header-brand h1 {
        font-size: 13.5px !important;
      }
      .brand-logo-main {
        height: 26px !important;
      }
      .brand-logo-partner {
        height: 20px !important;
        max-width: 70px !important;
      }
      .cat-grid {
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 5px !important;
      }
      .cat-tile {
        padding: 6px 2px !important;
        min-height: 48px !important;
      }
      .cat-dot {
        width: 24px !important;
        height: 24px !important;
        font-size: 12px !important;
      }
      .cat-label {
        font-size: 9.5px !important;
      }
      .action-grid-2 {
        gap: 8px !important;
      }
      .btn-secondary-action {
        font-size: 12px !important;
        padding: 0 6px !important;
        min-height: 40px !important;
      }
      .btn-primary-action {
        min-height: 44px !important;
        font-size: 14px !important;
      }
    }
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <nav class="header">
    <div class="header-inner">
      <div class="header-brand">
        <img src="/static/umang_logo.png" alt="Umang Utsav" class="brand-logo-main">
        <h1><span class="brand-title-full">Umang Utsav </span><span class="brand-title-sub">Coupon Studio</span></h1>
      </div>
      <div class="header-right">
        <img src="/static/humbee_logo.png" alt="HUMBEE" class="brand-logo-partner">
      </div>
    </div>
  </nav>

  <!-- Main Shell -->
  <main class="shell">

    <div class="tab-bar">
      <button class="on" id="tabSingle" type="button" onclick="tab('single')">Create Coupon</button>
      <button id="tabBatch" type="button" onclick="tab('batch')">Bulk Cards Batch</button>
    </div>

    <!-- ═══ SINGLE CARD WORKSPACE ═══ -->
    <div id="v-single" class="workspace">

      <!-- Left Card: Form Controls -->
      <div class="card" id="formCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center">
          <span>Coupon Details</span>
          <span id="catBadge" style="font-size:11px;font-weight:700;color:var(--navy);background:#e0f2fe;padding:2px 8px;border-radius:10px">Category E</span>
        </div>
        <div class="card-body">
          <form id="cardForm" autocomplete="off" onsubmit="event.preventDefault(); render();">

            <div class="form-section">Style</div>
            <div class="fg">
              <input type="hidden" id="selectedStyle" value="english">
              <div class="style-toggle">
                <button type="button" class="on" id="sEn" onclick="setStyle('english')">English</button>
                <button type="button" id="sHi" onclick="setStyle('hindi')">Hindi</button>
              </div>
            </div>

            <div class="form-section">Gift Category</div>
            <div class="fg">
              <input type="hidden" id="selectedCategory" value="E">
              <div class="cat-grid">
                <div class="cat-tile" id="c-A" onclick="cat('A')"><span class="cat-dot" style="background:var(--pink)">A</span><span class="cat-label">A-D</span></div>
                <div class="cat-tile" id="c-B" onclick="cat('B')"><span class="cat-dot" style="background:var(--pink)">B</span><span class="cat-label">A-D</span></div>
                <div class="cat-tile" id="c-C" onclick="cat('C')"><span class="cat-dot" style="background:var(--pink)">C</span><span class="cat-label">A-D</span></div>
                <div class="cat-tile" id="c-D" onclick="cat('D')"><span class="cat-dot" style="background:var(--pink)">D</span><span class="cat-label">A-D</span></div>
                <div class="cat-tile on" id="c-E" onclick="cat('E')"><span class="cat-dot" style="background:var(--yellow)">E</span><span class="cat-label">E</span></div>
                <div class="cat-tile" id="c-F" onclick="cat('F')"><span class="cat-dot" style="background:var(--orange)">F</span><span class="cat-label">F</span></div>
                <div class="cat-tile" id="c-G" onclick="cat('G')"><span class="cat-dot" style="background:var(--green)">G</span><span class="cat-label">G</span></div>
                <div class="cat-tile" id="c-H" onclick="cat('H')"><span class="cat-dot" style="background:var(--sky)">H</span><span class="cat-label">H</span></div>
              </div>
              <div class="route-bar">
                <span>Counter: <b id="routeText">E</b></span>
                <span id="routeDot" style="width:10px;height:10px;border-radius:50%;background:var(--yellow);display:inline-block"></span>
              </div>
            </div>

            <div class="form-section">Guest Information</div>

            <div class="fg">
              <label>Full Name</label>
              <input type="text" id="name" value="" placeholder="Guest Name" autocomplete="off" autocorrect="off" spellcheck="false" oninput="debounce()" required>
            </div>

            <div class="row2">
              <div class="fg">
                <label>Location</label>
                <input type="text" id="location" value="" placeholder="Event Location" autocomplete="off" autocorrect="off" spellcheck="false" oninput="debounce()" required>
              </div>
              <div class="fg">
                <label style="display:flex;justify-content:space-between;align-items:center">
                  <span>OTP Code</span>
                  <span id="otpErr" style="display:none;color:#dc2626;font-size:11px;font-weight:700">⚠ Numbers only (0-9)</span>
                </label>
                <input type="text" id="otp" class="mono" value="" inputmode="numeric" placeholder="OTP Code" autocomplete="off" autocorrect="off" spellcheck="false" oninput="onOtpInput(this)" required>
              </div>
            </div>

            <!-- Contextual Editing Bar (Sleek, minimal, appears only when editing a card) -->
            <div id="editingBanner" style="display:none;margin-top:14px;padding:8px 14px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;font-size:12.5px;color:#1e40af;align-items:center;justify-content:space-between">
              <div style="display:flex;align-items:center;gap:6px">
                <span style="font-size:13px">✏️</span>
                <span>Editing <b>Card #<span id="editCardNum">1</span></b></span>
              </div>
              <button type="button" onclick="cancelEdit()" style="background:none;border:none;color:#2563eb;font-size:12px;font-weight:700;cursor:pointer;padding:2px 6px">✕ Done Editing</button>
            </div>

            <!-- Action Buttons Panel -->
            <div class="actions-panel" style="margin-top:18px">
              <button type="button" class="btn btn-primary-action" id="dlPdfBtn" onclick="dlPdf()">
                Download PDF
              </button>
              <div class="action-grid-2">
                <button type="button" class="btn btn-secondary-action" id="dlPngBtn" onclick="dlPng()">Download Image</button>
                <button type="button" class="btn btn-secondary-action btn-add" id="addCardBtn" onclick="addCardToQueue()">+ Add Card</button>
              </div>
              <button type="button" class="btn btn-whatsapp-action" id="shareWaBtn" onclick="sharePdfOnly()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0"><path d="M12.031 6.172c-3.181 0-5.767 2.586-5.768 5.766-.001 1.298.38 2.27 1.019 3.287l-.711 2.598 2.668-.699c.969.585 1.961.948 3.228.948h.001c3.181 0 5.767-2.586 5.768-5.766 0-3.18-2.586-5.766-5.767-5.766zm9.969 5.766c0 5.514-4.486 10-10 10-1.748 0-3.385-.45-4.815-1.242l-5.185 1.358 1.382-5.048c-.886-1.488-1.382-3.226-1.382-5.068 0-5.514 4.486-10 10-10s10 4.486 10 10z"/></svg>
                Share PDF via WhatsApp
              </button>
            </div>

            <!-- Inline Download Notice (Discrete & Professional) -->
            <div id="dlNotice" style="display:none;margin-top:10px;padding:8px 12px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;font-size:12px;color:#166534;font-weight:600"></div>

            <!-- Unified Card Manager Panel -->
            <div id="queueBar" style="display:none;margin-top:16px;border-radius:12px;border:1px solid #e2e8f0;background:#ffffff;box-shadow:0 1px 3px rgba(0,0,0,0.03);overflow:hidden">
              <!-- Manager Header -->
              <div style="padding:10px 14px;background:#f8fafc;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                <div style="display:flex;align-items:center;gap:8px">
                  <span style="font-size:12.5px;font-weight:700;color:#0f172a">Batch Queue</span>
                  <span id="queueBadge" style="background:#2563eb;color:#fff;font-size:11px;font-weight:700;padding:1px 7px;border-radius:10px"><span id="queueCount">0</span> Cards</span>
                  <span id="sourceFileBadge" style="display:none;background:#e2e8f0;color:#475569;font-size:11px;font-weight:600;padding:1px 8px;border-radius:10px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"></span>
                </div>
                <div style="display:flex;align-items:center;gap:10px">
                  <label for="pdfRepairIn" onclick="try{document.getElementById('pdfRepairIn').value=''}catch(e){}" style="background:none;border:none;color:#2563eb;font-size:11.5px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:4px">
                    📂 Import PDF
                  </label>
                  <button type="button" id="restoreBtn" style="display:none;background:none;border:none;color:#475569;font-size:11.5px;font-weight:600;cursor:pointer" onclick="restoreLastBatch()">
                    🔄 Restore (<span id="restoreCount">0</span>)
                  </button>
                  <button type="button" onclick="clearQueue()" style="background:none;border:none;color:#94a3b8;font-size:11.5px;font-weight:600;cursor:pointer" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#94a3b8'">
                    Clear All
                  </button>
                </div>
              </div>

              <!-- In-Card Status Alert (Crisp, Single-Line, Professional) -->
              <div id="queueStatusToast" style="display:none;margin:8px 12px 0 12px;padding:6px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;font-size:11.5px;color:#166534;justify-content:space-between;align-items:center">
                <span id="queueStatusText">✓ Ready</span>
                <button type="button" onclick="document.getElementById('queueStatusToast').style.display='none'" style="background:none;border:none;color:#166534;font-size:13px;cursor:pointer;padding:0 4px">&times;</button>
              </div>

              <!-- List of Card Chips -->
              <div id="queueListPills" style="padding:10px 12px;display:flex;flex-wrap:wrap;gap:6px;max-height:220px;overflow-y:auto"></div>
            </div>

            <!-- Standalone Import Toolbar (Visible only when Queue is empty) -->
            <div id="emptyImportBar" style="margin-top:16px;display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:8px">
              <span style="font-size:12px;color:#64748b">Existing coupon PDF?</span>
              <div style="display:flex;gap:8px;align-items:center">
                <button type="button" id="restoreBtnEmpty" style="display:none;background:none;border:none;color:#2563eb;font-size:12px;font-weight:600;cursor:pointer;padding:0" onclick="restoreLastBatch()">
                  🔄 Restore (<span id="restoreCountEmpty">0</span>)
                </button>
                <label for="pdfRepairIn" onclick="try{document.getElementById('pdfRepairIn').value=''}catch(e){}" style="background:#ffffff;border:1px solid #cbd5e1;color:#334155;font-size:12px;font-weight:600;padding:5px 12px;border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;gap:5px" title="Import an existing PDF to inspect and edit cards">
                  📂 Import & Edit
                </label>
              </div>
            </div>

            <!-- Global Hidden File Input (Always in layout DOM, Works 100% on iOS & Android) -->
            <input type="file" id="pdfRepairIn" accept=".pdf,application/pdf" style="position:fixed;top:-1000px;left:-1000px;width:1px;height:1px;opacity:0.01;" onchange="onLoadPdfFile(event)">
          </form>
        </div>
      </div>

      <!-- Right Card: Live Preview -->
      <div class="card" id="previewCard">
        <div class="card-head preview-head">
          <span>Coupon Card Preview</span>
          <span class="live-dot-badge">● Live Sync</span>
        </div>
        <div class="card-body">
          <div class="stage">
            <div id="spinner" class="stage-spinner">Generating preview...</div>
            <img id="preview" src="/api/preview?category=E&style=english&v=3" alt="Coupon Card Preview">
          </div>
        </div>
      </div>

    </div>

    <!-- ═══ BATCH WORKSPACE ═══ -->
    <div id="v-batch" class="hidden" style="display:none">
      <div class="card batch-wrap">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
          <span>Bulk Cards Batch</span>
          <div style="display:flex;gap:8px" class="sample-btn-group">
            <button type="button" class="btn btn-outline sample-btn" style="flex:none;padding:6px 12px;font-size:12px;min-height:auto" onclick="window.location.href='/api/sample_excel'">Download Sample Excel</button>
            <button type="button" class="btn btn-outline sample-btn" style="flex:none;padding:6px 12px;font-size:12px;min-height:auto" onclick="window.location.href='/api/sample_csv'">Download Sample CSV</button>
          </div>
        </div>
        <div class="card-body">
          <div class="drop-zone" id="rosterDropZone" onclick="document.getElementById('rosterIn').click()"
               ondragover="event.preventDefault(); this.classList.add('drag-over');"
               ondragleave="this.classList.remove('drag-over');"
               ondrop="event.preventDefault(); this.classList.remove('drag-over'); onRosterDrop(event);">
            <input type="file" id="rosterIn" multiple accept=".csv, .xlsx, .xls" style="display:none" onchange="onRosterFile(event)">
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.6"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <h3>Upload File(s)</h3>
            <p>Select single or multiple files (.xlsx, .csv)</p>
            <div id="fileInfo" style="margin-top:8px;font-weight:600;color:var(--blue);font-size:12.5px"></div>
          </div>

          <!-- Selected Files List -->
          <div id="fileManifestBox" style="display:none;margin-top:14px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;padding:0 2px">
              <span style="font-size:11.5px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px">
                Selected Files (<span id="manifestCountBadge">0</span>)
              </span>
              <div style="display:flex;gap:12px;align-items:center">
                <button type="button" onclick="document.getElementById('rosterIn').click()" style="background:none;border:none;font-size:11.5px;font-weight:600;color:var(--blue);cursor:pointer;padding:0">+ Add File</button>
                <button type="button" onclick="clearAllUploadedFiles()" style="background:none;border:none;font-size:11.5px;font-weight:600;color:#94a3b8;cursor:pointer;padding:0" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#94a3b8'">Clear</button>
              </div>
            </div>
            <div id="fileManifestList" style="display:flex;flex-direction:column;gap:6px"></div>
          </div>

          <!-- Verification Summary Card -->
          <div id="summaryBox" class="summary-box">
            <div class="summary-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
              <span>Verification Summary</span>
              <span id="validBadge" style="display:none;background:#dcfce7;color:#166534;font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px">✓ Valid</span>
            </div>
            <div class="stat-row">
              <span class="stat stat-blue" id="sTotal">Total: 0</span>
              <span class="stat stat-green" id="sValid">Ready: 0</span>
              <span class="stat stat-red" id="sInvalid" style="cursor:pointer" onclick="toggleErrorDetails()">Issues: 0</span>
              <span class="stat" id="sLocations" style="display:none;background:#f3e8ff;color:#6b21a8"></span>
            </div>
            <div class="cat-pills" id="catPills"></div>

            <!-- Error Details Drawer (Detailed Row Inspector) -->
            <div id="errorDetailsBox" style="display:none;margin-top:12px;padding:12px 14px;border-radius:8px;background:#fef2f2;border:1px solid #fecaca">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:12px;font-weight:700;color:#991b1b">
                  ⚠ <span id="errCountText">0</span> Rows with Missing / Invalid Data (Skipped)
                </span>
                <span style="font-size:11px;color:#b91c1c">Only clean rows will be printed</span>
              </div>
              <div id="errorListItems" style="margin-top:8px;max-height:130px;overflow-y:auto;font-size:11.5px;color:#7f1d1d;line-height:1.6;border-top:1px dashed #fca5a5;padding-top:6px"></div>
            </div>

            <!-- Dynamic Pre-Generation Estimation Bar -->
            <div id="estimateCard" style="display:none;margin-top:14px;padding:10px 14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
                <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:#334155">
                  <span style="color:#2563eb">⏱</span>
                  <span><b>Estimated Time:</b> <span id="estTimeLabel">~15s</span></span>
                </div>
                <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:#334155">
                  <span style="color:#2563eb">📦</span>
                  <span><b>Estimated File Size:</b> <span id="estSizeLabel">~20 MB</span></span>
                </div>
              </div>
            </div>
          </div>

          <div class="batch-config-panel">
            <div class="batch-config-grid">
              <!-- Configuration Column 1: Card Language (English / Hindi Only) -->
              <div class="batch-opt-card">
                <label class="batch-opt-label">Card Language</label>
                <div class="style-toggle" style="height:40px">
                  <button type="button" class="on" id="bStyleEn" onclick="setBatchStyle('english')">English</button>
                  <button type="button" id="bStyleHi" onclick="setBatchStyle('hindi')">Hindi (हिंदी)</button>
                </div>
                <input type="hidden" id="batchStyleVal" value="english">
              </div>

              <!-- Configuration Column 2: Package Mode -->
              <div class="batch-opt-card">
                <label class="batch-opt-label">Package Mode</label>
                <select id="exportMode" class="batch-select">
                  <option value="merged">Single Combined PDF</option>
                  <option value="zip">ZIP Package (By Location)</option>
                </select>
              </div>

              <!-- Configuration Column 3: Output Quality -->
              <div class="batch-opt-card">
                <label class="batch-opt-label">Output Quality</label>
                <select id="pdfSizeOpt" class="batch-select" onchange="updateEstimates()">
                  <option value="compact">Standard Vector PDF</option>
                  <option value="heavy">High-Res Press PDF (300 DPI)</option>
                </select>
              </div>
            </div>
          </div>

          <div class="actions" style="border:none;padding-top:12px;display:flex;align-items:center;gap:10px">
            <button class="btn btn-green" id="batchBtn" onclick="runBatch()" disabled style="flex:1">Compile Production Batch</button>
            <button type="button" class="btn btn-outline" id="cancelBatchBtn" onclick="cancelBatch()" style="display:none;flex:none;border-color:#ef4444;color:#ef4444;font-weight:700;padding:0 20px">✕ Cancel Generation</button>
          </div>

          <!-- Real-Time Progress Timeline Box -->
          <div id="timelineCard" class="timeline-container">
            <div class="timeline-stepper">
              <div class="t-step done" id="tStep1"><span class="t-circle">&check;</span><span>Roster Verified</span></div>
              <div class="t-line done" id="tLine1"></div>
              <div class="t-step done" id="tStep2"><span class="t-circle">&check;</span><span>Sequenced (A&rarr;H)</span></div>
              <div class="t-line done" id="tLine2"></div>
              <div class="t-step active" id="tStep3"><span class="t-circle" id="tCircle3">&bull;</span><span>Rendering Coupons</span></div>
              <div class="t-line" id="tLine3"></div>
              <div class="t-step" id="tStep4"><span class="t-circle" id="tCircle4">4</span><span>Package Ready</span></div>
            </div>

            <div>
              <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; font-weight:700; color:var(--navy); margin-bottom:6px;">
                <span id="pStatusLabel">Rendering Print-Ready Batch...</span>
                <span id="pPercentLabel" style="color:var(--blue);font-size:14px">0%</span>
              </div>
              <div class="p-bar-outer" style="height:8px;border-radius:99px">
                <div class="p-bar-inner" id="pBarFill" style="border-radius:99px;transition:width 0.25s ease"></div>
              </div>
            </div>

            <div class="metrics-grid">
              <div>Coupons Rendered<b id="pCountLabel">0 / 0</b></div>
              <div>Processing Rate<b id="pSpeedLabel">0 c/s</b></div>
              <div>Elapsed / Remaining<b id="pEtaLabel">0s &bull; ~0s</b></div>
              <div>Active Record<b id="pCurrentCardLabel">-</b></div>
            </div>

            <div class="cat-live-track">
              <span class="trk-pill" id="trk-A">A</span>
              <span class="trk-pill" id="trk-B">B</span>
              <span class="trk-pill" id="trk-C">C</span>
              <span class="trk-pill" id="trk-D">D</span>
              <span class="trk-pill" id="trk-E">E</span>
              <span class="trk-pill" id="trk-F">F</span>
              <span class="trk-pill" id="trk-G">G</span>
              <span class="trk-pill" id="trk-H">H</span>
            </div>
          </div>

          <!-- Stopped / Paused Box with Partial Download & Resume Option -->
          <div id="stoppedBox" style="display:none;margin-top:20px;padding:20px;border-radius:12px;background:#fffbeb;border:1px solid #fde68a">
            <h4 style="color:#92400e;font-size:16px;font-weight:700;margin:0;display:flex;align-items:center;gap:8px">
              <span>⏸️ Batch Generation Paused</span>
            </h4>
            <p id="stoppedDesc" style="color:#b45309;font-size:13px;margin:8px 0 0 0;line-height:1.5">
              Generation was stopped. All cards rendered up to this point have been safely compiled into a print-ready document.
            </p>
            <div style="margin-top:16px;display:flex;flex-wrap:wrap;align-items:center;gap:12px">
              <a id="partialDlLink" class="btn btn-green" style="display:inline-flex;width:auto;padding:10px 20px;font-weight:700;text-decoration:none" href="#">
                ⬇️ Download Printed Cards (<span id="partialCountLabel">0</span> Cards)
              </a>
              <button type="button" id="resumeBatchBtn" class="btn btn-primary" onclick="resumeBatch()" style="display:inline-flex;width:auto;padding:10px 20px;font-weight:700">
                ▶️ Resume Generation
              </button>
              <button type="button" class="btn btn-outline" onclick="restartBatch()" style="display:inline-flex;width:auto;padding:10px 16px;font-size:13px">
                🔄 Start from Beginning
              </button>
            </div>
          </div>

          <!-- Finished Box -->
          <div id="doneBox" class="done-box" style="margin-top:20px;padding:20px;border-radius:12px;background:#f0fdf4;border:1px solid #bbf7d0">
            <h4 style="color:#166534;font-size:16px;font-weight:700;margin:0">✓ Production Batch Ready for Print</h4>
            <p id="doneDesc" style="color:#15803d;font-size:13px;margin:8px 0 0 0;line-height:1.5"></p>
            <div style="margin-top:14px">
              <a id="doneLink" class="btn btn-fill" style="display:inline-flex;width:auto;padding:11px 24px;background:#15803d;border:none;font-weight:700" href="#">Download Production PDF</a>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Scanning / Extracting Cards Modal -->
    <div id="pdfLoadingModal" onclick="if(event.target===this) this.style.display='none'" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(15,23,42,0.68);z-index:999999;backdrop-filter:blur(6px);align-items:center;justify-content:center;padding:20px">
      <div style="position:relative;background:#ffffff;border-radius:18px;padding:32px 28px;max-width:440px;width:100%;box-shadow:0 25px 60px -15px rgba(0,0,0,0.35);text-align:center;display:flex;flex-direction:column;align-items:center;gap:14px;border:1px solid #f1f5f9;box-sizing:border-box">
        <button type="button" onclick="document.getElementById('pdfLoadingModal').style.display='none'" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:20px;color:#94a3b8;cursor:pointer;line-height:1;padding:4px" title="Dismiss">&times;</button>
        <div style="width:54px;height:54px;position:relative;display:flex;align-items:center;justify-content:center">
          <svg style="animation:modalSpinRing 1.1s linear infinite;width:54px;height:54px" viewBox="0 0 50 50">
            <circle cx="25" cy="25" r="20" fill="none" stroke="#e2e8f0" stroke-width="4.5"></circle>
            <circle cx="25" cy="25" r="20" fill="none" stroke="#2563eb" stroke-width="4.5" stroke-linecap="round" stroke-dasharray="85" stroke-dashoffset="65"></circle>
          </svg>
          <span style="position:absolute;font-size:18px">📄</span>
        </div>
        <div>
          <div style="font-size:17.5px;font-weight:700;color:#0f172a;line-height:1.3" id="pdfLoadingTitle">Extracting Cards from PDF...</div>
          <div id="pdfLoadingFilePill" style="display:inline-flex;align-items:center;gap:6px;background:#f8fafc;border:1px solid #e2e8f0;color:#334155;font-size:12px;font-weight:600;padding:4px 14px;border-radius:20px;max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:8px">
            <span id="pdfLoadingFileName">Document.pdf</span>
          </div>
        </div>
        <div style="font-size:13px;color:#64748b;line-height:1.55;max-width:360px;margin:0" id="pdfLoadingDesc">
          Scanning pages, reading QR codes, and extracting guest details. Please wait a moment.
        </div>
        <!-- Animated Progress Shimmer -->
        <div style="width:100%;height:6px;background:#f1f5f9;border-radius:99px;overflow:hidden;position:relative;margin-top:4px">
          <div style="position:absolute;top:0;left:0;height:100%;width:50%;background:linear-gradient(90deg,#2563eb,#38bdf8);border-radius:99px;animation:modalProgressShimmer 1.6s infinite ease-in-out"></div>
        </div>
      </div>
    </div>

  </main>

  <script>
    const CI = {
      A:{c:'A-D',clr:'#ec4899'},B:{c:'A-D',clr:'#ec4899'},C:{c:'A-D',clr:'#ec4899'},D:{c:'A-D',clr:'#ec4899'},
      E:{c:'E',clr:'#f59e0b'},F:{c:'F',clr:'#ea580c'},G:{c:'G',clr:'#10b981'},H:{c:'H',clr:'#0284c7'}
    };
    let _t = null, _files = [], _pollTimer = null;

    function debounce() {
      clearTimeout(_t);
      _t = setTimeout(render, 220);
    }

    function cat(l) {
      document.querySelectorAll('.cat-tile').forEach(e => e.classList.remove('on'));
      const tile = document.getElementById('c-' + l);
      if (tile) tile.classList.add('on');
      document.getElementById('selectedCategory').value = l;
      const i = CI[l] || CI.B;
      document.getElementById('routeText').textContent = i.c;
      document.getElementById('routeDot').style.background = i.clr;
      const cb = document.getElementById('catBadge');
      if (cb) cb.textContent = 'Category ' + l;
      // Reset counter override so switching category strictly adopts the new category's counter
      const co = document.getElementById('counterOverride');
      if (co) co.value = '';
      render(); // Instantly re-render, even if name is blank!
    }

    function setStyle(v) {
      document.getElementById('selectedStyle').value = v;
      document.getElementById('sEn').classList.toggle('on', v === 'english');
      document.getElementById('sHi').classList.toggle('on', v === 'hindi');
      render(); // Instantly re-render with new language
    }

    function setBatchStyle(v) {
      const val = (v === 'hindi') ? 'hindi' : 'english';
      const input = document.getElementById('batchStyleVal');
      if (input) input.value = val;
      const bEn = document.getElementById('bStyleEn');
      const bHi = document.getElementById('bStyleHi');
      if (bEn) bEn.classList.toggle('on', val === 'english');
      if (bHi) bHi.classList.toggle('on', val === 'hindi');
      try {
        localStorage.setItem('uu_batch_style', val);
      } catch (e) {}
    }

    function fd() {
      const co = document.getElementById('counterOverride');
      const clr = document.getElementById('colorOverride');
      return {
        name: (document.getElementById('name') ? document.getElementById('name').value : '').trim(),
        location: (document.getElementById('location') ? document.getElementById('location').value : '').trim(),
        otp: (document.getElementById('otp') ? document.getElementById('otp').value : '').trim(),
        category: document.getElementById('selectedCategory') ? document.getElementById('selectedCategory').value : 'E',
        style: document.getElementById('selectedStyle') ? document.getElementById('selectedStyle').value : 'english',
        counter: co ? co.value.trim() : '',
        color: clr ? clr.value.trim() : ''
      };
    }

    function onOtpInput(el) {
      const errSpan = document.getElementById('otpErr');
      const val = el.value;
      if (/[^0-9]/.test(val)) {
        if (errSpan) errSpan.style.display = 'inline';
        el.style.borderColor = '#dc2626';
      } else {
        if (errSpan) errSpan.style.display = 'none';
        el.style.borderColor = '';
      }
      debounce();
    }

    function commitActiveCard() {
      if (_editingIndex >= 0 && _editingIndex < _cardQueue.length) {
        const d = fd();
        const curName = d.name.trim();
        const curLoc = d.location.trim();
        const curOtp = d.otp.trim();
        const curCat = d.category || _cardQueue[_editingIndex].category || 'A';
        const curStyle = d.style || _cardQueue[_editingIndex].style || 'english';
        const curCounter = (d.counter !== undefined) ? d.counter : (_cardQueue[_editingIndex].counter || '');
        const curColor = (d.color !== undefined) ? d.color : (_cardQueue[_editingIndex].color || '');

        _cardQueue[_editingIndex] = {
          ..._cardQueue[_editingIndex],
          name: curName,
          location: curLoc || (_cardQueue[_editingIndex].location || 'Event'),
          category: curCat,
          otp: curOtp || _cardQueue[_editingIndex].otp,
          style: curStyle,
          counter: curCounter,
          color: curColor
        };
        saveSession();
      }
    }

    function render() {
      const d = fd();

      // Real-time sync: if user is editing a card from the queue, sync inputs immediately!
      if (_editingIndex >= 0 && _editingIndex < _cardQueue.length) {
        commitActiveCard();

        const pillName = document.getElementById('queuePillName_' + _editingIndex);
        if (pillName) pillName.textContent = d.name.trim() || 'Unnamed';
        const pillCat = document.getElementById('queuePillCat_' + _editingIndex);
        if (pillCat) pillCat.textContent = 'Cat ' + (d.category || 'A');

        const numSpan = document.getElementById('editCardNum');
        if (numSpan) numSpan.textContent = (_editingIndex + 1) + (d.name ? ': ' + d.name.trim() : '');
      }

      const payload = {
        name: d.name,
        location: d.location,
        otp: d.otp,
        category: d.category || "E",
        style: d.style || "english",
        counter: d.counter || "",
        color: d.color || ""
      };

      const sp = document.getElementById('spinner');
      if (sp) sp.style.display = 'block';

      const url = '/api/preview?' + new URLSearchParams(payload).toString() + '&t=' + Date.now();
      const p = new Image();
      p.onload = function() {
        document.getElementById('preview').src = url;
        if (sp) sp.style.display = 'none';
      };
      p.onerror = function() {
        if (sp) sp.style.display = 'none';
      };
      p.src = url;
    }

    async function dlPng() {
      // 1. Commit active edits or un-added input into the queue
      commitActiveCard();
      const d = fd();
      const curName = d.name.trim();
      const curOtp = d.otp.trim();

      if (curName && curOtp && _editingIndex === -1) {
        _cardQueue.push({
          name: curName,
          location: d.location.trim() || 'Event',
          category: d.category || 'E',
          otp: curOtp,
          style: d.style || 'english',
          counter: d.counter || '',
          color: d.color || ''
        });
        document.getElementById('name').value = '';
        document.getElementById('otp').value = '';
        updateQueueUI();
      }

      // If cards have been added to the queue:
      if (_cardQueue.length > 0) {
        if (_cardQueue.length === 1) {
          const c = _cardQueue[0];
          window.location.href = '/api/download_png?' + new URLSearchParams(c).toString();
          return;
        }

        const btn = document.getElementById('dlPngBtn');
        const origText = btn ? btn.textContent : 'Download Images';
        if (btn) {
          btn.disabled = true;
          btn.textContent = `Generating Images (${_cardQueue.length})...`;
        }

        const defLoc = (_cardQueue[0].location || 'Event').trim();

        try {
          const res = await fetch('/api/generate_multi_images', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              cards: _cardQueue,
              default_location: defLoc
            })
          });

          if (!res.ok) {
            const err = await res.json();
            alert('Error generating images: ' + (err.error || 'Failed to render'));
            if (btn) { btn.disabled = false; btn.textContent = origText; }
            return;
          }

          const blob = await res.blob();
          let filename = defLoc + ' Card Images.zip';
          const disposition = res.headers.get('Content-Disposition');
          if (disposition && disposition.includes('filename=')) {
            const match = disposition.match(/filename=["']?([^"';]+)["']?/);
            if (match && match[1]) filename = match[1].trim();
          }

          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);

          if (btn) {
            btn.disabled = false;
            btn.textContent = origText;
          }
        } catch (err) {
          alert('Failed to download images: ' + err.message);
          if (btn) { btn.disabled = false; btn.textContent = origText; }
        }
        return;
      }

      // Queue is empty: check form fields
      if (!d.name || !d.name.trim()) {
        alert('Please enter a Guest Name first.');
        document.getElementById('name').focus();
        return;
      }
      if (!d.otp || !d.otp.trim()) {
        alert('Please enter an OTP Code first.');
        document.getElementById('otp').focus();
        return;
      }
      if (!/^\d+$/.test(d.otp.trim())) {
        alert('Invalid OTP: OTP Code must contain only numeric digits (0-9).\n\nPlease remove any letters or symbols.');
        document.getElementById('otp').focus();
        return;
      }

      window.location.href = '/api/download_png?' + new URLSearchParams(d).toString();
    }

    /* ─── DIRECT PDF SHARING (NO TEXT, ONLY PDF FILE) ─── */
    async function sharePdfOnly() {
      commitActiveCard();
      const btn = document.getElementById('shareWaBtn');
      const origHtml = btn ? btn.innerHTML : '';
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span style="display:inline-block;animation:modalSpinRing 1s linear infinite">⏳</span> Preparing PDF...`;
      }

      try {
        let blob = null;
        let filename = 'Soft copy.pdf';

        if (_cardQueue.length > 0) {
          const locInput = (document.getElementById('location').value || '').trim();
          const defLoc = locInput || (_cardQueue[0].location || 'Event').trim();
          filename = defLoc + ' Soft copy.pdf';

          const res = await fetch('/api/generate_multi_pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              cards: _cardQueue,
              default_location: defLoc,
              preserve_order: true,
              original_filename: _importedFileName || ''
            })
          });

          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || 'Failed to generate PDF');
          }
          blob = await res.blob();
          const disp = res.headers.get('Content-Disposition');
          if (disp && disp.includes('filename=')) {
            const m = disp.match(/filename=["']?([^"';]+)["']?/);
            if (m && m[1]) filename = m[1].trim();
          }
        } else {
          const d = fd();
          if (!d.name || !d.name.trim()) {
            alert('Please enter a Guest Name first.');
            document.getElementById('name').focus();
            if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
            return;
          }
          if (!d.otp || !d.otp.trim()) {
            alert('Please enter an OTP Code first.');
            document.getElementById('otp').focus();
            if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
            return;
          }
          if (!/^\d+$/.test(d.otp.trim())) {
            alert('Invalid OTP: Numbers only (0-9).');
            document.getElementById('otp').focus();
            if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
            return;
          }

          const loc = (d.location || 'Event').trim();
          filename = `${loc} Soft copy.pdf`;

          const res = await fetch('/api/download_single?' + new URLSearchParams(d).toString());
          if (!res.ok) {
            throw new Error('Failed to generate single PDF');
          }
          blob = await res.blob();
        }

        const file = new File([blob], filename, { type: 'application/pdf' });

        // Native Mobile Share (iOS Safari, Android Chrome, Edge) - Sends ONLY the PDF file to WhatsApp!
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share({
            files: [file]
          });
        } else {
          // Desktop Fallback: Download file directly and open WhatsApp Web
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);

          window.open('https://web.whatsapp.com', '_blank');
          const notice = document.getElementById('dlNotice');
          if (notice) {
            notice.style.display = 'block';
            notice.textContent = `✓ PDF "${filename}" downloaded! Drag & drop it into your WhatsApp chat.`;
            setTimeout(() => { notice.style.display = 'none'; }, 8000);
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          alert('Could not share PDF: ' + err.message);
        }
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = origHtml;
        }
      }
    }

    /* ─── SESSION PERSISTENCE (GAP 3) ─── */
    let _cardQueue = [];
    let _editingIndex = -1;
    let _loadedPdfBlob = null;
    let _importedFileName = '';

    function saveSession() {
      try {
        localStorage.setItem('uu_card_queue', JSON.stringify(_cardQueue || []));
        localStorage.setItem('uu_editing_idx', String(_editingIndex));
        localStorage.setItem('uu_form_draft', JSON.stringify(fd()));
        if (_importedFileName) {
          localStorage.setItem('uu_imported_filename', _importedFileName);
        } else {
          localStorage.removeItem('uu_imported_filename');
        }
      } catch (e) {
        console.warn('Storage save failed:', e);
      }
    }

    function restoreSession() {
      try {
        const qRaw = localStorage.getItem('uu_card_queue');
        if (qRaw) {
          const parsed = JSON.parse(qRaw);
          if (Array.isArray(parsed) && parsed.length > 0) {
            _cardQueue = parsed;
            const savedIdx = parseInt(localStorage.getItem('uu_editing_idx') || '-1', 10);
            _importedFileName = localStorage.getItem('uu_imported_filename') || '';
            updateQueueUI();
            if (savedIdx >= 0 && savedIdx < _cardQueue.length) {
              editQueueItem(savedIdx);
              return true;
            } else {
              editQueueItem(0);
              return true;
            }
          }
        }
        const fRaw = localStorage.getItem('uu_form_draft');
        if (fRaw) {
          const f = JSON.parse(fRaw);
          if (f.name && document.getElementById('name')) document.getElementById('name').value = f.name;
          if (f.location && document.getElementById('location')) document.getElementById('location').value = f.location;
          if (f.otp && document.getElementById('otp')) document.getElementById('otp').value = f.otp;
          if (f.category) cat(f.category);
          if (f.style) setStyle(f.style);
        }
        const savedBatchStyle = localStorage.getItem('uu_batch_style');
        if (savedBatchStyle) {
          setBatchStyle(savedBatchStyle);
        }
      } catch (e) {
        console.warn('Storage restore failed:', e);
      }
      return false;
    }

    function tab(m) {
      document.querySelectorAll('.tab-bar button').forEach(b => b.classList.remove('on'));
      const vSingle = document.getElementById('v-single');
      const vBatch = document.getElementById('v-batch');
      if (m === 'single') {
        const btn = document.getElementById('tabSingle') || document.querySelectorAll('.tab-bar button')[0];
        if (btn) btn.classList.add('on');
        vSingle.classList.remove('hidden');
        vSingle.style.display = '';
        vBatch.classList.add('hidden');
        vBatch.style.display = 'none';
      } else {
        const btn = document.getElementById('tabBatch') || document.querySelectorAll('.tab-bar button')[1];
        if (btn) btn.classList.add('on');
        vSingle.classList.add('hidden');
        vSingle.style.display = 'none';
        vBatch.classList.remove('hidden');
        vBatch.style.display = 'block';
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function editQueueItem(idx) {
      if (idx < 0 || idx >= _cardQueue.length) return;
      if (_editingIndex >= 0 && _editingIndex < _cardQueue.length && _editingIndex !== idx) {
        commitActiveCard();
      }
      _editingIndex = idx;
      const c = _cardQueue[idx];

      // Populate form controls with card details
      document.getElementById('name').value = c.name || '';
      document.getElementById('location').value = c.location || '';
      document.getElementById('otp').value = c.otp || '';

      if (c.category) cat(c.category);
      if (c.style) setStyle(c.style);
      if (document.getElementById('counterOverride')) {
        const std = (['A','B','C','D'].includes(c.category)) ? 'A-D' : c.category;
        const rawC = (c.counter || '').replace(/^counter\s*[-:]?\s*/i, '').replace(/^-\s*/, '').trim().toUpperCase();
        if (rawC && rawC !== std && rawC !== (c.category || '').toUpperCase()) {
          document.getElementById('counterOverride').value = c.counter || '';
        } else {
          document.getElementById('counterOverride').value = '';
        }
      }
      if (document.getElementById('colorOverride')) {
        document.getElementById('colorOverride').value = c.color || '';
      }

      // Show editing banner & update button
      const banner = document.getElementById('editingBanner');
      if (banner) banner.style.display = 'flex';
      const numSpan = document.getElementById('editCardNum');
      if (numSpan) numSpan.textContent = (idx + 1) + (c.name ? ': ' + c.name : '');

      const addBtn = document.getElementById('addCardBtn');
      if (addBtn) {
        addBtn.textContent = '✓ Save Changes';
        addBtn.style.background = 'var(--blue)';
        addBtn.style.color = '#ffffff';
        addBtn.style.borderColor = 'var(--blue)';
      }

      // Live update preview and queue highlighting
      render();
      updateQueueUI();
      document.getElementById('name').focus();
    }

    function cancelEdit() {
      commitActiveCard();
      _editingIndex = -1;
      const banner = document.getElementById('editingBanner');
      if (banner) banner.style.display = 'none';

      const addBtn = document.getElementById('addCardBtn');
      if (addBtn) {
        addBtn.textContent = '+ Add Card';
        addBtn.style.background = '';
        addBtn.style.color = 'var(--blue)';
        addBtn.style.borderColor = 'var(--blue)';
      }

      updateQueueUI();
      render();
    }

    function addCardToQueue() {
      const d = fd();
      if (!d.name || !d.name.trim()) {
        alert('Please enter a Guest Name first.');
        document.getElementById('name').focus();
        return;
      }
      if (!d.otp || !d.otp.trim()) {
        alert('Please enter an OTP Code first.');
        document.getElementById('otp').focus();
        return;
      }
      if (!/^\d+$/.test(d.otp.trim())) {
        alert('Invalid OTP: OTP Code must contain only numeric digits (0-9).\n\nPlease remove any letters or symbols.');
        document.getElementById('otp').focus();
        return;
      }

      if (_editingIndex >= 0 && _editingIndex < _cardQueue.length) {
        // Update existing card in queue
        _cardQueue[_editingIndex] = {
          name: d.name.trim(),
          location: d.location.trim() || 'Event',
          category: d.category || 'A',
          otp: d.otp.trim(),
          style: d.style || 'english',
          counter: d.counter || '',
          color: d.color || ''
        };
        const savedIdx = _editingIndex;
        _editingIndex = -1;

        const banner = document.getElementById('editingBanner');
        if (banner) banner.style.display = 'none';

        const addBtn = document.getElementById('addCardBtn');
        if (addBtn) {
          addBtn.textContent = '+ Add Card';
          addBtn.style.background = '';
          addBtn.style.color = 'var(--blue)';
          addBtn.style.borderColor = 'var(--blue)';
        }

        const toast = document.getElementById('queueStatusToast');
        const toastText = document.getElementById('queueStatusText');
        if (toast && toastText) {
          toastText.textContent = `✓ Card #${savedIdx + 1} updated! Ready to download.`;
          toast.style.display = 'flex';
          setTimeout(() => { if (toast) toast.style.display = 'none'; }, 4000);
        }

        updateQueueUI();
        saveSession();
        render();
      } else {
        // Add new card to queue
        _cardQueue.push({
          name: d.name.trim(),
          location: d.location.trim() || 'Event',
          category: d.category || 'E',
          otp: d.otp.trim(),
          style: d.style || 'english',
          counter: d.counter || '',
          color: d.color || ''
        });

        // Clear guest name and OTP for next attendee
        document.getElementById('name').value = '';
        document.getElementById('otp').value = '';
        updateQueueUI();
        saveSession();
        render();
        document.getElementById('name').focus();
      }
    }

    function removeQueueItem(idx) {
      if (_editingIndex === idx) {
        cancelEdit();
      } else if (_editingIndex > idx) {
        _editingIndex--;
      }
      _cardQueue.splice(idx, 1);
      updateQueueUI();
      saveSession();
    }

    function clearQueue() {
      if (_cardQueue.length > 0) {
        if (!confirm(`Are you sure you want to clear ${_cardQueue.length} queued cards and start fresh?`)) {
          return;
        }
      }
      cancelEdit();
      _cardQueue = [];
      _importedFileName = '';
      try {
        localStorage.removeItem('uu_card_queue');
        localStorage.removeItem('uu_editing_idx');
        localStorage.removeItem('uu_imported_filename');
      } catch(e) {}
      updateQueueUI();
      saveSession();
      render();
    }

    function updateQueueUI() {
      const count = _cardQueue.length;
      const btn = document.getElementById('dlPdfBtn');
      const pngBtn = document.getElementById('dlPngBtn');
      const bar = document.getElementById('queueBar');
      const emptyBar = document.getElementById('emptyImportBar');
      const countEl = document.getElementById('queueCount');
      const pillsEl = document.getElementById('queueListPills');
      const srcEl = document.getElementById('sourceFileBadge');

      if (pngBtn) {
        if (count > 1) {
          pngBtn.textContent = `Download Images (${count} in ZIP)`;
          pngBtn.title = `Download all ${count} card images in a single ZIP package`;
        } else {
          pngBtn.textContent = 'Download Image';
          pngBtn.title = 'Download single card PNG image';
        }
      }

      if (srcEl) {
        if (_importedFileName && count > 0) {
          srcEl.textContent = '📄 ' + _importedFileName;
          srcEl.style.display = 'inline-block';
        } else {
          srcEl.style.display = 'none';
        }
      }

      if (count > 0) {
        btn.textContent = `Download PDF (${count} Card${count > 1 ? 's' : ''})`;
        btn.style.background = '#15803d';
        if (bar) bar.style.display = 'block';
        if (emptyBar) emptyBar.style.display = 'none';
        if (countEl) countEl.textContent = count;
        if (pillsEl) {
          pillsEl.innerHTML = '';
          _cardQueue.forEach((c, idx) => {
            const isEditing = (_editingIndex === idx);
            const pill = document.createElement('div');
            pill.style.cssText = isEditing
              ? 'background:#eff6ff;border:1.5px solid #2563eb;border-radius:8px;padding:5px 10px;font-size:12px;color:#1e3a8a;display:inline-flex;align-items:center;gap:7px;cursor:pointer;box-shadow:0 0 0 2px rgba(37,99,235,0.15);transition:all 0.15s'
              : 'background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:5px 10px;font-size:12px;color:#334155;display:inline-flex;align-items:center;gap:7px;cursor:pointer;transition:all 0.15s';
            
            pill.innerHTML = `
              <span onclick="editQueueItem(${idx})" style="display:inline-flex;align-items:center;gap:6px">
                <b style="color:${isEditing ? '#2563eb' : '#64748b'}">${idx + 1}.</b>
                <span style="font-weight:600;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(c.name || 'Unnamed')}</span>
                <span style="font-size:10.5px;font-weight:700;padding:1px 5px;border-radius:4px;background:${isEditing ? '#dbeafe' : '#f1f5f9'};color:${isEditing ? '#1e40af' : '#475569'}">Cat ${c.category || 'A'}</span>
                ${isEditing ? '<span style="font-size:10px;background:#2563eb;color:#fff;padding:1px 5px;border-radius:4px;font-weight:700">Editing</span>' : ''}
              </span>
              <button type="button" onclick="event.stopPropagation(); removeQueueItem(${idx})" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:14px;line-height:1;padding:0 2px;margin-left:2px;transition:color 0.15s" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#94a3b8'" title="Remove card">&times;</button>
            `;
            pillsEl.appendChild(pill);
          });
        }
      } else {
        btn.textContent = 'Download PDF';
        btn.style.background = '';
        if (bar) bar.style.display = 'none';
        if (emptyBar) emptyBar.style.display = 'flex';
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    async function dlPdf() {
      // 1. Commit active edits into the card queue immediately
      commitActiveCard();

      // If cards have been added to the queue, download all in 1 combined PDF!
      if (_cardQueue.length > 0) {
        // If user also currently typed a name and OTP while not in edit mode, auto-include it
        const curName = document.getElementById('name').value.trim();
        const curOtp = document.getElementById('otp').value.trim();
        if (curName && curOtp && _editingIndex === -1) {
          if (!/^\d+$/.test(curOtp)) {
            alert('Invalid OTP: OTP Code must contain only numeric digits (0-9).\n\nPlease remove any letters or symbols.');
            document.getElementById('otp').focus();
            return;
          }
          const d = fd();
          _cardQueue.push({
            name: d.name.trim(),
            location: d.location.trim() || 'Event',
            category: d.category || 'E',
            otp: d.otp.trim(),
            style: d.style || 'english',
            counter: d.counter || '',
            color: d.color || ''
          });
          document.getElementById('name').value = '';
          document.getElementById('otp').value = '';
          updateQueueUI();
        }

        const btn = document.getElementById('dlPdfBtn');
        const origText = btn.textContent;
        btn.disabled = true;
        btn.textContent = `Generating Combined PDF (${_cardQueue.length} Cards)...`;

        const locInput = (document.getElementById('location').value || '').trim();
        const defLoc = locInput || (_cardQueue[0].location || 'Event').trim();

        try {
          const res = await fetch('/api/generate_multi_pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              cards: _cardQueue,
              default_location: defLoc,
              preserve_order: true,
              original_filename: _importedFileName || ''
            })
          });

          if (!res.ok) {
            const err = await res.json();
            alert('Error: ' + (err.error || 'Failed to generate PDF'));
            btn.disabled = false;
            btn.textContent = origText;
            return;
          }

          const blob = await res.blob();
          let filename = defLoc + ' Soft copy.pdf';
          const disposition = res.headers.get('Content-Disposition');
          if (disposition && disposition.includes('filename=')) {
            const match = disposition.match(/filename=["']?([^"';]+)["']?/);
            if (match && match[1]) filename = match[1].trim();
          }

          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);

          // Save to localStorage
          try {
            localStorage.setItem('umang_last_batch', JSON.stringify({
              cards: _cardQueue,
              location: defLoc,
              time: Date.now()
            }));
          } catch(e) {}

          // Keep cards in queue so user can correct any typo without having to start over!
          btn.disabled = false;
          btn.textContent = origText;
          checkRestoreAvailable();

          const notif = document.getElementById('dlNotice');
          if (notif) {
            notif.innerHTML = `✓ <b>Download ready:</b> ${escapeHtml(filename)} (${_cardQueue.length} card${_cardQueue.length > 1 ? 's' : ''})`;
            notif.style.display = 'block';
            setTimeout(() => { if (notif) notif.style.display = 'none'; }, 8000);
          }
        } catch (err) {
          alert('Failed to generate PDF: ' + err.message);
          btn.disabled = false;
          btn.textContent = origText;
        }
        return;
      }

      // Single card mode: check fields and numeric OTP before download
      const d = fd();
      if (!d.name || !d.name.trim()) {
        alert('Please enter a Guest Name first.');
        document.getElementById('name').focus();
        return;
      }
      if (!d.otp || !d.otp.trim()) {
        alert('Please enter an OTP Code first.');
        document.getElementById('otp').focus();
        return;
      }
      if (!/^\d+$/.test(d.otp.trim())) {
        alert('Invalid OTP: OTP Code must contain only numeric digits (0-9).\n\nPlease remove any letters or symbols.');
        document.getElementById('otp').focus();
        return;
      }
      window.location.href = '/api/download_single?' + new URLSearchParams(d).toString();
    }

    function checkRestoreAvailable() {
      try {
        const raw = localStorage.getItem('umang_last_batch');
        const rBtn = document.getElementById('restoreBtn');
        const rCount = document.getElementById('restoreCount');
        const rBtnEmpty = document.getElementById('restoreBtnEmpty');
        const rCountEmpty = document.getElementById('restoreCountEmpty');

        if (raw) {
          const data = JSON.parse(raw);
          if (data && data.cards && data.cards.length > 0) {
            const count = data.cards.length;
            if (rBtn && rCount) {
              rCount.textContent = count;
              rBtn.style.display = 'inline-block';
            }
            if (rBtnEmpty && rCountEmpty) {
              rCountEmpty.textContent = count;
              rBtnEmpty.style.display = 'inline-block';
            }
            return;
          }
        }
        if (rBtn) rBtn.style.display = 'none';
        if (rBtnEmpty) rBtnEmpty.style.display = 'none';
      } catch (e) {}
    }

    function restoreLastBatch() {
      try {
        const raw = localStorage.getItem('umang_last_batch');
        if (!raw) return;
        const data = JSON.parse(raw);
        if (data && data.cards && data.cards.length > 0) {
          _cardQueue = JSON.parse(JSON.stringify(data.cards));
          _importedFileName = (data.location ? data.location + ' Session' : 'Saved Batch');
          updateQueueUI();
          if (data.location && document.getElementById('location')) {
            document.getElementById('location').value = data.location;
          }
          editQueueItem(0);

          const toast = document.getElementById('queueStatusToast');
          const toastText = document.getElementById('queueStatusText');
          if (toast && toastText) {
            toastText.textContent = `✓ Restored ${data.cards.length} cards from previous download`;
            toast.style.display = 'flex';
            setTimeout(() => { if (toast) toast.style.display = 'none'; }, 6000);
          }
        }
      } catch (e) {
        alert('Could not restore last batch: ' + e.message);
      }
    }

    function triggerPdfImport() {
      const el = document.getElementById('pdfRepairIn');
      if (el) {
        try { el.value = ''; } catch(e) {}
        el.click();
      }
    }

    async function onLoadPdfFile(e) {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      const file = files[0];

      const modal = document.getElementById('pdfLoadingModal');
      const titleEl = document.getElementById('pdfLoadingTitle');
      const descEl = document.getElementById('pdfLoadingDesc');
      const fnEl = document.getElementById('pdfLoadingFileName');
      if (modal) {
        if (titleEl) titleEl.textContent = 'Extracting Cards from PDF...';
        if (fnEl) fnEl.textContent = file.name;
        if (descEl) descEl.textContent = 'Scanning pages, reading QR codes, and extracting guest details. Please wait a moment.';
        modal.style.display = 'flex';
      }

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/load_cards_from_pdf', { method: 'POST', body: formData });
        if (modal) modal.style.display = 'none';

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          alert('Could not inspect PDF: ' + (err.error || 'Server error ' + res.status));
          return;
        }
        const data = await res.json();
        if (data.cards && data.cards.length > 0) {
          _cardQueue = data.cards;
          _loadedPdfBlob = file;
          _importedFileName = file.name;
          updateQueueUI();
          if (data.cards[0].location && document.getElementById('location')) {
            document.getElementById('location').value = data.cards[0].location;
          }

          // Auto-load Card 1 into the form and preview for instant editing
          editQueueItem(0);
          saveSession();

          const toast = document.getElementById('queueStatusToast');
          const toastText = document.getElementById('queueStatusText');
          if (toast && toastText) {
            toastText.textContent = `✓ Loaded ${data.total} cards from "${file.name}"`;
            toast.style.display = 'flex';
            setTimeout(() => { if (toast) toast.style.display = 'none'; }, 7000);
          }
        } else {
          alert(`This PDF contains ${data.total || 0} pages, but no cards could be recognized.`);
        }
      } catch (err) {
        if (modal) modal.style.display = 'none';
        alert('Error loading PDF: ' + err.message);
      } finally {
        try { e.target.value = ''; } catch(e) {}
      }
    }

    async function quickSwapPageInPdf() {
      if (!_loadedPdfBlob) {
        alert('No source PDF is currently loaded. Click "Import PDF to Edit" first.');
        return;
      }
      if (_editingIndex < 0 || _editingIndex >= _cardQueue.length) {
        alert('Please select a card from the queue first.');
        return;
      }

      const d = fd();
      if (!d.name || !d.name.trim()) {
        alert('Guest Name cannot be empty.');
        return;
      }
      if (!d.otp || !d.otp.trim()) {
        alert('OTP Code cannot be empty.');
        return;
      }

      const swapBtn = document.getElementById('quickSwapBtn');
      const origText = swapBtn.textContent;
      swapBtn.disabled = true;
      swapBtn.textContent = 'Replacing page in PDF...';

      const formData = new FormData();
      formData.append('file', _loadedPdfBlob);
      formData.append('page_index', _editingIndex);
      formData.append('name', d.name.trim());
      formData.append('location', d.location.trim() || 'Event');
      formData.append('category', d.category || 'A');
      formData.append('otp', d.otp.trim());
      formData.append('counter', d.counter || '');
      formData.append('style', d.style || 'english');

      try {
        const res = await fetch('/api/replace_pdf_page', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const err = await res.json();
          alert('Error replacing page: ' + (err.error || 'Server error'));
          swapBtn.disabled = false;
          swapBtn.textContent = origText;
          return;
        }

        const blob = await res.blob();
        let filename = (d.location.trim() || 'Event') + ' Soft copy (Corrected).pdf';
        const disposition = res.headers.get('Content-Disposition');
        if (disposition && disposition.includes('filename=')) {
          const match = disposition.match(/filename=["']?([^"';]+)["']?/);
          if (match && match[1]) filename = match[1].trim();
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        // Update in-memory file blob so subsequent swaps can build on this file
        _loadedPdfBlob = new File([blob], filename, { type: 'application/pdf' });

        // Update card in queue
        _cardQueue[_editingIndex] = {
          name: d.name.trim(),
          location: d.location.trim() || 'Event',
          category: d.category || 'A',
          otp: d.otp.trim(),
          style: d.style || 'english',
          counter: d.counter || '',
          color: d.color || ''
        };
        updateQueueUI();

        swapBtn.disabled = false;
        swapBtn.textContent = origText;

        const notif = document.getElementById('dlNotice');
        if (notif) {
          notif.innerHTML = `✓ <b>Page #${_editingIndex + 1} successfully replaced!</b> Downloaded as "${escapeHtml(filename)}".`;
          notif.style.display = 'block';
          setTimeout(() => { if (notif) notif.style.display = 'none'; }, 8000);
        }
      } catch (err) {
        alert('Failed to replace page: ' + err.message);
        swapBtn.disabled = false;
        swapBtn.textContent = origText;
      }
    }

    let _activeJobId = null;
    let _preflightTotal = 0;

    function formatSec(s) {
      s = Math.max(0, Math.round(s));
      if (s < 60) return s + 's';
      const m = Math.floor(s / 60);
      const rem = s % 60;
      return m + 'm ' + (rem > 0 ? rem + 's' : '');
    }

    function toggleErrorDetails() {
      const box = document.getElementById('errorDetailsBox');
      if (!box) return;
      box.style.display = (box.style.display === 'none' || !box.style.display) ? 'block' : 'none';
    }

    function updateEstimates() {
      const opt = document.getElementById('pdfSizeOpt').value;
      if (!_preflightTotal) return;
      const estCard = document.getElementById('estimateCard');
      const timeEl = document.getElementById('estTimeLabel');
      const sizeEl = document.getElementById('estSizeLabel');
      if (estCard) estCard.style.display = 'block';

      if (opt === 'compact') {
        const estSec = Math.max(2, Math.round(_preflightTotal / 12));
        const estMb = Math.max(1, (_preflightTotal * 0.008).toFixed(1));
        if (timeEl) timeEl.textContent = '~' + formatSec(estSec);
        if (sizeEl) sizeEl.textContent = '~' + (estMb >= 1000 ? (estMb/1024).toFixed(1) + ' GB' : estMb + ' MB') + ' (Optimized size)';
      } else {
        const estSec = Math.max(5, Math.round(_preflightTotal / 5));
        const estMb = Math.max(1, (_preflightTotal * 0.95).toFixed(0));
        if (timeEl) timeEl.textContent = '~' + formatSec(estSec);
        if (sizeEl) sizeEl.textContent = '~' + (estMb >= 1000 ? (estMb/1024).toFixed(1) + ' GB' : estMb + ' MB') + ' (High definition)';
      }
    }

    function onRosterDrop(e) {
      e.preventDefault();
      const dz = document.getElementById('dropZone');
      if (dz) dz.classList.remove('drag-over');
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleRosterFiles(Array.from(e.dataTransfer.files));
      }
    }

    function onRosterFile(e) {
      if (e.target && e.target.files && e.target.files.length > 0) {
        handleRosterFiles(Array.from(e.target.files));
      }
    }

    function handleRosterFiles(newFiles) {
      const validFiles = newFiles.filter(f => /\.(xlsx|xls|csv)$/i.test(f.name));
      if (validFiles.length === 0) {
        alert('Please select Excel (.xlsx, .xls) or CSV (.csv) files.');
        return;
      }

      // Avoid duplicate uploads of exact same file (by name and size)
      const existingKeys = new Set(_files.map(f => f.name + '::' + f.size));
      for (const f of validFiles) {
        const key = f.name + '::' + f.size;
        if (!existingKeys.has(key)) {
          _files.push(f);
          existingKeys.add(key);
        }
      }

      runPreflightValidation();
    }

    function removeRosterFile(idx) {
      if (idx >= 0 && idx < _files.length) {
        _files.splice(idx, 1);
      }
      const rosterIn = document.getElementById('rosterIn');
      if (rosterIn) rosterIn.value = '';

      if (_files.length === 0) {
        clearAllUploadedFiles();
      } else {
        runPreflightValidation();
      }
    }

    function clearAllUploadedFiles() {
      _files = [];
      const rosterIn = document.getElementById('rosterIn');
      if (rosterIn) rosterIn.value = '';
      const manifestBox = document.getElementById('fileManifestBox');
      if (manifestBox) manifestBox.style.display = 'none';
      const manifestList = document.getElementById('fileManifestList');
      if (manifestList) manifestList.innerHTML = '';
      const summaryBox = document.getElementById('summaryBox');
      if (summaryBox) summaryBox.style.display = 'none';
      const fileInfo = document.getElementById('fileInfo');
      if (fileInfo) fileInfo.innerHTML = '';
      const locStat = document.getElementById('sLocations');
      if (locStat) locStat.style.display = 'none';
      const batchBtn = document.getElementById('batchBtn');
      if (batchBtn) batchBtn.disabled = true;

      // Reset export mode
      const expSel = document.getElementById('exportMode');
      if (expSel) {
        const optMerged = expSel.querySelector('option[value="merged"]');
        if (optMerged) {
          optMerged.disabled = false;
          optMerged.textContent = 'Single Combined PDF';
        }
        expSel.value = 'merged';
      }
      const sValid = document.getElementById('sValid');
      if (sValid) sValid.style.display = 'none';
      const sInvalid = document.getElementById('sInvalid');
      if (sInvalid) sInvalid.style.display = 'none';
      const estCard = document.getElementById('estimateCard');
      if (estCard) estCard.style.display = 'none';
    }

    async function runPreflightValidation() {
      if (!_files || _files.length === 0) {
        clearAllUploadedFiles();
        return;
      }
      const formData = new FormData();
      for (let i = 0; i < _files.length; i++) {
        formData.append('file', _files[i]);
      }

      const fileInfo = document.getElementById('fileInfo');
      if (fileInfo) {
        fileInfo.innerHTML = '';
      }

      try {
        const res = await fetch('/api/preflight', { method: 'POST', body: formData });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          alert('Validation error: ' + (err.error || 'Failed to inspect file(s)'));
          return;
        }
        const data = await res.json();
        _preflightTotal = data.valid || 0;

        // Render Manifest Box (Clean per-file list with location, count and remove button)
        const manifestBox = document.getElementById('fileManifestBox');
        const manifestList = document.getElementById('fileManifestList');
        const manifestBadge = document.getElementById('manifestCountBadge');
        if (manifestBox && manifestList) {
          manifestBox.style.display = 'block';
          if (manifestBadge) {
            manifestBadge.textContent = _files.length;
          }

          const fileRows = (data.files || []).map((f, idx) => {
            return `
              <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;gap:12px">
                <div style="display:flex;align-items:center;gap:8px;min-width:0;flex:1">
                  <span style="font-size:13px;font-weight:600;color:#0f172a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(f.filename)}</span>
                  <span style="font-size:11.5px;font-weight:600;color:#64748b;background:#f1f5f9;padding:1px 6px;border-radius:4px">${escapeHtml(f.location)}</span>
                </div>
                <div style="display:flex;align-items:center;gap:10px;flex-shrink:0">
                  <span style="font-size:12.5px;font-weight:700;color:#0f172a">${f.valid} cards</span>
                  ${f.invalid > 0 ? `<span style="font-size:11px;font-weight:600;color:#b91c1c;background:#fee2e2;padding:1px 6px;border-radius:4px">${f.invalid} errors</span>` : ''}
                  <button type="button" onclick="event.stopPropagation(); removeRosterFile(${idx})" style="background:none;border:none;color:#94a3b8;font-size:16px;line-height:1;cursor:pointer;padding:2px 6px;border-radius:4px;transition:color 0.15s" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#94a3b8'" title="Remove file">&times;</button>
                </div>
              </div>
            `;
          }).join('');
          manifestList.innerHTML = fileRows;
        }

        if (fileInfo) {
          fileInfo.innerHTML = '';
        }

        // Summary Box
        document.getElementById('summaryBox').style.display = 'block';

        const sTotal = document.getElementById('sTotal');
        const sValid = document.getElementById('sValid');
        const errEl = document.getElementById('sInvalid');
        const errBox = document.getElementById('errorDetailsBox');
        const errList = document.getElementById('errorListItems');
        const errCountText = document.getElementById('errCountText');
        const validBadge = document.getElementById('validBadge');

        // If all rows are valid, show only 1 number (Total: N) without duplicate Ready: N
        // If there are skipped/invalid rows, show both Total Rows, Ready, and Issues
        if (data.invalid > 0) {
          sTotal.style.display = 'inline-block';
          sTotal.textContent = 'Total Rows: ' + data.total;
          sValid.style.display = 'inline-block';
          sValid.textContent = 'Ready: ' + data.valid;
          errEl.style.display = 'inline-block';
          errEl.textContent = 'Issues: ' + data.invalid;
          if (errCountText) errCountText.textContent = data.invalid;
          if (validBadge) validBadge.style.display = 'none';
          if (errList) {
            errList.innerHTML = (data.errors || []).map(err => `<div>&bull; ${escapeHtml(err)}</div>`).join('');
            if (data.total_errors > (data.errors || []).length) {
              errList.innerHTML += `<div style="margin-top:4px;font-style:italic">...and ${data.total_errors - (data.errors || []).length} more invalid rows</div>`;
            }
          }
          if (errBox) errBox.style.display = 'block';
        } else {
          sTotal.style.display = 'inline-block';
          sTotal.textContent = 'Total: ' + data.total;
          sValid.style.display = 'none';
          errEl.style.display = 'none';
          if (errBox) errBox.style.display = 'none';
          if (validBadge) validBadge.style.display = 'inline-block';
        }

        const locStat = document.getElementById('sLocations');
        if (locStat) {
          if (data.location_count > 1) {
            locStat.style.display = 'inline-block';
            locStat.textContent = `Locations: ${data.location_count}`;
          } else if (data.location_count === 1) {
            locStat.style.display = 'inline-block';
            locStat.textContent = `Location: ${data.locations[0]}`;
          } else {
            locStat.style.display = 'none';
          }
        }

        const pp = document.getElementById('catPills');
        pp.innerHTML = '';
        for (const [k, v] of Object.entries(data.categories || {})) {
          const s = document.createElement('span');
          s.textContent = k + ': ' + v;
          pp.appendChild(s);
        }

        // Package Mode: when multi-location or multiple files, auto-set to 'zip' and disable 'merged'
        const expSel = document.getElementById('exportMode');
        if (expSel) {
          const optMerged = expSel.querySelector('option[value="merged"]');
          if (data.location_count > 1 || _files.length > 1) {
            expSel.value = 'zip';
            if (optMerged) {
              optMerged.disabled = true;
              optMerged.textContent = 'Single Combined PDF (Disabled)';
            }
          } else {
            if (optMerged) {
              optMerged.disabled = false;
              optMerged.textContent = 'Single Combined PDF';
            }
          }
        }

        updateEstimates();
        document.getElementById('batchBtn').disabled = (data.valid === 0);
      } catch (err) {
        document.getElementById('batchBtn').disabled = false;
      }
    }

    async function runBatch() {
      if (!_files || _files.length === 0) return;
      const btn = document.getElementById('batchBtn');
      const cancelBtn = document.getElementById('cancelBatchBtn');
      btn.style.display = 'block';
      btn.disabled = true;
      btn.textContent = 'Compiling Production Batch...';
      if (cancelBtn) {
        cancelBtn.disabled = false;
        cancelBtn.textContent = '✕ Cancel Generation';
        cancelBtn.style.display = 'inline-block';
      }

      const stoppedBox = document.getElementById('stoppedBox');
      if (stoppedBox) stoppedBox.style.display = 'none';
      document.getElementById('doneBox').style.display = 'none';
      const timeline = document.getElementById('timelineCard');
      timeline.style.display = 'block';

      // Reset progress UI
      document.getElementById('pBarFill').style.width = '0%';
      document.getElementById('pBarFill').style.background = 'var(--blue)';
      document.getElementById('pPercentLabel').textContent = '0%';
      document.getElementById('pStatusLabel').textContent = 'Rendering Print-Ready Batch...';
      document.getElementById('tStep3').className = 't-step active';
      document.getElementById('tCircle3').textContent = '•';
      document.getElementById('tLine3').className = 't-line';
      document.getElementById('tStep4').className = 't-step';

      // Reset category pills
      ['A','B','C','D','E','F','G','H'].forEach(c => {
        const pill = document.getElementById('trk-' + c);
        if (pill) pill.className = 'trk-pill';
      });

      const mode = document.getElementById('exportMode').value;
      const pdfSizeOpt = document.getElementById('pdfSizeOpt').value;
      const batchStyle = document.getElementById('batchStyleVal') ? document.getElementById('batchStyleVal').value : 'english';
      const body = new FormData();
      for (let i = 0; i < _files.length; i++) {
        body.append('file', _files[i]);
      }
      body.append('mode', mode);
      body.append('pdf_size_opt', pdfSizeOpt);
      body.append('style', batchStyle);

      try {
        const res = await fetch('/api/start_batch', { method: 'POST', body });
        if (!res.ok) {
          const e = await res.json();
          alert(e.error || 'Generation error');
          btn.disabled = false;
          btn.textContent = 'Compile Production Batch';
          if (cancelBtn) cancelBtn.style.display = 'none';
          timeline.style.display = 'none';
          return;
        }
        const startData = await res.json();
        _activeJobId = startData.job_id;
        
        // Start polling progress
        pollBatchProgress(_activeJobId, mode);
      } catch (err) {
        alert(err.message);
        btn.disabled = false;
        btn.textContent = 'Compile Production Batch';
        if (cancelBtn) cancelBtn.style.display = 'none';
        timeline.style.display = 'none';
      }
    }

    async function cancelBatch() {
      if (!_activeJobId) return;
      const cancelBtn = document.getElementById('cancelBatchBtn');
      if (cancelBtn) {
        cancelBtn.disabled = true;
        cancelBtn.textContent = 'Stopping & Saving...';
      }
      try {
        await fetch('/api/batch_cancel/' + _activeJobId, { method: 'POST' });
      } catch (e) {}
    }

    function pollBatchProgress(jobId, mode) {
      if (_pollTimer) clearInterval(_pollTimer);

      _pollTimer = setInterval(async () => {
        try {
          const res = await fetch('/api/batch_progress/' + jobId);
          if (!res.ok) return;
          const p = await res.json();

          if (p.status === 'processing') {
            document.getElementById('pBarFill').style.width = p.percent + '%';
            document.getElementById('pPercentLabel').textContent = p.percent + '%';
            document.getElementById('pStatusLabel').textContent = 'Rendering Print-Ready Batch...';
            document.getElementById('pCountLabel').textContent = p.current + ' / ' + p.total;
            document.getElementById('pSpeedLabel').textContent = p.speed + ' coupons/sec';
            document.getElementById('pEtaLabel').textContent = formatSec(p.elapsed) + ' elapsed • ~' + formatSec(p.eta) + ' remaining';
            document.getElementById('pCurrentCardLabel').textContent = p.current_card || '-';

            // Highlight current category
            if (p.category) {
              const currentPill = document.getElementById('trk-' + p.category);
              if (currentPill) currentPill.className = 'trk-pill current';
              
              // Mark earlier categories as done
              const catLetters = ['A','B','C','D','E','F','G','H'];
              const curIdx = catLetters.indexOf(p.category);
              for (let i = 0; i < curIdx; i++) {
                const prevPill = document.getElementById('trk-' + catLetters[i]);
                if (prevPill) prevPill.className = 'trk-pill done';
              }
            }
          } else if (p.status === 'completed') {
            clearInterval(_pollTimer);
            document.getElementById('pBarFill').style.width = '100%';
            document.getElementById('pPercentLabel').textContent = '100%';
            document.getElementById('pStatusLabel').textContent = 'Completed!';
            document.getElementById('pCountLabel').textContent = p.total + ' / ' + p.total;
            document.getElementById('pSpeedLabel').textContent = p.speed + ' c/s avg';
            document.getElementById('pEtaLabel').textContent = formatSec(p.elapsed) + ' total';

            // Mark stepper completed
            document.getElementById('tStep3').className = 't-step done';
            document.getElementById('tCircle3').textContent = '✓';
            document.getElementById('tLine3').className = 't-line done';
            document.getElementById('tStep4').className = 't-step done';
            document.getElementById('tCircle4').textContent = '✓';

            // Mark all category pills done
            ['A','B','C','D','E','F','G','H'].forEach(c => {
              const pill = document.getElementById('trk-' + c);
              if (pill) pill.className = 'trk-pill done';
            });

            // Hide stopped box & show done box with file size and download button
            const stoppedBox = document.getElementById('stoppedBox');
            if (stoppedBox) stoppedBox.style.display = 'none';

            const doneBox = document.getElementById('doneBox');
            doneBox.style.display = 'block';
            document.getElementById('doneDesc').textContent = p.filename + ' (' + p.file_size_mb + ' MB) · All ' + p.total + ' coupons generated successfully.';
            const dl = document.getElementById('doneLink');
            dl.href = '/api/batch_download/' + jobId;
            dl.download = p.filename;
            dl.textContent = p.filename.endsWith('.zip') ? 'Download Production ZIP (By Location)' : 'Download Production PDF';

            const btn = document.getElementById('batchBtn');
            const cancelBtn = document.getElementById('cancelBatchBtn');
            btn.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Compile Production Batch';
            if (cancelBtn) cancelBtn.style.display = 'none';
          } else if (p.status === 'stopped') {
            clearInterval(_pollTimer);
            document.getElementById('pStatusLabel').textContent = `Paused at Card ${p.current} of ${p.total}`;
            document.getElementById('pBarFill').style.background = '#f59e0b';

            const btn = document.getElementById('batchBtn');
            const cancelBtn = document.getElementById('cancelBatchBtn');
            if (cancelBtn) {
              cancelBtn.style.display = 'none';
              cancelBtn.disabled = false;
              cancelBtn.textContent = '✕ Cancel Generation';
            }
            btn.style.display = 'none';

            const stoppedBox = document.getElementById('stoppedBox');
            if (stoppedBox) {
              stoppedBox.style.display = 'block';
              const cntEl = document.getElementById('partialCountLabel');
              if (cntEl) cntEl.textContent = p.current;
              const descEl = document.getElementById('stoppedDesc');
              if (descEl) {
                descEl.textContent = `Batch generation paused at card #${p.current} of ${p.total}. ` +
                  (p.file_size_mb ? `Partial print document (${p.file_size_mb} MB) is compiled and ready for download. ` : '') +
                  (p.can_resume ? `You can download the cards printed so far or click "Resume Generation" to continue from card #${p.current + 1}.` : `You can download the completed locations below.`);
              }
              const partialDl = document.getElementById('partialDlLink');
              if (partialDl) {
                partialDl.href = '/api/batch_download/' + jobId;
                partialDl.download = p.filename || `Partial_Coupons_${p.current}.pdf`;
              }
              const resumeBtn = document.getElementById('resumeBatchBtn');
              if (resumeBtn) {
                resumeBtn.style.display = p.can_resume ? 'inline-flex' : 'none';
                resumeBtn.disabled = false;
                resumeBtn.textContent = `▶️ Resume Generation (Card #${p.current + 1})`;
              }
            }
          } else if (p.status === 'cancelled') {
            clearInterval(_pollTimer);
            document.getElementById('pStatusLabel').textContent = 'Generation Cancelled by User';
            document.getElementById('pBarFill').style.background = '#ef4444';
            const btn = document.getElementById('batchBtn');
            const cancelBtn = document.getElementById('cancelBatchBtn');
            btn.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Compile Production Batch';
            if (cancelBtn) {
              cancelBtn.style.display = 'none';
              cancelBtn.disabled = false;
              cancelBtn.textContent = '✕ Cancel Generation';
            }
          } else if (p.status === 'error') {
            clearInterval(_pollTimer);
            alert('Batch Generation Error: ' + (p.error || 'Failed'));
            const btn = document.getElementById('batchBtn');
            const cancelBtn = document.getElementById('cancelBatchBtn');
            btn.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Compile Production Batch';
            if (cancelBtn) cancelBtn.style.display = 'none';
          }
        } catch (err) {}
      }, 500);
    }

    async function resumeBatch() {
      if (!_activeJobId) return;
      const resumeBtn = document.getElementById('resumeBatchBtn');
      if (resumeBtn) {
        resumeBtn.disabled = true;
        resumeBtn.textContent = 'Resuming batch...';
      }
      try {
        const res = await fetch('/api/batch_resume/' + _activeJobId, { method: 'POST' });
        if (!res.ok) {
          const err = await res.json();
          alert('Could not resume batch: ' + (err.error || 'Server error'));
          if (resumeBtn) {
            resumeBtn.disabled = false;
            resumeBtn.textContent = '▶️ Resume Generation';
          }
          return;
        }
        document.getElementById('stoppedBox').style.display = 'none';
        document.getElementById('pBarFill').style.background = 'var(--blue)';
        document.getElementById('pStatusLabel').textContent = 'Resuming Print-Ready Batch...';
        const cancelBtn = document.getElementById('cancelBatchBtn');
        if (cancelBtn) {
          cancelBtn.style.display = 'inline-block';
          cancelBtn.disabled = false;
          cancelBtn.textContent = '✕ Cancel Generation';
        }
        pollBatchProgress(_activeJobId);
      } catch (e) {
        alert('Resume error: ' + e.message);
        if (resumeBtn) {
          resumeBtn.disabled = false;
          resumeBtn.textContent = '▶️ Resume Generation';
        }
      }
    }

    function restartBatch() {
      document.getElementById('stoppedBox').style.display = 'none';
      document.getElementById('doneBox').style.display = 'none';
      document.getElementById('timelineCard').style.display = 'none';
      const btn = document.getElementById('batchBtn');
      btn.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Compile Production Batch';
      _activeJobId = null;
      clearAllUploadedFiles();
    }

    // Auto-restore working session on page load (queue, edits, and draft inputs)
    window.addEventListener('DOMContentLoaded', () => {
      checkRestoreAvailable();
      const hasRestored = restoreSession();
      if (!hasRestored) {
        render();
      }
    });
  </script>
</body>
</html>
"""

def process_batch_worker(job_id, cards, mode, upload_filename="", pdf_size_opt="compact", start_index=0, batch_style=""):
    """Background worker generating print cards with sequence sorting, cancel/resume support, and live progress tracking."""
    t0 = time.time()
    total = len(cards)
    gen = make_cards.FastCardGenerator()
    is_standalone = (pdf_size_opt == "heavy")

    # Determine clean download filename: strictly "{Location} Soft copy"
    unique_locs = list(OrderedDict.fromkeys(c.get("location", "").strip() for c in cards if c.get("location", "").strip()))
    if len(unique_locs) == 1:
        loc_name = unique_locs[0]
    elif len(unique_locs) > 1:
        loc_name = f"Umang Utsav ({len(unique_locs)} Locations)"
    elif upload_filename:
        inferred = make_cards.extract_location_from_filename(upload_filename)
        loc_name = inferred if inferred else (unique_locs[0] if unique_locs else "Event")
    else:
        loc_name = unique_locs[0] if unique_locs else "Event"

    is_hindi_batch = (batch_style == "hindi") or (all(c.get("style") == "hindi" for c in cards) and len(cards) > 0)
    suffix = " (Hindi)" if is_hindi_batch else ""
    output_name = f"{loc_name} Soft copy{suffix}"

    try:
        if mode == "zip":
            # Group cards by location
            groups = OrderedDict()
            for cd in cards:
                loc = cd.get("location", "").strip() or "Event"
                groups.setdefault(loc, []).append(cd)

            # Dedicated working directory for this job's per-location PDFs
            parts_dir = os.path.join(OUTPUT_DIR, f"parts_{job_id}")
            os.makedirs(parts_dir, exist_ok=True)

            zip_filename = f"{output_name}.zip"
            zip_path = os.path.join(OUTPUT_DIR, f"batch_{job_id}.zip")

            processed = 0
            for loc, loc_cards in groups.items():
                loc_cards = make_cards.sort_cards_sequence(loc_cards)
                loc_total = len(loc_cards)
                loc_filename = f"{loc} Soft copy{suffix}.pdf"
                loc_pdf_path = os.path.join(parts_dir, loc_filename)

                # If resuming and this entire location was already completed
                if start_index > 0 and processed + loc_total <= start_index:
                    processed += loc_total
                    continue

                # If resuming mid-location
                loc_start = max(0, start_index - processed) if start_index > 0 else 0
                if loc_start > 0 and os.path.exists(loc_pdf_path):
                    out_doc = pymupdf.open(loc_pdf_path)
                else:
                    out_doc = pymupdf.open()

                for i in range(loc_start, loc_total):
                    cd = loc_cards[i]
                    if JOBS.get(job_id, {}).get("cancel_requested"):
                        # SAVE CURRENT LOCATION PDF WITH ALL CARDS RENDERED SO FAR
                        if len(out_doc) > 0:
                            out_doc.set_metadata({"subject": "UmangCouponData:" + json.dumps(loc_cards[:len(out_doc)])})
                            tmp_p = loc_pdf_path + ".tmp"
                            if is_standalone:
                                out_doc.save(tmp_p, deflate=False)
                            else:
                                out_doc.save(tmp_p, deflate=True, garbage=3)
                            out_doc.close()
                            if os.path.exists(loc_pdf_path):
                                try: os.remove(loc_pdf_path)
                                except Exception: pass
                            os.replace(tmp_p, loc_pdf_path)
                        else:
                            out_doc.close()

                        # PACKAGE ALL COMPLETED AND PARTIAL LOCATION PDFs INTO ZIP
                        if processed > 0:
                            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
                                for f_name in sorted(os.listdir(parts_dir)):
                                    if f_name.endswith(".pdf"):
                                        f_full = os.path.join(parts_dir, f_name)
                                        zf.write(f_full, arcname=f_name)

                            file_size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2) if os.path.exists(zip_path) else 0
                            partial_zip_name = f"{output_name} (Partial {processed} of {total}).zip"
                            JOBS[job_id].update({
                                "status": "stopped",
                                "current": processed,
                                "total": total,
                                "percent": round((processed / total) * 100, 1),
                                "file_path": zip_path,
                                "file_size_mb": file_size_mb,
                                "filename": partial_zip_name,
                                "can_resume": True,
                                "remaining": total - processed
                            })
                        else:
                            JOBS[job_id]["status"] = "cancelled"
                            if os.path.exists(zip_path):
                                try: os.remove(zip_path)
                                except Exception: pass
                        return

                    gen.draw_card_page(out_doc, cd, standalone=is_standalone)
                    processed += 1
                    el = time.time() - t0
                    speed = (processed - start_index) / el if el > 0 else 0
                    rem = (total - processed) / speed if speed > 0 else 0

                    JOBS[job_id].update({
                        "current": processed,
                        "percent": round((processed / total) * 100, 1),
                        "current_card": f"Cat {cd['category']} • {cd['name']} (OTP {cd['otp']})",
                        "category": cd["category"],
                        "speed": round(speed, 1),
                        "elapsed": round(el, 1),
                        "eta": round(rem, 1)
                    })

                # Location completed! Save to disk and close out_doc to free memory
                out_doc.set_metadata({"subject": "UmangCouponData:" + json.dumps(loc_cards)})
                tmp_p = loc_pdf_path + ".tmp"
                if is_standalone:
                    out_doc.save(tmp_p, deflate=False)
                else:
                    out_doc.save(tmp_p, deflate=True, garbage=3)
                out_doc.close()
                if os.path.exists(loc_pdf_path):
                    try: os.remove(loc_pdf_path)
                    except Exception: pass
                os.replace(tmp_p, loc_pdf_path)

            # All locations completed! Package into final ZIP
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
                for f_name in sorted(os.listdir(parts_dir)):
                    if f_name.endswith(".pdf"):
                        f_full = os.path.join(parts_dir, f_name)
                        zf.write(f_full, arcname=f_name)

            file_size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
            el_total = time.time() - t0
            avg_speed = (total - start_index) / el_total if el_total > 0 else 0
            JOBS[job_id].update({
                "status": "completed",
                "current": total,
                "percent": 100.0,
                "speed": round(avg_speed, 1),
                "elapsed": round(el_total, 1),
                "file_path": zip_path,
                "file_size_mb": file_size_mb,
                "filename": zip_filename,
                "can_resume": False
            })
        else:
            pdf_filename = f"{output_name}.pdf"
            pdf_path = os.path.join(OUTPUT_DIR, f"batch_{job_id}.pdf")

            if start_index > 0 and os.path.exists(pdf_path):
                out_doc = pymupdf.open(pdf_path)
            else:
                out_doc = pymupdf.open()

            for i in range(start_index, total):
                cd = cards[i]
                if JOBS.get(job_id, {}).get("cancel_requested"):
                    if i > 0:
                        out_doc.set_metadata({"subject": "UmangCouponData:" + json.dumps(cards[:i])})
                        tmp_path = pdf_path + ".partial.tmp"
                        if is_standalone:
                            out_doc.save(tmp_path, deflate=False)
                        else:
                            out_doc.save(tmp_path, deflate=True, garbage=3)
                        out_doc.close()
                        if os.path.exists(pdf_path):
                            try: os.remove(pdf_path)
                            except Exception: pass
                        os.replace(tmp_path, pdf_path)

                        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                        partial_filename = f"{output_name} (Cards 1-{i} of {total}).pdf"
                        JOBS[job_id].update({
                            "status": "stopped",
                            "current": i,
                            "total": total,
                            "percent": round((i / total) * 100, 1),
                            "file_path": pdf_path,
                            "file_size_mb": round(file_size_mb, 2),
                            "filename": partial_filename,
                            "can_resume": True,
                            "remaining": total - i
                        })
                    else:
                        out_doc.close()
                        JOBS[job_id]["status"] = "cancelled"
                        if os.path.exists(pdf_path):
                            try: os.remove(pdf_path)
                            except Exception: pass
                    return

                gen.draw_card_page(out_doc, cd, standalone=is_standalone)
                processed_now = i + 1
                el = time.time() - t0
                session_cards = processed_now - start_index
                speed = session_cards / el if el > 0 else 0
                rem = (total - processed_now) / speed if speed > 0 else 0

                JOBS[job_id].update({
                    "current": processed_now,
                    "percent": round((processed_now / total) * 100, 1),
                    "current_card": f"Cat {cd['category']} • {cd['name']} (OTP {cd['otp']})",
                    "category": cd["category"],
                    "speed": round(speed, 1),
                    "elapsed": round(el, 1),
                    "eta": round(rem, 1)
                })

            out_doc.set_metadata({"subject": "UmangCouponData:" + json.dumps(cards)})
            tmp_path = pdf_path + ".final.tmp"
            if is_standalone:
                out_doc.save(tmp_path, deflate=False)
            else:
                out_doc.save(tmp_path, deflate=True, garbage=3)
            out_doc.close()
            if os.path.exists(pdf_path):
                try: os.remove(pdf_path)
                except Exception: pass
            os.replace(tmp_path, pdf_path)

            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            el_total = time.time() - t0
            avg_speed = (total - start_index) / el_total if el_total > 0 else 0
            JOBS[job_id].update({
                "status": "completed",
                "current": total,
                "percent": 100.0,
                "speed": round(avg_speed, 1),
                "elapsed": round(el_total, 1),
                "file_path": pdf_path,
                "file_size_mb": round(file_size_mb, 2),
                "filename": pdf_filename,
                "can_resume": False
            })
    except Exception as e:
        JOBS[job_id].update({
            "status": "error",
            "error": str(e)
        })


@app.route("/")
def index():
    resp = make_response(render_template_string(ENTERPRISE_UI_HTML))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@app.route("/api/preview")
def preview():
    card = {
        "name": request.args.get("name", "").strip(),
        "location": request.args.get("location", "").strip(),
        "category": request.args.get("category", "E").strip(),
        "otp": request.args.get("otp", "").strip(),
        "style": request.args.get("style", "english").strip(),
        "counter": request.args.get("counter", "").strip(),
        "color": request.args.get("color", "").strip(),
        "is_preview": True,
    }
    try:
        png_bytes = make_cards.card_to_png_bytes(card, dpi=180)
        return send_file(io.BytesIO(png_bytes), mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/download_single")
def download_single():
    card = {
        "name": request.args.get("name", "").strip(),
        "location": request.args.get("location", "").strip(),
        "category": request.args.get("category", "E").strip(),
        "otp": request.args.get("otp", "").strip(),
        "style": request.args.get("style", "english").strip(),
        "counter": request.args.get("counter", "").strip(),
        "color": request.args.get("color", "").strip(),
    }
    try:
        pdf_bytes = make_cards.card_to_pdf_bytes(card)
        loc = (card.get("location") or "Event").strip()
        fname = f"{loc} Soft copy.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=fname
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/download_png")
def download_png():
    card = {
        "name": request.args.get("name", "").strip(),
        "location": request.args.get("location", "").strip(),
        "category": request.args.get("category", "E").strip(),
        "otp": request.args.get("otp", "").strip(),
        "style": request.args.get("style", "english").strip(),
        "counter": request.args.get("counter", "").strip(),
        "color": request.args.get("color", "").strip(),
    }
    try:
        png_bytes = make_cards.card_to_png_bytes(card, dpi=300)
        loc = (card.get("location") or "Event").strip()
        fname = f"{loc} Soft copy.png"
        return send_file(
            io.BytesIO(png_bytes),
            mimetype="image/png",
            as_attachment=True,
            download_name=fname
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/generate_multi_images", methods=["POST"])
def generate_multi_images():
    try:
        data = request.get_json(force=True)
        raw_cards = data.get("cards", [])
        if not raw_cards:
            return jsonify({"error": "No attendee records provided"}), 400
        
        default_loc = (data.get("default_location") or "Event").strip() or "Event"

        cards = []
        for i, c in enumerate(raw_cards):
            name = c.get("name", "").strip() or f"Guest_{i+1}"
            cat = c.get("category", "E").strip().upper()
            otp = c.get("otp", "").strip() or f"{10000+i}"
            loc = c.get("location", default_loc).strip() or default_loc
            cnt = c.get("counter", "").strip() or cat
            style = c.get("style", "english").strip().lower()
            cards.append({
                "name": name,
                "category": cat,
                "otp": otp,
                "location": loc,
                "counter": cnt,
                "style": style,
                "color": c.get("color", "")
            })

        if len(cards) == 1:
            png_bytes = make_cards.card_to_png_bytes(cards[0], dpi=300)
            loc = cards[0]["location"]
            fname = f"{loc} Soft copy.png"
            return send_file(
                io.BytesIO(png_bytes),
                mimetype="image/png",
                as_attachment=True,
                download_name=fname
            )

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, c in enumerate(cards):
                png_bytes = make_cards.card_to_png_bytes(c, dpi=300)
                safe_name = re.sub(r"[^\w\s-]", "", c["name"]).strip().replace(" ", "_")
                img_name = f"{idx+1:02d}_{safe_name}_Cat{c['category']}_{c['otp']}.png"
                zf.writestr(img_name, png_bytes)

        zip_buf.seek(0)
        zip_fname = f"{default_loc} Card Images.zip"
        return send_file(
            zip_buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=zip_fname
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/generate_multi_pdf", methods=["POST"])
def generate_multi_pdf():
    try:
        data = request.get_json(force=True)
        raw_cards = data.get("cards", [])
        if not raw_cards:
            return jsonify({"error": "No attendee records provided"}), 400
        
        default_loc = (data.get("default_location") or "Event").strip() or "Event"
        default_style = data.get("style", "english")
        preserve_order = data.get("preserve_order", True)

        valid_cards = []
        for i, c in enumerate(raw_cards):
            name = str(c.get("name", "")).strip() or f"Guest_{i+1}"
            loc = str(c.get("location", "")).strip() or default_loc
            cat = str(c.get("category", "")).strip().upper() or "A"
            raw_otp = str(c.get("otp", "")).strip()
            otp = re.sub(r"\D", "", raw_otp)
            if not otp:
                otp = f"{10000+i}"
            style = str(c.get("style") or default_style).strip().lower()
            valid_cards.append({
                "name": name,
                "location": loc,
                "category": cat,
                "otp": otp,
                "style": "hindi" if "hindi" in style else "english",
                "counter": c.get("counter", ""),
                "color": c.get("color", "")
            })

        if not valid_cards:
            return jsonify({"error": "Please enter valid Guest Name, Category, and OTP"}), 400

        # Sort only if preserve_order is False, otherwise keep exact page sequence
        if not preserve_order:
            sorted_cards = make_cards.sort_cards_sequence(valid_cards)
        else:
            sorted_cards = valid_cards

        gen = make_cards.FastCardGenerator()
        out_doc = pymupdf.open()
        for cd in sorted_cards:
            gen.draw_card_page(out_doc, cd, standalone=True)

        out_doc.set_metadata({"subject": "UmangCouponData:" + json.dumps(sorted_cards)})
        pdf_bytes = out_doc.tobytes(deflate=False)
        out_doc.close()

        # Filename handling
        orig_fname = str(data.get("original_filename") or "").strip()
        locs = list(OrderedDict.fromkeys(c["location"] for c in sorted_cards if c.get("location") and c["location"] != "Event"))
        loc_name = locs[0] if locs else default_loc

        if orig_fname:
            base_fname = re.sub(r"\.pdf$", "", orig_fname, flags=re.I)
            if "(Edited)" not in base_fname:
                fname = f"{base_fname} (Edited).pdf"
            else:
                fname = f"{base_fname}.pdf"
        else:
            fname = f"{loc_name} Soft copy.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=fname
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

_ocr_instance = None
_qr_detector_instance = None
_ocr_lock = threading.Lock()

def get_ocr_instance():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_instance = RapidOCR(use_angle_cls=False)
        except Exception as e:
            print("RapidOCR load failed:", e)
    return _ocr_instance

def get_qr_detector_instance():
    global _qr_detector_instance
    if _qr_detector_instance is None:
        try:
            import cv2
            _qr_detector_instance = cv2.QRCodeDetector()
        except Exception as e:
            print("QRCodeDetector load failed:", e)
    return _qr_detector_instance

def parse_card_from_pdf_page(page):
    import cv2
    import numpy as np
    import re
    import json

    # 1. Instant extraction via embedded invisible text layer (0.0001s!)
    try:
        txt = page.get_text()
        if txt and "UmangCard:" in txt:
            m = re.search(r"UmangCard:(\{.*?\})", txt)
            if m:
                card_data = json.loads(m.group(1))
                # Enforce clean counter binding
                cat = (card_data.get("category") or "A").strip().upper()
                c_cnt = card_data.get("counter", "")
                clean_c = re.sub(r"^(counter\s*[-:]?\s*)", "", str(c_cnt), flags=re.I).strip()
                clean_c = re.sub(r"^-\s*", "", clean_c).strip()
                if not clean_c or clean_c.upper() in ["A", "B", "C", "D", "E", "F", "G", "H", "A-D"]:
                    card_data["counter"] = "A-D" if cat in "ABCD" else f"- {cat}"
                return card_data
    except Exception:
        pass

    # 2. Text-based regex extraction (0.001s!)
    try:
        txt = page.get_text()
        if txt and ("OTP" in txt or "Category" in txt or "Collect" in txt):
            lines = [line.strip() for line in txt.split("\n") if line.strip()]
            otp = ""
            cat = ""
            name = ""
            loc = ""
            counter = ""
            for i, line in enumerate(lines):
                m_otp = re.search(r"OTP\s*[:\s]\s*(\d+)", line, re.I)
                if m_otp and not otp:
                    otp = m_otp.group(1)
                m_cat = re.search(r"Gift Category\s*[:\s]\s*([A-Za-z0-9]+)", line, re.I)
                if m_cat:
                    cat = m_cat.group(1).upper()
                    if i > 0 and not name:
                        candidate = lines[i-1]
                        if not any(skip in candidate.upper() for skip in ["GUEST NAME", "UMANG", "UTSAV", "OTP", "DALMIA", "BHARAT"]):
                            name = candidate
                m_col = re.search(r"Collect Your Gift from\s*(.*)", line, re.I)
                if m_col:
                    raw_c = m_col.group(1).strip()
                    counter = re.sub(r"^(counter\s*[-:]?\s*)", "", raw_c, flags=re.I).strip()

            if not name:
                for i, line in enumerate(lines):
                    if "GUEST NAME" in line.upper() and i + 1 < len(lines):
                        name = lines[i+1]
                        break

            if otp and cat:
                clean_c = re.sub(r"^(counter\s*[-:]?\s*)", "", counter, flags=re.I).strip()
                clean_c = re.sub(r"^-\s*", "", clean_c).strip()
                if not clean_c or clean_c.upper() in ["A", "B", "C", "D", "E", "F", "G", "H", "A-D"]:
                    counter = "A-D" if cat in "ABCD" else f"- {cat}"
                return {
                    "otp": otp,
                    "name": name or "Guest",
                    "category": cat,
                    "location": loc or "Event",
                    "counter": counter,
                    "style": "english"
                }
    except Exception:
        pass

    # 3. Targeted cropped extraction for legacy scanned/image-only PDFs (Fast & Thread-Safe)
    pix = page.get_pixmap(dpi=110)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    h, w = img.shape[:2]

    # QR Code fast cropped decoding (~10ms)
    otp = ""
    qr_det = get_qr_detector_instance()
    if qr_det:
        try:
            qr_crop = img[int(h*0.25):int(h*0.60), int(w*0.70):w]
            val, _, _ = qr_det.detectAndDecode(qr_crop)
            if val:
                otp = val.strip()
            else:
                val, _, _ = qr_det.detectAndDecode(img)
                otp = (val or "").strip()
        except Exception:
            pass

    # OCR: target header (Location) and guest box (Name, Category, Counter)
    ocr = get_ocr_instance()
    lines = []
    header_lines = []
    if ocr:
        try:
            top_crop = img[0:int(h*0.26), 0:w]
            guest_crop = img[int(h*0.54):int(h*0.87), 0:int(w*0.55)]
            with _ocr_lock:
                top_res, _ = ocr(top_crop)
                header_lines = [item[1].strip() for item in (top_res or [])]
                res, _ = ocr(guest_crop)
                lines.extend([item[1].strip() for item in (res or [])])
        except Exception as e:
            print("OCR extraction error:", e)

    cat = ""
    loc = ""
    name = ""
    counter = ""

    # Extract location from header OCR
    ignore_loc = {"DALMIA", "BHARAT", "CEMENT", "UMANG", "UTSAV", "COUPON", "CARD", "DEALER", "MEET", "ANNUAL", "GIFT", "COUNTER", "WELCOME", "VIP"}
    for hl in header_lines:
        t = hl.strip()
        if re.search(r"OTP\s*[:\s]?\s*\d+", t, re.I):
            continue
        words = re.findall(r"[a-zA-Z]+", t)
        cand = [w for w in words if w.upper() not in ignore_loc]
        if cand:
            loc = " ".join(cand).title()
            break

    for i, line in enumerate(lines):
        # Category
        m_cat = re.search(r"Gift Category\s*[:\s]\s*([A-Za-z0-9]+)", line, re.I)
        if m_cat:
            cat = m_cat.group(1).upper()
            if i > 0 and not name:
                candidate = lines[i-1]
                if not any(skip in candidate.upper() for skip in ["GUEST NAME", "UMANG", "UTSAV", "OTP", "DALMIA", "BHARAT", "CEMENT"]):
                    name = candidate

        # Counter
        m_col = re.search(r"Collect Your Gift from\s*(.*)", line, re.I)
        if m_col:
            raw_c = m_col.group(1).strip()
            counter = re.sub(r"^(counter\s*[-:]?\s*)", "", raw_c, flags=re.I).strip()

        # OTP fallback
        if not otp:
            m_otp = re.search(r"OTP\s*[:\s]\s*([A-Za-z0-9]+)", line, re.I)
            if m_otp:
                otp = m_otp.group(1)

    if not name:
        for i, line in enumerate(lines):
            if "GUEST NAME" in line.upper() and i + 1 < len(lines):
                cand = lines[i+1]
                if not any(k in cand.upper() for k in ["GIFT CATEGORY", "COLLECT", "UMANG", "DALMIA"]):
                    name = cand
                    break

    cat = cat or "A"
    clean_c = re.sub(r"^(counter\s*[-:]?\s*)", "", counter, flags=re.I).strip()
    clean_c = re.sub(r"^-\s*", "", clean_c).strip()
    if not clean_c or clean_c.upper() in ["A", "B", "C", "D", "E", "F", "G", "H", "A-D"]:
        counter = "A-D" if cat in "ABCD" else f"- {cat}"
    else:
        counter = clean_c

    is_hindi = any("उमंग" in l or "उपहार" in l or "उत्सव" in l for l in lines + header_lines)
    style = "hindi" if is_hindi else "english"

    return {
        "otp": otp or "00000",
        "name": name or "Guest",
        "category": cat,
        "location": loc or "Event",
        "counter": counter,
        "style": style
    }

@app.route("/api/load_cards_from_pdf", methods=["POST"])
def load_cards_from_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400
    file = request.files["file"]
    try:
        pdf_bytes = file.read()
        if not pdf_bytes:
            return jsonify({"error": "Uploaded file is empty"}), 400
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        # Inferred location from filename
        inferred_loc = ""
        orig_fn = file.filename or ""
        clean_fn = re.sub(r"\.pdf$", "", orig_fn, flags=re.I)
        clean_fn = re.sub(r"\s*(Soft\s*copy|\(Edited\)|\(Corrected\)).*", "", clean_fn, flags=re.I).strip()
        if clean_fn and clean_fn.lower() not in ["cards", "document", "download", "event", "file", "coupon"]:
            inferred_loc = clean_fn.title()

        subj = doc.metadata.get("subject", "")
        if subj and subj.startswith("UmangCouponData:"):
            cards = json.loads(subj[len("UmangCouponData:"):])
            for c in cards:
                cat = (c.get("category") or "A").strip().upper()
                c_cnt = c.get("counter", "")
                clean_c = re.sub(r"^(counter\s*[-:]?\s*)", "", str(c_cnt), flags=re.I).strip()
                clean_c = re.sub(r"^-\s*", "", clean_c).strip()
                if not clean_c or clean_c.upper() in ["A", "B", "C", "D", "E", "F", "G", "H", "A-D"]:
                    c["counter"] = "A-D" if cat in "ABCD" else f"- {cat}"
                if (not c.get("location") or c.get("location") == "Event") and inferred_loc:
                    c["location"] = inferred_loc
            return jsonify({
                "success": True,
                "type": "exact_cards",
                "cards": cards,
                "total": len(cards),
                "filename": orig_fn
            })
        
        # Fast, stable sequential extraction (avoids CPU thread contention & deadlocks)
        num_pages = len(doc)
        cards = [parse_card_from_pdf_page(doc[i]) for i in range(num_pages)]

        found_loc = next((c["location"] for c in cards if c.get("location") and c["location"] != "Event"), "")
        target_loc = found_loc or inferred_loc
        if target_loc:
            for c in cards:
                if not c.get("location") or c["location"] == "Event":
                    c["location"] = target_loc

        return jsonify({
            "success": True,
            "type": "extracted_cards",
            "cards": cards,
            "total": len(cards),
            "filename": orig_fn
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/replace_pdf_page", methods=["POST"])
def replace_pdf_page():
    if "file" not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400
    file = request.files["file"]
    try:
        page_index = int(request.form.get("page_index", 0))
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "A").strip().upper()
        otp = request.form.get("otp", "").strip()
        location = request.form.get("location", "").strip()
        counter = request.form.get("counter", "").strip() or category
        style = request.form.get("style", "english").strip().lower()

        card = {
            "name": name,
            "category": category,
            "otp": otp,
            "location": location,
            "counter": counter,
            "style": style
        }

        new_page_bytes = make_cards.card_to_pdf_bytes(card)
        new_doc = pymupdf.open(stream=new_page_bytes, filetype="pdf")

        orig_bytes = file.read()
        doc = pymupdf.open(stream=orig_bytes, filetype="pdf")

        if page_index < 0 or page_index >= len(doc):
            return jsonify({"error": f"Invalid page index {page_index}. Document has {len(doc)} pages."}), 400

        doc.delete_page(page_index)
        doc.insert_pdf(new_doc, from_page=0, to_page=0, start_at=page_index)

        meta = doc.metadata
        subj = meta.get("subject", "")
        if subj and subj.startswith("UmangCouponData:"):
            try:
                cards_list = json.loads(subj[len("UmangCouponData:"):])
                if page_index < len(cards_list):
                    cards_list[page_index] = card
                    meta["subject"] = "UmangCouponData:" + json.dumps(cards_list)
                    doc.set_metadata(meta)
            except Exception:
                pass

        out_pdf = doc.tobytes(deflate=True)
        fname = f"{location} Soft copy (Page {page_index + 1} Replaced).pdf"
        return send_file(
            io.BytesIO(out_pdf),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=fname
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/sample_csv")
def sample_csv():
    sample_path = os.path.join(HERE, "sample_guests.csv")
    return send_file(sample_path, mimetype="text/csv", as_attachment=True, download_name="sample_guests.csv")

@app.route("/api/sample_excel")
def sample_excel():
    sample_path = os.path.join(HERE, "sample_guests.xlsx")
    return send_file(sample_path, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="sample_guests.xlsx")

@app.route("/api/preflight", methods=["POST"])
def preflight():
    files = request.files.getlist("file")
    if not files:
        if "file" in request.files:
            files = [request.files["file"]]
        else:
            return jsonify({"error": "No file uploaded"}), 400

    all_valid = []
    all_errors = []
    cat_counts = {}
    file_summaries = []
    loc_counts = OrderedDict()

    try:
        is_multi = (len(files) > 1)
        for idx, f in enumerate(files):
            fname = f.filename or "file.csv"
            file_bytes = io.BytesIO(f.read())
            fsize = file_bytes.getbuffer().nbytes
            inferred_loc = make_cards.extract_location_from_filename(fname)
            valid, errors, c_counts = make_cards.preflight_validate_roster(file_bytes, fname, default_location=inferred_loc)

            for cd in valid:
                if (not cd.get("location") or cd.get("location") == "Event") and inferred_loc:
                    cd["location"] = inferred_loc
                loc = cd.get("location", "Event").strip()
                loc_counts[loc] = loc_counts.get(loc, 0) + 1
            all_valid.extend(valid)

            if is_multi:
                all_errors.extend([f"[{fname}] {err}" for err in errors])
            else:
                all_errors.extend(errors)

            for cat, cnt in c_counts.items():
                cat_counts[cat] = cat_counts.get(cat, 0) + cnt

            # File-specific locations
            f_locs = list(OrderedDict.fromkeys(cd.get("location", "").strip() for cd in valid if cd.get("location", "").strip()))
            file_display_loc = ", ".join(f_locs) if f_locs else (inferred_loc or "Event")

            file_summaries.append({
                "file_index": idx,
                "filename": fname,
                "filesize_kb": round(fsize / 1024, 1),
                "location": file_display_loc,
                "valid": len(valid),
                "invalid": len(errors),
                "total": len(valid) + len(errors),
                "categories": c_counts
            })

        # Sort category counts A to H
        sorted_counts = OrderedDict()
        for c in ["A","B","C","D","E","F","G","H"]:
            if c in cat_counts:
                sorted_counts[c] = cat_counts[c]
        for c, cnt in cat_counts.items():
            if c not in sorted_counts:
                sorted_counts[c] = cnt

        unique_locs = list(loc_counts.keys())

        return jsonify({
            "total": len(all_valid) + len(all_errors),
            "valid": len(all_valid),
            "invalid": len(all_errors),
            "file_count": len(files),
            "files": file_summaries,
            "locations": unique_locs,
            "location_counts": loc_counts,
            "location_count": len(unique_locs),
            "categories": sorted_counts,
            "errors": all_errors[:50],
            "total_errors": len(all_errors)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/start_batch", methods=["POST"])
def start_batch():
    files = request.files.getlist("file")
    if not files:
        if "file" in request.files:
            files = [request.files["file"]]
        else:
            return jsonify({"error": "No file uploaded"}), 400

    mode = request.form.get("mode", "merged")
    pdf_size_opt = request.form.get("pdf_size_opt", "compact").lower()
    batch_style = request.form.get("style", "english").lower().strip()

    try:
        all_valid_cards = []
        for f in files:
            fname = f.filename or "file.csv"
            file_bytes = io.BytesIO(f.read())
            inferred_loc = make_cards.extract_location_from_filename(fname)
            valid_cards, _, _ = make_cards.preflight_validate_roster(file_bytes, fname, default_location=inferred_loc)
            for cd in valid_cards:
                if (not cd.get("location") or cd.get("location") == "Event") and inferred_loc:
                    cd["location"] = inferred_loc
            all_valid_cards.extend(valid_cards)

        if not all_valid_cards:
            return jsonify({"error": "Uploaded file(s) contain no valid attendee records"}), 400

        # Enforce ZIP package mode when multiple files or multiple locations exist
        unique_locs = list(OrderedDict.fromkeys(c.get("location", "").strip() for c in all_valid_cards if c.get("location", "").strip()))
        if len(files) > 1 or len(unique_locs) > 1:
            mode = "zip"

        # Apply batch style strictly (hindi or english)
        target_style = "hindi" if batch_style == "hindi" else "english"
        for cd in all_valid_cards:
            cd["style"] = target_style

        # STRICT SEQUENCE SORTING: A -> B -> C -> D -> E -> F -> G -> H!
        sorted_cards = make_cards.sort_cards_sequence(all_valid_cards)

        upload_filename = files[0].filename if len(files) == 1 else f"{len(files)}_locations.xlsx"

        job_id = uuid.uuid4().hex
        JOBS[job_id] = {
            "status": "processing",
            "cancel_requested": False,
            "total": len(sorted_cards),
            "current": 0,
            "percent": 0.0,
            "current_card": "Initializing...",
            "category": sorted_cards[0]["category"] if sorted_cards else "",
            "speed": 0.0,
            "elapsed": 0.0,
            "eta": 0.0,
            "file_size_mb": 0.0,
            "filename": "",
            "file_path": "",
            "cards": sorted_cards,
            "mode": mode,
            "upload_filename": upload_filename,
            "pdf_size_opt": pdf_size_opt,
            "batch_style": batch_style,
            "can_resume": False,
            "error": None
        }

        # Start worker thread with upload filename, pdf_size_opt, and batch_style
        t = threading.Thread(target=process_batch_worker, args=(job_id, sorted_cards, mode, upload_filename, pdf_size_opt, 0, batch_style), daemon=True)
        t.start()

        return jsonify({
            "job_id": job_id,
            "total": len(sorted_cards)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/batch_cancel/<job_id>", methods=["POST"])
def batch_cancel(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    job["cancel_requested"] = True
    return jsonify({"success": True})

@app.route("/api/batch_resume/<job_id>", methods=["POST"])
def batch_resume(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job.get("status") != "stopped" or not job.get("can_resume"):
        return jsonify({"error": "This batch cannot be resumed"}), 400

    start_index = job.get("current", 0)
    cards = job.get("cards", [])
    mode = job.get("mode", "single")
    upload_filename = job.get("upload_filename", "")
    pdf_size_opt = job.get("pdf_size_opt", "compact")
    batch_style = job.get("batch_style", "")

    job["status"] = "processing"
    job["cancel_requested"] = False

    t = threading.Thread(
        target=process_batch_worker,
        args=(job_id, cards, mode, upload_filename, pdf_size_opt, start_index, batch_style),
        daemon=True
    )
    t.start()
    return jsonify({"success": True, "resumed_from": start_index})

@app.route("/api/batch_progress/<job_id>")
def batch_progress(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job.get("status"),
        "total": job.get("total", 0),
        "current": job.get("current", 0),
        "percent": job.get("percent", 0.0),
        "current_card": job.get("current_card", ""),
        "category": job.get("category", ""),
        "speed": job.get("speed", 0.0),
        "elapsed": job.get("elapsed", 0.0),
        "eta": job.get("eta", 0.0),
        "file_size_mb": job.get("file_size_mb", 0.0),
        "filename": job.get("filename", ""),
        "can_resume": job.get("can_resume", False),
        "error": job.get("error")
    })

@app.route("/api/batch_download/<job_id>")
def batch_download(job_id):
    job = JOBS.get(job_id)
    if not job or job.get("status") not in ["completed", "stopped"]:
        return jsonify({"error": "Job output not available"}), 404
    
    file_path = job.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Output file not found"}), 404

    mime = "application/zip" if file_path.endswith(".zip") else "application/pdf"
    return send_file(
        file_path,
        mimetype=mime,
        as_attachment=True,
        download_name=job.get("filename", "coupons.pdf")
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Umang Utsav Coupon Studio running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
