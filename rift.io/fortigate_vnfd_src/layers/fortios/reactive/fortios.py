
from charmhelpers.core.hookenv import (
    config,
    status_set,
    action_get,
    action_set,
    action_fail,
    log,
)

from charms.reactive import (
    when,
    when_not,
    helpers,
    set_state,
    remove_state,
)


from charms import fortios
import logging
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortinetconflib')
hdlr = logging.FileHandler('/var/tmp/fortigateconflib.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)

cfg = config()

            
@when_not('fortios.configured')
def not_ready_add():
    actions = [
        'actions.configure-interface',
        'actions.apiset'
        'actions.sshcmd'
    ]

    if helpers.any_states(*actions):
        action_fail('FORTIOS is not configured')

    status_set('blocked', 'fortios is not configured')


@when('fortios.configured')
@when('actions.apiset')
def apiset():
    """
    Configure an ethernet interface
    """
    set_state('actions.apiset')
    name = action_get('name')
    path = action_get('path')
    params = action_get('parameters')
    
    status_set('maintenance', 'running cmd on fortios')
    try:
        is_set, resp = fortios.apiset(name,path,data=params)
    except Exception as e:
         action_fail('API call on fortios failed reason:'+repr(e))
    else:
        if is_set is True:
            log('API call successfull response %s' % resp)
            action_set({'output': resp})
        else:
            action_fail('API call on fortios failed reason:'+resp)
    remove_state('actions.apiset')



@when('fortios.configured')
@when('actions.sshcmd')
def sshcmd():
    '''
    Create and Activate the network corporation
    '''
    set_state('actions.sshcmd')
    commands = action_get('commands').split("\\n")
    # multi line is accepted with \n to separate then converted because juju does not allow advanced types like list or json :(
    cmdsMultiLines="""
    {}
    """.format("\n".join(commands))

    status_set('maintenance', 'running cmd on fortios')
    try:
        log("trying to run cmd: %s on fortios" % cmdsMultiLines )
        stdout,stderr = fortios.sshcmd(cmdsMultiLines)
    except Exception as e:
         action_fail('cmd on fortios failed reason:'+repr(e))
    else:
        log('sshcmd resp %s' % stdout)
        action_set({'output': stdout})
    remove_state('actions.sshcmd')


@when('fortios.configured')
@when('update-status')
def update_status():
    try:
        """
        Using the fortigaeconf lib to connect ot rest api
        """
        if fortios.connectionisok(vdom="root"):
            status_set('active', 'alive')
        else:
            status_set('blocked', fortios+' can not be reached')
            raise Exception(fortios+' unreachable')
    except Exception as e:
        log(repr(e))
        status_set('blocked', 'validation failed: %s' % e)
