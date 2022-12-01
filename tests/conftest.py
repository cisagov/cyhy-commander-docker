"""pytest configuration."""

# Standard Python Libraries
import os
from pathlib import Path

# Third-Party Libraries
import docker
import pytest

COMMANDER_DATA_VOLUME = "tests/config/commander_data_volume"
MAIN_SERVICE_NAME = "commander"
MONGO_IMAGE_NAME = "mongo:3.6"
MONGO_INIT_JS_FILE = "tests/config/mongo-init.js"
MONGO_ROOT_PASSWORD_FILE = "tests/config/mongo-root-passwd.txt"
MONGO_SERVICE_NAME = "mongo"
NETWORK_NAME = "cyhy-test-network"
VERSION_FILE = "src/version.txt"
VERSION_SERVICE_NAME = f"{MAIN_SERVICE_NAME}-version"

client = docker.from_env()


@pytest.fixture(autouse=True)
def group_github_log_lines(request):
    """Group log lines when running in GitHub actions."""
    # Group output from each test with workflow log groups
    # https://help.github.com/en/actions/reference/workflow-commands-for-github-actions#grouping-log-lines

    if os.environ.get("GITHUB_ACTIONS") != "true":
        # Not running in GitHub actions
        yield
        return
    # Group using the current test name
    print()
    print(f"::group::{request.node.name}")
    yield
    print()
    print("::endgroup::")


@pytest.fixture(scope="session")
def docker_network():
    """Create a docker network for the tests."""
    network = client.networks.create(NETWORK_NAME, driver="bridge", scope="local")
    yield network
    network.remove()


@pytest.fixture(scope="session")
def main_container(docker_network, image_tag):
    """Fixture for the main Commander container."""
    # Create the container but don't start it yet.
    # Mongo must be running before the Commander can start.
    container = client.containers.create(
        image_tag,
        detach=True,
        environment={
            "CONTAINER_VERBOSE": True,
            "CYHY_CONFIG_SECTION": "testing",
        },
        name=MAIN_SERVICE_NAME,
        network=docker_network.name,
        ports={},
        volumes={
            str(Path.cwd() / Path(COMMANDER_DATA_VOLUME)): {
                "bind": "/data",
                "driver": "local",
            }
        },
    )
    yield container
    container.remove(force=True)


@pytest.fixture(scope="session")
def version_container(image_tag):
    """Fixture for the version container."""
    container = client.containers.run(
        image_tag,
        command="--version",
        detach=True,
        name=VERSION_SERVICE_NAME,
    )
    yield container
    container.remove(force=True)


@pytest.fixture(scope="session")
def mongo_container(docker_network):
    """Fixture for the database container."""
    container = client.containers.run(
        MONGO_IMAGE_NAME,
        detach=True,
        environment={
            "MONGO_INITDB_DATABASE": "test_cyhy",
            "MONGO_INITDB_ROOT_USERNAME": "root",
            "MONGO_INITDB_ROOT_PASSWORD_FILE": "/run/secrets/mongo_root_passwd_txt",
        },
        name=MONGO_SERVICE_NAME,
        network=docker_network.name,
        ports={},
        volumes={
            str(Path.cwd() / Path(MONGO_INIT_JS_FILE)): {
                "bind": "/docker-entrypoint-initdb.d/mongo-init.js",
                "driver": "local",
                "mode": "ro",
            },
            # Pretend that we've got the secret file mounted
            str(Path.cwd() / Path(MONGO_ROOT_PASSWORD_FILE)): {
                "bind": "/run/secrets/mongo_root_passwd_txt",
                "driver": "local",
                "mode": "ro",
            },
        },
    )
    yield container
    container.remove(force=True)


@pytest.fixture(scope="session")
def project_version():
    """Get the project version."""
    pkg_vars = {}
    with open(VERSION_FILE) as f:
        exec(f.read(), pkg_vars)  # nosec
    return pkg_vars["__version__"]


def pytest_addoption(parser):
    """Add new commandline options to pytest."""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--image-tag",
        action="store",
        default="local/test-image:latest",
        help="image tag to test",
    )


@pytest.fixture
def image_tag(request):
    """Get the image tag to test."""
    return request.config.getoption("--image-tag")


def pytest_collection_modifyitems(config, items):
    """Modify collected tests based on custom marks and commandline options."""
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
