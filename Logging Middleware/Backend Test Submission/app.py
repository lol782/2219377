from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, AnyHttpUrl
from datetime import datetime, timedelta
import string, random
from sys import path as sys_path
import os
sys_path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from custom_logging import log, stack, level

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
    await log(stack.backend, level.info, "controller", f"Short URL created: {code}")
    return short_res(shortcode=code, expiry=expiry_time)

@app.get("/{code}")
async def redirect(code: str, request: Request):
    data = memory_store.get(code)
    if not data:
        await log(stack.backend, level.error, "route", f"Shortcode not found: {code}")
        raise HTTPException(status_code=404, detail="Shortcode not found")

    if datetime.utcnow() > data["expiry"]:
        await log(stack.backend, level.warn, "route", f"Expired code accessed: {code}")
        raise HTTPException(status_code=410, detail="Link expired")

    click_stats[code].append({
        "timestamp": datetime.utcnow().isoformat(),
        "referer": request.headers.get("referer"),
        "ip": request.client.host
    })

    await log(stack.backend, level.info, "route", f"Redirected: {code}")
    return RedirectResponse(url=data["original_url"], status_code=307)

@app.get("/shorturls/{code}")
async def get_stats(code: str):
    if code not in memory_store:
        await log(stack.backend, level.error, "controller", f"Stats requested for invalid code: {code}")
        raise HTTPException(status_code=404, detail="Shortcode not found")

    data = memory_store[code]
    await log(stack.backend, level.debug, "controller", f"Stats retrieved for: {code}")
    return {
        "clicks": len(click_stats[code]),
        "createdAt": data["created_at"],
        "expiry": data["expiry"],
        "originalUrl": data["original_url"],
        "clickData": click_stats[code]
    }