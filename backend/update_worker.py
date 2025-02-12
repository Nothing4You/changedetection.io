import threading
import queue

# Requests for checking on the site use a pool of thread Workers managed by a Queue.
class update_worker(threading.Thread):
    current_uuid = None

    def __init__(self, q, notification_q, app, datastore, *args, **kwargs):
        self.q = q
        self.app = app
        self.notification_q = notification_q
        self.datastore = datastore
        super().__init__(*args, **kwargs)

    def run(self):
        from backend import fetch_site_status

        update_handler = fetch_site_status.perform_site_check(datastore=self.datastore)

        while not self.app.config.exit.is_set():

            try:
                uuid = self.q.get(block=False)
            except queue.Empty:
                pass

            else:
                self.current_uuid = uuid

                if uuid in list(self.datastore.data['watching'].keys()):
                    try:
                        changed_detected, result, contents = update_handler.run(uuid)

                    except PermissionError as e:
                        self.app.logger.error("File permission error updating", uuid, str(e))
                    except Exception as e:
                        self.app.logger.error("Exception reached", uuid, str(e))
                    else:
                        if result:
                            try:
                                self.datastore.update_watch(uuid=uuid, update_obj=result)
                                if changed_detected:

                                    # A change was detected
                                    newest_version_file_contents = ""
                                    self.datastore.save_history_text(uuid=uuid, contents=contents, result_obj=result)
                                    watch = self.datastore.data['watching'][uuid]

                                    newest_key = self.datastore.get_newest_history_key(uuid)
                                    if newest_key:
                                        with open(watch['history'][newest_key], 'r') as f:
                                            newest_version_file_contents = f.read().strip()

                                    n_object = {
                                        'watch_url': self.datastore.data['watching'][uuid]['url'],
                                        'uuid': uuid,
                                        'current_snapshot': newest_version_file_contents
                                    }

                                    # Did it have any notification alerts to hit?
                                    if len(watch['notification_urls']):
                                        print("Processing notifications for UUID: {}".format(uuid))
                                        n_object['notification_urls'] = watch['notification_urls']
                                        self.notification_q.put(n_object)

                                    # No? maybe theres a global setting, queue them all
                                    elif len(self.datastore.data['settings']['application']['notification_urls']):
                                        print("Processing GLOBAL notifications for UUID: {}".format(uuid))
                                        n_object['notification_urls'] = self.datastore.data['settings']['application']['notification_urls']
                                        self.notification_q.put(n_object)

                            except Exception as e:
                                print("!!!! Exception in update_worker !!!\n", e)

                self.current_uuid = None  # Done
                self.q.task_done()

            self.app.config.exit.wait(1)
