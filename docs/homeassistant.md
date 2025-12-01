# Home Assistant Integration

Scan2Target provides full integration with Home Assistant to trigger scans via automations, buttons, and scripts.

## Quick Start

### 1. REST Command for Quick Scan (using favorites)

```yaml
# configuration.yaml
rest_command:
  scan_document:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document"}'
```

> **Note:** `rest_command` does not create an entity - it's only a service you can call. To get clickable buttons or status entities, see steps 2-4 below.

### 2. Create Button Entity (optional but recommended)

```yaml
# configuration.yaml
script:
  scan_document:
    alias: "Scan Document"
    icon: mdi:scanner
    sequence:
      - service: rest_command.scan_document
      - service: notify.persistent_notification
        data:
          message: "Scan started"
          title: "Scan2Target"
```

This creates `script.scan_document` that you can add to your dashboard as a button.

### 3. Status Sensor (optional - for monitoring)

```yaml
# configuration.yaml
binary_sensor:
  - platform: rest
    name: "Scan2Target Online"
    resource: "http://YOUR_SERVER_IP/api/v1/homeassistant/status"
    value_template: "{{ value_json.online }}"
    device_class: connectivity
    scan_interval: 30
```

This creates `binary_sensor.scan2target_online` showing online/offline status.

### 4. Automation to Trigger Scan

```yaml
# automations.yaml
- alias: "Scan on Button Press"
  trigger:
    - platform: state
      entity_id: script.scan_document
      to: "on"
  action:
    - service: rest_command.scan_document
    - service: notify.mobile_app
      data:
        message: "Scan started"
```

**Simple Dashboard Button:**
```yaml
# In your Lovelace dashboard
type: button
entity: script.scan_document
name: Scan Document
icon: mdi:scanner
tap_action:
  action: call-service
  service: script.scan_document
```

## Understanding Entities vs Services

| Type | Creates Entity? | Use Case |
|------|----------------|----------|
| `rest_command` | ❌ No | Service to call the API |
| `script` | ✅ Yes (`script.*`) | Clickable button in dashboard |
| `button` helper | ✅ Yes (`button.*`) | Simple trigger button |
| `sensor` | ✅ Yes (`sensor.*`) | Display status/values |
| `binary_sensor` | ✅ Yes (`binary_sensor.*`) | Online/offline status |

**Quick Setup for Beginners:**
1. Add `rest_command` (to call the API)
2. Add `script` (to get a button entity)
3. Add script to dashboard (now you can click it)

## Advanced Configuration

### Multiple Scan Profiles

```yaml
# configuration.yaml
rest_command:
  # Document (standard, grayscale)
  scan_document:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document"}'
  
  # Multi-page Scan (ADF)
  scan_multipage:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "adf", "source": "ADF"}'
  
  # Color (higher quality)
  scan_color:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "color"}'
  
  # Photo (highest quality)
  scan_photo:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "photo"}'
```

### Scanner and Target Selection

```yaml
# configuration.yaml
input_select:
  scan_scanner:
    name: Scanner
    options:
      - "Use Favorite"
    initial: "Use Favorite"
  
  scan_target:
    name: Target
    options:
      - "Use Favorite"
    initial: "Use Favorite"
  
  scan_profile:
    name: Scan Profile
    options:
      - "document"
      - "adf"
      - "color"
      - "photo"
    initial: "document"

rest_command:
  scan_custom:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: >
      {
        "scanner_id": "{{ 'favorite' if states('input_select.scan_scanner') == 'Use Favorite' else states('input_select.scan_scanner') }}",
        "target_id": "{{ 'favorite' if states('input_select.scan_target') == 'Use Favorite' else states('input_select.scan_target') }}",
        "profile": "{{ states('input_select.scan_profile') }}"
      }
```

### Status Sensor

```yaml
# configuration.yaml
sensor:
  - platform: rest
    name: "Scan2Target Status"
    resource: "http://YOUR_SERVER_IP/api/v1/homeassistant/status"
    method: GET
    value_template: "{{ 'Online' if value_json.online else 'Offline' }}"
    json_attributes:
      - scanner_count
      - target_count
      - active_scans
      - favorite_scanner
      - favorite_target
      - last_scan
    scan_interval: 30

  - platform: template
    sensors:
      scan2target_scanner_count:
        friendly_name: "Scanner Count"
        value_template: "{{ state_attr('sensor.scan2target_status', 'scanner_count') }}"
        unit_of_measurement: "Scanner"
      
      scan2target_active_scans:
        friendly_name: "Active Scans"
        value_template: "{{ state_attr('sensor.scan2target_status', 'active_scans') }}"
        unit_of_measurement: "Scans"
```

### Dashboard Card

```yaml
# Lovelace UI
type: vertical-stack
cards:
  - type: entities
    title: Scan2Target
    entities:
      - entity: sensor.scan2target_status
        name: Status
      - entity: sensor.scan2target_scanner_count
        name: Available Scanners
      - entity: sensor.scan2target_active_scans
        name: Active Scans
      - type: attribute
        entity: sensor.scan2target_status
        attribute: favorite_scanner
        name: Favorite Scanner
      - type: attribute
        entity: sensor.scan2target_status
        attribute: favorite_target
        name: Favorite Target
  
  - type: entities
    title: Scan Options
    entities:
      - input_select.scan_profile
  
  - type: horizontal-stack
    cards:
      - type: button
        name: Document
        icon: mdi:file-document-outline
        tap_action:
          action: call-service
          service: rest_command.scan_document
      
      - type: button
        name: Multi-Page
        icon: mdi:file-document-multiple-outline
        tap_action:
          action: call-service
          service: rest_command.scan_multipage
      
      - type: button
        name: Color
        icon: mdi:palette
        tap_action:
          action: call-service
          service: rest_command.scan_color
      
      - type: button
        name: Photo
        icon: mdi:camera
        tap_action:
          action: call-service
          service: rest_command.scan_photo
```

## Automation Examples

### 1. Daily Automatic Scan

```yaml
- alias: "Daily Document Scan"
  trigger:
    - platform: time
      at: "09:00:00"
  condition:
    - condition: state
      entity_id: binary_sensor.workday
      state: "on"
  action:
    - service: rest_command.scan_document
    - service: notify.mobile_app
      data:
        title: "Scan started"
        message: "Daily document scan has been triggered"
```

### 2. Scan on NFC Tag

```yaml
- alias: "Scan on NFC Tag"
  trigger:
    - platform: tag
      tag_id: YOUR_NFC_TAG_ID
  action:
    - service: rest_command.scan_document
    - service: notify.mobile_app
      data:
        message: "Scan started by NFC tag"
```

### 3. Scan on Voice Command

```yaml
- alias: "Scan on Voice Command"
  trigger:
    - platform: conversation
      command:
        - "Scan a document"
        - "Start a scan"
  action:
    - service: rest_command.scan_document
    - service: tts.google_translate_say
      data:
        entity_id: media_player.living_room
        message: "Starting scan"
```

### 4. Scan with Completion Notification

```yaml
# First create a helper for job ID
input_text:
  last_scan_job_id:
    name: "Last Scan Job ID"
    initial: ""

# REST Command with Response
rest_command:
  scan_with_notification:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document"}'

# Automation
- alias: "Scan with Notification"
  trigger:
    - platform: state
      entity_id: input_button.scan_with_notification
  action:
    - service: rest_command.scan_with_notification
    - delay:
        seconds: 5
    - service: notify.mobile_app
      data:
        message: "Scan running, please wait..."
    - delay:
        seconds: 30  # Estimated scan duration
    - service: notify.mobile_app
      data:
        message: "Scan completed!"
        data:
          url: "http://YOUR_SERVER_IP"
```

### 5. Conditional Scan Based on Presence

```yaml
- alias: "Scan when someone is home"
  trigger:
    - platform: state
      entity_id: input_button.scan_trigger
  condition:
    - condition: state
      entity_id: zone.home
      state: "home"
  action:
    - service: rest_command.scan_document
  else:
    - service: notify.mobile_app
      data:
        message: "Scan not possible - nobody home"
```

## API Endpoints

### POST /api/v1/homeassistant/scan
Starts a scan.

**Parameters:**
- `scanner_id` (optional): Scanner ID or "favorite" (default)
- `target_id` (optional): Target ID or "favorite" (default)
- `profile` (optional): Scan profile (document, adf, color, photo)
- `filename` (optional): Custom filename
- `source` (optional): Scan source (Flatbed, ADF)

**Response:**
```json
{
  "success": true,
  "job_id": "abc123",
  "message": "Scan started successfully",
  "scanner_name": "HP Scanner",
  "target_name": "NAS Scans",
  "estimated_duration": 15
}
```

### GET /api/v1/homeassistant/status
Returns system status.

**Response:**
```json
{
  "online": true,
  "scanner_count": 2,
  "target_count": 3,
  "active_scans": 0,
  "last_scan": "2025-12-01T10:30:00",
  "favorite_scanner": "HP Scanner",
  "favorite_target": "NAS Scans"
}
```

### GET /api/v1/homeassistant/scanners
List of all available scanners.

### GET /api/v1/homeassistant/targets
List of all available targets.

### GET /api/v1/homeassistant/profiles
List of all available scan profiles.

## Preparation in Scan2Target

1. **Set Favorite Scanner:**
   - Open Web UI → Scan section
   - Select scanner → Click ⭐ star

2. **Set Favorite Target:**
   - Open Web UI → Targets section
   - Select target → Click ⭐ star

3. **Optional: Disable Authentication (local network only!):**
   ```bash
   sudo nano /etc/systemd/system/scan2target.service
   # Add:
   Environment="SCAN2TARGET_REQUIRE_AUTH=false"
   
   sudo systemctl daemon-reload
   sudo systemctl restart scan2target
   ```

## Troubleshooting

### Error: "No favorite scanner configured"
- Mark a scanner as favorite in Scan2Target Web UI
- Or use specific `scanner_id` in REST command

### Error: "No favorite target configured"
- Mark a target as favorite in Scan2Target Web UI
- Or use specific `target_id` in REST command

### REST Command not responding
- Check server IP: `http://YOUR_SERVER_IP/health`
- Check firewall rules
- Check Scan2Target logs: `sudo journalctl -u scan2target -f`

### Scan not starting
- Discover scanner in Scan2Target Web UI
- Test target connectivity (Test & Save button)
- Check Active Jobs in Web UI

## Security Notes

⚠️ **Important for Production Environments:**

1. **Network Isolation:** Operate Scan2Target only on local network
2. **Reverse Proxy:** Use HTTPS reverse proxy for internet access
3. **Authentication:** Enable JWT auth for external access
4. **API Token:** Use API tokens instead of favorites for external calls

## Additional Resources

- [Scan2Target API Documentation](http://YOUR_SERVER_IP/docs)
- [Home Assistant REST Integration](https://www.home-assistant.io/integrations/rest/)
- [Home Assistant RESTful Command](https://www.home-assistant.io/integrations/rest_command/)
