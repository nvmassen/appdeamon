"""
OpenClaw Control - AppDaemon app for controlling Home Assistant entities via REST API.

Endpoints:
  POST /api/appdaemon/light
    Body: {"entity_id": "light.living", "action": "on|off|toggle", "brightness": 255}
    
  POST /api/appdaemon/switch
    Body: {"entity_id": "switch.plug", "action": "on|off|toggle"}
    
  POST /api/appdaemon/cover
    Body: {"entity_id": "cover.blind", "action": "open|close|stop", "position": 50}
    
  GET /api/appdaemon/status
    Returns: {"entities": {"light.living": {"state": "on", ...}}}

All endpoints require X-API-Key header.
"""

import appdaemon.plugins.hass.hassapi as hass
import json


class OpenClawControl(hass.Hass):
    """AppDaemon app that exposes REST API endpoints for entity control."""

    # Domain configurations: allowed actions and service mappings
    DOMAIN_CONFIG = {
        "light": {
            "actions": ["on", "off", "toggle"],
            "services": {"on": "turn_on", "off": "turn_off", "toggle": "toggle"},
            "extra_params": ["brightness", "color_temp", "rgb_color"],
        },
        "switch": {
            "actions": ["on", "off", "toggle"],
            "services": {"on": "turn_on", "off": "turn_off", "toggle": "toggle"},
            "extra_params": [],
        },
        "cover": {
            "actions": ["open", "close", "stop", "position"],
            "services": {"open": "open_cover", "close": "close_cover", "stop": "stop_cover", "position": "set_cover_position"},
            "extra_params": ["position"],
        },
        "climate": {
            "actions": ["heat", "cool", "off", "auto"],
            "services": {"heat": "set_hvac_mode", "cool": "set_hvac_mode", "off": "set_hvac_mode", "auto": "set_hvac_mode"},
            "extra_params": ["temperature", "target_temp_high", "target_temp_low"],
        },
        "fan": {
            "actions": ["on", "off", "toggle"],
            "services": {"on": "turn_on", "off": "turn_off", "toggle": "toggle"},
            "extra_params": ["percentage", "preset_mode"],
        },
    }

    def initialize(self):
        """Initialize the app and register API endpoints."""
        self.log("OpenClaw Control initializing...")
        
        # Get API key from config (required for security)
        self.api_key = self.args.get("api_key")
        if not self.api_key:
            self.log("WARNING: No api_key configured! API will reject all requests.", level="WARNING")
        
        # Get entities organized by domain from apps.yaml
        # Format: {"lights": [...], "switches": [...], "covers": [...]}
        self.entities_by_domain = {
            "light": self.args.get("lights", []),
            "switch": self.args.get("switches", []),
            "cover": self.args.get("covers", []),
            "climate": self.args.get("climates", []),
            "fan": self.args.get("fans", []),
        }
        
        # Build flat list for status endpoint
        self.all_entities = []
        for domain, entities in self.entities_by_domain.items():
            self.all_entities.extend(entities)
            if entities:
                self.log(f"  {domain}: {entities}")
        
        # Register domain-specific endpoints
        self.register_endpoint(self.handle_light, "light")
        self.register_endpoint(self.handle_switch, "switch")
        self.register_endpoint(self.handle_cover, "cover")
        self.register_endpoint(self.handle_climate, "climate")
        self.register_endpoint(self.handle_fan, "fan")
        self.register_endpoint(self.handle_status, "status")
        
        self.log(f"OpenClaw Control ready! {len(self.all_entities)} entities configured.")

    def verify_api_key(self, kwargs):
        """Verify the API key from request headers."""
        if not self.api_key:
            return False, ({"error": "API not configured"}, 503)
        
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

    def _control_entity(self, request, kwargs, domain):
        """
        Generic entity control handler.
        
        Args:
            request: Request data (dict or JSON string)
            kwargs: Request kwargs (contains headers)
            domain: Entity domain (light, switch, cover, etc.)
            
        Returns:
            tuple: (response_dict, http_status_code)
        """
        # Verify API key
        is_valid, error_response = self.verify_api_key(kwargs)
        if not is_valid:
            return error_response
        
        # Get domain config
        config = self.DOMAIN_CONFIG.get(domain)
        if not config:
            return {"error": f"Unknown domain: {domain}"}, 400
        
        try:
            data = request
            if isinstance(data, str):
                data = json.loads(data)
            
            entity_id = data.get("entity_id")
            action = data.get("action", config["actions"][0]).lower()
            
            # Validate entity_id
            if not entity_id:
                return {"error": "entity_id is required"}, 400
            
            # Validate entity belongs to correct domain
            if not entity_id.startswith(f"{domain}."):
                return {"error": f"Entity {entity_id} is not a {domain}"}, 400
            
            # Validate entity is in allowed list
            if entity_id not in self.entities_by_domain.get(domain, []):
                return {"error": f"Entity {entity_id} not in allowed list"}, 403
            
            # Validate action
            if action not in config["actions"]:
                return {"error": f"Invalid action: {action}. Use: {', '.join(config['actions'])}"}, 400
            
            # Build service call kwargs
            service_data = {"entity_id": entity_id}
            
            # Add extra parameters if provided
            for param in config.get("extra_params", []):
                if param in data:
                    service_data[param] = data[param]
            
            # Special handling for climate hvac_mode
            if domain == "climate" and action in ["heat", "cool", "off", "auto"]:
                service_data["hvac_mode"] = action
            
            # Get the service to call
            service = config["services"].get(action)
            
            # Call the service
            if service in ["turn_on", "turn_off", "toggle"]:
                # Use built-in methods
                if service == "turn_on":
                    self.turn_on(entity_id, **{k: v for k, v in service_data.items() if k != "entity_id"})
                elif service == "turn_off":
                    self.turn_off(entity_id)
                else:
                    self.toggle(entity_id)
            else:
                # Use call_service for domain-specific services
                self.call_service(f"{domain}/{service}", **service_data)
            
            # Get new state
            new_state = self.get_state(entity_id)
            attributes = self.get_state(entity_id, attribute="all")
            
            return {
                "success": True,
                "entity_id": entity_id,
                "action": action,
                "state": new_state,
                "attributes": attributes.get("attributes", {}) if attributes else {}
            }, 200
            
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}, 400
        except Exception as e:
            self.log(f"Error handling {domain} request: {e}", level="ERROR")
            return {"error": str(e)}, 500

    # Domain-specific endpoint handlers (thin wrappers around generic handler)
    
    def handle_light(self, request, kwargs):
        """Handle light control requests."""
        return self._control_entity(request, kwargs, "light")
    
    def handle_switch(self, request, kwargs):
        """Handle switch control requests."""
        return self._control_entity(request, kwargs, "switch")
    
    def handle_cover(self, request, kwargs):
        """Handle cover control requests."""
        return self._control_entity(request, kwargs, "cover")
    
    def handle_climate(self, request, kwargs):
        """Handle climate control requests."""
        return self._control_entity(request, kwargs, "climate")
    
    def handle_fan(self, request, kwargs):
        """Handle fan control requests."""
        return self._control_entity(request, kwargs, "fan")

    def handle_status(self, request, kwargs):
        """Return status of all configured entities."""
        is_valid, error_response = self.verify_api_key(kwargs)
        if not is_valid:
            return error_response
        
        try:
            entities_status = {}
            
            for entity_id in self.all_entities:
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
