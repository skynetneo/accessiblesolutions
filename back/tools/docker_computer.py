import time
import traceback
import base64
from typing import Optional, List, Dict as PyDict

try:
    import docker
except ModuleNotFoundError:  # Optional dependency for container-backed tooling.
    docker = None
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# This tool provides a Docker-based computer environment for running GUI applications.
# It uses a minimal Ubuntu 22.04-slim image with essential GUI tools installed.


class DockerComputerWithSDK:
    environment = "linux"
    dimensions = (1280, 720)  

    def __init__(
        self,
        container_name: str = "computer",
        image: str = "ubuntu:22.04-slim",
        display: str = ":99",
        vnc_port: int = 5900,
        # Attempt to run as non-root 
        user: str = "1000:1000",      
        # Disable external networking by default
        network_mode: str = "none",   
    ):
        if docker is None:
            raise RuntimeError("Missing optional dependency 'docker'. Install the docker Python package to enable DockerComputerWithSDK.")

        self.container_name = container_name
        self.image = image
        self.display = display
        self.vnc_port = vnc_port
        self.user = user
        self.network_mode = network_mode

        self._client = docker.from_env()   
        self._container = None
        self._dependencies_installed = False
        self._is_initialized = False

    def _ensure_initialized(self):
        """
        1. If container does not exist → create it + install packages + start Xvfb + x11vnc
        2. If container exists but is not running → start it
        3. Once running, verify dependencies (i.e. that Xvfb is up, xdotool exists, etc.)
        4. Query display geometry via xdpyinfo or xdotool getdisplaygeometry
        """
        if self._is_initialized:
            return
        try:
            existing = self._client.containers.get(self.container_name)
        except docker.errors.NotFound:
            existing = None

        if existing is None:

            # Define the command that runs inside the container on startup
            init_cmd = (
                "bash -lc \""
                "apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y xdotool imagemagick x11-apps xvfb x11vnc && "
                # Start Xvfb in background
                "Xvfb {disp} -screen 0 1280x720x24 > /dev/null 2>&1 & "
                # Start x11vnc (no password) on display :99
                "x11vnc -display {disp} -nopw -forever -shared > /dev/null 2>&1 & "
                # Keep container alive
                "tail -f /dev/null\""
            ).format(disp=self.display)

            try:
                self._container = self._client.containers.run(
                    self.image,
                    command=init_cmd,
                    name=self.container_name,
                    detach=True,
                    user=self.user,
                    network_mode=self.network_mode,
                    ports={f"{self.vnc_port}/tcp": self.vnc_port},
                    # ephemeral container: remove on stop
                    auto_remove=True,
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create & run container '{self.container_name}': {e}"
                )

            # Give Xvfb + x11vnc a moment to come up
            time.sleep(3)
            self._dependencies_installed = True
        else:
            
            if existing.status != "running":
                try:
                    existing.start()
                    # Give a moment for Xvfb + x11vnc to come up (assuming they were started as part of the container's command)
                    time.sleep(3)
                except Exception as e:
                    raise RuntimeError(f"Could not start existing container: {e}")
            self._container = existing

            # Check or install dependencies
            if not self._dependencies_installed:
                # Quick check: does xdotool exist?
                exit_code, _ = self._container.exec_run("which xdotool", demux=True)
                if exit_code != 0:
                    # Re-install dependencies
                    try:
                        self._install_dependencies()
                        self._dependencies_installed = True
                    except Exception as e:
                        raise RuntimeError(f"Failed to install dependencies: {e}")
                else:
                    self._dependencies_installed = True

        # Step 2: Display geometry
        self._update_display_geometry()
        self._is_initialized = True

    def _install_dependencies(self):
        """
        If xdotool (or other tools) are missing, install them in the container.
        """
        install_cmd = (
            "bash -lc \""
            "apt-get update && "
            "DEBIAN_FRONTEND=noninteractive apt-get install -y xdotool imagemagick x11-apps xvfb x11vnc"
            "\""
        )
        exit_code, (out, err) = self._container.exec_run(install_cmd, demux=True)
        if exit_code != 0:
            raise RuntimeError(f"apt-get install failed: {err.decode('utf-8').strip()}")

        # Restart Xvfb and x11vnc (in case container was already running without them)
        restart_cmd = (
            "bash -lc \""
            "pkill Xvfb || true; pkill x11vnc || true; "
            "Xvfb {disp} -screen 0 1280x720x24 > /dev/null 2>&1 & "
            "x11vnc -display {disp} -nopw -forever -shared > /dev/null 2>&1 &\""
        ).format(disp=self.display)

        exit_code, (out, err) = self._container.exec_run(restart_cmd, demux=True)
        if exit_code != 0:
            raise RuntimeError(f"Failed to restart Xvfb/x11vnc: {err.decode('utf-8').strip()}")

    def _update_display_geometry(self):
        """
        Attempts to retrieve the virtual display’s geometry via xdpyinfo or xdotool.
        Falls back to default (1280x720) if both fail.
        """
        # Try xdpyinfo first
        try:
            cmd = f"bash -lc \"DISPLAY={self.display} xdpyinfo 2>/dev/null | awk '/dimensions:/{{print $2}}'\""
            exit_code, (out, err) = self._container.exec_run(cmd, demux=True)
            geometry = out.decode("utf-8").strip()
            if geometry and "x" in geometry:
                w_str, h_str = geometry.split("x")
                self.dimensions = (int(w_str), int(h_str))
                return
        except Exception:
            pass

        # Fallback to xdotool getdisplaygeometry
        try:
            cmd2 = f"bash -lc \"DISPLAY={self.display} xdotool getdisplaygeometry\""
            exit_code, (out2, err2) = self._container.exec_run(cmd2, demux=True)
            geom2 = out2.decode("utf-8").strip()
            if geom2 and " " in geom2:
                w_str, h_str = geom2.split()
                self.dimensions = (int(w_str), int(h_str))
                return
        except Exception:
            pass

        # If both fail, keep default (1280x720)

    def run_command(self, command: str) -> str:
        """
        Execute an arbitrary shell command inside the container (under /bin/bash -lc).
        Returns stdout (or combined stdout+stderr if something fails).
        """
        self._ensure_initialized()
        try:
            full_cmd = f"bash -lc \"{command}\""
            exit_code, (out, err) = self._container.exec_run(full_cmd, demux=True)
            out_str = out.decode("utf-8") if out else ""
            err_str = err.decode("utf-8") if err else ""
            if exit_code != 0:
                return f"ERROR (code {exit_code})\n{err_str.strip()}\n{out_str.strip()}"
            return out_str.strip()
        except docker.errors.APIError as ae:
            return f"Error executing command in container: {str(ae)}"
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error running command: {e}\n{tb}"

    def screenshot(self) -> str:
        """
        Take a screenshot of the entire Xvfb display (:99) and return a data URI.
        If it fails, return an error string.
        """
        self._ensure_initialized()
        try:
            # Use ImageMagick 'import' to capture root window, output PNG to stdout, pipe through base64
            cmd = (
                f"bash -lc \"DISPLAY={self.display} import -window root png:- | base64 -w 0\""
            )
            exit_code, (out, err) = self._container.exec_run(cmd, demux=True)
            if exit_code != 0 or not out:
                err_msg = err.decode("utf-8").strip()
                return f"ERROR capturing screenshot: {err_msg}"
            b64 = out.decode("utf-8").strip()
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error taking screenshot: {e}\n{tb}"

    def click(self, x: int, y: int, button: str = "left") -> str:
        """
        Simulate a single mouse click at (x,y) in the container’s Xvfb display.
        """
        self._ensure_initialized()

        button_map = {"left": 1, "middle": 2, "right": 3}
        b = button_map.get(button.lower())
        if b is None:
            return f"Error: Invalid mouse button '{button}'. Valid options: left, middle, right."

        try:
            cmd = f"bash -lc \"DISPLAY={self.display} xdotool mousemove {x} {y} click {b}\""
            exit_code, (out, err) = self._container.exec_run(cmd, demux=True)
            if exit_code != 0:
                return f"ERROR clicking: {err.decode('utf-8').strip()}"
            return f"Clicked {button} at ({x}, {y})."
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error in click(): {e}\n{tb}"

    def double_click(self, x: int, y: int) -> str:
        """
        Simulate a double-click at (x,y).
        """
        self._ensure_initialized()
        try:
            cmd = f"bash -lc \"DISPLAY={self.display} xdotool mousemove {x} {y} click --repeat 2 1\""
            exit_code, (out, err) = self._container.exec_run(cmd, demux=True)
            if exit_code != 0:
                return f"ERROR double-click: {err.decode('utf-8').strip()}"
            return f"Double-clicked at ({x}, {y})."
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error in double_click(): {e}\n{tb}"

    def scroll(
        self, x: int, y: int, scroll_x_units: int = 0, scroll_y_units: int = 0
    ) -> str:
        """
        Simulate mouse scroll at (x,y). 
        scroll_y_units < 0 → scroll up, >0 → scroll down 
        scroll_x_units < 0 → scroll left, >0 → scroll right
        """
        self._ensure_initialized()
        actions = []

        # First move the mouse to (x,y)
        try:
            move_cmd = f"bash -lc \"DISPLAY={self.display} xdotool mousemove {x} {y}\""
            exit_code, (out, err) = self._container.exec_run(move_cmd, demux=True)
            if exit_code != 0:
                return f"ERROR moving mouse for scroll: {err.decode('utf-8').strip()}"
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error in scroll (mousemove): {e}\n{tb}"

        # Vertical scroll
        if scroll_y_units != 0:
            units = abs(scroll_y_units)
            button = 4 if scroll_y_units < 0 else 5
            try:
                scroll_cmd = f"bash -lc \"DISPLAY={self.display} xdotool click --repeat {units} {button}\""
                exit_code, (out, err) = self._container.exec_run(scroll_cmd, demux=True)
                if exit_code != 0:
                    return f"ERROR vertical scroll: {err.decode('utf-8').strip()}"
                direction = "up" if scroll_y_units < 0 else "down"
                actions.append(f"scrolled {direction} {units} units")
            except Exception as e:
                tb = traceback.format_exc()
                return f"Unexpected error in scroll (vertical): {e}\n{tb}"

        # Horizontal scroll
        if scroll_x_units != 0:
            units = abs(scroll_x_units)
            button = 6 if scroll_x_units < 0 else 7
            try:
                scroll_cmd2 = f"bash -lc \"DISPLAY={self.display} xdotool click --repeat {units} {button}\""
                exit_code, (out, err) = self._container.exec_run(scroll_cmd2, demux=True)
                if exit_code != 0:
                    return f"ERROR horizontal scroll: {err.decode('utf-8').strip()}"
                direction = "left" if scroll_x_units < 0 else "right"
                actions.append(f"scrolled {direction} {units} units")
            except Exception as e:
                tb = traceback.format_exc()
                return f"Unexpected error in scroll (horizontal): {e}\n{tb}"

        if not actions:
            return "No scrolling action performed."
        return f"At ({x}, {y}), " + " and ".join(actions) + "."

    def type_text(self, text_to_type: str) -> str:
        """
        Type the given text into the active window (using xdotool type).
        We bypass the shell by embedding in bash -lc, but xdotool’s 'type' is safe as long as we quote properly.
        """
        self._ensure_initialized()
        try:
            # We still wrap it in bash -lc so that multi-word strings are handled. xdotool type "some text"
            safe_text = text_to_type.replace('"', r'\"')
            cmd = f"bash -lc \"DISPLAY={self.display} xdotool type \\\"{safe_text}\\\"\""
            exit_code, (out, err) = self._container.exec_run(cmd, demux=True)
            if exit_code != 0:
                return f"ERROR typing text: {err.decode('utf-8').strip()}"
            return f"Typed: '{text_to_type}'."
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error in type_text(): {e}\n{tb}"

    def wait_ms(self, milliseconds: int = 1000) -> str:
        """
        Sleep on the host side. The container’s processes continue running. 
        """
        ms = max(0, milliseconds)
        time.sleep(ms / 1000.0)
        return f"Waited for {ms} milliseconds."

    def move_mouse(self, x: int, y: int) -> str:
        """
        Move the mouse pointer to (x,y).
        """
        self._ensure_initialized()
        try:
            cmd = f"bash -lc \"DISPLAY={self.display} xdotool mousemove {x} {y}\""
            exit_code, (out, err) = self._container.exec_run(cmd, demux=True)
            if exit_code != 0:
                return f"ERROR moving mouse: {err.decode('utf-8').strip()}"
            return f"Moved mouse to ({x}, {y})."
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error in move_mouse(): {e}\n{tb}"

    def key_press(self, keys_to_press: List[str]) -> str:
        """
        Press or hold keys. For multi-key combos, join with '+'. 
        E.g. ['CTRL','c'] becomes xdotool key Control_L+c
        """
        self._ensure_initialized()
        mapping = {
            "ENTER": "Return", "LEFT": "Left", "RIGHT": "Right", "UP": "Up", "DOWN": "Down",
            "ESC": "Escape", "SPACE": "space", "BACKSPACE": "BackSpace", "TAB": "Tab",
            "CTRL": "Control_L", "ALT": "Alt_L", "SHIFT": "Shift_L",
            "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4", "F5": "F5",
            "F6": "F6", "F7": "F7", "F8": "F8", "F9": "F9", "F10": "F10",
            "F11": "F11", "F12": "F12"
        }
        if not keys_to_press:
            return "Error: No keys provided."

        mapped = []
        for k in keys_to_press:
            key_sym = mapping.get(k.upper(), None)
            if key_sym:
                mapped.append(key_sym)
            else:
                # If it’s not a special key, pass it literally (xdotool will interpret it as a keysym)
                mapped.append(k)

        combo = "+".join(mapped)
        try:
            cmd = f"bash -lc \"DISPLAY={self.display} xdotool key {combo}\""
            exit_code, (out, err) = self._container.exec_run(cmd, demux=True)
            if exit_code != 0:
                return f"ERROR pressing keys: {err.decode('utf-8').strip()}"
            return f"Pressed: {keys_to_press} (as {combo})."
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error in key_press(): {e}\n{tb}"

    def drag_mouse(self, path_points: List[PyDict[str, int]]) -> str:
        """
        Drag the mouse along a sequence of points. 
        Issue separate xdotool calls for each segment to avoid huge single-line commands.
        """
        self._ensure_initialized()
        if not path_points or not all(isinstance(p, dict) and "x" in p and "y" in p for p in path_points):
            return "Error: drag_mouse expects a list of {'x':int,'y':int} dicts."

        try:
            # 1. Move to first point & hold down
            start = path_points[0]
            cmd1 = f"bash -lc \"DISPLAY={self.display} xdotool mousemove {start['x']} {start['y']} mousedown 1\""
            exit_code, (out1, err1) = self._container.exec_run(cmd1, demux=True)
            if exit_code != 0:
                return f"ERROR starting drag: {err1.decode('utf-8').strip()}"

            # 2. Move through intermediate points
            for pt in path_points[1:]:
                cmdn = f"bash -lc \"DISPLAY={self.display} xdotool mousemove {pt['x']} {pt['y']}\""
                exit_code, (out_i, err_i) = self._container.exec_run(cmdn, demux=True)
                if exit_code != 0:
                    return f"ERROR dragging at ({pt['x']},{pt['y']}): {err_i.decode('utf-8').strip()}"

            # 3. Release mouse
            cmd_end = f"bash -lc \"DISPLAY={self.display} xdotool mouseup 1\""
            exit_code, (out_end, err_end) = self._container.exec_run(cmd_end, demux=True)
            if exit_code != 0:
                return f"ERROR releasing drag: {err_end.decode('utf-8').strip()}"

            return f"Dragged mouse along {len(path_points)} points."
        except Exception as e:
            tb = traceback.format_exc()
            return f"Unexpected error in drag_mouse(): {e}\n{tb}"

    def get_dimensions(self) -> PyDict[str, int]:
        """
        Return the last‐known display geometry as a Python dict.
        """
        self._ensure_initialized()
        return {"width": self.dimensions[0], "height": self.dimensions[1]}


# Instantiate a single global instance (to be shared by all tools)
try:
    docker_computer_instance = DockerComputerWithSDK(container_name="computer")
except Exception as e:
    # If we can’t even create the Python-SDK client or something goes wrong early
    print(f"Failed to initialize DockerComputerWithSDK: {e}")
    docker_computer_instance = None


# Pydantic Schemas for Tool Arguments

class DockerRunCommandArgs(BaseModel):
    command: str = Field(description="Shell command to run inside the Docker container (bash -lc).")

class DockerClickMouseArgs(BaseModel):
    x: int = Field(description="X coordinate to click.")
    y: int = Field(description="Y coordinate to click.")
    button: Optional[str] = Field(default="left", description="Mouse button: 'left','middle','right'.")

class DockerDoubleClickMouseArgs(BaseModel):
    x: int = Field(description="X coordinate for double click.")
    y: int = Field(description="Y coordinate for double click.")

class DockerScrollMouseArgs(BaseModel):
    x: int = Field(description="X coordinate before scrolling.")
    y: int = Field(description="Y coordinate before scrolling.")
    scroll_x_units: Optional[int] = Field(default=0, description="Horizontal units: negative=left, positive=right.")
    scroll_y_units: Optional[int] = Field(default=0, description="Vertical units: negative=up, positive=down.")

class DockerTypeTextArgs(BaseModel):
    text_to_type: str = Field(description="Text to type into the container’s active window.")

class DockerWaitMsArgs(BaseModel):
    milliseconds: Optional[int] = Field(default=1000, description="Milliseconds to wait on the host side.")

class DockerMoveMouseArgs(BaseModel):
    x: int = Field(description="X coordinate to move mouse to.")
    y: int = Field(description="Y coordinate to move mouse to.")

class DockerKeyPressArgs(BaseModel):
    keys_to_press: List[str] = Field(description="List of keys to press, e.g. ['CTRL','c'].")

class DockerDragMouseArgs(BaseModel):
    path_points: List[PyDict[str, int]] = Field(
        description=(
            "List of {'x':int,'y':int} dicts for drag path, "
            "e.g. [{'x':100,'y':100}, {'x':200,'y':200}]."
        )
    )



# Tool Definitions for agents

if docker_computer_instance:
    @tool("docker_run_command", args_schema=DockerRunCommandArgs)
    def docker_run_command_tool(command: str) -> str:
        """Execute a shell command inside the Docker container."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.run_command(command)
        except Exception as e:
            return f"Error executing command: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_take_screenshot")
    def docker_take_screenshot_tool() -> str:
        """Capture a screenshot of the container’s display, return as data URI (base64‐encoded PNG)."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.screenshot()
        except Exception as e:
            return f"Error taking screenshot: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_click_mouse", args_schema=DockerClickMouseArgs)
    def docker_click_mouse_tool(
        x: int, y: int, button: Optional[str] = "left"
    ) -> str:
        """Simulate mouse click at (x,y)."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.click(x, y, button)
        except Exception as e:
            return f"Error clicking mouse: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_double_click_mouse", args_schema=DockerDoubleClickMouseArgs)
    def docker_double_click_mouse_tool(x: int, y: int) -> str:
        """Simulate a double‐click at (x,y)."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.double_click(x, y)
        except Exception as e:
            return f"Error double‐clicking mouse: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_scroll_mouse", args_schema=DockerScrollMouseArgs)
    def docker_scroll_mouse_tool(
        x: int, y: int, scroll_x_units: int = 0, scroll_y_units: int = 0
    ) -> str:
        """
        Scroll the mouse wheel at (x,y). 
        Negative scroll_y_units → scroll up. Positive → scroll down.
        Negative scroll_x_units → scroll left. Positive → scroll right.
        """
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.scroll(x, y, scroll_x_units, scroll_y_units)
        except Exception as e:
            return f"Error scrolling mouse: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_type_text", args_schema=DockerTypeTextArgs)
    def docker_type_text_tool(text_to_type: str) -> str:
        """Type the given text into the container’s active window."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.type_text(text_to_type)
        except Exception as e:
            return f"Error typing text: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_wait_ms", args_schema=DockerWaitMsArgs)
    def docker_wait_ms_tool(milliseconds: int = 1000) -> str:
        """Pause the host process for the given number of milliseconds."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.wait_ms(milliseconds)
        except Exception as e:
            return f"Error waiting: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_move_mouse", args_schema=DockerMoveMouseArgs)
    def docker_move_mouse_tool(x: int, y: int) -> str:
        """Move the mouse cursor to (x,y)."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.move_mouse(x, y)
        except Exception as e:
            return f"Error moving mouse: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_press_keys", args_schema=DockerKeyPressArgs)
    def docker_press_keys_tool(keys_to_press: List[str]) -> str:
        """
        Simulate pressing one or more keys. 
        E.g. ['CTRL','c'] → Control_L+c
        """
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.key_press(keys_to_press)
        except Exception as e:
            return f"Error pressing keys: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_drag_mouse", args_schema=DockerDragMouseArgs)
    def docker_drag_mouse_tool(path_points: List[PyDict[str, int]]) -> str:
        """Simulate a mouse drag along the specified path."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.drag_mouse(path_points)
        except Exception as e:
            return f"Error dragging mouse: {str(e)}\n{traceback.format_exc()}"

    @tool("docker_get_display_dimensions")
    def docker_get_display_dimensions_tool() -> PyDict[str, int] | str:
        """Return the container’s current display dimensions as a dict."""
        if not docker_computer_instance:
            return "Error: DockerComputerWithSDK not initialized."
        try:
            return docker_computer_instance.get_dimensions()
        except Exception as e:
            return f"Error getting dimensions: {str(e)}\n{traceback.format_exc()}"

    docker_tools = [
        docker_run_command_tool,
        docker_take_screenshot_tool,
        docker_click_mouse_tool,
        docker_double_click_mouse_tool,
        docker_scroll_mouse_tool,
        docker_type_text_tool,
        docker_wait_ms_tool,
        docker_move_mouse_tool,
        docker_press_keys_tool,
        docker_drag_mouse_tool,
        docker_get_display_dimensions_tool,
    ]
else:
    docker_tools = []
    print("WARNING: DockerComputerWithSDK tools not loaded because initialization failed.")
