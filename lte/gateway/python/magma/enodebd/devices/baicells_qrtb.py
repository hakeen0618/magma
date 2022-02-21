"""
Copyright 2021 The Magma Authors.

This source code is licensed under the BSD-style license found in the
LICENSE file in the root directory of this source tree.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import re
from typing import Any, Callable, Dict, List, Optional

from dp.protos.enodebd_dp_pb2 import CBSDRequest, CBSDStateResult
from magma.common.service import MagmaService
from magma.enodebd.data_models import transform_for_magma
from magma.enodebd.data_models.data_model import DataModel, TrParam
from magma.enodebd.data_models.data_model_parameters import (
    BaicellsParameterName,
    ParameterName,
    TrParameterType,
)
from magma.enodebd.device_config.cbrs_consts import (
    BAND,
    SAS_MAX_POWER_SPECTRAL_DENSITY,
    SAS_MIN_POWER_SPECTRAL_DENSITY,
)
from magma.enodebd.device_config.configuration_init import build_desired_config
from magma.enodebd.device_config.configuration_util import (
    calc_bandwidth_mhz,
    calc_bandwidth_rbs,
    calc_earfcn,
)
from magma.enodebd.device_config.enodeb_config_postprocessor import (
    EnodebConfigurationPostProcessor,
)
from magma.enodebd.device_config.enodeb_configuration import EnodebConfiguration
from magma.enodebd.devices.device_utils import EnodebDeviceName
from magma.enodebd.dp_client import get_cbsd_state
from magma.enodebd.exceptions import ConfigurationError, Tr069Error
from magma.enodebd.logger import EnodebdLogger
from magma.enodebd.state_machines.acs_state_utils import (
    get_all_objects_to_add,
    get_all_objects_to_delete,
    get_all_param_values_to_set,
    get_params_to_get,
    parse_get_parameter_values_response,
    process_inform_message,
)
from magma.enodebd.state_machines.enb_acs import EnodebAcsStateMachine
from magma.enodebd.state_machines.enb_acs_impl import BasicEnodebAcsStateMachine
from magma.enodebd.state_machines.enb_acs_states import (
    AcsMsgAndTransition,
    AcsReadMsgResult,
    DeleteObjectsState,
    EnbSendRebootState,
    EnodebAcsState,
    ErrorState,
    GetParametersState,
    NotifyDPState,
    SendGetTransientParametersState,
    SetParameterValuesState,
    WaitEmptyMessageState,
    WaitGetParametersState,
    WaitInformMRebootState,
    WaitInformState,
    WaitRebootResponseState,
    WaitSetParameterValuesState,
)
from magma.enodebd.state_machines.timer import StateMachineTimer
from magma.enodebd.tr069 import models

logger = EnodebdLogger


class BaicellsQRTBHandler(BasicEnodebAcsStateMachine):
    """
    BaicellsQRTB State Machine
    """

    def __init__(
            self,
            service: MagmaService,
    ) -> None:
        self._state_map = {}
        super().__init__(service, use_param_key=False)

    def reboot_asap(self) -> None:
        """
        Transition to 'reboot' state
        """
        self.transition('reboot')

    def is_enodeb_connected(self) -> bool:
        """
        Check if enodebd has received an Inform from the enodeb

        Returns:
            bool
        """
        return not isinstance(self.state, WaitInformState)

    def _init_state_map(self) -> None:
        self._state_map = {
            # RemWait state seems not needed for QRTB
            'wait_inform': WaitInformState(self, when_done='wait_empty', when_boot=None),
            'wait_empty': WaitEmptyMessageState(self, when_done='get_transient_params'),
            'get_transient_params': SendGetTransientParametersState(self, when_done='wait_get_transient_params'),
            'wait_get_transient_params': BaicellsWaitGetTransientParametersState(
                self,
                when_get='get_params',
                when_get_obj_params='get_obj_params',
                when_delete='delete_objs',
                when_add='add_objs',
                when_set='set_params',
                when_skip='end_session',
                request_all_params=True,
            ),
            'get_params': GetParametersState(self, when_done='wait_get_params', request_all_params=True),
            'wait_get_params': WaitGetParametersState(self, when_done='get_obj_params'),
            'get_obj_params': BaicellsGetObjectParametersState(self, when_done='wait_get_obj_params', request_all_params=True),
            'wait_get_obj_params': BaicellsWaitGetObjectParametersState(
                self, when_delete='delete_objs', when_add='add_objs',
                when_set='set_params', when_skip='end_session',
            ),
            'delete_objs': DeleteObjectsState(self, when_add='add_objs', when_skip='set_params'),
            'add_objs': BaicellsAddObjectsState(self, when_done='set_params'),
            'set_params': SetParameterValuesState(self, when_done='wait_set_params'),
            'wait_set_params': WaitSetParameterValuesState(
                self, when_done='check_get_params',
                when_apply_invasive='reboot',
            ),
            'check_get_params': GetParametersState(
                self,
                when_done='check_wait_get_params',
                request_all_params=True,
            ),
            'check_wait_get_params': WaitGetParametersState(self, when_done='end_session'),
            'end_session': BaicellsQRTBEndSessionState(self, when_done='notify_dp'),
            'notify_dp': BaicellsQRTBNotifyDPState(self, when_inform='wait_inform'),
            'reboot': EnbSendRebootState(self, when_done='wait_reboot'),
            'wait_reboot': WaitRebootResponseState(self, when_done='wait_post_reboot_inform'),
            'wait_post_reboot_inform': BaicellsQRTBWaitInformRebootState(
                self,
                when_done='wait_queued_events_post_reboot',
                when_timeout='wait_inform_post_reboot',
            ),
            "wait_queued_events_post_reboot": BaicellsQRTBQueuedEventsWaitState(
                self,
                when_done='wait_inform_post_reboot',
            ),
            'wait_inform_post_reboot': WaitInformState(self, when_done='wait_empty_post_reboot', when_boot=None),
            'wait_empty_post_reboot': WaitEmptyMessageState(
                self, when_done='get_transient_params',
                when_missing='check_optional_params',
            ),
            # The states below are entered when an unexpected message type is
            # received
            'unexpected_fault': ErrorState(self, inform_transition_target='wait_inform'),
        }

    @property
    def device_name(self) -> str:
        """
        Return the device name

        Returns:
            device name
        """
        return EnodebDeviceName.BAICELLS_QRTB

    @property
    def data_model_class(self) -> DataModel:
        """
        Return the class of the data model

        Returns:
            DataModel
        """
        return BaicellsQRTBTrDataModel

    @property
    def config_postprocessor(self) -> EnodebConfigurationPostProcessor:
        """
        Return the instance of config postprocessor

        Returns:
            EnodebConfigurationPostProcessor
        """
        return BaicellsQRTBTrConfigurationInitializer()

    @property
    def state_map(self) -> Dict[str, EnodebAcsState]:
        """
        Return the state map for the State Machine

        Returns:
            Dict[str, EnodebAcsState]
        """
        return self._state_map

    @property
    def disconnected_state_name(self) -> str:
        """
        Return the string representation of a disconnected state

        Returns:
            str
        """
        return 'wait_inform'

    @property
    def unexpected_fault_state_name(self) -> str:
        """
        Return the string representation of an unexpected fault state

        Returns:
            str
        """
        return 'unexpected_fault'


class BaicellsQRTBEndSessionState(EnodebAcsState):
    """ To end a TR-069 session, send an empty HTTP response

    For Baicells QRTB we can expect an inform message on
    End Session state, either a queued one or a periodic one
    """

    def __init__(
            self,
            acs: EnodebAcsStateMachine,
            when_done: str,
    ):
        super().__init__()
        self.acs = acs
        self.done_transition = when_done

    def get_msg(self, message: Any) -> AcsMsgAndTransition:
        """
        Send back a message to enb

        Args:
            message (Any): TR069 message

        Returns:
            AcsMsgAndTransition
        """
        request = models.DummyInput()
        return AcsMsgAndTransition(msg=request, next_state=self.done_transition)

    def state_description(self) -> str:
        """
        Describe the state

        Returns:
            str
        """
        return 'Completed provisioning eNB. Notifying DP.'


class BaicellsQRTBQueuedEventsWaitState(EnodebAcsState):
    """
    We've already received an Inform message. This state is to handle a
    Baicells eNodeB issue.

    After eNodeB is rebooted, hold off configuring it for some time.

    In this state, just hang at responding to Inform, and then ending the
    TR-069 session.
    """

    CONFIG_DELAY_AFTER_BOOT = 60

    def __init__(self, acs: EnodebAcsStateMachine, when_done: str):
        super().__init__()
        self.acs = acs
        self.done_transition = when_done
        self.wait_timer = None

    def enter(self):
        """
        Perform additional actions on state enter
        """
        self.wait_timer = StateMachineTimer(self.CONFIG_DELAY_AFTER_BOOT)
        logger.info(
            'Holding off of eNB configuration for %s seconds. ',
            self.CONFIG_DELAY_AFTER_BOOT,
        )

    def exit(self):
        """
        Perform additional actions on state exit
        """
        self.wait_timer = None

    def read_msg(self, message: Any) -> AcsReadMsgResult:
        """
        Read incoming message

        Args:
            message (Any): TR069 message

        Returns:
            AcsReadMsgResult
        """
        if not isinstance(message, models.Inform):
            return AcsReadMsgResult(msg_handled=False, next_state=None)
        process_inform_message(
            message, self.acs.data_model,
            self.acs.device_cfg,
        )
        return AcsReadMsgResult(msg_handled=True, next_state=None)

    def get_msg(self, message: Any) -> AcsMsgAndTransition:
        """
        Send back a message to enb

        Args:
            message (Any): TR069 message

        Returns:
            AcsMsgAndTransition
        """
        if self.wait_timer.is_done():
            return AcsMsgAndTransition(
                msg=models.DummyInput(),
                next_state=self.done_transition,
            )
        remaining = self.wait_timer.seconds_remaining()
        logger.info(
            'Waiting with eNB configuration for %s more seconds. ',
            remaining,
        )
        return AcsMsgAndTransition(msg=models.DummyInput(), next_state=None)

    def state_description(self) -> str:
        """
        Describe the state

        Returns:
            str
        """
        remaining = self.wait_timer.seconds_remaining()
        return 'Waiting for eNB REM to run for %d more seconds before ' \
               'resuming with configuration.' % remaining


class BaicellsQRTBWaitInformRebootState(WaitInformMRebootState):
    """
    BaicellsQRTB WaitInformRebootState implementation
    """
    INFORM_EVENT_CODE = '1 BOOT'


class BaicellsQRTBNotifyDPState(NotifyDPState):
    """
        BaicellsQRTB NotifyDPState implementation
    """

    def enter(self):
        """
        Enter the state
        """
        request = CBSDRequest(
            serial_number=self.acs.device_cfg.get_parameter(ParameterName.SERIAL_NUMBER),
        )
        state = get_cbsd_state(request)
        qrtb_update_desired_config_from_cbsd_state(state, self.acs.desired_cfg)


class BaicellsQRTBTrDataModel(DataModel):
    """
    Class to represent relevant data model parameters from TR-196/TR-098/TR-181.
    This class is effectively read-only

    This is for Baicells QRTB based on software BaiBS_QRTB_2.6.2.
    Tested on hw version E01 and A01
    """
    # Parameters to query when reading eNodeB config
    LOAD_PARAMETERS = [ParameterName.DEVICE]
    # Mapping of TR parameter paths to aliases
    DEVICE_PATH = 'Device.'
    FAPSERVICE_PATH = DEVICE_PATH + 'Services.FAPService.1.'
    PARAMETERS = {
        # Top-level objects
        ParameterName.DEVICE: TrParam(
            path=DEVICE_PATH, is_invasive=True, type=TrParameterType.OBJECT,
            is_optional=False,
        ),
        ParameterName.FAP_SERVICE: TrParam(
            path=FAPSERVICE_PATH, is_invasive=True, type=TrParameterType.OBJECT,
            is_optional=False,
        ),

        # Device info parameters
        ParameterName.GPS_STATUS: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.X_COM_GPS_Status', is_invasive=True,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.PTP_STATUS: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.X_COM_1588_Status', is_invasive=True,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.MME_STATUS: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.X_COM_MME_Status', is_invasive=True,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.REM_STATUS: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.X_COM_REM_Status', is_invasive=True,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.LOCAL_GATEWAY_ENABLE: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.X_COM_LTE_LGW_Switch',
            is_invasive=False, type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.GPS_ENABLE: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.X_COM_GpsSyncEnable', is_invasive=False,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.GPS_LAT: TrParam(
            path=DEVICE_PATH + 'FAP.GPS.LockedLatitude', is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.GPS_LONG: TrParam(
            path=DEVICE_PATH + 'FAP.GPS.LockedLongitude', is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.SW_VERSION: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SoftwareVersion', is_invasive=True,
            type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.SERIAL_NUMBER: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SerialNumber', is_invasive=True,
            type=TrParameterType.STRING, is_optional=False,
        ),

        # Capabilities
        ParameterName.DUPLEX_MODE_CAPABILITY: TrParam(
            path=FAPSERVICE_PATH + 'Capabilities.LTE.DuplexMode',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.BAND_CAPABILITY: TrParam(
            path=FAPSERVICE_PATH + 'Capabilities.LTE.BandsSupported',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),

        # RF-related parameters
        ParameterName.EARFCNDL: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.EARFCNDL', is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),
        ParameterName.EARFCNUL: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.EARFCNUL', is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),
        ParameterName.BAND: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.FreqBandIndicator', is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),
        ParameterName.PCI: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.PhyCellID', is_invasive=False,
            type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.DL_BANDWIDTH: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.DLBandwidth',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.UL_BANDWIDTH: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.ULBandwidth',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.RADIO_ENABLE: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.X_COM_RadioEnable',
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.SUBFRAME_ASSIGNMENT: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.PHY.TDDFrame.SubFrameAssignment', is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.SPECIAL_SUBFRAME_PATTERN: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.PHY.TDDFrame.SpecialSubframePatterns', is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.CELL_ID: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Common.CellIdentity',
            is_invasive=True, type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),
        ParameterName.POWER_SPECTRAL_DENSITY: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.PowerSpectralDensity',
            is_invasive=False, type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),

        # Other LTE parameters
        ParameterName.ADMIN_STATE: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.AdminState', is_invasive=False,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.OP_STATE: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.OpState', is_invasive=True,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.RF_TX_STATUS: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.RFTxStatus', is_invasive=True,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),

        # Core network parameters
        ParameterName.MME_IP: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.Gateway.S1SigLinkServerList',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.MME_PORT: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.Gateway.S1SigLinkPort', is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.NUM_PLMNS: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNListNumberOfEntries',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        BaicellsParameterName.NUM_LTE_NEIGHBOR_FREQ: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.CarrierNumberOfEntries', is_invasive=False,
            type=TrParameterType.INT, is_optional=False,
        ),
        BaicellsParameterName.NUM_LTE_NEIGHBOR_CELL: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECellNumberOfEntries', is_invasive=False, type=TrParameterType.INT,
            is_optional=False,
        ),

        # PLMN arrays are added below
        ParameterName.PLMN: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.', is_invasive=True,
            type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.TAC: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.TAC', is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.IP_SEC_ENABLE: TrParam(
            path=DEVICE_PATH + 'Services.FAPService.Ipsec.IPSEC_ENABLE',
            is_invasive=False, type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.MME_POOL_ENABLE: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.Gateway.X_COM_MmePool.Enable',
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        ),

        # Management server parameters
        ParameterName.PERIODIC_INFORM_ENABLE: TrParam(
            path=DEVICE_PATH + 'ManagementServer.PeriodicInformEnable',
            is_invasive=True, type=TrParameterType.BOOLEAN,
            is_optional=False,
        ),
        ParameterName.PERIODIC_INFORM_INTERVAL: TrParam(
            path=DEVICE_PATH + 'ManagementServer.PeriodicInformInterval',
            is_invasive=True, type=TrParameterType.UNSIGNED_INT,
            is_optional=False,
        ),

        # Performance management parameters
        ParameterName.PERF_MGMT_ENABLE: TrParam(
            path=DEVICE_PATH + 'FAP.PerfMgmt.Config.1.Enable', is_invasive=False,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.PERF_MGMT_UPLOAD_INTERVAL: TrParam(
            path=DEVICE_PATH + 'FAP.PerfMgmt.Config.1.PeriodicUploadInterval', is_invasive=False,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.PERF_MGMT_UPLOAD_URL: TrParam(
            path=DEVICE_PATH + 'FAP.PerfMgmt.Config.1.URL', is_invasive=False,
            type=TrParameterType.STRING, is_optional=False,
        ),

        # SAS parameters
        ParameterName.SAS_FCC_ID: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SAS.FccId', is_invasive=False,
            type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.SAS_USER_ID: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SAS.UserId', is_invasive=False,
            type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.SAS_ENABLED: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SAS.enableMode', is_invasive=False,
            type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.SAS_RADIO_ENABLE: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SAS.RadioEnable', is_invasive=False,
            type=TrParameterType.BOOLEAN, is_optional=False,
        ),
    }

    NUM_PLMNS_IN_CONFIG = 6
    for i in range(1, NUM_PLMNS_IN_CONFIG + 1):  # noqa: WPS604
        PARAMETERS[(ParameterName.PLMN_N) % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.' % i, is_invasive=True, type=TrParameterType.STRING,
            is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_CELL_RESERVED % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.CellReservedForOperatorUse' % i, is_invasive=True,
            type=TrParameterType.BOOLEAN,
            is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_ENABLE % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.Enable' % i, is_invasive=True,
            type=TrParameterType.BOOLEAN,
            is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_PRIMARY % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.IsPrimary' % i, is_invasive=True,
            type=TrParameterType.BOOLEAN,
            is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_PLMNID % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.PLMNID' % i, is_invasive=True,
            type=TrParameterType.STRING,
            is_optional=False,
        )

    NUM_NEIGHBOR_CELL_CONFIG = 16
    for i in range(1, NUM_NEIGHBOR_CELL_CONFIG + 1):
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_LIST_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.' % i, is_invasive=True, type=TrParameterType.INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_CELL_ID_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.CID' % i, is_invasive=True, type=TrParameterType.UNSIGNED_INT,
            is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_PLMN_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.PLMNID' % i, is_invasive=True, type=TrParameterType.STRING,
            is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_EARFCN_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.EUTRACarrierARFCN' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_PCI_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.PhyCellID' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_TAC_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.X_COM_TAC' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_QOFFSET_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.QOffset' % i, is_invasive=True, type=TrParameterType.INT,
            is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_CIO_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.CIO' % i, is_invasive=True, type=TrParameterType.INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_CELL_ENABLE_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.NeighborList.LTECell.%d.Enable' % i, is_invasive=True, type=TrParameterType.BOOLEAN,
            is_optional=False,
        )

    NUM_NEIGHBOR_FREQ_CONFIG = 8
    for i in range(1, NUM_NEIGHBOR_FREQ_CONFIG + 1):
        PARAMETERS[BaicellsParameterName.NEGIH_FREQ_LIST % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_EARFCN_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.EUTRACarrierARFCN' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_QRXLEVMINSIB5_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.QRxLevMinSIB5' % i, is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_Q_OFFSETRANGE_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.QOffsetFreq' % i, is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_TRESELECTIONEUTRA_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.TReselectionEUTRA' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_RESELECTIONPRIORITY_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.CellReselectionPriority' % i,
            is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_RESELTHRESHHIGH_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.ThreshXHigh' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_RESELTHRESHLOW_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.ThreshXLow' % i, is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_PMAX_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.PMax' % i, is_invasive=True,
            type=TrParameterType.INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_TRESELECTIONEUTRASFMEDIUM_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.TReselectionEUTRASFMedium' % i,
            is_invasive=True,
            type=TrParameterType.UNSIGNED_INT, is_optional=False,
        )
        PARAMETERS[BaicellsParameterName.NEIGHBOR_FREQ_ENABLE_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.InterFreq.Carrier.%d.Enable' % i, is_invasive=True,
            type=TrParameterType.BOOLEAN, is_optional=False,
        )

    TRANSFORMS_FOR_MAGMA = {
        # We don't set GPS, so we don't need transform for enb
        ParameterName.GPS_LAT: transform_for_magma.gps_tr181,
        ParameterName.GPS_LONG: transform_for_magma.gps_tr181,
    }

    @classmethod
    def get_parameter(cls, param_name: ParameterName) -> Optional[TrParam]:
        """
        Retrieve parameter by its name

        Args:
            param_name (ParameterName): parameter name to retrieve

        Returns:
            Optional[TrParam]
        """
        return cls.PARAMETERS.get(param_name)

    @classmethod
    def _get_magma_transforms(
            cls,
    ) -> Dict[ParameterName, Callable[[Any], Any]]:
        return cls.TRANSFORMS_FOR_MAGMA

    @classmethod
    def _get_enb_transforms(cls) -> Dict[ParameterName, Callable[[Any], Any]]:
        return {}

    @classmethod
    def get_load_parameters(cls) -> List[ParameterName]:
        """
        Retrieve all load parameters

        Returns:
             List[ParameterName]
        """
        return cls.LOAD_PARAMETERS

    @classmethod
    def get_num_plmns(cls) -> int:
        """
        Retrieve the number of all PLMN parameters

        Returns:
            int
        """
        return cls.NUM_PLMNS_IN_CONFIG

    @classmethod
    def get_num_neighbor_freq(cls) -> int:
        """ Get the neighbor freq number """
        return cls.NUM_NEIGHBOR_FREQ_CONFIG

    @classmethod
    def get_num_neighbor_cell(cls) -> int:
        """ Get the neighbor cell number """
        return cls.NUM_NEIGHBOR_CELL_CONFIG

    @classmethod
    def get_parameter_names(cls) -> List[ParameterName]:
        """
        Retrieve all parameter names

        Returns:
            List[ParameterName]
        """
        excluded_params = [
            str(ParameterName.DEVICE),
            str(ParameterName.FAP_SERVICE),
        ]
        names = list(
            filter(
                lambda x: (not str(x).startswith('PLMN')) and (not str(x).startswith('neighbor'))
                and (str(x) not in excluded_params),
                cls.PARAMETERS.keys(),
            ),
        )
        return names

    @classmethod
    def get_numbered_param_names(cls) -> Dict[ParameterName, List[ParameterName]]:
        """
        Retrieve parameter names of all objects

        Returns:
            Dict[ParameterName, List[ParameterName]]
        """
        names = {}
        for i in range(1, cls.NUM_PLMNS_IN_CONFIG + 1):
            params = []
            params.append(ParameterName.PLMN_N_CELL_RESERVED % i)
            params.append(ParameterName.PLMN_N_ENABLE % i)
            params.append(ParameterName.PLMN_N_PRIMARY % i)
            params.append(ParameterName.PLMN_N_PLMNID % i)
            names[ParameterName.PLMN_N % i] = params
        for i in range(1, cls.NUM_NEIGHBOR_FREQ_CONFIG + 1):
            params = [
                BaicellsParameterName.NEIGHBOR_FREQ_ENABLE_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_EARFCN_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_PMAX_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_Q_OFFSETRANGE_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_Q_OFFSETRANGE_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_RESELTHRESHLOW_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_RESELTHRESHHIGH_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_RESELECTIONPRIORITY_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_QRXLEVMINSIB5_N % i,
                BaicellsParameterName.NEIGHBOR_FREQ_TRESELECTIONEUTRA_N % i,
            ]
            names[BaicellsParameterName.NEGIH_FREQ_LIST % i] = params
        for i in range(1, cls.NUM_NEIGHBOR_CELL_CONFIG + 1):
            params = [
                BaicellsParameterName.NEIGHBOR_CELL_ENABLE_N % i,
                BaicellsParameterName.NEIGHBOR_CELL_PLMN_N % i,
                BaicellsParameterName.NEIGHBOR_CELL_CELL_ID_N % i,
                BaicellsParameterName.NEIGHBOR_CELL_EARFCN_N % i,
                BaicellsParameterName.NEIGHBOR_CELL_PCI_N % i,
                BaicellsParameterName.NEIGHBOR_CELL_TAC_N % i,
                BaicellsParameterName.NEIGHBOR_CELL_QOFFSET_N % i,
                BaicellsParameterName.NEIGHBOR_CELL_CIO_N % i,
            ]
            names[BaicellsParameterName.NEIGHBOR_CELL_LIST_N % i] = params
        return names


class BaicellsQRTBTrConfigurationInitializer(EnodebConfigurationPostProcessor):
    """
    Overrides desired config on the State Machine
    """

    def postprocess(self, mconfig: Any, service_cfg: Any, desired_cfg: EnodebConfiguration) -> None:
        """
        Add some params to the desired config

        Args:
            mconfig (Any): mconfig
            service_cfg (Any): service config
            desired_cfg (EnodebConfiguration): desired config
        """
        desired_cfg.set_parameter(ParameterName.SAS_ENABLED, 1)

        desired_cfg.set_parameter_for_object(
            ParameterName.PLMN_N_CELL_RESERVED % 1, True,  # noqa: WPS345,WPS425
            ParameterName.PLMN_N % 1,  # noqa: WPS345
        )
        parameters_to_delete = [
            ParameterName.RADIO_ENABLE, ParameterName.POWER_SPECTRAL_DENSITY,
            ParameterName.EARFCNDL, ParameterName.EARFCNUL, ParameterName.BAND,
            ParameterName.DL_BANDWIDTH, ParameterName.UL_BANDWIDTH,
            ParameterName.SAS_RADIO_ENABLE,
        ]
        for p in parameters_to_delete:
            if desired_cfg.has_parameter(p):
                desired_cfg.delete_parameter(p)


def qrtb_update_desired_config_from_cbsd_state(state: CBSDStateResult, config: EnodebConfiguration) -> None:
    """
    Call grpc endpoint on the Domain Proxy to update the desired config based on sas grant

    Args:
        state (CBSDStateResult): state result as received from DP
        config (EnodebConfiguration): configuration to update
    """
    logger.debug("Updating desired config based on sas grant")
    config.set_parameter(ParameterName.SAS_RADIO_ENABLE, state.radio_enabled)

    if not state.radio_enabled:
        return

    earfcn = calc_earfcn(state.channel.low_frequency_hz, state.channel.high_frequency_hz)
    bandwidth_mhz = calc_bandwidth_mhz(state.channel.low_frequency_hz, state.channel.high_frequency_hz)
    bandwidth_rbs = calc_bandwidth_rbs(bandwidth_mhz)
    psd = _calc_psd(state.channel.max_eirp_dbm_mhz)

    params_to_set = {
        ParameterName.SAS_RADIO_ENABLE: True,
        ParameterName.BAND: BAND,
        ParameterName.DL_BANDWIDTH: bandwidth_rbs,
        ParameterName.UL_BANDWIDTH: bandwidth_rbs,
        ParameterName.EARFCNDL: earfcn,
        ParameterName.EARFCNUL: earfcn,
        ParameterName.POWER_SPECTRAL_DENSITY: psd,
    }

    for param, value in params_to_set.items():
        config.set_parameter(param, value)


def _calc_psd(eirp: float) -> int:
    psd = int(eirp)
    if not SAS_MIN_POWER_SPECTRAL_DENSITY <= psd <= SAS_MAX_POWER_SPECTRAL_DENSITY:  # noqa: WPS508
        raise ConfigurationError(
            'Power Spectral Density %d exceeds allowed range [%d, %d]' %
            (psd, SAS_MIN_POWER_SPECTRAL_DENSITY, SAS_MAX_POWER_SPECTRAL_DENSITY),
        )
    return psd


class BaicellsWaitGetObjectParametersState(EnodebAcsState):
    """
        The state method for Baicells 436q.  Add the neighbor cell
        object and neighbor freq object in current method.
    """

    def __init__(
            self,
            acs: EnodebAcsStateMachine,
            when_delete: str,
            when_add: str,
            when_set: str,
            when_skip: str,
    ):
        super().__init__()
        self.acs = acs
        self.rm_obj_transition = when_delete
        self.add_obj_transition = when_add
        self.set_params_transition = when_set
        self.skip_transition = when_skip

    def read_msg(self, message: Any) -> AcsReadMsgResult:
        """ Process GetParameterValuesResponse """
        if not isinstance(
                message,
                models.GetParameterValuesResponse,
        ):
            return AcsReadMsgResult(msg_handled=False, next_state=None)

        path_to_val = {}
        if hasattr(message.ParameterList, 'ParameterValueStruct') and \
                message.ParameterList.ParameterValueStruct is not None:
            for param_value_struct in message.ParameterList.ParameterValueStruct:
                path_to_val[param_value_struct.Name] = \
                    param_value_struct.Value.Data
        logger.debug('Received object parameters: %s', str(path_to_val))

        # Number of PLMN objects reported can be incorrect. Let's count them
        num_plmns = 0
        obj_to_params = self.acs.data_model.get_numbered_param_names()
        logger.info('enb obj_to_params= %s', obj_to_params)
        while True:
            obj_name = ParameterName.PLMN_N % (num_plmns + 1)
            if obj_name not in obj_to_params or len(obj_to_params[obj_name]) == 0:
                logger.warning(
                    "eNB has PLMN %s but not defined in model",
                    obj_name,
                )
                break
            param_name_list = obj_to_params[obj_name]
            obj_path = self.acs.data_model.get_parameter(param_name_list[0]).path
            if obj_path not in path_to_val:
                break
            if not self.acs.device_cfg.has_object(obj_name):
                self.acs.device_cfg.add_object(obj_name)
            num_plmns += 1
            for name in param_name_list:
                path = self.acs.data_model.get_parameter(name).path
                value = path_to_val[path]
                magma_val = \
                    self.acs.data_model.transform_for_magma(name, value)
                self.acs.device_cfg.set_parameter_for_object(
                    name, magma_val,
                    obj_name,
                )
        num_plmns_reported = \
            int(self.acs.device_cfg.get_parameter(ParameterName.NUM_PLMNS))
        if num_plmns != num_plmns_reported:
            logger.warning(
                "eNB reported %d PLMNs but found %d",
                num_plmns_reported, num_plmns,
            )
            self.acs.device_cfg.set_parameter(
                ParameterName.NUM_PLMNS,
                num_plmns,
            )
        # Number of Neighbor Freq objects reported can be incorrect. Let's count them
        num_neighbor = 0
        while True:
            obj_name = BaicellsParameterName.NEGIH_FREQ_LIST % (num_neighbor + 1)
            logger.info('enb obj_name= %s', obj_name)
            if obj_name not in obj_to_params or len(obj_to_params[obj_name]) == 0:
                logger.warning(
                    "eNB has Neighbor %s but not defined in model",
                    obj_name,
                )
                break
            param_name_list = obj_to_params[obj_name]
            obj_path = self.acs.data_model.get_parameter(param_name_list[0]).path
            if obj_path not in path_to_val:
                break
            if not self.acs.device_cfg.has_object(obj_name):
                self.acs.device_cfg.add_object(obj_name)
            num_neighbor = num_neighbor + 1
            for name in param_name_list:
                path = self.acs.data_model.get_parameter(name).path
                value = path_to_val[path]
                magma_val = \
                    self.acs.data_model.transform_for_magma(name, value)
                self.acs.device_cfg.set_parameter_for_object(
                    name, magma_val, obj_name,
                )
        num_neighbor_reported = \
            int(self.acs.device_cfg.get_parameter(BaicellsParameterName.NUM_LTE_NEIGHBOR_FREQ))
        if num_neighbor != num_neighbor_reported:
            logger.warning(
                "eNB reported %d Neighbor but found %d",
                num_neighbor_reported, num_neighbor,
            )
            self.acs.device_cfg.set_parameter(
                BaicellsParameterName.NUM_LTE_NEIGHBOR_FREQ,
                num_neighbor,
            )
        # Number of Neighbor Cell objects reported can be incorrect. Let's count them
        num_neighbor_cell = 0
        while True:
            obj_name = BaicellsParameterName.NEIGHBOR_CELL_LIST_N % (num_neighbor_cell + 1)
            if obj_name not in obj_to_params or len(obj_to_params[obj_name]) == 0:
                logger.warning(
                    "eNB has Neighbor %s but not defined in model",
                    obj_name,
                )
                break
            param_name_list = obj_to_params[obj_name]
            obj_path = self.acs.data_model.get_parameter(param_name_list[0]).path
            if obj_path not in path_to_val:
                break
            if not self.acs.device_cfg.has_object(obj_name):
                self.acs.device_cfg.add_object(obj_name)
            num_neighbor_cell = num_neighbor_cell + 1
            for name in param_name_list:
                path = self.acs.data_model.get_parameter(name).path
                value = path_to_val[path]
                magma_val = \
                    self.acs.data_model.transform_for_magma(name, value)
                self.acs.device_cfg.set_parameter_for_object(
                    name, magma_val, obj_name,
                )
        num_neighbor_cell_reported = int(self.acs.device_cfg.get_parameter(BaicellsParameterName.NUM_LTE_NEIGHBOR_CELL))
        if num_neighbor_cell != num_neighbor_cell_reported:
            logger.warning(
                "eNB reported %d neighbor cell but found %d",
                num_neighbor_cell_reported, num_neighbor_cell,
            )
            self.acs.device_cfg.set_parameter(
                BaicellsParameterName.NUM_LTE_NEIGHBOR_CELL,
                num_neighbor_cell,
            )

        # Now we can have the desired state
        if self.acs.desired_cfg is None:
            self.acs.desired_cfg = build_desired_config(
                self.acs.mconfig,
                self.acs.service_config,
                self.acs.device_cfg,
                self.acs.data_model,
                self.acs.config_postprocessor,
            )
        logger.debug('the building desired config is %s', self.acs.desired_cfg.get_object_names())
        logger.debug('the building device_cfg  is------%s-------', self.acs.device_cfg.get_object_names())
        if len(
                get_all_objects_to_delete(
                    self.acs.desired_cfg,
                    self.acs.device_cfg,
                ),
        ) > 0:

            return AcsReadMsgResult(msg_handled=True, next_state=self.rm_obj_transition)
        elif len(
                get_all_objects_to_add(
                    self.acs.desired_cfg,
                    self.acs.device_cfg,
                ),
        ) > 0:
            return AcsReadMsgResult(msg_handled=True, next_state=self.add_obj_transition)
        elif len(
                get_all_param_values_to_set(
                    self.acs.desired_cfg,
                    self.acs.device_cfg,
                    self.acs.data_model,
                ),
        ) > 0:
            return AcsReadMsgResult(msg_handled=True, next_state=self.set_params_transition)
        return AcsReadMsgResult(msg_handled=True, next_state=self.skip_transition)

    def state_description(self) -> str:
        return 'Getting object parameters'


class BaicellsDeleteObjectsState(EnodebAcsState):
    def __init__(
            self,
            acs: EnodebAcsStateMachine,
            when_add: str,
            when_skip: str,
    ):
        super().__init__()
        self.acs = acs
        self.deleted_param = None
        self.add_obj_transition = when_add
        self.skip_transition = when_skip

    def get_msg(self, message: Any) -> AcsMsgAndTransition:
        """
        Send DeleteObject message to TR-069 and poll for response(s).
        Input:
            - Object name (string)
            - message
        - return
        """
        request = models.DeleteObject()
        self.deleted_param = get_all_objects_to_delete(
            self.acs.desired_cfg,
            self.acs.device_cfg,
        )[0]
        logger.debug('get obj to delete %s', self.deleted_param)
        request.ObjectName = \
            self.acs.data_model.get_parameter(self.deleted_param).path
        return AcsMsgAndTransition(request, None)

    def read_msg(self, message: Any) -> AcsReadMsgResult:
        """
        Send DeleteObject message to TR-069 and poll for response(s).
        Input:
            - Object name (string)
        """
        if isinstance(message, models.DeleteObjectResponse):
            if message.Status != 0:
                raise Tr069Error(
                    'Received DeleteObjectResponse with '
                    'Status=%d' % message.Status,
                )
        elif isinstance(message, models.Fault):
            raise Tr069Error(
                'Received Fault in response to DeleteObject '
                '(faultstring = %s)' % message.FaultString,
            )
        else:
            return AcsReadMsgResult(msg_handled=False, next_state=None)

        self.acs.device_cfg.delete_object(self.deleted_param)
        obj_list_to_delete = get_all_objects_to_delete(
            self.acs.desired_cfg,
            self.acs.device_cfg,
        )
        if len(obj_list_to_delete) > 0:
            return AcsReadMsgResult(True, None)
        if len(
                get_all_objects_to_add(
                    self.acs.desired_cfg,
                    self.acs.device_cfg,
                ),
        ) == 0:
            return AcsReadMsgResult(True, self.skip_transition)
        return AcsReadMsgResult(True, self.add_obj_transition)

    def state_description(self) -> str:
        return 'Deleting objects'


class BaicellsGetObjectParametersState(EnodebAcsState):
    def __init__(self, acs: EnodebAcsStateMachine, when_done: str, request_all_params: bool = False):
        super().__init__()
        self.acs = acs
        self.done_transition = when_done
        self.request_all_params = request_all_params

    def get_msg(self, message: Any) -> AcsMsgAndTransition:
        """ Respond with GetParameterValuesRequest """
        names = get_object_params_to_get(
            self.acs.desired_cfg,
            self.acs.device_cfg,
            self.acs.data_model,
            self.request_all_params,
        )

        # Generate the request
        request = models.GetParameterValues()
        request.ParameterNames = models.ParameterNames()
        request.ParameterNames.arrayType = 'xsd:string[%d]' \
                                           % len(names)
        request.ParameterNames.string = []
        for name in names:
            path = self.acs.data_model.get_parameter(name).path
            request.ParameterNames.string.append(path)

        return AcsMsgAndTransition(request, self.done_transition)

    def state_description(self) -> str:
        return 'Getting object parameters'


class BaicellsWaitGetTransientParametersState(EnodebAcsState):
    """
    Periodically read eNodeB status. Note: keep frequency low to avoid
    backing up large numbers of read operations if enodebd is busy
    """

    def __init__(
            self,
            acs: EnodebAcsStateMachine,
            when_get: str,
            when_get_obj_params: str,
            when_delete: str,
            when_add: str,
            when_set: str,
            when_skip: str,
            request_all_params: bool = False,
    ):
        super().__init__()
        self.acs = acs
        self.done_transition = when_get
        self.get_obj_params_transition = when_get_obj_params
        self.rm_obj_transition = when_delete
        self.add_obj_transition = when_add
        self.set_transition = when_set
        self.skip_transition = when_skip
        self.request_all_params = request_all_params

    def read_msg(self, message: Any) -> AcsReadMsgResult:
        if not isinstance(message, models.GetParameterValuesResponse):
            return AcsReadMsgResult(False, None)
        # Current values of the fetched parameters
        name_to_val = parse_get_parameter_values_response(
            self.acs.data_model,
            message,
        )
        logger.debug('Fetched Transient Params: %s', str(name_to_val))

        # Update device configuration
        for name in name_to_val:
            magma_val = \
                self.acs.data_model.transform_for_magma(
                    name,
                    name_to_val[name],
                )
            self.acs.device_cfg.set_parameter(name, magma_val)

        return AcsReadMsgResult(True, self.get_next_state())

    def get_next_state(self) -> str:
        should_get_params = \
            len(
                get_params_to_get(
                    self.acs.device_cfg,
                    self.acs.data_model,
                    request_all_params=self.request_all_params,
                ),
            ) > 0
        if should_get_params:
            return self.done_transition
        should_get_obj_params = \
            len(
                get_object_params_to_get(
                    self.acs.desired_cfg,
                    self.acs.device_cfg,
                    self.acs.data_model,
                ),
            ) > 0
        if should_get_obj_params:
            return self.get_obj_params_transition
        elif len(
            get_all_objects_to_delete(
                self.acs.desired_cfg,
                self.acs.device_cfg,
            ),
        ) > 0:
            return self.rm_obj_transition
        elif len(
            get_all_objects_to_add(
                self.acs.desired_cfg,
                self.acs.device_cfg,
            ),
        ) > 0:
            return self.add_obj_transition
        return self.skip_transition

    def state_description(self) -> str:
        return 'Getting transient read-only parameters'


def get_object_params_to_get(
        desired_cfg: Optional[EnodebConfiguration],
        device_cfg: EnodebConfiguration,
        data_model: DataModel,
        request_all_params: bool = False,
) -> List[ParameterName]:
    """
     - data_model
     - desired_cfg
     - device_cfg
     - return Returns a list of parameter names for object parameters we don't know the
    current value of
    """
    names = []
    # TODO: This might a string for some strange reason, investigate why
    num_plmns = \
        int(device_cfg.get_parameter(ParameterName.NUM_PLMNS))
    for i in range(1, num_plmns + 1):
        obj_name = ParameterName.PLMN_N % i
        if not device_cfg.has_object(obj_name):
            device_cfg.add_object(obj_name)
        obj_to_params = data_model.get_numbered_param_names()
        desired = obj_to_params[obj_name]
        if request_all_params:
            names += desired
        else:
            current = []
            if desired_cfg is not None:
                current = desired_cfg.get_parameter_names_for_object(obj_name)
            names_to_add = list(set(desired) - set(current))
            names = names + names_to_add
    num_neighbor_freq = int(device_cfg.get_parameter(BaicellsParameterName.NUM_LTE_NEIGHBOR_FREQ))
    for i in range(1, num_neighbor_freq + 1):
        obj_name = BaicellsParameterName.NEGIH_FREQ_LIST % i
        if not device_cfg.has_object(obj_name):
            device_cfg.add_object(obj_name)
        obj_to_params = data_model.get_numbered_param_names()
        desired = obj_to_params[obj_name]
        if request_all_params:
            names += desired
        else:
            current = []
            if desired_cfg is not None and desired_cfg.has_object():
                current = desired_cfg.get_parameter_names_for_object(obj_name)
            names_to_add = list(set(desired) - set(current))
            names = names + names_to_add
    num_neighbor_cell = int(device_cfg.get_parameter(BaicellsParameterName.NUM_LTE_NEIGHBOR_CELL))
    for i in range(1, num_neighbor_cell + 1):
        obj_name = BaicellsParameterName.NEIGHBOR_CELL_LIST_N % i
        if not device_cfg.has_object(obj_name):
            device_cfg.add_object(obj_name)
        obj_to_params = data_model.get_numbered_param_names()
        desired = obj_to_params[obj_name]
        if request_all_params:
            names += desired
        else:
            current = []
            if desired_cfg is not None and desired_cfg.has_object(obj_name):
                current = desired_cfg.get_parameter_names_for_object(obj_name)
            names_to_add = list(set(desired) - set(current))
            names = names + names_to_add
    return names


class BaicellsAddObjectsState(EnodebAcsState):
    def __init__(self, acs: EnodebAcsStateMachine, when_done: str):
        super().__init__()
        self.acs = acs
        self.done_transition = when_done
        self.added_param = None

    def get_msg(self, message: Any) -> AcsMsgAndTransition:
        request = models.AddObject()
        self.added_param = get_all_objects_to_add(
            self.acs.desired_cfg,
            self.acs.device_cfg,
        )[0]
        desired_param = self.acs.data_model.get_parameter(self.added_param)
        desired_path = desired_param.path
        path_parts = desired_path.split('.')
        # If adding enumerated object, ie. XX.N. we should add it to the
        # parent object XX. so strip the index
        if len(path_parts) > 2 and \
                path_parts[-1] == '' and path_parts[-2].isnumeric():
            logger.debug('Stripping index from path=%s', desired_path)
            desired_path = '.'.join(path_parts[:-2]) + '.'
        request.ObjectName = desired_path
        return AcsMsgAndTransition(request, None)

    def read_msg(self, message: Any) -> AcsReadMsgResult:
        if isinstance(message, models.AddObjectResponse):
            if message.Status != 0:
                raise Tr069Error(
                    'Received AddObjectResponse with '
                    'Status=%d' % message.Status,
                )
        elif isinstance(message, models.Fault):
            raise Tr069Error(
                'Received Fault in response to AddObject '
                '(faultstring = %s)' % message.FaultString,
            )
        else:
            return AcsReadMsgResult(msg_handled=False, next_state=None)
        instance_n = message.InstanceNumber
        self.added_param = re.sub(r'\d', str(instance_n), self.added_param)
        self.acs.device_cfg.add_object(self.added_param)
        obj_list_to_add = get_all_objects_to_add(
            self.acs.desired_cfg,
            self.acs.device_cfg,
        )
        if len(obj_list_to_add) > 0:
            return AcsReadMsgResult(msg_handled=True, next_state=None)
        return AcsReadMsgResult(msg_handled=True, next_state=self.done_transition)

    def state_description(self) -> str:
        return 'Adding objects'
