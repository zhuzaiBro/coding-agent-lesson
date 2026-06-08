import os
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from routes.index import router as index_router
from routes.template import router as template_router
from routes.chat import router as chat_router
from routes.upload import router as upload_router
from routes.supabase import router as supabase_router
from routes.figma import router as figma_router
from services.supabase.oauth_flow import get_access_token_for_session
from services.figma.oauth_flow import get_access_token_for_session as get_figma_token_for_session
from config.supabase import OAUTH_COOKIE, set_request_oauth_context
from config.figma import FIGMA_OAUTH_COOKIE, set_request_figma_oauth_token

app = FastAPI(title="Duyi Figma Make Server")


@app.middleware("http")
async def mcp_oauth_context_middleware(request: Request, call_next):
    supabase_sid = request.cookies.get(OAUTH_COOKIE)
    set_request_oauth_context(
        supabase_sid,
        get_access_token_for_session(supabase_sid),
    )
    figma_sid = request.cookies.get(FIGMA_OAUTH_COOKIE)
    set_request_figma_oauth_token(get_figma_token_for_session(figma_sid))
    response = await call_next(request)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(index_router)
app.include_router(template_router, prefix="/api/template")
app.include_router(chat_router, prefix="/api/chat")
app.include_router(upload_router, prefix="/api/upload")
app.include_router(supabase_router, prefix="/api/supabase")
app.include_router(figma_router, prefix="/api/figma")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7001"))
    print(f"Server is running at http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
