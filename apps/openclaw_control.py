"""
OpenClaw Control - AppDaemon app for controlling Home Assistant entities via REST API.

Endpoints:
  POST /api/appdaemon/light
    Headers: X-API-Key: <your_api_key>
    Body: {"entity_id": "light.living", "action": "on|off|toggle"}
    
  GET /api/appdaemon/status
    Headers: X-API-Key: <your_api_key>
    Returns: {"entities": {"light.living": {"state": "on", "brightness": 255}}}
"""

import appdaemon.plugins.hass.hassapi as hass
import json


class OpenClawControl(hass.Hass):
    """AppDaemon app that exposes REST API endpoints for entity control."""

    def initialize(self):
        """Initialize the app and register API endpoints."""
        self.log("OpenClaw Control initializing...")
        
        # Get configured entities from apps.yaml (default to light.living)
        self.entities = self.args.get("entities", ["light.living"])
        
        # Get API key from config (required for security)
        self.api_key = self.args.get("api_key")
        if not self.api_key:
            self.log("WARNING: No api_key configured! API will reject all requests.", level="WARNING")
        
        self.log(f"Controlling entities: {self.entities}")
        
        # Register API endpoints
        self.register_endpoint(self.handle_light, "light")
        self.register_endpoint(self.handle_status, "status")
        
        self.log("OpenClaw Control ready!")

    def verify_api_key(self, kwargs):
        """
        Verify the API key from request headers.
        
        Args:
            kwargs: contains 'headers' dict from the request
            
        Returns:
            tuple: (is_valid, error_response) - error_response is None if valid
        """
        if not self.api_key:
            return False, ({"error": "API not configured"}, 503)
        
        # Get headers from the request object
        request = kwargs.get("request")
        headers = dict(request.headers) if request else {}
        
        # Check X-API-Key header (case-insensitive)
        provided_key = None
        for key, value in headers.items():
            if key.lower() == "x-api-key":
                provided_key = value
                break
        
        # Also check Authorization: Bearer <key>
        if not provided_key:
            auth_header = headers.get("Authorization", headers.get("authorization", ""))
            if auth_header.startswith("Bearer "):
                provided_key = auth_header[7:]
        
        if not provided_key:
            return False, ({"error": "Missing API key. Use X-API-Key header."}, 401)
        
        if provided_key != self.api_key:
            return False, ({"error": "Invalid API key"}, 403)
        
        return True, None

    def handle_light(self, request, kwargs):
        """
        Handle light control requests.
        
        Args:
            request: dict with request data
            kwargs: additional keyword arguments (includes headers)
            
        Returns:
            tuple: (response_dict, http_status_code)
        """
        # Verify API key
        is_valid, error_response = self.verify_api_key(kwargs)
        if not is_valid:
            return error_response
        
        data = request
        try:
            # Parse request body if it's a string
            if isinstance(data, str):
                data = json.loads(data)
            
            entity_id = data.get("entity_id")
            action = data.get("action", "toggle").lower()
            
            # Validate entity_id
            if not entity_id:
                return {"error": "entity_id is required"}, 400
            
            # Validate action
            if action not in ["on", "off", "toggle"]:
                return {"error": f"Invalid action: {action}. Use on/off/toggle"}, 400
            
            # Validate entity is in allowed list
            if entity_id not in self.entities:
                return {"error": f"Entity {entity_id} not in allowed list"}, 403
            
            # Perform the action
            if action == "on":
                self.turn_on(entity_id)
            elif action == "off":
                self.turn_off(entity_id)
            else:  # toggle
                self.toggle(entity_id)
            
            # Get new state
            new_state = self.get_state(entity_id)
            
            return {
                "success": True,
                "entity_id": entity_id,
                "action": action,
                "new_state": new_state
            }, 200
            
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}, 400
        except Exception as e:
            self.log(f"Error handling light request: {e}", level="ERROR")
            return {"error": str(e)}, 500

    def handle_status(self, request, kwargs):
        """
        Return status of all configured entities.
        
        Args:
            request: dict with request data
            kwargs: additional keyword arguments (includes headers)
            
        Returns:
            tuple: (response_dict, http_status_code)
        """
        # Verify API key
        is_valid, error_response = self.verify_api_key(kwargs)
        if not is_valid:
            return error_response
        
        try:
            entities_status = {}
            
            for entity_id in self.entities:
                state = self.get_state(entity_id)
                attributes = self.get_state(entity_id, attribute="all")
                
                entities_status[entity_id] = {
                    "state": state,
                    "attributes": attributes.get("attributes", {}) if attributes else {}
                }
            
            return {
                "success": True,
                "entities": entities_status
            }, 200
            
        except Exception as e:
            self.log(f"Error getting status: {e}", level="ERROR")
            return {"error": str(e)}, 500
