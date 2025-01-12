from django.http.response import HttpResponse
from django.shortcuts import render
from yahoo_fin.stock_info import *
import time
import queue
from threading import Thread
from asgiref.sync import sync_to_async

def stockPicker(request):
    # Extracting 50 stocks present inside this nifty
    stock_picker = tickers_nifty50()
    # print(stock_picker)
    # Render this stock_picker to front end, got all the stocks present inside the nifty.
    return render(request, 'mainapp/stockpicker.html', {'stockpicker':stock_picker})

@sync_to_async
def checkAuthenticated(request):
    if not request.user.is_authenticated:
        return False
    else:
        return True

async def stockTracker(request):
    # Get all the real time data of stock that are selected by the user.
    is_loginned = await checkAuthenticated(request)
    if not is_loginned:
        return HttpResponse("Login First")
    # Get the list of all stocks selected by the user in backend.
    # We want in the list format all the selected stocks.
    # Name of the select attribute is 'stockpicker'
    stockpicker = request.GET.getlist('stockpicker')
    stockshare=str(stockpicker)[1:-1]
    
    print(stockpicker)
    # Creating dict, for rendering data to frontend.
    data = {}
    # We want to make user to select stocks that are mention(available_stocks) in the stockpicker.
    available_stocks = tickers_nifty50()
    for i in stockpicker:
        if i in available_stocks:
            pass
        else:
            return HttpResponse("Error")
    # How many threads we want.
    n_threads = len(stockpicker)
    thread_list = []
    que = queue.Queue()
    # start = time.time()
    # for i in stockpicker:
    #     result = get_quote_table(i)
    #     data.update({i: result})
    for i in range(n_threads):
        # get_quote_table() it is trying to webscrape the yahoo data
        # The args parameter passes the queue and the current stock symbol to the lambda.
        # Adding created dict to q.(Getting data returned by the thread inside the queue)
        thread = Thread(target = lambda q, arg1: q.put({stockpicker[i]: get_quote_table(arg1)}), args = (que, stockpicker[i]))
        # Creating thread list.
        thread_list.append(thread)
        # Starting all these threads.
        thread_list[i].start()

    for thread in thread_list:
        # We want to prceed futher after the threads completed their task.
        thread.join()

    while not que.empty():
        result = que.get()
        # Updating data dictionary
        data.update(result)
    # end = time.time()
    # time_taken =  end - start
    # print(time_taken)
            
    
    # print(data)
    # Sending this data to frontend using the context dictionary.
    return render(request, 'mainapp/stocktracker.html', {'data': data, 'room_name': 'track','selectedstock':stockshare})
