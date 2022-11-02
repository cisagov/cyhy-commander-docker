"""Helper utilities for pytest."""

# Standard Python Libraries
from datetime import datetime
from queue import Queue
import threading
import time


class LogTailer:
    """Create a separate threat to follow the logs and add to a queue."""

    def __init__(self, container, since: datetime | int = 0):
        """Initialize the log tailer."""
        self.log_generator = container.logs(
            follow=True,
            since=since,
            stream=True,
        )
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.queue: Queue = Queue()
        self.thread.start()

    def _run(self):
        for line in self.log_generator:
            self.queue.put(line.decode("utf-8"))

    def read(self):
        """Read the next line from the queue if possible."""
        if self.queue.empty():
            return None
        return self.queue.get()

    def empty(self):
        """Return if the queue is empty."""
        return self.queue.empty()


class RedactedPrinter:
    """Prints lines to stdout with redactions applied."""

    def __init__(self, redaction_regexes):
        """Initialize the printer."""
        self.redaction_regexes = redaction_regexes

    def print(self, *args, **kwargs):
        """Print with redaction of sensitive information."""
        # For each regular expression, replace the capture groups with asterisks.
        for regex in self.redaction_regexes:
            redacted_args = []
            for arg in args:
                # find all the matches for the current regex
                m_iter = regex.finditer(arg)
                # loop through matches
                for m in m_iter:
                    # replace each capture group of the match with asterisks
                    for g in range(1, len(m.groups()) + 1):
                        arg = (
                            arg[: m.span(g)[0]]
                            + "*" * (m.span(g)[1] - m.span(g)[0])
                            + arg[m.span(g)[1] :]  # noqa: E203
                        )
                # all redactions applied for this regex and arg
                redacted_args.append(arg)
            # send the redacted args to the next regex
            args = redacted_args
        print(*args, **kwargs)


def expect_log_entry(container, expected: str, log_stall_timeout: int = 60):
    """Wait for the container to log a message."""
    log_stall_timeout = 60
    tailer = LogTailer(container, since=1)
    timeout: float = time.time() + log_stall_timeout
    while (not tailer.empty()) or (
        container.status == "running" and time.time() < timeout
    ):
        log_line = tailer.read()
        if log_line is None:
            # No new log lines, wait a bit
            time.sleep(1)
            continue
        else:
            # The log is still alive, reset the timeout
            timeout = time.time() + log_stall_timeout
        print(log_line, end="")
        if expected in log_line:
            return  # success
        container.reload()
    else:
        # The container exited or we timed out
        print(
            f"Test ending... container status: {container.status}, log timeout: {time.time() - timeout}"
        )
        assert container.status == "running", "The container unexpectedly exited."
        assert (
            False
        ), "Logging stalled for {log_stall_timeout} seconds, and did not contain the ready message: {expected}"
