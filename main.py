import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Fetch Telex Channel ID from environment variables
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request):
    try:
        # Read incoming JSON request
        data = await request.json()
        logger.info(f"Received request data: {data}")

        # Log headers for debugging
        headers = dict(request.headers)
        logger.info(f"Request headers: {headers}")

        # Check the request source
        user_agent = headers.get('user-agent', '')
        
        if "Zendesk Webhook" in user_agent:
            # Handle Zendesk webhook format
            if "ticket" not in data:
                logger.error("Missing 'ticket' data in Zendesk webhook")
                return JSONResponse(content={"error": "Missing ticket data"}, status_code=400)

            ticket = data["ticket"]
            ticket_id = str(ticket.get("id", "Unknown"))
            subject = ticket.get("subject", "No Subject")
            requester = ticket.get("requester", {})
            requester_email = requester.get("email", "Unknown")
            status = ticket.get("status", "Unknown")
            description = ticket.get("description", "No message provided")

            # Log extracted ticket details
            logger.info(
                f"Extracted Ticket Details: ID={ticket_id}, Subject={subject}, "
                f"Requester={requester_email}, Status={status}, "
                f"Message={description}"
            )

            telex_payload = {
                "event_name": "Zendesk New Ticket",
                "username": "ZendeskBot",
                "status": "success",
                "message": (
                    f"🎫 **New Ticket #{ticket_id}**\n\n"
                    f"📌 **Subject:** {subject}\n"
                    f"🔘 **Status:** {status}\n"
                    f"⚡ **Priority:** Unknown\n"
                    f"👤 **Requester:** {requester_email}\n\n"
                    f"💬 **Message:**\n{description}"
                )
            }
        elif "python-requests" in user_agent:
            # Skip duplicate requests from the script
            logger.info("Skipping duplicate request from script")
            return JSONResponse(content={"message": "Skipped duplicate request"}, status_code=200)
        else:
            # Handle other formats if needed
            if "message" in data:
                telex_payload = {
                    "event_name": "Zendesk Ticket",
                    "username": "ZendeskBot",
                    "status": "success",
                    "message": data["message"]
                }
            else:
                logger.error("Invalid request format")
                return JSONResponse(content={"error": "Invalid request format"}, status_code=400)

        logger.info(f"Telex Payload: {telex_payload}")

        # Send to Telex
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

            logger.info(f"Telex Response Status: {response.status_code}")
            logger.info(f"Telex Response Headers: {response.headers}")
            logger.info(f"Telex Response Body: {response.text}")

            response.raise_for_status()
            return JSONResponse(content={"message": "Sent to Telex"}, status_code=200)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {str(e)}")
        return JSONResponse(content={"error": "Invalid JSON format"}, status_code=400)

    except httpx.HTTPStatusError as e:
        logger.error(f"Telex HTTP error: {e.response.status_code}, Response Body: {e.response.text}")
        return JSONResponse(
            content={"error": f"Telex API error: {e.response.text}"},
            status_code=e.response.status_code
        )

    except httpx.RequestError as e:
        logger.error(f"Failed to send request to Telex: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to send request to Telex"},
            status_code=500
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
