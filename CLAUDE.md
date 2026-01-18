# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AiPlugs is a Windows-based AI plugin orchestration platform that injects AI-powered scripts into web pages based on browsing context. It uses an Electron frontend with a Python backend, featuring a centralized AI engine (SOA architecture) for efficient model sharing across plugins.

## Development Commands

```bash
# Install dependencies
npm install                              # Electron dependencies
pip install -r python/requirements.txt   # Python dependencies (PyTorch, FastAPI, etc.)

# Run the application
npm start                                # Launches Electron app which spawns Python backend
```

## Architecture

### Dual-Process Model
- **Electron (Node.js)**: Main process handles window management, tab management via BrowserView, and IPC
- **Python Backend**: API server (FastAPI/Uvicorn) + optional mitmproxy for packet interception

### Startup Flow
1. Electron loads `config/config.json` and applies security switches
2. Dynamic port allocation (API: 5000-5100, Proxy: 8080-8180)
3. `process-manager.js` spawns `python/main.py` with allocated ports
4. Python launches `api_server.py` subprocess, then `SystemOrchestrator`
5. Initial tab created; script injection begins on navigation events

### Plugin Execution Modes
Plugins define `execution_type` in their `manifest.json`:
- **SOA Mode** (`"none"`): Lightweight plugins call central AI engine via API - no subprocess spawned
- **Legacy Mode** (`"process"`): Independent Python subprocess per plugin (v2.6 compatibility)

### Key Components

**Electron (`electron/`)**:
- `main/index.js` - Entry point, port allocation, IPC handlers, script injection orchestration
- `main/managers/tab-manager.js` - BrowserView-based multi-tab management with isolation
- `main/security-bypass.js` - CSP/CORS bypass for local API communication
- `main/process-manager.js` - Python process lifecycle management

**Python (`python/`)**:
- `main.py` - Entry point, spawns API server, initializes orchestrator
- `core/api_server.py` - FastAPI gateway handling `/v1/match`, `/v1/inference/*` endpoints
- `core/ai_engine.py` - Central PyTorch model hosting with lazy loading
- `core/orchestrator.py` - System lifecycle, proxy control, cleanup
- `core/injector.py` - Injects `window.__AI_API_BASE_URL__` into HTML responses
- `core/matcher.py` - URL pattern matching for plugin activation

### Configuration Files
- `config/config.json` - System settings (ports, AI engine, security policies)
- `config/settings.json` - User preferences, active plugins, plugin modes (local/web)

### Plugin Structure
Each plugin in `plugins/` contains:
- `manifest.json` - Metadata, URL match patterns, execution type, model definitions
- `content.js` - Frontend script injected into matched pages
- `backend.py` (optional) - Python backend for legacy process mode

## Communication Flow

1. TabManager emits `did-navigate` event with URL
2. Electron fetches `/v1/match` from Python API with URL
3. API returns matching plugin scripts
4. Electron injects scripts with `window.__AI_API_BASE_URL__` for backend access
5. Injected scripts call `/v1/inference/{plugin_id}/{function}` for AI operations

## System Modes
- **Native-Only**: Electron hooks only (faster, recommended)
- **Dual Mode**: Enables mitmproxy for HTTP header manipulation when `requires_proxy: true`
