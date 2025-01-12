from celery import shared_task
from yahoo_fin.stock_info import *
from threading import Thread
import queue
from channels.layers import get_channel_layer
import asyncio
import simplejson as json
# When bind=True is set, the first argument of the task function becomes the task instance itself.
# The @shared_task(bind=True) decorator is used to bind the task instance (the self object) to the task function.
# This allows the task to access attributes and methods of the task instance, 
# enabling additional functionality like retrying the task or accessing the task's request metadata.
@shared_task(bind = True)
def update_stock(self, stockpicker):
    # stockpicker, these are the stocks that has been selected by the user
    # Update the data at regular intervals
    data = {}
    available_stocks = tickers_nifty50()
    for i in stockpicker:
        if i in available_stocks:
            pass
        else:
            stockpicker.remove(i)
    
    n_threads = len(stockpicker)
    thread_list = []
    que = queue.Queue()
    for i in range(n_threads):
        thread = Thread(target = lambda q, arg1: q.put({stockpicker[i]: json.loads(json.dumps(get_quote_table(arg1), ignore_nan = True))}), args = (que, stockpicker[i]))
        thread_list.append(thread)
        thread_list[i].start()

    for thread in thread_list:
        thread.join()

    while not que.empty():
        result = que.get()
        data.update(result)

    # send data to group, first we retrive the channel layer
    channel_layer = get_channel_layer()
    # Function used to send data to a group is async function, we are running this
    # function inside celery worker, currently it has no event loop, to add event loop
    # we want to add asyncio module
    loop = asyncio.new_event_loop()

    # setting event loop inside our thread
    asyncio.set_event_loop(loop)

    # After we have started loop inside the thread, then we allocate a task in the lopp.
    # Loop will run until task cmpleted then we will proceed further
    # Group name is stock_track
    # message is data that you recieve.
    # After it calls to group_send, wee have to recive function in consumers
    # That recieve function will get all the data/messages that has been passed to group
    loop.run_until_complete(channel_layer.group_send("stock_track", {
        'type': 'send_stock_update',
        'message': data,
    }))
            
    
    return 'Done'