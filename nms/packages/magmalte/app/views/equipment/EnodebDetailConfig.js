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

import {EnodeConfigFdd} from './EnodebDetailConfigFdd';
import {EnodeConfigTdd} from './EnodebDetailConfigTdd';
import {colors, typography} from '../../theme/default';
import {makeStyles} from '@material-ui/styles';
import {useContext, useState} from 'react';
import {useEnqueueSnackbar} from '@fbcnms/ui/hooks/useSnackbar';
import {useReducer} from 'react';
import {useRouter} from '@fbcnms/ui/hooks';

import AddIcon from '@material-ui/icons/Add';
import DeleteIcon from '@material-ui/icons/Delete';
import EditIcon from '@material-ui/icons/Edit';
import IconButton from '@material-ui/core/IconButton';

import ActionTable from '../../components/ActionTable';
import Box from '@material-ui/core/Box';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import FormControl from '@material-ui/core/FormControl';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import Select from '@material-ui/core/Select';
import Switch from '@material-ui/core/Switch';
import TextField from '@material-ui/core/TextField';

function reducer(state, action) {
  const index = state.indexOf(action.item);

  switch (action.type) {
    case 'add':
      const arr = [...state, action.item];
      if (action.fn) action.fn(arr);
      return arr;
    case 'modify':
      Object.assign(state[index], action.new);
      if (action.fn) action.fn(state);
      return [...state];
    case 'remove':
      const arrD = [...state.slice(0, index), ...state.slice(index + 1)];
      if (action.fn) action.fn(arrD);
      return arrD;
    default:
      throw new Error();
  }
}

function cellReducer(state, action) {
  const index = state.indexOf(action.item);

  switch (action.type) {
    case 'add':
      const arr = [...state, action.item];
      if (action.fn) action.fn(arr);
      return arr;
    case 'modify':
      Object.assign(state[index], action.new);
      if (action.fn) action.fn(state);
      return [...state];
    case 'remove':
      const arrD = [...state.slice(0, index), ...state.slice(index + 1)];
      if (action.fn) action.fn(arrD);
      return arrD;
    default:
      throw new Error();
  }
}

function FreqFormDialog(props) {
  const type = props.type || 'add',
    row = {
      enable: true,
      index: '',
      earfcn: '',
      q_offset_range: '',
      q_rx_lev_min_sib5: '',
      p_max: '',
      t_reselection_eutra: '',
      t_reselection_eutra_sf_medium: '',
      resel_thresh_high: '',
      resel_thresh_low: '',
      reselection_priority: '',
    },
    classes = useStyles();

  if (props.list) {
    const idxes = props.list.map(function (m) {
        return m.index - 0;
      }),
      maxList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];

    maxList.map(function (idx) {
      if (!idxes.includes(idx) && [''].includes(row.index)) {
        row.index = idx;
      }
    });
  }
  if (props.row) {
    [
      'enable',
      'index',
      'earfcn',
      'q_offset_range',
      'q_rx_lev_min_sib5',
      'p_max',
      't_reselection_eutra',
      't_reselection_eutra_sf_medium',
      'resel_thresh_high',
      'resel_thresh_low',
      'reselection_priority',
    ].map(function (key) {
      row[key] = props.row[key];
    });
  }

  const [form, setForm] = React.useState(row);

  const handleChange = (key, val) => setForm({...form, [key]: val});

  const [open, setOpen] = React.useState(false);

  const handleClickOpen = () => {
    setForm(row);
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  return (
    <div>
      <IconButton aria-label="delete" size="small">
        {type === 'add' ? (
          <AddIcon onClick={handleClickOpen} fontSize="inherit" />
        ) : (
          <EditIcon onClick={handleClickOpen} fontSize="inherit" />
        )}
      </IconButton>

      <Dialog open={open} onClose={handleClose}>
        <DialogTitle>
          {type === 'edit' ? 'Modify' : 'Add'} Neigh Freq
        </DialogTitle>
        <DialogContent>
          <Box
            component="form"
            sx={{
              '& .MuiTextField-root': {m: 1, width: '25ch'},
            }}>
            <TextField
              variant="standard"
              label="EARFCN"
              name="earfcn"
              value={form.earfcn}
              onChange={({target}) => handleChange('earfcn', target.value)}
            />
            <FormControlLabel
              sx={{paddingTop: 3, paddingLeft: 1}}
              control={
                <Switch
                  checked={form.enable}
                  name="enable"
                  // eslint-disable-next-line
                  onChange={({target}) => handleChange('enable', !form.enable)}
                />
              }
              label="Enable"
            />
            <FormControl className={classes.formControl}>
              <InputLabel id="qOffsetRange-select-label">
                Q-OffsetRange
              </InputLabel>
              <Select
                width="200"
                labelId="qOffsetRange-select-label"
                variant="standard"
                name="q_offset_range"
                value={form.q_offset_range}
                onChange={({target}) =>
                  handleChange('q_offset_range', target.value)
                }>
                <MenuItem value={-22}>-22</MenuItem>
                <MenuItem value={-24}>-24</MenuItem>
              </Select>
            </FormControl>
            <TextField
              variant="standard"
              label="q_rx_lev_min_sib5"
              name="q_rx_lev_min_sib5"
              value={form.q_rx_lev_min_sib5}
              onChange={({target}) =>
                handleChange('q_rx_lev_min_sib5', target.value)
              }
            />
            <TextField
              variant="standard"
              label="p_max"
              name="p_max"
              value={form.p_max}
              onChange={({target}) => handleChange('p_max', target.value)}
            />
            <TextField
              variant="standard"
              label="t_reselection_eutra"
              name="t_reselection_eutra"
              value={form.t_reselection_eutra}
              onChange={({target}) =>
                handleChange('t_reselection_eutra', target.value)
              }
            />
            <FormControl className={classes.formControl}>
              <InputLabel id="medium-select-label">
                t_reselection_eutra_sf_medium
              </InputLabel>
              <Select
                width="200"
                labelId="medium-select-label"
                variant="standard"
                name="t_reselection_eutra_sf_medium"
                value={form.t_reselection_eutra_sf_medium}
                onChange={({target}) =>
                  handleChange('t_reselection_eutra_sf_medium', target.value)
                }>
                <MenuItem value={25}>25</MenuItem>
                <MenuItem value={50}>50</MenuItem>
                <MenuItem value={75}>75</MenuItem>
                <MenuItem value={100}>100</MenuItem>
              </Select>
            </FormControl>
            <TextField
              variant="standard"
              label="resel_thresh_high"
              name="resel_thresh_high"
              value={form.resel_thresh_high}
              onChange={({target}) =>
                handleChange('resel_thresh_high', target.value)
              }
            />
            <TextField
              variant="standard"
              label="resel_thresh_low"
              name="resel_thresh_low"
              value={form.resel_thresh_low}
              onChange={({target}) =>
                handleChange('resel_thresh_low', target.value)
              }
            />
            <TextField
              variant="standard"
              label="reselection_priority"
              name="reselection_priority"
              value={form.reselection_priority}
              onChange={({target}) =>
                handleChange('reselection_priority', target.value)
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              props.onSave(form);
              handleClose();
            }}>
            OK
          </Button>
          <Button onClick={handleClose}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

function CellFormDialog(props) {
  const type = props.type || 'add',
    row = {
      enable: true,
      index: '',
      plmn: '',
      cellId: '',
      earfcn: '',
      pci: '',
      qOffset: '',
      cio: '',
      tac: '',
    },
    classes = useStyles();

  if (props.list) {
    const idxes = props.list.map(function (m) {
        return m.index - 0;
      }),
      maxList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];

    maxList.map(function (idx) {
      if (!idxes.includes(idx) && [''].includes(row.index)) {
        row.index = idx;
      }
    });
  }

  if (props.row) {
    [
      'enable',
      'index',
      'plmn',
      'cellId',
      'earfcn',
      'pci',
      'qOffset',
      'cio',
      'tac',
    ].map(function (key) {
      row[key] = props.row[key];
    });
  }

  const [cellForm, setCellForm] = React.useState(row);

  const handleChange = (key, val) => setCellForm({...cellForm, [key]: val});

  const [cellOpen, setCellOpen] = React.useState(false);

  const handleClickOpen = () => {
    setCellOpen(true);
  };

  const handleClose = () => {
    setCellForm(row);
    setCellOpen(false);
  };

  return (
    <div>
      <IconButton aria-label="delete" size="small">
        {type === 'add' ? (
          <AddIcon onClick={handleClickOpen} fontSize="inherit" />
        ) : (
          <EditIcon onClick={handleClickOpen} fontSize="inherit" />
        )}
      </IconButton>

      <Dialog open={cellOpen} onClose={handleClose}>
        <DialogTitle>
          {type === 'edit' ? 'Modify' : 'Add'} Frequence
        </DialogTitle>
        <DialogContent>
          <Box
            component="form"
            sx={{
              '& .MuiTextField-root': {m: 1, width: '25ch'},
            }}>
            <TextField
              label="PLMN"
              variant="standard"
              name="plmn"
              value={cellForm.plmn}
              onChange={({target}) => handleChange('plmn', target.value)}
            />
            <FormControlLabel
              sx={{paddingTop: 3, paddingLeft: 1}}
              control={
                <Switch
                  checked={cellForm.enable}
                  name="enable"
                  onChange={() => handleChange('enable', !cellForm.enable)}
                />
              }
              label="Enable"
            />
            <TextField
              label="Cell ID"
              variant="standard"
              name="cellId"
              value={cellForm.cellId}
              onChange={({target}) => handleChange('cellId', target.value)}
            />
            <TextField
              label="EARFCN"
              variant="standard"
              name="earfcn"
              value={cellForm.earfcn}
              onChange={({target}) => handleChange('earfcn', target.value)}
            />
            <TextField
              label="PCI"
              variant="standard"
              name="pci"
              value={cellForm.pci}
              onChange={({target}) => handleChange('pci', target.value)}
            />
            <FormControl className={classes.formControl}>
              <InputLabel id="qOffset-select-label">qOffset</InputLabel>
              <Select
                width="200"
                labelId="qOffset-select-label"
                variant="standard"
                name="cio"
                value={cellForm.qOffset}
                onChange={({target}) => handleChange('qOffset', target.value)}>
                <MenuItem value={-20}>-20</MenuItem>
                <MenuItem value={-22}>-22</MenuItem>
                <MenuItem value={-24}>-24</MenuItem>
              </Select>
            </FormControl>
            <FormControl className={classes.formControl}>
              <InputLabel id="cio-select-label">CIO</InputLabel>
              <Select
                labelId="cio-select-label"
                variant="standard"
                name="cio"
                value={cellForm.cio}
                onChange={({target}) => handleChange('cio', target.value)}>
                <MenuItem value={-22}>-22</MenuItem>
                <MenuItem value={-24}>-24</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="TAC"
              variant="standard"
              name="tac"
              value={cellForm.tac}
              onChange={({target}) => handleChange('tac', target.value)}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              props.onSave(cellForm);
              handleClose();
            }}>
            OK
          </Button>
          <Button onClick={handleClose}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

export function NeighFreq() {
  const ctx = useContext(EnodebContext);
  const {match} = useRouter();
  const enodebSerial: string = nullthrows(match.params.enodebSerial);
  const enbInfo = ctx.state.enbInfo[enodebSerial];
  const [dataList, dispatch] = useReducer(
    reducer,
    enbInfo.enb?.enodeb_config?.managed_config?.NeighborFreqList ?? [],
  );
  const enqueueSnackbar = useEnqueueSnackbar();

  const addFreq = (row, cb) => {
    if (row === '') {
      return;
    }
    dispatch({type: 'add', item: row, fn: cb});
  };
  // modify will use  in future.
  // const modify = (row, newRow, cb) => {
  //   dispatch({type: 'modify', item: row, new: newRow, fn: cb});
  // };

  const remove = (row, cb) => {
    dispatch({type: 'remove', item: row, fn: cb});
  };

  const columns = [
    {
      field: 'index',
      title: 'Index',
      width: 120,
      render: function (o) {
        return o.index - 1;
      },
    },
    {
      field: 'enable',
      title: 'Enable',
      width: 150,
    },
    {
      field: 'earfcn',
      title: 'EARFCN',
      width: 150,
    },
    {
      field: 'q_offset_range',
      title: 'Q-OffsetRange',
      width: 150,
    },
    {
      field: 'q_rx_lev_min_sib5',
      title: 'q_rx_lev_min_sib5',
      width: 150,
    },
    {
      field: 'p_max',
      title: 'p_max',
      width: 150,
    },
    {
      field: 't_reselection_eutra',
      title: 'tReselectionEutra',
      width: 150,
    },
    {
      field: 't_reselection_eutra_sf_medium',
      title: 'tReselectionEutraMedium',
      width: 150,
    },
    {
      field: 'resel_thresh_high',
      title: 'ReselThreshHign',
      width: 150,
    },
    {
      field: 'resel_thresh_low',
      title: 'resel_thresh_low',
      width: 150,
    },
    {
      field: 'reselection_priority',
      title: 'reselection_priority',
      width: 150,
    },
    {
      field: 'op',
      title: 'Operations',
      width: 150,
      render: function (o) {
        return (
          <>
            <IconButton aria-label="delete" size="small">
              <DeleteIcon
                onClick={() => {
                  try {
                    remove(o, function (p) {
                      const list = JSON.parse(JSON.stringify(p));
                      try {
                        list.map(function (item) {
                          [
                            'index',
                            'earfcn',
                            'q_offset_range',
                            'q_rx_lev_min_sib5',
                            'p_max',
                            't_reselection_eutra',
                            't_reselection_eutra_sf_medium',
                            'resel_thresh_high',
                            'resel_thresh_low',
                            'reselection_priority',
                          ].map(function (key) {
                            item[key] = parseInt(item[key]);
                          });

                          delete item.tableData;
                        });
                      } catch (e) {}
                      enbInfo.enb.enodeb_config.managed_config.NeighborFreqList = list;
                      enbInfo.enb.config.NeighborFreqList = list;
                      ctx.setState(enbInfo.enb.serial, {
                        ...enbInfo,
                        enb: enbInfo.enb,
                      });
                      enqueueSnackbar('eNodeb deleted successfully', {
                        variant: 'success',
                      });
                    });
                  } catch (e) {}
                }}
                fontSize="inherit"
              />
            </IconButton>
          </>
        );
      },
    },
  ];

  return (
    <div>
      <div>
        Neigh Freq List
        <IconButton aria-label="add" size="small">
          <FreqFormDialog
            list={enbInfo.enb.config.NeighborFreqList}
            onSave={freq => {
              try {
                addFreq(freq, function (p) {
                  const list = JSON.parse(JSON.stringify(p));
                  try {
                    list.map(function (item) {
                      [
                        'index',
                        'earfcn',
                        'q_offset_range',
                        'q_rx_lev_min_sib5',
                        'p_max',
                        't_reselection_eutra',
                        't_reselection_eutra_sf_medium',
                        'resel_thresh_high',
                        'resel_thresh_low',
                        'reselection_priority',
                      ].map(function (key) {
                        if (![''].includes(item[key])) {
                          item[key] = parseInt(item[key]);
                        }
                      });

                      delete item.tableData;
                    });
                  } catch (e) {}

                  enbInfo.enb.enodeb_config.managed_config.NeighborFreqList = list;
                  enbInfo.enb.config.NeighborFreqList = list;
                  ctx.setState(enbInfo.enb.serial, {
                    ...enbInfo,
                    enb: enbInfo.enb,
                  });
                  enqueueSnackbar('eNodeb saved successfully', {
                    variant: 'success',
                  });
                });
              } catch (e) {}
            }}
          />
        </IconButton>
      </div>

      <div style={{width: '100%'}}>
        <ActionTable data={dataList} columns={columns} />
      </div>
    </div>
  );
}

export function NeighCell() {
  const ctx = useContext(EnodebContext);
  const {match} = useRouter();
  const enodebSerial: string = nullthrows(match.params.enodebSerial);
  const enbInfo = ctx.state.enbInfo[enodebSerial];
  const [cells, dispatch] = useReducer(
    cellReducer,
    enbInfo.enb?.enodeb_config?.managed_config?.NeighborCellList ?? [],
  );
  const enqueueSnackbar = useEnqueueSnackbar();

  const addCell = (row, cb) => {
    if (row === '') {
      return;
    }
    dispatch({type: 'add', item: row, fn: cb});
  };
  // modify will use in future.
  // const modify = (row, newRow, cb) => {
  //   dispatch({type: 'modify', item: row, new: newRow, fn: cb});
  // };

  const remove = (row, cb) => {
    dispatch({type: 'remove', item: row, fn: cb});
  };

  const columns = [
    {
      field: 'index',
      title: 'Index',
      width: 120,
      render: function (o) {
        return o.index - 1;
      },
    },
    {
      field: 'enable',
      title: 'Enable',
      width: 150,
    },
    {
      field: 'plmn',
      title: 'PLMN',
      width: 150,
    },
    {
      field: 'cellId',
      title: 'Cell ID',
      minWidth: 120,
    },
    {
      field: 'earfcn',
      title: 'EARFCN',
      width: 150,
    },
    {
      field: 'pci',
      title: 'PCI',
      width: 150,
    },
    {
      field: 'qOffset',
      title: 'qOffset',
      width: 150,
    },
    {
      field: 'cio',
      title: 'CIO',
      width: 150,
    },
    {
      field: 'tac',
      title: 'TAC',
      width: 150,
    },
    {
      field: 'op',
      title: 'Operations',
      width: 150,
      render: function (o) {
        return (
          <>
            <IconButton aria-label="delete" size="small">
              <DeleteIcon
                onClick={() => {
                  try {
                    remove(o, function (p) {
                      const list = JSON.parse(JSON.stringify(p));
                      try {
                        list.map(function (item) {
                          [
                            'index',
                            'cellId',
                            'earfcn',
                            'pci',
                            'qOffset',
                            'cio',
                            'tac',
                          ].map(function (key) {
                            item[key] = parseInt(item[key]);
                          });

                          delete item.tableData;
                        });
                      } catch (e) {}
                      enbInfo.enb.enodeb_config.managed_config.NeighborCellList = list;
                      enbInfo.enb.config.NeighborCellList = list;
                      ctx.setState(enbInfo.enb.serial, {
                        ...enbInfo,
                        enb: enbInfo.enb,
                      });
                      enqueueSnackbar('eNodeb deleted successfully', {
                        variant: 'success',
                      });
                    });
                  } catch (e) {}
                }}
                fontSize="inherit"
              />
            </IconButton>
          </>
        );
      },
    },
  ];

  return (
    <div>
      <div>
        Neigh Cell List
        <IconButton aria-label="add" size="small">
          <CellFormDialog
            list={enbInfo.enb.config.NeighborCellList}
            onSave={cell => {
              try {
                addCell(cell, function (p) {
                  const list = JSON.parse(JSON.stringify(p));
                  try {
                    list.map(function (item) {
                      [
                        'index',
                        // 'plmn',
                        'cellId',
                        'earfcn',
                        'pci',
                        'qOffset',
                        'cio',
                        'tac',
                      ].map(function (key) {
                        if (![''].includes(item[key])) {
                          item[key] = parseInt(item[key]);
                        }
                      });

                      delete item.tableData;
                    });
                  } catch (e) {}

                  enbInfo.enb.enodeb_config.managed_config.NeighborCellList = list;
                  enbInfo.enb.config.NeighborCellList = list;
                  ctx.setState(enbInfo.enb.serial, {
                    ...enbInfo,
                    enb: enbInfo.enb,
                  });
                  enqueueSnackbar('eNodeb saved successfully', {
                    variant: 'success',
                  });
                });
              } catch (e) {}
            }}
          />
        </IconButton>
      </div>

      <div style={{width: '100%'}}>
        <ActionTable data={cells} columns={columns} />
      </div>
    </div>
  );
}

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

          <NeighFreq />

          <NeighCell />
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
        category: 'Transmit',
        value: enbInfo.enb.enodeb_config?.managed_config?.transmit_enabled
          ? 'Enabled'
          : 'Disabled',
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
