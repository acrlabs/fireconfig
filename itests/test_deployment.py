from constructs import Construct

import fireconfig as fire
from fireconfig.types import Capability

GRPC_PORT = 8086
OUTPUT_DIR = "itests/output"


def _make_deployment():
    volumes = (
        fire.VolumesBuilder()
        .with_config_map("the-volume-name", "/mount/path", {"foo.yml": "bar"})
        .with_config_map("other_name", "/mount/path", {"bar.yml": "asdf"})
    )

    container = (
        fire.ContainerBuilder(
            name="container1",
            image="test:latest",
            args=["/run.sh"],
        )
        .with_ports(GRPC_PORT)
        .with_security_context(Capability.DEBUG)
        .with_volumes(volumes)
    )

    return (
        fire.DeploymentBuilder(app_label="deployment1")
        .with_containers(container)
        .with_service()
        .with_service_account_and_role_binding("cluster-admin", True)
        .with_node_selector("type", "kind-worker")
    )


class FcTestPackage(fire.AppPackage):
    def __init__(self):
        self._depl = _make_deployment()

    def compile(self, chart: Construct):
        self._depl.build(chart)


def test_deployment():
    old_dag_filename = f"{OUTPUT_DIR}/dag.mermaid"
    dag, diff = fire.compile(
        {"the-namespace": [FcTestPackage()]},
        dag_filename=old_dag_filename,
        cdk8s_outdir=OUTPUT_DIR,
        dry_run=True,
    )

    assert not diff
    with open(old_dag_filename, encoding="utf-8") as f:
        # the resulting dag file has a blank newline which gets stripped by pre-commit,
        # so compare everything except for that very last character
        assert dag[:-1] == f.read()
