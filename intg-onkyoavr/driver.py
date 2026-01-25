{
  "driver_id": "onkyoavr",
  "version": "0.4.1",
  "min_core_api": "0.20.0",
  "name": {
    "en": "Onkyo AVR"
  },
  "icon": "uc:tv-music",
  "description": {
    "en": "Control Onkyo AV Receivers"
  },
  "setup_data_schema": {
    "title": {
      "en": "Add Onkyo Receiver",
      "de": "Onkyo Receiver hinzufügen"
    },
    "settings": [
      {
        "id": "series",
        "label": {
          "en": "Receiver Series",
          "de": "Receiver Serie"
        },
        "field": {
          "dropdown": {
            "value": "TX-NR6xx",
            "items": [
              {"id": "TX-NR5xx", "label": {"en": "TX-NR5xx (z.B. NR555, NR575, NR579)", "de": "TX-NR5xx (z.B. NR555, NR575, NR579)"}},
              {"id": "TX-NR6xx", "label": {"en": "TX-NR6xx (z.B. NR616, NR656, NR676, NR696)", "de": "TX-NR6xx (z.B. NR616, NR656, NR676, NR696)"}},
              {"id": "TX-NR7xx", "label": {"en": "TX-NR7xx (z.B. NR717, NR747, NR777)", "de": "TX-NR7xx (z.B. NR717, NR747, NR777)"}},
              {"id": "TX-RZxxx", "label": {"en": "TX-RZxxx (z.B. RZ610, RZ720, RZ810)", "de": "TX-RZxxx (z.B. RZ610, RZ720, RZ810)"}},
              {"id": "TX-NR8xx-9xx", "label": {"en": "TX-NR8xx/9xx (z.B. NR818, NR929)", "de": "TX-NR8xx/9xx (z.B. NR818, NR929)"}},
              {"id": "GENERIC", "label": {"en": "Other / Unknown", "de": "Andere / Unbekannt"}}
            ]
          }
        }
      },
      {
        "id": "address",
        "label": {
          "en": "IP Address",
          "de": "IP-Adresse"
        },
        "field": {
          "text": {
            "value": ""
          }
        }
      },
      {
        "id": "name",
        "label": {
          "en": "Name",
          "de": "Name"
        },
        "field": {
          "text": {
            "value": "Onkyo AVR"
          }
        }
      }
    ]
  },
  "developer": {
    "name": "Quirin",
    "email": "quirin@lippls.de",
    "url": "https://github.com/quintz"
  },
  "home_page": "https://github.com/quintz/integration-onkyoavr",
  "release_date": "2025-01-25"
}