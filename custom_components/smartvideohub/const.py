import logging

from homeassistant.const import CONF_HOST, CONF_PORT
from .pyvideohub import MODEL_TERANEX, MODEL_VIDEOHUB, MODEL_STREAMING

DOMAIN = "smartvideohub"
CONF_HIDE_DEFAULT_INPUTS = "hide_default_inputs"
CONF_LOG_LEVEL = "log_level"
DEFAULT_PORT = 9990
DEFAULT_LOG_LEVEL = "warning"

LOG_LEVELS: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}
