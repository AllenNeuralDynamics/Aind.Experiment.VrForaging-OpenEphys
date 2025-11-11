import asyncio
import logging
from pathlib import Path

from clabe import resource_monitor
from clabe.apps import BonsaiApp, StdCommand
from clabe.apps.open_ephys import OpenEphysApp, OpenEphysAppSettings
from clabe.launcher import Launcher, LauncherCliArgs
from clabe.xml_rpc import XmlRpcClient, XmlRpcClientSettings
from pydantic_settings import CliApp

logger = logging.getLogger(__name__)


async def experiment(launcher: Launcher) -> None:
    monitor = resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(launcher.settings.data_dir, 2e11),
        ]
    )

    # Validate resources
    monitor.run()

    # Set up the RPC client
    rpc_client = XmlRpcClient(settings=XmlRpcClientSettings())
    result = await StdCommand("ipconfig").execute_async(rpc_client)
    print(result.stdout)
    # Post-fetching modifications
    open_ephys = OpenEphysApp(
        OpenEphysAppSettings(
            executable=Path(r"./Aind.Physiology.OpenEphys/.open-ephys/open-ephys.exe"),
            signal_chain=Path(r"./Aind.Physiology.OpenEphys/src/example.xml"),
        ),
        skip_validation=True,
    )
    result = await open_ephys.command.execute_async(rpc_client)
    # Run the task via Bonsai
    bonsai_app = BonsaiApp(
        workflow=Path(r"./Aind.Behavior.VrForaging/src/main.bonsai"),
        executable=Path(r"./Aind.Behavior.VrForaging/bonsai/bonsai.exe"),
    )

    async def start_ephys():
        await asyncio.sleep(2)  # Wait for Bonsai to initialize
        try:
            open_ephys.client.start_acquisition()
        except Exception as e:
            logger.error(f"Failed to start Open Ephys acquisition: {e}")

        logger.info("Started Open Ephys acquisition.")

    # Run both applications concurrently
    await asyncio.gather(open_ephys.run_async(), bonsai_app.run_async(), start_ephys())
    return


class ClabeCli(LauncherCliArgs):
    def cli_cmd(self):
        launcher = Launcher(settings=self)
        launcher.run_experiment(experiment)
        return None


def main() -> None:
    CliApp().run(ClabeCli)


if __name__ == "__main__":
    main()
