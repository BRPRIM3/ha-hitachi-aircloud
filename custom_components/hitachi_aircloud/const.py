"""Constantes da integração Hitachi airCloud Gateway (HC-IOTGW)."""

DOMAIN = "hitachi_aircloud"

UPDATE_INTERVAL_SECONDS = 30
# O gateway leva de 10 a 60 s para refletir um comando; mantemos o valor
# enviado na tela por até este tempo, a menos que o gateway confirme antes.
PENDING_TIMEOUT_SECONDS = 90
MAX_UNITS_PROBE = 16

# Modo de operação: texto devolvido no status -> código usado no comando
MODE_TEXT_TO_CODE = {"Cool": 4, "Heat": 2, "Fan": 1, "Dry": 64}

# Ventilação: texto devolvido no status -> (fan_mode do HA, código do comando)
FAN_TEXT_TO_MODE = {
    "Weak Wind": "low",
    "Strong Wind": "medium",
    "Sharp Wind": "high",
    "Super Wind": "max",
    "Auto": "auto",
}
FAN_MODE_TO_CODE = {"low": 0, "medium": 1, "high": 2, "max": 18, "auto": 32}

MIN_TEMP = 16.0
MAX_TEMP = 30.0
TEMP_STEP = 0.5
