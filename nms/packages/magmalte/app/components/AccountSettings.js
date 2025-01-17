/**
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

import Button from '../../fbc_js_core/ui/components/design-system/Button';
import FormGroup from '@material-ui/core/FormGroup';
import Paper from '@material-ui/core/Paper';
import React, {useContext} from 'react';
import Text from '../../fbc_js_core/ui/components/design-system/Text';
import TextField from '@material-ui/core/TextField';
import axios from 'axios';

import AppContext from '../../fbc_js_core/ui/context/AppContext';
import TopBar from './TopBar';
import {makeStyles} from '@material-ui/styles';
import {useEnqueueSnackbar} from '../../fbc_js_core/ui/hooks/useSnackbar';
import {useState} from 'react';

const TITLE = 'Account Settings';

const useStyles = makeStyles(theme => ({
  input: {},
  formContainer: {
    margin: theme.spacing(2),
    paddingBottom: theme.spacing(2),
  },
  paper: {
    margin: theme.spacing(3),
    padding: theme.spacing(),
  },
  formGroup: {
    marginBottom: theme.spacing(2),
  },
}));

export default function AccountSettings() {
  const classes = useStyles();
  const enqueueSnackbar = useEnqueueSnackbar();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const {isOrganizations} = useContext(AppContext);

  const onSave = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      enqueueSnackbar('Please complete all fields', {variant: 'error'});
      return;
    }

    if (newPassword !== confirmPassword) {
      enqueueSnackbar('Passwords do not match', {variant: 'error'});
      return;
    }

    try {
      await axios.post('/user/change_password', {
        currentPassword: currentPassword,
        newPassword: newPassword,
      });

      enqueueSnackbar('Success', {variant: 'success'});
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      enqueueSnackbar(error.response.data.error, {variant: 'error'});
    }
  };

  return (
    <>
      {!isOrganizations && <TopBar header={TITLE} tabs={[]} />}
      <Paper className={classes.paper}>
        <div className={classes.formContainer}>
          <Text data-testid="change-password-title" variant="h5">
            Change Password
          </Text>
          <FormGroup row className={classes.formGroup}>
            <TextField
              required
              label="Current Password"
              type="password"
              value={currentPassword}
              onChange={({target}) => setCurrentPassword(target.value)}
              className={classes.input}
            />
          </FormGroup>
          <FormGroup row className={classes.formGroup}>
            <TextField
              required
              autoComplete="off"
              label="New Password"
              type="password"
              value={newPassword}
              onChange={({target}) => setNewPassword(target.value)}
              className={classes.input}
            />
          </FormGroup>
          <FormGroup row className={classes.formGroup}>
            <TextField
              required
              autoComplete="off"
              label="Confirm Password"
              type="password"
              value={confirmPassword}
              onChange={({target}) => setConfirmPassword(target.value)}
              className={classes.input}
            />
          </FormGroup>
          <FormGroup row className={classes.formGroup}>
            <Button onClick={onSave}>Save</Button>
          </FormGroup>
        </div>
      </Paper>
    </>
  );
}
