#!/usr/bin/python3

# Launch as a eventlet.wsgi server instance.

import getopt
import os
import sys

import eventlet
import eventlet.wsgi
import backend

from backend import store

def main(argv):
    ssl_mode = False
    port = 5000
    do_cleanup = False

    # Must be absolute so that send_from_directory doesnt try to make it relative to backend/
    datastore_path = os.path.join(os.getcwd(), "datastore")

    try:
        opts, args = getopt.getopt(argv, "csd:p:", "port")
    except getopt.GetoptError:
        print('backend.py -s SSL enable -p [port] -d [datastore path]')
        sys.exit(2)

    for opt, arg in opts:
        #        if opt == '--purge':
        # Remove history, the actual files you need to delete manually.
        #            for uuid, watch in datastore.data['watching'].items():
        #                watch.update({'history': {}, 'last_checked': 0, 'last_changed': 0, 'previous_md5': None})

        if opt == '-s':
            ssl_mode = True

        if opt == '-p':
            port = int(arg)

        if opt == '-d':
            datastore_path = arg

        # Cleanup (remove text files that arent in the index)
        if opt == '-c':
            do_cleanup = True

    # isnt there some @thingy to attach to each route to tell it, that this route needs a datastore
    app_config = {'datastore_path': datastore_path}

    datastore = store.ChangeDetectionStore(datastore_path=app_config['datastore_path'])
    app = backend.changedetection_app(app_config, datastore)

    # Go into cleanup mode
    if do_cleanup:
        datastore.remove_unused_snapshots()

    app.config['datastore_path'] = datastore_path


    @app.context_processor
    def inject_version():
        return dict(right_sticky="v{}".format(datastore.data['version_tag']),
                    new_version_available=app.config['NEW_VERSION_AVAILABLE'],
                    has_password=datastore.data['settings']['application']['password'] != False
                    )

    # Proxy sub-directory support
    # Set environment var USE_X_SETTINGS=1 on this script
    # And then in your proxy_pass settings
    #
    #         proxy_set_header Host "localhost";
    #         proxy_set_header X-Forwarded-Prefix /app;

    if os.getenv('USE_X_SETTINGS'):
        print ("USE_X_SETTINGS is ENABLED\n")
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1, x_host=1)

    if ssl_mode:
        # @todo finalise SSL config, but this should get you in the right direction if you need it.
        eventlet.wsgi.server(eventlet.wrap_ssl(eventlet.listen(('', port)),
                                               certfile='cert.pem',
                                               keyfile='privkey.pem',
                                               server_side=True), app)

    else:
        eventlet.wsgi.server(eventlet.listen(('', port)), app)


if __name__ == '__main__':
    main(sys.argv[1:])
