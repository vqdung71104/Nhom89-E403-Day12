"""Graceful shutdown signal handler for development app."""
import signal
import sys
import time
from typing import Callable


def register_shutdown_handler(
    stop_accepting_cb: Callable[[], None],
    mark_not_ready_cb: Callable[[], None],
    in_flight_cb: Callable[[], int],
    close_connections_cb: Callable[[], None],
    logger,
    timeout_seconds: int = 30,
    poll_interval_seconds: float = 0.5,
):
    """Register SIGTERM/SIGINT handlers with graceful shutdown steps.

    Steps:
    1. Stop accepting new requests.
    2. Finish in-flight requests (with timeout).
    3. Close active connections/resources.
    4. Exit process.
    """
    shutting_down = {"started": False}

    def shutdown_handler(signum, frame):
        if shutting_down["started"]:
            logger.info("Shutdown already in progress, ignoring repeated signal")
            return

        shutting_down["started"] = True
        logger.info("Received signal %s. Starting graceful shutdown...", signum)

        # 1) Stop accepting new requests immediately.
        stop_accepting_cb()
        mark_not_ready_cb()

        # 2) Wait for in-flight requests to finish.
        start = time.time()
        while True:
            in_flight = in_flight_cb()
            elapsed = time.time() - start
            if in_flight <= 0:
                logger.info("All in-flight requests completed")
                break
            if elapsed >= timeout_seconds:
                logger.warning(
                    "Graceful timeout reached (%ss) with %s in-flight request(s)",
                    timeout_seconds,
                    in_flight,
                )
                break
            logger.info("Waiting for %s in-flight request(s)...", in_flight)
            time.sleep(poll_interval_seconds)

        # 3) Close connections/resources.
        close_connections_cb()

        # 4) Exit process.
        logger.info("Graceful shutdown finished. Exiting process.")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
