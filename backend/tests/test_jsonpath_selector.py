#!/usr/bin/python3

import time
from flask import url_for
from . util import live_server_setup

def test_setup(live_server):
    live_server_setup(live_server)

def set_original_response():
    test_return_data = """
    {
      "employees": [
        {
          "id": 1,
          "name": "Pankaj",
          "salary": "10000"
        },
        {
          "name": "David",
          "salary": "5000",
          "id": 2
        }
      ],
      "boss": {
        "name": "Fat guy"
      }
    }
    """
    with open("test-datastore/output.txt", "w") as f:
        f.write(test_return_data)
    return None

def set_modified_response():
    test_return_data = """
    {
      "employees": [
        {
          "id": 1,
          "name": "Pankaj",
          "salary": "10000"
        },
        {
          "name": "David",
          "salary": "5000",
          "id": 2
        }
      ],
      "boss": {
        "name": "Foobar"
      }
    }
        """

    with open("test-datastore/output.txt", "w") as f:
        f.write(test_return_data)

    return None



def test_check_json_filter(client, live_server):

    json_filter = 'json:boss.name'

    set_original_response()

    # Give the endpoint time to spin up
    time.sleep(1)

    # Add our URL to the import page
    test_url = url_for('test_endpoint', _external=True)
    res = client.post(
        url_for("import_page"),
        data={"urls": test_url},
        follow_redirects=True
    )
    assert b"1 Imported" in res.data

    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # Give the thread time to pick it up
    time.sleep(3)

    # Goto the edit page, add our ignore text
    # Add our URL to the import page
    res = client.post(
        url_for("edit_page", uuid="first"),
        data={"css_filter": json_filter, "url": test_url, "tag": "", "headers": ""},
        follow_redirects=True
    )
    assert b"Updated watch." in res.data

    # Check it saved
    res = client.get(
        url_for("edit_page", uuid="first"),
    )
    assert bytes(json_filter.encode('utf-8')) in res.data

    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # Give the thread time to pick it up
    time.sleep(3)
    #  Make a change
    set_modified_response()

    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)
    # Give the thread time to pick it up
    time.sleep(3)

    # It should have 'unviewed' still
    res = client.get(url_for("index"))
    assert b'unviewed' in res.data

    # Should not see this, because its not in the JSONPath we entered
    res = client.get(url_for("diff_history_page", uuid="first"))
    # But the change should be there, tho its hard to test the change was detected because it will show old and new versions
    assert b'Foobar' in res.data
