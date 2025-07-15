# Copied from logging.py to avoid import conflict with standard library
import httpx
from enum import Enum

endpoint="http://20.244.56.144/evaluation-service/logs"

class stack(str, Enum):
    backend="backend"

class level(str, Enum):
    debug="debug"
    info="info"
    warn="warn"
    error="error"
    fatal="fatal"
package={"cache","controller","cronjob","db","domain","repository","service","route"}

async def log(stack:stack,level:level,package:str,message:str)->str:
    if package not in package:
        raise ValueError("Invalid package")
    payload = {
        "stack":stack.value,
        "level":level.value,
        "package":package,
        "message":message,
    }
    async with httpx.AsyncClient() as client:
        r=await client.post(endpoint, json=payload)
        r.raise_for_status()
        return r.json().get("logID")
