import socket

def check(host='127.0.0.1', port=8000):
    s = socket.socket()
    try:
        s.settimeout(2)
        s.connect((host, port))
        print('PORT_OPEN')
    except Exception as e:
        print('PORT_CLOSED', e)
    finally:
        s.close()

if __name__ == '__main__':
    check()