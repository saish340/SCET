"""
SCET Backend Entry Point
Run with: python run.py
"""

import uvicorn
from app.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   SCET - Smart Copyright Expiry Tag System                   ║
║   ========================================                   ║
║                                                              ║
║   Starting server...                                         ║
║                                                              ║
║   API:     http://localhost:{settings.PORT}                          ║
║   Docs:    http://localhost:{settings.PORT}/docs                     ║
║   ReDoc:   http://localhost:{settings.PORT}/redoc                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
