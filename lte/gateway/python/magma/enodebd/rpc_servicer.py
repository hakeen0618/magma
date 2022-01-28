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

from typing import Any

import grpc
from lte.protos.enodebd_pb2 import (
    AllEnodebStatus,
    DownloadRequest,
    DownloadResponse,
    EnodebIdentity,
    GetParameterRequest,
    GetParameterResponse,
    SetParameterRequest,
    SingleEnodebStatus,
)
from lte.protos.enodebd_pb2_grpc import (
    EnodebdServicer,
    add_EnodebdServicer_to_server,
)
from magma.common.rpc_utils import print_grpc, return_void
from magma.enodebd.enodeb_status import (
    get_service_status,
    get_single_enb_status,
)
from magma.enodebd.state_machines.enb_acs import EnodebAcsStateMachine
from magma.enodebd.state_machines.enb_acs_manager import StateMachineManager
from orc8r.protos.common_pb2 import Void
from orc8r.protos.service303_pb2 import ServiceStatus


class EnodebdRpcServicer(EnodebdServicer):
    """ gRPC based server for enodebd """

    def __init__(
        self, state_machine_manager: StateMachineManager,
        print_grpc_payload: bool = False,
    ) -> None:
        self.state_machine_manager = state_machine_manager
        self._print_grpc_payload = print_grpc_payload

    def add_to_server(self, server) -> None:
        """
        Add the servicer to a gRPC server
        """
        add_EnodebdServicer_to_server(self, server)

    def _get_handler(self, device_serial: str) -> EnodebAcsStateMachine:
        return self.state_machine_manager.get_handler_by_serial(device_serial)

    def GetParameter(
            self,
            request: GetParameterRequest,
            context: Any,
    ) -> GetParameterResponse:
        """
        Sends a GetParameterValues message. Used for testing only.

        Different data models will have different names for the same
        parameter. Whatever name that the data model uses, we call the
        'parameter path', eg. "Device.DeviceInfo.X_BAICELLS_COM_GPS_Status"
        We denote 'ParameterName' to be a standard string name for
        equivalent parameters between different data models
        """
        print_grpc(
            request, self._print_grpc_payload,
            "GetParameter Request:",
        )
        # Get the parameter value information
        parameter_path = request.parameter_name
        handler = self._get_handler(request.device_serial)
        data_model = handler.data_model
        param_name = data_model.get_parameter_name_from_path(parameter_path)
        param_value = str(handler.get_parameter(param_name))

        # And now construct the response to the rpc request
        get_parameter_values_response = GetParameterResponse()
        get_parameter_values_response.parameters.add(
            name=parameter_path, value=param_value,
        )
        print_grpc(
            get_parameter_values_response, self._print_grpc_payload,
            "GetParameter Response:",
        )
        return get_parameter_values_response

    @return_void
    def SetParameter(self, request: SetParameterRequest, context: Any) -> None:
        """
        Sends a SetParameterValues message. Used for testing only.

        Different data models will have different names for the same
        parameter. Whatever name that the data model uses, we call the
        'parameter path', eg. "Device.DeviceInfo.X_BAICELLS_COM_GPS_Status"
        We denote 'ParameterName' to be a standard string name for
        equivalent parameters between different data models
        """
        print_grpc(
            request, self._print_grpc_payload,
            "SetParameter Request:",
        )
        # Parse the request
        if request.HasField('value_int'):
            value = (request.value_int, 'int')
        elif request.HasField('value_bool'):
            value = (request.value_bool, 'boolean')
        elif request.HasField('value_string'):
            value = (request.value_string, 'string')
        else:
            context.set_details(
                'SetParameter: Unsupported type %d',
                request.type,
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return

        # Update the handler so it will set the parameter value
        parameter_path = request.parameter_name
        handler = self._get_handler(request.device_serial)
        data_model = handler.data_model
        param_name = data_model.get_parameter_name_from_path(parameter_path)
        handler.set_parameter_asap(param_name, value)

    @return_void
    def Reboot(self, request: EnodebIdentity, context=None) -> None:
        """ Reboot eNodeB """
        print_grpc(
            request, self._print_grpc_payload,
            "Reboot Request:",
        )
        handler = self._get_handler(request.device_serial)
        handler.reboot_asap()

    @return_void
    def RebootAll(self, _=None, context=None) -> None:
        """ Reboot all connected eNodeB devices """
        print_grpc(
            Void(), self._print_grpc_payload,
            "RebootAll Request:",
        )
        serial_list = self.state_machine_manager.get_connected_serial_id_list()
        for enb_serial in serial_list:
            handler = self._get_handler(enb_serial)
            handler.reboot_asap()

    def Download(self, request: DownloadRequest, context: Any) -> DownloadResponse:
        """ Download file and upgrade the eNodeB """
        url = request.url
        user_name = request.user_name
        password = request.password
        target_file_name = request.target_file_name
        file_size = int(request.file_size)
        md5 = request.md5
        download_resp = DownloadResponse()
        handler = self._get_handler(request.device_serial)
        handler.download_asap(
            url=url, user_name=user_name, password=password, target_file_name=target_file_name,
            file_size=file_size, md5=md5,
        )
        download_resp.status = 0
        download_resp.start_time = ''
        download_resp.complete_time = ''
        return download_resp

    def GetStatus(self, _=None, context=None) -> ServiceStatus:
        """
        Get eNodeB status
        Note: input variable defaults used so this can be either called locally
        or as an RPC.
        """
        print_grpc(
            Void(), self._print_grpc_payload,
            "GetStatus Request:",
        )
        status = dict(get_service_status(self.state_machine_manager))
        status_message = ServiceStatus()
        status_message.meta.update(status)
        print_grpc(
            status_message, self._print_grpc_payload,
            "GetStatus Response:",
        )
        return status_message

    def GetAllEnodebStatus(self, _=None, context=None) -> AllEnodebStatus:
        print_grpc(
            Void(), self._print_grpc_payload,
            "GetAllEnodebStatus Request:",
        )
        all_enb_status = AllEnodebStatus()
        serial_list = self.state_machine_manager.get_connected_serial_id_list()
        for enb_serial in serial_list:
            enb_status = get_single_enb_status(
                enb_serial,
                self.state_machine_manager,
            )
            all_enb_status.enb_status_list.add(
                device_serial=enb_status.device_serial,
                ip_address=enb_status.ip_address,
                connected=enb_status.connected,
                configured=enb_status.configured,
                opstate_enabled=enb_status.opstate_enabled,
                rf_tx_on=enb_status.rf_tx_on,
                rf_tx_desired=enb_status.rf_tx_desired,
                gps_connected=enb_status.gps_connected,
                ptp_connected=enb_status.ptp_connected,
                mme_connected=enb_status.mme_connected,
                gps_longitude=enb_status.gps_longitude,
                gps_latitude=enb_status.gps_latitude,
                fsm_state=enb_status.fsm_state,
            )
        print_grpc(
            all_enb_status, self._print_grpc_payload,
            "GetAllEnodebStatus Response:",
        )
        return all_enb_status

    def GetEnodebStatus(
            self,
            request: EnodebIdentity,
            _context=None,
    ) -> SingleEnodebStatus:
        print_grpc(
            request, self._print_grpc_payload,
            "GetEnodebStatus Request:",
        )
        response = get_single_enb_status(
            request.device_serial,
            self.state_machine_manager,
        )
        print_grpc(
            response, self._print_grpc_payload,
            "GetEnodebStatus Response:",
        )
        return response
