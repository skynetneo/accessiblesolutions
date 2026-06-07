import subprocess
import time
from typing import Dict, List


class DockerComputer:
    def __init__(
        self,
        container_name: str = "cua-sample-app",
        image: str = "ghcr.io/openai/openai-cua-sample-app:latest",
        display: str = ":99",
        port_mapping: str = "5900:5900",
        start_timeout: int = 10
    ):
        self.container_name = container_name
        self.image = image
        self.display = display
        self.port_mapping = port_mapping
        self.start_timeout = start_timeout
        self.dimensions = (1280, 720)  # Default fallback

    def __enter__(self):
        if not self._is_container_running():
            self._start_container()
            self._wait_for_container_ready()
        
        self._set_display_dimensions()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_container()

    def _exec(self, cmd: str) -> str:
        """Execute command in container safely"""
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "sh", "-c", cmd],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Command failed: {cmd}\nError: {e.stderr}"
            ) from e

    def _is_container_running(self) -> bool:
        """Check if container is running"""
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", f"name={self.container_name}"],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())

    def _start_container(self):
        """Start Docker container"""
        subprocess.check_call([
            "docker", "run", "-d", "--rm",
            "--name", self.container_name,
            "-p", self.port_mapping,
            "-e", f"DISPLAY={self.display}",
            self.image
        ])

    def _wait_for_container_ready(self):
        """Wait for container services to be ready"""
        end_time = time.time() + self.start_timeout
        while time.time() < end_time:
            try:
                self._exec("true")  # Simple test command
                return
            except RuntimeError:
                time.sleep(0.5)
        raise TimeoutError("Container failed to start within timeout period")

    def _set_display_dimensions(self):
        """Set display dimensions from actual container display"""
        try:
            geometry = self._exec(
                f"DISPLAY={self.display} xdotool getdisplaygeometry"
            ).strip()
            if geometry:
                self.dimensions = tuple(map(int, geometry.split()))
        except RuntimeError:
            pass  # Use default dimensions

    def _stop_container(self):
        """Stop Docker container"""
        subprocess.run(
            ["docker", "stop", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )

    def _xdo(self, command: str) -> None:
        """Helper method for xdotool commands"""
        full_cmd = f"DISPLAY={self.display} xdotool {command}"
        self._exec(full_cmd)

    def screenshot(self) -> str:
        """Capture screenshot as base64-encoded PNG"""
        return self._exec(
            f"DISPLAY={self.display} "
            "import -window root png:- | base64 -w 0"
        )

    def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at specified coordinates"""
        button_map = {"left": 1, "middle": 2, "right": 3}
        self._xdo(f"mousemove {x} {y} click {button_map.get(button, 1)}")

    def double_click(self, x: int, y: int) -> None:
        """Double-click at specified coordinates"""
        self._xdo(f"mousemove {x} {y} click --repeat 2 1")

    def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """Perform scrolling action"""
        self._xdo(f"mousemove {x} {y}")
        clicks = abs(scroll_y)
        button = 4 if scroll_y < 0 else 5
        if clicks > 0:
            self._xdo(f"click --repeat {clicks} {button}")

    def type(self, text: str) -> None:
        """Type text using xdotool"""
        safe_text = text.replace("'", "'\\''")
        self._xdo(f"type --delay 50 -- '{safe_text}'")

    def move(self, x: int, y: int) -> None:
        """Move mouse to coordinates"""
        self._xdo(f"mousemove {x} {y}")

    def keypress(self, keys: List[str]) -> None:
        """Send key combination"""
        mapping = {
            "ENTER": "Return",
            "LEFT": "Left",
            "RIGHT": "Right",
            "UP": "Up",
            "DOWN": "Down",
            "ESC": "Escape",
            "SPACE": "space",
            "BACKSPACE": "BackSpace",
            "TAB": "Tab",
        }
        combo = "+".join(mapping.get(k, k) for k in keys)
        self._xdo(f"key {combo}")

    def drag(self, path: List[Dict[str, int]]) -> None:
        """Perform drag operation along path"""
        if not path:
            return
            
        commands = []
        start = path[0]
        commands.append(f"mousemove {start['x']} {start['y']} mousedown 1")
        
        for point in path[1:]:
            commands.append(f"mousemove {point['x']} {point['y']}")
            
        commands.append("mouseup 1")
        self._xdo(" ".join(commands))

    def wait(self, ms: int = 1000) -> None:
        """Wait for specified milliseconds"""
        time.sleep(ms / 1000)