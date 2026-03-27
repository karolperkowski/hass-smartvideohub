import asyncio
import logging
import re
import collections

_LOGGER = logging.getLogger(__name__)
SERVER_RECONNECT_DELAY = 30

MODEL_VIDEOHUB = "VideoHub"
MODEL_STREAMING = "Streaming"
MODEL_TERANEX = "TERANEX"

class SmartVideoHub(asyncio.Protocol):
    def __init__(self, host, port):
        self._cmdServer = host
        self._cmdServerPort = port
        self._transport = None
        self._updateCallbacks = []
        self._errorMessage = None
        self._connected = False
        self._connecting = False
        self._stopped = False
        self.initialised = asyncio.Event()
        self.inputs = dict()
        self.filtered_inputs = dict()
        self.outputs = collections.defaultdict(dict)
        self.attrs = dict()
        self.stream_set = dict()
        self.stream_state = dict()
        self.teranex_set = dict()
        self.model = None
        self.name = ""
        self._buffer = ""
        self._current_block = None

    def connection_made(self, transport):
        """asyncio callback for a successful connection."""
        _LOGGER.debug("Connected to Black Magic Smart Video Hub API")
        self._transport = transport
        self._connected = True
        self._connecting = False
        self._buffer = ""
        self._current_block = None
        asyncio.get_running_loop().create_task(self.keep_alive())

    def data_received(self, data):
        """asyncio callback when data is received on the socket"""
        chunk = data.decode("utf-8")
        _LOGGER.debug(
            "TCP chunk received: %i bytes, buffer was %i bytes\n%s",
            len(chunk), len(self._buffer), chunk.replace("\r", "\\r").replace("\n", "\\n\n")
        )
        self._buffer += chunk
        # Only process complete lines; keep any trailing incomplete line in the buffer
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            # Blank lines indicate the end of a block
            if not line.strip():
                _LOGGER.debug("End of block: %s", self._current_block)
                self._current_block = None
            else:
                search = re.search("([A-Z ]+):$", line)
                line_conf = line.split(": ")

                if search:
                    self._current_block = search.group(1)
                    _LOGGER.debug("New block: %s", self._current_block)
                    if self._current_block == "END PRELUDE":
                        _LOGGER.info(
                            "Prelude complete — inputs: %i, outputs: %i",
                            len(self.inputs), len(self.outputs)
                        )
                        self.initialised.set()
                        self._send_update_callback(output_id=0)
                elif self._current_block == "INPUT LABELS":
                    input_number = int(line.split(" ", 1)[0]) + 1
                    input_label = line.split(" ", 1)[1].strip()
                    self.inputs[input_number] = input_label
                    if input_label != "Input " + str(input_number):
                        self.filtered_inputs[input_number] = input_label
                    elif input_number in self.filtered_inputs:
                        del self.filtered_inputs[input_number]
                    _LOGGER.debug("Input %i = '%s'", input_number, input_label)
                    if self.initialised.is_set():
                        self._send_update_callback(output_id=0)
                elif self._current_block == "OUTPUT LABELS":
                    output_number = int(line.split(" ", 1)[0]) + 1
                    output_label = line.split(" ", 1)[1].strip()
                    self.outputs[output_number]["name"] = output_label
                    self.outputs[output_number]["output"] = output_number
                    _LOGGER.debug("Output %i = '%s'", output_number, output_label)
                    if self.initialised.is_set():
                        self._send_update_callback(output_id=output_number)
                elif self._current_block == "VIDEO OUTPUT ROUTING":
                    output_id = int(line.split(" ", 1)[0]) + 1
                    input_id = int(line.split(" ", 1)[1]) + 1
                    self.outputs[output_id]["input"] = input_id
                    self.outputs[output_id]["input_name"] = self.get_input_name(input_id)
                    _LOGGER.debug(
                        "Routing output %i -> input %i ('%s')",
                        output_id, input_id, self.get_input_name(input_id)
                    )
                    if self.initialised.is_set():
                        self._send_update_callback(output_id=output_id)
                elif self._current_block == "VIDEOHUB DEVICE":
                    self.model = MODEL_VIDEOHUB
                    if len(line_conf) == 2 and line_conf[1].strip() != "":
                        self.attrs[line_conf[0]] = line_conf[1].strip()
                        if line_conf[0] == "Friendly Name":
                            self.name = line_conf[1].strip()
                elif self._current_block == "IDENTITY":
                    if len(line_conf) == 2 and line_conf[1].strip() != "":
                        self.attrs[line_conf[0]] = line_conf[1].strip()
                        if line_conf[0] == "Model":
                            if line_conf[1].startswith("Blackmagic Web Presenter"):
                                self.model = MODEL_STREAMING
                        elif line_conf[0] == "Label":
                            self.name = line_conf[1].strip()
                elif self._current_block == "STREAM SETTINGS":
                    if len(line_conf) == 2 and line_conf[1].strip() != "":
                        self.stream_set[line_conf[0]] = line_conf[1].strip()
                    if self.initialised.is_set():
                        self._send_update_callback(output_id=0)
                elif self._current_block == "STREAM STATE":
                    if len(line_conf) == 2 and line_conf[1].strip() != "":
                        self.stream_state[line_conf[0]] = line_conf[1].strip()
                    if self.initialised.is_set():
                        self._send_update_callback(output_id=0)
                elif self._current_block == "TERANEX MINI DEVICE":
                    self.model = MODEL_TERANEX
                    if len(line_conf) == 2 and line_conf[1].strip() != "":
                        if line_conf[0] == "Unique ID":
                            self.attrs[line_conf[0]] = line_conf[1].strip()
                        elif line_conf[0] == "Label":
                            self.name = line_conf[1].strip()
                        self.teranex_set[line_conf[0]] = line_conf[1].strip()
                    if self.initialised.is_set():
                        self._send_update_callback(output_id=0)
                elif self._current_block == "VIDEO OUTPUT":
                    if len(line_conf) == 2 and line_conf[1].strip() != "":
                        self.teranex_set[line_conf[0]] = line_conf[1].strip()
                    if self.initialised.is_set():
                        self._send_update_callback(output_id=0)
                else:
                    if self._current_block is not None:
                        _LOGGER.debug("Unhandled line in block '%s': %s", self._current_block, line)
                    else:
                        _LOGGER.debug("Line received outside any block: %s", line)
        if self._buffer:
            _LOGGER.debug("Partial line remaining in buffer (%i bytes): %s", len(self._buffer), self._buffer)


    def connection_lost(self, exc):
        """asyncio callback for a lost TCP connection."""
        self._connected = False
        self.initialised.clear()
        self._send_update_callback()
        _LOGGER.error("Connection to the server lost")
        if not self._stopped:
            _LOGGER.info("Reconnecting in %i seconds", SERVER_RECONNECT_DELAY)
            asyncio.get_running_loop().call_later(SERVER_RECONNECT_DELAY, self.connect)

    def connect(self):
        """Initiate a TCP connection to the device."""
        _LOGGER.info("Connecting to Smart Video Hub at %s:%s", self._cmdServer, self._cmdServerPort)
        self._connecting = True
        loop = asyncio.get_running_loop()
        coro = loop.create_connection(
            lambda: self, self._cmdServer, self._cmdServerPort
        )
        return loop.create_task(coro)

    def start(self):
        """Connect to the device and start the keep-alive loop."""
        self._stopped = False
        self.connect()

    def stop(self):
        """Disconnect from the device."""
        self._connected = False
        self._stopped = True
        if self._transport:
            self._transport.close()

    def _send_update_callback(self, output_id=0):
        """Internal method to notify all update callback subscribers."""
        if not self._updateCallbacks:
            _LOGGER.debug("Update callback has not been set by client")

        for callback in self._updateCallbacks:
            callback(output_id=output_id)

    def set_input(self, outputNumber, inputNumber):
        if (
            outputNumber <= len(self.outputs)
            and inputNumber <= len(self.inputs)
            and self.connected
        ):
            _LOGGER.debug("Setting output %i to input %i", outputNumber, inputNumber)
            command = (
                "VIDEO OUTPUT ROUTING:\n"
                + str(outputNumber - 1)
                + " "
                + str(inputNumber - 1)
                + "\n\n"
            )
            self._transport.write(command.encode("ascii"))

    def set_input_by_name(self, outputNumber, inputName):
        if not self._connected:
            _LOGGER.debug(
                "Cannot set input %s: server is disconnected", inputName
            )
            return False
        for input_number, label in self.inputs.items():
            if label == inputName:
                self.set_input(outputNumber, input_number)
                return True
        _LOGGER.debug(
            "Input %s was not found in the list of inputs", inputName
        )
        return False

    def get_input_list(self, filter_inputs=False) -> list[str]:
        if filter_inputs:
            return list(self.filtered_inputs.values())
        else:
            return list(self.inputs.values())

    def get_inputs(self, filter_inputs=False):
        if filter_inputs:
            return self.filtered_inputs
        else:
            return self.inputs

    def get_input_name(self, input_number):
        if input_number in self.inputs:
            return self.inputs[input_number]
        else:
            return "Input %d" % input_number

    def get_selected_input(self, output_number):
        if output_number in self.outputs:
            return self.outputs[output_number]["input"]
        else:
            return None

    async def keep_alive(self):
        """Send a keepalive command to reset its watchdog timer."""
        while self._connected:
            _LOGGER.debug("Sending keepalive to the server")
            command = "PING:\n\n"
            self._transport.write(command.encode("ascii"))
            await asyncio.sleep(120)

    def get_outputs(self):
        return self.outputs

    @property
    def error_message(self):
        """Returns the last error message, or None if there were no errors."""
        return self._errorMessage

    @property
    def is_initialised(self):
        return self.initialised.is_set()

    @property
    def connected(self):
        return self._connected

    def add_update_callback(self, method):
        """Public method to add a callback subscriber."""
        self._updateCallbacks.append(method)

    def set_video_mode(self, mode):
        command = "STREAM SETTINGS:\nVideo Mode: %s\n\n" % mode
        self._transport.write(command.encode("ascii"))

    def set_stream_platform(self, platform):
        command = "STREAM SETTINGS:\nCurrent Platform: %s\n\n" % platform
        self._transport.write(command.encode("ascii"))

    def set_stream_key(self, mode):
        command = "STREAM SETTINGS:\nStream Key: %s\n\n" % mode
        self._transport.write(command.encode("ascii"))

    def set_quality_level(self, mode):
        command = "STREAM SETTINGS:\nCurrent Quality Level: %s\n\n" % mode
        self._transport.write(command.encode("ascii"))

    def set_lut(self, lut_id):
        if isinstance(lut_id, str):
            lut = lut_id
        elif isinstance(lut_id, int) and lut_id == 1:
            lut = "Lut 0"
        elif isinstance(lut_id, int) and lut_id == 2:
            lut = "Lut 1"
        else:
            lut = "none"
        command = "VIDEO OUTPUT:\nLut on loop: true\nLut selection: %s\n\n" % lut
        self._transport.write(command.encode("ascii"))

    def set_steam_state(self, mode):
        command = "STREAM STATE:\nAction: %s\n\n" % ("Start" if mode else "Stop")
        self._transport.write(command.encode("ascii"))

    def reboot(self):
        command = "SHUTDOWN:\nAction: Reboot\n\n"
        self._transport.write(command.encode("ascii"))