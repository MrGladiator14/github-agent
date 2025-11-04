#!/usr/bin/env python3
"""
GitHub Actions webhook server that stores events for MCP server.
"""

import json
from datetime import datetime
from pathlib import Path
from aiohttp import web
from logger import get_logger

EVENTS_FILE = Path(__file__).parent / "github_events.json"

async def handle_webhook(request):
    """Handle incoming GitHub webhook"""
    logger = get_logger(__name__)
    try:
        data = await request.json()
        
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        logger.info(f"Received GitHub webhook event: {event_type}")
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "action": data.get("action"),
            "workflow_run": data.get("workflow_run"),
            "check_run": data.get("check_run"),
            "repository": data.get("repository", {}).get("full_name"),
            "sender": data.get("sender", {}).get("login")
        }
        
        # Read existing events
        if EVENTS_FILE.exists():
            try:
                with open(EVENTS_FILE, 'r') as f:
                    events = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error reading events file: {e}")
                events = []
        else:
            events = []
            
        # Add new event and keep only last 100
        events.append(event)
        events = events[-100:]
        
        # Save back to file
        try:
            with open(EVENTS_FILE, 'w') as f:
                json.dump(events, f, indent=2)
            logger.debug(f"Successfully saved event to {EVENTS_FILE}")
            return web.json_response({"status": "success"})
            
        except Exception as e:
            logger.error(f"Error saving events file: {e}", exc_info=True)
            return web.json_response(
                {"status": "error", "message": "Failed to save event"}, 
                status=500
            )
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}", exc_info=True)
        return web.json_response(
            {"status": "error", "message": "Invalid JSON"}, 
            status=400
        )
    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        return web.json_response(
            {"status": "error", "message": "Internal server error"}, 
            status=500
        )

def create_app():
    """Create and configure the web application"""
    logger = get_logger(__name__)
    
    app = web.Application()
    app.router.add_post('/webhook/github', handle_webhook)
    
    @app.on_startup.append
    async def on_startup(app):
        logger.info("GitHub webhook server starting...")
        
    @app.on_shutdown.append
    async def on_shutdown(app):
        logger.info("GitHub webhook server shutting down...")
    
    return app

if __name__ == '__main__':
    logger = get_logger(__name__)
    app = create_app()
    
    host = '0.0.0.0'
    port = 8080
    
    logger.info(f"Starting GitHub webhook server on http://{host}:{port}")
    logger.info("Configure your GitHub webhook to POST to http://your-server:8080/webhook/github")
    
    web.run_app(app, host=host, port=port, access_log=None)  # Disable aiohttp access logs