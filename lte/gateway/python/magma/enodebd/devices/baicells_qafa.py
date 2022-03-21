"""
Copyright 2020 The Magma Authors.

This source code is licensed under the BSD-style license found in the
LICENSE file in the root directory of this source tree.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import Any, Callable, Dict, List, Optional, Type

from magma.common.service import MagmaService
from magma.enodebd.data_models import transform_for_enb, transform_for_magma
from magma.enodebd.data_models.data_model import (
    DataModel,
    InvalidTrParamPath,
    TrParam,
)
from magma.enodebd.data_models.data_model_parameters import (
    BaicellsParameterName,
    ParameterName,
    TrParameterType,
)
from magma.enodebd.device_config.enodeb_config_postprocessor import (
    EnodebConfigurationPostProcessor,
)
from magma.enodebd.device_config.enodeb_configuration import EnodebConfiguration
from magma.enodebd.devices.baicells_qafb import (
    BaicellsQafbGetObjectParametersState,
    BaicellsQafbWaitGetTransientParametersState,
)
from magma.enodebd.devices.device_utils import EnodebDeviceName
from magma.enodebd.state_machines.enb_acs_impl import BasicEnodebAcsStateMachine
from magma.enodebd.state_machines.enb_acs_states import (
    AddObjectsState,
    DeleteObjectsState,
    EnbSendDownloadState,
    EnbSendRebootState,
    EndSessionState,
    EnodebAcsState,
    ErrorState,
    GetParametersState,
    GetRPCMethodsState,
    SendFactoryResetState,
    SendGetTransientParametersState,
    SetParameterValuesState,
    WaitDownloadResponseState,
    WaitEmptyMessageState,
    WaitFactoryResetResponseState,
    WaitGetParametersState,
    WaitInformMRebootState,
    WaitInformState,
    WaitRebootResponseState,
    WaitSetParameterValuesState,
)


class BaicellsQAFAHandler(BasicEnodebAcsStateMachine):
    def __init__(
        self,
        service: MagmaService,
    ) -> None:
        self._state_map = {}
        super().__init__(service=service, use_param_key=False)

    def reboot_asap(self) -> None:
        self.transition('reboot')

    def download_asap(
        self, url: str, user_name: str, password: str, target_file_name: str, file_size: int,
        md5: str,
    ) -> None:
        if url is not None:
            self.desired_cfg.set_parameter(ParameterName.DOWNLOAD_URL, url)
            self.desired_cfg.set_parameter(ParameterName.DOWNLOAD_USER, user_name)
            self.desired_cfg.set_parameter(ParameterName.DOWNLOAD_PASSWORD, password)
            self.desired_cfg.set_parameter(ParameterName.DOWNLOAD_FILENAME, target_file_name)
            self.desired_cfg.set_parameter(ParameterName.DOWNLOAD_FILESIZE, file_size)
            self.desired_cfg.set_parameter(ParameterName.DOWNLOAD_MD5, md5)
        self.transition('download')

    def factory_reset_asap(self) -> None:
        """
        Impl to send a request to factoryRest the eNodeB ASAP
        The eNB will factory reset from this method.
        """
        self.transition('factory_reset')

    def is_enodeb_connected(self) -> bool:
        return not isinstance(self.state, WaitInformState)

    def _init_state_map(self) -> None:
        self._state_map = {
            'wait_inform': WaitInformState(self, when_done='get_rpc_methods'),
            'get_rpc_methods': GetRPCMethodsState(self, when_done='wait_empty', when_skip='get_transient_params'),
            'wait_empty': WaitEmptyMessageState(self, when_done='get_transient_params'),
            'get_transient_params': SendGetTransientParametersState(self, when_done='wait_get_transient_params'),
            'wait_get_transient_params': BaicellsQafbWaitGetTransientParametersState(self, when_get='get_params', when_get_obj_params='get_obj_params', when_delete='delete_objs', when_add='add_objs', when_set='set_params', when_skip='end_session'),
            'get_params': GetParametersState(self, when_done='wait_get_params'),
            'wait_get_params': WaitGetParametersState(self, when_done='get_obj_params'),
            'get_obj_params': BaicellsQafbGetObjectParametersState(self, when_delete='delete_objs', when_add='add_objs', when_set='set_params', when_skip='end_session'),
            'delete_objs': DeleteObjectsState(self, when_add='add_objs', when_skip='set_params'),
            'add_objs': AddObjectsState(self, when_done='set_params'),
            'set_params': SetParameterValuesState(self, when_done='wait_set_params'),
            'wait_set_params': WaitSetParameterValuesState(self, when_done='check_get_params', when_apply_invasive='check_get_params'),
            'check_get_params': GetParametersState(self, when_done='check_wait_get_params', request_all_params=True),
            'check_wait_get_params': WaitGetParametersState(self, when_done='end_session'),
            'end_session': EndSessionState(self),
            # These states are only entered through manual user intervention
            'reboot': EnbSendRebootState(self, when_done='wait_reboot'),
            'wait_reboot': WaitRebootResponseState(self, when_done='wait_post_reboot_inform'),
            'wait_post_reboot_inform': WaitInformMRebootState(self, when_done='wait_empty', when_timeout='wait_inform'),
            'download': EnbSendDownloadState(self, when_done='wait_download'),
            'wait_download': WaitDownloadResponseState(self, when_done='wait_inform_post_download'),
            'wait_inform_post_download': WaitInformState(self, when_done='wait_empty_post_download', when_boot=None),
            'wait_empty_post_download': WaitEmptyMessageState(
                self, when_done='get_transient_params',
                when_missing='check_optional_params',
            ),
            'factory_reset': SendFactoryResetState(self, when_done='wait_factory_reset'),
            'wait_factory_reset': WaitFactoryResetResponseState(self, when_done='wait_inform'),

            # The states below are entered when an unexpected message type is
            # received
            'unexpected_fault': ErrorState(self, inform_transition_target='wait_inform'),
        }

    @property
    def device_name(self) -> str:
        return EnodebDeviceName.BAICELLS_QAFA

    @property
    def data_model_class(self) -> Type[DataModel]:
        return BaicellsQAFATrDataModel

    @property
    def config_postprocessor(self) -> EnodebConfigurationPostProcessor:
        return BaicellsQAFATrConfigurationInitializer()

    @property
    def state_map(self) -> Dict[str, EnodebAcsState]:
        return self._state_map

    @property
    def disconnected_state_name(self) -> str:
        return 'wait_inform'

    @property
    def unexpected_fault_state_name(self) -> str:
        return 'unexpected_fault'


class BaicellsQAFATrDataModel(DataModel):
    """
    Class to represent relevant data model parameters from TR-196/TR-098.
    This class is effectively read-only.

    This model specifically targets Qualcomm-based BaiCells units running
    QAFA firmware.

    These models have these idiosyncrasies (on account of running TR098):

    - Parameter content root is different (InternetGatewayDevice)
    - GetParameter queries with a wildcard e.g. InternetGatewayDevice. do
      not respond with the full tree (we have to query all parameters)
    - MME status is not exposed - we assume the MME is connected if
      the eNodeB is transmitting (OpState=true)
    - Parameters such as band capability/duplex config
      are rooted under `boardconf.` and not the device config root
    - Parameters like Admin state, CellReservedForOperatorUse,
      Duplex mode, DL bandwidth and Band capability have different
      formats from Intel-based Baicells units, necessitating,
      formatting before configuration and transforming values
      read from eNodeB state.
    - Num PLMNs is not reported by these units
    """
    # Parameters to query when reading eNodeB config
    LOAD_PARAMETERS = [ParameterName.DEVICE]
    # Mapping of TR parameter paths to aliases
    DEVICE_PATH = 'InternetGatewayDevice.'
    FAPSERVICE_PATH = DEVICE_PATH + 'Services.FAPService.1.'
    EEPROM_PATH = 'boardconf.status.eepromInfo.'
    PARAMETERS = {
        # Top-level objects
        ParameterName.DEVICE: TrParam(
            path=DEVICE_PATH,
            is_invasive=True, type=TrParameterType.OBJECT, is_optional=False,
        ),
        ParameterName.FAP_SERVICE: TrParam(
            path=FAPSERVICE_PATH,
            is_invasive=True, type=TrParameterType.OBJECT, is_optional=False,
        ),

        # Device info parameters
        # Qualcomm units do not expose MME_Status (We assume that the eNB is broadcasting state is connected to the MME)
        ParameterName.MME_STATUS: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.OpState',
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.GPS_LAT: TrParam(
            DEVICE_PATH + 'DeviceInfo.X_BAICELLS_COM_Latitude',
            True, TrParameterType.INT, True,
        ),
        ParameterName.GPS_LONG: TrParam(
            DEVICE_PATH + 'DeviceInfo.X_BAICELLS_COM_Longitude',
            True, TrParameterType.INT, True,
        ),
        ParameterName.GPS_ALTI: TrParam(
            DEVICE_PATH + 'DeviceInfo.X_BAICELLS_COM_Height',
            True, TrParameterType.STRING, True,
        ),
        ParameterName.SW_VERSION: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SoftwareVersion',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.SERIAL_NUMBER: TrParam(
            path=DEVICE_PATH + 'DeviceInfo.SerialNumber',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.VENDOR: TrParam(
            DEVICE_PATH + 'DeviceInfo.ManufacturerOUI',
            False, TrParameterType.STRING, True,
        ),
        ParameterName.MODEL_NAME: TrParam(
            DEVICE_PATH + 'DeviceInfo.ModelName',
            False, TrParameterType.STRING, True,
        ),
        ParameterName.RF_STATE: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.X_BAICELLS_COM_RadioEnable',
            True, TrParameterType.BOOLEAN, False,
        ),
        ParameterName.UPTIME: TrParam(
            DEVICE_PATH + 'DeviceInfo.X_BAICELLS_COM_STATION_RUN_Time',
            False, TrParameterType.STRING, True,
        ),

        # Capabilities
        ParameterName.DUPLEX_MODE_CAPABILITY: TrParam(
            path=EEPROM_PATH + 'div_multiple',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.BAND_CAPABILITY: TrParam(
            path=EEPROM_PATH + 'work_mode',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),

        # RF-related parameters
        ParameterName.EARFCNDL: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.EARFCNDL',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.PCI: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.PhyCellID',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.DL_BANDWIDTH: TrParam(
            path=DEVICE_PATH + 'Services.RfConfig.1.RfCarrierCommon.carrierBwMhz',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.SUBFRAME_ASSIGNMENT: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.PHY.TDDFrame.SubFrameAssignment',
            is_invasive=True, type='bool', is_optional=False,
        ),
        ParameterName.SPECIAL_SUBFRAME_PATTERN: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.PHY.TDDFrame.SpecialSubframePatterns',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.CELL_ID: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Common.CellIdentity',
            is_invasive=True, type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),

        # Other LTE parameters
        ParameterName.ADMIN_STATE: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.AdminState',
            is_invasive=False, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.OP_STATE: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.OpState',
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.RF_TX_STATUS: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.OpState',
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        ),

        # RAN parameters
        BaicellsParameterName.X2_ENABLE_DISABLE: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.X_QUALCOMM_ULTRASON_CONFIG.SelfConfig.X2ConnectionEnabled',
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        ),

        # Core network parameters
        ParameterName.MME_IP: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.Gateway.S1SigLinkServerList',
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.MME_PORT: TrParam(
            path=FAPSERVICE_PATH + 'FAPControl.LTE.Gateway.S1SigLinkPort',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        # This parameter is standard but doesn't exist
        # ParameterName.NUM_PLMNS: TrParam(FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNListNumberOfEntries', True, TrParameterType.INT, False),
        ParameterName.TAC: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.TAC',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.IP_SEC_ENABLE: TrParam(
            path='boardconf.ipsec.ipsecConfig.onBoot',
            is_invasive=False, type=TrParameterType.BOOLEAN, is_optional=False,
        ),

        # Management server parameters
        ParameterName.PERIODIC_INFORM_ENABLE: TrParam(
            path=DEVICE_PATH + 'ManagementServer.PeriodicInformEnable',
            is_invasive=False, type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.PERIODIC_INFORM_INTERVAL: TrParam(
            path=DEVICE_PATH + 'ManagementServer.PeriodicInformInterval',
            is_invasive=False, type=TrParameterType.INT, is_optional=False,
        ),

        # Performance management parameters
        ParameterName.PERF_MGMT_ENABLE: TrParam(
            path=DEVICE_PATH + 'FAP.PerfMgmt.Config.Enable',
            is_invasive=False, type=TrParameterType.BOOLEAN, is_optional=False,
        ),
        ParameterName.PERF_MGMT_UPLOAD_INTERVAL: TrParam(
            path=DEVICE_PATH + 'FAP.PerfMgmt.Config.PeriodicUploadInterval',
            is_invasive=False, type=TrParameterType.INT, is_optional=False,
        ),
        ParameterName.PERF_MGMT_UPLOAD_URL: TrParam(
            path=DEVICE_PATH + 'FAP.PerfMgmt.Config.URL',
            is_invasive=False, type=TrParameterType.STRING, is_optional=False,
        ),

        # download params that don't have tr69 representation.
        ParameterName.DOWNLOAD_URL: TrParam(
            path=InvalidTrParamPath,
            is_invasive=False, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.DOWNLOAD_USER: TrParam(
            path=InvalidTrParamPath,
            is_invasive=False, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.DOWNLOAD_PASSWORD: TrParam(
            path=InvalidTrParamPath,
            is_invasive=False, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.DOWNLOAD_FILENAME: TrParam(
            path=InvalidTrParamPath,
            is_invasive=False, type=TrParameterType.STRING, is_optional=False,
        ),
        ParameterName.DOWNLOAD_FILESIZE: TrParam(
            path=InvalidTrParamPath,
            is_invasive=False, type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),
        ParameterName.DOWNLOAD_MD5: TrParam(
            path=InvalidTrParamPath,
            is_invasive=False, type=TrParameterType.STRING, is_optional=False,
        ),

        # Radio Power config
        BaicellsParameterName.REFERENCE_SIGNAL_POWER: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.RF.ReferenceSignalPower',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        BaicellsParameterName.POWER_CLASS: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.X_QUALCOMM_EXPANDED_POWER_PARAMS.MaxTxPowerExpanded',
            is_invasive=True, type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),
        BaicellsParameterName.PA: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.PHY.PDSCH.Pa',
            is_invasive=True, type=TrParameterType.INT, is_optional=False,
        ),
        BaicellsParameterName.PB: TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.RAN.PHY.PDSCH.Pb',
            is_invasive=True, type=TrParameterType.UNSIGNED_INT, is_optional=False,
        ),

        # Management server
        BaicellsParameterName.MANAGEMENT_SERVER:
            TrParam('Device.ManagementServer.URL', True, TrParameterType.STRING, False),
        BaicellsParameterName.MANAGEMENT_SERVER_PORT:
            TrParam('Device.ManagementServer.tr069_port', True, TrParameterType.INT, False),
        BaicellsParameterName.MANAGEMENT_SERVER_SSL_ENABLE:
            TrParam('Device.ManagementServer.ssl_enable', True, TrParameterType.BOOLEAN, False),

        # SYNC
        BaicellsParameterName.SYNC_1588_SWITCH:
            TrParam('Device.DeviceInfo.X_BAICELLS_COM_1588SyncEnable', True, TrParameterType.BOOLEAN, False),
        BaicellsParameterName.SYNC_1588_DOMAIN:
            TrParam('Device.DeviceInfo.X_COM_1588Domain_Num', True, TrParameterType.INT, False),
        BaicellsParameterName.SYNC_1588_SYNC_MSG_INTREVAL:
            TrParam('Device.DeviceInfo.X_COM_1588Sync_Message_Interval', True, TrParameterType.INT, False),
        BaicellsParameterName.SYNC_1588_DELAY_REQUEST_MSG_INTERVAL:
            TrParam('Device.DeviceInfo.X_COM_1588Delay_Request_Message_Interval', True, TrParameterType.INT, False),
        BaicellsParameterName.SYNC_1588_HOLDOVER:
            TrParam('Device.DeviceInfo.X_COM_1588Holdover', True, TrParameterType.INT, False),
        BaicellsParameterName.SYNC_1588_ASYMMETRY:
            TrParam('Device.DeviceInfo.X_COM_1588Asymmetry_Value', True, TrParameterType.INT, False),
        BaicellsParameterName.SYNC_1588_UNICAST_ENABLE:
            TrParam('Device.DeviceInfo.X_COM_1588Unicast_Switch', True, TrParameterType.INT, False),
        BaicellsParameterName.SYNC_1588_UNICAST_SERVERIP:
            TrParam('Device.DeviceInfo.X_COM_1588Unicast_IpAddr', True, TrParameterType.STRING, False),

        # Ho algorithm
        BaicellsParameterName.HO_A1_THRESHOLD_RSRP: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.ConnMode.EUTRA.A1ThresholdRSRP', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_A2_THRESHOLD_RSRP: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.ConnMode.EUTRA.A2ThresholdRSRP', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_A3_OFFSET: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.HOVA3Offset', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_A3_OFFSET_ANR: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.ANR.AnrA3Offset', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_A4_THRESHOLD_RSRP: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.LTE.RAN.Mobility.ConnMode.EUTRA.A4ThresholdRSRP', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_LTE_INTRA_A5_THRESHOLD_1_RSRP: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.HOVInterA5Threshold1RSRP', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_LTE_INTRA_A5_THRESHOLD_2_RSRP: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.HOVInterA5Threshold2RSRP', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_LTE_INTER_ANR_A5_THRESHOLD_1_RSRP: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.ANR.InterAnrA5Threshold1RSRP', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_LTE_INTER_ANR_A5_THRESHOLD_2_RSRP: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.ANR.InterAnrA5Threshold2RSRP', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_B2_THRESHOLD1_RSRP: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.IRAT.B2threshold1RsrpHO', True, TrParameterType.UNSIGNED_INT,
            False,
        ),
        BaicellsParameterName.HO_B2_THRESHOLD2_RSRP: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.ConnMode.IRAT.X_BAICELLS_COM_UTRANTDD.B2Threshold2UTRATDDRSCP',
            True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_B2_GERAN_IRAT_THRESHOLD: TrParam(
            FAPSERVICE_PATH + 'X_BAICELLS.COM.LTE.IRAT.B2Threshold2Geran', True, TrParameterType.UNSIGNED_INT,
            False,
        ),
        BaicellsParameterName.HO_QRXLEVMIN_SELECTION: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.IntraFreq.QRxLevMinSIB1', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_QRXLEVMINOFFSET: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.IntraFreq.QRxLevMinOffset', True,
            TrParameterType.UNSIGNED_INT,
            False,
        ),
        BaicellsParameterName.HO_S_INTRASEARCH: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.IntraFreq.SIntraSearch', True,
            TrParameterType.UNSIGNED_INT,
            False,
        ),
        BaicellsParameterName.HO_S_NONINTRASEARCH: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.IntraFreq.SNonIntraSearch', True,
            TrParameterType.UNSIGNED_INT,
            False,
        ),
        BaicellsParameterName.HO_QRXLEVMIN_RESELECTION: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.IntraFreq.QRxLevMinSIB3', True, TrParameterType.INT,
            False,
        ),
        BaicellsParameterName.HO_RESELECTION_PRIORITY: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.IntraFreq.CellReselectionPriority', True,
            TrParameterType.UNSIGNED_INT,
            False,
        ),
        BaicellsParameterName.HO_THRESHSERVINGLOW: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.RAN.Mobility.IdleMode.IntraFreq.ThreshServingLow', True,
            TrParameterType.UNSIGNED_INT,
            False,
        ),
        BaicellsParameterName.HO_CIPHERING_ALGORITHM: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.EPC.AllowedCipheringAlgorithmList', True, TrParameterType.STRING,
            False,
        ),
        BaicellsParameterName.HO_INTEGRITY_ALGORITHM: TrParam(
            FAPSERVICE_PATH + 'CellConfig.LTE.EPC.AllowedIntegrityProtectionAlgorithmList', True,
            TrParameterType.STRING,
            False,
        ),
    }

    NUM_PLMNS_IN_CONFIG = 6
    TRANSFORMS_FOR_ENB = {
        ParameterName.CELL_BARRED: transform_for_enb.invert_cell_barred,
    }
    for i in range(1, NUM_PLMNS_IN_CONFIG + 1):
        TRANSFORMS_FOR_ENB[ParameterName.PLMN_N_CELL_RESERVED % i] = transform_for_enb.cell_reserved
        PARAMETERS[ParameterName.PLMN_N % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.' % i,
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_CELL_RESERVED % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.CellReservedForOperatorUse' % i,
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_ENABLE % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.Enable' % i,
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_PRIMARY % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.IsPrimary' % i,
            is_invasive=True, type=TrParameterType.BOOLEAN, is_optional=False,
        )
        PARAMETERS[ParameterName.PLMN_N_PLMNID % i] = TrParam(
            path=FAPSERVICE_PATH + 'CellConfig.LTE.EPC.PLMNList.%d.PLMNID' % i,
            is_invasive=True, type=TrParameterType.STRING, is_optional=False,
        )

    TRANSFORMS_FOR_ENB[ParameterName.ADMIN_STATE] = transform_for_enb.admin_state
    TRANSFORMS_FOR_MAGMA = {
        # We don't set these parameters
        ParameterName.BAND_CAPABILITY: transform_for_magma.band_capability,
        ParameterName.DUPLEX_MODE_CAPABILITY: transform_for_magma.duplex_mode,
    }

    @classmethod
    def get_parameter(cls, param_name: ParameterName) -> Optional[TrParam]:
        return cls.PARAMETERS.get(param_name)

    @classmethod
    def _get_magma_transforms(
        cls,
    ) -> Dict[ParameterName, Callable[[Any], Any]]:
        return cls.TRANSFORMS_FOR_MAGMA

    @classmethod
    def _get_enb_transforms(cls) -> Dict[ParameterName, Callable[[Any], Any]]:
        return cls.TRANSFORMS_FOR_ENB

    @classmethod
    def get_load_parameters(cls) -> List[ParameterName]:
        """
        Load all the parameters instead of a subset.
        """
        return list(cls.PARAMETERS.keys())

    @classmethod
    def get_num_plmns(cls) -> int:
        return cls.NUM_PLMNS_IN_CONFIG

    @classmethod
    def get_parameter_names(cls) -> List[ParameterName]:
        excluded_params = [
            str(ParameterName.DEVICE),
            str(ParameterName.FAP_SERVICE),
        ]
        names = list(
            filter(
                lambda x: (not str(x).startswith('PLMN')) and (not str(x).startswith('Download')) and (
                    str(x) not in excluded_params
                ), cls.PARAMETERS.keys(),
            ),
        )
        return names

    @classmethod
    def get_numbered_param_names(
        cls,
    ) -> Dict[ParameterName, List[ParameterName]]:
        names = {}
        for i in range(1, cls.NUM_PLMNS_IN_CONFIG + 1):
            params = []
            params.append(ParameterName.PLMN_N_CELL_RESERVED % i)
            params.append(ParameterName.PLMN_N_ENABLE % i)
            params.append(ParameterName.PLMN_N_PRIMARY % i)
            params.append(ParameterName.PLMN_N_PLMNID % i)
            names[ParameterName.PLMN_N % i] = params

        return names


class BaicellsQAFATrConfigurationInitializer(EnodebConfigurationPostProcessor):
    def postprocess(self, mconfig: Any, service_cfg: Any, desired_cfg: EnodebConfiguration) -> None:

        desired_cfg.delete_parameter(ParameterName.ADMIN_STATE)
        desired_cfg.set_parameter(ParameterName.PERF_MGMT_UPLOAD_INTERVAL, 900)
