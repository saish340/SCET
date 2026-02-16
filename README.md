# SCET - Smart Copyright Expiry Tag System

## AI-Powered Copyright Status Search

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Live Demo](https://img.shields.io/badge/demo-live-success.svg)](https://scet.vercel.app/)

**Live Demo:** [https://scet.vercel.app/](https://scet.vercel.app/)

---

## 📋 Overview

SCET (Smart Copyright Expiry Tag) is an AI-powered web application that helps you search and verify copyright status of creative works including books, films, music, and artwork.

**Key Capabilities:**
- Search copyright status with AI-powered relevance matching
- Determine copyright ownership and expiry dates
- Get instant analysis with confidence scores
- Filter by jurisdiction (US, EU, UK, CA, AU, JP, IN)
- Real-time similarity matching for accurate results

---

## 🎯 Features

### 🔍 AI-Based Search Engine
- **Text similarity matching** using advanced algorithms (Jaccard similarity)
- **Multi-source data aggregation** from Open Library, Wikipedia, US Copyright Office
- **Relevance filtering** - only shows results above 30% similarity threshold
- **Real-time search** with instant results
- **Quick search sidebar** with popular searches and category filters

### ⚖️ Copyright Status Analysis
- **Automatic status detection** (PROTECTED, PUBLIC_DOMAIN, UNKNOWN)
- **Multi-jurisdiction support** with region-specific copyright rules
- **Publication year analysis** for copyright expiry calculation
- **Confidence scoring** for reliability assessment
- **Detailed metadata** including creator, publication year, source

### 🎨 Modern Dark Theme UI
- **Clean, minimal design** following modern SaaS principles
- **Fully responsive** layout works on desktop, tablet, and mobile
- **Enhanced result cards** with:
  - Color-coded status badges (red/green/gray)
  - Similarity match scores
  - Metadata tags (year, type, source)
  - Hover effects with glow
  - 2px outlined borders
- **Smooth animations** and transitions
- **Professional typography** using Inter font family

### 📊 Smart Copyright Tags
- **Detailed copyright information** including status, expiry, allowed uses
- **Visual indicators** with emojis and color coding
- **Legal jurisdiction context**
- **AI-powered reasoning** and confidence levels
- **Comprehensive metadata display**

---

## 🚀 Technology Stack

**Frontend:**
- HTML5, CSS3 (modern dark theme with gradients)
- Vanilla JavaScript (ES6+)
- Responsive design with CSS Grid and Flexbox
- Inter font family

**Backend:**
- Python 3.9+ with FastAPI framework
- RESTful API architecture
- Real-time web scraping
- Serverless deployment on Vercel

**Data Sources:**
- [Open Library API](https://openlibrary.org/developers/api) - Books and publications
- [Wikipedia API](https://www.mediawiki.org/wiki/API) - General knowledge and films
- US Copyright Office - Copyright records
- Indian Copyright Office - Regional records

---

## 📁 Project Structure

```
SCET/
├── api/
│   └── index.py          # FastAPI backend (Vercel serverless function)
├── css/
│   └── styles.css        # Main stylesheet (dark theme)
├── js/
│   └── app-v3.js         # Frontend JavaScript
├── index.html            # Main HTML file
├── vercel.json           # Vercel deployment configuration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## 🔧 API Endpoints

### Search
```
GET /api/v1/search?q={query}&jurisdiction={jurisdiction}
```
Search for works by title with optional jurisdiction filter.

**Example:**
```bash
curl "https://scet.vercel.app/api/v1/search?q=harry+potter"
```

### Generate Smart Tag
```
GET /api/v1/tag/detailed?title={title}&year={year}&creator={creator}&jurisdiction={jurisdiction}
```
Generate a detailed copyright tag for a specific work.

**Example:**
```bash
curl "https://scet.vercel.app/api/v1/tag/detailed?title=Romeo+and+Juliet&year=1597&jurisdiction=US"
```

### Health Check
```
GET /api/v1/health
```
Check API status.

---

## 🌐 Deployment

The application is deployed on **Vercel** with serverless functions.

**Deployment Configuration (`vercel.json`):**
- API routes are handled by Python serverless functions
- Static assets (HTML, CSS, JS) served from root
- Cache headers configured for optimal performance
- CORS enabled for all origins

**To deploy your own instance:**

1. Fork this repository
2. Import to Vercel
3. Deploy automatically (Vercel auto-detects configuration)

---

## 🎨 UI Features

### Search Results Display
- **Outlined cards** with 2px borders
- **Color-coded badges:**
  - 🔴 PROTECTED (red) - Still under copyright protection
  - 🟢 PUBLIC_DOMAIN (green) - Free to use
  - ⚪ UNKNOWN (gray) - Status unclear
- **Metadata display:**
  - 📅 Publication year
  - 📑 Content type (book, film, music, etc.)
  - 📚 Data source
  - 🎯 Similarity match percentage

### Quick Searches Sidebar
- **Popular searches:** Harry Potter, Star Wars, Beatles, etc.
- **Category filters:** Books, Films, Music, Art
- **One-click search** activation
- **Sticky positioning** (remains visible while scrolling)

### Responsive Design
- Desktop: Two-column layout (results + sidebar)
- Tablet/Mobile: Stacked layout with sidebar on top
- Touch-friendly buttons and cards

---

## ⚠️ Disclaimer

**Important Legal Notice:**

This tool provides **informational analysis only** and does **not constitute legal advice**. Copyright laws are complex and vary by jurisdiction. The information provided by SCET should not be relied upon for legal decisions.

**For accurate copyright status:**
- Consult a qualified intellectual property attorney
- Verify with official copyright office records
- Consider jurisdiction-specific regulations
- Account for special cases and exceptions

---

## 📄 License

This project is created for educational and research purposes.

---

## 👨‍💻 Developer

Created by **Saish Malvankar** (saish340)

---

## 🔗 Links

- **Live Demo:** [https://scet.vercel.app/](https://scet.vercel.app/)
- **GitHub:** [https://github.com/saish340/SCET](https://github.com/saish340/SCET)
- **API Health:** [https://scet.vercel.app/api/v1/health](https://scet.vercel.app/api/v1/health)

---

**Last Updated:** February 2026
