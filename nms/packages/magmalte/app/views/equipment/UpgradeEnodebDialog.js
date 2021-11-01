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
import ActionTable from '../../components/ActionTable';
import Axios from 'axios';
// import Button from '@fbcnms/ui/components/design-system/Button';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '../../theme/design-system/DialogTitle';
import EnodebContext from '../../components/context/EnodebContext';
import React from 'react';
import Tab from '@material-ui/core/Tab';
import Tabs from '@material-ui/core/Tabs';
import nullthrows from '@fbcnms/util/nullthrows';
import withAlert from '@fbcnms/ui/components/Alert/withAlert';
import {Button, Upload, message} from 'antd';
import {RunGatewayCommands} from '../../state/lte/EquipmentState';
import {UploadOutlined} from '@ant-design/icons';
import {colors, typography} from '../../theme/default';
import {makeStyles} from '@material-ui/styles';
import {useContext, useState} from 'react';
import {useEnqueueSnackbar} from '@fbcnms/ui/hooks/useSnackbar';
import {useRouter} from '@fbcnms/ui/hooks';
import type {WithAlert} from '@fbcnms/ui/components/Alert/withAlert';

const useStyles = makeStyles(theme => ({
  dashboardRoot: {
    margin: theme.spacing(3),
    flexGrow: 1,
  },
  topBar: {
    backgroundColor: colors.primary.mirage,
    padding: '20px 40px 20px 40px',
    color: colors.primary.white,
  },
  tabBar: {
    backgroundColor: colors.primary.brightGray,
    color: colors.primary.white,
  },
  tabs: {
    color: colors.primary.white,
  },
  tab: {
    fontSize: '18px',
    textTransform: 'none',
  },
  tabLabel: {
    padding: '16px 0 16px 0',
    display: 'flex',
    alignItems: 'center',
  },
  tabIconLabel: {
    marginRight: '8px',
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
  appBarBtnSecondary: {
    color: colors.primary.white,
  },
  input: {
    display: 'inline-flex',
    margin: '5px 0',
    width: '50%',
    fullWidth: true,
  },
}));

export default function EnodebUpgradeButton() {
  const classes = useStyles();
  const [open, setOpen] = useState(false);

  return (
    <>
      <UpgradeDialog open={open} onClose={() => setOpen(false)} />
      <Button
        variant="text"
        onClick={() => setOpen(true)}
        className={classes.appBarBtnSecondary}>
        {'Upgrade'}
      </Button>
    </>
  );
}

type DialogProps = {
  open: boolean,
  onClose: () => void,
};

function UpgradeDialog(props: DialogProps) {
  const classes = useStyles();
  const [tabPos, setTabPos] = useState(0);

  return (
    <Dialog
      data-testid="editDialog"
      open={props.open}
      fullWidth={true}
      maxWidth="lg">
      <DialogTitle label={'Upgrade'} onClose={props.onClose} />
      <Tabs
        value={tabPos}
        onChange={(_, v) => setTabPos(v)}
        indicatorColor="primary"
        className={classes.tabBar}>
        <Tab key="upgrade" label={'Enodeb Upgrade'} />; ;
        <Tab key="upload" label={'Upload Enodeb'} />
      </Tabs>
      {tabPos === 0 && <UpgradeDetails {...props} />}
      {tabPos === 1 && <UploadDetails {...props} />}
    </Dialog>
  );
}

const UpgradeDetails = withAlert(UpgradeDetailsInternal);
function UpgradeDetailsInternal(props: WithAlert) {
  const ctx = useContext(EnodebContext);
  const {match} = useRouter();
  const networkId: string = nullthrows(match.params.networkId);
  const enodebSerial: string = nullthrows(match.params.enodebSerial);
  const enbInfo = ctx.state.enbInfo[enodebSerial];
  const gatewayId = enbInfo?.enb_state?.reporting_gateway_id;
  const enqueueSnackbar = useEnqueueSnackbar();
  console.log('gatewayid', enodebSerial);
  // const [error, setError] = useState('');
  // const [updatedTierEntries, setUpdatedTierEntries] = useState(new Set());
  // const [removedTierEntries, setRemovedTierEntries] = useState(new Set());
  // const [enbEntries, setEnbEntries] = useState(
  //   Object.keys(ctx.state.tiers).map(tierId => ({
  //     id: tierId,
  //     name: ctx.state.tiers[tierId].name,
  //     version: ctx.state.tiers[tierId].version,
  //   })),
  // );
  const data = [
    {
      id: 'BaiBS_RTS_3.8.6.IMG',
      md5: 'f66aafe0077cbe90e3a1ab7314565be9',
      size: 66232320,
    },
  ];
  const upgrade = (name, size, md5)=>() => {
    if (gatewayId == null) {
      enqueueSnackbar(
        'Unable to trigger Upgrade, reporting gateway not found',
        {variant: 'error'},
      );
      return;
    }
    props
      .confirm(`Are you sure you want to upgrade the ${enodebSerial}?`)
      .then(async confirmed => {
        if (!confirmed) {
          return;
        }
        const params = {
          command: 'download_enodeb',
          params: {
            shell_params: {
              [enodebSerial]: {
                url: 'http://192.168.8.112:8000/rts/BaiBS_RTS_3.8.6.IMG',
                user_name: 'admin',
                password: 'admin',
                file_size: size,
                target_file_name: name,
                md5: md5,
              },
            },
          },
        };
        try {
          await RunGatewayCommands({
            networkId,
            gatewayId,
            command: 'generic',
            params,
          });
        } catch (e) {
          enqueueSnackbar(e.response?.data?.message ?? e.message, {
            variant: 'error',
          });
        }
      });
  };

  return (
    <>
      <DialogContent>
        <ActionTable
          data={data}
          columns={[
            {
              title: 'file name',
              field: 'id',
            },
            {
              title: 'md5',
              field: 'md5',
            },
            {
              title: 'file size',
              field: 'size',
            },
            {
              title: 'Action',
              field: 'action',
              render: record => (
                <Button onClick={upgrade(record.id, record.size, record.md5)}>
                  Upgrade
                </Button>
              ),
            },
          ]}
          options={{
            actionsColumnIndex: -1,
            pageSizeOptions: [10, 15],
          }}
        />
      </DialogContent>
      <DialogActions>
        {/*<Button onClick={props.onClose}> Cancel </Button>*/}
        {/*<Button onClick={Upgrade}> Upgrade </Button>*/}
      </DialogActions>
    </>
  );
}

function UploadDetails() {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const handleUpload = () => {
    const formData = new FormData();
    fileList.forEach(file => {
      formData.append('file', file);
    });
    setUploading(true);
    Axios({
      url: '',
      method: 'POST',
      crossOrigin: true,
      processData: false,
      headers: {'Content-Type': 'mulitipart/form-data'},
      data: formData,
    }).then(
      request => {
        setUploading(false);
        setFileList([]);
        message.success(`upload successfully.`);
      },
      error => {
        setUploading(false);
        message.error(`${error.data}`);
      },
    );
  };
  const props_upload = {
    beforeUpload: file => {
      setFileList([file]);
      return false;
    },
    onRemove: file => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
  };
  return (
    <DialogContent>
      <Upload {...props_upload}>
        <Button icon={<UploadOutlined />} disabled={fileList.length >= 1}>
          Select Enodeb Packages
        </Button>
      </Upload>
      <Button
        type="primary"
        onClick={handleUpload}
        disabled={fileList.length === 0}
        loading={uploading}
        style={{marginTop: 16}}>
        {uploading ? 'Uploading' : 'Start Upload'}
      </Button>
    </DialogContent>
  );
}
