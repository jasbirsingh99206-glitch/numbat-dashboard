#!/usr/bin/env python3
"""
Numbat Dashboard Server
Run: python3 numbat_dashboard.py
Then open: http://localhost:7474
"""

import os
import time
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

RECORDS_FILE = Path.home() / ".numbat" / "records.ndjson"
PORT = int(os.environ.get("NUMBAT_DASH_PORT", "7474"))


def list_record_files():
    """Live file first, then archives newest → oldest."""
    d = RECORDS_FILE.parent
    if not d.exists():
        return []
    live = []
    archives = []
    for p in d.glob("records.ndjson*"):
        if p.name.endswith(".gz"):
            continue
        (live if p.name == "records.ndjson" else archives).append(p.name)
    archives.sort(reverse=True)
    return live + archives

HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Numbat — Agent Monitor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── LIGHT THEME ── */
[data-theme="light"] {
  --bg:          #f7f8fb;
  --surface:     #ffffff;
  --surface2:    #f3f5f9;
  --surface3:    #e9edf4;
  --border:      #e2e6ee;
  --border2:     #c9d0dc;
  --text:        #0f1419;
  --text2:       #2d3540;
  --muted:       #6b7385;
  --amber:       #c2680a;
  --amber-bg:    #fff3dc;
  --amber-dim:   #7a4a08;
  --red:         #c41e3a;
  --red-bg:      #ffe8ec;
  --green:       #0f8a3d;
  --green-bg:    #e3f7e8;
  --blue:        #1d4ed8;
  --blue-bg:     #e3edff;
  --purple:      #6b21a8;
  --purple-bg:   #f1e6fb;
  --orange:      #d24e0a;
  --cyan:        #0e7490;
  --shadow:      0 1px 3px rgba(15,20,25,0.06), 0 1px 2px rgba(15,20,25,0.04);
  --shadow-md:   0 4px 12px rgba(15,20,25,0.08), 0 2px 4px rgba(15,20,25,0.04);
}

/* ── DARK THEME — refined system palette ── */
[data-theme="dark"] {
  --bg:          #2C2C2A;
  --surface:     #363633;
  --surface2:    #404040;
  --surface3:    #4a4a47;
  --border:      #4a4a47;
  --border2:     #606060;
  --text:        #F0EDE6;
  --text2:       #D8D4CB;
  --muted:       #a8a59c;
  --amber:       #E5A876;
  --amber-bg:    rgba(212,151,90,0.18);
  --amber-dim:   #8a5e30;
  --red:         #ec8a8a;
  --red-bg:      rgba(224,120,120,0.14);
  --green:       #8FC565;
  --green-bg:    rgba(126,181,90,0.16);
  --blue:        #9bc3df;
  --blue-bg:     rgba(138,180,212,0.14);
  --purple:      #c89ce8;
  --purple-bg:   rgba(200,156,232,0.16);
  --orange:      #E5A876;
  --cyan:        #7ac8b3;
  --shadow:      0 1px 3px rgba(0,0,0,0.5);
  --shadow-md:   0 4px 12px rgba(0,0,0,0.55), 0 2px 4px rgba(0,0,0,0.4);
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', sans-serif;
  font-size: 15px;
  line-height: 1.35;
  height: 100vh;
  display: grid;
  grid-template-rows: 56px 1fr;
  grid-template-columns: 240px 1fr 320px;py
  grid-template-areas:
    "header header header"
    "sidebar feed alerts";
  overflow: hidden;
  transition: background 0.2s, color 0.2s, grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── HEADER ── */
header {
  grid-area: header;
  background: var(--surface);
  border-bottom: 1px solid var(--border);py
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 14px;
  box-shadow: var(--shadow);
  z-index: 10;
}

.logo {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  font-size: 15px;
  color: var(--amber);
  display: flex;
  align-items: center;
  gap: 9px;
  letter-spacing: -0.3px;
}

.logo-box {
  width: 28px; height: 28px;
  background: linear-gradient(135deg, var(--amber), var(--orange));
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(217,119,6,0.35);
}

.side-btn {
  width: 34px; height: 34px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface2);
  color: var(--text2);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.side-btn:hover { background: var(--amber-bg); border-color: var(--amber); color: var(--amber); }

body.sidebar-collapsed {
  grid-template-columns: 0px 1fr 320px;
}
body.sidebar-collapsed aside {
  opacity: 0;
  pointer-events: none;
  visibility: hidden;
}

body.right-collapsed {
  grid-template-columns: 240px 1fr 44px;
}
body.right-collapsed .alerts-panel {
  opacity: 0;
  pointer-events: none;
  visibility: hidden;
}
body.right-collapsed .right-rail {
  opacity: 1;
  pointer-events: auto;
  visibility: visible;
  transition: opacity 0.2s ease, visibility 0s;
}
body.sidebar-collapsed.right-collapsed { grid-template-columns: 0px 1fr 44px; }

/* hover-expand */
body.sidebar-collapsed.hover-left { grid-template-columns: 240px 1fr 320px; }
body.sidebar-collapsed.right-collapsed.hover-left { grid-template-columns: 240px 1fr 44px; }
body.sidebar-collapsed.hover-left aside {
  opacity: 1;
  pointer-events: auto;
  visibility: visible;
  transition: opacity 0.2s ease, visibility 0s;
}

body.right-collapsed.hover-right { grid-template-columns: 240px 1fr 320px; }
body.sidebar-collapsed.right-collapsed.hover-right { grid-template-columns: 0px 1fr 320px; }
body.right-collapsed.hover-right .alerts-panel {
  opacity: 1;
  pointer-events: auto;
  visibility: visible;
  transition: opacity 0.2s ease, visibility 0s;
}
body.right-collapsed.hover-right .right-rail {
  opacity: 0;
  pointer-events: none;
  visibility: hidden;
}

.hover-strip {
  position: fixed;
  top: 56px;
  bottom: 0;
  width: 8px;
  z-index: 6;
  cursor: pointer;
}
.hover-strip.left { left: 0; }
.hover-strip.right { right: 0; }
body:not(.sidebar-collapsed) .hover-strip.left,
body.hover-left .hover-strip.left { display: none; }
body:not(.right-collapsed) .hover-strip.right,
body.hover-right .hover-strip.right { display: none; }
.hover-strip.left:hover { box-shadow: inset 2px 0 0 var(--amber); }
.hover-strip.right:hover { box-shadow: inset -2px 0 0 var(--amber); }

.pulse-row {
  display: flex; align-items: center; gap: 7px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text2);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 5px 12px;
}


.dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--muted);
  flex-shrink: 0;
  transition: background 0.3s, box-shadow 0.3s;
}
.dot.live  { background: var(--green); box-shadow: 0 0 0 3px var(--green-bg); animation: pulse 2s ease-in-out infinite; }
.dot.error { background: var(--red); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

.file-drop {
  position: relative;
  flex-shrink: 0;
  max-width: 320px;
  padding-bottom: 6px;
  margin-bottom: -6px;
}
.file-select {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 5px 10px 5px 14px;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  color: var(--text2);
  width: 100%;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.file-select:hover { border-color: var(--amber); }
.file-select:focus-visible {
  outline: none;
  border-color: var(--amber);
  box-shadow: 0 0 0 3px var(--amber-bg);
}
.file-current {
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}
.file-chevron {
  flex-shrink: 0;
  color: var(--muted);
  transition: color 0.15s, transform 0.15s;
}
.file-drop:hover .file-chevron,
.file-drop.open .file-chevron {
  color: var(--amber);
  transform: rotate(180deg);
}
.file-menu {
  position: absolute;
  top: calc(100% - 2px);
  left: 0;
  min-width: 100%;
  max-width: 340px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-md);
  padding: 4px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px);
  transition: opacity 0.15s, transform 0.15s, visibility 0.15s;
  z-index: 100;
}
.file-drop:hover .file-menu,
.file-drop.open .file-menu {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}
.file-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text2);
  background: transparent;
  border: none;
  border-radius: 7px;
  padding: 7px 10px;
  cursor: pointer;
  white-space: nowrap;
}
.file-menu-item:hover { background: var(--amber-bg); color: var(--amber); }
.file-menu-item.active { color: var(--amber); font-weight: 600; }
.file-menu-item .file-check {
  visibility: hidden;
  color: var(--amber);
  font-size: 9px;
}
.file-menu-item.active .file-check { visibility: visible; }

.header-right { margin-left: auto; display: flex; align-items: center; gap: 6px; }

.stat-pill {
  display: flex; align-items: center; gap: 7px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 5px 12px;
  cursor: default;
}
.stat-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 16px;
  font-weight: 600;
  line-height: 1;
}
.stat-label { font-size: 11px; color: var(--muted); line-height: 1; }
.stat-divider { width: 1px; height: 20px; background: var(--border); }

.theme-btn {
  width: 34px; height: 34px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface2);
  color: var(--text2);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  flex-shrink: 0;
}
.theme-btn:hover { background: var(--amber-bg); border-color: var(--amber); color: var(--amber); }

/* ── SIDEBAR ── */
aside {
  grid-area: sidebar;
  background: var(--surface);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: opacity 0.2s ease, visibility 0s linear 0.2s;
}

.sb-spacer { flex: 1; }

.sb-section { padding: 14px 0 4px; }

.sb-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--muted);
  padding: 0 14px 6px;
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
}
.sb-label:hover { color: var(--text2); }

.sb-caret {
  font-size: 9px;
  transition: transform 0.2s;
  color: var(--muted);
  display: inline-block;
}
.sb-section.collapsed .sb-caret { transform: rotate(-90deg); }
.sb-section.collapsed .sb-collapse-body { display: none; }

.filter-btn {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 6px 14px;
  background: none; border: none;
  color: var(--text2);
  cursor: pointer;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  text-align: left;
  border-radius: 0;
  transition: background 0.12s, color 0.12s;
  gap: 6px;
}
.filter-btn:hover { background: var(--surface2); color: var(--text); }
.filter-btn.active {
  background: var(--amber-bg);
  color: var(--amber);
  font-weight: 500;
  box-shadow: inset 3px 0 0 var(--amber);
}

.filter-left { display: flex; align-items: center; gap: 8px; }

.fdot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px transparent;
  transition: box-shadow 0.15s;
}
.filter-btn:hover .fdot { box-shadow: 0 0 0 2px var(--surface3); }

.badge {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  background: var(--surface3);
  color: var(--muted);
  padding: 1px 7px;
  border-radius: 10px;
  min-width: 22px;
  text-align: center;
  border: 1px solid var(--border);
}
.filter-btn.active .badge {
  background: rgba(255,255,255,0.15);
  color: var(--amber);
  border-color: transparent;
}

.sb-divider { height: 1px; background: var(--border); margin: 8px 14px; }

.meta-block {
  padding: 8px 14px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.7;
  font-family: 'JetBrains Mono', monospace;
}
.meta-block strong { color: var(--text); font-weight: 500; }

.sb-actions { padding: 8px 10px 14px; display: flex; flex-direction: column; gap: 4px; }

.action-btn {
  width: 100%; padding: 7px 10px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text2);
  font-size: 12px;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  text-align: left;
  display: flex; align-items: center; gap: 7px;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}
.action-btn:hover { border-color: var(--amber); color: var(--amber); background: var(--amber-bg); }

/* ── MAIN FEED ── */
main {
  grid-area: feed;
  display: flex; flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}

.feed-header {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
  background: var(--surface);
  flex-shrink: 0;
  box-shadow: var(--shadow);
}

.feed-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  display: flex; align-items: center; gap: 7px;
}

.feed-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--border2);
  transition: background 0.3s, box-shadow 0.3s;
}

.autoscroll-row {
  margin-left: auto;
  display: flex; align-items: center; gap: 7px;
  font-size: 12px; color: var(--muted);
  cursor: pointer; user-select: none;
}

.tog {
  width: 30px; height: 16px;
  background: var(--border2);
  border-radius: 10px;
  position: relative;
  transition: background 0.2s;
}
.tog.on { background: var(--amber); }
.tog::after {
  content: '';
  position: absolute;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: #fff;
  top: 2px; left: 2px;
  transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.25);
}
.tog.on::after { transform: translateX(14px); }

.feed-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0 28px;
}

/* Table-style rows */
.event-row {
  display: grid;
  grid-template-columns: 72px 160px 96px 1fr;
  column-gap: 10px;
  align-items: start;
  padding: 4px 16px;
  border-bottom: 1px solid transparent;
  cursor: default;
  transition: background 0.1s;
  animation: slideIn 0.15s ease;
}
@keyframes slideIn { from { opacity:0; transform:translateY(-2px); } to { opacity:1; transform:translateY(0); } }
.event-row:hover { background: var(--surface2); border-bottom-color: var(--border); }
.event-row.is-finding { background: var(--red-bg); }
.event-row.is-finding:hover { background: color-mix(in srgb, var(--red-bg) 80%, var(--surface2)); }

.col-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--muted);
  padding-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: clip;
}

.col-type {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  display: flex; align-items: center; gap: 5px;
  padding-top: 1px;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.type-chip {
  display: inline-block;
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 3px;
  font-weight: 600;
  letter-spacing: 0.2px;
  border: 1px solid transparent;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.col-actor {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding-top: 1px;
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.col-content {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text);
  word-break: break-all;
  line-height: 1.35;
  min-width: 0;
}

.empty-feed {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 100%;
  color: var(--text2);
  font-size: 12px;
  gap: 10px;
}
.empty-icon { font-size: 36px; opacity: 0.4; }
.empty-sub { font-size: 11px; color: var(--muted); }

/* ── ALERTS PANEL ── */
.alerts-panel {
  grid-area: alerts;
  background: var(--surface);
  border-left: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
  transition: opacity 0.2s ease, visibility 0s linear 0.2s;
}

.right-rail {
  grid-area: alerts;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  background: var(--surface);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  min-width: 0;
  opacity: 0;
  pointer-events: none;
  visibility: hidden;
  transition: opacity 0.2s ease, visibility 0s linear 0.2s;
}
.rail-btn {
  width: 32px; height: 32px;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  position: relative;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--text2);
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.rail-btn:hover { background: var(--amber-bg); border-color: var(--amber); color: var(--amber); }
.rail-spacer { flex: 1; }
.rail-badge {
  position: absolute;
  top: -3px; right: -3px;
  min-width: 15px; height: 15px;
  padding: 0 4px;
  border-radius: 8px;
  background: var(--red);
  color: #fff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-weight: 700;
  line-height: 15px;
  text-align: center;
}
.rail-badge.purple { background: var(--purple); }

.panel-header {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
  background: var(--surface);
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  display: flex; align-items: center; gap: 6px;
  background: transparent;
  border: none;
  padding: 0;
  font-family: inherit;
  cursor: pointer;
  transition: color 0.15s;
}
.panel-title:hover { color: var(--amber); }
.collapse-chevron {
  font-size: 10px;
  color: var(--muted);
  transition: color 0.15s, transform 0.15s;
}
.panel-title:hover .collapse-chevron { color: var(--amber); }

.sev-pill {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid;
  font-weight: 600;
}
.sev-pill.red    { background: var(--red-bg);    color: var(--red);    border-color: color-mix(in srgb, var(--red) 30%, transparent); }
.sev-pill.amber  { background: var(--amber-bg);  color: var(--amber);  border-color: color-mix(in srgb, var(--amber) 30%, transparent); }
.sev-pill.blue   { background: var(--blue-bg);   color: var(--blue);   border-color: color-mix(in srgb, var(--blue) 30%, transparent); }

.alerts-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 8px 28px;
  display: flex; flex-direction: column; gap: 6px;
}

.no-findings {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 28px 16px;
  color: var(--text2);
  font-size: 11px;
  text-align: center;
  gap: 8px;
}
.no-findings-icon { font-size: 28px; opacity: 0.5; }

.finding-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  border-left: 3px solid var(--red);
  animation: slideIn 0.2s ease;
  box-shadow: var(--shadow);
}
.finding-card.high   { border-left-color: var(--red);    background: var(--red-bg); }
.finding-card.medium { border-left-color: var(--amber);  background: var(--amber-bg); }
.finding-card.low    { border-left-color: var(--blue);   background: var(--blue-bg); }

.finding-top {
  display: flex; align-items: center; gap: 6px; margin-bottom: 5px;
}

.finding-sev {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  padding: 2px 6px;
  border-radius: 3px;
  color: #fff;
}
.finding-sev.high   { background: var(--red);   }
.finding-sev.medium { background: var(--amber); color: #1a1208; }
.finding-sev.low    { background: var(--blue);  }

.finding-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.35;
  margin-bottom: 5px;
}

.finding-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text2);
  line-height: 1.6;
}
.finding-meta b { color: var(--text); font-weight: 500; }

.finding-cmd {
  margin-top: 6px;
  padding: 5px 8px;
  background: var(--surface3);
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--orange);
  word-break: break-all;
  line-height: 1.4;
  border: 1px solid var(--border);
}

/* ── INDICATORS ── */
.ind-section {
  border-top: 1px solid var(--border);
  flex: 0 0 auto;
  height: 195px;
  min-height: 36px;
  max-height: 60vh;
  display: flex; flex-direction: column;
  background: var(--surface);
  position: relative;
  margin-top: auto;
}
.ind-section.collapsed { height: 36px; }
.ind-section.collapsed .ind-scroll,
.ind-section.collapsed .ind-resize-handle { display: none; }

.ind-resize-handle {
  position: absolute;
  top: 0;
  left: 0; right: 0;
  height: 8px;
  cursor: ns-resize;
  z-index: 5;
}
.ind-resize-handle::before {
  content: '';
  position: absolute;
  top: 3px; left: 50%;
  transform: translateX(-50%);
  width: 36px; height: 2px;
  background: var(--border2);
  border-radius: 2px;
  transition: background 0.15s, width 0.15s;
}
.ind-resize-handle:hover::before,
.ind-resize-handle.dragging::before {
  background: var(--amber);
  width: 56px;
}

.ind-header {
  padding: 9px 14px;
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
  cursor: pointer;
  user-select: none;
}

.ind-toggle {
  font-size: 10px;
  color: var(--muted);
  transition: transform 0.2s, color 0.15s;
  display: inline-block;
  margin-left: 4px;
}
.ind-section.collapsed .ind-toggle { transform: rotate(-90deg); }
.ind-header:hover .ind-toggle { color: var(--amber); }

.ind-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text2);
  display: flex; align-items: center; gap: 6px;
}

.ind-scroll {
  overflow-y: auto;
  padding: 0 8px 28px;
  display: flex; flex-direction: column; gap: 3px;
}

.ind-row {
  display: flex; align-items: flex-start; gap: 6px;
  padding: 4px 8px;
  background: var(--surface2);
  border-radius: 4px;
  border: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
  transition: border-color 0.15s;
}
.ind-row:hover { border-color: var(--border2); }

.ind-type {
  font-size: 9px;
  padding: 2px 5px;
  border-radius: 3px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  flex-shrink: 0;
  margin-top: 1px;
}
.ind-type.domain { background: var(--purple-bg); color: var(--purple); border: 1px solid color-mix(in srgb, var(--purple) 25%, transparent); }
.ind-type.url    { background: var(--blue-bg);   color: var(--blue);   border: 1px solid color-mix(in srgb, var(--blue)   25%, transparent); }

.ind-val {
  font-size: 11px;
  color: var(--text);
  word-break: break-all;
  line-height: 1.35;
}

/* scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }
</style>
</head>
<body>

<header>
  <button class="side-btn" id="side-btn" onclick="toggleSidebar()" title="Toggle sidebar">☰</button>
  <div class="logo">
    <div class="logo-box">🦔</div>
    numbat
  </div>

  <div class="pulse-row">
    <div class="dot" id="dot"></div>
    <span id="conn-lbl">connecting…</span>
  </div>

  <div class="file-drop" id="file-drop">
    <button type="button" class="file-select" id="file-trigger" aria-haspopup="listbox" aria-expanded="false">
      <span class="file-current" id="file-current">records.ndjson</span>
      <svg class="file-chevron" width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
        <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
    <div class="file-menu" id="file-menu" role="listbox"></div>
  </div>

  <div class="header-right">
    <div class="stat-pill">
      <div>
        <div class="stat-val" id="s-events" style="color:var(--text)">0</div>
        <div class="stat-label">Events</div>
      </div>
      <div class="stat-divider"></div>
      <div>
        <div class="stat-val" id="s-cmds" style="color:var(--orange)">0</div>
        <div class="stat-label">Commands</div>
      </div>
      <div class="stat-divider"></div>
      <div>
        <div class="stat-val" id="s-net" style="color:var(--purple)">0</div>
        <div class="stat-label">Network</div>
      </div>
      <div class="stat-divider"></div>
      <div>
        <div class="stat-val" id="s-findings" style="color:var(--red)">0</div>
        <div class="stat-label">Findings</div>
      </div>
    </div>

    <button class="theme-btn" id="theme-btn" onclick="toggleTheme()" title="Toggle light/dark">☀️</button>
  </div>
</header>

<div class="hover-strip left" id="hover-strip-left" title="Open sidebar"></div>
<div class="hover-strip right" id="hover-strip-right" title="Open panel"></div>

<aside id="sidebar">
  <div class="sb-section">
    <div class="sb-label">Filter Events</div>
    <button class="filter-btn active" onclick="setFilter('all',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--muted)"></div>All events</div>
      <span class="badge" id="c-all">0</span>
    </button>
    <button class="filter-btn" onclick="setFilter('session',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--green)"></div>Sessions</div>
      <span class="badge" id="c-session">0</span>
    </button>
    <button class="filter-btn" onclick="setFilter('prompt',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--blue)"></div>Prompts</div>
      <span class="badge" id="c-prompt">0</span>
    </button>
    <button class="filter-btn" onclick="setFilter('command',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--orange)"></div>Commands</div>
      <span class="badge" id="c-command">0</span>
    </button>
    <button class="filter-btn" onclick="setFilter('network',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--purple)"></div>Network</div>
      <span class="badge" id="c-network">0</span>
    </button>
    <button class="filter-btn" onclick="setFilter('file',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--amber)"></div>File access</div>
      <span class="badge" id="c-file">0</span>
    </button>
    <button class="filter-btn" onclick="setFilter('tool',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--muted)"></div>Tool results</div>
      <span class="badge" id="c-tool">0</span>
    </button>
    <button class="filter-btn" onclick="setFilter('message',this)">
      <div class="filter-left"><div class="fdot" style="background:var(--cyan)"></div>Messages</div>
      <span class="badge" id="c-message">0</span>
    </button>
  </div>

  <div class="sb-spacer"></div>

  <div class="sb-divider"></div>

  <div class="sb-section collapsed" id="sb-session">
    <div class="sb-label" onclick="toggleSection('sb-session')">
      <span>Session Info</span>
      <span class="sb-caret">▼</span>
    </div>
    <div class="sb-collapse-body">
      <div class="meta-block" id="meta-block">
        agent&nbsp;&nbsp;&nbsp; <strong id="m-agent">—</strong><br>
        model&nbsp;&nbsp;&nbsp; <strong id="m-model">—</strong><br>
        project&nbsp; <strong id="m-project">—</strong><br>
        session&nbsp; <strong id="m-session">—</strong>
      </div>
    </div>
  </div>

  <div class="sb-divider"></div>

  <div class="sb-section collapsed" id="sb-actions">
    <div class="sb-label" onclick="toggleSection('sb-actions')">
      <span>Actions</span>
      <span class="sb-caret">▼</span>
    </div>
    <div class="sb-collapse-body">
      <div class="sb-actions">
        <button class="action-btn" onclick="clearAll()">⊘ Clear feed</button>
        <button class="action-btn" onclick="exportEvents()">↓ Export NDJSON</button>
      </div>
    </div>
  </div>
</aside>

<main>
  <div class="feed-header">
    <div class="feed-title">
      <div class="feed-dot" id="feed-dot"></div>
      Live Event Feed
    </div>
    <label class="autoscroll-row">
      <div class="tog on" id="scroll-tog" onclick="toggleScroll()"></div>
      Auto-scroll
    </label>
  </div>
  <div class="feed-list" id="feed-list">
    <div class="empty-feed" id="empty-feed">
      <div class="empty-icon">📡</div>
      <div>Waiting for OpenCode activity…</div>
      <div class="empty-sub">Events stream here as you use OpenCode</div>
    </div>
  </div>
</main>

<div class="alerts-panel" id="alerts-panel">
  <div class="panel-header">
    <button class="panel-title" onclick="toggleRightPanel()" title="Collapse to rail">
      ⚠ Findings
      <span class="collapse-chevron">▸</span>
    </button>
    <span class="sev-pill red" id="finding-count">0</span>
  </div>
  <div class="alerts-scroll" id="alerts-scroll">
    <div class="no-findings">
      <div class="no-findings-icon">🛡</div>
      <div>No security findings yet</div>
      <div style="font-size:10px;opacity:0.65;margin-top:2px">Alerts appear when rules trigger</div>
    </div>
  </div>

  <div class="ind-section" id="ind-section">
    <div class="ind-resize-handle" id="ind-resize" title="Drag to resize"></div>
    <div class="ind-header" id="ind-header">
      <div class="ind-title">
        <span>🌐 Network Indicators</span>
        <span class="ind-toggle">▼</span>
      </div>
      <span class="badge" id="ind-count">0</span>
    </div>
    <div class="ind-scroll" id="ind-scroll"></div>
  </div>
</div>

<div class="right-rail" id="right-rail">
  <button class="rail-btn" onclick="toggleRightPanel()" title="Expand panel">❮</button>
  <div class="rail-spacer"></div>
  <button class="rail-btn" onclick="openRightPanel('findings')" title="Findings">
    ⚠<span class="rail-badge" id="rail-fcount">0</span>
  </button>
  <button class="rail-btn" onclick="openRightPanel('network')" title="Network indicators">
    🌐<span class="rail-badge purple" id="rail-icount">0</span>
  </button>
</div>

<script>
const TYPE_COLOR = {
  'session.start':     'var(--green)',
  'session.end':       'var(--green)',
  'prompt.user':       'var(--blue)',
  'message.assistant': 'var(--cyan)',
  'command.exec':      'var(--orange)',
  'command.result':    'var(--orange)',
  'file.read':         'var(--amber)',
  'file.write':        'var(--amber)',
  'network.indicator': 'var(--purple)',
  'tool.result':       'var(--muted)',
  'tool.call':         'var(--muted)',
};

const TYPE_BG = {
  'session.start':     'var(--green-bg)',
  'session.end':       'var(--green-bg)',
  'prompt.user':       'var(--blue-bg)',
  'message.assistant': 'color-mix(in srgb, var(--cyan) 12%, transparent)',
  'command.exec':      'color-mix(in srgb, var(--orange) 14%, transparent)',
  'command.result':    'color-mix(in srgb, var(--orange) 14%, transparent)',
  'file.read':         'var(--amber-bg)',
  'file.write':        'var(--amber-bg)',
  'network.indicator': 'var(--purple-bg)',
  'tool.result':       'var(--surface3)',
};

const ACTOR_COLOR = {
  user:      'var(--blue)',
  assistant: 'var(--green)',
  tool:      'var(--text2)',
  system:    'var(--amber)',
};

let allEvents = [], findings = [], indicators = [];
let autoScroll = true, currentFilter = 'all';
let counts = { all:0, session:0, prompt:0, command:0, network:0, file:0, tool:0, message:0 };
let meta = {};

// ── theme ──
let isDark = false;
applyTheme();

function applyTheme() {
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  document.getElementById('theme-btn').textContent = isDark ? '☀️' : '🌙';
}
function toggleTheme() { isDark = !isDark; applyTheme(); }

// ── sidebar ──
let sideOpen = true;
function isSidebarVisible() {
  return !document.body.classList.contains('sidebar-collapsed') || document.body.classList.contains('hover-left');
}
function toggleSidebar() {
  if (isSidebarVisible()) {
    sideOpen = false;
    document.body.classList.add('sidebar-collapsed');
    document.body.classList.remove('hover-left');
  } else {
    sideOpen = true;
    document.body.classList.remove('sidebar-collapsed', 'hover-left');
  }
}
function setSidebar(open) {
  sideOpen = open;
  document.body.classList.toggle('sidebar-collapsed', !open);
  document.body.classList.remove('hover-left');
}

// ── hover-expand ──
let leftCollapseTimer = null;
document.getElementById('hover-strip-left').addEventListener('mouseenter', () => {
  clearTimeout(leftCollapseTimer);
  if (document.body.classList.contains('sidebar-collapsed')) document.body.classList.add('hover-left');
});
document.getElementById('sidebar').addEventListener('mouseleave', () => {
  leftCollapseTimer = setTimeout(() => document.body.classList.remove('hover-left'), 200);
});

let rightCollapseTimer = null;
let rightHoverTimer = null;
document.getElementById('hover-strip-right').addEventListener('mouseenter', () => {
  clearTimeout(rightCollapseTimer);
  if (document.body.classList.contains('right-collapsed')) document.body.classList.add('hover-right');
});
document.getElementById('right-rail').addEventListener('mouseenter', () => {
  clearTimeout(rightCollapseTimer);
  if (!document.body.classList.contains('right-collapsed')) return;
  rightHoverTimer = setTimeout(() => {
    if (document.body.classList.contains('right-collapsed')) document.body.classList.add('hover-right');
  }, 250);
});
document.getElementById('right-rail').addEventListener('mouseleave', () => {
  clearTimeout(rightHoverTimer);
});
document.getElementById('alerts-panel').addEventListener('mouseleave', () => {
  rightCollapseTimer = setTimeout(() => document.body.classList.remove('hover-right'), 200);
});

// keyboard shortcuts
document.addEventListener('keydown', e => {
  if (!e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === 's') { e.preventDefault(); toggleSidebar(); }
  if (k === 'p') { e.preventDefault(); toggleRightPanel(); }
});

// ── right panel rail ──
let rightOpen = true;
function isRightVisible() {
  return !document.body.classList.contains('right-collapsed') || document.body.classList.contains('hover-right');
}
function toggleRightPanel() {
  if (isRightVisible()) {
    rightOpen = false;
    document.body.classList.add('right-collapsed');
    document.body.classList.remove('hover-right');
  } else {
    rightOpen = true;
    document.body.classList.remove('right-collapsed', 'hover-right');
  }
}
function setRightPanel(open) {
  rightOpen = open;
  document.body.classList.toggle('right-collapsed', !open);
  document.body.classList.remove('hover-right');
}
function openRightPanel(section) {
  if (!rightOpen) setRightPanel(true);
  if (section === 'network') {
    document.getElementById('ind-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } else if (section === 'findings') {
    const s = document.getElementById('alerts-scroll');
    if (s) s.scrollTop = 0;
  }
}
function setRailCounts() {
  document.getElementById('rail-fcount').textContent = findings.length;
  document.getElementById('rail-icount').textContent = indicators.length;
}

// ── helpers ──
function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function trunc(s, n) { return s && s.length > n ? s.slice(0, n) + '…' : (s || ''); }
function fmtTime(ts) {
  if (!ts) return '—';
  try { return new Date(ts).toTimeString().slice(0,8); } catch { return ts.slice(11,19)||'—'; }
}
function getFilterKey(ev) {
  const t = ev.event_type || '';
  if (t.startsWith('session')) return 'session';
  if (t.startsWith('prompt'))  return 'prompt';
  if (t.startsWith('command')) return 'command';
  if (t.startsWith('network')) return 'network';
  if (t.startsWith('file'))    return 'file';
  if (t.startsWith('tool'))    return 'tool';
  if (t.startsWith('message')) return 'message';
  return null;
}

// ── render event row ──
function makeEventRow(ev) {
  const t   = ev.event_type || ev.record_type || '?';
  const col = TYPE_COLOR[t] || 'var(--muted)';
  const bg  = TYPE_BG[t]    || 'var(--surface3)';
  const acol = ACTOR_COLOR[ev.actor] || 'var(--muted)';

  const t2 = ev.event_type || '';
  let content = '';
  if (ev.command)
    content = `<span style="color:var(--orange)">${esc(trunc(ev.command,130))}</span>`;
  else if (ev.url)
    content = `<span style="color:var(--purple)">${esc(trunc(ev.url,100))}</span>`;
  else if (ev.file_path)
    content = `<span style="color:var(--amber)">📄 <b>${esc(trunc(ev.file_path, 140))}</b></span>`;
  else if (ev.content_preview)
    content = `<span style="color:var(--text2)">${esc(trunc(ev.content_preview,110))}</span>`;
  else if (ev.tool_name)
    content = `<span style="color:var(--muted)">tool: <b style="color:var(--amber)">${esc(ev.tool_name)}</b></span>`;
  else if (ev.title)
    content = `<span style="color:var(--red)">⚠ ${esc(ev.title)}</span>`;
  else if (t2.startsWith('session') && ev.session_id)
    content = `<span style="color:var(--muted)">session: <b style="color:var(--text2)">${esc(trunc(ev.session_id, 32))}</b></span>`;
  else if (t2 === 'message.assistant')
    content = `<span style="color:var(--muted);font-style:italic">no content captured</span>`;
  else if (t2 === 'command.result' || t2 === 'tool.result')
    content = `<span style="color:var(--muted);font-style:italic">result returned</span>`;
  else
    content = `<span style="color:var(--muted)">—</span>`;

  const row = document.createElement('div');
  row.className = 'event-row' + (ev.record_type === 'finding' ? ' is-finding' : '');
  row.innerHTML = `
    <div class="col-time">${fmtTime(ev.timestamp)}</div>
    <div class="col-type">
      <span class="type-chip" style="background:${bg};color:${col}">${esc(t)}</span>
    </div>
    <div class="col-actor" style="color:${acol}">${esc(ev.actor||'')}</div>
    <div class="col-content">${content}</div>
  `;
  return row;
}

// ── render finding card ──
function makeFindingCard(ev) {
  const sev = (ev.severity||'medium').toLowerCase();
  const ruleId = ev.rule_id || ev.deny_rule_id || '—';
  const cmdHtml = ev.observed_command
    ? `<div class="finding-cmd">${esc(trunc(ev.observed_command,160))}</div>` : '';

  const card = document.createElement('div');
  card.className = `finding-card ${sev}`;
  card.innerHTML = `
    <div class="finding-top">
      <span class="finding-sev ${sev}">${sev.toUpperCase()}</span>
    </div>
    <div class="finding-title">${esc(ev.title||ruleId)}</div>
    ${cmdHtml}
    <div class="finding-meta">
      rule: <b>${esc(ruleId)}</b><br>
      agent: <b>${esc(ev.source_agent||'—')}</b><br>
      time: <b>${fmtTime(ev.timestamp)}</b>
    </div>
  `;
  return card;
}

// ── render indicator row ──
function makeIndRow(ev) {
  const t = (ev.type||'url').toLowerCase();
  const row = document.createElement('div');
  row.className = 'ind-row';
  row.innerHTML = `
    <span class="ind-type ${t}">${t}</span>
    <span class="ind-val">${esc(trunc(ev.value||ev.url||'',70))}</span>
  `;
  return row;
}

// ── process record ──
function processRecord(ev) {
  if (!ev || !ev.record_type) return;

  if (ev.record_type === 'event') {
    allEvents.push(ev);
    counts.all++;
    const k = getFilterKey(ev);
    if (k) counts[k] = (counts[k]||0) + 1;
    updateMeta(ev);
    updateCounts();
    updateStats();
    appendRow(ev);
  } else if (ev.record_type === 'finding') {
    findings.push(ev);
    allEvents.push(ev);
    counts.all++;
    appendFinding(ev);
    updateStats();
    updateCounts();
  } else if (ev.record_type === 'indicator') {
    if (!indicators.find(i => i.value === ev.value)) {
      indicators.push(ev);
      appendIndicator(ev);
      document.getElementById('ind-count').textContent = indicators.length;
      setRailCounts();
    }
  }
}

function appendRow(ev) {
  const list = document.getElementById('feed-list');
  const empty = document.getElementById('empty-feed');
  if (empty && empty.parentNode) empty.remove();

  const k = getFilterKey(ev);
  if (currentFilter !== 'all' && k !== currentFilter) return;

  list.appendChild(makeEventRow(ev));
  if (autoScroll) list.scrollTop = list.scrollHeight;

  // flash feed dot
  const fd = document.getElementById('feed-dot');
  const col = TYPE_COLOR[ev.event_type] || 'var(--amber)';
  fd.style.background = col;
  fd.style.boxShadow = `0 0 6px ${col}`;
  clearTimeout(fd._t);
  fd._t = setTimeout(() => { fd.style.background = ''; fd.style.boxShadow = ''; }, 500);
}

function appendFinding(ev) {
  const scroll = document.getElementById('alerts-scroll');
  const noFind = scroll.querySelector('.no-findings');
  if (noFind) noFind.remove();
  scroll.insertBefore(makeFindingCard(ev), scroll.firstChild);
  document.getElementById('finding-count').textContent = findings.length;
  setRailCounts();
}

function appendIndicator(ev) {
  document.getElementById('ind-scroll').appendChild(makeIndRow(ev));
}

function updateMeta(ev) {
  if (ev.source_agent) meta.agent   = ev.source_agent;
  if (ev.model)        meta.model   = ev.model;
  if (ev.project_path) meta.project = ev.project_path.replace(/^\/home\/[^/]+/, '~');
  if (ev.session_id)   meta.session = ev.session_id.slice(0, 24) + '…';
  document.getElementById('m-agent').textContent   = meta.agent   || '—';
  document.getElementById('m-model').textContent   = meta.model   || '—';
  document.getElementById('m-project').textContent = meta.project || '—';
  document.getElementById('m-session').textContent = meta.session || '—';
}

function updateCounts() {
  Object.keys(counts).forEach(k => {
    const el = document.getElementById(`c-${k}`);
    if (el) el.textContent = counts[k];
  });
}

function updateStats() {
  document.getElementById('s-events').textContent   = allEvents.filter(e=>e.record_type==='event').length;
  document.getElementById('s-cmds').textContent     = counts.command || 0;
  document.getElementById('s-net').textContent      = counts.network || 0;
  document.getElementById('s-findings').textContent = findings.length;
  document.getElementById('finding-count').textContent = findings.length;
  setRailCounts();
}

function setFilter(key, btn) {
  currentFilter = key;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  rebuildFeed();
}

function rebuildFeed() {
  const list = document.getElementById('feed-list');
  const visible = currentFilter === 'all' ? allEvents : allEvents.filter(e => getFilterKey(e) === currentFilter);
  list.innerHTML = '';
  const frag = document.createDocumentFragment();
  visible.slice(-500).forEach(e => frag.appendChild(makeEventRow(e)));
  list.appendChild(frag);
  if (autoScroll) list.scrollTop = list.scrollHeight;
}

function toggleScroll() {
  autoScroll = !autoScroll;
  document.getElementById('scroll-tog').classList.toggle('on', autoScroll);
}

function clearAll() {
  allEvents = []; findings = []; indicators = [];
  Object.keys(counts).forEach(k => counts[k] = 0);
  document.getElementById('feed-list').innerHTML = '<div class="empty-feed"><div class="empty-icon">📡</div><div>Feed cleared</div></div>';
  document.getElementById('alerts-scroll').innerHTML = '<div class="no-findings"><div class="no-findings-icon">🛡</div><div>No security findings yet</div></div>';
  document.getElementById('ind-scroll').innerHTML = '';
  document.getElementById('ind-count').textContent = 0;
  setRailCounts();
  updateCounts(); updateStats();
}

function exportEvents() {
  const visible = currentFilter === 'all' ? allEvents : allEvents.filter(e => getFilterKey(e) === currentFilter);
  const blob = new Blob([visible.map(e => JSON.stringify(e)).join('\n')], {type:'application/x-ndjson'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `numbat-${Date.now()}.ndjson`;
  a.click();
}

// ── collapsible sidebar sections ──
function toggleSection(id) {
  document.getElementById(id).classList.toggle('collapsed');
}

// ── collapsible + resizable Network Indicators panel ──
(function initIndicatorsPanel() {
  const sec = document.getElementById('ind-section');
  const header = document.getElementById('ind-header');
  const handle = document.getElementById('ind-resize');
  const STORAGE_KEY = 'numbat-ind-height';

  // restore height
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    const h = parseInt(saved, 10);
    if (!isNaN(h) && h >= 36 && h <= window.innerHeight * 0.7) {
      sec.style.height = h + 'px';
    }
  }

  // collapse toggle on header
  header.addEventListener('click', (e) => {
    // ignore if click was on the resize handle area
    sec.classList.toggle('collapsed');
  });

  // resize
  let startY = 0, startH = 0, dragging = false;
  const onMove = (e) => {
    if (!dragging) return;
    const dy = startY - e.clientY;
    let nh = startH + dy;
    nh = Math.max(36, Math.min(window.innerHeight * 0.7, nh));
    sec.style.height = nh + 'px';
  };
  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove('dragging');
    document.body.style.cursor = '';
    localStorage.setItem(STORAGE_KEY, parseInt(sec.style.height, 10));
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
  };

  handle.addEventListener('mousedown', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragging = true;
    startY = e.clientY;
    startH = sec.offsetHeight;
    handle.classList.add('dragging');
    document.body.style.cursor = 'ns-resize';
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  });

  // prevent header collapse when starting drag on handle area
  handle.addEventListener('click', (e) => e.stopPropagation());
})();

// ── file dropdown ──
let es = null;
let currentFile = 'records.ndjson';
const drop = document.getElementById('file-drop');
const trigger = document.getElementById('file-trigger');
const menu = document.getElementById('file-menu');

async function loadFiles() {
  try {
    const res = await fetch('/files');
    const files = await res.json();
    menu.innerHTML = '';
    files.forEach(f => {
      const it = document.createElement('button');
      it.type = 'button';
      it.className = 'file-menu-item';
      it.setAttribute('role', 'option');
      it.innerHTML = `<span class="file-check">✓</span><span class="file-opt-name"></span>`;
      it.querySelector('.file-opt-name').textContent = f;
      it.addEventListener('click', () => switchFile(f));
      menu.appendChild(it);
    });
    if (files.length > 0) switchFile(files[0], true);
  } catch (e) {}
}

function renderFile(name) {
  currentFile = name;
  document.getElementById('file-current').textContent = name;
  document.querySelectorAll('.file-menu-item').forEach(it => {
    it.classList.toggle('active', it.querySelector('.file-opt-name').textContent === name);
  });
}

function setOpen(open) {
  drop.classList.toggle('open', open);
  trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
}

function switchFile(name, silent) {
  if (name === currentFile && !silent) { setOpen(false); return; }
  renderFile(name);
  setOpen(false);
  if (!silent) { clearAll(); if (es) es.close(); connect(name); }
}

trigger.addEventListener('click', () => setOpen(!drop.classList.contains('open')));
document.addEventListener('click', e => { if (!drop.contains(e.target)) setOpen(false); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') setOpen(false); });

// ── SSE ──
function connect(file) {
  const dot  = document.getElementById('dot');
  const lbl  = document.getElementById('conn-lbl');
  es = new EventSource('/stream?file=' + encodeURIComponent(file));

  es.onopen = () => {
    dot.className = 'dot live';
    lbl.textContent = 'live';
  };
  es.addEventListener('record', e => {
    try { processRecord(JSON.parse(e.data)); } catch {}
  });
  es.onerror = () => {
    dot.className = 'dot error';
    lbl.textContent = 'reconnecting…';
  };
}

loadFiles();
connect(currentFile);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def do_GET(self):
        if self.path == '/':
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(HTML.encode())
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif self.path.split('?')[0] == '/files':
            try:
                body = json.dumps(list_record_files()).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif self.path.split('?')[0] == '/stream':
            qs = parse_qs(urlparse(self.path).query)
            name = (qs.get('file') or ['records.ndjson'])[0]
            if not name.startswith('records.ndjson') or '/' in name or '..' in name:
                name = 'records.ndjson'
            fp = RECORDS_FILE.parent / name
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Send existing records first
            if fp.exists():
                try:
                    with open(fp, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    json.loads(line)
                                    self.wfile.write(f"event: record\ndata: {line}\n\n".encode())
                                except json.JSONDecodeError:
                                    pass
                    self.wfile.flush()
                except Exception:
                    pass

            # Tail for new lines
            try:
                with open(fp, 'r') as f:
                    f.seek(0, 2)
                    while True:
                        line = f.readline()
                        if line:
                            line = line.strip()
                            if line:
                                try:
                                    json.loads(line)
                                    self.wfile.write(f"event: record\ndata: {line}\n\n".encode())
                                    self.wfile.flush()
                                except json.JSONDecodeError:
                                    pass
                        else:
                            self.wfile.write(b": heartbeat\n\n")
                            self.wfile.flush()
                            time.sleep(1)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                while not fp.exists():
                    try:
                        self.wfile.write(b": waiting\n\n")
                        self.wfile.flush()
                    except Exception:
                        return
                    time.sleep(2)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    print(f"""
  🦔 Numbat Dashboard
  ───────────────────────────────────
  Watching : {RECORDS_FILE}
  Open     : http://localhost:{PORT}

  Ctrl+C to stop.
""")
    ThreadingHTTPServer(('localhost', PORT), Handler).serve_forever()
