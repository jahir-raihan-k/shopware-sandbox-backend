import secrets
from datetime import datetime
from fastapi import FastAPI, Request, Query, Header, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Shop
from utils import (
    generate_hmac,
    verify_header_signature,
    verify_query_param_signature,
    verify_body_signature
)

# ── App setup ─────────────────────────────────────────────────────────────
app = FastAPI()
templates = Jinja2Templates(directory="templates")

APP_SECRET = "mysecret" # Only for local development
APP_NAME = "MyExampleApp"
CONFIRMATION_URL= "http://host.docker.internal:8000/confirmation"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Pydantic model for confirmation body ─────────────────────────────────
class ConfirmationRequest(BaseModel):
    shopId:    str
    shopUrl:   str
    apiKey:    str
    secretKey: str
    timestamp: str

# ── Registration: HMAC‑of‑query → issue proof & shop_secret ────────────────
@app.get("/registration")
async def registration(
    request: Request,
    shop_id: str = Query(..., alias="shop-id"),
    shop_url: str = Query(..., alias="shop-url"),
    timestamp: str = Query(..., alias="timestamp"),
    sw_version: str|None = Header(None, alias="sw-version"),
    db: Session = Depends(get_db),
):
    """
    Registration handshake initiator. It gets called whenever a shop installs our
    extension.
    """

    # 1) verify Shopware’s signature on the raw query string
    await verify_header_signature(request, APP_SECRET, header_name="shopware-app-signature")

    # 2) generate proof
    proof = generate_hmac(f"{shop_id}{shop_url}{APP_NAME}".encode('utf-8'), APP_SECRET)

    # 3) generate per‑shop secret
    shop_secret = secrets.token_urlsafe(64)

    # 4) upsert into DB
    shop = Shop(
        shop_id=shop_id,
        shop_url=shop_url,
        shop_secret=shop_secret,
        sw_version=sw_version
    )
    db.merge(shop)
    db.commit()

    # 5) return registration payload
    return {
        "proof": proof,
        "secret": shop_secret,
        "confirmation_url": CONFIRMATION_URL
    }

# ── Confirmation: HMAC‑of‑body → store API keys ─────────────────────────────
@app.post("/confirmation")
async def confirmation(
    request: Request,
    data: ConfirmationRequest,
    db: Session = Depends(get_db),
):
    """
    Registration confirmation endpoint. This is where shopware shares shop
    auth credentials with us to access their admin & storefront apis.
    """

    # 1) load shop to get its secret
    shop = db.query(Shop).filter(Shop.shop_id == data.shopId).first()
    if not shop:
        raise HTTPException(400, "Unknown shopId—register first.")

    # 2) verify Shopware’s signature on raw JSON body  
    await verify_body_signature(request, shop_secret=shop.shop_secret, header_name="shopware-shop-signature")

    # 3) persist API credentials
    shop.api_key = data.apiKey
    shop.secret_key = data.secretKey
    shop.confirmed_at = datetime.now()
    db.commit()

    return {"status": "success", "message": f"Shop {data.shopId} confirmed."}

# ── Main‑module “Connect” page ────────────────────────────────────────────
@app.get("/connect", response_class=HTMLResponse)
async def connect(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Endpoint for rendering a html template to see if embedding Iframe works.
    """

    shop_id = request.query_params.get("shop-id")
    shop_url = request.query_params.get("shop-url")

    if not shop_id or not shop_url:
        raise HTTPException(400, detail="Missing shop-id or shop-url")

    # Load the shop
    shop = db.query(Shop).filter(Shop.shop_id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail=f"No shop found with id {shop_id}")

    # Verify signature from query string
    await verify_query_param_signature(request, shop_secret=shop.shop_secret)

    return templates.TemplateResponse("connect.html", {"request": request, "shop": shop})

# -- Tax-Provider endpoint (Its for test only) ----------------------
@app.post("/provide-tax")
async def provide_tax(request: Request, data: dict):
    """
    Test endpoint for checking if shopware is calling the endpoint during order
    checkout process. Well I guess we'll have ton of work based on this endpoint.
    """

    breakpoint_variable = True  # Make a breakpoint here to debug.

    dummy_data = {
        # optional: Overwrite the tax of an line item
        "lineItemTaxes": {
            "unique-identifier-of-lineitem": [
                {"tax":19,"taxRate":23,"price":19}
            ]
        },
        # optional: Overwrite the tax of an delivery
        "deliveryTaxes": {
            "unique-identifier-of-delivery-position": [
                {"tax":19,"taxRate":23,"price":19}
            ]
        },
        # optional: Overwrite the tax of the entire cart
        "cartPriceTaxes": [
            {"tax":19,"taxRate":23,"price":19}
        ]
    }

    return dummy_data

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",            # locate your FastAPI “app” in main.py
        host="0.0.0.0",        # listen on all interfaces
        port=8000,             # port number
        reload=True,           # auto‑restart on code changes
        log_level="debug"      # show debug output in console
    )