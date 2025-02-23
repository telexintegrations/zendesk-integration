import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],  
    allow_headers=["*"],
)

TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        logger.info(f"Received data: {data}")
        
        # Handle settings request from Telex
        if "settings" in data:
            logger.info("Received settings configuration request")
            return JSONResponse(content={"message": "Settings received"}, status_code=200)

        ticket = data.get("ticket", {})
        if not ticket:
            logger.error("Missing ticket data in request")
            return JSONResponse(content={"error": "Missing 'ticket' data in request."}, status_code=400)

        ticket_id = str(ticket.get("id", "Unknown"))
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")
        message = ticket.get("latest_comment", {}).get("body") or ticket.get("description") or "No message provided"

        # Restructured payload for Telex
        message_content = (
            f"🎫 Ticket #{ticket_id}\n"
            f"📌 Subject: {subject}\n"
            f"🔘 Status: {status}\n"
            f"⚡ Priority: {priority}\n"
            f"👤 Requester: {requester_email}\n"
            f"💬 Message: {message}"
        )

        telex_payload = {
            "text": message_content,
            "event": {
                "name": "Zendesk New Ticket",
                "status": "success"
            },
            "sender": {
                "username": "ZendeskBot"
            }
        }

        logger.info(f"Sending payload to Telex: {telex_payload}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                TELEX_WEBHOOK_URL,
                json=telex_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                follow_redirects=True
            )
            response.raise_for_status()
            logger.info(f"Telex response: {response.text}")
            return JSONResponse(content={"message": "Sent to Telex"}, status_code=200)

    except httpx.RequestError as e:
        logger.error(f"Failed to send request to Telex: {str(e)}")
        return JSONResponse(content={"error": "Failed to send request to Telex"}, status_code=500)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
