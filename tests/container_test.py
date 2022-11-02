#!/usr/bin/env pytest -vs
"""Tests for CyHy Commander container."""

# Standard Python Libraries
import os
import time

# Third-Party Libraries
import pytest

from .utils import expect_log_entry

COMMANDER_READY_MESSAGE = "Balancing READY status of hosts"
MONGO_READY_MESSAGE = "waiting for connections on port 27017"


def test_mongo_running(mongo_container):
    """Verify the mongo container is running."""
    for _ in range(10):
        mongo_container.reload()
        if mongo_container.status != "created":
            break
        time.sleep(1)
    assert mongo_container.status == "running", "Mongo container is not running"


def test_mongo_ready(mongo_container, main_container):
    """Verify the mongo container is ready and start the main container."""
    expect_log_entry(mongo_container, MONGO_READY_MESSAGE)
    time.sleep(2)
    main_container.start()


def test_network(docker_network, main_container, mongo_container):
    """Verify the containers are connected to the test network."""
    docker_network.reload()
    assert set(docker_network.containers) == {
        main_container,
        mongo_container,
    }, "Network does not contain the expected containers"
    assert (
        docker_network.name in main_container.attrs["NetworkSettings"]["Networks"]
    ), "Main container not connected to test network"
    assert (
        docker_network.name in mongo_container.attrs["NetworkSettings"]["Networks"]
    ), "Mongo container not connected to test network"


@pytest.mark.parametrize(
    "container",
    [
        pytest.lazy_fixture("main_container"),
        pytest.lazy_fixture("version_container"),
        pytest.lazy_fixture("mongo_container"),
    ],
)
def test_container_running_or_exited(container):
    """Test that the container has started."""
    # Wait until the container is running or timeout.
    TIMEOUT = 10
    for _ in range(TIMEOUT):
        container.reload()
        if container.status != "created":
            break
        time.sleep(1)
    print(f"Container {container.name} status: {container.status}")
    assert container.status in ("exited", "running")


def test_wait_for_version_container_exit(version_container):
    """Wait for version container to exit cleanly."""
    assert (
        version_container.wait()["StatusCode"] == 0
    ), "The version container did not exit cleanly"


def test_log_version(version_container, project_version):
    """Verify the container outputs the correct version to the logs."""
    version_container.wait()  # make sure container exited if running test isolated
    log_output = version_container.logs(tail=1).decode("utf-8").strip()
    assert (
        log_output == f"v{project_version}"
    ), "Container version output to log does not match project version file"


@pytest.mark.slow
def test_commander_ready(main_container):
    """Wait for the Commander to be ready."""
    expect_log_entry(main_container, COMMANDER_READY_MESSAGE)


@pytest.mark.slow
def test_wait_for_healthy(main_container):
    """Wait for container to be healthy."""
    # It could already in an unhealthy state when we start as we may have been
    # rate limited.
    TIMEOUT = 180
    api_client = main_container.client.api
    for _ in range(TIMEOUT):
        # Verify the container is still running
        main_container.reload()
        assert main_container.status == "running", "The container unexpectedly exited."
        inspect = api_client.inspect_container(main_container.name)
        status = inspect["State"]["Health"]["Status"]
        if status == "healthy":
            break
        time.sleep(1)
    else:
        assert (
            False
        ), f"Container status did not transition to 'healthy' within {TIMEOUT} seconds."


@pytest.mark.skipif(
    os.environ.get("RELEASE_TAG") in [None, ""],
    reason="this is not a release (RELEASE_TAG not set)",
)
def test_release_version(project_version):
    """Verify that release tag version agrees with the module version."""
    assert (
        os.getenv("RELEASE_TAG") == f"v{project_version}"
    ), "RELEASE_TAG does not match the project version"


# The container version label is added during the GitHub Actions build workflow.
# It will not be present if the container is built locally.
# Skip this check if we are not running in GitHub Actions.
@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") != "true", reason="not running in GitHub Actions"
)
def test_container_version_label_matches(version_container, project_version):
    """Verify the container version label is the correct version."""
    assert (
        version_container.labels["org.opencontainers.image.version"] == project_version
    ), "Container version label does not match project version"
