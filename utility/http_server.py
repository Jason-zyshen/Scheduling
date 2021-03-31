from http.server import SimpleHTTPRequestHandler as SimpleHTTP
import socketserver


class MyRequestHandler(SimpleHTTP):
    def do_GET(self):
        if self.path == '/':
            self.path = '/preview'
        return SimpleHTTP.do_GET(self)


def server():
    Handler = MyRequestHandler
    server = socketserver.TCPServer(('', 1111), Handler)

    server.serve_forever()

server()