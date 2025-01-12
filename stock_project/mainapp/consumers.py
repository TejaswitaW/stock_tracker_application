import json
from mainapp.models import StockDetail
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from asgiref.sync import sync_to_async, async_to_sync
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import copy
class StockConsumer(AsyncWebsocketConsumer):
    # @sync_to_async as we are calling sync function inside async
    @sync_to_async
    def addToCeleryBeat(self, stockpicker):
        # Doing django ORM operations, because we want to add our new data to database,
        # we cant perform that in async function
        # We want to perform some changes in PeriodicTask model
        # name = "every-10-seconds"the task that we create.
        task = PeriodicTask.objects.filter(name = "every-10-seconds")
        # len(task) > 0, means task is already existing, means someone tries to 
        # see stock we will add those arguments in the same task argument, so celery 
        # will call the API for those new stocks as well.
        if len(task)>0:
            print("hello")  # testing that task.first() will work or not
            task = task.first()
            args = json.loads(task.args)
            args = args[0]
            for x in stockpicker:
                if x not in args:
                    args.append(x)
            # dump data into celery beat arguments.
            task.args = json.dumps([args])
            task.save()
        else:
            # We have to create this task again
            # If we would have removed that task , we have to again add that task 
            # inside the table, and update args argument
            # Successfully added that task to periodic table, then build in celery wil
            # perform that task
            schedule, created = IntervalSchedule.objects.get_or_create(every=10, period = IntervalSchedule.SECONDS)
            task = PeriodicTask.objects.create(interval = schedule, name='every-10-seconds', task="mainapp.tasks.update_stock", args = json.dumps([stockpicker]))

    @sync_to_async    
    def addToStockDetail(self, stockpicker):
        user = self.scope["user"]
        for i in stockpicker:
            stock, created = StockDetail.objects.get_or_create(stock = i)
            stock.user.add(user)


    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'stock_%s' % self.room_name

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Parse query_string
        query_params = parse_qs(self.scope["query_string"].decode())

        print(query_params)
        # Getting user selected stocks from query string
        stockpicker = query_params['stockpicker']

        # add to celery beat, and create the task
        await self.addToCeleryBeat(stockpicker)

        # add user to stockdetail(database)
        await self.addToStockDetail(stockpicker)


        await self.accept()

    @sync_to_async
    def helper_func(self):
        user = self.scope["user"]
        stocks = StockDetail.objects.filter(user__id = user.id)
        task = PeriodicTask.objects.get(name = "every-10-seconds")
        args = json.loads(task.args)
        args = args[0]
        for i in stocks:
            i.user.remove(user)
            if i.user.count() == 0:
                args.remove(i.stock)
                i.delete()
        if args == None:
            args = []

        if len(args) == 0:
            # It will not access third party APIs
            task.delete()
        else:
            task.args = json.dumps([args])
            task.save()


    async def disconnect(self, close_code):
        # We want to delete all those 
        # stocks those are not present in the selected list of other users,
        # then we want to delete those stocks from the args field of periodic task
        await self.helper_func()

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    # Once it recives tha data we need to do certain changes here, then we will 
    # call function send_update which will actually send data to that websocket to
    # that user.
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_update',
                'message': message
            }
        )
    
    @sync_to_async
    def selectUserStocks(self):
        user = self.scope["user"]
        # Returns us a list.
        user_stocks = user.stockdetail_set.values_list('stock', flat = True)
        # Returning list of users stock. It is converted to list, if wee pass directly
        # to async function it will give django error.
        return list(user_stocks)

    # Receive message from room group
    async def send_stock_update(self, event):
        message = event['message']
        # If wee try to modify event directly here, when we do message = event['message'],
        # new reference for same event object will get created, so if we do any changes to 
        # message , the same changes will get reflected in original event object, so this
        # event object will get changed for all the users, we dont want that so, foll. code
        message = copy.copy(message)

        # Select users stock those present only in database corresponding to that user.
        # Using user stocks object here.
        user_stocks = await self.selectUserStocks()
        # After retrival of user stocks , we will delete those users stock from this 
        # message. message is a dictionary
        keys = message.keys()
        for key in list(keys):
            if key in user_stocks:
                pass
            else:
                del message[key]

        # Send message to WebSocket, user specific data
        await self.send(text_data=json.dumps(message))