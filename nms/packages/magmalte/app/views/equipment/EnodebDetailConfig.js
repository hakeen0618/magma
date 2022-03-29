/*
 * Copyright 2020 The Magma Authors.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree.
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * @flow strict-local
 * @format
 */
import type {DataRows} from '../../components/DataGrid';
import type {EnodebInfo} from '../../components/lte/EnodebUtils';
import type {network_ran_configs} from '../../../generated/MagmaAPIBindings';

import AddEditEnodeButton from './EnodebDetailConfigEdit';
import Button from '@material-ui/core/Button';
import CardTitleRow from '../../components/layout/CardTitleRow';
import DataGrid from '../../components/DataGrid';
import EnodebContext from '../../components/context/EnodebContext';
import Grid from '@material-ui/core/Grid';
import JsonEditor from '../../components/JsonEditor';
import React from 'react';
import SettingsIcon from '@material-ui/icons/Settings';
import nullthrows from '@fbcnms/util/nullthrows';
import {NeighborCellConfig, NeighborFreqConfig} from './EnodebDetailNeighbor';

import {EnodeConfigFdd} from './EnodebDetailConfigFdd';
import {EnodeConfigTdd} from './EnodebDetailConfigTdd';
import {colors, typography} from '../../theme/default';
import {makeStyles} from '@material-ui/styles';
import {useContext, useState} from 'react';
import {useEnqueueSnackbar} from '@fbcnms/ui/hooks/useSnackbar';
import {useRouter} from '@fbcnms/ui/hooks';

const useStyles = makeStyles(theme => ({
  formControl: {
    margin: theme.spacing(1),
    minWidth: 260,
  },
  dashboardRoot: {
    margin: theme.spacing(3),
    flexGrow: 1,
  },
  itemTitle: {
    color: colors.primary.comet,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  itemValue: {
    color: colors.primary.brightGray,
  },
  appBarBtn: {
    color: colors.primary.white,
    background: colors.primary.comet,
    fontFamily: typography.button.fontFamily,
    fontWeight: typography.button.fontWeight,
    fontSize: typography.button.fontSize,
    lineHeight: typography.button.lineHeight,
    letterSpacing: typography.button.letterSpacing,

    '&:hover': {
      background: colors.primary.mirage,
    },
  },
}));

export function EnodebJsonConfig() {
  const ctx = useContext(EnodebContext);
  const {match} = useRouter();
  const [error, setError] = useState('');
  const enodebSerial: string = nullthrows(match.params.enodebSerial);
  const enbInfo = ctx.state.enbInfo[enodebSerial];
  const enqueueSnackbar = useEnqueueSnackbar();

  return (
    <JsonEditor
      content={enbInfo.enb}
      error={error}
      onSave={async enb => {
        try {
          ctx.setState(enbInfo.enb.serial, {...enbInfo, enb: enb});
          enqueueSnackbar('eNodeb saved successfully', {
            variant: 'success',
          });
          setError('');
        } catch (e) {
          setError(e.response?.data?.message ?? e.message);
        }
      }}
    />
  );
}

export default function EnodebConfig() {
  const classes = useStyles();
  const {history, relativeUrl} = useRouter();
  const ctx = useContext(EnodebContext);
  const {match} = useRouter();
  const enodebSerial: string = nullthrows(match.params.enodebSerial);
  const enbInfo = ctx.state.enbInfo[enodebSerial];
  const lteRanConfigs = ctx.lteRanConfigs;
  const enbManaged = enbInfo.enb.enodeb_config?.config_type === 'MANAGED';

  function editJSON() {
    return (
      <Button
        className={classes.appBarBtn}
        onClick={() => {
          history.push(relativeUrl('/json'));
        }}>
        Edit JSON
      </Button>
    );
  }

  function editEnodeb() {
    return (
      <AddEditEnodeButton
        title={'Edit'}
        isLink={true}
        editProps={{
          editTable: 'config',
        }}
      />
    );
  }

  function editRAN() {
    return (
      <AddEditEnodeButton
        title={'Edit'}
        isLink={true}
        editProps={{
          editTable: 'ran',
        }}
      />
    );
  }

  return (
    <div className={classes.dashboardRoot}>
      <Grid container spacing={4}>
        <Grid item xs={12}>
          <CardTitleRow label="Config" icon={SettingsIcon} filter={editJSON} />
        </Grid>

        <Grid item xs={12} md={6}>
          <CardTitleRow label="eNodeb" filter={editEnodeb} />
          <EnodebInfoConfig />
        </Grid>

        <Grid item xs={12} md={6}>
          <CardTitleRow label="RAN" filter={editRAN} />
          {enbManaged ? (
            <EnodebManagedRanConfig
              enbInfo={enbInfo}
              lteRanConfigs={lteRanConfigs}
            />
          ) : (
            <EnodebUnmanagedRanConfig enbInfo={enbInfo} />
          )}

          <NeighborFreqConfig />

          <NeighborCellConfig />
        </Grid>
      </Grid>
    </div>
  );
}

function EnodebManagedRanConfig({
  enbInfo,
  lteRanConfigs,
}: {
  enbInfo: EnodebInfo,
  lteRanConfigs?: network_ran_configs,
}) {
  const managedConfig: DataRows[] = [
    [
      {
        category: 'eNodeB Externally Managed',
        value: 'False',
      },
    ],
    [
      {
        category: 'Bandwidth',
        value: enbInfo.enb.enodeb_config?.managed_config?.bandwidth_mhz ?? '-',
      },
    ],
    [
      {
        category: 'Cell ID',
        value: enbInfo.enb.enodeb_config?.managed_config?.cell_id ?? '-',
      },
    ],
    [
      {
        category: 'RAN Config',
        value: lteRanConfigs?.tdd_config
          ? 'TDD'
          : lteRanConfigs?.fdd_config
          ? 'FDD'
          : '-',
        collapse: lteRanConfigs?.tdd_config ? (
          <EnodeConfigTdd
            earfcndl={enbInfo.enb.enodeb_config?.managed_config?.earfcndl ?? 0}
            specialSubframePattern={
              enbInfo.enb.enodeb_config?.managed_config
                ?.special_subframe_pattern ?? 0
            }
            subframeAssignment={
              enbInfo.enb.enodeb_config?.managed_config?.subframe_assignment ??
              0
            }
          />
        ) : lteRanConfigs?.fdd_config ? (
          <EnodeConfigFdd
            earfcndl={enbInfo.enb.enodeb_config?.managed_config?.earfcndl ?? 0}
            earfcnul={lteRanConfigs.fdd_config.earfcnul}
          />
        ) : (
          false
        ),
      },
    ],
    [
      {
        category: 'PCI',
        value: enbInfo.enb.enodeb_config?.managed_config?.pci ?? '-',
      },
    ],
    [
      {
        category: 'TAC',
        value: enbInfo.enb.enodeb_config?.managed_config?.tac ?? '-',
      },
    ],
    [
      {
        category: 'X2 Enable/Disable',
        value:
          //   enbInfo.enb.enodeb_config?.managed_config?.x2_enable_disable
          // ? 'Enabled'
          // : 'Disabled',
          enbInfo.enb.enodeb_config &&
          enbInfo.enb.enodeb_config.managed_config &&
          [true, 'Enabled', 1].includes(
            enbInfo.enb.enodeb_config?.managed_config?.x2_enable_disable,
          )
            ? 'Enabled'
            : 'Disabled',
      },
    ],
    [
      {
        category: 'Reference Signal Power',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.power_control
            ?.reference_signal_power ?? '-',
      },
    ],
    [
      {
        category: 'Power Class',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.power_control
            ?.power_class ?? '-',
      },
    ],
    [
      {
        category: 'PA',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.power_control?.pa ?? '-',
      },
    ],
    [
      {
        category: 'PB',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.power_control?.pb ?? '-',
      },
    ],
    [
      {
        category: 'MME Pool 1',
        value: enbInfo.enb.enodeb_config?.managed_config?.mme_pool_1 ?? '-',
      },
    ],
    [
      {
        category: 'MME Pool 2',
        value: enbInfo.enb.enodeb_config?.managed_config?.mme_pool_2 ?? '-',
      },
    ],
    [
      {
        category: 'Management Server SSL Enable',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.managementServer
            ?.management_server_ssl_enable ?? false
            ? 'Enabled'
            : 'Disabled',
      },
    ],
    [
      {
        category: 'Management Server Host',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.managementServer
            ?.management_server_host ?? '-',
      },
    ],
    [
      {
        category: 'Management Server Port',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.managementServer
            ?.management_server_port ?? '',
      },
    ],
    [
      {
        category: '1588 SYNC Switch',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_switch ?? false
            ? 'Enabled'
            : 'Disabled',
      },
    ],
    [
      {
        category: '1588 SYNC domain num',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_domain ?? '',
      },
    ],
    [
      {
        category: '1588 SYNC asymmetry',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_asymmetry ?? '',
      },
    ],
    [
      {
        category: '1588 SYNC holdover',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_holdover ?? '',
      },
    ],
    [
      {
        category: '1588 SYNC Message Interval',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_msg_interval ?? '',
      },
    ],
    [
      {
        category: '1588 SYNC Delay request message Interval',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_delay_rq_msg_interval ?? '',
      },
    ],
    [
      {
        category: '1588 unicast switch',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_unicast_enable ?? false
            ? 'Unicast'
            : 'Multicast',
      },
    ],
    [
      {
        category: '1588 SYNC Unicast ServerIp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.sync_1588
            ?.sync_1588_unicast_serverIp ?? '',
      },
    ],
    [
      {
        category: 'Transmit',
        value: enbInfo.enb.enodeb_config?.managed_config?.transmit_enabled
          ? 'Enabled'
          : 'Disabled',
      },
    ],
    [
      {
        category: 'A1 Threshold Rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.a1_threshold_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'lte a1 threshold rsrq',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_a1_threshold_rsrq ?? '-',
      },
    ],
    [
      {
        category: 'hysteresis',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.hysteresis ?? '-',
      },
    ],
    [
      {
        category: 'time to trigger',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.time_to_trigger ?? '-',
      },
    ],
    [
      {
        category: 'a2 threshold rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.a2_threshold_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'lte a2 threshold rsrq',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_a2_threshold_rsrq ?? '-',
      },
    ],
    [
      {
        category: 'lte a2 threshold rsrp irat volte',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_a2_threshold_rsrp_irat_volte ?? '-',
      },
    ],
    [
      {
        category: 'lte a2 threshold rsrq irat volte',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_a2_threshold_rsrq_irat_volte ?? '-',
      },
    ],
    [
      {
        category: 'a3_offset',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.a3_offset ?? '-',
      },
    ],
    [
      {
        category: 'a3 offset anr',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.a3_offset_anr ?? '-',
      },
    ],
    [
      {
        category: 'a4 threshold rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.a4_threshold_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'lte intraa5 threshold1 rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_intra_a5_threshold_1_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'lte intraa5 threshold2 rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_intra_a5_threshold_2_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'lte inter anra5 threshold1 rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_inter_anr_a5_threshold_1_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'lte intraa5 threshold2 rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.lte_inter_anr_a5_threshold_2_rsrp ?? '-',
      },
    ],

    [
      {
        category: 'b2 threshold1 rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.b2_threshold1_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'b2 threshold2 rsrp',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.b2_threshold2_rsrp ?? '-',
      },
    ],
    [
      {
        category: 'b2 geran irat threshold',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.b2_geran_irat_threshold ?? '-',
      },
    ],
    [
      {
        category: 'qrxlevmin sib1',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.qrxlevmin_selection ?? '-',
      },
    ],
    [
      {
        category: 'qrxlevminoffset',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.qrxlevminoffset ?? '-',
      },
    ],
    [
      {
        category: 's intrasearch',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.s_intrasearch ?? '-',
      },
    ],
    [
      {
        category: 'qrxlevmin sib3',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.qrxlevmin_reselection ?? '-',
      },
    ],
    [
      {
        category: 'reselection priority',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.reselection_priority ?? '-',
      },
    ],
    [
      {
        category: 'threshservinglow',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.threshservinglow ?? '-',
      },
    ],
    [
      {
        category: 'ciphering algorithm',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.ciphering_algorithm ?? '-',
      },
    ],
    [
      {
        category: 'integrity algorithm',
        value:
          enbInfo.enb.enodeb_config?.managed_config?.ho_algorithm_config
            ?.integrity_algorithm ?? '-',
      },
    ],
  ];
  return <DataGrid data={managedConfig} testID="ran" />;
}

function EnodebUnmanagedRanConfig({enbInfo}: {enbInfo: EnodebInfo}) {
  const unmanagedConfig: DataRows[] = [
    [
      {
        category: 'eNodeB Externally Managed',
        value: 'True',
      },
    ],
    [
      {
        category: 'Cell ID',
        value: enbInfo.enb.enodeb_config?.unmanaged_config?.cell_id ?? '-',
      },
    ],
    [
      {
        category: 'TAC',
        value: enbInfo.enb.enodeb_config?.unmanaged_config?.tac ?? '-',
      },
    ],
    [
      {
        category: 'IP Address',
        value: enbInfo.enb.enodeb_config?.unmanaged_config?.ip_address ?? '-',
      },
    ],
  ];
  return <DataGrid data={unmanagedConfig} testID="ran" />;
}

function EnodebInfoConfig() {
  const ctx = useContext(EnodebContext);
  const {match} = useRouter();
  const enodebSerial: string = nullthrows(match.params.enodebSerial);
  const enbInfo = ctx.state.enbInfo[enodebSerial];

  const data: DataRows[] = [
    [
      {
        category: 'Name',
        value: enbInfo.enb.name,
      },
    ],
    [
      {
        category: 'Serial Number',
        value: enbInfo.enb.serial,
      },
    ],
    [
      {
        category: 'Description',
        value: enbInfo.enb.description ?? '-',
      },
    ],
  ];

  return <DataGrid data={data} testID="config" />;
}
