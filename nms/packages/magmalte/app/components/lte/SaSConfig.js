import React from 'react';
import {makeStyles} from '@material-ui/styles';

const useStyles = makeStyles(theme => ({
    iframeAutoFit: {
        flex: '1 auto',
        height: '100%',
        width: '100%',
        overflow: 'auto',
    },
    iframeCtn: {
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    },
}));

export default function SaSConfig() {
    const classes = useStyles(),
        url = 'http://127.0.0.1:8082';

    return (
        <div className={classes.iframeCtn}>
            <iframe src={url} className={classes.iframeAutoFit}></iframe>
        </div>
    );
}
