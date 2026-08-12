import asyncio
from aiohttp import web

ROOMS = {}

def set_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

async def handle_options(request):
    return set_cors(web.Response(status=200))

async def send_msg(request):
    data = await request.json()
    code = data.get('code')
    
    if code not in ROOMS:
        ROOMS[code] = {'messages': [], 'waiters': []}
        
    msg = {'id': len(ROOMS[code]['messages']), 'sender': data.get('sender'), 'text': data.get('text')}
    ROOMS[code]['messages'].append(msg)
    
    waiters = ROOMS[code]['waiters']
    ROOMS[code]['waiters'] = []
    for waiter in waiters:
        if not waiter.done():
            waiter.set_result(msg)
            
    return set_cors(web.json_response({'status': 'delivered'}))

async def wait_msg(request):
    data = await request.json()
    code = data.get('code')
    last_id = data.get('last_id', -1)

    if code not in ROOMS:
        ROOMS[code] = {'messages': [], 'waiters': []}

    messages = ROOMS[code]['messages']
    if len(messages) > last_id + 1:
        return set_cors(web.json_response({'status': 'ok', 'msgs': messages[last_id + 1:]}))

    loop = asyncio.get_running_loop()
    waiter = loop.create_future()
    ROOMS[code]['waiters'].append(waiter)

    try:
        new_msg = await asyncio.wait_for(waiter, timeout=25.0)
        return set_cors(web.json_response({'status': 'ok', 'msgs': [new_msg]}))
    except asyncio.TimeoutError:
        return set_cors(web.json_response({'status': 'timeout', 'msgs': []}))
    finally:
        if waiter in ROOMS[code]['waiters']:
            ROOMS[code]['waiters'].remove(waiter)

if __name__ == '__main__':
    app = web.Application()
    app.router.add_options('/{tail:.*}', handle_options)
    app.router.add_post('/api/send', send_msg)
    app.router.add_post('/api/wait', wait_msg)
    web.run_app(app, host='0.0.0.0', port=8080)
