import json


class Process:

    @staticmethod
    def send(data):
        line = json.dumps(data)
        assert "\n" not in line
        return line

    @staticmethod
    def recv(line):
        data = ""
        if line and line[-1] != "\n":
            return json.loads(line)
        return data

    @staticmethod
    def fake_link(data):
        return Process.recv(Process.send(data))
