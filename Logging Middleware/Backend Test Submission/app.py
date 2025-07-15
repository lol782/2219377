from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, AnyHttpUrl
from datetime import datetime, timedelta
import string, random
# from logging import log,stack,level

app = FastAPI()
memory_store={}
click_stats={}

def gen_url(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class short_req(BaseModel):
    url: AnyHttpUrl
    validity: int = 30
    shortcode: str | None = None

class short_res(BaseModel):
    shortcode: str
    expiry: datetime

@app.post("/shorten", response_model=short_res)
async def shorten_url(req: short_req):
    code = req.shortcode or gen_url()
    if code in memory_store:
        raise HTTPException(status_code=409, detail="Shortcode already exists")
    expiry_time = datetime.utcnow() + timedelta(minutes=req.validity)
    memory_store[code] = {
        "original_url": str(req.url),
        "expiry": expiry_time,
        "created_at": datetime.utcnow()
    }
    click_stats[code] = []
    # Logging can be added here if needed
    return short_res(shortcode=code, expiry=expiry_time)

@app.get("/{code}")
async def redirect(code: str, request: Request):
    data = memory_store.get(code)
    if not data:
        # Logging can be added here if needed
        raise HTTPException(status_code=404, detail="Shortcode not found")

    if datetime.utcnow() > data["expiry"]:
        # Logging can be added here if needed
        raise HTTPException(status_code=410, detail="Link expired")

    click_stats[code].append({
        "timestamp": datetime.utcnow().isoformat(),
        "referer": request.headers.get("referer"),
        "ip": request.client.host
    })

    # Logging can be added here if needed
    return RedirectResponse(url=data["original_url"], status_code=307)

@app.get("/shorturls/{code}")
async def get_stats(code: str):
    if code not in memory_store:
        # Logging can be added here if needed
        raise HTTPException(status_code=404, detail="Shortcode not found")

    data = memory_store[code]
    # Logging can be added here if needed
    return {
        "clicks": len(click_stats[code]),
        "createdAt": data["created_at"],
        "expiry": data["expiry"],
        "originalUrl": data["original_url"],
        "clickData": click_stats[code]
    }