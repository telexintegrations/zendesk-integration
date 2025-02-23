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

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
