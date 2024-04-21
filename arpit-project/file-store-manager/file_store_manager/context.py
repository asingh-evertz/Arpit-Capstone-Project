"""Variables in use during the lifecycle of an invocation request"""

import logging
from typing import Union

# default this to the root logger
logger: Union[logging.Logger, logging.LoggerAdapter] = logging.getLogger()
