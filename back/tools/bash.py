import asyncio
import curses
import signal
import sys

async def stream_command(command: str):
    """Runs a command and streams the output to the curses screen."""
    process = await asyncio.create_subprocess_exec(
        *command.split(),  # Split the command string into arguments
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
      while True:
        line = await process.stdout.readline()
        if not line:
          break
        yield line.decode('utf-8', errors='ignore')
      while True:
         line = await process.stderr.readline()
         if not line:
            break
         yield line.decode('utf-8', errors='ignore')
      await process.wait()
    except asyncio.CancelledError:
      if process.returncode is None:
        process.terminate()
        await process.wait()
      raise

async def main(stdscr):
    stdscr.clear()
    stdscr.refresh()

    command = input("Enter command to execute: ")
    y = 0
    try:
        async for line in stream_command(command):
            stdscr.addstr(y, 0, line)
            y += 1
            stdscr.refresh()
    except asyncio.CancelledError:
      stdscr.addstr(y, 0, f"Command interrupted by user.")
      stdscr.refresh()
    stdscr.addstr(y, 0, f"Command finished")
    stdscr.refresh()

    stdscr.getch()


def signal_handler(sig, frame):
    """Handles interrupt signals."""
    if sig == signal.SIGINT:
      raise KeyboardInterrupt
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    try:
        asyncio.run(curses.wrapper(main))
    except KeyboardInterrupt:
        print("Main loop interrupted")