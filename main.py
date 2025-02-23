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
async def zendesk_integration(request: Request):
    try:
        # Read incoming JSON request
        data = await request.json()
        logger.info(f"Received request data: {data}")

        # Debugging: Log request headers
        headers = dict(request.headers)
        logger.info(f"Request headers: {headers}")

        # Extract message from request
        message = data.get("message")
        if not message:
            logger.error("No 'message' found in request data.")
            return JSONResponse(content={"error": "No 'message' found in request."}, status_code=400)

        # Log extracted message
        logger.info(f"Extracted Message: {message}")

        # Construct Telex payload
        telex_payload = {
            "event_name": "Zendesk New Ticket",
            "username": "ZendeskBot",
            "status": "success",
            "message": message
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

            # Log response status and full response content
            logger.info(f"Telex Response Status: {response.status_code}")
            logger.info(f"Telex Response Headers: {response.headers}")
            logger.info(f"Telex Response Body: {response.text}")

            # Ensure request was successful
            response.raise_for_status()
            return JSONResponse(content={"message": "Sent to Telex"}, status_code=200)

    except httpx.HTTPStatusError as e:
        logger.error(f"Telex HTTP error: {e.response.status_code}, Response Body: {e.response.text}")
        return JSONResponse(content={"error": f"Telex API error: {e.response.text}"}, status_code=e.response.status_code)

    except httpx.RequestError as e:
        logger.error(f"Failed to send request to Telex: {str(e)}")
        return JSONResponse(content={"error": "Failed to send request to Telex"}, status_code=500)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
