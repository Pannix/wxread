"""Run with python test_login.py; no network or real credentials are used."""
import io
import logging
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests


def check(responses, succeeds):
    config = SimpleNamespace(data={}, headers={}, cookies={}, READ_NUM=200,
                             PUSH_METHOD='wxpusher', book=[], chapter=[])
    push = Mock()
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    logging.getLogger().addHandler(handler)
    try:
        with patch.dict(sys.modules, {
            'config': config,
            'push': SimpleNamespace(push=push),
            'log_utils': SimpleNamespace(setup_logging=lambda: print),
        }), patch.object(sys, 'argv', ['main.py', '--check-login']), \
                patch.object(requests, 'post', side_effect=responses) as post:
            try:
                runpy.run_path(str(Path(__file__).with_name('main.py')))
                raise AssertionError('login check must exit')
            except SystemExit as exc:
                assert succeeds and exc.code == 0
            except Exception as exc:
                assert not succeeds and '无法获取新密钥' in str(exc)
            assert post.call_count == len(responses)
            assert all(call.args[0].endswith('/login/renewal')
                       for call in post.call_args_list)
            push.assert_not_called()
    finally:
        logging.getLogger().removeHandler(handler)
    assert 'private-value' not in output.getvalue()
    return output.getvalue()


if __name__ == '__main__':
    success = Mock(cookies={'wr_skey': 'private-value'}, status_code=200)
    failure = Mock(cookies={}, status_code=200)
    failure.json.return_value = {'errcode': -2012, 'message': 'private-value'}
    check([success], True)
    check([failure, success], True)
    assert 'errcode=-2012' in check([failure] * 3, False)
    failure.json.side_effect = ValueError('private-value')
    assert 'errcode=unknown' in check([failure] * 3, False)
    assert 'ConnectionError' in check(
        [requests.ConnectionError('private-value')] * 3, False)
    print('PASS: login success, fallback, rejection, non-JSON and network failure; no reading, push or credential logs')
