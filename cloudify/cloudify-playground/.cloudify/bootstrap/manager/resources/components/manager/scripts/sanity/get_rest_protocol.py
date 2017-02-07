#!/usr/bin/env python

from cloudify import ctx


def get_rest_config():
    rest_protocol = ctx.target.instance.runtime_properties['rest_protocol']
    rest_port = ctx.target.instance.runtime_properties['rest_port']

    ctx.source.instance.runtime_properties['rest_protocol'] = rest_protocol
    ctx.source.instance.runtime_properties['rest_port'] = rest_port

get_rest_config()
