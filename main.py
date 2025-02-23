import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],  
    allow_headers=["*"],
)

# Fetch Telex Channel ID
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request) -> JSONResponse:
    try:
        # Read incoming JSON request
        data = await request.json()
        logger.info(f"Received request data: {data}")

        # Debugging: Log request headers
        headers = dict(request.headers)
        logger.info(f"Request headers: {headers}")

        # Handle settings request from Telex
        if "settings" in data:
            logger.info("Received settings configuration request")
            return JSONResponse(content={"message": "Settings received"}, status_code=200)

        # Extract ticket data
        ticket = data.get("ticket")
        if not ticket:
            logger.error("Missing 'ticket' data in request.")
            return JSONResponse(content={"error": "Missing 'ticket' data in request."}, status_code=400)

        # Extract ticket details
        ticket_id = str(ticket.get("id", "Unknown"))
        subject = ticket.get("subject", "No Subject")
        requester = ticket.get("requester", {})
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")
        message = ticket.get("latest_comment", {}).get("body") or ticket.get("description") or "No message provided"

        # Log extracted details
        logger.info(f"Extracted Ticket Details: ID={ticket_id}, Subject={subject}, Requester={requester_email}, "
                    f"Status={status}, Priority={priority}, Message={message}")

        # Construct Telex payload
        telex_payload = {
            "event_name": "Zendesk New Ticket",
            "username": "ZendeskBot",
            "status": "success",
            "message": (
                f"🎫 **New Ticket #{ticket_id}**\n\n"
                f"📌 **Subject:** {subject}\n"
                f"🔘 **Status:** {status}\n"
                f"⚡ **Priority:** {priority}\n"
                f"👤 **Requester:** {requester_email}\n\n"
                f"💬 **Message:**\n{message}"
            )
        }

        logger.info(f"Telex Payload: {telex_payload}")

        # Send payload to Telex
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

            # Log response status and content
            logger.info(f"Telex Response Status: {response.status_code}")
            logger.info(f"Telex Response Body: {response.text}")

            # Ensure request was successful
            response.raise_for_status()
            return JSONResponse(content={"message": "Sent to Telex"}, status_code=200)

    except httpx.RequestError as e:
        logger.error(f"Failed to send request to Telex: {str(e)}")
        return JSONResponse(content={"error": "Failed to send request to Telex"}, status_code=500)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
