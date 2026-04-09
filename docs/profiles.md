# Scan Profiles

This document lists all available scan profiles and their configuration.

## Available Profiles

### 1. Document @200 DPI (Small)
**Profile ID:** `document_200_pdf`

- **Resolution:** 200 DPI
- **Color Mode:** Grayscale
- **Paper Size:** A4
- **Format:** PDF
- **Quality:** 80%
- **Source:** Flatbed
- **Batch Scan:** No
- **Auto Detect:** Yes
- **Description:** Best for text documents - smallest size

**Use Case:** Single-page text documents, letters, invoices

---

### 2. Multi-Page Document (ADF)
**Profile ID:** `document_adf_200_pdf`

- **Resolution:** 200 DPI
- **Color Mode:** Grayscale
- **Paper Size:** A4
- **Format:** PDF
- **Quality:** 80%
- **Source:** ADF (Automatic Document Feeder)
- **Batch Scan:** Yes
- **Auto Detect:** Yes
- **Description:** Scan multiple pages from document feeder

**Use Case:** Multi-page documents, contracts, forms with multiple pages

---

### 3. Color @300 DPI (Medium)
**Profile ID:** `color_300_pdf`

- **Resolution:** 300 DPI
- **Color Mode:** Color
- **Paper Size:** A4
- **Format:** PDF
- **Quality:** 85%
- **Source:** Flatbed
- **Batch Scan:** No
- **Auto Detect:** Yes
- **Description:** Good quality for mixed content

**Use Case:** Documents with images, colored graphics, presentations

---

### 4. Grayscale @150 DPI (Fast)
**Profile ID:** `gray_150_pdf`

- **Resolution:** 150 DPI
- **Color Mode:** Grayscale
- **Paper Size:** A4
- **Format:** PDF
- **Quality:** 75%
- **Source:** Flatbed
- **Batch Scan:** No
- **Auto Detect:** Yes
- **Description:** Quick scans, very small size

**Use Case:** Quick preview scans, drafts, temporary documents

---

### 5. Photo @600 DPI (High Quality)
**Profile ID:** `photo_600_jpeg`

- **Resolution:** 600 DPI
- **Color Mode:** Color
- **Paper Size:** A4
- **Format:** JPEG
- **Quality:** 95%
- **Source:** Flatbed
- **Batch Scan:** No
- **Auto Detect:** No
- **Description:** Best quality for photos

**Use Case:** Photo archiving, high-quality images, artwork

---

## Usage Examples

### REST API

```bash
# Single page document
curl -X POST http://localhost/api/v1/homeassistant/scan \
  -H "Content-Type: application/json" \
  -d '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document_200_pdf"}'

# Multi-page document (ADF)
curl -X POST http://localhost/api/v1/homeassistant/scan \
  -H "Content-Type: application/json" \
  -d '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document_adf_200_pdf"}'

# Color scan
curl -X POST http://localhost/api/v1/homeassistant/scan \
  -H "Content-Type: application/json" \
  -d '{"scanner_id": "favorite", "target_id": "favorite", "profile": "color_300_pdf"}'
```

### Home Assistant

```yaml
rest_command:
  # Flatbed document scan
  scan_document:
    url: "http://192.168.1.100/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document_200_pdf"}'
  
  # Multi-page ADF scan
  scan_multipage:
    url: "http://192.168.1.100/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document_adf_200_pdf"}'
  
  # Color scan
  scan_color:
    url: "http://192.168.1.100/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "color_300_pdf"}'
  
  # Photo scan
  scan_photo:
    url: "http://192.168.1.100/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "photo_600_jpeg"}'
```

---

## Technical Details

### Source Types

- **Flatbed:** Single-page scanning from the flatbed scanner
- **ADF:** Multi-page scanning from the Automatic Document Feeder

### Batch Scanning

When `batch_scan` is enabled (ADF profiles), the scanner will:
1. Scan the first page
2. Check if more pages are available in the feeder
3. Continue scanning until the feeder is empty
4. Combine all pages into a single PDF

### Auto Detection

When `auto_detect` is enabled, the scanner will automatically:
- Detect page boundaries
- Crop white margins
- Optimize image size

### File Naming

Files are named according to this pattern:
- **With custom filename:** `{custom_name}_{job_id}.{format}`
- **Without custom filename:** `scan_{job_id}.{format}`
- **Batch scan pages (intermediate):** `{prefix}_{job_id}_page001.tiff`, `page002.tiff`, etc.

---

## Creating Custom Profiles

Currently, profiles are hardcoded in `app/core/scanning/manager.py`. To add custom profiles:

1. Edit `app/core/scanning/manager.py`
2. Add a new profile to the `list_profiles()` method
3. Restart the Scan2Target service

**Future Enhancement:** Profile management via Web UI is planned for a future release.
